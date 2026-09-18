import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), nullable=True, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    feature = Column(String(50), nullable=False, index=True)  # TUTOR, QUIZ, ASSESSMENT, RECOMMENDATION, DOCUMENT, EMBEDDING
    operation = Column(String(64), nullable=False, default="generate_text", index=True)  # generate_text, generate_stream, generate_structured, evaluate_answer
    provider = Column(String(50), nullable=False, default="gemini")
    model_name = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    status_code = Column(String(50), default="SUCCESS", nullable=False)
    error_type = Column(String(64), nullable=True, index=True)
    error_details = Column(Text, nullable=True)
    prompt_version = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id = Column(String(64), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    retrieval_method = Column(String(50), default="hybrid_rrf", nullable=False)
    top_k = Column(Integer, default=20, nullable=False)
    final_k = Column(Integer, default=6, nullable=False)
    retrieved_chunk_ids = Column(JSON, default=list, nullable=False)
    similarity_scores = Column(JSON, default=dict, nullable=False)
    retrieval_latency_ms = Column(Integer, default=0, nullable=False)
    reranking_latency_ms = Column(Integer, default=0, nullable=False)
    final_chunk_ids = Column(JSON, default=list, nullable=False)
    has_sufficient_evidence = Column(Boolean, default=True, nullable=False)
    retrieval_version = Column(String(50), default="hybrid_rrf_v1.0_bge384", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class AIEvaluationRun(Base):
    __tablename__ = "ai_evaluation_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    run_name = Column(String(128), nullable=False)
    evaluation_type = Column(String(50), nullable=False, index=True)  # TUTOR, RETRIEVAL, ASSESSMENT, RECOMMENDATION, FULL_SUITE
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(64), nullable=True)
    retrieval_version = Column(String(64), nullable=True)
    status = Column(String(50), default="COMPLETED", nullable=False, index=True)  # RUNNING, COMPLETED, FAILED
    total_cases = Column(Integer, default=0, nullable=False)
    passed_cases = Column(Integer, default=0, nullable=False)
    failed_cases = Column(Integer, default=0, nullable=False)
    metrics = Column(JSON, default=dict, nullable=False)  # aggregate metrics dictionary
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    results = relationship("AIEvaluationResult", back_populates="run", cascade="all, delete-orphan")


class AIEvaluationResult(Base):
    __tablename__ = "ai_evaluation_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id = Column(Uuid, ForeignKey("ai_evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    feature = Column(String(50), nullable=False, index=True)
    input_data = Column(JSON, default=dict, nullable=False)
    expected_output = Column(JSON, default=dict, nullable=False)
    actual_output = Column(JSON, default=dict, nullable=False)
    score = Column(Numeric(5, 4), default=0.0000, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    metrics = Column(JSON, default=dict, nullable=False)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    run = relationship("AIEvaluationRun", back_populates="results")


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Uuid, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
