# Switch - Real-Time Labor Placement Platform
## Implementation Plan & Gap Analysis

**Date:** January 26, 2026  
**Status:** Specification Review Complete

---

## 📊 CURRENT STATE vs SPECIFICATION

### ✅ **What's Already Implemented**

#### Candidate Side (Partially Complete)
- ✅ Phone + OTP authentication (`/api/candidate-onboarding/signup`, `/verify-otp`)
- ✅ Basic profile management (`/api/switch/profile/{user_id}`)
- ✅ Photo upload (`/api/switch/upload-photo/{user_id}`)
- ✅ Job application tracking (`/api/switch/apply`, `/applications/{user_id}`)
- ✅ Tinder-style swipe UI (frontend in `Switch/src/SwitchApp.jsx`)
- ✅ Stats tracking (totalApplied, interviews, hired)
- ✅ Data stored in `switch_users` Firestore collection

#### Infrastructure
- ✅ WhatsApp integration (via main Vance app)
- ✅ Twilio SMS/voice capabilities
- ✅ ElevenLabs AI integration (for practice calls)
- ✅ Firestore database
- ✅ FastAPI backend with CORS support

#### Partial Business Side
- ⚠️ `switch-polling/` system exists but is separate Node.js service
  - Polls MyOperator for incoming calls
  - Connects to ElevenLabs AI
  - Collects requirements
  - Calls candidates in batch
  - **Gap:** Not integrated with main Switch backend, uses in-memory storage

---

## ❌ **What's Missing (Per Specification)**

### 1. **Database Schema**
**Current:** Data in `switch_users`, `users`, `user_profiles` collections  
**Needed:** Structured collections matching spec:
- `candidates` collection
- `businesses` collection  
- `jobs` collection
- `job_applications` collection
- `calls` collection

### 2. **Business Side Flow**
- ❌ WhatsApp requirement intake (business texts Switch number)
- ❌ AI call to business for requirement collection
- ❌ Job creation from AI call data
- ❌ Real-time candidate matching after job creation
- ❌ Batch calling candidates with warm transfer
- ❌ WhatsApp candidate profile cards to business
- ❌ Interview confirmation flow

### 3. **Candidate Side Enhancements**
- ❌ Full onboarding form (Aadhaar, preferred areas, previous roles, etc.)
- ❌ AI screening call after onboarding
- ❌ Real-time job matching during screening call
- ❌ Job feed filtering (only show OPEN jobs, exclude swiped jobs)
- ❌ Distance calculation for job cards

### 4. **Real-Time Systems**
- ❌ Job status tracker (OPEN → PARTIALLY_FILLED → FILLED)
- ❌ Candidate availability tracker (AVAILABLE → IN_PROCESS → PLACED)
- ❌ Automatic feed updates when job status changes
- ❌ Auto-withdraw applications when candidate joins another job

### 5. **Call Management**
- ❌ Structured call tracking (business intake, screening, pitch, connected)
- ❌ Call recording storage and transcription
- ❌ AI-extracted data from calls
- ❌ Warm transfer/call merging logic

### 6. **WhatsApp Templates**
- ❌ Business candidate profile cards
- ❌ Interview confirmation messages
- ❌ Business confirmation notifications

---

## 🏗️ **IMPLEMENTATION ROADMAP**

### **Phase 1: Database Schema & Models** (Priority: HIGH)

