from sqlalchemy import Column, String
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(30), default="CITIZEN", index=True, nullable=False)
    phone = Column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
