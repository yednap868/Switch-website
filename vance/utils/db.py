import traceback
from typing import Literal, Optional, Union

import pendulum
from google.cloud.firestore_v1 import Query
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from utils.firebase_init import FIREBASE_AVAILABLE, fs
from utils.gmail.settings import SELF_EMAIL, Collections
from utils.gmail.types import ParsedEmailThread

DataSaveCollections = Literal["users", "extractions"]


def save_data_merge(uid: str, collection: DataSaveCollections, data: dict) -> str:
    """
    Helper to save data to Firestore with merge=True.
    """
    try:
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            print("No data provided to log.")
        fs.collection(collection).document(uid).set(update_data, merge=True)
        msg = f"Successfully saved to {collection} for {uid}: {update_data}"
    except Exception as e:
        msg = f"Error saving to {collection} for {uid}: {e}"

    return msg


def save_conversation(
    uid: str,
    result: Optional[AgentRunResult] = None,
    messages: Optional[list[ModelMessage]] = None,
) -> bool:
    """
    Saves a conversation to Firestore.
    """
    try:
        messages_col = (
            fs.collection("conversations").document(uid).collection("messages")
        )

        if not messages:
            assert result
            messages_to_save = to_jsonable_python(result.new_messages())
        else:
            assert messages
            messages_to_save = to_jsonable_python(messages)

        batch = fs.batch()
        for message in messages_to_save:
            message["ts"] = pendulum.now()
            doc = messages_col.document()
            batch.set(doc, message)
        batch.commit()
        return True
    except Exception:
        traceback.print_exc()
        return False