#### 1.1 Create Firestore Collections Structure
```python
# New file: models/switch_models.py

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class CandidateStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    IN_PROCESS = "IN_PROCESS"
    PLACED = "PLACED"
    INACTIVE = "INACTIVE"

class JobStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CLOSED = "CLOSED"

class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    MATCHED = "MATCHED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEWED = "INTERVIEWED"
    SELECTED = "SELECTED"
    JOINED = "JOINED"
    REJECTED = "REJECTED"
    NO_SHOW = "NO_SHOW"

class CallType(str, Enum):
    BUSINESS_INTAKE = "BUSINESS_INTAKE"
    CANDIDATE_SCREENING = "CANDIDATE_SCREENING"
    CANDIDATE_PITCH = "CANDIDATE_PITCH"
    INTERVIEW_CONFIRM = "INTERVIEW_CONFIRM"
    CONNECTED_CALL = "CONNECTED_CALL"

# Pydantic models for validation
class Candidate(BaseModel):
    id: str
    phone: str
    name: str
    photo_url: Optional[str]
    aadhaar_number: Optional[str]
    area: str
    preferred_areas: List[str]
    experience_level: str
    previous_roles: List[str]
    previous_employers: List[str]
    expected_salary_min: int
    expected_salary_max: int
    languages: List[str]
    availability: str
    status: CandidateStatus
    profile_completeness_score: int
    screening_call_recording_url: Optional[str]
    created_at: float
    last_active_at: float

class Business(BaseModel):
    id: str
    phone: str
    name: str
    contact_person: str
    business_type: str  # RESTAURANT | RETAIL | CAFE | OTHER
    area: str
    address: str
    created_at: float

class Job(BaseModel):
    id: str
    business_id: str
    role: str  # WAITER | HELPER | SALES | KITCHEN | DELIVERY | etc.
    positions_count: int
    positions_filled: int
    salary_min: int
    salary_max: int
    experience_required: str
    location: str
    shift_timing: Optional[str]
    requirements_notes: Optional[str]
    interview_address: str
    interview_timing: Optional[str]
    status: JobStatus
    ai_call_recording_url: Optional[str]
    created_at: float
    updated_at: float

class JobApplication(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    source: str  # SWIPE | AI_MATCH | BUSINESS_SELECT
    status: ApplicationStatus
    matched_at: Optional[float]
    interview_scheduled_at: Optional[float]
    joined_at: Optional[float]
    notes: Optional[str]

class Call(BaseModel):
    id: str
    call_type: CallType
    from_number: str
    to_number: str
    business_id: Optional[str]
    candidate_id: Optional[str]
    job_id: Optional[str]
    duration_seconds: Optional[int]
    recording_url: Optional[str]
    transcript: Optional[str]
    ai_extracted_data: Optional[dict]
    status: str  # INITIATED | IN_PROGRESS | COMPLETED | FAILED | NO_ANSWER
    created_at: float
```

#### 1.2 Migration Script
Create script to migrate existing `switch_users` data to new `candidates` collection structure.

---

### **Phase 2: Business Side Flow** (Priority: HIGH)

#### 2.1 WhatsApp Business Intake Handler
```python
# New file: api/switch_business_routes.py

@router.post("/whatsapp/business-requirement")
async def handle_business_requirement(message: WhatsAppMessage):
    """
    Receives WhatsApp message from business with job requirement.
    Triggers AI call to business.
    """
    # 1. Detect new business message
    # 2. Extract business phone number
    # 3. Create/update business record
    # 4. Trigger AI call to business
    # 5. Store call record
```

#### 2.2 AI Business Intake Call Service
```python
# New file: services/switch_business_intake_service.py

class BusinessIntakeService:
    async def initiate_business_call(self, business_phone: str, initial_message: str):
        """
        Calls business via ElevenLabs AI to collect:
        - Role type
        - Number of positions
        - Salary range
        - Experience required
        - Location
        - Timing/shifts
        - Requirements
        - Interview availability
        """
        # Use ElevenLabs conversational AI
        # Configure agent to collect structured data
        # Return extracted requirements
```

#### 2.3 Job Creation Service
```python
# New file: services/switch_job_service.py

class SwitchJobService:
    async def create_job_from_requirements(self, business_id: str, requirements: dict):
        """
        Creates Job record from AI-extracted requirements.
        Sets status = OPEN
        Triggers real-time candidate matching
        """
        # 1. Create job document
        # 2. Set status = OPEN
        # 3. Trigger candidate matching
        # 4. Add to candidate feeds
```

