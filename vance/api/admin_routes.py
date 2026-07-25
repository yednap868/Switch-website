"""
Admin Dashboard Routes for Manual Profile Sending
Integrated into the main FastAPI application
"""

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from api.whatsapp_modules.conversation_history import conversation_history
from services.claude_profile_service import claude_profile_service
from utils.db import fs, get_extraction_data, get_user_profile
from utils.whatsapp.components import MsgComponents

# Import your existing modules
from utils.whatsapp.whatsapp import WhatsAppSender

# Create router
router = APIRouter(prefix="/admin", tags=["admin"])

# Templates directory
templates = Jinja2Templates(directory="templates")

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "vance2024")

# Session secret key
SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", secrets.token_hex(16))


# Dependency to check if user is logged in
async def get_current_admin(request: Request):
    if not request.session.get("logged_in"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return True


@router.get("/", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.post("/login")
async def admin_login(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    """Handle admin login using session + JSON response"""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["logged_in"] = True

        return JSONResponse({"success": True, "message": "Login successful"})

    return JSONResponse(
        {"success": False, "error": "Invalid credentials"}, status_code=401
    )


@router.get("/me")
async def admin_me(request: Request):
    return {"authenticated": bool(request.session.get("logged_in"))}


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_analytics_dashboard(
    request: Request, admin: bool = Depends(get_current_admin)
):
    """Analytics dashboard"""
    return templates.TemplateResponse("admin_analytics.html", {"request": request})


@router.get("/profiles", response_class=HTMLResponse)
async def admin_profile_sending(
    request: Request, admin: bool = Depends(get_current_admin)
):
    """Profile sending dashboard"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


@router.get("/messages", response_class=HTMLResponse)
async def admin_messages(request: Request, admin: bool = Depends(get_current_admin)):
    """Manual messaging dashboard"""
    return templates.TemplateResponse("admin_messages.html", {"request": request})


@router.get("/switch", response_class=HTMLResponse)
async def admin_switch_dashboard(request: Request, admin: bool = Depends(get_current_admin)):
    """Switch/Jyoti call analytics dashboard"""
    return templates.TemplateResponse("admin_switch.html", {"request": request})


@router.get("/employer-outbound", response_class=HTMLResponse)
async def admin_employer_outbound_dashboard(request: Request, admin: bool = Depends(get_current_admin)):
    """Employer outbound calling dashboard"""
    return templates.TemplateResponse("admin_employer_outbound.html", {"request": request})


# ---------------------------------------------------------------------------
# Order Manager — ops-head view over Switch hiring requests (orders)
# ---------------------------------------------------------------------------
ORDERS_COLLECTION = "switch_hiring_requests"

# Fields the ops head is allowed to edit on an order.
ORDER_EDITABLE_FIELDS = {
    "company", "role_label", "location", "when_needed", "notes",
    "status", "priority", "salary", "headcount",
    "order_value", "amount_collected", "payment_status",
    "assigned_worker_name", "assigned_worker_phone",
}

ORDER_STATUSES = ["placed", "open", "reviewing", "in_progress", "hired", "completed", "closed", "cancelled"]


def _to_number(val) -> float:
    """Coerce a possibly-string/None money field to a float, defaulting to 0."""
    if val is None or val == "":
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _interested_workers(order: dict) -> list:
    """Extract workers who raised their hand, with profile if enriched."""
    out = []
    for phone, info in (order.get("pinged_workers") or {}).items():
        if not isinstance(info, dict):
            continue
        if info.get("status") == "interested":
            profile = info.get("profile") or {}
            out.append({
                "phone":           phone,
                "name":            profile.get("name") or "",
                "location":        profile.get("location") or "",
                "experience":      profile.get("experience") or "",
                "expected_salary": profile.get("expected_salary") or "",
                "previous_company": profile.get("previous_company") or "",
                "responded_at":    info.get("responded_at") or "",
            })
    return out


def _shape_order(order: dict) -> dict:
    """Normalise a raw Firestore order doc into the manager's view model."""
    pinged = order.get("pinged_workers") or {}
    interested = _interested_workers(order)
    return {
        "id":               order.get("id", ""),
        "company":          order.get("company") or "",
        "role":             order.get("role") or "",
        "role_label":       order.get("role_label") or order.get("role") or "",
        "location":         order.get("location") or "",
        "headcount":        order.get("headcount") or 1,
        "salary":           order.get("salary") or "",
        "when_needed":      order.get("when_needed") or "",
        "notes":            order.get("notes") or "",
        "status":           order.get("status") or "open",
        "priority":         order.get("priority") or "normal",
        "employer_phone":   order.get("employer_phone") or "",
        "created_at":       order.get("created_at") or "",
        "workers_notified": order.get("workers_notified") or len(pinged),
        "interested_count": len(interested),
        "interested":       interested,
        # Ops-managed commercial fields
        "order_value":       _to_number(order.get("order_value")),
        "amount_collected":  _to_number(order.get("amount_collected")),
        "payment_status":    order.get("payment_status") or "unpaid",
        "assigned_worker_name":  order.get("assigned_worker_name") or "",
        "assigned_worker_phone": order.get("assigned_worker_phone") or "",
        "last_edited_by":   order.get("last_edited_by") or "",
        "last_edited_at":   order.get("last_edited_at") or "",
        # Placement / workflow provenance
        "source":           order.get("source") or "employer_app",
        "placed_by":        order.get("placed_by") or "",
    }


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request, admin: bool = Depends(get_current_admin)):
    """Order Manager dashboard — list, edit, and assign workers to orders."""
    return templates.TemplateResponse("admin_orders.html", {"request": request})


@router.get("/api/orders")
async def admin_orders_list(request: Request, admin: bool = Depends(get_current_admin)):
    """Return all orders (hiring requests) plus rolled-up stats for the ops head."""
    orders = []
    try:
        for doc in fs.collection(ORDERS_COLLECTION).stream():
            raw = doc.to_dict() or {}
            raw.setdefault("id", doc.id)
            orders.append(_shape_order(raw))
    except Exception as exc:
        return JSONResponse({"error": f"Failed to load orders: {exc}"}, status_code=500)

    orders.sort(key=lambda o: o.get("created_at") or "", reverse=True)

    active_statuses = {"placed", "open", "reviewing", "in_progress", "hired"}
    done_statuses = {"completed", "hired"}
    stats = {
        "total":            len(orders),
        "active":           sum(1 for o in orders if o["status"] in active_statuses),
        "awaiting_ops":     sum(1 for o in orders if o["status"] == "placed"),
        "completed":        sum(1 for o in orders if o["status"] == "completed"),
        "unassigned":       sum(1 for o in orders if not o["assigned_worker_phone"] and o["status"] in active_statuses),
        "total_value":      round(sum(o["order_value"] for o in orders), 2),
        "collected":        round(sum(o["amount_collected"] for o in orders), 2),
        "outstanding":      round(sum(max(o["order_value"] - o["amount_collected"], 0) for o in orders), 2),
        "interested_total": sum(o["interested_count"] for o in orders),
    }
    filled = sum(1 for o in orders if o["status"] in done_statuses)
    stats["fill_rate"] = round(100 * filled / len(orders), 1) if orders else 0.0

    return {"orders": orders, "stats": stats, "statuses": ORDER_STATUSES}


@router.post("/api/orders/{order_id}")
async def admin_order_update(order_id: str, request: Request, admin: bool = Depends(get_current_admin)):
    """Ops-head edit of a single order. Whitelisted fields only; writes an audit stamp."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    doc_ref = fs.collection(ORDERS_COLLECTION).document(order_id)
    snap = doc_ref.get()
    if not snap.exists:
        return JSONResponse({"error": "Order not found"}, status_code=404)

    updates = {}
    for key, value in body.items():
        if key not in ORDER_EDITABLE_FIELDS:
            continue
        if key in ("order_value", "amount_collected"):
            updates[key] = _to_number(value)
        elif key == "headcount":
            try:
                updates[key] = max(1, int(value))
            except (ValueError, TypeError):
                continue
        elif key == "status" and value not in ORDER_STATUSES:
            continue
        else:
            updates[key] = value

    if not updates:
        return JSONResponse({"error": "No editable fields supplied"}, status_code=400)

    updates["last_edited_by"] = ADMIN_USERNAME
    updates["last_edited_at"] = datetime.utcnow().isoformat() + "Z"

    try:
        doc_ref.set(updates, merge=True)
    except Exception as exc:
        return JSONResponse({"error": f"Failed to save: {exc}"}, status_code=500)

    fresh = doc_ref.get().to_dict() or {}
    fresh.setdefault("id", order_id)
    return {"success": True, "order": _shape_order(fresh)}


@router.post("/api/orders/create")
async def admin_order_create(request: Request, admin: bool = Depends(get_current_admin)):
    """Manager places a new order from the dashboard. Starts as 'placed' — awaiting an ops decision."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    company = (body.get("company") or "").strip()
    role = (body.get("role_label") or body.get("role") or "").strip()
    if not company or not role:
        return JSONResponse({"error": "Company and role are required"}, status_code=400)

    try:
        headcount = max(1, int(body.get("headcount") or 1))
    except (ValueError, TypeError):
        headcount = 1

    order_id = str(uuid.uuid4())
    order = {
        "id":               order_id,
        "company":          company,
        "role":             role,
        "role_label":       role,
        "location":         body.get("location") or "",
        "headcount":        headcount,
        "salary":           body.get("salary") or "",
        "when_needed":      body.get("when_needed") or "Immediately",
        "notes":            body.get("notes") or "",
        "order_value":      _to_number(body.get("order_value")),
        "amount_collected": 0.0,
        "payment_status":   "unpaid",
        "priority":         body.get("priority") or "normal",
        "status":           "placed",
        "employer_phone":   body.get("employer_phone") or "",
        "source":           "manager_dashboard",
        "placed_by":        ADMIN_USERNAME,
        "created_at":       datetime.utcnow().isoformat() + "Z",
        "pinged_workers":   {},
        "workers_notified": 0,
    }
    try:
        fs.collection(ORDERS_COLLECTION).document(order_id).set(order)
    except Exception as exc:
        return JSONResponse({"error": f"Failed to place order: {exc}"}, status_code=500)

    return {"success": True, "order": _shape_order(order)}


@router.post("/api/orders/{order_id}/assign")
async def admin_order_assign(order_id: str, request: Request, admin: bool = Depends(get_current_admin)):
    """Assign a worker to an order and move it to 'hired'."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    phone = (body.get("phone") or "").strip()
    name = (body.get("name") or "").strip()
    if not phone:
        return JSONResponse({"error": "phone is required"}, status_code=400)

    doc_ref = fs.collection(ORDERS_COLLECTION).document(order_id)
    if not doc_ref.get().exists:
        return JSONResponse({"error": "Order not found"}, status_code=404)

    updates = {
        "assigned_worker_phone": phone,
        "assigned_worker_name":  name,
        "status":                "hired",
        "last_edited_by":        ADMIN_USERNAME,
        "last_edited_at":        datetime.utcnow().isoformat() + "Z",
    }
    try:
        doc_ref.set(updates, merge=True)
    except Exception as exc:
        return JSONResponse({"error": f"Failed to assign: {exc}"}, status_code=500)

    fresh = doc_ref.get().to_dict() or {}
    fresh.setdefault("id", order_id)
    return {"success": True, "order": _shape_order(fresh)}


@router.get("/logout")
async def admin_logout(request: Request):
    """Logout and clear session"""
    try:
        # Clear the session
        request.session.clear()

        # Create a response that redirects to login page
        response = RedirectResponse(url="/admin/", status_code=303)

        # Clear any session cookies
        response.delete_cookie("session")

        # Add cache control headers to prevent caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response
    except Exception as e:
        print(f"❌ [LOGOUT] Error during logout: {e}")
        # Even if there's an error, redirect to login page
        return RedirectResponse(url="/admin/", status_code=303)


@router.post("/send-message")
async def send_manual_message(
    user_id: str = Form(...),
    message: str = Form(...),
    admin: bool = Depends(get_current_admin),
):
    """Send manual message to user by User ID"""
    try:
        user_id = user_id.strip()
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        # Validate user ID format (should be digits only, no + or spaces, country code + number)
        import re

        if not re.match(r"^\d{10,15}$", user_id):
            raise HTTPException(
                status_code=400,
                detail="User ID must be a valid WhatsApp number (10-15 digits, no + or spaces, e.g., 919876543210)",
            )

        if not message.strip():
            raise HTTPException(status_code=400, detail="Message is required")

        # Send message via WhatsApp
        success = send_message_to_whatsapp(user_id, message.strip())

        if success:
            # Log the admin-sent message to conversations for full context/audit
            try:
                conversation_history.save_message(
                    user_id,
                    "agent",
                    message,
                    message_type="text",
                    metadata={"source": "admin_manual", "channel": "whatsapp"},
                )
            except Exception as _hist_err:
                print(
                    f"⚠️ [ADMIN_HISTORY] Failed to save admin message to history: {_hist_err}"
                )

            # Invalidate analytics cache since we sent a message
            _invalidate_analytics_cache()

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Message sent successfully to user {user_id}",
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")

    except Exception as e:
        print(f"❌ [MANUAL_MESSAGE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.post("/send-profile")
async def send_profile(
    request: Request,
    admin: bool = Depends(get_current_admin),
    user_phone: str = Form(...),
    profiles: str = Form(...),  # JSON string of profiles
):
    """API endpoint to send manual profiles to users"""
    try:
        import json

        # Parse profiles JSON
        try:
            profiles_data = json.loads(profiles)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid profiles JSON")

        # Validation
        if not user_phone.strip():
            raise HTTPException(status_code=400, detail="User phone number is required")

        if not profiles_data:
            raise HTTPException(
                status_code=400, detail="At least one profile is required"
            )

        # Validate profile data
        for i, profile in enumerate(profiles_data):
            if not profile.get("name", "").strip():
                raise HTTPException(
                    status_code=400, detail=f"Profile {i+1}: Name is required"
                )
            if not profile.get("summary", "").strip():
                raise HTTPException(
                    status_code=400, detail=f"Profile {i+1}: Summary is required"
                )
            if not profile.get("linkedin_url", "").strip():
                raise HTTPException(
                    status_code=400, detail=f"Profile {i+1}: LinkedIn URL is required"
                )

        # Send profiles via WhatsApp
        success = send_profiles_to_whatsapp(user_phone, profiles_data)

        if success:
            # Store in Firebase using existing format
            store_manual_profiles_in_firebase(user_phone, profiles_data)

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Successfully sent {len(profiles_data)} profile(s) to {user_phone}",
                }
            )
        else:
            raise HTTPException(
                status_code=500, detail="Failed to send WhatsApp messages"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ADMIN] Error sending profiles: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/user-conversations/{user_id}")
async def get_user_conversations(
    user_id: str, admin: bool = Depends(get_current_admin)
):
    """Get conversation history for a specific user"""
    try:
        from api.whatsapp_modules.conversation_history import ConversationHistoryManager

        # Initialize conversation history manager
        history_manager = ConversationHistoryManager()

        # Get recent messages (last 50 messages)
        messages = history_manager.get_recent_messages(user_id, limit=50)

        # Format messages for display
        formatted_messages = []
        for msg in messages:
            formatted_messages.append(
                {
                    "timestamp": msg.get("timestamp", 0),
                    "formatted_time": datetime.fromtimestamp(
                        msg.get("timestamp", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "sender": msg.get("sender", "unknown"),
                    "content": msg.get("content", ""),
                    "type": msg.get("type", "text"),
                    "channel": msg.get("channel", "whatsapp"),
                }
            )

        # Sort by timestamp (oldest first)
        formatted_messages.sort(key=lambda x: x["timestamp"])

        return JSONResponse(
            {
                "success": True,
                "user_id": user_id,
                "messages": formatted_messages,
                "total_messages": len(formatted_messages),
            }
        )

    except Exception as e:
        print(f"❌ [ADMIN] Error retrieving conversations for {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving conversations: {str(e)}"
        )


@router.get("/user-search")
async def search_users_for_conversations(admin: bool = Depends(get_current_admin)):
    """Get list of users for conversation viewing"""
    try:
        # Get first 20 users with basic info
        users_ref = fs.collection("users")
        users_docs = list(users_ref.limit(20).stream())

        users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            users.append(
                {
                    "user_id": doc.id,
                    "name": user_data.get("name", ""),
                    "email": user_data.get("email", ""),
                    "phone": user_data.get("phone", ""),
                    "goal": user_data.get("goal", ""),
                    "created_at": user_data.get("created_at", 0),
                    "last_interaction": user_data.get("last_interaction", 0),
                }
            )

        return JSONResponse(
            {"success": True, "users": users, "total_users": len(users)}
        )

    except Exception as e:
        print(f"❌ [ADMIN] Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")


@router.get("/templates")
async def get_message_templates(admin: bool = Depends(get_current_admin)):
    """Get all message templates"""
    try:
        with open("config/profile_templates.json", "r") as f:
            templates_data = json.load(f)
        return JSONResponse({"success": True, "templates": templates_data})
    except Exception as e:
        print(f"❌ [TEMPLATES] Error loading templates: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/templates")
async def update_message_template(
    template_id: str = Form(...),
    template_name: str = Form(...),
    template_description: str = Form(...),
    template_content: str = Form(...),
    template_category: str = Form(...),
    admin: bool = Depends(get_current_admin),
):
    """Update or create a message template"""
    try:
        with open("config/profile_templates.json", "r") as f:
            templates_data = json.load(f)

        # Create new template
        new_template = {
            "id": template_id,
            "name": template_name,
            "description": template_description,
            "template": template_content,
            "category": template_category,
        }

        # Add to appropriate category
        if template_category not in templates_data:
            templates_data[template_category] = {}

        templates_data[template_category][template_id] = new_template

        # Save back to file
        with open("config/profile_templates.json", "w") as f:
            json.dump(templates_data, f, indent=2)

        return JSONResponse(
            {"success": True, "message": "Template updated successfully"}
        )

    except Exception as e:
        print(f"❌ [TEMPLATES] Error updating template: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/send-template-message")
async def send_template_message(
    request: Request,
    user_id: str = Form(...),
    template_id: str = Form(...),
    admin: bool = Depends(get_current_admin),
):
    """Send a template message to a user"""
    try:
        user_id = user_id.strip()
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        # Validate user ID format (should be digits only, no + or spaces, country code + number)
        import re

        if not re.match(r"^\d{10,15}$", user_id):
            raise HTTPException(
                status_code=400,
                detail="User ID must be a valid WhatsApp number (10-15 digits, no + or spaces, e.g., 919876543210)",
            )

        # Load templates
        with open("config/profile_templates.json", "r") as f:
            templates_data = json.load(f)

        # Find template
        template = None
        for category in templates_data.values():
            if template_id in category:
                template = category[template_id]
                break

        if not template:
            raise HTTPException(status_code=400, detail="Template not found")

        # Build WhatsApp TEMPLATE payload (Cloud API) with variables
        from utils.whatsapp.components import MsgComponents

        # Determine template name in WhatsApp and expected variables
        whatsapp_template_name = template.get("whatsapp_template_name", template_id)
        # Prefer variables defined on the template itself
        expected_vars = list(template.get("variables", []) or [])
        # if not expected_vars:
        #     # Backward-compatible fallback mapping by WhatsApp template name
        #     variable_map = {
        #         "follow_up": ["name"],
        #         "missing_name": ["name"],
        #         "missing_email": ["email"],
        #         "missing_linkedin": ["linkedin_url", "linkedin"],
        #         "missing_goal": ["primary_goal", "goal"],
        #     }
        #     expected_vars = variable_map.get(whatsapp_template_name, [])

        # Fetch user profile to populate variables
        body_params: list[str] = []
        try:
            user_doc = fs.collection("users").document(user_id).get()
            user_data = user_doc.to_dict() or {}
            profile = user_data.get("profile", {})
            # Convenience access from top level as fallback
            top = user_data
            for key in expected_vars:
                # Try profile then top-level
                value = profile.get(key) or top.get(key) or ""
                body_params.append(str(value) if value is not None else "")
        except Exception as _e:
            # If profile fetch fails, send empty params to avoid template mismatch
            body_params = [""] * len(expected_vars)

        # Collect admin overrides (form fields named var_<key>)
        try:
            form_data = await request.form()
        except Exception:
            form_data = {}
        overrides: dict[str, str] = {}
        for k, v in form_data.items() if hasattr(form_data, "items") else []:
            if isinstance(k, str) and k.startswith("var_"):
                overrides[k[4:]] = str(v)

        # Apply overrides to body params in order
        if expected_vars:
            body_params = [
                overrides.get(k, body_params[i] if i < len(body_params) else "")
                for i, k in enumerate(expected_vars)
            ]

        # Use named parameters when variable names are known (Cloud API requires parameter_name for named vars)
        named_params = []
        if expected_vars:
            for key, val in zip(expected_vars, body_params):
                named_params.append({"name": key, "value": val})

        payload = MsgComponents.template_scaffold(
            to=user_id,
            template_name=whatsapp_template_name,
            language_code="en",
            body_parameters=None if named_params else body_params,
            body_named_parameters=named_params or None,
        )

        # Send template using WhatsAppSender
        sender = WhatsAppSender()
        send_result = sender.send(payload)
        success = (
            isinstance(send_result, dict) and send_result.get("status") == "success"
        )

        if success:
            # Log the template message
            try:
                conversation_history.save_message(
                    user_id,
                    "agent",
                    template.get("template", ""),
                    message_type="template",
                    metadata={
                        "source": "admin_template",
                        "template_id": template_id,
                        "channel": "whatsapp",
                        "whatsapp_template_name": whatsapp_template_name,
                        "params": body_params,
                    },
                )
            except Exception as _hist_err:
                print(
                    f"⚠️ [TEMPLATE_HISTORY] Failed to save template message to history: {_hist_err}"
                )

            # Invalidate analytics cache since we sent a message
            _invalidate_analytics_cache()

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Template message sent successfully to user {user_id}",
                }
            )
        else:
            raise HTTPException(
                status_code=500, detail="Failed to send template message"
            )

    except Exception as e:
        print(f"❌ [TEMPLATE_MESSAGE] Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error sending template message: {str(e)}"
        )


@router.post("/send-bulk-template-messages")
async def send_bulk_template_messages(
    user_ids: List[str] = Form(...),
    template_id: str = Form(...),
    admin: bool = Depends(get_current_admin),
):
    """Send template messages to multiple users"""
    try:
        # Validate user IDs
        import re

        for user_id in user_ids:
            user_id = user_id.strip()
            if not user_id:
                raise HTTPException(status_code=400, detail="User ID cannot be empty")
            if not re.match(r"^\d{10,15}$", user_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"User ID '{user_id}' must be a valid WhatsApp number (10-15 digits, no + or spaces, e.g., 919876543210)",
                )

        # Load templates
        with open("config/profile_templates.json", "r") as f:
            templates_data = json.load(f)

        # Find template
        template = None
        for category in templates_data.values():
            if template_id in category:
                template = category[template_id]
                break

        if not template:
            raise HTTPException(status_code=400, detail="Template not found")

        results = []
        successful_count = 0

        for user_id in user_ids:
            try:
                success = send_message_to_whatsapp(user_id, template["template"])
                if success:
                    successful_count += 1
                    # Log the template message
                    try:
                        conversation_history.save_message(
                            user_id,
                            "agent",
                            template["template"],
                            message_type="text",
                            metadata={
                                "source": "admin_bulk_template",
                                "template_id": template_id,
                                "channel": "whatsapp",
                            },
                        )
                    except Exception as _hist_err:
                        print(
                            f"⚠️ [BULK_TEMPLATE_HISTORY] Failed to save template message to history for {user_id}: {_hist_err}"
                        )

                results.append(
                    {
                        "user_id": user_id,
                        "success": success,
                        "message": (
                            "Message sent successfully"
                            if success
                            else "Failed to send message"
                        ),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "user_id": user_id,
                        "success": False,
                        "message": f"Error: {str(e)}",
                    }
                )

        # Invalidate analytics cache since we sent messages
        if successful_count > 0:
            _invalidate_analytics_cache()

        return JSONResponse(
            {
                "success": True,
                "message": f"Bulk template messages sent. {successful_count}/{len(user_ids)} successful.",
                "results": results,
            }
        )

    except Exception as e:
        print(f"❌ [BULK_TEMPLATE_MESSAGE] Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error sending bulk template messages: {str(e)}"
        )


@router.post("/invalidate-cache")
async def invalidate_analytics_cache(admin: bool = Depends(get_current_admin)):
    """Manually invalidate analytics cache - useful for testing or when data changes"""
    try:
        _invalidate_analytics_cache()
        return JSONResponse(
            {"success": True, "message": "Analytics cache invalidated successfully"}
        )
    except Exception as e:
        print(f"❌ [CACHE_INVALIDATION] Error: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@router.get("/profile-completion-status")
async def get_profile_completion_status(admin: bool = Depends(get_current_admin)):
    """Get profile completion status for all users"""
    try:
        # Get all users from Firebase
        users_docs = fs.collection("users").stream()

        users_with_status = []

        for doc in users_docs:
            user_data = doc.to_dict()
            user_id = doc.id

            # Get profile data
            profile_data = user_data.get("profile", {})
            user_name = profile_data.get("name", "")
            user_email = profile_data.get("email", "")
            linkedin_url = profile_data.get("linkedin", "")
            primary_goal = profile_data.get("goal", "")

            # Check profile completion
            has_name = bool(user_name and user_name.strip())
            has_email = bool(user_email and user_email.strip())
            has_linkedin = bool(linkedin_url and linkedin_url.strip())
            has_goal = bool(primary_goal and primary_goal.strip())

            # Determine completion status
            missing_fields = []
            if not has_name:
                missing_fields.append("Name")
            if not has_email:
                missing_fields.append("Email")
            if not has_linkedin:
                missing_fields.append("LinkedIn")
            if not has_goal:
                missing_fields.append("Goal")

            is_profile_complete = len(missing_fields) == 0
            completion_status = (
                "Complete"
                if is_profile_complete
                else f"Missing: {', '.join(missing_fields)}"
            )

            # Check call status and count
            call_status = "No Call Yet"
            call_count = 0

            # Get call count from user_calls collection
            try:
                call_docs = (
                    fs.collection("user_calls")
                    .document(user_id)
                    .collection("calls")
                    .stream()
                )
                call_count = len(list(call_docs))

                if call_count > 0:
                    call_status = (
                        f"{call_count} Call{'s' if call_count > 1 else ''} Completed"
                    )
                else:
                    # Check if call was initiated but not completed
                    if user_data.get("arbitrary", {}).get("voice_call_initiated"):
                        call_status = "Call Initiated"
                        call_count = 0  # Initiated but not completed
            except Exception as e:
                print(f"⚠️ [CALL_COUNT] Error getting call count for {user_id}: {e}")
                # Fallback to basic call status check
                if user_data.get("arbitrary", {}).get("voice_call_initiated"):
                    call_status = "Call Initiated"

            users_with_status.append(
                {
                    "user_id": user_id,
                    "name": user_name or "N/A",
                    "email": user_email or "N/A",
                    "linkedin": linkedin_url or "N/A",
                    "goal": primary_goal or "N/A",
                    "profile_complete": is_profile_complete,
                    "completion_status": completion_status,
                    "missing_fields": missing_fields,
                    "call_status": call_status,
                    "call_count": call_count,
                    "created_at": user_data.get("created_at", 0),
                    "last_interaction": user_data.get("last_interaction", 0),
                }
            )

        return JSONResponse(
            {
                "success": True,
                "users": users_with_status,
                "total_users": len(users_with_status),
                "complete_profiles": len(
                    [u for u in users_with_status if u["profile_complete"]]
                ),
                "incomplete_profiles": len(
                    [u for u in users_with_status if not u["profile_complete"]]
                ),
            }
        )

    except Exception as e:
        print(f"❌ [PROFILE_STATUS] Error getting profile completion status: {e}")
        return JSONResponse({"success": False, "error": str(e)})


class ProfileMatch(BaseModel):
    name: str
    profile_summary: str
    linkedin_url: str
    match_reason: Optional[str] = None
    score: Optional[float] = None


class ProfileSuggestionResponse(BaseModel):
    user_id: str
    urgent_needs: str
    user_intent: str
    matches: List[ProfileMatch]
    total_matches: int


# Updated suggest_profiles_get endpoint in admin_routes.py


@router.get("/suggest-profiles/{user_id}", response_model=ProfileSuggestionResponse)
async def suggest_profiles_get(user_id: str):
    """
    GET endpoint for profile suggestions based on complete user extraction data.

    Args:
        user_id: User ID from path parameter

    Returns:
        ProfileSuggestionResponse with matched profiles from Qdrant
    """
    try:
        uid = user_id

        # Validate user_id
        if not uid or uid == "default" or len(uid) < 5:
            raise HTTPException(status_code=400, detail="Invalid user_id")

        print(f"🔍 [PROFILE_SUGGESTION] Processing suggestion request for user {uid}")

        # Get user profile and extraction data
        user_profile = get_user_profile(uid)
        extraction_data = get_extraction_data(uid)

        if not extraction_data:
            raise HTTPException(
                status_code=404,
                detail="No extraction data found for user. User must complete a voice call first.",
            )

        # Use ALL extraction data dynamically (don't hardcode any keys)
        if isinstance(extraction_data, dict):
            # Take the entire extraction data as user context
            user_context = extraction_data.copy()
        else:
            # Fallback if extraction_data is not a dict
            user_context = {"data": str(extraction_data) if extraction_data else ""}

        if not user_context or len(user_context) == 0:
            raise HTTPException(
                status_code=404, detail="No extraction data fields found for user"
            )

        print(
            f"🎯 [EXTRACTION_DATA] User {uid} context fields: {list(user_context.keys())}"
        )

        # Classify user intent using Claude AI
        from services.claude_profile_service import claude_profile_service

        user_intent = claude_profile_service.classify_intent(
            user_profile.get("goal", "") if user_profile else ""
        )

        print(f"🤖 [CLAUDE] Classified intent as: {user_intent}")

        # Get profile summary if available
        profile_summary = ""
        if user_profile:
            profile_summary = user_profile.get("summary", "")

        # If no profile summary, create one from extraction data dynamically
        if not profile_summary:
            # Combine relevant fields from extraction data (prioritize key narrative fields)
            summary_keys = [
                "the_story",
                "current_focus",
                "challenges",
                "goals",
                "background",
                "description",
            ]
            summary_parts = []
            for key in summary_keys:
                if key in user_context and user_context[key]:
                    summary_parts.append(str(user_context[key]))
            profile_summary = " ".join(summary_parts).strip()

        # Get LinkedIn URL
        linkedin_url = ""
        if user_profile:
            linkedin_data = user_profile.get("linkedin", "")
            if isinstance(linkedin_data, dict):
                linkedin_url = linkedin_data.get("linkedin_url", "")
            elif isinstance(linkedin_data, str):
                linkedin_url = linkedin_data
            else:
                linkedin_url = user_profile.get("linkedin_url", "")

        # Search for matches using Claude-powered intelligent matching with full context
        matches = await _search_profiles_with_complete_context(
            user_context=user_context,
            profile_summary=profile_summary if profile_summary else None,
            user_intent=user_intent,
            self_linkedin_url=linkedin_url,
            limit=3,
            user_id=uid,
        )

        if not matches:
            print(f"⚠️ [NO_MATCHES] No matching profiles found for user {uid}")

            # Get summary for response
            extraction_summary = ""
            summary_fields = [
                "description",
                "summary",
                "the_story",
                "current_focus",
                "goals",
                "challenges",
            ]
            for field in summary_fields:
                if field in user_context and user_context[field]:
                    extraction_summary = str(user_context[field])[:200]
                    break

            return ProfileSuggestionResponse(
                user_id=uid,
                urgent_needs=extraction_summary,
                user_intent=user_intent,
                matches=[],
                total_matches=0,
            )

        # Format matches for response
        formatted_matches = []
        for match in matches:
            # Handle both dict and object formats
            if isinstance(match, dict):
                formatted_match = ProfileMatch(
                    name=match.get("name", "Unknown"),
                    email=match.get("email", ""),
                    profile_summary=match.get("profile_summary", ""),
                    linkedin_url=match.get("linkedin_url", ""),
                    match_reason=match.get("match_reason", ""),
                    score=match.get("score", None),
                )
            else:
                formatted_match = ProfileMatch(
                    name=match.name,
                    email=match.email,
                    profile_summary=match.profile_summary,
                    linkedin_url=match.linkedin_url,
                    match_reason=getattr(match, "match_reason", ""),
                    score=getattr(match, "score", None),
                )

            formatted_matches.append(formatted_match)

        print(f"✅ [SUCCESS] Found {len(formatted_matches)} matches for user {uid}")

        # Get a summary of extraction data for response (first available descriptive field)
        extraction_summary = ""
        summary_fields = [
            "description",
            "summary",
            "the_story",
            "current_focus",
            "goals",
            "challenges",
        ]
        for field in summary_fields:
            if field in user_context and user_context[field]:
                extraction_summary = str(user_context[field])[:200]
                break

        return ProfileSuggestionResponse(
            user_id=uid,
            urgent_needs=extraction_summary,  # Use summary from extraction data
            user_intent=user_intent,
            matches=formatted_matches,
            total_matches=len(formatted_matches),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ERROR] Error in suggest_profiles for user {uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _search_profiles_with_complete_context(
    user_context: dict,
    profile_summary: str,
    user_intent: str,
    self_linkedin_url: str,
    limit: int = 3,
    user_id: str = None,
):
    """
    Search for profiles using Claude AI with complete user context for intelligent matching.
    """
    try:
        print(
            f"🤖 [CLAUDE] Starting intelligent profile search with full context for intent: {user_intent}"
        )

        # Step 1: Get available profiles from database (pre-filtered by complementary intents)
        available_profiles = await _get_available_profiles_for_matching(
            self_linkedin_url=self_linkedin_url,
            user_id=user_id,
            user_intent=user_intent,
        )

        if not available_profiles:
            print("⚠️ [CLAUDE] No available profiles for matching")
            return []

        print(f"📊 [CLAUDE] Found {len(available_profiles)} available profiles")

        # Step 2: Use Claude to find intelligent matches with complete context
        from services.claude_profile_service import claude_profile_service

        try:
            profile_matches = claude_profile_service.find_profile_matches_with_context(
                user_intent=user_intent,
                user_context=user_context,  # Pass complete context
                available_profiles=available_profiles,
                user_profile_summary=profile_summary,
                limit=limit,
            )

            # Convert ProfileMatch objects to the expected format
            matches = []
            for match in profile_matches:
                matches.append(
                    {
                        "uid": match.uid,
                        "name": match.name,
                        "email": match.email,
                        "profile_summary": match.profile_summary,
                        "urgent_needs": match.urgent_needs,
                        "linkedin_url": match.linkedin_url,
                        "source": match.source,
                        "compatibility_score": match.compatibility_score,
                        "match_reason": match.match_reason,
                    }
                )

            if matches:
                print(f"✅ [CLAUDE] Found {len(matches)} intelligent matches")
                return matches

        except Exception as claude_error:
            print(f"❌ [CLAUDE] Claude matching failed: {claude_error}")
            return []

    except Exception as e:
        print(f"❌ [CLAUDE] Profile search failed: {e}")
        return []


async def _search_profiles_with_claude(
    urgent_needs: str,
    profile_summary: str,
    user_intent: str,
    self_linkedin_url: str,
    limit: int = 3,
    user_id: str = None,
):
    """
    Search for profiles using Claude AI for intelligent matching.
    """
    try:
        print(
            f"🤖 [CLAUDE] Starting intelligent profile search for intent: {user_intent}"
        )

        # Step 1: Get available profiles from database (pre-filtered by complementary intents)
        available_profiles = await _get_available_profiles_for_matching(
            self_linkedin_url=self_linkedin_url,
            user_id=user_id,
            user_intent=user_intent,
        )

        if not available_profiles:
            print("⚠️ [CLAUDE] No available profiles for matching")
            return []

        print(f"📊 [CLAUDE] Found {len(available_profiles)} available profiles")

        # Step 2: Use Claude to find intelligent matches
        from services.claude_profile_service import claude_profile_service

        try:
            profile_matches = claude_profile_service.find_profile_matches(
                user_intent=user_intent,
                user_urgent_needs=urgent_needs,
                available_profiles=available_profiles,
                user_profile_summary=profile_summary,
                limit=limit,
            )

            # Convert ProfileMatch objects to the expected format
            matches = []
            for match in profile_matches:
                matches.append(
                    {
                        "uid": match.uid,
                        "name": match.name,
                        "email": match.email,
                        "profile_summary": match.profile_summary,
                        "urgent_needs": match.urgent_needs,
                        "linkedin_url": match.linkedin_url,
                        "source": match.source,
                        "compatibility_score": match.compatibility_score,
                        "match_reason": match.match_reason,
                    }
                )

            if matches:
                print(f"✅ [CLAUDE] Found {len(matches)} intelligent matches")
                return matches

        except Exception as claude_error:
            print(f"❌ [CLAUDE] Claude matching failed: {claude_error}")
            # Return empty list instead of falling back to semantic search
            # Claude should be the primary intelligence for business matching
            return []

    except Exception as e:
        print(f"❌ [CLAUDE] Profile search failed: {e}")
        return []


async def _get_available_profiles_for_matching(
    self_linkedin_url: str, user_id: str = None, user_intent: str = None
):
    """
    Get available profiles for Claude to match against, filtered by complementary intents.
    """
    try:
        # Simple intent matching - job providers match with job seekers and vice versa
        complementary_intents = []
        if user_intent:
            if "job_provider" in user_intent or "hiring" in user_intent.lower():
                complementary_intents = ["job_seeker", "looking_for_job"]
            elif "job_seeker" in user_intent or "job" in user_intent.lower():
                complementary_intents = ["job_provider", "hiring"]
        print(
            f"🔍 [FILTER] Filtering by complementary intents for '{user_intent}': {complementary_intents}"
        )

        # Get profiles from database (limit to prevent token overflow)
        from utils.db import fs

        # Query user_profiles collection with intent filtering
        profiles_ref = fs.collection("user_profiles")
        if complementary_intents:
            # Filter Firestore profiles by complementary intents - increase limit for Claude
            profiles_docs = []
            for intent in complementary_intents:
                intent_docs = (
                    profiles_ref.where("intent", "==", intent).limit(100).stream()
                )
                profiles_docs.extend(list(intent_docs))
        else:
            profiles_docs = profiles_ref.limit(
                200
            ).stream()  # Increased limit for Claude processing

        # Also get profiles from Qdrant UserProfiles collection with retry logic
        from qdrant_client.http import models

        from utils.qdrant import qdrant_client

        qdrant_profiles = []
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                if complementary_intents:
                    # Filter Qdrant profiles by complementary intents using index
                    intent_filter = models.Filter(
                        should=[
                            models.FieldCondition(
                                key="intent", match=models.MatchValue(value=intent)
                            )
                            for intent in complementary_intents
                        ]
                    )
                    qdrant_result = qdrant_client.scroll(
                        collection_name="UserProfiles",
                        scroll_filter=intent_filter,
                        limit=100,
                        with_payload=True,
                    )
                else:
                    qdrant_result = qdrant_client.scroll(
                        collection_name="UserProfiles", limit=200, with_payload=True
                    )
                qdrant_profiles = qdrant_result[0]
                print(
                    f"📊 [QDRANT] Found {len(qdrant_profiles)} filtered profiles in Qdrant UserProfiles collection"
                )
                break  # Success, exit retry loop
            except Exception as e:
                print(
                    f"⚠️ [QDRANT] Error fetching from Qdrant (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                else:
                    print(
                        f"❌ [QDRANT] Failed to fetch from Qdrant after {max_retries} attempts, continuing with Firestore only"
                    )

        available_profiles = []
        excluded_uids = set()

        # Exclude previously suggested profiles
        if user_id:
            previously_suggested = await _get_previously_suggested_profile_uids(user_id)
            excluded_uids.update(previously_suggested)

        # Process Firestore profiles
        for doc in profiles_docs:
            profile_data = doc.to_dict()
            profile_uid = doc.id

            # Skip excluded profiles
            if profile_uid in excluded_uids:
                continue

            # Skip self-profile
            if profile_data.get("linkedin_url") == self_linkedin_url:
                continue

            # Format for Claude
            profile = {
                "uid": profile_uid,
                "name": profile_data.get("name", "Unknown"),
                "urgent_needs": profile_data.get("urgent_needs", ""),
                "profile_summary": f"{profile_data.get('name', '')} {profile_data.get('urgent_needs', '')}",
                "intent": profile_data.get("intent", "general"),
                "email": profile_data.get("email", ""),
                "linkedin_url": profile_data.get("linkedin_url", ""),
            }

            available_profiles.append(profile)

        # Process Qdrant profiles
        for point in qdrant_profiles:
            profile_data = point.payload
            profile_uid = f"qdrant_{point.id}"

            # Skip excluded profiles
            if profile_uid in excluded_uids:
                continue

            # Skip self-profile
            if profile_data.get("linkedin_url") == self_linkedin_url:
                continue

            # Format for Claude
            profile = {
                "uid": profile_uid,
                "name": profile_data.get("name", "Unknown"),
                "urgent_needs": profile_data.get("urgent_needs", ""),
                "profile_summary": profile_data.get("document", ""),
                "intent": profile_data.get("intent", "general"),
                "email": profile_data.get("email", ""),
                "linkedin_url": profile_data.get("linkedin_url", ""),
            }

            available_profiles.append(profile)

        return available_profiles

    except Exception as e:
        print(f"❌ [CLAUDE] Failed to get available profiles: {e}")
        return []


async def _get_previously_suggested_profile_uids(uid: str) -> set:
    """
    Get set of profile UIDs that have already been suggested to this user.
    """
    try:
        from utils.db import fs

        doc_ref = fs.collection("suggested_profiles").document(uid)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            profiles = data.get("profiles", [])
            suggested_uids = {
                profile.get("uid") for profile in profiles if profile.get("uid")
            }
            print(
                f"📋 [DEDUP] Found {len(suggested_uids)} previously suggested profiles for user {uid}"
            )
            return suggested_uids
        else:
            print(f"📋 [DEDUP] No previously suggested profiles found for user {uid}")
            return set()

    except Exception as e:
        print(f"❌ [DEDUP] Error retrieving previously suggested profiles: {e}")
        return set()


def send_message_to_whatsapp(user_id: str, message: str) -> bool:
    """Send manual message to user via WhatsApp"""
    try:
        sender = WhatsAppSender()

        # Send the custom message
        msg_data = MsgComponents.text_scaffold(to=user_id, text=message)
        result = sender.send(msg_data)

        # WhatsAppSender.send now returns a dict with 'status' key
        if isinstance(result, dict) and result.get("status") == "success":
            message_id = result.get("message_id")
            print(
                f"✅ [MANUAL_MESSAGE] Message sent successfully to {user_id}, ID: {message_id}"
            )
            return True
        else:
            error_msg = (
                result.get("error", "Unknown error")
                if isinstance(result, dict)
                else str(result)
            )
            print(
                f"❌ [MANUAL_MESSAGE] Failed to send message to {user_id}: {error_msg}"
            )
            return False

    except Exception as e:
        print(f"❌ [MANUAL_MESSAGE] Error sending message to {user_id}: {e}")
        return False


def send_profiles_to_whatsapp(user_phone: str, profiles: list) -> bool:
    """Send profiles to user via WhatsApp using existing format"""
    try:
        sender = WhatsAppSender()

        # Format messages exactly like existing system
        messages = ["Here are some profiles that match your goals:"]

        for i, profile in enumerate(profiles, 1):
            name = profile.get("name", "Unknown").strip()
            summary = profile.get("summary", "").strip()
            linkedin_url = profile.get("linkedin_url", "").strip()
            match_reason = profile.get("match_reason", "").strip()

            # Format name properly (capitalize first letter of each word)
            name = " ".join(word.capitalize() for word in name.split())

            # Truncate summary for WhatsApp (same as existing system)
            about = summary[:200] + "..." if len(summary) > 200 else summary

            # Format message exactly like existing system
            if match_reason:
                # Extract one line reason from match_reason
                reason_lines = match_reason.split(".")
                short_reason = (
                    reason_lines[0].strip() if reason_lines else match_reason[:100]
                )
                message = f"{i}. {name}\n\nSummary\n{about}\n\nLinkedIn Url\n{linkedin_url}\n\nWhy This Match\n{short_reason}"
            else:
                message = (
                    f"{i}. {name}\n\nSummary\n{about}\n\nLinkedIn Url\n{linkedin_url}"
                )

            messages.append(message)

        messages.append(
            "\nLet me know who you'd like to connect with! You can mention their name or say 'connect with all' to connect with everyone."
        )

        # Send each message
        for message in messages:
            try:
                msg_data = MsgComponents.text_scaffold(to=user_phone, text=message)
                result = sender.send(msg_data)

                if not isinstance(result, dict) or result.get("status") != "success":
                    error_msg = (
                        result.get("error", "Unknown error")
                        if isinstance(result, dict)
                        else str(result)
                    )
                    print(f"❌ [WHATSAPP] Failed to send message: {error_msg}")
                    return False

            except Exception as e:
                print(f"❌ [WHATSAPP] Error sending message: {e}")
                return False

        # State is now managed by the agent system
        print(f"✅ [ADMIN] Profiles sent to user {user_phone}")

        return True

    except Exception as e:
        print(f"❌ [WHATSAPP] Error in send_profiles_to_whatsapp: {e}")
        return False


def store_manual_profiles_in_firebase(user_id: str, profiles: list):
    """Store manually sent profiles in Firebase using existing format"""
    try:
        # Format profiles exactly like existing system
        profiles_data = []
        for profile in profiles:
            profiles_data.append(
                {
                    "uid": f"manual_{int(time.time())}_{len(profiles_data)}",  # Generate unique ID for manual profiles
                    "name": profile.get("name", "").strip(),
                    "email": profile.get("email", "").strip(),  # Optional field
                    "profile_summary": profile.get("summary", "").strip(),
                    "linkedin_url": profile.get("linkedin_url", "").strip(),
                    "match_reason": profile.get(
                        "match_reason", ""
                    ).strip(),  # Additional field for manual profiles
                    "source": "manual_admin",  # Mark as manually added
                    "suggested_at": time.time(),
                }
            )

        # Store in Firestore using existing collection structure
        fs.collection("suggested_profiles").document(user_id).set(
            {
                "profiles": profiles_data,
                "created_at": time.time(),
                "source": "manual_admin",
            }
        )

        print(
            f"✅ [FIREBASE] Stored {len(profiles)} manual profiles for user {user_id}"
        )

    except Exception as e:
        print(f"❌ [FIREBASE] Error storing manual profiles: {e}")


@router.get("/test-users")
async def test_users(admin: bool = Depends(get_current_admin)):
    """Test users collection directly"""
    try:
        # Get first 3 users
        users_ref = fs.collection("users")
        users_docs = list(users_ref.limit(3).stream())

        result = {"total_users": len(users_docs), "sample_users": []}

        for doc in users_docs:
            user_data = doc.to_dict()
            result["sample_users"].append(
                {
                    "id": doc.id,
                    "name": user_data.get("name", ""),
                    "email": user_data.get("email", ""),
                    "goal": user_data.get("goal", ""),
                    "linkedin": user_data.get("linkedin", ""),
                    "created_at": user_data.get("created_at", 0),
                    "has_complete_profile": bool(
                        user_data.get("name", "").strip()
                        and user_data.get("email", "").strip()
                        and user_data.get("linkedin", "").strip()
                        and user_data.get("goal", "").strip()
                        and user_data.get("goal", "") != "unknown"
                    ),
                }
            )

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"error": str(e)})


@router.get("/debug-user/{user_id}")
async def debug_user(user_id: str, admin: bool = Depends(get_current_admin)):
    """Debug specific user data"""
    try:
        # Get user data
        user_doc = fs.collection("users").document(user_id).get()
        if not user_doc.exists:
            return JSONResponse({"error": "User not found"})

        user_data = user_doc.to_dict()

        # Check profile completion
        user_name = user_data.get("name", "")
        user_email = user_data.get("email", "")
        linkedin = user_data.get("linkedin", "")
        goal = user_data.get("goal", "")

        has_name = bool(user_name and user_name.strip())
        has_email = bool(user_email and user_email.strip())
        has_linkedin = bool(linkedin and linkedin.strip())
        has_goal = bool(goal and goal.strip() and goal != "unknown")

        is_profile_complete = has_name and has_email and has_linkedin and has_goal

        return JSONResponse(
            {
                "user_id": user_id,
                "raw_data": user_data,
                "profile_check": {
                    "name": user_name,
                    "email": user_email,
                    "linkedin": linkedin,
                    "goal": goal,
                    "has_name": has_name,
                    "has_email": has_email,
                    "has_linkedin": has_linkedin,
                    "has_goal": has_goal,
                    "is_complete": is_profile_complete,
                },
            }
        )

    except Exception as e:
        return JSONResponse({"error": str(e)})


@router.get("/test-firebase")
async def test_firebase(admin: bool = Depends(get_current_admin)):
    """Test Firebase connection and data"""
    try:
        # Test basic Firebase connection
        users_ref = fs.collection("users")
        users_docs = list(users_ref.limit(3).stream())

        result = {
            "firebase_connected": True,
            "users_count": len(users_docs),
            "sample_users": [],
        }

        for doc in users_docs[:3]:
            user_data = doc.to_dict()
            result["sample_users"].append(
                {
                    "id": doc.id,
                    "keys": list(user_data.keys()),
                    "has_profile": "profile" in user_data,
                    "profile_keys": (
                        list(user_data.get("profile", {}).keys())
                        if "profile" in user_data
                        else []
                    ),
                }
            )

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"firebase_connected": False, "error": str(e)})


@router.get("/debug-onboarding")
async def debug_onboarding(admin: bool = Depends(get_current_admin)):
    """Debug onboarding calculation"""
    try:
        from datetime import datetime, timedelta

        # Get today and yesterday timestamps
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        today_timestamp = today.timestamp()
        yesterday_timestamp = yesterday.timestamp()

        # Get first 5 users
        users_ref = fs.collection("users")
        users_docs = list(users_ref.limit(5).stream())

        result = {
            "today": str(today),
            "yesterday": str(yesterday),
            "today_timestamp": today_timestamp,
            "yesterday_timestamp": yesterday_timestamp,
            "users": [],
        }

        for doc in users_docs:
            user_data = doc.to_dict()
            user_id = doc.id

            # Get user data
            user_name = user_data.get("name", "")
            user_email = user_data.get("email", "")
            need = user_data.get("goal", "unknown")
            created_at = user_data.get("created_at", 0)

            # Check profile completion
            has_name = bool(user_name and user_name.strip())
            has_email = bool(user_email and user_email.strip())
            has_goal = bool(need and need.strip() and need != "unknown")
            is_profile_complete = has_name and has_email and has_goal

            # Check date
            created_date = (
                datetime.fromtimestamp(created_at) if created_at > 0 else None
            )
            is_today = created_at >= today_timestamp if created_at > 0 else False
            is_yesterday = (
                created_at >= yesterday_timestamp and created_at < today_timestamp
                if created_at > 0
                else False
            )

            result["users"].append(
                {
                    "id": user_id,
                    "name": user_name,
                    "email": user_email,
                    "goal": need,
                    "created_at": created_at,
                    "created_date": str(created_date) if created_date else None,
                    "has_name": has_name,
                    "has_email": has_email,
                    "has_goal": has_goal,
                    "is_profile_complete": is_profile_complete,
                    "is_today": is_today,
                    "is_yesterday": is_yesterday,
                    "should_count_today": is_profile_complete and is_today,
                    "should_count_yesterday": is_profile_complete and is_yesterday,
                }
            )

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"error": str(e)})


@router.get("/debug-timestamps")
async def debug_timestamps(admin: bool = Depends(get_current_admin)):
    """Debug timestamp values for users created today"""
    try:
        from datetime import datetime, timedelta

        # Get today and yesterday timestamps
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        today_timestamp = today.timestamp()
        yesterday_timestamp = yesterday.timestamp()

        # Get users created today
        users_ref = fs.collection("users")
        users_docs = list(users_ref.stream())

        result = {
            "today": str(today),
            "yesterday": str(yesterday),
            "today_timestamp": today_timestamp,
            "yesterday_timestamp": yesterday_timestamp,
            "users_created_today": [],
        }

        for doc in users_docs:
            user_data = doc.to_dict()
            user_id = doc.id
            created_at = user_data.get("created_at", 0)

            if created_at > 0:
                created_date = datetime.fromtimestamp(created_at)
                # Check if created today
                if created_date.date() == today.date():
                    user_name = user_data.get("name", "")
                    user_email = user_data.get("email", "")
                    need = user_data.get("goal", "unknown")

                    has_name = bool(user_name and user_name.strip())
                    has_email = bool(user_email and user_email.strip())
                    has_goal = bool(need and need.strip() and need != "unknown")
                    is_profile_complete = has_name and has_email and has_goal

                    result["users_created_today"].append(
                        {
                            "id": user_id,
                            "name": user_name,
                            "email": user_email,
                            "goal": need,
                            "created_at": created_at,
                            "created_date": str(created_date),
                            "is_profile_complete": is_profile_complete,
                            "should_count_today": is_profile_complete
                            and created_at >= today_timestamp,
                        }
                    )

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"error": str(e)})


# Redis-based persistent cache for analytics data
try:
    from utils.redis_client import redis_cache

    REDIS_AVAILABLE = True
    print("✅ [CACHE] Redis available for analytics caching")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️ [CACHE] Redis not available for analytics caching: {e}")

# Fallback in-memory cache
_analytics_cache = {}
_cache_duration = 300  # Cache for 5 minutes (increased from 1 minute)


def _get_cache_key():
    """Get cache key for analytics data."""
    return "admin:analytics:data"


def _get_cache_timestamp_key():
    """Get cache key for analytics timestamp."""
    return "admin:analytics:timestamp"


def _get_user_count_key():
    """Get cache key for user count (for invalidation)."""
    return "admin:analytics:user_count"


def _get_last_interaction_key():
    """Get cache key for last interaction timestamp."""
    return "admin:analytics:last_interaction"


def _is_cache_valid():
    """Check if analytics cache is still valid using Redis or fallback."""
    if REDIS_AVAILABLE:
        try:
            # Check if we have cached data
            cached_data = redis_cache.get(_get_cache_key())
            if not cached_data:
                return False

            # Check if cache is still fresh (5 minutes)
            timestamp = redis_cache.get(_get_cache_timestamp_key(), int)
            if not timestamp:
                return False

            return time.time() < timestamp + _cache_duration
        except Exception as e:
            print(f"⚠️ [CACHE] Error checking Redis cache validity: {e}")
            return False
    else:
        # Fallback to in-memory cache
        if "timestamp" not in _analytics_cache:
            return False
        return time.time() < _analytics_cache["timestamp"] + _cache_duration


def _get_cached_analytics():
    """Get cached analytics data if valid."""
    if REDIS_AVAILABLE:
        try:
            if _is_cache_valid():
                cached_data = redis_cache.get(_get_cache_key())
                if cached_data:
                    print("🚀 [CACHE] Using Redis cached analytics data")
                    return cached_data
        except Exception as e:
            print(f"⚠️ [CACHE] Error getting Redis cached data: {e}")

    # Fallback to in-memory cache
    if _is_cache_valid():
        print("🚀 [CACHE] Using in-memory cached data")
        return _analytics_cache.get("data")
    return None


def _cache_analytics_data(data):
    """Cache analytics data using Redis or fallback."""
    current_time = time.time()

    if REDIS_AVAILABLE:
        try:
            # Cache data for 5 minutes
            redis_cache.set(_get_cache_key(), data, ttl_seconds=_cache_duration)
            redis_cache.set(
                _get_cache_timestamp_key(),
                int(current_time),
                ttl_seconds=_cache_duration,
            )
            print("💾 [CACHE] Analytics data cached in Redis")
        except Exception as e:
            print(f"⚠️ [CACHE] Error caching in Redis: {e}")
            # Fallback to in-memory
            _analytics_cache["data"] = data
            _analytics_cache["timestamp"] = current_time
            print("💾 [CACHE] Analytics data cached in memory (Redis fallback)")
    else:
        # Fallback to in-memory cache
        _analytics_cache["data"] = data
        _analytics_cache["timestamp"] = current_time
        print("💾 [CACHE] Analytics data cached in memory")


def _invalidate_analytics_cache():
    """Invalidate analytics cache when data changes."""
    if REDIS_AVAILABLE:
        try:
            redis_cache.delete(_get_cache_key())
            redis_cache.delete(_get_cache_timestamp_key())
            print("🗑️ [CACHE] Analytics cache invalidated in Redis")
        except Exception as e:
            print(f"⚠️ [CACHE] Error invalidating Redis cache: {e}")

    # Also clear in-memory cache
    _analytics_cache.clear()
    print("🗑️ [CACHE] Analytics cache invalidated in memory")


def _should_refresh_cache():
    """Check if cache should be refreshed based on data changes."""
    if not REDIS_AVAILABLE:
        return not _is_cache_valid()

    try:
        # Get current user count from Firebase
        users_docs = fs.collection("users").stream()
        current_user_count = len(list(users_docs))

        # Get cached user count
        cached_user_count = redis_cache.get(_get_user_count_key(), int)

        # If user count changed, refresh cache
        if cached_user_count is None or cached_user_count != current_user_count:
            print(
                f"🔄 [CACHE] User count changed ({cached_user_count} -> {current_user_count}), refreshing cache"
            )
            redis_cache.set(
                _get_user_count_key(), current_user_count, ttl_seconds=3600
            )  # Cache for 1 hour
            return True

        # Check if cache is still valid
        return not _is_cache_valid()

    except Exception as e:
        print(f"⚠️ [CACHE] Error checking cache refresh need: {e}")
        return not _is_cache_valid()


@router.get("/analytics-data")
async def get_analytics_data(admin: bool = Depends(get_current_admin)):
    """Get analytics data for dashboard - optimized version with caching"""
    try:
        # Check if we should refresh cache
        if not _should_refresh_cache():
            # Use cached data
            cached_data = _get_cached_analytics()
            if cached_data:
                return JSONResponse(cached_data)

        print("🔄 [ANALYTICS] Refreshing analytics data from Firebase")
        # Get today and yesterday timestamps
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        today_timestamp = today.timestamp()
        yesterday_timestamp = yesterday.timestamp()

        print(f"🔍 [ANALYTICS] Today: {today} (timestamp: {today_timestamp})")
        print(
            f"🔍 [ANALYTICS] Yesterday: {yesterday} (timestamp: {yesterday_timestamp})"
        )

        # Initialize stats
        stats = {"onboarded_today": 0, "onboarded_yesterday": 0, "intros_made": 0}

        # Get user data from Firebase - optimized
        users_data = []

        try:
            # Get all users from users collection
            users_ref = fs.collection("users")
            users_docs = list(
                users_ref.stream()
            )  # Convert to list for better performance

            print(f"🔍 [ANALYTICS] Found {len(users_docs)} users in Firebase")

            if len(users_docs) == 0:
                print(
                    "❌ [ANALYTICS] No users found in Firebase - this is the problem!"
                )
                return JSONResponse(
                    {
                        "success": True,
                        "stats": stats,
                        "data": [],
                        "debug": "No users found in Firebase users collection",
                    }
                )

            # Batch get all extraction data to avoid individual queries
            extraction_data_map = {}
            try:
                extractions_ref = fs.collection("extractions")
                extraction_docs = list(extractions_ref.stream())
                for doc in extraction_docs:
                    extraction_data_map[doc.id] = doc.to_dict()
                print(
                    f"🔍 [ANALYTICS] Loaded {len(extraction_data_map)} extraction records"
                )
            except Exception as e:
                print(f"⚠️ [ANALYTICS] Error loading extractions: {e}")

            # Process users in batch
            processed_count = 0
            for doc in users_docs:
                try:
                    user_data = doc.to_dict()
                    user_id = doc.id
                    processed_count += 1

                    if processed_count <= 3:
                        print(
                            f"🔍 [ANALYTICS] Processing user {processed_count}: {user_id}"
                        )

                    # Get user creation timestamp (fallback to last_updated or last_interaction if created_at is missing)
                    created_at = user_data.get("created_at", 0)
                    if created_at == 0:
                        created_at = user_data.get("last_updated", 0)
                    if created_at == 0:
                        created_at = user_data.get("last_interaction", 0)
                    last_interaction = user_data.get("last_interaction", 0)

                    # Get user data directly from top-level fields (as shown in Firebase)
                    user_name = user_data.get("name", "")
                    user_email = user_data.get("email", "")

                    # Get profile data from profile subcollection
                    profile_data = user_data.get("profile", {})
                    if not user_name and profile_data:
                        user_name = profile_data.get("name", "")
                    if not user_email and profile_data:
                        user_email = profile_data.get("email", "")

                    linkedin_url = profile_data.get("linkedin", "")

                    # Get user goal first
                    need = user_data.get("goal", "unknown")
                    if need and need.strip():
                        need = need.strip()
                    else:
                        # Check profile data for goal
                        if profile_data:
                            need = profile_data.get("goal", "unknown")
                        if not need or need == "unknown":
                            # Use pre-loaded extraction data instead of individual query
                            extraction_data = extraction_data_map.get(user_id, {})
                            urgent_needs = extraction_data.get("urgent_needs", [])
                            if urgent_needs and len(urgent_needs) > 0:
                                need = (
                                    urgent_needs[0]
                                    if isinstance(urgent_needs, list)
                                    else str(urgent_needs)
                                )

                    # Count onboarding stats - users who completed profile (name, email, goal)
                    # LinkedIn is optional for onboarding
                    has_name = bool(user_name and user_name.strip())
                    has_email = bool(user_email and user_email.strip())
                    has_linkedin = bool(linkedin_url and linkedin_url.strip())
                    has_goal = bool(need and need.strip() and need != "unknown")
                    is_profile_complete = has_name and has_email and has_goal

                    # Determine missing fields for profile completion status
                    missing_fields = []
                    if not has_name:
                        missing_fields.append("Name")
                    if not has_email:
                        missing_fields.append("Email")
                    if not has_linkedin:
                        missing_fields.append("LinkedIn")
                    if not has_goal:
                        missing_fields.append("Goal")

                    completion_status = (
                        "Complete"
                        if is_profile_complete
                        else f"Missing: {', '.join(missing_fields)}"
                    )

                    # Check call status and count
                    call_status = "No Call Yet"
                    call_count = 0

                    # Get call count from user_calls collection
                    try:
                        call_docs = (
                            fs.collection("user_calls")
                            .document(user_id)
                            .collection("calls")
                            .stream()
                        )
                        call_count = len(list(call_docs))

                        if call_count > 0:
                            call_status = f"{call_count} Call{'s' if call_count > 1 else ''} Completed"
                        else:
                            # Check if call was initiated but not completed
                            if user_data.get("arbitrary", {}).get(
                                "voice_call_initiated"
                            ):
                                call_status = "Call Initiated"
                                call_count = 0  # Initiated but not completed
                    except Exception as e:
                        print(
                            f"⚠️ [ANALYTICS_CALL_COUNT] Error getting call count for {user_id}: {e}"
                        )
                        # Fallback to basic call status check
                        if user_data.get("arbitrary", {}).get("voice_call_initiated"):
                            call_status = "Call Initiated"

                    if processed_count <= 10:  # Show more users for debugging
                        print(
                            f"🔍 [ANALYTICS] User {user_id}: name={has_name}, email={has_email}, linkedin={has_linkedin}, goal={has_goal}, complete={is_profile_complete}"
                        )
                        print(
                            f"🔍 [ANALYTICS] User {user_id}: created_at={created_at}, today_ts={today_timestamp}, yesterday_ts={yesterday_timestamp}"
                        )
                        if created_at > 0:
                            created_date = datetime.fromtimestamp(created_at)
                            print(
                                f"🔍 [ANALYTICS] User {user_id}: created_date={created_date}"
                            )
                            print(
                                f"🔍 [ANALYTICS] User {user_id}: created_at >= today_ts = {created_at >= today_timestamp}"
                            )
                            print(
                                f"🔍 [ANALYTICS] User {user_id}: created_at >= yesterday_ts = {created_at >= yesterday_timestamp}"
                            )
                            if is_profile_complete:
                                print(
                                    f"🔍 [ANALYTICS] User {user_id}: PROFILE COMPLETE - should count for onboarding!"
                                )

                    if is_profile_complete:
                        if created_at >= today_timestamp:
                            stats["onboarded_today"] += 1
                            print(
                                f"✅ [ANALYTICS] User {user_id} onboarded TODAY (created_at: {created_at})"
                            )
                        elif created_at >= yesterday_timestamp:
                            stats["onboarded_yesterday"] += 1
                            print(
                                f"✅ [ANALYTICS] User {user_id} onboarded YESTERDAY (created_at: {created_at})"
                            )

                    # Get user's current state from user data
                    current_state = user_data.get("state", "active")

                    users_data.append(
                        {
                            "user_id": user_id,
                            "name": user_name,
                            "email": user_email,
                            "linkedin": linkedin_url,
                            "need": need,
                            "date": (
                                datetime.fromtimestamp(created_at).isoformat()
                                if created_at
                                else datetime.now().isoformat()
                            ),
                            "status": current_state,
                            "profile_complete": is_profile_complete,
                            "completion_status": completion_status,
                            "missing_fields": missing_fields,
                            "call_status": call_status,
                            "call_count": call_count,
                            "last_interaction": last_interaction,
                        }
                    )

                except Exception as e:
                    print(f"❌ [ANALYTICS] Error processing user {doc.id}: {e}")
                    continue

            print(
                f"🔍 [ANALYTICS] Processed {processed_count} users, created {len(users_data)} user records"
            )

        except Exception as e:
            print(f"❌ [ANALYTICS] Error fetching user data: {e}")

        # Get introductions count - count users who have been introduced to Vance
        try:
            # Count users who have complete profiles (introduced to Vance)
            intros_made = 0
            print(
                f"🔍 [ANALYTICS] DEBUG: Starting intros calculation with {len(users_data)} users"
            )
            for user in users_data:
                # User is considered "introduced" if they have complete profile (name + email + goal)
                if (
                    user.get("name")
                    and user.get("name").strip()
                    and user.get("email")
                    and user.get("email").strip()
                    and user.get("need")
                    and user.get("need").strip()
                    and user.get("need") != "unknown"
                ):
                    intros_made += 1
            stats["intros_made"] = intros_made
            print(
                f"🔍 [ANALYTICS] Found {intros_made} users who have been introduced to Vance"
            )
        except Exception as e:
            print(f"❌ [ANALYTICS] Error counting introductions: {e}")

        # Sort users by date (newest first)
        users_data.sort(key=lambda x: x["date"], reverse=True)

        # Prepare response data
        response_data = {
            "success": True,
            "stats": stats,
            "users": users_data,
            "debug": {
                "today": str(today),
                "yesterday": str(yesterday),
                "today_timestamp": today_timestamp,
                "yesterday_timestamp": yesterday_timestamp,
                "total_users_processed": len(users_data),
                "users_with_complete_profiles": len(
                    [
                        u
                        for u in users_data
                        if u.get("name")
                        and u.get("email")
                        and u.get("need")
                        and u.get("need") != "unknown"
                    ]
                ),
            },
        }

        # Cache the data
        _cache_analytics_data(response_data)

        return JSONResponse(response_data)

    except Exception as e:
        print(f"❌ [ANALYTICS] Error in get_analytics_data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching analytics data: {str(e)}"
        )


@router.post("/auto-detect-schedule")
async def auto_detect_and_schedule(
    user_ids: List[str] = Form(...), admin: bool = Depends(get_current_admin)
):
    """Auto-detect user intent and schedule appropriate actions using Claude"""
    try:
        results = []

        for user_id in user_ids:
            try:
                result = await process_user_auto_detection(user_id)
                results.append(
                    {
                        "user_id": user_id,
                        "success": True,
                        "action": result.get("action", "none"),
                        "message": result.get("message", "No action needed"),
                        "scheduled_time": result.get("scheduled_time"),
                    }
                )
            except Exception as e:
                results.append({"user_id": user_id, "success": False, "error": str(e)})

        return JSONResponse(
            {
                "success": True,
                "results": results,
                "total_processed": len(user_ids),
                "successful": len([r for r in results if r["success"]]),
            }
        )

    except Exception as e:
        print(f"❌ [AUTO_DETECT] Error in auto_detect_and_schedule: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing auto-detection: {str(e)}"
        )


async def process_user_auto_detection(user_id: str) -> dict:
    """Process a single user for auto-detection and scheduling"""
    try:
        # Get recent conversation history
        recent_messages = conversation_history.get_recent_messages(user_id, limit=10)
        if not recent_messages:
            return {"action": "none", "message": "No conversation history found"}

        # Get user profile
        user_doc = fs.collection("users").document(user_id).get()
        if not user_doc.exists:
            return {"action": "none", "message": "User not found"}

        user_data = user_doc.to_dict()
        profile = user_data.get("profile", {})

        # Get the last user message
        last_user_message = None
        for msg in reversed(recent_messages):
            if msg.get("sender") == "user":
                last_user_message = msg
                break

        if not last_user_message:
            return {"action": "none", "message": "No user messages found"}

        # Use Claude to analyze the user's intent
        analysis = await analyze_user_intent_with_claude(
            user_id, last_user_message.get("content", ""), profile, recent_messages
        )

        # Execute the appropriate action based on Claude's analysis
        if analysis["intent"] == "schedule_availability":
            return await schedule_availability_check(user_id, analysis)
        elif analysis["intent"] == "initiate_call_now":
            return await initiate_immediate_call(user_id)
        elif analysis["intent"] == "complete_profile":
            return await send_profile_completion_prompt(user_id, analysis, profile)
        else:
            return {
                "action": "none",
                "message": "No action needed based on conversation context",
            }

    except Exception as e:
        print(f"❌ [AUTO_DETECT] Error processing user {user_id}: {e}")
        raise e


async def analyze_user_intent_with_claude(
    user_id: str, last_message: str, profile: dict, recent_messages: list
) -> dict:
    """Use Claude to analyze user intent and determine next action"""
    try:
        # Build context for Claude
        conversation_context = []
        for msg in recent_messages[-5:]:  # Last 5 messages for context
            sender = msg.get("sender", "unknown")
            content = msg.get("content", "")
            conversation_context.append(f"{sender}: {content}")

        context_text = "\n".join(conversation_context)

        # Check profile completeness
        has_name = bool(profile.get("name", "").strip())
        has_email = bool(profile.get("email", "").strip())
        has_linkedin = bool(profile.get("linkedin", "").strip())
        has_goal = bool(profile.get("goal", "").strip())

        missing_fields = []
        if not has_name:
            missing_fields.append("name")
        if not has_email:
            missing_fields.append("email")
        if not has_linkedin:
            missing_fields.append("linkedin")
        if not has_goal:
            missing_fields.append("goal")

        profile_complete = len(missing_fields) == 0

        prompt = f"""
Analyze this user's conversation and determine the best next action.

USER PROFILE STATUS:
- Profile complete: {profile_complete}
- Missing fields: {missing_fields if missing_fields else "none"}
- Name: {profile.get("name", "missing")}
- Email: {profile.get("email", "missing")}
- LinkedIn: {profile.get("linkedin", "missing")}
- Goal: {profile.get("goal", "missing")}

RECENT CONVERSATION:
{context_text}

LAST USER MESSAGE: "{last_message}"

ANALYSIS RULES:
1. If user mentions a specific time (like "in 2 minutes", "tomorrow 4pm", "later tonight"), classify as "schedule_availability"
2. If user agrees to call now (like "yes", "sure", "I'm available", "call me") AND profile is complete, classify as "initiate_call_now"
3. If profile is incomplete, classify as "complete_profile" and identify the next missing field
4. If no clear action needed, classify as "none"

Return JSON with:
{{
    "intent": "schedule_availability|initiate_call_now|complete_profile|none",
    "confidence": 0.0-1.0,
    "explanation": "brief reason",
    "time_expression": "extracted time if scheduling",
    "missing_field": "next field to collect if profile incomplete",
    "suggested_message": "message to send to user"
}}

Be precise and only suggest actions when there's clear intent.
"""

        response = claude_profile_service._call_claude_api(prompt, max_tokens=200)

        try:
            import json

            analysis = json.loads(response)
            print(
                f"🤖 [CLAUDE_ANALYSIS] User {user_id}: {analysis.get('intent')} (confidence: {analysis.get('confidence')})"
            )
            return analysis
        except json.JSONDecodeError:
            print(f"❌ [CLAUDE_ANALYSIS] Invalid JSON response: {response}")
            return {
                "intent": "none",
                "confidence": 0.0,
                "explanation": "Failed to parse Claude response",
            }

    except Exception as e:
        print(f"❌ [CLAUDE_ANALYSIS] Error analyzing intent: {e}")
        return {"intent": "none", "confidence": 0.0, "explanation": f"Error: {str(e)}"}


async def schedule_availability_check(user_id: str, analysis: dict) -> dict:
    """Schedule an availability check message for the user"""
    # Scheduling is now handled by the agent system
    return {
        "action": "none",
        "message": "Scheduling is now handled by the agent system",
    }


async def initiate_immediate_call(user_id: str) -> dict:
    """Initiate an immediate call for the user"""
    # Call initiation is now handled by the agent's start_voice_call tool
    return {
        "action": "none",
        "message": "Call initiation is now handled by the agent system",
    }


async def send_profile_completion_prompt(
    user_id: str, analysis: dict, profile: dict
) -> dict:
    """Send a prompt to complete missing profile fields"""
    # Profile completion is now handled naturally by the agent
    return {
        "action": "none",
        "message": "Profile completion is now handled by the agent system",
    }


# =============================================================================
# Switch Dashboard API
# =============================================================================


@router.get("/api/switch-dashboard")
async def switch_dashboard_data(request: Request, admin: bool = Depends(get_current_admin)):
    """
    Returns comprehensive analytics for the Switch/Jyoti dashboard.
    All Firestore queries run in parallel via asyncio.to_thread.
    """
    import asyncio

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    range_param = request.query_params.get("range", "all")
    cutoff = 0
    if range_param == "today":
        cutoff = today_start
    elif range_param == "7d":
        cutoff = (datetime.now() - timedelta(days=7)).timestamp()
    elif range_param == "30d":
        cutoff = (datetime.now() - timedelta(days=30)).timestamp()

    def _fetch_candidates():
        candidates = []
        total = 0
        try:
            for doc in fs.collection("switch_caller_memory").stream():
                data = doc.to_dict() or {}
                profile = data.get("profile", {}) or {}
                last_call_at = data.get("last_call_at", 0)
                if cutoff and last_call_at < cutoff:
                    continue
                total += 1
                candidates.append({
                    "phone": data.get("phone", doc.id),
                    "name": data.get("name", "") or profile.get("name", ""),
                    "total_calls": data.get("total_calls", 0),
                    "last_call_at": last_call_at,
                    "last_outcome": data.get("last_outcome", ""),
                    "caller_type": data.get("caller_type", ""),
                    "profile": profile,
                    "known_details": data.get("known_details", {}),
                    "last_summary": data.get("last_conversation_summary", ""),
                    "last_jobs_pitched": data.get("last_jobs_pitched", []),
                })
        except Exception as e:
            print(f"[SWITCH_DASH] Error fetching candidates: {e}")
        candidates.sort(key=lambda c: c.get("last_call_at", 0), reverse=True)
        return candidates, total

    def _fetch_sessions():
        sessions = []
        candidate_only = {
            "CALLING_CANDIDATE", "SCREENING_CANDIDATE", "CANDIDATE_HOLD",
            "CANDIDATE_NO_ANSWER", "CANDIDATE_DECLINED", "FAILED",
            "CALLING_CANDIDATES", "PITCHING_CANDIDATE",
        }
        metrics = {
            "calls_fired": 0, "candidate_picked_up": 0, "screening_completed": 0,
            "business_called": 0, "business_picked_up": 0, "bridge_completed": 0,
            "total_bridge_duration": 0, "bridge_duration_count": 0,
        }
        biz_phones = set()
        status_bd, outcome_bd, direction_bd = {}, {}, {}
        daily_s, daily_b = {}, {}
        for i in range(7):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_s[day] = 0
            daily_b[day] = 0
        try:
            query = fs.collection("live_connect_sessions").order_by(
                "created_at", direction="DESCENDING"
            ).limit(500)
            for doc in query.stream():
                data = doc.to_dict() or {}
                created_at = data.get("created_at", 0)
                if cutoff and created_at < cutoff:
                    continue
                status = data.get("status", "")
                direction = data.get("direction", "")
                outcome = data.get("outcome", "")
                metrics["calls_fired"] += 1
                if status not in ("CALLING_CANDIDATE", "FAILED", "CANDIDATE_NO_ANSWER"):
                    metrics["candidate_picked_up"] += 1
                if data.get("screening_data") or data.get("screening_summary"):
                    metrics["screening_completed"] += 1
                if status not in candidate_only:
                    metrics["business_called"] += 1
                    bp = data.get("business_phone", "")
                    if bp:
                        biz_phones.add(bp)
                if status not in candidate_only and status != "BUSINESS_NO_ANSWER":
                    metrics["business_picked_up"] += 1
                if data.get("bridge_started_at"):
                    metrics["bridge_completed"] += 1
                    dur = data.get("bridge_duration_seconds", 0) or 0
                    if dur:
                        metrics["total_bridge_duration"] += dur
                        metrics["bridge_duration_count"] += 1
                status_bd[status] = status_bd.get(status, 0) + 1
                if outcome:
                    outcome_bd[outcome] = outcome_bd.get(outcome, 0) + 1
                dl = direction or ("inbound" if data.get("inbound") else "outbound")
                direction_bd[dl] = direction_bd.get(dl, 0) + 1
                day_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")
                if day_str in daily_s:
                    daily_s[day_str] += 1
                if data.get("bridge_started_at") and day_str in daily_b:
                    daily_b[day_str] += 1
                sessions.append({
                    "id": doc.id,
                    "candidate_phone": data.get("candidate_phone", ""),
                    "candidate_name": data.get("candidate_name", ""),
                    "status": status, "direction": direction,
                    "created_at": created_at, "outcome": outcome,
                    "screening_summary": data.get("screening_summary", ""),
                    "screening_data": data.get("screening_data", {}),
                    "business_phone": data.get("business_phone", ""),
                    "business_name": data.get("business_name", ""),
                    "inbound": data.get("inbound", False),
                    "attempts_summary": data.get("attempts_summary", {}),
                    "matching_jobs_count": len(data.get("matching_jobs", []) or []),
                    "bridge_duration_seconds": data.get("bridge_duration_seconds"),
                    "bridge_started_at": data.get("bridge_started_at"),
                })
        except Exception as e:
            print(f"[SWITCH_DASH] Error fetching sessions: {e}")
        return sessions, metrics, biz_phones, status_bd, outcome_bd, direction_bd, daily_s, daily_b

    def _fetch_interviews():
        interviews = []
        confirmed = 0
        try:
            for doc in fs.collection("telephonic_interviews").order_by(
                "created_at", direction="DESCENDING"
            ).stream():
                data = doc.to_dict() or {}
                created_at = data.get("created_at", 0)
                if cutoff and created_at < cutoff:
                    continue
                ic = data.get("interview_confirmed", False)
                if ic:
                    confirmed += 1
                interviews.append({
                    "id": doc.id,
                    "session_id": data.get("session_id", ""),
                    "candidate_phone": data.get("candidate_phone", ""),
                    "candidate_name": data.get("candidate_name", ""),
                    "business_phone": data.get("business_phone", ""),
                    "business_name": data.get("business_name", ""),
                    "job_title": data.get("job_title", ""),
                    "bridge_duration_seconds": data.get("bridge_duration_seconds", 0),
                    "interview_confirmed": ic,
                    "interview_date": data.get("interview_date", ""),
                    "interview_time": data.get("interview_time", ""),
                    "interview_location": data.get("interview_location", ""),
                    "recording_url": data.get("recording_url", ""),
                    "analysis_summary": data.get("analysis_summary", ""),
                    "outcome": data.get("outcome", ""),
                    "created_at": created_at,
                })
        except Exception as e:
            print(f"[SWITCH_DASH] Error fetching telephonic interviews: {e}")
        return interviews, confirmed

    def _fetch_scheduled():
        scheduled = []
        try:
            for doc in fs.collection("interview_scheduling").stream():
                data = doc.to_dict() or {}
                scheduled.append({
                    "id": doc.id,
                    "business_phone": data.get("business_phone", ""),
                    "business_name": data.get("business_name", ""),
                    "candidate_name": data.get("selected_candidate_name", ""),
                    "candidate_phone": data.get("selected_candidate_phone", ""),
                    "job_role": data.get("job_role", ""),
                    "step": data.get("step", ""),
                    "interview_datetime": data.get("interview_datetime", ""),
                    "interview_location": data.get("interview_location", ""),
                    "created_at": data.get("created_at", 0),
                })
        except Exception as e:
            print(f"[SWITCH_DASH] Error fetching scheduled interviews: {e}")
        return scheduled

    def _count_candidate_pool():
        count = 0
        try:
            for _doc in fs.collection("candidates").stream():
                count += 1
        except Exception as e:
            print(f"[SWITCH_DASH] Error counting candidate pool: {e}")
        return count

    def _count_open_jobs():
        count = 0
        try:
            for doc in fs.collection("jobs").stream():
                data = doc.to_dict() or {}
                if data.get("status") in ("OPEN", "PARTIALLY_FILLED"):
                    count += 1
        except Exception as e:
            print(f"[SWITCH_DASH] Error counting jobs: {e}")
        return count

    def _count_businesses_roster():
        try:
            phones = set()
            for doc in fs.collection("jobhai_jobs").stream():
                data = doc.to_dict() or {}
                phone = data.get("phone", "")
                if phone:
                    phones.add(phone)
            return len(phones)
        except Exception as e:
            print(f"[SWITCH_DASH] Error counting businesses: {e}")
            return 0

    def _count_switches():
        count = 0
        try:
            for doc in fs.collection("job_applications").stream():
                data = doc.to_dict() or {}
                if data.get("status") == "JOINED":
                    count += 1
        except Exception as e:
            print(f"[SWITCH_DASH] Error counting switches: {e}")
        return count

    (
        (candidates, total_candidates_talked),
        (sessions, metrics, businesses_talked_phones, status_breakdown, outcome_breakdown, direction_breakdown, daily_sessions, daily_bridges),
        (interviews, interviews_confirmed),
        scheduled_interviews,
        candidate_pool,
        open_jobs,
        total_businesses_roster,
        total_switches,
    ) = await asyncio.gather(
        asyncio.to_thread(_fetch_candidates),
        asyncio.to_thread(_fetch_sessions),
        asyncio.to_thread(_fetch_interviews),
        asyncio.to_thread(_fetch_scheduled),
        asyncio.to_thread(_count_candidate_pool),
        asyncio.to_thread(_count_open_jobs),
        asyncio.to_thread(_count_businesses_roster),
        asyncio.to_thread(_count_switches),
    )

    calls_fired = metrics["calls_fired"]
    candidate_picked_up = metrics["candidate_picked_up"]
    screening_completed = metrics["screening_completed"]
    business_called = metrics["business_called"]
    business_picked_up = metrics["business_picked_up"]
    bridge_completed_count = metrics["bridge_completed"]
    total_bridge_duration = metrics["total_bridge_duration"]
    bridge_duration_count = metrics["bridge_duration_count"]

    candidate_pickup_rate = round(candidate_picked_up / calls_fired * 100, 1) if calls_fired else 0
    screening_rate = round(screening_completed / candidate_picked_up * 100, 1) if candidate_picked_up else 0
    bridge_rate = round(bridge_completed_count / business_called * 100, 1) if business_called else 0
    interview_confirm_rate = round(interviews_confirmed / bridge_completed_count * 100, 1) if bridge_completed_count else 0
    avg_bridge_duration = round(total_bridge_duration / bridge_duration_count, 1) if bridge_duration_count else 0

    daily_activity = []
    for day in sorted(daily_sessions.keys()):
        daily_activity.append({
            "date": day,
            "sessions": daily_sessions[day],
            "bridges": daily_bridges[day],
        })

    return {
        "stats": {
            "total_candidates_talked": total_candidates_talked,
            "total_businesses_talked": len(businesses_talked_phones),
            "telephonic_interviews": len(interviews),
            "interviews_confirmed": interviews_confirmed,
            "total_switches": total_switches,
            "total_lc_sessions": calls_fired,
            "candidate_pool": candidate_pool,
            "open_jobs": open_jobs,
            "total_businesses_roster": total_businesses_roster,
        },
        "funnel": {
            "calls_fired": calls_fired,
            "candidate_picked_up": candidate_picked_up,
            "screening_completed": screening_completed,
            "business_called": business_called,
            "business_picked_up": business_picked_up,
            "bridge_completed": bridge_completed_count,
            "interview_confirmed": interviews_confirmed,
            "joined": total_switches,
        },
        "rates": {
            "candidate_pickup_rate": candidate_pickup_rate,
            "screening_rate": screening_rate,
            "bridge_rate": bridge_rate,
            "interview_confirm_rate": interview_confirm_rate,
        },
        "breakdowns": {
            "status": status_breakdown,
            "outcome": outcome_breakdown,
            "direction": direction_breakdown,
        },
        "daily_activity": daily_activity,
        "avg_bridge_duration_seconds": avg_bridge_duration,
        "sessions": sessions[:200],
        "candidates": candidates,
        "interviews": interviews,
        "scheduled_interviews": scheduled_interviews,
    }
