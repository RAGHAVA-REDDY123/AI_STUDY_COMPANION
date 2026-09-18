import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base

class LearnerContext(Base):
    """
    PRD §11 Persistent Learner Context.
    Maintains a persistent, evolving representation of student strengths, weaknesses,
    diagnosed cognitive misconceptions, and preferred explanations across sessions.
    """
    __tablename__ = "learner_contexts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Persistent cognitive state
    strengths = Column(JSON, default=list, nullable=False)  # list of concept names
    weaknesses = Column(JSON, default=list, nullable=False)  # list of struggling concepts
    diagnosed_misconceptions = Column(JSON, default=list, nullable=False)  # [{concept, diagnosis, date, material_citation}]
    tutor_preferences = Column(JSON, default=dict, nullable=False)  # {explanation_style, target_pace}
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project_learner_context"),
    )

    user = relationship("User")
    project = relationship("Project")
