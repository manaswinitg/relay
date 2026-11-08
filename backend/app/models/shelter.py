from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Shelter(Base, TimestampMixin):
    __tablename__ = "shelters"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    client_assigned_uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    total_capacity = Column(Integer, default=0, nullable=False)
    current_occupancy = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="OPEN", index=True, nullable=False)
    contact_phone = Column(String(50), nullable=True)
    version = Column(Integer, default=1, nullable=False)

    inventories = relationship("ShelterInventory", back_populates="shelter", cascade="all, delete-orphan")
    assistance_requests = relationship("AssistanceRequest", back_populates="shelter")

    def __repr__(self) -> str:
        return f"<Shelter {self.name} (v{self.version})>"
