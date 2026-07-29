"""
Data models for Switch - Real-Time Labor Placement Platform.
Defines Pydantic models for validation and Firestore schema.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import time


class CandidateStatus(str, Enum):
    """Candidate availability status."""
    AVAILABLE = "AVAILABLE"
    IN_PROCESS = "IN_PROCESS"
    PLACED = "PLACED"
    INACTIVE = "INACTIVE"


class JobStatus(str, Enum):
    """Job posting status."""
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CLOSED = "CLOSED"


class ApplicationStatus(str, Enum):
    """Job application status."""
    APPLIED = "APPLIED"
    MATCHED = "MATCHED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEWED = "INTERVIEWED"
    SELECTED = "SELECTED"
    JOINED = "JOINED"
    REJECTED = "REJECTED"
    NO_SHOW = "NO_SHOW"


class ApplicationSource(str, Enum):
    """Source of job application."""
    SWIPE = "SWIPE"
    AI_MATCH = "AI_MATCH"
    BUSINESS_SELECT = "BUSINESS_SELECT"


class CallType(str, Enum):
    """Type of call."""
    BUSINESS_INTAKE = "BUSINESS_INTAKE"
    CANDIDATE_SCREENING = "CANDIDATE_SCREENING"
    CANDIDATE_PITCH = "CANDIDATE_PITCH"
    INTERVIEW_CONFIRM = "INTERVIEW_CONFIRM"
    CONNECTED_CALL = "CONNECTED_CALL"
    INCOMING_CALL = "INCOMING_CALL"
    LIVE_CONNECT_CANDIDATE = "LIVE_CONNECT_CANDIDATE"
    LIVE_CONNECT_BUSINESS = "LIVE_CONNECT_BUSINESS"


class LiveConnectStatus(str, Enum):
    """Live connect session status."""
    CALLING_CANDIDATE = "CALLING_CANDIDATE"
    SCREENING_CANDIDATE = "SCREENING_CANDIDATE"
    CANDIDATE_HOLD = "CANDIDATE_HOLD"
    CALLING_BUSINESS = "CALLING_BUSINESS"
    PITCHING_BUSINESS = "PITCHING_BUSINESS"
    BRIDGED = "BRIDGED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANDIDATE_DECLINED = "CANDIDATE_DECLINED"
    BUSINESS_DECLINED = "BUSINESS_DECLINED"
    BUSINESS_NO_ANSWER = "BUSINESS_NO_ANSWER"
    BUSINESS_HOLD = "BUSINESS_HOLD"
    CALLING_CANDIDATES = "CALLING_CANDIDATES"
    PITCHING_CANDIDATE = "PITCHING_CANDIDATE"
    CANDIDATE_NO_ANSWER = "CANDIDATE_NO_ANSWER"


class CallStatus(str, Enum):
    """Call status."""
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"


class BusinessType(str, Enum):
    """Business type."""
    RESTAURANT = "RESTAURANT"
    RETAIL = "RETAIL"
    CAFE = "CAFE"
    OTHER = "OTHER"


class Candidate(BaseModel):
    """Candidate profile model."""
    id: str = Field(..., description="Candidate ID (phone number)")
    phone: str = Field(..., description="Phone number")
    name: str = Field(..., description="Full name")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    aadhaar_number: Optional[str] = Field(None, description="Aadhaar number (optional)")
    area: str = Field(..., description="Current area/location")
    preferred_areas: List[str] = Field(default_factory=list, description="Preferred work areas")
    experience_level: str = Field(..., description="Experience level (Fresher/1-2 yrs/3-5 yrs/5+ yrs)")
    previous_roles: List[str] = Field(default_factory=list, description="Previous job roles")
    previous_employers: List[str] = Field(default_factory=list, description="Previous employer names")
    expected_salary_min: int = Field(..., description="Minimum expected salary")
    expected_salary_max: int = Field(..., description="Maximum expected salary")
    languages: List[str] = Field(default_factory=list, description="Languages known")
    availability: str = Field(..., description="Availability (Immediate/1 week/2 weeks)")
    status: CandidateStatus = Field(default=CandidateStatus.AVAILABLE, description="Current status")
    profile_completeness_score: int = Field(default=0, description="Profile completeness 0-100")
    screening_call_recording_url: Optional[str] = Field(None, description="Screening call recording")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    last_active_at: float = Field(default_factory=time.time, description="Last active timestamp")


class Business(BaseModel):
    """Business/employer model."""
    id: str = Field(..., description="Business ID")
    phone: str = Field(..., description="Business phone number")
    name: str = Field(..., description="Business name")
    contact_person: str = Field(..., description="Contact person name")
    business_type: BusinessType = Field(..., description="Type of business")
    area: str = Field(..., description="Business area/location")
    address: str = Field(..., description="Full address")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")


class Job(BaseModel):
    """Job posting model."""
    id: str = Field(..., description="Job ID")
    business_id: str = Field(..., description="Business ID (FK)")
    role: str = Field(..., description="Job role (WAITER/HELPER/SALES/KITCHEN/DELIVERY/etc.)")
    positions_count: int = Field(..., description="Number of positions")
    positions_filled: int = Field(default=0, description="Number of positions filled")
    salary_min: int = Field(..., description="Minimum salary")
    salary_max: int = Field(..., description="Maximum salary")
    experience_required: str = Field(..., description="Required experience")
    location: str = Field(..., description="Job location")
    shift_timing: Optional[str] = Field(None, description="Shift timing")
    requirements_notes: Optional[str] = Field(None, description="Additional requirements")
    interview_address: str = Field(..., description="Interview address")
    interview_timing: Optional[str] = Field(None, description="Interview timing")
    status: JobStatus = Field(default=JobStatus.OPEN, description="Job status")
    ai_call_recording_url: Optional[str] = Field(None, description="AI intake call recording")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    updated_at: float = Field(default_factory=time.time, description="Last update timestamp")


class JobApplication(BaseModel):
    """Job application model."""
    id: str = Field(..., description="Application ID")
    job_id: str = Field(..., description="Job ID (FK)")
    candidate_id: str = Field(..., description="Candidate ID (FK)")
    source: ApplicationSource = Field(..., description="Application source")
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED, description="Application status")
    matched_at: Optional[float] = Field(None, description="When candidate was matched")
    interview_scheduled_at: Optional[float] = Field(None, description="Interview scheduled timestamp")
    joined_at: Optional[float] = Field(None, description="When candidate joined")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")


class Call(BaseModel):
    """Call record model."""
    id: str = Field(..., description="Call ID")
    call_type: CallType = Field(..., description="Type of call")
    from_number: str = Field(..., description="Caller phone number")
    to_number: str = Field(..., description="Recipient phone number")
    business_id: Optional[str] = Field(None, description="Business ID if applicable")
    candidate_id: Optional[str] = Field(None, description="Candidate ID if applicable")
    job_id: Optional[str] = Field(None, description="Job ID if applicable")
    duration_seconds: Optional[int] = Field(None, description="Call duration")
    recording_url: Optional[str] = Field(None, description="Call recording URL")
    transcript: Optional[str] = Field(None, description="Call transcript")
    ai_extracted_data: Optional[dict] = Field(None, description="AI-extracted structured data")
    status: CallStatus = Field(default=CallStatus.INITIATED, description="Call status")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")


class BusinessRequirementRequest(BaseModel):
    """Request model for business requirement intake."""
    phone: str = Field(..., description="Business phone number")
    message: str = Field(..., description="Initial requirement message")


class JobCreationRequest(BaseModel):
    """Request model for creating job from requirements."""
    business_id: str = Field(..., description="Business ID")
    role: str = Field(..., description="Job role")
    positions_count: int = Field(..., description="Number of positions")
    salary_min: int = Field(..., description="Minimum salary")
    salary_max: int = Field(..., description="Maximum salary")
    experience_required: str = Field(..., description="Required experience")
    location: str = Field(..., description="Job location")
    shift_timing: Optional[str] = None
    requirements_notes: Optional[str] = None
    interview_address: str = Field(..., description="Interview address")
    interview_timing: Optional[str] = None


class LiveConnectSession(BaseModel):
    """Live connect session linking a candidate and business in a bridged call."""
    id: str = Field(..., description="Session ID")
    job_id: str = Field("", description="Job ID (set after screening/search)")
    candidate_id: str = Field("", description="Candidate ID (phone number)")
    candidate_phone: str = Field(..., description="Candidate phone number (E.164)")
    business_id: str = Field("", description="Business ID")
    business_phone: str = Field("", description="Business phone (set after job match)")
    status: LiveConnectStatus = Field(default=LiveConnectStatus.CALLING_CANDIDATE)
    candidate_call_uuid: Optional[str] = Field(None, description="Vobiz call UUID for candidate leg")
    business_call_uuid: Optional[str] = Field(None, description="Vobiz call UUID for business leg")
    candidate_conversation_id: Optional[str] = Field(None, description="ElevenLabs conversation ID for candidate screening")
    business_conversation_id: Optional[str] = Field(None, description="ElevenLabs conversation ID for business pitch")
    screening_summary: Optional[str] = Field(None, description="AI-generated candidate screening summary")
    screening_data: Optional[dict] = Field(None, description="Structured screening data from candidate")
    matching_jobs: Optional[list] = Field(None, description="Matched jobhai jobs for this session")
    current_job_index: int = Field(0, description="Index of current employer being called")
    current_job: Optional[dict] = Field(None, description="Currently active job being pitched")
    job_details: Optional[dict] = Field(None, description="Job details for context")
    candidate_name: Optional[str] = Field(None, description="Candidate name if known")
    business_name: Optional[str] = Field(None, description="Business name")
    bridge_started_at: Optional[float] = Field(None, description="When direct bridge started")
    bridge_ended_at: Optional[float] = Field(None, description="When direct bridge ended")
    outcome: Optional[str] = Field(None, description="Session outcome notes")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class OnboardingFormData(BaseModel):
    """Complete onboarding form data."""
    name: str
    photo_url: Optional[str] = None
    aadhaar_number: Optional[str] = None
    area: str
    preferred_areas: List[str] = Field(default_factory=list)
    experience_level: str
    previous_roles: List[str] = Field(default_factory=list)
    previous_employers: List[str] = Field(default_factory=list)
    expected_salary_min: int
    expected_salary_max: int
    languages: List[str] = Field(default_factory=list)
    availability: str
