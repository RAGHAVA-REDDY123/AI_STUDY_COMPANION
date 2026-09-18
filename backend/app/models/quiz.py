import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base

class QuizStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    FAILED = "FAILED"

class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    OPEN_ENDED = "OPEN_ENDED"

class QuestionDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class MistakeType(str, enum.Enum):
    CONCEPTUAL_MISUNDERSTANDING = "CONCEPTUAL_MISUNDERSTANDING"
    FACTUAL_ERROR = "FACTUAL_ERROR"
    MISSING_CONCEPT = "MISSING_CONCEPT"
    REASONING_ERROR = "REASONING_ERROR"
    CALCULATION_ERROR = "CALCULATION_ERROR"
    PARTIAL_UNDERSTANDING = "PARTIAL_UNDERSTANDING"

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(QuizStatus), default=QuizStatus.IN_PROGRESS, nullable=False, index=True)
    total_questions = Column(Integer, default=0, nullable=False)
    completed_questions = Column(Integer, default=0, nullable=False)
    score_percentage = Column(Float, default=0.0, nullable=False)
    overall_score = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin", order_by="Question.question_order")
    answers = relationship("QuestionAnswer", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin")
    mistakes = relationship("QuizMistake", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    concept_id = Column(Uuid, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(QuestionDifficulty), default=QuestionDifficulty.MEDIUM, nullable=False)
    question_order = Column(Integer, default=1, nullable=False)
    prompt = Column(Text, nullable=False)
    options = Column(JSON, default=list, nullable=False)  # For MCQ: [{key: "A", text: "..."}]
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    expected_concepts = Column(JSON, default=list, nullable=False)  # Expected key terms for open-ended rubric
    source_chunk_ids = Column(JSON, default=list, nullable=False)  # Tracking RAG source chunks
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, ANSWERED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    quiz = relationship("Quiz", back_populates="questions", lazy="selectin")
    concept = relationship("Concept", lazy="selectin")
    answers = relationship("QuestionAnswer", back_populates="question", cascade="all, delete-orphan", lazy="selectin")
    mistakes = relationship("QuizMistake", back_populates="question", cascade="all, delete-orphan", lazy="selectin")

class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    feedback = Column(Text, nullable=True)
    evaluation = Column(JSON, default=dict, nullable=False)  # Multi-factor rubric evaluation
    rubric_feedback = Column(JSON, default=dict, nullable=False)  # Backwards-compat
    answered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    quiz = relationship("Quiz", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class QuizMistake(Base):
    __tablename__ = "quiz_mistakes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Uuid, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    mistake_type = Column(Enum(MistakeType), default=MistakeType.CONCEPTUAL_MISUNDERSTANDING, nullable=False, index=True)
    mistake_description = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    quiz = relationship("Quiz", back_populates="mistakes")
    question = relationship("Question", back_populates="mistakes")
    concept = relationship("Concept", lazy="selectin")
