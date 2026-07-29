"""
Switch UPI payment routes — initiation, UTR confirmation, admin verification.

Flow:
  employer POST /payments/initiate  → creates UPI payment record, returns link
  employer POST /payments/confirm   → submits UTR, marks awaiting_verification
  admin    GET  /admin/payments/pending   → lists pending verifications (HTML page)
  admin    POST /admin/payments/{id}/verify  → marks verified
  admin    POST /admin/payments/{id}/reject  → marks failed
  admin    GET  /admin/payments/export  → CSV download
"""

import csv
import io
import os
import re
import threading
import time
from typing import Optional

import requests as _http
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from models.sql_models import UPIPayment
from utils.db import fs
from utils.hearus_auth import caller_phone
from utils.postgres import get_db
from utils.upi import generate_upi_link, UPI_VPA, MERCHANT_NAME

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "switch-admin-key")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
PRICE_PER_HIRE = 2000

router = APIRouter(prefix="/api/switch", tags=["Switch Payments"])
pages_router = APIRouter(tags=["Switch Payment Admin"])


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fetch_hiring_request(req_id: str) -> dict | None:
    try:
        doc = fs.collection("switch_hiring_requests").document(req_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None


def _update_firestore_payment_status(req_id: str, payment_status: str) -> None:
    def _write():
        try:
            fs.collection("switch_hiring_requests").document(req_id).update(
                {"payment_status": payment_status}
            )
        except Exception as exc:
            print(f"[PAYMENT] Firestore update failed for {req_id}: {exc}")
    threading.Thread(target=_write, daemon=True).start()


def _notify(message: str) -> None:
    print(f"[PAYMENT] {message}")
    if not SLACK_WEBHOOK_URL:
        return
    def _send():
        try:
            _http.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _check_admin(request: Request) -> bool:
    return request.headers.get("X-Admin-Key") == ADMIN_API_KEY


# ── Request models ───────────────────────────────────────────────────────────

class InitiatePaymentRequest(BaseModel):
    hiring_request_id: str


class ConfirmPaymentRequest(BaseModel):
    payment_id: int
    utr: str


class DirectUTRSubmit(BaseModel):
    hiring_request_id: str
    amount: int
    utr: str


class AdminVerifyRequest(BaseModel):
    notes: Optional[str] = None
    verified_by: Optional[str] = "admin"


class AdminRejectRequest(BaseModel):
    reason: str


# ── Employer endpoints ───────────────────────────────────────────────────────

@router.post("/payments/initiate")
async def initiate_payment(req: InitiatePaymentRequest, request: Request):
    if not UPI_VPA:
        return JSONResponse({"error": "UPI payments not configured. Contact support."}, status_code=503)

    employer_phone = caller_phone(request)

    hiring_req = _fetch_hiring_request(req.hiring_request_id)
    if not hiring_req:
        return JSONResponse({"error": "Hiring request not found"}, status_code=404)

    if hiring_req.get("employer_phone") != employer_phone:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    headcount = int(hiring_req.get("headcount", 1))
    amount = headcount * PRICE_PER_HIRE

    db = get_db()
    try:
        existing = (
            db.query(UPIPayment)
            .filter(
                UPIPayment.hiring_request_id == req.hiring_request_id,
                UPIPayment.status == "pending",
            )
            .all()
        )
        for p in existing:
            p.status = "duplicate"
            p.updated_at = time.time()
        db.commit()

        raw_ref = f"SW_{req.hiring_request_id[:20]}_{int(time.time())}"
        payment_ref = raw_ref[:35]

        upi_link = generate_upi_link(float(amount), payment_ref)

        payment = UPIPayment(
            hiring_request_id=req.hiring_request_id,
            employer_phone=employer_phone,
            amount=amount,
            upi_link=upi_link,
            payment_ref=payment_ref,
            status="pending",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        _update_firestore_payment_status(req.hiring_request_id, "pending")

        return JSONResponse({
            "payment_id": payment.id,
            "upi_link": upi_link,
            "amount": amount,
            "payment_ref": payment_ref,
            "merchant_vpa": UPI_VPA,
            "merchant_name": MERCHANT_NAME,
        }, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()


@router.post("/payments/confirm")
async def confirm_payment(req: ConfirmPaymentRequest, request: Request):
    if not re.fullmatch(r"\d{12}", req.utr):
        return JSONResponse(
            {"error": "UTR exactly 12 digits ka hona chahiye"},
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    caller = caller_phone(request)

    db = get_db()
    try:
        duplicate = db.query(UPIPayment).filter_by(employer_submitted_utr=req.utr).first()
        if duplicate:
            return JSONResponse(
                {"error": "Yeh UTR pehle se use ho chuka hai. Sahi UTR enter karein ya support se contact karein."},
                status_code=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        payment = db.query(UPIPayment).filter_by(id=req.payment_id).first()
        if not payment:
            return JSONResponse(
                {"error": "Payment record not found"},
                status_code=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if payment.employer_phone and payment.employer_phone != caller:
            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=403,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if payment.status == "verified":
            return JSONResponse(
                {"error": "Yeh payment pehle se verify ho chuka hai"},
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        payment.employer_submitted_utr = req.utr
        payment.status = "awaiting_verification"
        payment.updated_at = time.time()

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return JSONResponse(
                {"error": "Yeh UTR pehle se use ho chuka hai. Sahi UTR enter karein ya support se contact karein."},
                status_code=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        _update_firestore_payment_status(payment.hiring_request_id, "awaiting_verification")

        role = ""
        hr = _fetch_hiring_request(payment.hiring_request_id)
        if hr:
            role = hr.get("role_label") or hr.get("role", "")

        _notify(
            f"💰 UTR submitted — needs verification\n"
            f"Phone: {payment.employer_phone}\n"
            f"Amount: ₹{payment.amount:,}\n"
            f"UTR: {req.utr}\n"
            f"Role: {role} | Payment ID: {payment.id}\n"
            f"Verify: https://api.relayy.world/admin/payments/pending?admin_key=..."
        )

        return JSONResponse(
            {"success": True, "message": "Payment submitted for verification. Hum 2 ghante mein confirm kar denge."},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    finally:
        db.close()


@router.post("/payments/submit")
async def direct_utr_submit(req: DirectUTRSubmit, request: Request):
    """One-shot endpoint: create payment record and mark awaiting_verification."""
    employer_phone = caller_phone(request)

    if not re.fullmatch(r"\d{12}", req.utr):
        return JSONResponse(
            {"error": "UTR exactly 12 digits ka hona chahiye"},
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    db = get_db()
    try:
        duplicate = db.query(UPIPayment).filter_by(employer_submitted_utr=req.utr).first()
        if duplicate:
            return JSONResponse(
                {"error": "Yeh UTR pehle se use ho chuka hai. Sahi UTR enter karein."},
                status_code=409,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        payment_ref = f"SW_{req.hiring_request_id[:20]}_{int(time.time())}"[:35]
        upi_link = generate_upi_link(float(req.amount), payment_ref) if UPI_VPA else ""

        payment = UPIPayment(
            hiring_request_id=req.hiring_request_id,
            employer_phone=employer_phone,
            amount=req.amount,
            upi_link=upi_link,
            payment_ref=payment_ref,
            employer_submitted_utr=req.utr,
            status="awaiting_verification",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        _update_firestore_payment_status(req.hiring_request_id, "awaiting_verification")
        _notify(
            f"💰 UTR submitted — needs verification\n"
            f"Phone: {employer_phone}\n"
            f"Amount: ₹{req.amount:,}\n"
            f"UTR: {req.utr}\n"
            f"Payment ID: {payment.id}\n"
            f"Verify: https://api.relayy.world/admin/payments/pending?admin_key=..."
        )

        return JSONResponse(
            {"success": True},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            {"error": "Yeh UTR pehle se use ho chuka hai. Sahi UTR enter karein."},
            status_code=409,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    finally:
        db.close()


# ── Admin JSON endpoints ─────────────────────────────────────────────────────

@router.get("/admin/payments/list")
async def admin_list_payments(request: Request):
    if not _check_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        payments = (
            db.query(UPIPayment)
            .filter_by(status="awaiting_verification")
            .order_by(UPIPayment.created_at.asc())
            .all()
        )
        return JSONResponse({
            "payments": [
                {
                    "id": p.id,
                    "hiring_request_id": p.hiring_request_id,
                    "employer_phone": p.employer_phone,
                    "amount": p.amount,
                    "payment_ref": p.payment_ref,
                    "employer_submitted_utr": p.employer_submitted_utr,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in payments
            ]
        })
    finally:
        db.close()


@router.post("/admin/payments/{payment_id}/verify")
async def admin_verify_payment(payment_id: int, req: AdminVerifyRequest, request: Request):
    if not _check_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        payment = db.query(UPIPayment).filter_by(id=payment_id).first()
        if not payment:
            return JSONResponse({"error": "Not found"}, status_code=404)

        payment.status = "verified"
        payment.verified_at = time.time()
        payment.verified_by = req.verified_by or "admin"
        if req.notes:
            payment.notes = req.notes
        payment.updated_at = time.time()
        db.commit()

        _update_firestore_payment_status(payment.hiring_request_id, "verified")

        return JSONResponse({"success": True})
    finally:
        db.close()


@router.post("/admin/payments/{payment_id}/reject")
async def admin_reject_payment(payment_id: int, req: AdminRejectRequest, request: Request):
    if not _check_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        payment = db.query(UPIPayment).filter_by(id=payment_id).first()
        if not payment:
            return JSONResponse({"error": "Not found"}, status_code=404)

        payment.status = "failed"
        payment.notes = req.reason
        payment.updated_at = time.time()
        db.commit()

        _update_firestore_payment_status(payment.hiring_request_id, "failed")

        return JSONResponse({"success": True})
    finally:
        db.close()


@router.get("/admin/payments/export")
async def admin_export_csv(request: Request, admin_key: str = ""):
    key = request.headers.get("X-Admin-Key") or admin_key
    if key != ADMIN_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        payments = (
            db.query(UPIPayment)
            .filter(UPIPayment.status.in_(["awaiting_verification", "verified"]))
            .order_by(UPIPayment.created_at.desc())
            .all()
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Hiring Request ID", "Employer Phone", "Amount (₹)", "UTR", "Status", "Verified By", "Submitted At", "Verified At"])
        for p in payments:
            writer.writerow([
                p.id,
                p.hiring_request_id,
                p.employer_phone,
                p.amount,
                p.employer_submitted_utr or "",
                p.status,
                p.verified_by or "",
                time.strftime("%Y-%m-%d %H:%M", time.localtime(p.updated_at)) if p.updated_at else "",
                time.strftime("%Y-%m-%d %H:%M", time.localtime(p.verified_at)) if p.verified_at else "",
            ])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=switch_payments.csv"},
        )
    finally:
        db.close()


# ── Admin HTML page ──────────────────────────────────────────────────────────

_ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Switch — Payment Verification</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 24px; background: #f8f9fa; color: #1a1a1a; }
  h1 { margin: 0 0 4px; font-size: 22px; }
  .sub { color: #666; font-size: 13px; margin-bottom: 24px; }
  .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: gap; gap: 12px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; background: #fef3c7; color: #92400e; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
  th { background: #0A1F44; color: white; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; white-space: nowrap; }
  td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 13px; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #fafafa; }
  .utr { font-family: 'Courier New', monospace; font-size: 14px; letter-spacing: 1px; font-weight: 700; }
  .amount { font-weight: 700; color: #0A1F44; }
  .btn { display: inline-block; padding: 6px 14px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 700; transition: opacity .15s; }
  .btn:hover { opacity: .85; }
  .btn-verify { background: #10b981; color: white; margin-right: 6px; }
  .btn-reject { background: #ef4444; color: white; }
  .btn-export { background: #0A1F44; color: white; padding: 8px 18px; font-size: 14px; }
  .empty { text-align: center; padding: 48px 16px; color: #666; font-size: 15px; }
  .toast { position: fixed; bottom: 24px; right: 24px; background: #1f2937; color: white; padding: 12px 20px; border-radius: 10px; font-size: 14px; font-weight: 600; z-index: 9999; animation: slideIn .2s ease; }
  @keyframes slideIn { from { transform: translateY(12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  @media (max-width: 700px) { body { padding: 16px; } th, td { padding: 10px 10px; font-size: 12px; } }
</style>
</head>
<body>
<h1>💰 Payment Verification</h1>
<p class="sub">Switch employer UPI payments — manual UTR verification</p>
<div class="toolbar">
  <span id="count-label" class="badge">Loading…</span>
  <button class="btn btn-export" onclick="exportCSV()">⬇ Export CSV</button>
</div>
<div id="content"><p class="empty">Loading…</p></div>

<script>
const adminKey = new URLSearchParams(location.search).get('admin_key') || '';
const API = '/api/switch';

async function load() {
  try {
    const res = await fetch(API + '/admin/payments/list', { headers: { 'X-Admin-Key': adminKey } });
    const data = await res.json();
    if (!res.ok) { document.getElementById('content').innerHTML = '<p class="empty" style="color:red">' + (data.error || 'Unauthorized') + '</p>'; return; }
    render(data.payments || []);
  } catch(e) {
    document.getElementById('content').innerHTML = '<p class="empty" style="color:red">Failed to load: ' + e.message + '</p>';
  }
}

function render(payments) {
  document.getElementById('count-label').textContent = payments.length + ' pending';
  if (!payments.length) {
    document.getElementById('content').innerHTML = '<p class="empty">No pending payments — all clear 🎉</p>';
    return;
  }
  const rows = payments.map(p => {
    const date = new Date(p.updated_at * 1000).toLocaleString('en-IN', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' });
    const shortReqId = p.hiring_request_id.slice(0, 8) + '…';
    return '<tr id="row-' + p.id + '">'
      + '<td>' + p.id + '</td>'
      + '<td title="' + p.hiring_request_id + '">' + shortReqId + '</td>'
      + '<td>' + p.employer_phone + '</td>'
      + '<td class="amount">₹' + p.amount.toLocaleString('en-IN') + '</td>'
      + '<td class="utr">' + (p.employer_submitted_utr || '—') + '</td>'
      + '<td>' + date + '</td>'
      + '<td>'
      +   '<button class="btn btn-verify" onclick="verify(' + p.id + ')">✓ Verify</button>'
      +   '<button class="btn btn-reject" onclick="reject(' + p.id + ')">✗ Reject</button>'
      + '</td>'
      + '</tr>';
  }).join('');
  document.getElementById('content').innerHTML =
    '<table><thead><tr>'
    + '<th>ID</th><th>Request</th><th>Employer</th><th>Amount</th><th>UTR</th><th>Submitted</th><th>Actions</th>'
    + '</tr></thead><tbody>' + rows + '</tbody></table>';
}

async function verify(id) {
  const notes = prompt('Notes (optional — press OK to skip):');
  if (notes === null) return;
  const res = await fetch(API + '/admin/payments/' + id + '/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
    body: JSON.stringify({ notes: notes || null, verified_by: 'admin' }),
  });
  if (res.ok) { document.getElementById('row-' + id)?.remove(); updateCount(-1); toast('✓ Payment verified'); }
  else toast('Error verifying — try again');
}

async function reject(id) {
  const reason = prompt('Rejection reason:');
  if (!reason) return;
  const res = await fetch(API + '/admin/payments/' + id + '/reject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
    body: JSON.stringify({ reason }),
  });
  if (res.ok) { document.getElementById('row-' + id)?.remove(); updateCount(-1); toast('Payment rejected'); }
  else toast('Error rejecting — try again');
}

function exportCSV() {
  window.open(API + '/admin/payments/export?admin_key=' + encodeURIComponent(adminKey), '_blank');
}

function updateCount(delta) {
  const el = document.getElementById('count-label');
  const n = parseInt(el.textContent) + delta;
  el.textContent = n + ' pending';
  if (n === 0) document.getElementById('content').innerHTML = '<p class="empty">No pending payments — all clear 🎉</p>';
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast'; el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

load();
</script>
</body>
</html>"""


@pages_router.get("/admin/payments/pending")
async def admin_payments_page(admin_key: str = ""):
    if admin_key != ADMIN_API_KEY:
        return HTMLResponse("<h2 style='font-family:sans-serif;padding:32px'>401 Unauthorized — provide ?admin_key=</h2>", status_code=401)
    return HTMLResponse(_ADMIN_HTML)
