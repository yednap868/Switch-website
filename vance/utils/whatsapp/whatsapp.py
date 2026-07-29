import asyncio
import os
import time
from typing import Any

import aiohttp
import requests


class WhatsAppSender:
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    BASE_URL = "https://graph.facebook.com/v16.0"
    URL = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('META_SYS_USER_TOKEN')}",
    }

    media_headers = {
        "Authorization": f"Bearer {os.getenv('META_SYS_USER_TOKEN')}",
    }

    @classmethod
    def send(cls, data: dict[str, Any], tries: int = 1):
        """
        Sends a message to a WhatsApp user
        Args:
        data[dict]: The text message to send, dict object costructed
        according to API specs.

        Returns: dict with 'status' and either 'message_id' (success) or 'error' (failure)
        """
        print(
            f"📤 [WHATSAPP] Sending message to {data.get('to', 'unknown')}: {data.get('text', {}).get('body', '')[:100]}..."
        )

        try:
            # Debug: print request URL and token presence
            try:
                token = os.getenv("META_SYS_USER_TOKEN")
                print(
                    f"🔗 [WHATSAPP] URL: {cls.URL} | PHONE_NUMBER_ID={cls.PHONE_NUMBER_ID}"
                )
                print(f"🔐 [WHATSAPP] Token set: {'yes' if token else 'no'}")
            except Exception:
                pass

            # Debug: print template components if present
            try:
                if data.get("type") == "template":
                    tmpl = data.get("template", {})
                    comps = tmpl.get("components", [])
                    print(f"🧩 [WHATSAPP] Template components: {comps}")
            except Exception:
                pass

            res = requests.post(
                cls.URL,
                headers=cls.headers,
                json=data,
                timeout=30,
            )

            print(f"📤 [WHATSAPP] API Response: {res.status_code}")

            # Parse the response
            response_data = None
            try:
                response_data = res.json()
                print(f"📤 [WHATSAPP] Response body: {response_data}")
            except Exception as e:
                print(f"❌ [WHATSAPP] Failed to parse JSON response: {e}")
                return {
                    "status": "error",
                    "error": f"Invalid JSON response: {res.text}",
                }

            if res.status_code == 200:
                # Check if there are messages (success) or errors (failure)
                if "messages" in response_data and len(response_data["messages"]) > 0:
                    message_id = response_data["messages"][0].get("id")
                    print(f"✅ [WHATSAPP] Message sent successfully, ID: {message_id}")
                    return {"status": "success", "message_id": message_id}
                elif "errors" in response_data and len(response_data["errors"]) > 0:
                    error = response_data["errors"][0]
                    error_msg = error.get("message", "Unknown error")
                    error_code = error.get("code", "Unknown code")
                    print(
                        f"❌ [WHATSAPP] API validation error: {error_code} - {error_msg}"
                    )
                    return {
                        "status": "error",
                        "error": f"WhatsApp API error {error_code}: {error_msg}",
                    }
                else:
                    print(f"⚠️ [WHATSAPP] Unexpected response format: {response_data}")
                    return {
                        "status": "error",
                        "error": f"Unexpected response format: {response_data}",
                    }
            else:
                error_msg = response_data.get("error", {}).get("message", res.text)
                print(f"❌ [WHATSAPP] HTTP error {res.status_code}: {error_msg}")
                return {
                    "status": "error",
                    "error": f"HTTP {res.status_code}: {error_msg}",
                }

        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"❌ [WHATSAPP] {error_msg}")
            return {"status": "error", "error": error_msg}

    @classmethod
    def __get_media_url(cls, media_id: str, tries: int = 1):
        """
        Sends a message to a WhatsApp user
        Args:
        data[dict]: The text message to send, dict object costructed
        according to API specs.
        """
        res = requests.get(
            f"{cls.BASE_URL}/{media_id}?phone_number_id={cls.PHONE_NUMBER_ID}",
            headers=cls.headers,
            timeout=30,
        )

        if (res.status_code != 200) and (tries <= 3):
            time.sleep(2)
            cls.__get_media_url(media_id, tries=tries + 1)

        return res.json()["url"]

    @classmethod
    def get_audio(cls, media_id: str, tries: int = 1):
        url = cls.__get_media_url(media_id)
        # response = requests.get(url, headers=cls.alt_headers, timeout=5)
        response = requests.get(
            url,
            headers=cls.headers,
            timeout=30,
        )

        if response.status_code != 200:
            print(response.json())

        if (response.status_code != 200) and (tries <= 3):
            time.sleep(2)
            cls.get_audio(media_id, tries=tries + 1)

        return response.content

    @classmethod
    def send_with_human_behavior(cls, data: dict, behavior_config: dict):
        """Send message - simplified without artificial delays"""
        # Simplified behavior - no artificial delays or complex logic
        # Just send the message directly
        return cls.send(data)

    @classmethod
    def _send_typing_indicator(cls, to: str, duration: float):
        """Send typing indicator to user."""
        try:
            typing_data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "typing",
                "typing": {"action": "typing"},
            }

            # Send typing indicator
            requests.post(cls.URL, headers=cls.headers, json=typing_data, timeout=15)

            # Wait for the duration
            time.sleep(duration)

            # Stop typing indicator
            typing_data["typing"]["action"] = "stop"
            requests.post(cls.URL, headers=cls.headers, json=typing_data, timeout=15)

        except Exception as e:
            print(f"Error sending typing indicator: {e}")

    @classmethod
    def send_typing_indicator(cls, to: str, duration: int = 2):
        """Send typing indicator to user - DEPRECATED: Use send_typing_indicator_with_message_id instead"""
        print(
            f"⚠️ [TYPING] send_typing_indicator is deprecated - use send_typing_indicator_with_message_id with message_id"
        )
        # This method is deprecated - typing indicators require message_id
        time.sleep(min(duration, 2))

    @classmethod
    def send_typing_indicator_with_message_id(cls, message_id: str, duration: int = 1):
        """Send typing indicator using message_id as per WhatsApp Cloud API docs"""
        try:
            typing_data = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {"type": "text"},
            }

            print(f"⌨️ [TYPING] Sending typing indicator for message {message_id}")

            response = requests.post(
                cls.URL,
                headers=cls.headers,
                json=typing_data,
                timeout=10,  # Reduced timeout
            )

            if response.status_code == 200:
                print(f"⌨️ [TYPING] Typing indicator sent successfully")
                # Minimal delay - just enough to show typing
                time.sleep(min(duration, 0.5))  # Max 0.5 seconds
            else:
                print(
                    f"❌ [TYPING] Failed to send typing indicator: {response.status_code} - {response.text}"
                )

        except Exception as e:
            print(f"❌ [TYPING] Error sending typing indicator: {e}")

    @classmethod
    def mark_message_as_read(cls, message_id: str):
        """Mark a message as read to show read receipt."""
        try:
            read_data = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }

            print(f"👁️ [READ] Marking message {message_id} as read")

            response = requests.post(
                cls.URL, headers=cls.headers, json=read_data, timeout=15
            )

            if response.status_code == 200:
                print(f"👁️ [READ] Message marked as read successfully")
            else:
                print(
                    f"❌ [READ] Failed to mark message as read: {response.status_code} - {response.text}"
                )

            return response

        except Exception as e:
            print(f"❌ [READ] Error marking message as read: {e}")
            return None

    @classmethod
    def send_reaction(cls, to: str, message_id: str, emoji: str):
        """
        Send a reaction to a message.
        """
        reaction_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }
        return cls.send(reaction_data)

    @classmethod
    def upload_media(cls, image_bytes: bytes, mime_type: str = "image/png"):
        """
        Upload media to WhatsApp and get media ID.

        Args:
            image_bytes: Image content as bytes
            mime_type: MIME type of the media

        Returns:
            Media ID if successful, None otherwise
        """
        try:
            upload_url = f"{cls.BASE_URL}/{cls.PHONE_NUMBER_ID}/media"

            files = {
                'file': ('profile_card.png', image_bytes, mime_type),
            }
            data = {
                'messaging_product': 'whatsapp',
                'type': mime_type,
            }

            response = requests.post(
                upload_url,
                headers=cls.media_headers,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                media_id = result.get('id')
                print(f"✅ [WHATSAPP] Media uploaded successfully, ID: {media_id}")
                return media_id
            else:
                print(f"❌ [WHATSAPP] Failed to upload media: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ [WHATSAPP] Error uploading media: {e}")
            return None

    @classmethod
    def send_image(cls, to: str, image_bytes: bytes, caption: str = "") -> dict:
        """
        Send an image to a WhatsApp user.

        Args:
            to: Recipient phone number
            image_bytes: Image content as bytes
            caption: Optional caption for the image

        Returns:
            Response dict with status
        """
        # First upload the media
        media_id = cls.upload_media(image_bytes)
        if not media_id:
            return {"status": "error", "error": "Failed to upload media"}

        # Send the image message
        image_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "id": media_id,
            }
        }

        if caption:
            image_data["image"]["caption"] = caption

        print(f"📷 [WHATSAPP] Sending image to {to} with caption: {caption[:50]}...")
        return cls.send(image_data)

    @classmethod
    def send_image_from_url(cls, to: str, image_url: str, caption: str = "") -> dict:
        """
        Send an image from a URL to a WhatsApp user.

        Args:
            to: Recipient phone number
            image_url: Public URL of the image
            caption: Optional caption for the image

        Returns:
            Response dict with status
        """
        image_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url,
            }
        }

        if caption:
            image_data["image"]["caption"] = caption

        print(f"📷 [WHATSAPP] Sending image from URL to {to}")
        return cls.send(image_data)


