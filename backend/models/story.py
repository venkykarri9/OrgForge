"""SQLAlchemy model for a Jira story moving through the OrgForge pipeline."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base
import enum


class StoryStatus(str, enum.Enum):
    BACKLOG = "BACKLOG"
    STORY_LOADED = "STORY_LOADED"
    TDD_DRAFTED = "TDD_DRAFTED"
    TDD_APPROVED = "TDD_APPROVED"
    IN_DEVELOPMENT = "IN_DEVELOPMENT"
    PACKAGE_READY = "PACKAGE_READY"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    COMMITTED = "COMMITTED"
    PR_OPEN = "PR_OPEN"
    MERGED = "MERGED"


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    jira_issue_key: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. PROJ-123
    jira_summary: Mapped[str] = mapped_column(String(512), nullable=False)
    jira_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jira_acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[StoryStatus] = mapped_column(
        SAEnum(StoryStatus), default=StoryStatus.BACKLOG, nullable=False
    )

    # AI-generated artefacts
    tdd_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    mermaid_erd: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Git / deploy artefacts
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    package_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_pr_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    deploy_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="stories")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="story")
