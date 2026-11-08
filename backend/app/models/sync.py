from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, get_utc_now


class SyncAuditLog(Base):
    __tablename__ = "sync_audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    client_device_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50), nullable=False)  # CREATE, UPDATE, DELTA, DELETE
    entity_name = Column(String(50), nullable=False)  # SHELTER, INVENTORY, REPORT, REQUEST
    entity_id = Column(String(36), nullable=False)
    base_version = Column(Integer, nullable=True)
    resulting_version = Column(Integer, nullable=True)
    payload = Column(JSON, nullable=False)
    sync_status = Column(String(50), nullable=False, index=True)  # APPLIED, CONFLICT_DETECTED, REJECTED
    conflict_reason = Column(Text, nullable=True)
    client_timestamp = Column(DateTime(timezone=True), nullable=False)
    server_timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SyncAuditLog {self.action_type} {self.entity_name} ({self.sync_status})>"


class ConflictRecord(Base):
    __tablename__ = "conflict_records"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # SHELTER, INVENTORY, REPORT, REQUEST
    entity_id = Column(String(36), nullable=False, index=True)
    client_device_id = Column(String(100), nullable=False)
    client_base_version = Column(Integer, nullable=False)
    server_current_version = Column(Integer, nullable=False)
    client_payload = Column(JSON, nullable=False)
    server_payload = Column(JSON, nullable=False)
    resolution_status = Column(String(50), default="PENDING_REVIEW", nullable=False, index=True)  # PENDING_REVIEW, AUTO_RESOLVED, OVERWRITTEN, REJECTED
    resolved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    resolved_by = relationship("User")

    def __repr__(self) -> str:
        return f"<ConflictRecord {self.entity_type} {self.entity_id} status={self.resolution_status}>"