class WhatsAppSenderAsync:
    PHONE_NUMBER_ID = ""
    BASE_URL = "https://graph.facebook.com/v16.0"
    URL = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('META_SYS_USER_TOKEN')}",
    }

    media_headers = {
        "Authorization": f"Bearer {os.getenv('META_SYS_USER_TOKEN')}",
    }

    @classmethod
    async def send(cls, data: dict[str, Any], tries: int = 1):
        """
        Sends a message to a WhatsApp user
        Args:
        data[dict]: The text message to send, dict object costructed
        according to API specs.
        """
        params = {
            "url": cls.URL,
            "headers": cls.headers,
            "json": data,
            "timeout": 30,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(**params) as res:
                if res.status == 200:
                    return await res.json()

                if tries > 3:
                    return

                await asyncio.sleep(2)
                await cls.send(data, tries=tries + 1)

    @classmethod
    async def __get_media_url(cls, media_id: str, tries: int = 1):
        """
        Sends a message to a WhatsApp user
        Args:
        data[dict]: The text message to send, dict object costructed
        according to API specs.
        """
        params = {
            "url": f"{cls.BASE_URL}/{media_id}?phone_number_id={cls.PHONE_NUMBER_ID}",
            "headers": cls.headers,
            "timeout": 30,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(**params) as res:
                if res.status == 200:
                    return (await res.json())["url"]

                if tries > 3:
                    return

                await asyncio.sleep(2)
                await cls.__get_media_url(media_id, tries=tries + 1)

    @classmethod
    async def get_audio(cls, media_id: str, tries: int = 1):
        url = await cls.__get_media_url(media_id)

        params = {
            "url": url,
            "headers": cls.headers,
            "timeout": 30,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(**params) as res:
                if res.status == 200:
                    return res.content

                if tries > 3:
                    return

                await asyncio.sleep(2)
                await cls.get_audio(media_id, tries=tries + 1)

    @classmethod
    async def send_with_human_behavior(cls, data: dict[str, Any], behavior_config=None):
        """
        Send message with human-like behaviors (typing indicator, delays) - async version.
        """
        # Simplified behavior - no artificial delays or complex logic
        # Just send the message directly
        return await cls.send(data)

    @classmethod
    async def _send_typing_indicator_async(cls, to: str, duration: float):
        """Send typing indicator to user - async version."""
        try:
            typing_data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "typing",
                "typing": {"action": "typing"},
            }

            # Send typing indicator
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    cls.URL, headers=cls.headers, json=typing_data, timeout=15
                ) as response:
                    if response.status == 200:
                        # Wait for the duration
                        await asyncio.sleep(duration)

                        # Stop typing indicator
                        typing_data["typing"]["action"] = "stop"
                        async with session.post(
                            cls.URL, headers=cls.headers, json=typing_data, timeout=15
                        ) as stop_response:
                            pass

        except Exception as e:
            print(f"Error sending typing indicator: {e}")

    @classmethod
    async def send_reaction(cls, to: str, message_id: str, emoji: str):
        """
        Send a reaction to a message - async version.
        """
        reaction_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }
        return await cls.send(reaction_data)
