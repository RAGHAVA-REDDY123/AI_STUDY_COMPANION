import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base

class GrowthState(str, enum.Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    REQUIRING_ATTENTION = "REQUIRING_ATTENTION"

class ConceptMastery(Base):
    __tablename__ = "concept_masteries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery_score = Column(Float, default=0.0, nullable=False)  # 0.0% to 100.0%
    confidence = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0 confidence estimate
    trend_state = Column(Enum(GrowthState), default=GrowthState.STABLE, nullable=False)
    total_attempts = Column(Integer, default=0, nullable=False)
    successful_attempts = Column(Integer, default=0, nullable=False)
    consecutive_mistakes = Column(Integer, default=0, nullable=False)
    last_assessed_at = Column(DateTime(timezone=True), nullable=True)
    last_practiced_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "concept_id", "user_id", name="uq_project_concept_user_mastery"),
    )

    project = relationship("Project", back_populates="masteries")
    concept = relationship("Concept", back_populates="masteries", lazy="selectin")
    history_points = relationship("MasteryHistoryPoint", back_populates="mastery", cascade="all, delete-orphan", order_by="MasteryHistoryPoint.recorded_at")

    @property
    def attempt_count(self) -> int:
        return self.total_attempts

    @property
    def correct_count(self) -> int:
        return self.successful_attempts

    @property
    def incorrect_count(self) -> int:
        return max(0, self.total_attempts - self.successful_attempts)

class MasteryHistoryPoint(Base):
    __tablename__ = "mastery_history_points"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mastery_id = Column(Uuid, ForeignKey("concept_masteries.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    concept_id = Column(Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=True, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, index=True)
    quiz_question_id = Column(Uuid, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True)
    score_snapshot = Column(Float, nullable=False)
    source = Column(String(100), default="QUIZ", nullable=False)
    trigger_event = Column(String(50), nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    mastery = relationship("ConceptMastery", back_populates="history_points")
