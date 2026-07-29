"""
API routes for Community Feed - anonymous rants and engagement.
All data stored in PostgreSQL.
"""

import random
import time
import traceback

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from models.sql_models import CommunityPost, CommunityLike, CommunityComment
from utils.hearus_auth import caller_phone
from utils.postgres import get_db

router = APIRouter(prefix="/api/community", tags=["Community Feed"])


class PostRantRequest(BaseModel):
    """Request model for posting a rant."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None
    text: str
    is_anonymous: bool = True


class LikePostRequest(BaseModel):
    """Request model for liking a post."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None


class CommentPostRequest(BaseModel):
    """Request model for commenting on a post."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None
    text: str
    is_anonymous: bool = True




@router.get("/feed")
async def get_community_feed(request: Request):
    """Get community feed posts sorted by engagement and recency (caller identity from token)."""
    try:
        user_id = caller_phone(request)
        db = get_db()
        try:
            post_rows = (
                db.query(CommunityPost)
                .order_by(CommunityPost.created_at.desc())
                .limit(50)
                .all()
            )

            posts = []
            for p in post_rows:
                likes = db.query(CommunityLike).filter_by(post_id=p.post_id).all()
                likes_count = len(likes)

                user_liked = any(lk.user_id == user_id for lk in likes)

                comment_rows = (
                    db.query(CommunityComment)
                    .filter_by(post_id=p.post_id)
                    .order_by(CommunityComment.created_at.asc())
                    .limit(10)
                    .all()
                )

                comments = [
                    {
                        "id": c.comment_id,
                        "text": c.text or "",
                        "author_name": c.author_name,
                        "is_anonymous": c.is_anonymous,
                        "created_at": c.created_at,
                    }
                    for c in comment_rows
                ]

                posts.append({
                    "id": p.post_id,
                    "text": p.text or "",
                    "author_name": p.author_name,
                    "is_anonymous": p.is_anonymous,
                    "created_at": p.created_at,
                    "likes_count": likes_count,
                    "comments_count": len(comments),
                    "user_liked": user_liked,
                    "comments": comments,
                    "theme": p.theme,
                })
        finally:
            db.close()

        posts.sort(key=lambda p: (
            p["likes_count"] + p["comments_count"] * 2,
            p["created_at"]
        ), reverse=True)

        return JSONResponse({
            "status": "success",
            "posts": posts,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[COMMUNITY] Error fetching feed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching feed: {str(e)}")


@router.post("/post")
async def create_post(payload: PostRantRequest, http_request: Request):
    """Create a new community post for the calling user (identity from token)."""
    try:
        user_id = caller_phone(http_request)
        post_id = f"post_{int(time.time() * 1000)}_{user_id[:8]}"

        anonymous_names = ["Worker1", "JobSeeker", "Helper", "Supporter", "CommunityMember"]
        author_name = random.choice(anonymous_names)

        db = get_db()
        try:
            post = CommunityPost(
                post_id=post_id,
                user_id=user_id,
                text=payload.text,
                is_anonymous=payload.is_anonymous,
                author_name=author_name if payload.is_anonymous else None,
                is_ai_generated=False,
                needs_ai_comments=True,
                created_at=time.time(),
            )
            db.add(post)
            db.commit()
        finally:
            db.close()

        print(f"[COMMUNITY] Post created: {post_id}")

        return JSONResponse({
            "status": "success",
            "message": "Post created successfully",
            "post_id": post_id,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[COMMUNITY] Error creating post: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating post: {str(e)}")


@router.post("/post/{post_id}/like")
async def like_post(post_id: str, payload: LikePostRequest, http_request: Request):
    """Like or unlike a post (caller identity from token)."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            existing = (
                db.query(CommunityLike)
                .filter_by(post_id=post_id, user_id=user_id)
                .first()
            )

            if existing:
                db.delete(existing)
                action = "unliked"
            else:
                like_id = f"like_{int(time.time() * 1000)}_{user_id[:8]}"
                like = CommunityLike(
                    like_id=like_id,
                    post_id=post_id,
                    user_id=user_id,
                    created_at=time.time(),
                )
                db.add(like)
                action = "liked"

            db.commit()
        finally:
            db.close()

        print(f"[COMMUNITY] Post {post_id} {action} by user {user_id[:8]}")

        return JSONResponse({
            "status": "success",
            "action": action,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[COMMUNITY] Error liking post: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error liking post: {str(e)}")


@router.post("/post/{post_id}/comment")
async def add_comment(post_id: str, payload: CommentPostRequest, http_request: Request):
    """Add a comment to a post (caller identity from token)."""
    try:
        user_id = caller_phone(http_request)
        comment_id = f"comment_{int(time.time() * 1000)}_{user_id[:8]}"

        anonymous_names = ["Helper1", "Supporter", "Friend", "CommunityMember", "Worker"]
        author_name = random.choice(anonymous_names)

        db = get_db()
        try:
            comment = CommunityComment(
                comment_id=comment_id,
                post_id=post_id,
                user_id=user_id,
                text=payload.text,
                is_anonymous=payload.is_anonymous,
                author_name=author_name if payload.is_anonymous else None,
                is_ai_generated=False,
                created_at=time.time(),
            )
            db.add(comment)
            db.commit()
        finally:
            db.close()

        print(f"[COMMUNITY] Comment added to post {post_id}")

        return JSONResponse({
            "status": "success",
            "message": "Comment added successfully",
            "comment_id": comment_id,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[COMMUNITY] Error adding comment: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}")