#### 2.4 Real-Time Candidate Matching
```python
# Extend: services/switch_matching_service.py

class SwitchMatchingService:
    async def find_matching_candidates(self, job: Job) -> List[Candidate]:
        """
        Query candidates matching:
        - Role preference matches job role
        - Location proximity
        - Salary expectation <= job salary
        - Experience >= required
        - Status = AVAILABLE
        """
        # 1. Query Firestore with filters
        # 2. Calculate distance for each candidate
        # 3. Sort by: last active, profile completeness, distance
        # 4. Return top 10
```

#### 2.5 Batch Candidate Calling with Warm Transfer
```python
# New file: services/switch_call_service.py

class SwitchCallService:
    async def batch_call_candidates(self, job: Job, candidates: List[Candidate]):
        """
        Calls top 10 candidates in parallel.
        First to pick up gets connected to business.
        """
        # 1. Initiate calls to all candidates
        # 2. On first pickup:
        #    - Brief pitch about job
        #    - If interested: attempt warm transfer
        #    - Call business, merge calls
        #    - Drop AI from call
        # 3. Cancel pending calls
        # 4. If business doesn't pick: send WhatsApp profiles
```

---

### **Phase 3: Candidate Side Enhancements** (Priority: MEDIUM)

#### 3.1 Enhanced Onboarding Form
```python
# Extend: api/candidate_onboarding_routes.py

@router.post("/onboarding/complete")
async def complete_onboarding(user_id: str, form_data: OnboardingForm):
    """
    Collects full onboarding data:
    - Name, Photo, Aadhaar
    - Area, Preferred areas
    - Experience, Previous roles
    - Salary expectations
    - Languages, Availability
    """
    # 1. Validate and store form data
    # 2. Create candidate record
    # 3. Trigger AI screening call
```

#### 3.2 AI Screening Call
```python
# New file: services/switch_screening_service.py

class ScreeningService:
    async def initiate_screening_call(self, candidate_id: str):
        """
        Calls candidate after onboarding:
        - Verify identity
        - Confirm form details
        - Ask about experience
        - Check availability
        - Extract insights
        """
        # 1. Call candidate via ElevenLabs
        # 2. Run screening script
        # 3. Extract structured data
        # 4. Update candidate profile
        # 5. Check for real-time job matches
        # 6. If match: offer connection
```

#### 3.3 Job Feed Logic
```python
# Extend: api/switch_routes.py

@router.get("/jobs/feed/{candidate_id}")
async def get_job_feed(candidate_id: str):
    """
    Returns jobs matching candidate:
    - Only OPEN jobs
    - Only jobs not swiped
    - Sorted by distance, then recency
    - Exclude rejected jobs
    """
    # 1. Get candidate profile
    # 2. Query matching jobs
    # 3. Filter out swiped/rejected
    # 4. Calculate distances
    # 5. Sort and return
```

---

### **Phase 4: Real-Time Systems** (Priority: HIGH)

#### 4.1 Job Status Tracker
```python
# New file: services/switch_job_tracker.py

class JobStatusTracker:
    async def update_job_status(self, job_id: str):
        """
        Updates job status based on positions_filled:
        - If filled >= count: status = FILLED, remove from feeds
        - Else: status = PARTIALLY_FILLED
        """
```

#### 4.2 Candidate Availability Tracker
```python
# New file: services/switch_availability_tracker.py

class AvailabilityTracker:
    async def update_candidate_status(self, candidate_id: str, status: CandidateStatus):
        """
        Updates candidate status:
        - On apply: IN_PROCESS (temp lock)
        - On join: PLACED (remove from pool)
        - On reject: AVAILABLE (back to pool)
        - On inactive 7+ days: INACTIVE
        """
```

#### 4.3 Auto-Withdraw Applications
```python
# In: services/switch_job_service.py

async def handle_candidate_joined(self, candidate_id: str, job_id: str):
    """
    When candidate joins a job:
    - Update candidate status to PLACED
    - Withdraw from all other applications
    - Update other job statuses if needed
    """
```

---

### **Phase 5: WhatsApp Integration** (Priority: MEDIUM)

