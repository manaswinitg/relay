from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ShelterBase(BaseModel):
    name: str = Field(..., max_length=200)
    address: str = Field(..., max_length=500)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    total_capacity: int = Field(default=0, ge=0)
    current_occupancy: int = Field(default=0, ge=0)
    status: str = Field(default="OPEN")  # OPEN, FULL, EVACUATING, CLOSED
    contact_phone: Optional[str] = None


class ShelterCreate(ShelterBase):
    client_assigned_uuid: Optional[str] = None


class ShelterUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_capacity: Optional[int] = None
    current_occupancy: Optional[int] = None
    status: Optional[str] = None
    contact_phone: Optional[str] = None
    base_version: int = Field(..., description="Version of entity on client when edit started")


class ShelterResponse(ShelterBase):
    id: str
    client_assigned_uuid: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShelterWithDistance(ShelterResponse):
    distance_km: float
