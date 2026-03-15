"""SQLAlchemy model for a Jira project linked to a Salesforce org."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )

    jira_project_key: Mapped[str] = mapped_column(String(32), nullable=False)
    jira_project_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # GitHub repo for the SF org source
    github_repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_default_branch: Mapped[str] = mapped_column(String(128), default="main")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    org: Mapped["Org"] = relationship("Org", back_populates="projects")
    stories: Mapped[list["Story"]] = relationship("Story", back_populates="project")