def load_conversation(uid: str, limit: int = 20) -> list[ModelMessage]:
    """
    Loads recent conversation messages from Firestore.

    Args:
        uid: User's WhatsApp ID
        limit: Maximum number of messages to load (default 20, most recent)

    Returns:
        List of ModelMessage objects in chronological order
    """
    messages_col = fs.collection("conversations").document(uid).collection("messages")

    # Get the most recent N messages (order desc, limit, then reverse)
    messages_docs = list(
        messages_col.order_by("ts", direction=Query.DESCENDING).limit(limit).stream()
    )
    messages_docs.reverse()  # Back to chronological order

    messages = []
    for doc in messages_docs:
        message = doc.to_dict()
        if not message:
            continue

        # ModelMessage does not have a ts field
        if "ts" in message:
            del message["ts"]

        # Filter out tool_result and tool_use blocks from ALL messages
        # This prevents "unexpected tool_use_id found in tool_result blocks" errors
        # Tool results and tool uses are not needed for conversation context and can cause API errors
        # We need to check ALL message kinds, not just "response"
        content = message.get("content", [])
        if isinstance(content, list):
            # Remove all tool_result and tool_use blocks - they're not needed for context
            # CRITICAL: Must filter BEFORE validation to prevent tool_use_id mismatches
            filtered_content = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    # Skip both tool_result and tool_use blocks to avoid mismatches
                    # Also check for tool_use_id field as an additional safety check
                    if item_type in ("tool_result", "tool_use") or "tool_use_id" in item:
                        continue
                # Only add non-dict items or dict items that aren't tool blocks
                elif not isinstance(item, dict):
                    # Keep non-dict content (like text strings)
                    filtered_content.append(item)
                # If it's a dict but not a tool block, keep it
                else:
                    filtered_content.append(item)
            
            # Update content if we filtered anything
            if len(filtered_content) != len(content):
                message["content"] = filtered_content
                # If we removed all content, skip this message
                if not filtered_content:
                    continue
        elif isinstance(content, dict):
            # Handle case where content is a single dict (shouldn't happen, but be safe)
            content_type = content.get("type")
            if content_type in ("tool_result", "tool_use") or "tool_use_id" in content:
                # Skip this entire message if it's only a tool block
                continue

        messages.append(message)

    # Final pass: Double-check for any remaining tool blocks before validation
    # This is a safety net in case the first pass missed anything
    final_messages = []
    for msg in messages:
        content = msg.get("content", [])
        if isinstance(content, list):
            # Second pass filtering - remove any tool blocks that might have been missed
            final_content = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    # Remove any tool blocks or items with tool_use_id
                    if item_type in ("tool_result", "tool_use") or "tool_use_id" in item:
                        continue
                final_content.append(item)
            
            # Only keep message if it has non-tool content
            if final_content:
                msg["content"] = final_content
                final_messages.append(msg)
        elif content:  # Non-list content (shouldn't happen, but keep it)
            final_messages.append(msg)
    
    # Validate messages and handle any validation errors gracefully
    try:
        validated_messages = ModelMessagesTypeAdapter.validate_python(final_messages)
        return validated_messages
    except Exception as e:
        error_str = str(e).lower()
        print(f"⚠️ [LOAD_CONVERSATION] Validation error for {uid}: {e}")
        
        # If it's a tool_use_id error, be even more aggressive
        if "tool_use_id" in error_str or "tool_result" in error_str:
            print(f"⚠️ [LOAD_CONVERSATION] Tool-related error detected, removing ALL messages with any tool references...")
            ultra_filtered = []
            for msg in final_messages:
                content = msg.get("content", [])
                if isinstance(content, list):
                    # Remove message if ANY item has tool_use_id or is a tool block
                    has_tool_ref = False
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") in ("tool_result", "tool_use") or "tool_use_id" in item:
                                has_tool_ref = True
                                break
                    if not has_tool_ref:
                        ultra_filtered.append(msg)
                else:
                    ultra_filtered.append(msg)
            
            if ultra_filtered:
                try:
                    validated_messages = ModelMessagesTypeAdapter.validate_python(ultra_filtered)
                    print(f"✅ [LOAD_CONVERSATION] Fixed tool error, returning {len(validated_messages)} messages")
                    return validated_messages
                except Exception as e2:
                    print(f"❌ [LOAD_CONVERSATION] Still failing: {e2}")
        
        # Generic fallback: remove messages with empty content
        print(f"⚠️ [LOAD_CONVERSATION] Attempting generic fix...")
        fixed_messages = []
        for msg in final_messages:
            content = msg.get("content", [])
            if not content:
                continue
            if isinstance(content, list) and len(content) == 0:
                continue
            fixed_messages.append(msg)
        
        if fixed_messages:
            try:
                validated_messages = ModelMessagesTypeAdapter.validate_python(fixed_messages)
                print(f"✅ [LOAD_CONVERSATION] Fixed validation error, returning {len(validated_messages)} messages")
                return validated_messages
            except Exception as e2:
                print(f"❌ [LOAD_CONVERSATION] Still failing after fix attempt: {e2}")
                # Return empty list as last resort - better than crashing
                print(f"⚠️ [LOAD_CONVERSATION] Returning empty list to prevent crash")
                return []
        else:
            print(f"⚠️ [LOAD_CONVERSATION] No valid messages after filtering, returning empty list")
            return []


def save_data(uid: str, collection: DataSaveCollections, data: dict) -> bool:
    """
    Saves extracted data to Firestore.
    """
    try:
        data_ref = fs.collection(collection).document(uid)
        data_ref.set(data)
        return True
    except Exception:
        traceback.print_exc()
        return False


def get_user_profile(uid: str) -> dict:
    """
    Fetches user profile from Firestore.
    """
    print(f"[DB] Fetching user profile for uid={uid}")
    doc_ref = fs.collection("users").document(uid)
    doc = doc_ref.get()
    print(f"[DB] User profile fetched for uid={uid}")
    if doc.exists:
        return doc.to_dict()
    print(f"[DB] No user profile found for uid={uid}")
    return {}


