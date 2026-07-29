"""
API route to trigger auto-comment checking (can be called by cron or scheduled task).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.community_auto_comment_service import check_and_comment_on_new_posts

router = APIRouter(prefix="/api/community", tags=["Community Feed"])


@router.post("/auto-comment")
async def trigger_auto_comment():
    """
    Manually trigger auto-comment checking for new posts.
    This should be called every minute via cron or scheduled task.
    """
    try:
        check_and_comment_on_new_posts()
        
        return JSONResponse({
            "status": "success",
            "message": "Auto-comment check completed",
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
        }, status_code=500, headers={"Access-Control-Allow-Origin": "*"})
