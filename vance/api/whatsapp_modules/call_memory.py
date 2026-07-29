"""
Call memory and tracking system.
Handles complete conversation logging, call sequences, and agent memory.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

try:
    from utils.db import fs

    FIREBASE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ [FIREBASE] Firebase not available: {e}")
    fs = None
    FIREBASE_AVAILABLE = False


class TopicsResult(BaseModel):
    """Structured result for topic extraction."""

    topics: List[str] = Field(
        default_factory=list,
        description="List of specific, actionable conversation topics (max 5)",
    )


# Topic extraction agent (initialized once, reused)
_topic_extraction_agent = Agent(
    "anthropic:claude-3-5-haiku-20241022",
    output_type=TopicsResult,
    system_prompt="""You are a business conversation analyst. Extract the main topics discussed in a conversation.

Focus on:
1. Business activities (hiring, sales, partnerships, fundraising)
2. User's goals and priorities
3. Immediate needs and challenges
4. Industry or domain focus
5. Specific business processes discussed

Use specific, actionable topic names like:
- "angel investor fundraising" (not just "fundraising")
- "engineering team hiring" (not just "hiring")
- "B2B SaaS sales" (not just "sales")
- "technical partnerships" (not just "partnerships")

Return at most 5 topics.""",
)


class CallMemoryManager:
    """Manages call memory, conversation history, and agent context."""

    def __init__(self):
        self.retention_days = 90  # Keep call history for 90 days
        self.retention_seconds = self.retention_days * 24 * 60 * 60

    async def save_complete_call_log(self, user_id: str, call_data: dict) -> bool:
        """
        Save complete call log with full conversation transcript.

        Args:
            user_id: User identifier
            call_data: Complete call data including transcript, metadata, etc.

        Returns:
            bool: Success status
        """
        if not FIREBASE_AVAILABLE:
            print(f"📞 [CALL_MEMORY] Firebase not available - call log not saved")
            return False

        try:
            # Get call sequence number
            call_sequence = self._get_next_call_sequence(user_id)

            # Prepare complete call log
            call_log = {
                "user_id": user_id,
                "call_sequence": call_sequence,
                "timestamp": time.time(),
                "call_id": call_data.get("call_id", ""),
                "conversation_id": call_data.get("conversation_id", ""),
                "call_duration": call_data.get("duration", 0),
                "full_transcript": call_data.get("transcript", ""),
                "agent_messages": call_data.get("agent_messages", []),
                "user_messages": call_data.get("user_messages", []),
                "key_insights": call_data.get("key_insights", {}),
                "extraction_data": call_data.get("extraction_data", {}),
                "call_outcome": call_data.get("outcome", ""),
                "follow_up_notes": call_data.get("follow_up_notes", ""),
                "referral_messages_sent": call_data.get(
                    "referral_messages_sent", False
                ),
                "call_quality_score": call_data.get("quality_score", 0),
                "channel": "voice",
                "created_at": datetime.now().isoformat(),
            }

            # Save to user's call history
            fs.collection("user_calls").document(user_id).collection("calls").add(
                call_log
            )

            # Update user's call summary
            self._update_user_call_summary(user_id, call_log)

            # Update agent memory (async for LLM topic extraction)
            await self._update_agent_memory(user_id, call_log)

            print(
                f"📞 [CALL_MEMORY] Saved complete call log for {user_id} (call #{call_sequence})"
            )
            return True

        except Exception as e:
            print(f"❌ [CALL_MEMORY] Error saving call log: {e}")
            return False

    def _get_next_call_sequence(self, user_id: str) -> int:
        """Get the next call sequence number for a user."""
        try:
            # Get user's call summary to find current sequence
            doc_ref = fs.collection("user_call_summaries").document(user_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                current_sequence = data.get("total_calls", 0)
                return current_sequence + 1
            else:
                return 1  # First call

        except Exception as e:
            print(f"⚠️ [CALL_MEMORY] Error getting call sequence: {e}")
            return 1

    def _update_user_call_summary(self, user_id: str, call_log: dict):
        """Update user's call summary with latest call information."""
        try:
            doc_ref = fs.collection("user_call_summaries").document(user_id)
            doc = doc_ref.get()

            current_time = time.time()
            call_sequence = call_log["call_sequence"]

            if doc.exists:
                # Update existing summary
                data = doc.to_dict()
                total_calls = data.get("total_calls", 0) + 1
                last_call_timestamp = current_time

                # Update call history
                call_history = data.get("call_history", [])
                call_history.append(
                    {
                        "call_sequence": call_sequence,
                        "timestamp": current_time,
                        "duration": call_log["call_duration"],
                        "outcome": call_log["call_outcome"],
                    }
                )

                # Keep only last 10 calls in summary
                if len(call_history) > 10:
                    call_history = call_history[-10:]

                doc_ref.update(
                    {
                        "total_calls": total_calls,
                        "last_call_timestamp": last_call_timestamp,
                        "last_call_sequence": call_sequence,
                        "call_history": call_history,
                        "updated_at": current_time,
                    }
                )
            else:
                # Create new summary
                doc_ref.set(
                    {
                        "user_id": user_id,
                        "total_calls": 1,
                        "first_call_timestamp": current_time,
                        "last_call_timestamp": current_time,
                        "last_call_sequence": call_sequence,
                        "call_history": [
                            {
                                "call_sequence": call_sequence,
                                "timestamp": current_time,
                                "duration": call_log["call_duration"],
                                "outcome": call_log["call_outcome"],
                            }
                        ],
                        "created_at": current_time,
                        "updated_at": current_time,
                    }
                )

            print(f"📊 [CALL_SUMMARY] Updated call summary for {user_id}")

        except Exception as e:
            print(f"❌ [CALL_SUMMARY] Error updating call summary: {e}")

    async def _update_agent_memory(self, user_id: str, call_log: dict):
        """Update agent memory with conversation context."""
        try:
            # Get previous agent memory
            memory_ref = fs.collection("agent_memory").document(user_id)
            memory_doc = memory_ref.get()

            current_time = time.time()
            call_sequence = call_log["call_sequence"]

            # Prepare agent memory update with intelligent extraction
            extraction_data = call_log.get("extraction_data", {})

            # Extract topics asynchronously using LLM
            recent_topics = await self._extract_recent_topics(call_log)

            memory_update = {
                "last_call_sequence": call_sequence,
                "last_call_timestamp": current_time,
                "conversation_context": {
                    "recent_topics": recent_topics,
                    "user_goals": extraction_data.get("current_focus", ""),
                    "user_needs": extraction_data.get("urgent_needs", ""),
                    "user_story": extraction_data.get("the_story", ""),
                    "user_priorities": extraction_data.get("top_priority", ""),
                    "user_vision": extraction_data.get("future_vision", ""),
                },
                "call_insights": {
                    f"call_{call_sequence}": {
                        "key_insights": call_log.get("key_insights", {}),
                        "call_outcome": call_log.get("call_outcome", ""),
                        "follow_up_notes": call_log.get("follow_up_notes", ""),
                        "extraction_summary": self._create_extraction_summary(
                            extraction_data
                        ),
                    }
                },
                "updated_at": current_time,
            }

            if memory_doc.exists:
                # Update existing memory
                existing_data = memory_doc.to_dict()
                existing_insights = existing_data.get("call_insights", {})
                existing_insights.update(memory_update["call_insights"])
                memory_update["call_insights"] = existing_insights

                memory_ref.update(memory_update)
            else:
                # Create new memory
                memory_update["user_id"] = user_id
                memory_update["created_at"] = current_time
                memory_ref.set(memory_update)

            print(f"🧠 [AGENT_MEMORY] Updated agent memory for {user_id}")

        except Exception as e:
            print(f"❌ [AGENT_MEMORY] Error updating agent memory: {e}")

    async def _extract_recent_topics(self, call_log: dict) -> List[str]:
        """Extract recent conversation topics using intelligent semantic analysis."""
        try:
            transcript = call_log.get("full_transcript", "")
            extraction_data = call_log.get("extraction_data", {})

            if not transcript and not extraction_data:
                return []

            # Use intelligent topic extraction with pydantic_ai
            topics = await self._intelligent_topic_extraction(
                transcript, extraction_data
            )

            return topics[:5]  # Keep only top 5 topics

        except Exception as e:
            print(f"⚠️ [TOPICS] Error extracting topics: {e}")
            return []

    async def _intelligent_topic_extraction(
        self, transcript: str, extraction_data: dict
    ) -> List[str]:
        """Use LLM to intelligently extract conversation topics via pydantic_ai."""
        try:
            # Prepare content for topic extraction
            content_parts = []
            if transcript:
                content_parts.append(f"Transcript: {transcript}")
            if extraction_data:
                for key, value in extraction_data.items():
                    if value:
                        content_parts.append(f"{key}: {value}")

            if not content_parts:
                return []

            content = "\n".join(content_parts)

            # Use pydantic_ai agent for structured output (handles retries automatically)
            result = await _topic_extraction_agent.run(
                f"Extract topics from this conversation:\n\n{content}"
            )

            topics = result.output.topics
            print(
                f"🧠 [INTELLIGENT_TOPICS] Extracted {len(topics)} topics from conversation"
            )
            return topics

        except Exception as e:
            print(f"❌ [INTELLIGENT_TOPICS] Error: {e}")
            # Fallback to extraction data analysis
            return self._fallback_topic_extraction(extraction_data)

    def _fallback_topic_extraction(self, extraction_data: dict) -> List[str]:
        """Fallback topic extraction using extraction data."""
        topics = []

        # Extract topics from extraction data
        urgent_needs = extraction_data.get("urgent_needs", "")
        if urgent_needs:
            if "investor" in urgent_needs.lower():
                topics.append("investor fundraising")
            elif "hire" in urgent_needs.lower() or "hiring" in urgent_needs.lower():
                topics.append("team hiring")
            elif "customer" in urgent_needs.lower() or "sales" in urgent_needs.lower():
                topics.append("customer acquisition")
            elif "partner" in urgent_needs.lower():
                topics.append("business partnerships")

        current_focus = extraction_data.get("current_focus", "")
        if current_focus and len(topics) < 3:
            if "product" in current_focus.lower():
                topics.append("product development")
            elif "team" in current_focus.lower():
                topics.append("team management")
            elif "revenue" in current_focus.lower():
                topics.append("revenue growth")

        return topics[:5]

    def _create_extraction_summary(self, extraction_data: dict) -> str:
        """Create a concise summary of extraction data for agent memory."""
        if not extraction_data:
            return "No extraction data available"

        summary_parts = []

        # Add story if available
        story = extraction_data.get("the_story", "")
        if story:
            summary_parts.append(f"Story: {story[:100]}...")

        # Add current focus
        current_focus = extraction_data.get("current_focus", "")
        if current_focus:
            summary_parts.append(f"Focus: {current_focus}")

        # Add urgent needs
        urgent_needs = extraction_data.get("urgent_needs", "")
        if urgent_needs:
            summary_parts.append(f"Needs: {urgent_needs}")

        # Add top priority
        top_priority = extraction_data.get("top_priority", "")
        if top_priority:
            summary_parts.append(f"Priority: {top_priority}")

        # Add future vision
        future_vision = extraction_data.get("future_vision", "")
        if future_vision:
            summary_parts.append(f"Vision: {future_vision}")

        return (
            " | ".join(summary_parts)
            if summary_parts
            else "No key information extracted"
        )

    def get_call_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's call history."""
        if not FIREBASE_AVAILABLE:
            return []

        try:
            calls_ref = (
                fs.collection("user_calls").document(user_id).collection("calls")
            )
            query = calls_ref.order_by("timestamp", direction="DESCENDING").limit(limit)

            calls = []
            for doc in query.stream():
                call_data = doc.to_dict()
                call_data["id"] = doc.id
                calls.append(call_data)

            print(f"📞 [CALL_HISTORY] Retrieved {len(calls)} calls for {user_id}")
            return calls

        except Exception as e:
            print(f"❌ [CALL_HISTORY] Error retrieving call history: {e}")
            return []

    def get_agent_memory(self, user_id: str) -> Dict:
        """Get agent memory for a user."""
        if not FIREBASE_AVAILABLE:
            return {}

        try:
            memory_ref = fs.collection("agent_memory").document(user_id)
            memory_doc = memory_ref.get()

            if memory_doc.exists:
                return memory_doc.to_dict()
            else:
                return {}

        except Exception as e:
            print(f"❌ [AGENT_MEMORY] Error retrieving agent memory: {e}")
            return {}

    def get_call_summary(self, user_id: str) -> Dict:
        """Get user's call summary."""
        if not FIREBASE_AVAILABLE:
            return {}

        try:
            summary_ref = fs.collection("user_call_summaries").document(user_id)
            summary_doc = summary_ref.get()

            if summary_doc.exists:
                return summary_doc.to_dict()
            else:
                return {}

        except Exception as e:
            print(f"❌ [CALL_SUMMARY] Error retrieving call summary: {e}")
            return {}

    def get_conversation_context(self, user_id: str) -> str:
        """
        Get formatted conversation context for agent.
        Returns a string that can be included in agent prompts.
        """
        try:
            call_summary = self.get_call_summary(user_id)
            agent_memory = self.get_agent_memory(user_id)
            call_history = self.get_call_history(user_id, limit=3)

            if not call_summary:
                return "This is the user's first call."

            total_calls = call_summary.get("total_calls", 0)
            last_call_sequence = call_summary.get("last_call_sequence", 0)

            context_parts = [
                f"This is the user's {self._ordinal(total_calls)} call.",
                f"Previous call sequence: {last_call_sequence}",
            ]

            # Add conversation topics
            if agent_memory.get("conversation_context", {}).get("recent_topics"):
                topics = agent_memory["conversation_context"]["recent_topics"]
                context_parts.append(f"Recent topics discussed: {', '.join(topics)}")

            # Add user goals/needs
            user_goals = agent_memory.get("conversation_context", {}).get(
                "user_goals", ""
            )
            if user_goals:
                context_parts.append(f"User's current focus: {user_goals}")

            user_needs = agent_memory.get("conversation_context", {}).get(
                "user_needs", ""
            )
            if user_needs:
                context_parts.append(f"User's urgent needs: {user_needs}")

            # Add recent call insights
            if call_history:
                last_call = call_history[0]
                if last_call.get("call_outcome"):
                    context_parts.append(
                        f"Last call outcome: {last_call['call_outcome']}"
                    )

            return " | ".join(context_parts)

        except Exception as e:
            print(f"❌ [CONVERSATION_CONTEXT] Error generating context: {e}")
            return "Error retrieving conversation context."

    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def _update_call_referral_status(self, user_id: str, referral_sent: bool):
        """Update the latest call log with referral message status."""
        try:
            # Get the latest call for this user
            calls_ref = (
                fs.collection("user_calls").document(user_id).collection("calls")
            )
            query = calls_ref.order_by("timestamp", direction="DESCENDING").limit(1)

            for doc in query.stream():
                doc.reference.update(
                    {
                        "referral_messages_sent": referral_sent,
                        "referral_sent_timestamp": (
                            time.time() if referral_sent else None
                        ),
                    }
                )
                print(f"📞 [CALL_UPDATE] Updated referral status for call {doc.id}")
                break

        except Exception as e:
            print(f"❌ [CALL_UPDATE] Error updating referral status: {e}")


# Global instance
call_memory = CallMemoryManager()