def get_extraction_data(uid: str) -> dict:
    """
    Fetches extraction data from Firestore.
    """
    print(f"[DB] Fetching extraction data for uid={uid}")
    doc_ref = fs.collection("extractions").document(uid)
    doc = doc_ref.get()
    print(f"[DB] Extraction data fetched for uid={uid}")
    if doc.exists:
        data = doc.to_dict()
        # Debug logging for urgent needs
        if data and "urgent_needs" in data:
            urgent_needs = data.get("urgent_needs", "")
            print(
                f"🔍 [DB] Retrieved urgent_needs: '{urgent_needs}' (length: {len(urgent_needs) if urgent_needs else 0})"
            )
        return data
    print(f"[DB] No extraction data found for uid={uid}")
    return {}


def format_call_history_for_context(call_summaries: list) -> str:
    """
    Formats call summaries into a readable context string for Claude.
    """
    if not call_summaries:
        return "No previous calls recorded."

    formatted_history = []
    for idx, call in enumerate(call_summaries, 1):
        call_text = f"""
            Call {idx} ({call.get('call_id', 'unknown')}):
            - Outcome: {call.get('outcome', 'N/A')}
            - Summary: {call.get('extraction_summary', 'N/A')}
            - Follow-up: {call.get('follow_up_notes', 'N/A')}
            """
        formatted_history.append(call_text.strip())

    return "\n\n".join(formatted_history)


def get_agent_memory_for_call_summary(user_id: str) -> dict:
    """
    Fetches agent memory including all call summaries from Firestore.
    Returns structured call history with extraction summaries.
    """
    print(f"[DB] Fetching agent memory for call summary for user_id={user_id}")
    doc_ref = fs.collection("agent_memory").document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        agent_memory = doc.to_dict()
        print(f"[DB] Agent memory fetched for user_id={user_id}")

        # Extract call insights
        call_insights = agent_memory.get("call_insights", {})

        # Structure the call summaries
        call_summaries = []
        for call_key, call_data in call_insights.items():
            if isinstance(call_data, dict):
                summary = {
                    "call_id": call_key,
                    "outcome": call_data.get("call_outcome", ""),
                    "extraction_summary": call_data.get("extraction_summary", ""),
                    "follow_up_notes": call_data.get("follow_up_notes", ""),
                    "key_insights": call_data.get("key_insights", {}),
                    "timestamp": call_data.get("timestamp", ""),
                }
                call_summaries.append(summary)

        print(f"[DB] Found {len(call_summaries)} call summaries for user_id={user_id}")

        return {
            "user_id": user_id,
            "call_summaries": call_summaries,
            "total_calls": len(call_summaries),
            "raw_call_insights": call_insights,
        }

    print(f"[DB] No agent memory found for user_id={user_id}")
    return {"user_id": user_id, "call_summaries": [], "total_calls": 0}


def get_thread_from_db(
    self_email: str,
    thread_id: str,
    latest_reply_first: bool = False,
    skip_replies: int = 0,
) -> Optional[ParsedEmailThread]:
    """
    Retrieves the old thread data from firestore if it exists, None otherwise.
    """
    thread = (
        fs.collection(Collections.EMAILS.value)
        .document(self_email)
        .collection(Collections.THREADS.value)
        .document(thread_id)
        .get()
    )

    if not thread.exists:
        return None

    children = list(
        thread.reference.collection(Collections.REPLIES.value).order_by("ts").get()
    )

    # Exclude the specified number of replies if latest_reply_first is True and there are replies
    if latest_reply_first and children:
        children = children[:-skip_replies] if skip_replies > 0 else children

    # Log each reply's timestamp and message_id
    for child in children:
        child_data = child.to_dict()
        print(
            f"Reply: ts={child_data.get('ts')}, message_id={child_data.get('message_id')}"
        )

    return ParsedEmailThread.from_dicts(
        self_dict=thread.to_dict()["thread"],
        children_dicts=[child.to_dict() for child in children if child.exists],
        latest_reply_first=latest_reply_first,
    )


def find_connection_metadata_from_thread_id(thread_id: str):
    """
    Retrieves connection data from a thread_id.
    """
    connections_ref = fs.collection("connections")
    query = connections_ref.where("consent_thread_id", "==", thread_id).limit(1)
    docs = query.stream()

    for doc in docs:
        return doc.to_dict()

    return None
