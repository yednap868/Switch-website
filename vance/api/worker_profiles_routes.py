"""
Worker profiles viewer — reads switch_worker_profiles from Firestore.
GET /api/switch/worker-profiles        → JSON list
GET /api/switch/worker-profiles/view   → HTML card viewer
"""

import json
import time
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from utils.db import fs

router = APIRouter(prefix="/api/switch/worker-profiles", tags=["Worker Profiles"])

ROLE_EMOJI = {
    "waiter": "🍽️",
    "kitchen-helper": "👨‍🍳",
    "delivery-rider": "🛵",
    "warehouse-picker": "📦",
    "security-guard": "🔒",
    "store-helper": "🛒",
    "cashier": "💰",
    "office-cleaner": "🧹",
    "factory-helper": "🏭",
    "iti-fitter": "🔧",
    "iti-mechanical": "⚙️",
    "iti-machinist": "🔩",
    "iti-welder": "🔥",
    "factory-supervisor": "📋",
}


def load_profiles(limit: int = 0) -> list:
    query = fs.collection("switch_worker_profiles").order_by("generated_at", direction="DESCENDING")
    if limit:
        query = query.limit(limit)
    docs = list(query.stream())
    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    return results


@router.get("/")
async def get_profiles_json():
    profiles = load_profiles()
    return JSONResponse({"count": len(profiles), "profiles": profiles})


