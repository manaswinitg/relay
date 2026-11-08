from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class EmergencyReportBase(BaseModel):
    reporter_name: Optional[str] = None
    contact_info: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    address_hint: Optional[str] = None
    category: str = Field(default="OTHER")  # MEDICAL, WATER, FOOD, SHELTER, HAZARD, OTHER
    urgency: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    raw_text: str = Field(..., min_length=3)


class EmergencyReportCreate(EmergencyReportBase):
    client_assigned_uuid: Optional[str] = None
    client_created_at: Optional[datetime] = None


class EmergencyReportUpdate(BaseModel):
    status: Optional[str] = None  # SUBMITTED, VERIFIED, IN_PROGRESS, RESOLVED, REJECTED
    category: Optional[str] = None
    urgency: Optional[str] = None
    is_duplicate: Optional[bool] = None
    duplicate_of_report_id: Optional[str] = None
    base_version: int


class EmergencyReportResponse(EmergencyReportBase):
    id: str
    client_assigned_uuid: str
    status: str
    ai_summary: Optional[str] = None
    ai_confidence: Optional[float] = None
    is_duplicate: bool
    duplicate_of_report_id: Optional[str] = None
    verified_by_user_id: Optional[str] = None
    version: int
    client_created_at: datetime
    server_received_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssistanceRequestBase(BaseModel):
    shelter_id: Optional[str] = None
    resource_type_id: str
    requested_quantity: float = Field(..., gt=0.0)
    priority_score: int = Field(default=50, ge=1, le=100)


class AssistanceRequestCreate(AssistanceRequestBase):
    emergency_report_id: Optional[str] = None
    client_assigned_uuid: Optional[str] = None


class AssistanceRequestResponse(AssistanceRequestBase):
    id: str
    client_assigned_uuid: str
    emergency_report_id: Optional[str] = None
    fulfilled_quantity: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
