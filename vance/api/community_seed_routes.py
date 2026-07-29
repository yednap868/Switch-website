"""
API route to manually trigger community content seeding (for testing/admin).
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.community_ai_service import seed_community_content

router = APIRouter(prefix="/api/community", tags=["Community Feed"])


@router.post("/seed")
async def trigger_seeding(posts_per_day: int = 100):
    """
    Manually trigger community content seeding.
    WARNING: This generates AI content. Use sparingly.
    """
    try:
        result = seed_community_content(posts_per_day=posts_per_day)
        
        return JSONResponse({
            "status": "success",
            "message": f"Seeded {result['posts_created']} posts with engagement",
            "result": result,
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding content: {str(e)}")
