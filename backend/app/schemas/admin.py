from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime

class AIUsageOut(BaseModel):
    id: UUID
    request_id: Optional[str] = None
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    feature: str
    operation: Optional[str] = "generate_text"
    provider: Optional[str] = "gemini"
    model_name: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: int
    estimated_cost_usd: Optional[float] = None
    status_code: str
    error_type: Optional[str] = None
    error_details: Optional[str] = None
    prompt_version: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AdminPlatformStatsOut(BaseModel):
    total_users: int
    total_spaces: int
    total_projects: int
    total_materials: int
    total_ai_tokens: int
    total_estimated_cost_usd: float
    active_background_jobs: int
    failed_background_jobs: int

class BackgroundJobOut(BaseModel):
    id: UUID
    job_type: str
    entity_id: UUID
    idempotency_key: str
    status: str
    attempts: int
    last_error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AIOverviewOut(BaseModel):
    total_requests: int
    success_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    total_tokens: int
    total_estimated_cost_usd: float
    requests_by_feature: dict[str, int]
    requests_by_model: dict[str, int]
    errors_by_type: dict[str, int]
    requests_over_time: list[dict[str, Any]]
    latency_distribution: list[dict[str, Any]]

class RetrievalLogOut(BaseModel):
    id: UUID
    request_id: str
    project_id: UUID
    user_id: Optional[UUID] = None
    query: str
    retrieval_method: str
    top_k: int
    final_k: int
    retrieved_chunk_ids: list[Any]
    similarity_scores: dict[str, Any]
    retrieval_latency_ms: int
    reranking_latency_ms: int
    final_chunk_ids: list[Any]
    has_sufficient_evidence: bool
    retrieval_version: str
    created_at: datetime

    class Config:
        from_attributes = True

class AIEvaluationResultOut(BaseModel):
    id: UUID
    run_id: UUID
    case_id: str
    feature: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    actual_output: dict[str, Any]
    score: float
    passed: bool
    metrics: dict[str, Any]
    failure_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIEvaluationRunOut(BaseModel):
    id: UUID
    run_name: str
    evaluation_type: str
    model: str
    prompt_version: Optional[str] = None
    retrieval_version: Optional[str] = None
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    metrics: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class AIEvaluationRunDetailOut(AIEvaluationRunOut):
    results: list[AIEvaluationResultOut] = []

class EvaluationRunRequest(BaseModel):
    evaluation_type: str = "FULL_SUITE"
    run_name: Optional[str] = None

class AdminUserSummaryOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    spaces_count: int = 0
    projects_count: int = 0
    quizzes_taken: int = 0
    average_mastery: float = 0.0
    total_ai_tokens: int = 0
    total_ai_cost: float = 0.0

    class Config:
        from_attributes = True

class AdminUserJourneyDetailOut(BaseModel):
    user: dict[str, Any]
    spaces: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    mastery_breakdown: list[dict[str, Any]] = []
    quiz_history: list[dict[str, Any]] = []
    ai_usage: dict[str, Any] = {}
    diagnosed_misconceptions: list[dict[str, Any]] = []
    recent_activity: list[dict[str, Any]] = []

class ActivityEventAdminItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    event_type: str
    payload: dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True

class ActivityEventAdminResponse(BaseModel):
    items: list[ActivityEventAdminItem]
    total: int
    limit: int
    offset: int

