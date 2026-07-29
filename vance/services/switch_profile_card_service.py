"""
Switch Profile Card Service - Creates cards matching Switch app business UI.
White card with photo, verified badge, name, experience, role tags, location, language, salary, stats.
"""

import io
import os
import requests
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from services.switch_matching_service import SwitchCandidate


# Card dimensions
CARD_WIDTH = 480
CARD_HEIGHT = 720
PHOTO_HEIGHT = 320
CORNER_RADIUS = 20
PADDING = 24

# Colors matching Switch app
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)
GREY_TEXT = (130, 130, 130)
GREY_LIGHT = (245, 245, 245)
GREY_BORDER = (230, 230, 230)
GREEN = (16, 185, 129)
GREEN_DARK = (5, 150, 105)
GREEN_BG = (220, 252, 231)
GREEN_TEXT = (22, 163, 74)
BLUE_TEXT = (37, 99, 235)
BLUE_BG = (239, 246, 255)
ORANGE_TEXT = (234, 88, 12)
ORANGE_BG = (255, 247, 237)
PLACEHOLDER_BG = (240, 240, 240)
PLACEHOLDER_TEXT = (180, 180, 180)


class SwitchProfileCardService:
    """Service for generating Switch-style profile cards."""

    def __init__(self):
        self.fonts = {}
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts with multiple sizes."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]

        bold_path = None
        regular_path = None

        for path in font_paths:
            if os.path.exists(path):
                if "Bold" in path and not bold_path:
                    bold_path = path
                elif not regular_path:
                    regular_path = path

        try:
            if bold_path:
                self.fonts["name"] = ImageFont.truetype(bold_path, 26)
                self.fonts["stat_num"] = ImageFont.truetype(bold_path, 22)
                self.fonts["badge"] = ImageFont.truetype(bold_path, 13)
                self.fonts["avail_badge"] = ImageFont.truetype(bold_path, 14)
            if regular_path:
                self.fonts["experience"] = ImageFont.truetype(regular_path, 16)
                self.fonts["role_tag"] = ImageFont.truetype(regular_path, 14)
                self.fonts["info"] = ImageFont.truetype(regular_path, 15)
                self.fonts["stat_label"] = ImageFont.truetype(regular_path, 12)
                self.fonts["small"] = ImageFont.truetype(regular_path, 12)
        except Exception as e:
            print(f"[CARD] Font error: {e}")
            default = ImageFont.load_default()
            for k in ["name", "stat_num", "badge", "avail_badge", "experience", "role_tag", "info", "stat_label", "small"]:
                self.fonts[k] = default

    def _load_profile_photo(self, photo_url: str) -> Optional[Image.Image]:
        """Download profile photo."""
        if not photo_url:
            return None
        try:
            print(f"[CARD] Loading photo from: {photo_url[:60]}...")
            response = requests.get(photo_url, timeout=15)
            if response.status_code == 200:
                photo = Image.open(io.BytesIO(response.content))
                photo = photo.convert("RGB")
                return photo
            print(f"[CARD] Photo load failed: {response.status_code}")
        except Exception as e:
            print(f"[CARD] Photo error: {e}")
        return None

    def _create_placeholder_photo(self, name: str) -> Image.Image:
        """Create placeholder with initials when no photo available."""
        img = Image.new('RGB', (CARD_WIDTH, PHOTO_HEIGHT), PLACEHOLDER_BG)
        draw = ImageDraw.Draw(img)

        initials = "".join([n[0].upper() for n in (name or "?").split()[:2]])

        try:
            big_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90
            )
        except Exception:
            big_font = self.fonts.get("name", ImageFont.load_default())

        bbox = draw.textbbox((0, 0), initials, font=big_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (CARD_WIDTH - tw) // 2
        y = (PHOTO_HEIGHT - th) // 2 - 10

        draw.text((x, y), initials, font=big_font, fill=PLACEHOLDER_TEXT)
        return img

    def _draw_rounded_rect(self, draw: ImageDraw.Draw, xy: list, radius: int, fill=None, outline=None):
        """Draw a rounded rectangle."""
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)

    def _draw_pill_badge(self, draw: ImageDraw.Draw, text: str, x: int, y: int, font, bg_color, text_color, icon_text: str = ""):
        """Draw a pill-shaped badge with optional icon."""
        full_text = f"{icon_text} {text}".strip() if icon_text else text
        bbox = draw.textbbox((0, 0), full_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pad_x = 12
        pad_y = 6
        w = tw + pad_x * 2
        h = th + pad_y * 2

        draw.rounded_rectangle(
            [(x, y), (x + w, y + h)],
            radius=h // 2,
            fill=bg_color
        )
        draw.text((x + pad_x, y + pad_y), full_text, font=font, fill=text_color)

        return w, h

    def generate_profile_card(self, candidate: SwitchCandidate) -> bytes:
        """
        Generate a profile card matching Switch app business UI.

        Layout:
        1. Photo (full width, with verified + available badges)
        2. Name (bold)
        3. Experience
        4. Role tags (blue pills)
        5. Location, Language, Salary (with icons)
        6. Bottom stats bar (Jobs Done | Availability)
        """
        print(f"[CARD] Generating card for {candidate.name}")
        print(f"[CARD] Data: photo={candidate.photo_url is not None}, area={candidate.area}, exp={candidate.experience_level}, roles={candidate.preferred_roles}, langs={candidate.languages}")

        # Create white card
        card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
        draw = ImageDraw.Draw(card)

        # ============ PHOTO SECTION ============
        photo = self._load_profile_photo(candidate.photo_url)
        if photo:
            # Resize to cover photo area
            photo_ratio = photo.width / photo.height
            target_ratio = CARD_WIDTH / PHOTO_HEIGHT

            if photo_ratio > target_ratio:
                new_height = PHOTO_HEIGHT
                new_width = int(new_height * photo_ratio)
            else:
                new_width = CARD_WIDTH
                new_height = int(new_width / photo_ratio)

            photo = photo.resize((new_width, new_height), Image.Resampling.LANCZOS)

            left = (new_width - CARD_WIDTH) // 2
            top = (new_height - PHOTO_HEIGHT) // 2
            photo = photo.crop((left, top, left + CARD_WIDTH, top + PHOTO_HEIGHT))

            card.paste(photo, (0, 0))
        else:
            placeholder = self._create_placeholder_photo(candidate.name)
            card.paste(placeholder, (0, 0))

        # Redraw for badges on top of photo
        draw = ImageDraw.Draw(card)

        # Verified badge (top-right of photo)
        if candidate.is_verified:
            verified_text = "Verified"
            vb = draw.textbbox((0, 0), verified_text, font=self.fonts["badge"])
            vw = vb[2] - vb[0] + 28
            vh = vb[3] - vb[1] + 12
            vx = CARD_WIDTH - vw - 12
            vy = 12

            draw.rounded_rectangle(
                [(vx, vy), (vx + vw, vy + vh)],
                radius=vh // 2,
                fill=(255, 255, 255, 230)
            )
            draw.text((vx + 8, vy + 5), "\u2713", font=self.fonts["badge"], fill=GREEN)
            draw.text((vx + 22, vy + 5), verified_text, font=self.fonts["badge"], fill=GREEN)

        # "Available Now" badge (bottom-left of photo)
        if candidate.is_available:
            avail_text = "Available Now"
            ab = draw.textbbox((0, 0), avail_text, font=self.fonts["avail_badge"])
            aw = ab[2] - ab[0] + 30
            ah = ab[3] - ab[1] + 12
            ax = 12
            ay = PHOTO_HEIGHT - ah - 12

            draw.rounded_rectangle(
                [(ax, ay), (ax + aw, ay + ah)],
                radius=ah // 2,
                fill=GREEN
            )
            # Green dot
            dot_y = ay + ah // 2
            draw.ellipse([(ax + 10, dot_y - 4), (ax + 18, dot_y + 4)], fill=(255, 255, 255))
            draw.text((ax + 22, ay + 5), avail_text, font=self.fonts["avail_badge"], fill=WHITE)

        # ============ INFO SECTION (below photo) ============
        y_cursor = PHOTO_HEIGHT + 16

        # Name
        name = candidate.name or "Candidate"
        draw.text((PADDING, y_cursor), name, font=self.fonts["name"], fill=BLACK)
        y_cursor += 34

        # Experience
        exp_text = candidate.experience_level or "Not specified experience"
        draw.text((PADDING, y_cursor), exp_text, font=self.fonts["experience"], fill=GREY_TEXT)
        y_cursor += 28

        # ============ ROLE TAGS ============
        if candidate.preferred_roles:
            tag_x = PADDING
            tag_y = y_cursor
            max_tags_per_row = 2
            tag_count = 0

            for role in candidate.preferred_roles[:4]:
                rb = draw.textbbox((0, 0), role, font=self.fonts["role_tag"])
                rw = rb[2] - rb[0] + 20
                rh = rb[3] - rb[1] + 12

                # Wrap to next line if needed
                if tag_x + rw > CARD_WIDTH - PADDING:
                    tag_x = PADDING
                    tag_y += rh + 8

                draw.rounded_rectangle(
                    [(tag_x, tag_y), (tag_x + rw, tag_y + rh)],
                    radius=rh // 2,
                    fill=BLUE_BG
                )
                draw.text((tag_x + 10, tag_y + 5), role, font=self.fonts["role_tag"], fill=BLUE_TEXT)

                tag_x += rw + 8
                tag_count += 1

            y_cursor = tag_y + rh + 16
        else:
            y_cursor += 4

        # ============ INFO ROWS (location, language, salary) ============
        # Separator line
        draw.line([(PADDING, y_cursor), (CARD_WIDTH - PADDING, y_cursor)], fill=GREY_BORDER, width=1)
        y_cursor += 12

        info_items = []

        # Location
        if candidate.area:
            info_items.append(("location", candidate.area))

        # Language
        if candidate.languages:
            lang_text = ", ".join(candidate.languages[:2])
            info_items.append(("language", lang_text))

        # Salary
        if candidate.expected_salary_min or candidate.expected_salary_max:
            if candidate.expected_salary_min and candidate.expected_salary_max:
                salary_text = f"Expected: \u20b9{candidate.expected_salary_min:,} - \u20b9{candidate.expected_salary_max:,}"
            elif candidate.expected_salary_max:
                salary_text = f"Expected: \u20b9{candidate.expected_salary_max:,}"
            else:
                salary_text = "Expected: Negotiable"
            info_items.append(("salary", salary_text))
        else:
            info_items.append(("salary", "Expected: Negotiable"))

        for item_type, item_text in info_items:
            # Icon prefix
            if item_type == "location":
                icon = "\u25cf"  # filled circle as pin substitute
                icon_color = GREY_TEXT
            elif item_type == "language":
                icon = "\u25cb"  # open circle as chat substitute
                icon_color = GREY_TEXT
            elif item_type == "salary":
                icon = "\u20b9"  # rupee sign
                icon_color = GREY_TEXT
            else:
                icon = ""
                icon_color = GREY_TEXT

            draw.text((PADDING, y_cursor), icon, font=self.fonts["info"], fill=icon_color)
            draw.text((PADDING + 20, y_cursor), item_text, font=self.fonts["info"], fill=BLACK)
            y_cursor += 24

        # ============ BOTTOM STATS BAR ============
        y_cursor = max(y_cursor + 12, CARD_HEIGHT - 70)

        # Separator line
        draw.line([(PADDING, y_cursor), (CARD_WIDTH - PADDING, y_cursor)], fill=GREY_BORDER, width=1)
        y_cursor += 14

        # Three columns: Jobs Done | divider | Availability
        col_width = (CARD_WIDTH - PADDING * 2) // 2

        # Jobs Done (left)
        jobs_text = str(candidate.jobs_done)
        jobs_label = "Jobs Done"

        jb = draw.textbbox((0, 0), jobs_text, font=self.fonts["stat_num"])
        jw = jb[2] - jb[0]
        jlb = draw.textbbox((0, 0), jobs_label, font=self.fonts["stat_label"])
        jlw = jlb[2] - jlb[0]

        jobs_center_x = PADDING + col_width // 2
        draw.text((jobs_center_x - jw // 2, y_cursor), jobs_text, font=self.fonts["stat_num"], fill=GREEN_TEXT)
        draw.text((jobs_center_x - jlw // 2, y_cursor + 26), jobs_label, font=self.fonts["stat_label"], fill=GREY_TEXT)

        # Vertical divider
        div_x = PADDING + col_width
        draw.line([(div_x, y_cursor), (div_x, y_cursor + 42)], fill=GREY_BORDER, width=1)

        # Availability (right)
        avail_text = candidate.availability_type or "Immediately"
        avail_label = "Available"

        ab = draw.textbbox((0, 0), avail_text, font=self.fonts["stat_num"])
        aw = ab[2] - ab[0]
        alb = draw.textbbox((0, 0), avail_label, font=self.fonts["stat_label"])
        alw = alb[2] - alb[0]

        avail_center_x = PADDING + col_width + col_width // 2
        draw.text((avail_center_x - aw // 2, y_cursor), avail_text, font=self.fonts["stat_num"], fill=GREEN_TEXT)
        draw.text((avail_center_x - alw // 2, y_cursor + 26), avail_label, font=self.fonts["stat_label"], fill=GREY_TEXT)

        # ============ ROUNDED CORNERS ============
        card = self._round_corners(card, CORNER_RADIUS)

        # Convert to RGB for PNG output
        final = Image.new('RGB', card.size, WHITE)
        if card.mode == 'RGBA':
            final.paste(card, mask=card.split()[3])
        else:
            final.paste(card, (0, 0))

        # Save to bytes
        img_bytes = io.BytesIO()
        final.save(img_bytes, format='PNG', optimize=True)
        img_bytes.seek(0)

        result = img_bytes.getvalue()
        print(f"[CARD] Card generated: {len(result)} bytes")
        return result

    def _round_corners(self, img: Image.Image, radius: int) -> Image.Image:
        """Apply rounded corners to image."""
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)

        output = Image.new('RGBA', img.size, (0, 0, 0, 0))
        output.paste(img.convert('RGBA'), (0, 0))
        output.putalpha(mask)

        return output

    def generate_card_with_job_context(
        self,
        candidate: SwitchCandidate,
        job_role: str = "",
        job_location: str = "",
        match_reason: str = ""
    ) -> bytes:
        """Generate card (context shown in WhatsApp caption)."""
        return self.generate_profile_card(candidate)


# Singleton
switch_profile_card_service = SwitchProfileCardService()
