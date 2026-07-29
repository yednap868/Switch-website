"""
AI Service for Community Feed Content Generation.
Uses Claude to generate realistic rants and engagement (likes/comments).
"""

import os
import time
import random
from typing import Dict

from anthropic import Anthropic

from models.sql_models import CommunityPost, CommunityLike, CommunityComment
from utils.postgres import get_db

claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_rant_prompt(theme: str = None) -> str:
    """
    Generate a prompt for Claude to create a realistic job/work-related rant.
    """
    themes = {
        "morning_rant": """Generate a MORNING RANT post. Someone venting about their boss or work situation early in the day.
You can write in EITHER Hinglish (Roman script) OR Pure Hindi (Devanagari script). Mix both for authenticity.
CRITICAL: Use Hindi words for numbers: दस हज़ार, पंद्रह हज़ार, बीस हज़ार (NOT 10K, 15K, 20K).
Focus on: Boss behavior, workplace issues, frustration, morning incidents""",

        "success_story": """Generate a SUCCESS STORY post. Someone sharing their positive experience with Switch or job change.
You can write in EITHER Hinglish (Roman script) OR Pure Hindi (Devanagari script). Mix both for authenticity.
CRITICAL: Use Hindi words for numbers: अठारह हज़ार, चौबीस हज़ार (NOT ₹18K, ₹24K, 18K).
Focus on: Salary increase, job change success, Switch helping, positive outcomes""",

        "question": """Generate a QUESTION post. Someone asking for help or advice from the community.
You can write in EITHER Hinglish (Roman script) OR Pure Hindi (Devanagari script). Mix both for authenticity.
CRITICAL: Use Hindi words for numbers and dates.
Focus on: Asking for help, interview tips, job search advice, community support""",

        "state_callout": """Generate a STATE CALLOUT post. Someone looking for people from their state or region.
You can write in EITHER Hinglish (Roman script) OR Pure Hindi (Devanagari script). Mix both for authenticity.
Focus on: Regional identity, finding people from same state, community connection"""
    }

    selected_theme = theme if theme and theme in themes else random.choice(list(themes.keys()))
    theme_instruction = themes[selected_theme]

    return f"""You are a member of the Switch job platform community. Generate a realistic, relatable post about work, jobs, bosses, or career.

CRITICAL: You MUST write ONLY in PURE HINDI using Devanagari script (हिंदी लिपि).

THEME INSTRUCTIONS:
{theme_instruction}

GENERAL GUIDELINES:
- Write in PURE HINDI using Devanagari script (हिंदी)
- Keep it 30-100 words
- Make it relatable to blue-collar/service workers in India
- Include SPECIFIC details with Hindi words for numbers
- Should feel genuine and authentic
- Use natural Hindi phrases

Generate ONE post in PURE HINDI Devanagari script following the theme."""


def generate_engagement_prompt(post_text: str, engagement_type: str = "comment", comment_index: int = 0) -> str:
    """Generate a prompt for engagement comments."""
    return f"""You are a supportive community member on Switch. Someone posted this:

"{post_text}"

Write a helpful, empathetic comment (20-50 words) in Hinglish or Pure Hindi. Use Hindi words for numbers.

Generate ONE comment."""


def generate_rant(theme: str = None) -> Dict:
    """Use Claude to generate a realistic rant."""
    try:
        prompt = generate_rant_prompt(theme)

        message = claude_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        rant_text = message.content[0].text.strip()

        ai_names = [
            "Amit", "Suresh", "Mohan", "Rajesh", "Vikram", "Ramesh",
            "Kumar", "Deepak", "Anil", "Sunil", "Pradeep", "Naresh"
        ]

        detected_theme = None
        if "bezzati" in rant_text.lower() or "boss" in rant_text.lower():
            detected_theme = "morning_rant"
        elif "mil gayi" in rant_text.lower() or "success" in rant_text.lower():
            detected_theme = "success_story"
        elif "?" in rant_text or "chahiye" in rant_text.lower():
            detected_theme = "question"
        elif "se kaun" in rant_text.lower() or "bihar" in rant_text.lower():
            detected_theme = "state_callout"

        return {
            "text": rant_text,
            "author_name": random.choice(ai_names),
            "is_anonymous": True,
            "is_ai_generated": True,
            "theme": detected_theme or theme or random.choice(["morning_rant", "success_story", "question", "state_callout"]),
        }

    except Exception as e:
        print(f"[COMMUNITY_AI] Error generating rant: {e}")
        fallbacks = [
            "बॉस ने आज बेज्जती की। मीटिंग में सबके सामने गाली दी। क्या करूं?",
            "नौकरी मिल गई! Switch पर रजिस्टर किया, एक हफ्ते में जॉब मिल गई।",
            "इंटरव्यू टिप्स चाहिए, मदद करो। कल इंटरव्यू है।",
        ]
        return {
            "text": random.choice(fallbacks),
            "author_name": random.choice(["Amit", "Suresh", "Mohan"]),
            "is_anonymous": True,
            "is_ai_generated": True,
            "theme": theme or "morning_rant",
        }


