"""
Conversation history management module.
Handles message storage, 7-day retention, and context loading.
"""

import time
from typing import Any, Dict, List, Optional

try:
    from utils.db import fs

    FIREBASE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ [FIREBASE] Firebase not available: {e}")
    fs = None
    FIREBASE_AVAILABLE = False


class ConversationHistoryManager:
    """Manages conversation history with 7-day retention."""

    def __init__(self):
        self.retention_days = 7
        self.retention_seconds = self.retention_days * 24 * 60 * 60

    def _get_cutoff_timestamp(self) -> float:
        """Get timestamp for 7 days ago."""
        return time.time() - self.retention_seconds

    def save_message(
        self,
        user_id: str,
        sender: str,
        content: str,
        message_type: str = "text",
        metadata: dict = None,
    ):
        """Save a message to conversation history."""
        if not FIREBASE_AVAILABLE:
            print(
                f"💬 [HISTORY] Firebase not available - message not saved: {sender}: {content[:50]}..."
            )
            return
        try:
            message_data = {
                "timestamp": time.time(),
                "sender": sender,  # "user" or "agent"
                "content": content,
                "type": message_type,
                "metadata": metadata or {},
                "channel": (
                    metadata.get("channel", "whatsapp") if metadata else "whatsapp"
                ),  # Track if it's WhatsApp, voice, etc.
            }

            # Add to conversations collection
            fs.collection("conversations").document(user_id).collection("messages").add(
                message_data
            )

            # Update conversation summary
            self._update_conversation_summary(user_id, message_data)

            print(f"💬 [HISTORY] Saved {sender} {message_type} message for {user_id}")

        except Exception as e:
            print(f"❌ [HISTORY] Error saving message: {e}")

    def save_voice_call_summary(self, user_id: str, call_summary: dict):
        """Save voice call summary and key insights."""
        if not FIREBASE_AVAILABLE:
            print(f"📞 [VOICE] Firebase not available - voice call summary not saved")
            return

        try:
            voice_data = {
                "timestamp": time.time(),
                "type": "voice_call_summary",
                "call_duration": call_summary.get("duration", 0),
                "key_insights": call_summary.get("key_insights", {}),
                "extraction_data": call_summary.get("extraction_data", {}),
                "follow_up_call": call_summary.get("is_follow_up", False),
                "referral_messages_sent": call_summary.get(
                    "referral_messages_sent", False
                ),
                "referral_message_timestamp": call_summary.get(
                    "referral_message_timestamp", None
                ),
                "channel": "voice",
            }

            # Save as a special message type
            fs.collection("conversations").document(user_id).collection("messages").add(
                voice_data
            )

            # Update user profile with latest extraction data
            if call_summary.get("extraction_data"):
                fs.collection("users").document(user_id).set(
                    {
                        "latest_extraction": call_summary["extraction_data"],
                        "last_voice_call": time.time(),
                    },
                    merge=True,
                )

            print(f"📞 [VOICE] Saved voice call summary for {user_id}")

        except Exception as e:
            print(f"❌ [VOICE] Error saving voice call summary: {e}")

    def get_voice_call_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get voice call history for a user."""
        if not FIREBASE_AVAILABLE:
            return []

        try:
            messages_ref = (
                fs.collection("conversations").document(user_id).collection("messages")
            )

            # Try the optimized query first (requires composite index)
            try:
                query = (
                    messages_ref.where("type", "==", "voice_call_summary")
                    .order_by("timestamp", direction="DESCENDING")
                    .limit(limit)
                )
                voice_calls = []
                for doc in query.stream():
                    call_data = doc.to_dict()
                    call_data["id"] = doc.id
                    voice_calls.append(call_data)

                print(
                    f"📞 [VOICE] Retrieved {len(voice_calls)} voice call records for {user_id} (optimized)"
                )
                return voice_calls

            except Exception as index_error:
                # Fallback: Get all voice_call_summary messages and sort in memory
                print(
                    f"⚠️ [VOICE] Composite index missing, using fallback query: {str(index_error)[:100]}..."
                )

                try:
                    # Get all voice_call_summary messages without ordering
                    query = messages_ref.where(
                        "type", "==", "voice_call_summary"
                    ).limit(
                        limit * 2
                    )  # Get more to sort

                    voice_calls = []
                    for doc in query.stream():
                        call_data = doc.to_dict()
                        call_data["id"] = doc.id
                        voice_calls.append(call_data)

                    # Sort by timestamp in memory (most recent first)
                    voice_calls.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

                    # Limit results
                    voice_calls = voice_calls[:limit]

                    print(
                        f"📞 [VOICE] Retrieved {len(voice_calls)} voice call records for {user_id} (fallback)"
                    )
                    return voice_calls

                except Exception as fallback_error:
                    print(f"❌ [VOICE] Fallback query also failed: {fallback_error}")
                    return []

        except Exception as e:
            print(f"❌ [VOICE] Error retrieving voice call history: {e}")
            return []

    def get_recent_messages(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent messages for a user (last 7 days)."""
        if not FIREBASE_AVAILABLE:
            return []
        try:
            cutoff_time = self._get_cutoff_timestamp()

            # Query messages from last 7 days
            messages_ref = (
                fs.collection("conversations").document(user_id).collection("messages")
            )
            query = (
                messages_ref.where("timestamp", ">=", cutoff_time)
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
            )

            messages = []
            for doc in query.stream():
                message_data = doc.to_dict()
                message_data["id"] = doc.id
                messages.append(message_data)

            # Return in chronological order (oldest first)
            messages.reverse()

            print(f"📚 [HISTORY] Retrieved {len(messages)} messages for {user_id}")
            return messages

        except Exception as e:
            print(f"❌ [HISTORY] Error retrieving messages: {e}")
            return []

    def get_conversation_context(self, user_id: str) -> Dict[str, Any]:
        """Get conversation context including recent messages and summary."""
        try:
            # Get recent messages
            recent_messages = self.get_recent_messages(user_id, limit=20)

            # Get conversation summary
            summary_doc = fs.collection("conversations").document(user_id).get()
            summary_data = summary_doc.to_dict() if summary_doc.exists else {}

            context = {
                "recent_messages": recent_messages,
                "message_count": len(recent_messages),
                "last_interaction": summary_data.get("last_interaction", 0),
                "conversation_summary": summary_data.get("summary", ""),
                "key_topics": summary_data.get("key_topics", []),
                "user_goals": summary_data.get("user_goals", []),
            }

            print(f"🧠 [CONTEXT] Retrieved context for {user_id}")
            return context

        except Exception as e:
            print(f"❌ [CONTEXT] Error retrieving context: {e}")
            return {"recent_messages": [], "message_count": 0}

    def _update_conversation_summary(self, user_id: str, message_data: Dict):
        """Update conversation summary with new message."""
        try:
            summary_doc = fs.collection("conversations").document(user_id).get()
            summary_data = summary_doc.to_dict() if summary_doc.exists else {}

            # Update basic info
            summary_data["last_interaction"] = message_data["timestamp"]
            summary_data["message_count"] = summary_data.get("message_count", 0) + 1

            # Extract key topics from user messages using intelligent analysis
            if message_data["sender"] == "user":
                content = message_data["content"]
                existing_topics = summary_data.get("key_topics", [])

                # Use intelligent topic extraction for user messages
                new_topics = self._extract_message_topics(content, existing_topics)

                # Merge with existing topics (avoid duplicates)
                all_topics = existing_topics + [
                    topic for topic in new_topics if topic not in existing_topics
                ]
                summary_data["key_topics"] = all_topics[:5]  # Keep top 5 topics

            # Save updated summary
            fs.collection("conversations").document(user_id).set(
                summary_data, merge=True
            )

        except Exception as e:
            print(f"❌ [SUMMARY] Error updating summary: {e}")

    def _extract_message_topics(
        self, content: str, existing_topics: List[str]
    ) -> List[str]:
        """Extract topics from a single message using intelligent analysis."""
        if not content or len(content.strip()) < 10:
            return []

        try:
            from services.claude_profile_service import ClaudeProfileService

            # Create intelligent topic extraction prompt
            topic_prompt = f"""
Analyze this user message and extract key business topics mentioned.

USER MESSAGE: "{content}"
EXISTING TOPICS: {existing_topics}

EXTRACT TOPICS BASED ON:
1. Business activities (hiring, sales, partnerships, etc.)
2. Goals and objectives mentioned
3. Industry or domain references
4. Specific business needs or challenges
5. Products or services mentioned

RULES:
- Extract specific, actionable topics
- Avoid duplicating existing topics
- Use 2-3 words maximum per topic
- Focus on business-relevant topics only
- Return empty list if no clear business topics

RESPOND WITH JSON LIST (max 3 new topics):
["topic1", "topic2", "topic3"]
"""

            claude_service = ClaudeProfileService()
            response = claude_service._call_claude_api(topic_prompt).strip()

            # Parse JSON response
            import json

            topics = json.loads(response)

            if isinstance(topics, list):
                # Filter out empty or invalid topics
                valid_topics = [
                    topic
                    for topic in topics
                    if topic and isinstance(topic, str) and len(topic.strip()) > 2
                ]
                print(
                    f"🧠 [MESSAGE_TOPICS] Extracted {len(valid_topics)} topics from message"
                )
                return valid_topics[:3]  # Max 3 topics per message
            else:
                return []

        except Exception as e:
            print(f"❌ [MESSAGE_TOPICS] Error: {e}")
            # Fallback to simple heuristic extraction
            return self._fallback_message_topics(content, existing_topics)

    def _fallback_message_topics(
        self, content: str, existing_topics: List[str]
    ) -> List[str]:
        """Fallback topic extraction using simple heuristics."""
        content_lower = content.lower()
        new_topics = []

        # Business activity indicators
        if any(word in content_lower for word in ["looking for", "need", "seeking"]):
            if "investor" in content_lower:
                new_topics.append("investor search")
            elif "hire" in content_lower or "hiring" in content_lower:
                new_topics.append("team hiring")
            elif "customer" in content_lower:
                new_topics.append("customer acquisition")
            elif "partner" in content_lower:
                new_topics.append("partnerships")

        # Product/company indicators
        if any(
            word in content_lower for word in ["platform", "product", "app", "software"]
        ):
            new_topics.append("product development")

        # Funding indicators
        if any(
            word in content_lower
            for word in ["funding", "investment", "capital", "raise"]
        ):
            new_topics.append("fundraising")

        # Filter out existing topics
        new_topics = [topic for topic in new_topics if topic not in existing_topics]

        return new_topics[:2]  # Max 2 topics from fallback

    def cleanup_old_messages(self, user_id: str = None):
        """Clean up messages older than 7 days."""
        try:
            cutoff_time = self._get_cutoff_timestamp()

            if user_id:
                # Clean up specific user
                messages_ref = (
                    fs.collection("conversations")
                    .document(user_id)
                    .collection("messages")
                )
                query = messages_ref.where("timestamp", "<", cutoff_time)

                deleted_count = 0
                for doc in query.stream():
                    doc.reference.delete()
                    deleted_count += 1

                print(
                    f"🧹 [CLEANUP] Deleted {deleted_count} old messages for {user_id}"
                )
            else:
                # Clean up all users (batch operation)
                conversations_ref = fs.collection("conversations")
                for user_doc in conversations_ref.stream():
                    user_id = user_doc.id
                    self.cleanup_old_messages(user_id)

                print(f"🧹 [CLEANUP] Completed cleanup for all users")

        except Exception as e:
            print(f"❌ [CLEANUP] Error during cleanup: {e}")

    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a user."""
        try:
            # Get total message count
            messages_ref = (
                fs.collection("conversations").document(user_id).collection("messages")
            )
            total_messages = len(list(messages_ref.stream()))

            # Get recent message count (last 7 days)
            recent_messages = self.get_recent_messages(user_id, limit=1000)
            recent_count = len(recent_messages)

            # Get conversation summary
            summary_doc = fs.collection("conversations").document(user_id).get()
            summary_data = summary_doc.to_dict() if summary_doc.exists else {}

            stats = {
                "total_messages": total_messages,
                "recent_messages": recent_count,
                "last_interaction": summary_data.get("last_interaction", 0),
                "conversation_age_days": (
                    time.time() - summary_data.get("created_at", time.time())
                )
                / (24 * 60 * 60),
                "key_topics": summary_data.get("key_topics", []),
                "user_goals": summary_data.get("user_goals", []),
            }

            return stats

        except Exception as e:
            print(f"❌ [STATS] Error getting stats: {e}")
            return {"total_messages": 0, "recent_messages": 0}


# Global conversation history manager instance
conversation_history = ConversationHistoryManager()
