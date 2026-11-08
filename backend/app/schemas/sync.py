from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class SyncMutationItem(BaseModel):
    mutation_id: str = Field(..., description="Unique client UUID for this specific mutation")
    entity_type: str = Field(..., description="REPORT, INVENTORY, SHELTER, REQUEST")
    action: str = Field(..., description="CREATE, UPDATE, DELTA, DELETE")
    base_version: Optional[int] = Field(None, description="The version the client held when mutation occurred")
    payload: Dict[str, Any] = Field(..., description="Payload data for the mutation")
    client_timestamp: Optional[datetime] = None


class SyncPushRequest(BaseModel):
    device_id: str = Field(..., description="Client device or volunteer node identifier")
    client_sent_at: datetime
    batch: List[SyncMutationItem]


class SyncMutationResult(BaseModel):
    mutation_id: str
    status: str  # APPLIED, DUPLICATE_IGNORED, CONFLICT_ISOLATED, ERROR
    entity_id: Optional[str] = None
    resulting_version: Optional[int] = None
    message: Optional[str] = None


class SyncPushResponse(BaseModel):
    server_received_at: datetime
    processed_count: int
    results: List[SyncMutationResult]


class SyncPullResponse(BaseModel):
    server_timestamp: datetime
    shelters: List[Dict[str, Any]]
    inventory: List[Dict[str, Any]]
    reports: List[Dict[str, Any]]
    resource_types: List[Dict[str, Any]]


class ConflictRecordResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    client_device_id: str
    client_base_version: int
    server_current_version: int
    client_payload: Dict[str, Any]
    server_payload: Dict[str, Any]
    resolution_status: str
    resolved_by_user_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConflictResolveRequest(BaseModel):
    resolution: str = Field(..., description="ACCEPT_CLIENT, ACCEPT_SERVER, or MANUAL_MERGE")
    manual_payload: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
