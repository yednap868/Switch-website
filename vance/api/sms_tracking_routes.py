"""
SMS click tracking routes.
GET /t/{token} — logs click and redirects to app.switchlocally.com
GET /api/sms/stats — returns campaign stats
"""

import time

from fastapi import APIRouter
from fastapi.responses import RedirectResponse, JSONResponse

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postgres import get_db
from models.sql_models import SmsClick

router = APIRouter(tags=["SMS Tracking"])

REDIRECT_URL = "https://app.switchlocally.com"


@router.get("/t/{token}")
def track_click(token: str):
    db = get_db()
    try:
        record = db.query(SmsClick).filter(SmsClick.token == token).first()
        if record and not record.clicked_at:
            record.clicked_at = time.time()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()
    return RedirectResponse(url=REDIRECT_URL, status_code=302)


@router.get("/api/sms/stats")
def sms_stats(campaign: str = None):
    db = get_db()
    try:
        q = db.query(SmsClick)
        if campaign:
            q = q.filter(SmsClick.campaign == campaign)
        total_sent = q.filter(SmsClick.sent_at != None).count()
        total_clicked = q.filter(SmsClick.clicked_at != None).count()
        total_signed_up = q.filter(SmsClick.signed_up == True).count()
        click_rate = round(100 * total_clicked / total_sent, 1) if total_sent else 0
        signup_rate = round(100 * total_signed_up / total_sent, 1) if total_sent else 0
        return JSONResponse({
            "campaign": campaign or "all",
            "total_sent": total_sent,
            "total_clicked": total_clicked,
            "total_signed_up": total_signed_up,
            "click_rate_pct": click_rate,
            "signup_rate_pct": signup_rate,
        })
    finally:
        db.close()


@router.get("/api/sms/stats/all-campaigns")
def sms_stats_by_campaign():
    db = get_db()
    try:
        campaigns = [r[0] for r in db.query(SmsClick.campaign).distinct().all()]
        result = []
        for camp in campaigns:
            q = db.query(SmsClick).filter(SmsClick.campaign == camp)
            sent = q.filter(SmsClick.sent_at != None).count()
            clicked = q.filter(SmsClick.clicked_at != None).count()
            signed_up = q.filter(SmsClick.signed_up == True).count()
            result.append({
                "campaign": camp,
                "sent": sent,
                "clicked": clicked,
                "signed_up": signed_up,
                "click_rate_pct": round(100 * clicked / sent, 1) if sent else 0,
                "signup_rate_pct": round(100 * signed_up / sent, 1) if sent else 0,
            })
        return JSONResponse(result)
    finally:
        db.close()
