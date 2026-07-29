"""
Background service to automatically generate authentic AI comments on new user posts.
Runs every minute to check for posts that need comments (2-3 minutes after creation).
"""

import os
import time
import random
import traceback
from typing import Dict

from anthropic import Anthropic

from models.sql_models import CommunityPost, CommunityComment, CommunityLike
from utils.postgres import get_db

claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_authentic_comment(post_text: str, comment_index: int = 0, post_theme: str = None) -> Dict:
    """Generate an authentic-sounding comment."""
    try:
        anonymous_names = [
            "Amit", "Suresh", "Mohan", "Rajesh", "Vikram", "Ramesh",
            "Kumar", "Deepak", "Anil", "Sunil", "Pradeep", "Naresh",
            "Ravi", "Sandeep", "Manish", "Ajay", "Vishal", "Rohit"
        ]

        prompt = f"""Someone posted this on a job community:

"{post_text}"

Write a short, natural comment (20-35 words) in Hinglish or Pure Hindi. Be empathetic and real. Use Hindi words for numbers.

Generate ONE comment."""

        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "text": message.content[0].text.strip(),
            "author_name": random.choice(anonymous_names),
            "is_anonymous": True,
            "is_ai_generated": True,
        }

    except Exception as e:
        print(f"[AUTO_COMMENT] Error generating comment: {e}")
        fallback_comments = [
            "Bhai same situation mere saath bhi hua tha. Don't give up!",
            "Sahi bola. Stay strong!",
            "Bhai Switch try kar, help milegi.",
        ]
        return {
            "text": random.choice(fallback_comments),
            "author_name": random.choice(["Amit", "Suresh", "Mohan", "Rajesh"]),
            "is_anonymous": True,
            "is_ai_generated": True,
        }


def check_and_comment_on_new_posts():
    """Check for posts that need AI comments (2-3 minutes after creation)."""
    try:
        current_time = time.time()

        db = get_db()
        try:
            posts_needing_comments = (
                db.query(CommunityPost)
                .filter(CommunityPost.needs_ai_comments == True)
                .all()
            )

            posts_to_comment = []
            for p in posts_needing_comments:
                post_age = current_time - (p.created_at or 0)
                if 120 <= post_age <= 180:
                    existing_ai = (
                        db.query(CommunityComment)
                        .filter_by(post_id=p.post_id, is_ai_generated=True)
                        .count()
                    )
                    if existing_ai == 0:
                        posts_to_comment.append({
                            "id": p.post_id,
                            "text": p.text or "",
                            "created_at": p.created_at or 0,
                            "theme": p.theme,
                        })

            for post in posts_to_comment:
                try:
                    num_comments = random.randint(2, 3)
                    for i in range(num_comments):
                        comment_data = generate_authentic_comment(
                            post["text"],
                            comment_index=i,
                            post_theme=post.get("theme"),
                        )
                        comment_timestamp = post["created_at"] + random.randint(120, 240)
                        comment = CommunityComment(
                            comment_id=f"ai_comment_{int(time.time() * 1000)}_{i}",
                            post_id=post["id"],
                            user_id=f"ai_user_{random.randint(1000, 9999)}",
                            text=comment_data["text"],
                            author_name=comment_data["author_name"],
                            is_anonymous=True,
                            is_ai_generated=True,
                            created_at=comment_timestamp,
                        )
                        db.add(comment)

                    post_row = db.query(CommunityPost).filter_by(post_id=post["id"]).first()
                    if post_row:
                        post_row.needs_ai_comments = False

                    num_likes = random.randint(5, 10)
                    for j in range(num_likes):
                        like = CommunityLike(
                            like_id=f"ai_like_{int(time.time() * 1000)}_{j}",
                            post_id=post["id"],
                            user_id=f"ai_user_{random.randint(1000, 9999)}",
                            created_at=post["created_at"] + random.randint(60, 180),
                        )
                        db.add(like)

                    db.commit()
                    print(f"[AUTO_COMMENT] Processed post {post['id'][:20]} with {num_comments} comments and {num_likes} likes")

                except Exception as e:
                    print(f"[AUTO_COMMENT] Error processing post {post['id']}: {e}")
                    db.rollback()
                    continue

            if posts_to_comment:
                print(f"[AUTO_COMMENT] Processed {len(posts_to_comment)} posts")
        finally:
            db.close()

    except Exception as e:
        print(f"[AUTO_COMMENT] Error in check_and_comment: {e}")
        traceback.print_exc()
