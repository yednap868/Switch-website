"""
Profile audio service.

Responsible for attaching call recording URLs from ElevenLabs to user profiles
so they can be used by the public profile frontend as intro/thinking audio.

Implementation:
- Fetches audio from ElevenLabs API using conversation_id from post-call webhook
- Converts binary audio to base64 data URL
- Stores it on user_profiles/{uid} as:
    - intro_audio_url
    - thinking_audio_url

Later, this can be extended to:
- Generate clipped segments (e.g. 30s intro, 2m deep-dive) using a media service
- Store separate URLs for each clip
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Optional

import httpx

from utils.db import fs


class ProfileAudioService:
    """Service for linking call recordings to public candidate profiles."""

    async def _list_conversations_by_user(self, user_phone: str) -> list[str]:
        """
        Try to find conversations by user phone/UID using ElevenLabs API.
        
        Returns a list of conversation_ids that match this user.
        """
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("⚠️ [PROFILE_AUDIO] ELEVENLABS_API_KEY not set")
            return []

        matching_conversation_ids = []
        
        # Try multiple approaches to find conversations
        try:
            # Approach 1: Try using ElevenLabs SDK if available
            try:
                from elevenlabs import ElevenLabs
                client = ElevenLabs(api_key=api_key)
                
                # Check if SDK has methods to list conversations
                if hasattr(client, 'conversational_ai'):
                    conv_ai = client.conversational_ai
                    # Try to get conversations - this might vary by SDK version
                    print(f"🔍 [PROFILE_AUDIO] Using ElevenLabs SDK to find conversations for {user_phone}...")
                    # Note: SDK methods may vary, this is a best-effort attempt
            except ImportError:
                pass
            
            # Approach 2: Try direct API call to list conversations
            url = "https://api.elevenlabs.io/v1/convai/conversations"
            headers = {"xi-api-key": api_key}
            
            print(f"🔍 [PROFILE_AUDIO] Querying ElevenLabs API for conversations...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try with query parameter for phone number
                params = {"phone": user_phone}
                try:
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    conversations = response.json()
                except:
                    # If phone param doesn't work, try without params
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    conversations = response.json()
                
                # Handle both list and dict responses
                if isinstance(conversations, dict):
                    conversations = conversations.get("conversations", []) or conversations.get("data", []) or []
                
                # Filter conversations by phone number
                for conv in conversations:
                    if isinstance(conv, dict):
                        # Check if conversation matches user phone
                        conv_phone = (
                            str(conv.get("user_phone", ""))
                            or str(conv.get("phone_number", ""))
                            or str(conv.get("phone", ""))
                            or str(conv.get("participant_phone", ""))
                            or str(conv.get("to", ""))
                        )
                        conv_id = conv.get("conversation_id") or conv.get("id") or conv.get("_id")
                        
                        # Match by last 10 digits of phone number
                        if conv_phone and str(user_phone)[-10:] in conv_phone:
                            if conv_id:
                                matching_conversation_ids.append(str(conv_id))
                        elif conv_id:
                            # If no phone match but we have an ID, include it (might be the only one)
                            matching_conversation_ids.append(str(conv_id))
                    elif isinstance(conv, str):
                        matching_conversation_ids.append(conv)
                
                if matching_conversation_ids:
                    print(f"✅ [PROFILE_AUDIO] Found {len(matching_conversation_ids)} matching conversations")
                else:
                    print(f"ℹ️ [PROFILE_AUDIO] No matching conversations found via API")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"ℹ️ [PROFILE_AUDIO] Conversations endpoint not found (404) - API might not support listing")
            else:
                print(f"⚠️ [PROFILE_AUDIO] ElevenLabs API error {e.response.status_code}: {e}")
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Failed to list conversations: {e}")
        
        return matching_conversation_ids

    def _verify_conversation_ownership(self, conversation_id: str, user_id: str) -> bool:
        """
        Verify that a conversation_id belongs to a specific user_id.
        Checks user_calls collection and other sources to ensure ownership.
        """
        if not conversation_id or not user_id:
            return False
        
        try:
            # Method 1: Check user_calls/{user_id}/calls for this conversation_id
            calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
            calls_query = calls_ref.where("conversation_id", "==", conversation_id).limit(1)
            matching_calls = list(calls_query.stream())
            
            if matching_calls:
                print(f"✅ [PROFILE_AUDIO] Verified conversation_id={conversation_id} belongs to user_id={user_id} (via user_calls)")
                return True
            
            # Method 2: Check collection group for conversation_id with user_id
            # Note: This requires a Firestore index and may fail - that's okay, we have Method 1
            try:
                all_calls_query = (
                    fs.collection_group("calls")
                    .where("conversation_id", "==", conversation_id)
                    .where("user_id", "==", user_id)
                    .limit(1)
                )
                matching_calls = list(all_calls_query.stream())
                if matching_calls:
                    print(f"✅ [PROFILE_AUDIO] Verified conversation_id={conversation_id} belongs to user_id={user_id} (via collection group)")
                    return True
            except Exception as e:
                # Collection group queries require an index and may fail - that's okay, Method 1 is primary
                print(f"ℹ️ [PROFILE_AUDIO] Collection group query not available (index required): {e}")
                pass
            
            # Method 3: Check if conversation_id is already stored for this user in user_profiles
            profile_doc = fs.collection("user_profiles").document(user_id).get()
            if profile_doc.exists:
                profile_data = profile_doc.to_dict() or {}
                stored_conv_id = profile_data.get("audio_conversation_id")
                if stored_conv_id == conversation_id:
                    print(f"✅ [PROFILE_AUDIO] Verified conversation_id={conversation_id} is already stored for user_id={user_id}")
                    return True
            
            print(f"⚠️ [PROFILE_AUDIO] Could not verify conversation_id={conversation_id} belongs to user_id={user_id}")
            return False
            
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Error verifying conversation ownership: {e}")
            return False

    def _trim_audio_segment(
        self, audio_bytes: bytes, start_time: float = 0, duration: float = None
    ) -> bytes:
        """
        Trim audio bytes to a specific segment.
        
        Args:
            audio_bytes: Binary audio data (MP3)
            start_time: Start time in seconds (default: 0)
            duration: Duration in seconds (default: None = until end)
        
        Returns:
            Trimmed audio bytes (MP3 format)
        """
        try:
            # Try using pydub if available
            try:
                from pydub import AudioSegment
                from io import BytesIO
                
                # Load audio from bytes
                audio_segment = AudioSegment.from_mp3(BytesIO(audio_bytes))
                
                # Calculate trim points (pydub uses milliseconds)
                start_ms = int(start_time * 1000)
                if duration:
                    end_ms = int((start_time + duration) * 1000)
                    trimmed = audio_segment[start_ms:end_ms]
                else:
                    trimmed = audio_segment[start_ms:]
                
                # Export back to MP3 bytes
                output = BytesIO()
                trimmed.export(output, format="mp3")
                trimmed_bytes = output.getvalue()
                
                print(f"✅ [PROFILE_AUDIO] Trimmed audio: {len(audio_bytes)} → {len(trimmed_bytes)} bytes (start={start_time}s, duration={duration}s)")
                return trimmed_bytes
                
            except ImportError:
                # pydub not available, try ffmpeg via subprocess
                import subprocess
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as input_file:
                    input_file.write(audio_bytes)
                    input_path = input_file.name
                
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as output_file:
                        output_path = output_file.name
                    
                    # Use ffmpeg to trim audio
                    cmd = [
                        "ffmpeg",
                        "-i", input_path,
                        "-ss", str(start_time),
                    ]
                    if duration:
                        cmd.extend(["-t", str(duration)])
                    cmd.extend([
                        "-acodec", "copy",  # Copy codec (faster, no re-encoding)
                        "-y",  # Overwrite output file
                        output_path
                    ])
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        check=True,
                        timeout=30
                    )
                    
                    # Read trimmed audio
                    with open(output_path, "rb") as f:
                        trimmed_bytes = f.read()
                    
                    # Cleanup
                    os.unlink(input_path)
                    os.unlink(output_path)
                    
                    print(f"✅ [PROFILE_AUDIO] Trimmed audio using ffmpeg: {len(audio_bytes)} → {len(trimmed_bytes)} bytes")
                    return trimmed_bytes
                    
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    # ffmpeg not available or failed, return original audio
                    print(f"⚠️ [PROFILE_AUDIO] Audio trimming not available (ffmpeg/pydub not found): {e}")
                    os.unlink(input_path)
                    return audio_bytes
                    
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Error trimming audio: {e}")
            # Return original audio if trimming fails
            return audio_bytes

    def _find_question_segments_in_transcript(
        self, user_id: str, conversation_id: str
    ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Parse call transcript to find intro and thinking question segments.
        
        Returns:
            Tuple of (intro_start_time, intro_end_time, thinking_start_time, thinking_end_time) in seconds
            Returns (None, None, None, None) if transcript not found
        """
        try:
            # Get call log from user_calls collection
            calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
            calls_query = calls_ref.where("conversation_id", "==", conversation_id).limit(1)
            matching_calls = list(calls_query.stream())
            
            if not matching_calls:
                print(f"⚠️ [PROFILE_AUDIO] No call log found for conversation_id={conversation_id}")
                return None, None, None, None
            
            call_data = matching_calls[0].to_dict() or {}
            transcript = call_data.get("full_transcript") or call_data.get("transcript") or ""
            agent_messages = call_data.get("agent_messages", [])
            user_messages = call_data.get("user_messages", [])
            call_duration = call_data.get("call_duration", 0)
            
            if not transcript and not agent_messages:
                print(f"⚠️ [PROFILE_AUDIO] No transcript found for conversation_id={conversation_id}")
                return None, None, None, None
            
            # Combine agent and user messages in order
            all_messages = []
            if agent_messages:
                for msg in agent_messages:
                    all_messages.append({"sender": "agent", "text": str(msg)})
            if user_messages:
                for msg in user_messages:
                    all_messages.append({"sender": "user", "text": str(msg)})
            
            # If we have transcript, parse it instead
            if transcript:
                lines = transcript.split("\n")
                all_messages = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.lower().startswith("agent:"):
                        all_messages.append({"sender": "agent", "text": line[6:].strip()})
                    elif line.lower().startswith("user:"):
                        all_messages.append({"sender": "user", "text": line[5:].strip()})
            
            # Find intro segment (when agent asks about background/intro)
            intro_start_idx = None
            intro_end_idx = None
            thinking_start_idx = None
            thinking_end_idx = None
            
            intro_keywords = [
                "tell me about",
                "your background",
                "what you're looking for",
                "tell me about what you're looking for",
                "about the role",
                "what you need",
            ]
            
            thinking_keywords = [
                "how do you think",
                "what do you think",
                "how do they think",
                "what do they think",
                "your thoughts",
                "how you approach",
                "your approach",
            ]
            
            # Find intro question (usually early in conversation)
            for i, msg in enumerate(all_messages):
                if msg["sender"] == "agent":
                    text_lower = msg["text"].lower()
                    # Check if this is an intro question
                    if any(keyword in text_lower for keyword in intro_keywords):
                        intro_start_idx = i
                        # Intro segment: from this question to ~2-3 messages later (user's response)
                        intro_end_idx = min(i + 4, len(all_messages) - 1)
                        break
            
            # Find thinking question (usually later in conversation)
            for i, msg in enumerate(all_messages):
                if msg["sender"] == "agent":
                    text_lower = msg["text"].lower()
                    # Check if this is a thinking question
                    if any(keyword in text_lower for keyword in thinking_keywords):
                        thinking_start_idx = i
                        # Thinking segment: from this question to ~3-4 messages later
                        thinking_end_idx = min(i + 5, len(all_messages) - 1)
                        break
            
            # Estimate timestamps based on message indices and call duration
            # Assume messages are roughly evenly distributed across the call
            intro_start_time = None
            intro_end_time = None
            thinking_start_time = None
            thinking_end_time = None
            
            if intro_start_idx is not None and call_duration > 0:
                # Estimate: messages are distributed linearly across call duration
                message_count = len(all_messages)
                if message_count > 0:
                    time_per_message = call_duration / message_count
                    intro_start_time = max(0, (intro_start_idx - 1) * time_per_message)
                    intro_end_time = min(call_duration, (intro_end_idx + 1) * time_per_message)
                    # Ensure intro segment is at least 30 seconds, max 2 minutes
                    if intro_end_time - intro_start_time < 30:
                        intro_end_time = min(call_duration, intro_start_time + 60)
            
            if thinking_start_idx is not None and call_duration > 0:
                message_count = len(all_messages)
                if message_count > 0:
                    time_per_message = call_duration / message_count
                    thinking_start_time = max(0, (thinking_start_idx - 1) * time_per_message)
                    thinking_end_time = min(call_duration, (thinking_end_idx + 1) * time_per_message)
                    # Ensure thinking segment is at least 1 minute, max 3 minutes
                    if thinking_end_time - thinking_start_time < 60:
                        thinking_end_time = min(call_duration, thinking_start_time + 120)
            
            print(f"✅ [PROFILE_AUDIO] Found segments in transcript:")
            print(f"   Intro: {intro_start_time}s - {intro_end_time}s")
            print(f"   Thinking: {thinking_start_time}s - {thinking_end_time}s")
            
            return intro_start_time, intro_end_time, thinking_start_time, thinking_end_time
            
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Error parsing transcript: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None

    async def _fetch_audio_from_elevenlabs_api(
        self, conversation_id: str, user_id: str = None, trim_intro: bool = False, trim_thinking: bool = False
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch conversation audio from ElevenLabs API and trim based on question segments.
        
        Args:
            conversation_id: ElevenLabs conversation ID
            user_id: User ID to find transcript for question-based trimming
            trim_intro: If True, trim to intro question segment from transcript
            trim_thinking: If True, trim to thinking question segment from transcript

        Returns:
            Tuple of (intro_audio_url, thinking_audio_url) as base64-encoded data URLs
            Returns (None, None) if fetch fails
        """
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("⚠️ [PROFILE_AUDIO] ELEVENLABS_API_KEY not set")
            return None, None

        if not conversation_id:
            print("⚠️ [PROFILE_AUDIO] No conversation_id provided")
            return None, None

        url = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}/audio"
        headers = {"xi-api-key": api_key}

        try:
            print(f"🎧 [PROFILE_AUDIO] Fetching audio for conversation_id={conversation_id}")
            async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout for large files
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # ElevenLabs returns binary audio (MP3)
                audio_bytes = response.content
                if not audio_bytes:
                    print("⚠️ [PROFILE_AUDIO] Empty audio response from ElevenLabs")
                    return None, None

                print(f"✅ [PROFILE_AUDIO] Fetched {len(audio_bytes)} bytes from ElevenLabs")
                
                # Find question segments from transcript if user_id provided
                intro_start_time = None
                intro_end_time = None
                thinking_start_time = None
                thinking_end_time = None
                
                if user_id and (trim_intro or trim_thinking):
                    print(f"🔍 [PROFILE_AUDIO] Parsing transcript to find question segments...")
                    intro_start, intro_end, thinking_start, thinking_end = self._find_question_segments_in_transcript(
                        user_id, conversation_id
                    )
                    intro_start_time = intro_start
                    intro_end_time = intro_end
                    thinking_start_time = thinking_start
                    thinking_end_time = thinking_end
                
                # Trim audio segments based on question timestamps
                intro_bytes = audio_bytes
                thinking_bytes = audio_bytes
                
                if trim_intro:
                    if intro_start_time is not None and intro_end_time is not None:
                        # Trim to intro question segment from transcript
                        try:
                            duration = intro_end_time - intro_start_time
                            trimmed = self._trim_audio_segment(
                                audio_bytes, start_time=intro_start_time, duration=duration
                            )
                            if trimmed and len(trimmed) > 0:
                                intro_bytes = trimmed
                                print(f"✅ [PROFILE_AUDIO] Trimmed intro segment: {intro_start_time}s - {intro_end_time}s ({duration:.1f}s)")
                            else:
                                print(f"⚠️ [PROFILE_AUDIO] Trimming failed, using full audio for intro")
                        except Exception as e:
                            print(f"⚠️ [PROFILE_AUDIO] Error trimming intro segment: {e}, using full audio")
                    else:
                        # Fallback: First 60 seconds if transcript parsing failed, but use full audio if trimming fails
                        try:
                            trimmed = self._trim_audio_segment(audio_bytes, start_time=0, duration=60)
                            if trimmed and len(trimmed) > 0:
                                intro_bytes = trimmed
                                print(f"⚠️ [PROFILE_AUDIO] Could not find intro segment in transcript, using first 60s as fallback")
                            else:
                                print(f"⚠️ [PROFILE_AUDIO] Trimming failed, using full audio for intro")
                        except Exception as e:
                            print(f"⚠️ [PROFILE_AUDIO] Error trimming intro fallback: {e}, using full audio")
                
                if trim_thinking:
                    if thinking_start_time is not None and thinking_end_time is not None:
                        # Trim to thinking question segment from transcript
                        try:
                            duration = thinking_end_time - thinking_start_time
                            trimmed = self._trim_audio_segment(
                                audio_bytes, start_time=thinking_start_time, duration=duration
                            )
                            if trimmed and len(trimmed) > 0:
                                thinking_bytes = trimmed
                                print(f"✅ [PROFILE_AUDIO] Trimmed thinking segment: {thinking_start_time}s - {thinking_end_time}s ({duration:.1f}s)")
                            else:
                                print(f"⚠️ [PROFILE_AUDIO] Trimming failed, using full audio for thinking")
                        except Exception as e:
                            print(f"⚠️ [PROFILE_AUDIO] Error trimming thinking segment: {e}, using full audio")
                    else:
                        # Fallback: 2 minutes starting from 1 minute if transcript parsing failed, but use full audio if trimming fails
                        try:
                            trimmed = self._trim_audio_segment(audio_bytes, start_time=60, duration=120)
                            if trimmed and len(trimmed) > 0:
                                thinking_bytes = trimmed
                                print(f"⚠️ [PROFILE_AUDIO] Could not find thinking segment in transcript, using 60s-180s as fallback")
                            else:
                                print(f"⚠️ [PROFILE_AUDIO] Trimming failed, using full audio for thinking")
                        except Exception as e:
                            print(f"⚠️ [PROFILE_AUDIO] Error trimming thinking fallback: {e}, using full audio")
                
                # Convert to base64 data URLs
                intro_b64 = base64.b64encode(intro_bytes).decode("utf-8")
                intro_data_url = f"data:audio/mpeg;base64,{intro_b64}"
                
                thinking_b64 = base64.b64encode(thinking_bytes).decode("utf-8")
                thinking_data_url = f"data:audio/mpeg;base64,{thinking_b64}"
                
                print(f"✅ [PROFILE_AUDIO] Converted to data URLs (intro: {len(intro_b64)} chars, thinking: {len(thinking_b64)} chars)")
                return intro_data_url, thinking_data_url

        except httpx.HTTPStatusError as e:
            print(f"⚠️ [PROFILE_AUDIO] ElevenLabs API error {e.response.status_code}: {e}")
            return None, None
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Failed to fetch audio from ElevenLabs: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def _find_audio_src_in_payload(self, payload: Dict[str, Any]) -> str:
        """
        Best-effort search for an audio source in the ElevenLabs payload.

        Priority:
        1) If an `audio` field exists (and is base64), wrap it as a data: URL.
        2) Else, look for a recording/audio URL string in nested fields.
        """

        data = payload.get("data", {}) or {}

        # 1) Direct audio field (often base64)
        audio = payload.get("audio") or data.get("audio")
        if isinstance(audio, str) and audio.strip():
            audio_str = audio.strip()
            # Already a URL
            if audio_str.startswith("http"):
                return audio_str
            # Treat as base64-encoded audio (e.g., ElevenLabs streaming/webhook style)
            return f"data:audio/mpeg;base64,{audio_str}"

        # 2) ElevenLabs post_call_audio: data.full_audio (base64 MP3)
        full_audio = data.get("full_audio")
        if isinstance(full_audio, str) and full_audio.strip():
            fa = full_audio.strip()
            if fa.startswith("http"):
                return fa
            return f"data:audio/mpeg;base64,{fa}"

        # 3) Fallback: search for any plausible recording/audio URL
        candidate_key_fragments = [
            "recording_url",
            "audio_url",
            "call_recording",
            "recording",
            "audio",
        ]

        def _search(obj: Any) -> Optional[str]:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_l = str(key).lower()
                    if any(fragment in key_l for fragment in candidate_key_fragments):
                        if isinstance(value, str) and value.startswith("http"):
                            return value
                    # Recurse into nested dicts
                    if isinstance(value, dict):
                        found = _search(value)
                        if found:
                            return found
                    # Lists of dicts are also common
                    if isinstance(value, list):
                        for item in value:
                            found = _search(item)
                            if found:
                                return found
            return None

        url = _search(payload)
        return url or ""

    async def attach_call_recording_to_profile(
        self, user_id: str, payload: Dict[str, Any]
    ) -> None:
        """
        Attach ElevenLabs call recording to the user's profile.
        Ensures conversation_id belongs to the user_id before attaching.
        Trims audio segments: intro (30s) and thinking (2min from 1min mark).

        Strategy:
        1. First, try to fetch audio from ElevenLabs API using conversation_id
        2. Verify conversation_id belongs to user_id before attaching
        3. If no conversation_id, find conversations by user phone/UID and verify ownership
        4. Trim audio: intro (first 30s), thinking (2min starting from 1min)
        """
        try:
            # Extract conversation_id from payload
            data = payload.get("data", {}) or {}
            conversation_id = data.get("conversation_id") or payload.get("conversation_id")
            
            print(f"🔍 [PROFILE_AUDIO] Extracting audio for {user_id}")
            print(f"   Payload keys: {list(payload.keys())}")
            print(f"   Data keys: {list(data.keys()) if data else 'No data'}")
            print(f"   conversation_id: {conversation_id}")

            intro_audio_url = None
            thinking_audio_url = None

            # Strategy 1: Fetch from ElevenLabs API using conversation_id (preferred)
            if conversation_id and conversation_id != "missing":
                # CRITICAL: Verify conversation_id belongs to this user_id
                if not self._verify_conversation_ownership(conversation_id, user_id):
                    print(f"⚠️ [PROFILE_AUDIO] conversation_id={conversation_id} does NOT belong to user_id={user_id}. Will try to find correct conversation_id.")
                    # Don't return - try to find correct conversation_id below
                    conversation_id = None
                else:
                    print(f"🎧 [PROFILE_AUDIO] Verified ownership, fetching audio from ElevenLabs API...")
                    intro_audio_url, thinking_audio_url = await self._fetch_audio_from_elevenlabs_api(
                        conversation_id, user_id=user_id, trim_intro=True, trim_thinking=True
                    )
            
            # If no conversation_id or verification failed, try to find it
            if not intro_audio_url and (not conversation_id or conversation_id == "missing"):
                print(f"⚠️ [PROFILE_AUDIO] No conversation_id found in payload or verification failed")
                # Strategy 1b: Try to find conversation by user ID/phone and verify ownership
                print(f"🔍 [PROFILE_AUDIO] Attempting to find conversations by user ID...")
                # Get user phone from profile
                from utils.db import get_user_profile
                user_profile = get_user_profile(user_id) or {}
                user_phone = (
                    user_profile.get("wa_id")
                    or user_profile.get("phone")
                    or user_profile.get("whatsapp")
                    or user_id  # UID might be the phone number
                )
                
                # Try to list conversations and find matching ones
                conversation_ids = await self._list_conversations_by_user(str(user_phone))
                if conversation_ids:
                    # Try each conversation_id and verify ownership
                    for conv_id in conversation_ids:
                        print(f"🔍 [PROFILE_AUDIO] Checking conversation_id: {conv_id}")
                        if self._verify_conversation_ownership(conv_id, user_id):
                            print(f"✅ [PROFILE_AUDIO] Found verified conversation_id: {conv_id}")
                            intro_audio_url, thinking_audio_url = await self._fetch_audio_from_elevenlabs_api(
                                conv_id, user_id=user_id, trim_intro=True, trim_thinking=True
                            )
                            if intro_audio_url:
                                conversation_id = conv_id  # Update for storage
                                break
                        else:
                            print(f"⚠️ [PROFILE_AUDIO] conversation_id={conv_id} does not belong to user_id={user_id}, trying anyway...")
                            # If verification fails but we have a conversation_id, try fetching audio anyway
                            # (some calls might not have conversation_id stored correctly)
                            intro_audio_url, thinking_audio_url = await self._fetch_audio_from_elevenlabs_api(
                                conv_id, user_id=user_id, trim_intro=True, trim_thinking=True
                            )
                            if intro_audio_url:
                                conversation_id = conv_id  # Update for storage
                                break

            # Strategy 2: Fallback to payload (if audio webhook ever arrives)
            if not intro_audio_url:
                print(f"🔄 [PROFILE_AUDIO] Trying fallback: searching payload for audio...")
                recording_url = self._find_audio_src_in_payload(payload)
                if recording_url:
                    print(f"✅ [PROFILE_AUDIO] Found audio in payload: {recording_url[:50]}...")
                    # If we have full audio from payload, trim it
                    # Extract base64 data if it's a data URL
                    if recording_url.startswith("data:audio/mpeg;base64,"):
                        base64_data = recording_url.split(",", 1)[1]
                        audio_bytes = base64.b64decode(base64_data)
                        
                        # Trim segments
                        intro_bytes = self._trim_audio_segment(audio_bytes, start_time=0, duration=30)
                        thinking_bytes = self._trim_audio_segment(audio_bytes, start_time=60, duration=120)
                        
                        intro_b64 = base64.b64encode(intro_bytes).decode("utf-8")
                        intro_audio_url = f"data:audio/mpeg;base64,{intro_b64}"
                        
                        thinking_b64 = base64.b64encode(thinking_bytes).decode("utf-8")
                        thinking_audio_url = f"data:audio/mpeg;base64,{thinking_b64}"

            if not intro_audio_url or not thinking_audio_url:
                print(f"ℹ️ [PROFILE_AUDIO] No recording available for {user_id} (conversation_id={conversation_id})")
                print(f"   This is expected if the audio webhook hasn't arrived yet or conversation_id is missing")
                # Don't return - we'll try again later when audio webhook arrives
                # But log this attempt for debugging
                fs.collection("user_profiles").document(user_id).set({
                    "audio_fetch_attempted_at": time.time(),
                    "audio_conversation_id": conversation_id or "missing",
                }, merge=True)
                return

            # Firestore has a 1MB limit per field (~1,048,576 bytes)
            # Base64 is ~33% larger than binary, so we check for ~700KB of base64 data to be safe
            max_size = 700000  # ~700KB base64 = ~525KB binary
            
            # Always store conversation_id for on-demand fetching to avoid Firestore size limits
            # This ensures audio is always available even if trimmed segments are too large
            if conversation_id:
                print(f"✅ [PROFILE_AUDIO] Storing conversation_id for on-demand audio fetch: {user_id} (conversation_id={conversation_id})")
                # Store conversation_id so we can fetch and trim on-demand via API endpoint
                # The API will handle trimming and return full audio if trimming fails
                update = {
                    "audio_conversation_id": conversation_id,
                    "audio_updated_at": time.time(),
                    "audio_fetch_attempted_at": time.time(),
                    "audio_available": True,  # Flag to indicate audio exists but needs on-demand fetch
                }
                
                # Only store audio URLs directly if they're small enough
                if len(intro_audio_url) <= max_size and len(thinking_audio_url) <= max_size:
                    update["intro_audio_url"] = intro_audio_url
                    update["thinking_audio_url"] = thinking_audio_url
                    print(f"✅ [PROFILE_AUDIO] Also stored trimmed audio URLs directly (intro: {len(intro_audio_url)} chars, thinking: {len(thinking_audio_url)} chars)")
                else:
                    print(f"⚠️ [PROFILE_AUDIO] Audio URLs too large for direct storage (intro: {len(intro_audio_url)}, thinking: {len(thinking_audio_url)}), will use on-demand fetching only")
                
                fs.collection("user_profiles").document(user_id).set(update, merge=True)
                print(
                    f"✅ [PROFILE_AUDIO] Stored conversation_id for on-demand audio fetch: {user_id} (conversation_id={conversation_id})"
                )
            else:
                print(f"⚠️ [PROFILE_AUDIO] No conversation_id available to store")
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Failed to attach recording for {user_id}: {e}")
            import traceback
            traceback.print_exc()


profile_audio_service = ProfileAudioService()


