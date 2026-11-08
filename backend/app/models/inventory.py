from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, get_utc_now


class ResourceType(Base):
    __tablename__ = "resource_types"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # WATER, FOOD, MEDICAL, SHELTER_SUPPLIES, POWER, SANITATION
    unit = Column(String(30), nullable=False)  # LITERS, MEALS, KITS, PERSONS, UNITS
    is_critical = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    inventories = relationship("ShelterInventory", back_populates="resource_type")

    def __repr__(self) -> str:
        return f"<ResourceType {self.code}>"


class ShelterInventory(Base):
    __tablename__ = "shelter_inventories"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    shelter_id = Column(String(36), ForeignKey("shelters.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type_id = Column(String(36), ForeignKey("resource_types.id"), nullable=False, index=True)
    quantity = Column(Float, default=0.0, nullable=False)
    min_threshold = Column(Float, default=10.0, nullable=False)
    last_updated_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    shelter = relationship("Shelter", back_populates="inventories")
    resource_type = relationship("ResourceType", back_populates="inventories")
    last_updated_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("shelter_id", "resource_type_id", name="uq_shelter_resource"),
    )

    def __repr__(self) -> str:
        return f"<ShelterInventory shelter={self.shelter_id} qty={self.quantity} v={self.version}>"
