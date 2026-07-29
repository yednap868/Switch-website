"""
API routes for Interview Practice feature with payment.
"""

import os
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from utils.db import fs
from utils.hearus_auth import caller_phone

# Optional Razorpay import - app will work without it, but payment feature will be disabled
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    razorpay = None
    RAZORPAY_AVAILABLE = False
    print("⚠️ [PRACTICE] Razorpay package not installed. Install with: uv pip install razorpay==1.4.2")

router = APIRouter(prefix="/api/switch", tags=["Switch App"])


class PracticePaymentRequest(BaseModel):
    """Request model for creating practice payment order."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None
    job_id: str
    job_role: str
    job_company: str
    amount: int = 50


class PaymentVerifyRequest(BaseModel):
    """Request model for verifying payment."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None
    job_id: str
    payment_id: str
    order_id: str
    signature: str


# Initialize Razorpay client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_AVAILABLE and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as e:
        razorpay_client = None
        print(f"⚠️ [PRACTICE] Failed to initialize Razorpay client: {e}")
else:
    razorpay_client = None
    if not RAZORPAY_AVAILABLE:
        print("⚠️ [PRACTICE] Razorpay package not installed. Payment will not work.")
    elif not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        print("⚠️ [PRACTICE] Razorpay credentials not found. Payment will not work.")


@router.post("/practice-payment")
async def create_practice_payment(payload: PracticePaymentRequest, http_request: Request):
    """
    Create a Razorpay order for interview practice payment (₹50).
    """
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")

    user_id = caller_phone(http_request)

    try:
        # Create Razorpay order
        order_data = {
            'amount': payload.amount * 100,  # Amount in paise
            'currency': 'INR',
            'receipt': f"practice_{user_id[:8]}_{int(time.time())}",
            'notes': {
                'user_id': user_id,
                'job_id': payload.job_id,
                'job_role': payload.job_role,
                'job_company': payload.job_company,
                'type': 'interview_practice'
            }
        }

        order = razorpay_client.order.create(data=order_data)

        print(f"✅ [PRACTICE] Payment order created: {order['id']} for user {user_id[:8]}")
        
        return JSONResponse({
            "status": "success",
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "razorpay_key": RAZORPAY_KEY_ID,
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        print(f"❌ [PRACTICE] Error creating payment order: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating payment order: {str(e)}")


@router.post("/practice-payment/verify")
async def verify_practice_payment(payload: PaymentVerifyRequest, http_request: Request):
    """
    Verify Razorpay payment and initiate practice call.
    """
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")

    user_id = caller_phone(http_request)

    try:
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': payload.order_id,
            'razorpay_payment_id': payload.payment_id,
            'razorpay_signature': payload.signature
        }

        razorpay_client.utility.verify_payment_signature(params_dict)

        print(f"✅ [PRACTICE] Payment verified: {payload.payment_id} for user {user_id[:8]}")

        # Save payment record
        payment_record = {
            "user_id": user_id,
            "job_id": payload.job_id,
            "payment_id": payload.payment_id,
            "order_id": payload.order_id,
            "amount": 50,
            "status": "completed",
            "created_at": time.time(),
            "type": "interview_practice"
        }

        fs.collection("switch_practice_payments").document(payload.payment_id).set(payment_record)

        # Initiate practice call
        try:
            await initiate_practice_call(user_id, payload.job_id)
        except Exception as call_err:
            print(f"⚠️ [PRACTICE] Error initiating call: {call_err}")
            # Don't fail payment verification if call fails
        
        return JSONResponse({
            "status": "success",
            "message": "Payment verified and practice call initiated",
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        # Check if it's a signature verification error
        if RAZORPAY_AVAILABLE and hasattr(razorpay, 'errors'):
            if isinstance(e, razorpay.errors.SignatureVerificationError):
                print(f"❌ [PRACTICE] Payment signature verification failed")
                raise HTTPException(status_code=400, detail="Payment signature verification failed")
        
        # Check error message for signature/verification keywords
        error_str = str(e).lower()
        if "signature" in error_str or "verification" in error_str:
            print(f"❌ [PRACTICE] Payment signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Payment signature verification failed")
        
        print(f"❌ [PRACTICE] Error verifying payment: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error verifying payment: {str(e)}")


async def initiate_practice_call(user_id: str, job_id: str):
    """
    Initiate practice call via ElevenLabs AI + Twilio.
    """
    try:
        # Get user phone number from profile
        user_doc = fs.collection("switch_users").document(user_id).get()
        if not user_doc.exists:
            raise Exception(f"User {user_id} not found")
        
        user_data = user_doc.to_dict()
        import re
        phone_number = re.sub(r'\D', '', user_data.get("phone", ""))  # Remove non-digits
        
        if not phone_number:
            raise Exception(f"Phone number not found for user {user_id}")
        
        # Format phone number for ElevenLabs (E.164 format)
        if not phone_number.startswith('+'):
            if phone_number.startswith('91'):
                phone_number = '+' + phone_number
            else:
                phone_number = '+91' + phone_number
        
        # Get job details from payment record or applications
        job_role = "Interview Practice"
        job_company = "Practice Session"
        
        # Try to get job details from applications
        applications_ref = fs.collection("switch_users").document(user_id).collection("applications")
        apps = list(applications_ref.where("job_id", "==", job_id).limit(1).stream())
        if apps:
            app_data = apps[0].to_dict()
            job_role = app_data.get("role", "Interview Practice")
            job_company = app_data.get("company", "Practice Session")
        
        # Call ElevenLabs API to initiate conversation
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        elevenlabs_phone_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
        
        if not elevenlabs_api_key or not elevenlabs_agent_id or not elevenlabs_phone_id:
            raise Exception("ElevenLabs credentials not configured")
        
        from elevenlabs import ConversationInitiationClientDataRequestInput, ElevenLabs
        
        elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
        
        # Initiate practice call with interview context
        elevenlabs_client.conversational_ai.twilio.outbound_call(
            agent_id=elevenlabs_agent_id,
            agent_phone_number_id=elevenlabs_phone_id,
            to_number=phone_number,
            conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                user_id=user_id,
                dynamic_variables={
                    "name": user_data.get("name", ""),
                    "uid": user_id,
                    "user_type": "job_seeker",
                    "connection_type": "interview_practice",
                    "primary_goal": f"Practice interview for {job_role} at {job_company}",
                    "job_role": job_role,
                    "job_company": job_company,
                    "practice_type": "interview_preparation",
                },
            ),
        )
        
        print(f"✅ [PRACTICE] Practice call initiated for user {user_id[:8]} for job {job_id} to {phone_number}")
        
        # Save call record
        call_record = {
            "user_id": user_id,
            "job_id": job_id,
            "phone_number": phone_number,
            "job_role": job_role,
            "job_company": job_company,
            "type": "practice_call",
            "status": "initiated",
            "created_at": time.time(),
        }
        
        fs.collection("switch_practice_calls").document(f"{user_id}_{job_id}_{int(time.time())}").set(call_record)
        
    except Exception as e:
        print(f"❌ [PRACTICE] Error initiating practice call: {e}")
        import traceback
        traceback.print_exc()
        raise
