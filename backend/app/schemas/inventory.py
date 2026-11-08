from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ResourceTypeBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    category: str = Field(..., max_length=50)  # WATER, FOOD, MEDICAL, SHELTER_SUPPLIES, POWER, SANITATION
    unit: str = Field(..., max_length=30)  # LITERS, MEALS, KITS, PERSONS, UNITS
    is_critical: bool = False


class ResourceTypeCreate(ResourceTypeBase):
    pass


class ResourceTypeResponse(ResourceTypeBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ShelterInventoryBase(BaseModel):
    shelter_id: str
    resource_type_id: str
    quantity: float = Field(..., ge=0.0)
    min_threshold: float = Field(default=10.0, ge=0.0)


class ShelterInventoryUpdate(BaseModel):
    quantity: float = Field(..., ge=0.0)
    min_threshold: Optional[float] = None
    base_version: int = Field(..., description="OCC version from client")


class ShelterInventoryResponse(ShelterInventoryBase):
    id: str
    version: int
    updated_at: datetime
    resource_type: Optional[ResourceTypeResponse] = None

    model_config = {"from_attributes": True}


class InventoryDeltaRequest(BaseModel):
    shelter_id: str
    resource_type_code: str
    delta: float = Field(..., description="Positive for additions, negative for distributions")
    base_version: Optional[int] = None
    mutation_id: Optional[str] = None
    client_timestamp: Optional[datetime] = None
