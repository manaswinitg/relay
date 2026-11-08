from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, get_utc_now


class EmergencyReport(Base):
    __tablename__ = "emergency_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    client_assigned_uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    reporter_name = Column(String(150), nullable=True)
    contact_info = Column(String(150), nullable=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    address_hint = Column(Text, nullable=True)
    category = Column(String(50), default="OTHER", index=True, nullable=False)
    urgency = Column(String(30), default="MEDIUM", index=True, nullable=False)
    status = Column(String(30), default="SUBMITTED", index=True, nullable=False)
    raw_text = Column(Text, nullable=False)
    ai_summary = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    is_duplicate = Column(Boolean, default=False, index=True, nullable=False)
    duplicate_of_report_id = Column(String(36), ForeignKey("emergency_reports.id"), nullable=True)
    verified_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    client_created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    server_received_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    verified_by = relationship("User")
    assistance_requests = relationship("AssistanceRequest", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EmergencyReport {self.id[:8]} ({self.urgency})>"


class AssistanceRequest(Base, TimestampMixin):
    __tablename__ = "assistance_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    client_assigned_uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    emergency_report_id = Column(String(36), ForeignKey("emergency_reports.id", ondelete="CASCADE"), nullable=True, index=True)
    shelter_id = Column(String(36), ForeignKey("shelters.id"), nullable=True, index=True)
    resource_type_id = Column(String(36), ForeignKey("resource_types.id"), nullable=False, index=True)
    requested_quantity = Column(Float, nullable=False)
    fulfilled_quantity = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), default="PENDING", index=True, nullable=False)
    priority_score = Column(Integer, default=50, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    report = relationship("EmergencyReport", back_populates="assistance_requests")
    shelter = relationship("Shelter", back_populates="assistance_requests")
    resource_type = relationship("ResourceType")

    def __repr__(self) -> str:
        return f"<AssistanceRequest {self.id[:8]} status={self.status}>"
