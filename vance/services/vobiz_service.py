"""
Service for Vobiz.ai telephony integration.
Handles phone number provisioning, SIP trunk management, and call API.

Vobiz provides the telephony layer (phone numbers, SIP trunks) while
ElevenLabs provides the AI voice agent. Incoming calls flow:
  Caller → Vobiz number → answer_url webhook → <Stream> → WebSocket bridge → ElevenLabs Conversation API
"""

import os
from typing import Optional

import httpx


VOBIZ_API_BASE = "https://api.vobiz.ai/api/v1"

# ElevenLabs SIP URI for forwarding incoming calls
ELEVENLABS_SIP_URI = "sip.rtc.elevenlabs.io"
ELEVENLABS_SIP_PORT = 5060
ELEVENLABS_SIP_TRANSPORT = "tcp"


class VobizService:
    """Manages Vobiz.ai telephony resources and call routing."""

    def __init__(self):
        self.auth_id = os.getenv("VOBIZ_AUTH_ID", "").strip()
        self.auth_token = os.getenv("VOBIZ_AUTH_TOKEN", "").strip()
        self.account_id = os.getenv("VOBIZ_ACCOUNT_ID", "").strip()
        self.phone_number = os.getenv("VOBIZ_PHONE_NUMBER", "").strip()
        print(f"📞 [VOBIZ] Init: auth_id={self.auth_id} token_len={len(self.auth_token)} token_start={self.auth_token[:8]}... token_end=...{self.auth_token[-8:]} phone={self.phone_number}")

    @property
    def _headers(self) -> dict:
        return {
            "X-Auth-ID": self.auth_id,
            "X-Auth-Token": self.auth_token,
            "Content-Type": "application/json",
        }

    @property
    def _base_url(self) -> str:
        return f"{VOBIZ_API_BASE}/Account/{self.auth_id}"

    @property
    def is_configured(self) -> bool:
        return bool(self.auth_id and self.auth_token and self.account_id)

    async def list_phone_numbers(self) -> dict:
        """List all phone numbers on the account."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/numbers",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_phone_number(self, number_id: str) -> dict:
        """Get details of a specific phone number."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/numbers/{number_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_sip_trunks(self) -> dict:
        """List all SIP trunks on the account."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/trunks",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_sip_trunk(self, name: str, origination_url: Optional[str] = None) -> dict:
        """
        Create a SIP trunk that forwards calls to ElevenLabs.

        Args:
            name: Trunk name (e.g. "elevenlabs-jyoti")
            origination_url: SIP origination URL. Defaults to ElevenLabs SIP URI.
        """
        if origination_url is None:
            origination_url = (
                f"sip:{ELEVENLABS_SIP_URI}:{ELEVENLABS_SIP_PORT}"
                f";transport={ELEVENLABS_SIP_TRANSPORT}"
            )

        payload = {
            "name": name,
            "origination_url": origination_url,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/trunks",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def make_call(
        self,
        to_number: str,
        answer_url: str,
        hangup_url: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> dict:
        """
        Initiate an outbound call via Vobiz.

        Args:
            to_number: Destination phone number (E.164)
            answer_url: URL Vobiz hits when the call is answered
            hangup_url: URL Vobiz hits when the call ends
            from_number: Caller ID (defaults to configured phone number)
        """
        caller_id = from_number or self.phone_number
        if not caller_id:
            print("⚠️ [VOBIZ_API] No from_number set! Callee sees Vobiz account default number. Set VOBIZ_PHONE_NUMBER env var.")
        # Normalize to E.164 digits WITHOUT + prefix (Vobiz expects e.g. "919876543210")
        if caller_id:
            digits = caller_id.replace("+", "").replace("-", "").replace(" ", "")
            if not digits.startswith("91"):
                digits = "91" + digits
            caller_id = digits

        # Normalize to_number the same way (strip + prefix, ensure 91 prefix)
        to_digits = to_number.replace("+", "").replace("-", "").replace(" ", "")
        if not to_digits.startswith("91") and len(to_digits) == 10:
            to_digits = "91" + to_digits

        payload = {
            "from": caller_id,
            "to": to_digits,
            "answer_url": answer_url,
            "answer_method": "POST",
        }
        if hangup_url:
            payload["hangup_url"] = hangup_url
            payload["hangup_method"] = "POST"

        url = f"{self._base_url}/Call/"
        print(f"📞 [VOBIZ_API] POST {url} payload={payload}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json=payload,
            )
            print(f"📞 [VOBIZ_API] Response {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()

    async def hangup_call(self, call_uuid: str) -> dict:
        """Hang up an active call by its UUID."""
        url = f"{self._base_url}/Call/{call_uuid}/"
        print(f"📞 [VOBIZ_API] DELETE {url} (hangup)")
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self._headers)
            print(f"📞 [VOBIZ_API] Hangup response {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json()

    async def transfer_call(self, call_uuid: str, aleg_url: str) -> dict:
        """Transfer a live call to a new answer URL (fetches new XML)."""
        url = f"{self._base_url}/Call/{call_uuid}/"
        payload = {
            "legs": "aleg",
            "aleg_url": aleg_url,
            "aleg_method": "POST",
        }
        print(f"📞 [VOBIZ_API] POST {url} (transfer) payload={payload}")
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers, json=payload)
            print(f"📞 [VOBIZ_API] Transfer response {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()

    def build_conference_xml(self, room_name: str, intro_text: str = "", callback_url: str = "", wait_sound: bool = False) -> str:
        """Build Vobiz XML to join a conference room for direct bridge."""
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n']
        if intro_text:
            xml_parts.append(
                f'  <Speak voice="WOMAN" language="hi-IN">{intro_text}</Speak>\n'
            )
        record_attrs = ' record="true" recordFileFormat="mp3"'
        if callback_url:
            safe_url = callback_url.replace('&', '&amp;')
            record_attrs += f' action="{safe_url}" method="POST"'
        wait_attr = ' waitSound="true"' if wait_sound else ''
        xml_parts.append(
            f'  <Conference startConferenceOnEnter="true"'
            f' endConferenceOnExit="true"'
            f'{wait_attr}'
            f'{record_attrs}>'
            f'{room_name}'
            f'</Conference>\n'
        )
        xml_parts.append('</Response>')
        return ''.join(xml_parts)

    def build_dial_number_xml(self, caller_number: str) -> str:
        """
        Build Vobiz XML response to forward an incoming call to the
        ElevenLabs agent by dialing the ElevenLabs Indian phone number
        as a regular PSTN call.

        Flow: Caller → Vobiz → Dial ElevenLabs number → Jyoti answers

        Args:
            caller_number: The caller's phone number (for logging).
        """
        elevenlabs_number = os.getenv("ELEVENLABS_INDIAN_NUMBER", "+918037565248")
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            "  <Dial>\n"
            f"    <Number>{elevenlabs_number}</Number>\n"
            "  </Dial>\n"
            "</Response>"
        )
        return xml

    def build_bridge_stream_xml(self, caller_phone: str = "") -> str:
        """
        Build Vobiz XML that opens a bidirectional audio stream to our
        WebSocket bridge, which relays audio to/from ElevenLabs.

        Flow: Caller → Vobiz → <Stream> WebSocket → Bridge → ElevenLabs Conversation API

        The bridge handles audio format conversion (mulaw 8kHz ↔ PCM 16kHz)
        and relays bidirectionally so the ElevenLabs agent can converse with
        the caller in real time.
        """
        server_host = os.getenv("SERVER_HOST", "api.relayy.world")
        ws_url = f"wss://{server_host}/ws/vobiz-bridge"
        if caller_phone:
            ws_url += f"?caller_phone={caller_phone}"

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Stream bidirectional="true" keepCallAlive="true"'
            f' contentType="audio/x-mulaw;rate=8000"'
            f' streamTimeout="86400">'
            f"{ws_url}"
            f"</Stream>\n"
            "</Response>"
        )
        return xml

    def build_custom_stream_xml(self, ws_path: str, query_params: str = "", speak_first: str = "") -> str:
        """
        Build Vobiz XML that opens a bidirectional audio stream to a custom
        WebSocket path on our server. Used for live connect bridges.

        Args:
            ws_path: WebSocket path (e.g. "/ws/live-connect/candidate")
            query_params: Optional query string (e.g. "session_id=abc123")
            speak_first: Optional text to speak before opening the stream
                         (prevents silence while ElevenLabs initializes)
        """
        server_host = os.getenv("SERVER_HOST", "api.relayy.world")
        ws_url = f"wss://{server_host}{ws_path}"
        if query_params:
            ws_url += f"?{query_params}"

        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            "<Response>\n",
        ]
        if speak_first:
            xml_parts.append(
                f'  <Speak voice="WOMAN" language="hi-IN">{speak_first}</Speak>\n'
            )
        xml_parts.append(
            f'  <Stream bidirectional="true" keepCallAlive="true"'
            f' contentType="audio/x-mulaw;rate=8000"'
            f' streamTimeout="86400">'
            f"{ws_url.replace('&', '&amp;')}"
            f"</Stream>\n"
        )
        xml_parts.append("</Response>")
        return "".join(xml_parts)

    def build_sip_dial_xml(self) -> str:
        """
        Build Vobiz XML to forward an incoming call to ElevenLabs via SIP.

        Uses the ElevenLabs Indian SIP trunk number (+918037565248) which
        is registered directly in ElevenLabs with the Switch agent.

        Flow: Caller → Vobiz → SIP dial → ElevenLabs → Jyoti
        """
        el_number = os.getenv("ELEVENLABS_SIP_PHONE_NUMBER", "+918037565248")
        sip_uri = (
            f"sip:{el_number}@{ELEVENLABS_SIP_URI}"
            f":{ELEVENLABS_SIP_PORT};transport={ELEVENLABS_SIP_TRANSPORT}"
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            "  <Dial>\n"
            f"    <User>{sip_uri}</User>\n"
            "  </Dial>\n"
            "</Response>"
        )
        return xml


vobiz_service = VobizService()