@router.get("/view", response_class=HTMLResponse)
async def view_profiles():
    profiles = load_profiles()

    if not profiles:
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;padding:40px;background:#f5f5f5">
        <h2>No worker profiles yet</h2>
        <p>Run <code>uv run python scripts/generate_worker_profiles_from_jyoti.py --limit 10</code></p>
        </body></html>
        """)

    cards_html = ""
    for p in profiles:
        phone = p.get("phone", "")
        name = p.get("name") or "Unknown"
        display_phone = f"+{phone[-10:]}" if len(phone) >= 10 else phone
        pitch = p.get("pitch", "")
        strengths = p.get("strengths", [])
        work_history = p.get("work_history", [])
        best_roles = p.get("best_roles", [])
        qf = p.get("quick_facts", {})
        outcome = p.get("last_outcome", "")
        calls = p.get("total_calls", 0)
        summary = p.get("call_summary", "")
        conv_id = p.get("conversation_id", "")
        generated_at = p.get("generated_at", 0)
        gen_time = time.strftime("%d %b %H:%M", time.localtime(generated_at)) if generated_at else ""

        # Role chips
        role_chips = ""
        for role in best_roles:
            emoji = ROLE_EMOJI.get(role, "💼")
            role_chips += f'<span class="chip">{emoji} {role}</span>'

        # Strengths list
        strengths_html = ""
        for s in (strengths or []):
            strengths_html += f'<li>{s}</li>'

        # Work history
        work_html = ""
        for w in (work_history or []):
            role_w = w.get("role", "")
            employer = w.get("employer", "")
            duration = w.get("duration", "")
            if role_w or employer:
                work_html += f'<div class="work-item"><strong>{role_w}</strong>'
                if employer:
                    work_html += f' @ {employer}'
                if duration:
                    work_html += f' <span class="muted">· {duration}</span>'
                work_html += '</div>'

        # Quick facts
        exp = qf.get("experience", "")
        sal_min = qf.get("salary_min", 0)
        sal_max = qf.get("salary_max", 0)
        city = qf.get("city", "")
        area = qf.get("area", "")
        avail = qf.get("availability", "")
        langs = qf.get("languages", "")
        edu = qf.get("education", "")

        salary_str = ""
        if sal_min and sal_max:
            salary_str = f"₹{sal_min:,}–₹{sal_max:,}/mo"
        elif sal_min:
            salary_str = f"₹{sal_min:,}+/mo"

        facts_html = ""
        for label, val in [("Experience", exp), ("Salary", salary_str), ("City", city), ("Area", area), ("Available", avail), ("Languages", langs), ("Education", edu)]:
            if val:
                facts_html += f'<div class="fact"><span class="fact-label">{label}</span><span class="fact-val">{val}</span></div>'

        outcome_color = {"interested": "#22c55e", "completed": "#3b82f6", "callback": "#f59e0b"}.get(outcome, "#94a3b8")
        outcome_label = outcome or "unknown"

        # ElevenLabs link
        el_link = f'<a class="conv-link" href="https://elevenlabs.io/app/conversational-ai/history/{conv_id}" target="_blank">View transcript ↗</a>' if conv_id else ''

        cards_html += f"""
        <div class="card">
          <div class="card-header">
            <div>
              <div class="worker-name">{name if name and name != 'Unknown' else display_phone}</div>
              <div class="worker-sub">{display_phone if name and name != 'Unknown' else ''}</div>
            </div>
            <div class="meta-right">
              <span class="outcome-badge" style="background:{outcome_color}20;color:{outcome_color};border:1px solid {outcome_color}40">{outcome_label}</span>
              <div class="muted" style="margin-top:4px">{calls} call{'s' if calls != 1 else ''}</div>
            </div>
          </div>

          <div class="roles-row">{role_chips}</div>

          <div class="pitch">{pitch}</div>

          <div class="section-grid">
            <div>
              {'<div class="section-title">Strengths</div><ul class="strengths-list">' + strengths_html + '</ul>' if strengths_html else ''}
              {'<div class="section-title">Work History</div><div class="work-list">' + work_html + '</div>' if work_html else ''}
            </div>
            <div>
              {'<div class="section-title">Quick Facts</div><div class="facts">' + facts_html + '</div>' if facts_html else ''}
            </div>
          </div>

          <div class="card-footer">
            <span class="muted">Generated {gen_time}</span>
            {el_link}
          </div>
        </div>
        """

    total = len(profiles)
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Switch Worker Profiles</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; }}
    .header {{ background: #0f172a; color: white; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }}
    .header h1 {{ font-size: 20px; font-weight: 700; }}
    .header .count {{ background: #334155; color: #94a3b8; padding: 4px 10px; border-radius: 20px; font-size: 13px; }}
    .container {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; display: grid; gap: 20px; }}
    .card {{ background: white; border-radius: 16px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
    .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }}
    .worker-name {{ font-size: 18px; font-weight: 700; color: #0f172a; }}
    .worker-sub {{ font-size: 13px; color: #64748b; margin-top: 2px; }}
    .meta-right {{ text-align: right; }}
    .outcome-badge {{ font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 20px; text-transform: capitalize; }}
    .muted {{ font-size: 12px; color: #94a3b8; }}
    .roles-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
    .chip {{ background: #f1f5f9; color: #475569; font-size: 12px; font-weight: 500; padding: 4px 10px; border-radius: 20px; border: 1px solid #e2e8f0; }}
    .pitch {{ font-size: 15px; line-height: 1.6; color: #334155; background: #f8fafc; border-radius: 10px; padding: 14px 16px; margin-bottom: 16px; border-left: 3px solid #3b82f6; }}
    .section-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 600px) {{ .section-grid {{ grid-template-columns: 1fr; }} }}
    .section-title {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 8px; }}
    .strengths-list {{ padding-left: 16px; }}
    .strengths-list li {{ font-size: 13px; color: #475569; margin-bottom: 5px; line-height: 1.5; }}
    .work-list {{ display: flex; flex-direction: column; gap: 6px; }}
    .work-item {{ font-size: 13px; color: #475569; }}
    .work-item strong {{ color: #1e293b; }}
    .facts {{ display: flex; flex-direction: column; gap: 6px; }}
    .fact {{ display: flex; justify-content: space-between; font-size: 13px; padding: 5px 0; border-bottom: 1px solid #f1f5f9; }}
    .fact-label {{ color: #94a3b8; font-weight: 500; }}
    .fact-val {{ color: #1e293b; font-weight: 600; text-align: right; max-width: 55%; }}
    .card-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 12px; border-top: 1px solid #f1f5f9; }}
    .conv-link {{ font-size: 13px; color: #3b82f6; text-decoration: none; font-weight: 500; }}
    .conv-link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Switch Worker Profiles</h1>
    <span class="count">{total} profile{'s' if total != 1 else ''}</span>
  </div>
  <div class="container">
    {cards_html}
  </div>
</body>
</html>"""

    return HTMLResponse(page_html)