#### 5.1 WhatsApp Message Templates
```python
# New file: services/switch_whatsapp_service.py

class SwitchWhatsAppService:
    async def send_candidate_profiles(self, business_id: str, candidates: List[Candidate], job_id: str):
        """Send formatted candidate cards to business"""
    
    async def send_interview_confirmation(self, candidate_id: str, job: Job):
        """Send interview confirmation to candidate"""
    
    async def send_business_confirmation(self, business_id: str, candidate: Candidate, job: Job):
        """Send confirmation to business when candidate confirms"""
```

---

### **Phase 6: Call Management** (Priority: MEDIUM)

#### 6.1 Call Tracking Service
```python
# New file: services/switch_call_tracking.py

class CallTrackingService:
    async def create_call_record(self, call_data: dict):
        """Store call record in calls collection"""
    
    async def update_call_status(self, call_id: str, status: str, recording_url: str = None):
        """Update call status and store recording"""
    
    async def extract_call_data(self, call_id: str, transcript: str):
        """Use AI to extract structured data from transcript"""
```

---

## 🔄 **INTEGRATION POINTS**

### 1. **WhatsApp Router Integration**
- Extend `api/whatsapp_modules/router_v2.py` to detect Switch business messages
- Route to `api/switch_business_routes.py`

### 2. **ElevenLabs Integration**
- Reuse existing ElevenLabs setup
- Create new agent configurations for:
  - Business intake calls
  - Candidate screening calls
  - Candidate pitch calls

### 3. **Twilio Integration**
- Reuse existing Twilio setup
- Add warm transfer/call merging logic
- Store call recordings

### 4. **Firestore Collections**
- Create new collections: `candidates`, `businesses`, `jobs`, `job_applications`, `calls`
- Migrate existing `switch_users` data

---

## 📋 **FILE STRUCTURE**

```
api/
  ├── switch_routes.py (existing - extend)
  ├── switch_business_routes.py (new)
  ├── candidate_onboarding_routes.py (existing - extend)
  └── routers.py (existing - add new routes)

services/
  ├── switch_business_intake_service.py (new)
  ├── switch_job_service.py (new)
  ├── switch_matching_service.py (new)
  ├── switch_call_service.py (new)
  ├── switch_screening_service.py (new)
  ├── switch_job_tracker.py (new)
  ├── switch_availability_tracker.py (new)
  ├── switch_whatsapp_service.py (new)
  └── switch_call_tracking.py (new)

models/
  └── switch_models.py (new)

scripts/
  └── migrate_switch_data.py (new)
```

---

## 🎯 **SUCCESS METRICS**

Track these metrics (as specified):
- Time to first candidate (after business requirement)
- Call pickup rate (candidates)
- Match rate (candidates matched per job)
- Show-up rate (interviews attended / scheduled)
- Placement rate (joined / interviewed)
- Revenue per day
- Candidates in pool (AVAILABLE status)
- Open jobs count

---

## 🚀 **NEXT STEPS**

1. **Review & Approve Plan** - Confirm approach
2. **Phase 1 Implementation** - Database schema & models
3. **Phase 2 Implementation** - Business side flow
4. **Phase 3 Implementation** - Candidate enhancements
5. **Phase 4 Implementation** - Real-time systems
6. **Phase 5 Implementation** - WhatsApp integration
7. **Phase 6 Implementation** - Call management
8. **Testing & Deployment** - End-to-end testing

---

## ⚠️ **EDGE CASES TO HANDLE**

1. No matching candidates → Notify business, trigger sourcing alert
2. Candidate doesn't pick screening call → Retry 2x, then WhatsApp callback request
3. Business doesn't pick for warm transfer → Send WhatsApp profiles
4. Candidate no-show → Mark NO_SHOW, notify business, offer replacement
5. Job filled externally → Business can mark CLOSED via WhatsApp
6. Candidate placed elsewhere → Auto-withdraw from other applications

---

**Status:** Ready for implementation  
**Estimated Timeline:** 4-6 weeks for full implementation  
**Priority:** HIGH - Core business functionality
