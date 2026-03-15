"""SQLAlchemy model for a connected Salesforce org."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instance_url: Mapped[str] = mapped_column(String(512), nullable=False)
    org_id: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)  # SF 18-char org ID
    username: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted OAuth tokens
    access_token_enc: Mapped[str] = mapped_column(String(1024), nullable=False)
    refresh_token_enc: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="org")