def generate_engagement_comment(post_text: str, comment_index: int = 0) -> Dict:
    """Use Claude to generate an engaging comment."""
    try:
        prompt = generate_engagement_prompt(post_text, "comment", comment_index)

        message = claude_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "text": message.content[0].text.strip(),
            "author_name": random.choice(["Amit", "Suresh", "Mohan", "Rajesh", "Vikram"]),
            "is_anonymous": True,
            "is_ai_generated": True,
        }

    except Exception as e:
        print(f"[COMMUNITY_AI] Error generating comment: {e}")
        fallbacks = [
            "Bhai exact same tha mera. Switch try kar, better job milega.",
            "Arre bhai tu kyun seh raha hai? Switch try kar.",
            "Sahi bola. Main bhi badla tha. Best decision.",
        ]
        return {
            "text": random.choice(fallbacks),
            "author_name": random.choice(["Amit", "Suresh", "Mohan"]),
            "is_anonymous": True,
            "is_ai_generated": True,
        }


def seed_community_content(posts_per_day: int = 100):
    """Seed community feed with AI-generated posts and engagement."""
    try:
        print(f"[COMMUNITY_AI] Starting content seeding: {posts_per_day} posts/day")

        posts_created = 0
        comments_created = 0
        likes_created = 0
        themes = ["morning_rant", "success_story", "question", "state_callout"]

        for i in range(posts_per_day):
            try:
                theme = themes[i % len(themes)]
                rant_data = generate_rant(theme=theme)

                post_id = f"ai_post_{int(time.time() * 1000)}_{i}"
                post_timestamp = time.time() - random.randint(0, 86400)

                db = get_db()
                try:
                    post = CommunityPost(
                        post_id=post_id,
                        user_id=f"ai_user_{random.randint(1000, 9999)}",
                        text=rant_data["text"],
                        author_name=rant_data["author_name"],
                        is_anonymous=True,
                        is_ai_generated=True,
                        theme=rant_data.get("theme", "morning_rant"),
                        created_at=post_timestamp,
                    )
                    db.add(post)
                    posts_created += 1

                    num_comments = random.randint(3, 6)
                    for j in range(num_comments):
                        comment_data = generate_engagement_comment(rant_data["text"], comment_index=j)
                        if j < 3:
                            comment_timestamp = post_timestamp + random.randint(300, 3600)
                        elif j == 4:
                            comment_timestamp = post_timestamp + random.randint(7200, 14400)
                        else:
                            comment_timestamp = post_timestamp + random.randint(86400, 172800)

                        comment = CommunityComment(
                            comment_id=f"ai_comment_{int(time.time() * 1000)}_{i}_{j}",
                            post_id=post_id,
                            user_id=f"ai_user_{random.randint(1000, 9999)}",
                            text=comment_data["text"],
                            author_name=comment_data["author_name"],
                            is_anonymous=True,
                            is_ai_generated=True,
                            created_at=comment_timestamp,
                        )
                        db.add(comment)
                        comments_created += 1

                    num_likes = random.randint(5, 20)
                    for k in range(num_likes):
                        like_user = f"ai_user_{random.randint(1000, 9999)}"
                        like = CommunityLike(
                            like_id=f"ai_like_{int(time.time() * 1000)}_{i}_{k}",
                            post_id=post_id,
                            user_id=like_user,
                            created_at=post_timestamp + random.randint(60, 7200),
                        )
                        db.add(like)
                        likes_created += 1

                    db.commit()
                finally:
                    db.close()

                if i % 10 == 0:
                    print(f"  Created {i+1}/{posts_per_day} posts...")
                    time.sleep(1)

            except Exception as e:
                print(f"  Error creating post {i}: {e}")
                continue

        print(f"[COMMUNITY_AI] Content seeding complete: {posts_created} posts, {comments_created} comments, {likes_created} likes")

        return {
            "posts_created": posts_created,
            "comments_created": comments_created,
            "likes_created": likes_created,
        }

    except Exception as e:
        print(f"[COMMUNITY_AI] Error in content seeding: {e}")
        raise
