"""
Compensation insight service.

After a compensation-focused call, we want to:
- Use Claude to infer: compensation band, signals helping, what's holding back, and fixes
- Render this into a beautiful PNG card matching the vance-comp-card React component exactly
"""

from __future__ import annotations

import io
import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont

from utils.db import get_extraction_data, get_user_profile


@dataclass
class CompensationInsights:
    """Structured result from Claude for compensation feedback."""

    compensation_band: str
    helping_signals: List[str]
    holding_back: List[str]
    fixes: List[str]


class CompensationInsightService:
    """Service to generate compensation insights and render them as images."""

    def __init__(self) -> None:
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Use same model family as other Claude calls
        self.model = "claude-3-7-sonnet-20250219"

    # ------------------------------------------------------------------
    # Claude analysis
    # ------------------------------------------------------------------
    def _build_context_text(self, uid: str) -> str:
        """Build a text context from extraction data + basic profile."""
        extraction = get_extraction_data(uid) or {}
        profile = get_user_profile(uid) or {}

        parts: List[str] = []

        name = profile.get("name") or extraction.get("name")
        if name:
            parts.append(f"name: {name}")

        # Core fields that matter for compensation
        for key in [
            "target_role",
            "current_role",
            "current_company",
            "current_location",
            "work_experience",
            "core_skills",
            "tech_stack",
            "education",
            "industry_background",
            "job_search_urgency",
            "achievements",
            "projects",
        ]:
            val = extraction.get(key)
            if not val:
                continue
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            parts.append(f"{key}: {val}")

        # Fallback: include raw extraction if nothing else
        if not parts and extraction:
            for k, v in extraction.items():
                if v:
                    parts.append(f"{k}: {v}")

        return "\n".join(parts) if parts else "No structured data available."

    def _call_claude_for_insights(self, uid: str) -> CompensationInsights:
        """Call Claude to get compensation insights for this user."""
        context_text = self._build_context_text(uid)

        prompt = f"""
You are helping a candidate understand how founders would price their profile *today*.

Based on the structured data from their onboarding/voice call, estimate:
- A realistic compensation band founders would place them in today
- The signals that are *helping* their profile
- What's *holding it back*
- Concrete, practical suggestions to fix the weak points

User data:
{context_text}

Return a compact JSON object with this exact shape:
{{
  "compensation_band": "short human-readable band, e.g. '₹28–35L fixed + ESOPs' or '$160k–190k base + equity'",
  "helping_signals": [
    "short bullet 1",
    "short bullet 2",
    "short bullet 3"
  ],
  "holding_back": [
    "short bullet 1",
    "short bullet 2"
  ],
  "fixes": [
    "short, practical action 1",
    "short, practical action 2",
    "short, practical action 3"
  ]
}}

Rules:
- Be specific and realistic for *today's* early-stage founder market.
- Prefer concise, founder-style phrasing (no fluff).
- If data is thin, make conservative, reasonable assumptions and say so in the phrasing.
- Do NOT mention that you are guessing or that data is limited; just reflect that in how confident/hedged the language is.
Return ONLY the JSON, no extra text.
"""

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = resp.content[0].text.strip()

        # Extract JSON block if Claude wraps it
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start != -1 and json_end != -1:
            raw = raw[json_start:json_end]

        import json

        try:
            data = json.loads(raw)
        except Exception:
            # Fallback: very conservative defaults
            return CompensationInsights(
                compensation_band="Compensation band not clear from the call.",
                helping_signals=["Strong signals not clearly captured in the call."],
                holding_back=["Missing detail on experience or impact."],
                fixes=[
                    "Clarify your recent work and impact in concrete terms.",
                    "Tighten your LinkedIn/profile to match the roles you want.",
                ],
            )

        def _as_list(val: Any) -> List[str]:
            if not val:
                return []
            if isinstance(val, list):
                return [str(v) for v in val if str(v).strip()]
            return [str(val)]

        return CompensationInsights(
            compensation_band=str(data.get("compensation_band", "") or "").strip()
            or "Compensation band not clear from the call.",
            helping_signals=_as_list(data.get("helping_signals")),
            holding_back=_as_list(data.get("holding_back")),
            fixes=_as_list(data.get("fixes")),
        )

    def get_insights(self, uid: str) -> CompensationInsights:
        """Public entrypoint: get (or compute) insights for a user."""
        # For now, compute on demand. Could be cached in Firestore later.
        return self._call_claude_for_insights(uid)

    # ------------------------------------------------------------------
    # Image rendering - Matching vance-comp-card React component exactly
    # ------------------------------------------------------------------
    def _load_font(self, size: int, weight: str = "normal") -> ImageFont.FreeTypeFont:
        """Load a font with specified size and weight."""
        try:
            # Try system fonts
            if weight == "semibold" or weight == "bold":
                font_paths = [
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                ]
            else:
                font_paths = [
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/Arial.ttf",
                ]
            
            for font_path in font_paths:
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def _hsl_to_rgb(self, h: float, s: float, l: float) -> tuple:
        """Convert HSL to RGB (0-255)."""
        import colorsys
        r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
        return (int(r * 255), int(g * 255), int(b * 255))

    def render_card_png(self, uid: str, insights: CompensationInsights) -> bytes:
        """
        Render card optimized for mobile-first (Hinge-style dimensions).
        Designed for clear readability on mobile devices.
        """
        try:
            print(f"🎨 [COMP_CARD] Starting image render for uid={uid}")
            
            # Mobile-first dimensions (Hinge-style: 1080x1920 portrait)
            # Render at high resolution for clarity
            card_width = 1080
            card_height = 1920
            padding = 60  # Generous padding for mobile
            
            # Colors from CSS variables (HSL to RGB)
            # --background: 0 0% 0% = black
            # --card: 0 0% 6% = very dark gray
            # --primary: 142 71% 45% = green
            # --info: 217 91% 60% = blue
            # --warning: 38 92% 50% = amber
            # --foreground: 0 0% 100% = white
            # --muted-foreground: 0 0% 60% = gray
            # --border: 0 0% 18% = dark gray
            # --secondary: 0 0% 12% = dark gray
            
            bg_color = (0, 0, 0)  # --background
            card_bg = self._hsl_to_rgb(0, 0, 6)  # --card
            primary = self._hsl_to_rgb(142, 71, 45)  # --primary (green)
            info = self._hsl_to_rgb(217, 91, 60)  # --info (blue)
            warning = self._hsl_to_rgb(38, 92, 50)  # --warning (amber)
            foreground = (255, 255, 255)  # --foreground
            muted_foreground = self._hsl_to_rgb(0, 0, 60)  # --muted-foreground
            border_color = self._hsl_to_rgb(0, 0, 18)  # --border
            secondary = self._hsl_to_rgb(0, 0, 12)  # --secondary
            
            # Create image with black background
            img = Image.new("RGB", (card_width, card_height), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            # Load fonts optimized for mobile readability (much larger)
            # Mobile-first: larger fonts for readability
            small_font = self._load_font(28)  # Footer text
            body_font = self._load_font(42)  # Body text (readable on mobile)
            title_font = self._load_font(52)  # Compensation band
            header_font = self._load_font(56)  # Main title
            semibold_small = self._load_font(36, "semibold")  # Section headers
            semibold_body = self._load_font(32, "semibold")  # VANCE label
            
            # Card container - full width with padding
            card_inner_width = card_width - 2 * padding
            card_x = padding
            card_y = padding
            card_inner_height = card_height - 2 * padding
            
            # Draw card background with rounded corners (mobile-friendly)
            draw.rounded_rectangle(
                [card_x, card_y, card_x + card_inner_width, card_y + card_inner_height],
                radius=32,  # Larger radius for mobile
                fill=card_bg,
                outline=tuple(int(c * 0.5) for c in border_color),
                width=2,
            )
            
            # Gradient overlay (subtle, from-primary/5 to-info/5)
            # We'll simulate this with a subtle overlay
            overlay = Image.new("RGBA", (card_inner_width, card_inner_height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            # Simple gradient simulation
            for i in range(card_inner_height):
                alpha = int(5 * (1 - abs(i - card_inner_height/2) / (card_inner_height/2)))
                if alpha > 0:
                    overlay_draw.rectangle(
                        [0, i, card_inner_width, i + 1],
                        fill=(primary[0], primary[1], primary[2], alpha),
                    )
            img.paste(overlay, (card_x, card_y), overlay)
            draw = ImageDraw.Draw(img)  # Recreate draw after paste
            
            # Current Y position
            y = card_y + 80  # Top padding
            
            # Header section
            header_x = card_x + 40  # Left padding
            
            # Sparkles icon + "VANCE" text
            sparkles_size = 48  # Larger for mobile
            sparkles_x = header_x
            sparkles_y = y
            self._draw_sparkles_icon(draw, sparkles_x + sparkles_size//2, sparkles_y + sparkles_size//2, sparkles_size, primary)
            
            # "VANCE" text
            vance_x = sparkles_x + sparkles_size + 16
            bbox = draw.textbbox((0, 0), "VANCE", font=semibold_body)
            vance_h = bbox[3] - bbox[1]
            draw.text((vance_x, sparkles_y), "VANCE", font=semibold_body, fill=primary)
            
            y += sparkles_size + 32  # Spacing
            
            # "Compensation Analysis" title
            bbox = draw.textbbox((0, 0), "Compensation Analysis", font=header_font)
            draw.text((header_x, y), "Compensation Analysis", font=header_font, fill=foreground)
            y += bbox[3] - bbox[1] + 40
            
            # Border bottom
            border_y = y
            draw.line(
                [header_x, border_y, card_x + card_inner_width - 40, border_y],
                fill=tuple(int(c * 0.3) for c in border_color),
                width=2,
            )
            y = border_y + 50
            
            # Compensation Band Pill (px-6 py-5)
            band_text = insights.compensation_band
            bbox = draw.textbbox((0, 0), band_text, font=title_font)
            band_w = bbox[2] - bbox[0]
            band_h = bbox[3] - bbox[1]
            
            # Pill: larger for mobile
            pill_padding_x = 40
            pill_padding_y = 24
            pill_w = band_w + 2 * pill_padding_x
            pill_h = band_h + 2 * pill_padding_y
            pill_x = header_x
            pill_y = y
            
            # Pill background
            pill_bg = (int(info[0] * 0.15), int(info[1] * 0.15), int(info[2] * 0.15))
            pill_border = (int(info[0] * 0.3), int(info[1] * 0.3), int(info[2] * 0.3))
            
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                radius=pill_h // 2,
                fill=pill_bg,
                outline=pill_border,
                width=2,
            )
            
            # Band text
            draw.text(
                (pill_x + pill_padding_x, pill_y + pill_padding_y),
                band_text,
                font=title_font,
                fill=info,
            )
            y = pill_y + pill_h + 50
            
            # Helping Signals Section (px-6 pb-5)
            signals_x = header_x
            
            # Header: CheckCircle icon + "HELPING SIGNALS"
            check_size = 40  # Larger for mobile
            self._draw_check_circle_icon(draw, signals_x + check_size//2, y + check_size//2, check_size, primary)
            
            header_text = "HELPING SIGNALS"
            bbox = draw.textbbox((0, 0), header_text, font=semibold_small)
            header_h = bbox[3] - bbox[1]
            draw.text(
                (signals_x + check_size + 16, y),
                header_text,
                font=semibold_small,
                fill=primary,
            )
            y += max(check_size, header_h) + 30
            
            # Signal items - larger spacing for mobile
            helping = insights.helping_signals or []
            for signal in helping[:4]:  # Max 4 items
                # Bullet: larger for mobile
                bullet_radius = 8
                bullet_x = signals_x
                bullet_y = y + 20
                draw.ellipse(
                    [
                        bullet_x - bullet_radius,
                        bullet_y - bullet_radius,
                        bullet_x + bullet_radius,
                        bullet_y + bullet_radius,
                    ],
                    fill=primary,
                )
                
                # Text: larger font for mobile readability
                text_x = signals_x + 30
                draw.text((text_x, y), signal, font=body_font, fill=tuple(int(c * 0.9) for c in foreground))
                
                bbox = draw.textbbox((0, 0), signal, font=body_font)
                y += max(bbox[3] - bbox[1], 50) + 20
            
            y += 20
            
            # Divider
            divider_y = y
            draw.line(
                [signals_x, divider_y, card_x + card_inner_width - 40, divider_y],
                fill=tuple(int(c * 0.5) for c in border_color),
                width=2,
            )
            y = divider_y + 50
            
            # Holding Back & Fixes Section
            holding_x = header_x
            
            # Header: AlertCircle icon + "HOLDING BACK & FIXES"
            alert_size = 40
            self._draw_alert_circle_icon(draw, holding_x + alert_size//2, y + alert_size//2, alert_size, warning)
            
            header_text = "HOLDING BACK & FIXES"
            bbox = draw.textbbox((0, 0), header_text, font=semibold_small)
            header_h = bbox[3] - bbox[1]
            draw.text(
                (holding_x + alert_size + 16, y),
                header_text,
                font=semibold_small,
                fill=warning,
            )
            y += max(alert_size, header_h) + 30
            
            # Combine holding_back and fixes
            combined_items = insights.holding_back.copy()
            if insights.fixes:
                combined_items.extend(insights.fixes)
            
            if not combined_items:
                combined_items = ["No specific issues identified."]
            
            # Items - larger spacing for mobile
            for item in combined_items[:4]:  # Max 4 items
                # Bullet: larger for mobile
                bullet_radius = 8
                bullet_x = holding_x
                bullet_y = y + 20
                draw.ellipse(
                    [
                        bullet_x - bullet_radius,
                        bullet_y - bullet_radius,
                        bullet_x + bullet_radius,
                        bullet_y + bullet_radius,
                    ],
                    fill=warning,
                )
                
                # Text: larger font for mobile readability
                text_x = holding_x + 30
                draw.text((text_x, y), item, font=body_font, fill=tuple(int(c * 0.9) for c in foreground))
                
                bbox = draw.textbbox((0, 0), item, font=body_font)
                y += max(bbox[3] - bbox[1], 50) + 20
            
            # Footer
            footer_padding_y = 40
            footer_y = y
            footer_bg = (int(secondary[0] * 0.3), int(secondary[1] * 0.3), int(secondary[2] * 0.3))
            
            # Footer background
            footer_height = footer_padding_y * 2 + 60
            draw.rectangle(
                [card_x, footer_y, card_x + card_inner_width, footer_y + footer_height],
                fill=footer_bg,
            )
            
            # Border top
            draw.line(
                [card_x, footer_y, card_x + card_inner_width, footer_y],
                fill=tuple(int(c * 0.3) for c in border_color),
                width=2,
            )
            
            # Footer content: Sparkles icon + text
            footer_text = "Generated by Vance from your call"
            footer_sparkles_size = 32
            footer_content_y = footer_y + footer_padding_y
            
            # Center the footer content
            bbox_text = draw.textbbox((0, 0), footer_text, font=small_font)
            footer_text_w = bbox_text[2] - bbox_text[0]
            total_footer_width = footer_sparkles_size + 16 + footer_text_w
            footer_start_x = card_x + (card_inner_width - total_footer_width) // 2
            
            footer_sparkles_x = footer_start_x
            self._draw_sparkles_icon(
                draw,
                footer_sparkles_x + footer_sparkles_size//2,
                footer_content_y + footer_sparkles_size//2,
                footer_sparkles_size,
                muted_foreground,
            )
            
            footer_text_x = footer_sparkles_x + footer_sparkles_size + 16
            draw.text(
                (footer_text_x, footer_content_y),
                footer_text,
                font=small_font,
                fill=muted_foreground,
            )
            
            # Crop to actual content height
            actual_height = min(footer_y + footer_height, card_height)
            img = img.crop((0, 0, card_width, actual_height))
            
            # Export to PNG bytes
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
            print(f"✅ [COMP_CARD] Successfully generated {len(png_bytes)} bytes PNG for uid={uid}")
            return png_bytes
        except Exception as e:
            print(f"❌ [COMP_CARD] Error rendering card for uid={uid}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _draw_sparkles_icon(self, draw: ImageDraw.Draw, x: int, y: int, size: int, color: tuple):
        """Draw sparkles icon (4-pointed star with corner points)."""
        import math
        radius = size // 3
        # Main center point
        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=color)
        # 4 corner points
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            draw.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=color)

    def _draw_check_circle_icon(self, draw: ImageDraw.Draw, x: int, y: int, size: int, color: tuple):
        """Draw check circle icon."""
        radius = size // 2
        # Circle outline
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=color, width=2)
        # Check mark
        check_size = radius * 0.6
        draw.line(
            [x - check_size*0.5, y, x - check_size*0.1, y + check_size*0.6],
            fill=color,
            width=2,
        )
        draw.line(
            [x - check_size*0.1, y + check_size*0.6, x + check_size*0.5, y - check_size*0.3],
            fill=color,
            width=2,
        )

    def _draw_alert_circle_icon(self, draw: ImageDraw.Draw, x: int, y: int, size: int, color: tuple):
        """Draw alert circle icon."""
        radius = size // 2
        # Circle outline
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=color, width=2)
        # Exclamation mark
        exclam_height = radius * 0.6
        draw.line([x, y - exclam_height*0.3, x, y + exclam_height*0.3], fill=color, width=2)
        draw.ellipse([x - 2, y + exclam_height*0.4, x + 2, y + exclam_height*0.5], fill=color)


compensation_insight_service = CompensationInsightService()
