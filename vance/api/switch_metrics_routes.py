"""
API routes for Switch metrics and analytics.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from services.switch_metrics import switch_metrics_service

router = APIRouter(prefix="/api/switch/metrics", tags=["Switch Metrics"])




@router.get("/")
async def get_all_metrics():
    """Get all key metrics."""
    try:
        metrics = switch_metrics_service.get_all_metrics()
        return JSONResponse({
            "status": "success",
            "metrics": metrics
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")


@router.get("/job/{job_id}")
async def get_job_metrics(job_id: str):
    """Get metrics for a specific job."""
    try:
        time_to_first = switch_metrics_service.get_time_to_first_candidate(job_id)
        match_rate = switch_metrics_service.get_match_rate(job_id)
        show_up_rate = switch_metrics_service.get_show_up_rate(job_id)
        placement_rate = switch_metrics_service.get_placement_rate(job_id)
        
        return JSONResponse({
            "status": "success",
            "job_id": job_id,
            "time_to_first_candidate_seconds": time_to_first,
            "match_rate": match_rate,
            "show_up_rate": show_up_rate,
            "placement_rate": placement_rate
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job metrics: {str(e)}")


@router.get("/candidates/pool")
async def get_candidates_pool():
    """Get candidates in pool metrics."""
    try:
        pool_metrics = switch_metrics_service.get_candidates_in_pool()
        return JSONResponse({
            "status": "success",
            "pool": pool_metrics
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pool metrics: {str(e)}")


@router.get("/jobs/open")
async def get_open_jobs_count():
    """Get count of open jobs."""
    try:
        count = switch_metrics_service.get_open_jobs_count()
        return JSONResponse({
            "status": "success",
            "open_jobs_count": count
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting open jobs count: {str(e)}")
