from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime

class MasteryTimelinePoint(BaseModel):
    date: str
    concept_name: str
    score: float

class QuizHistoryPoint(BaseModel):
    quiz_id: UUID
    completed_at: str
    score_percentage: float
    total_questions: int
    correct_count: int

class ConceptMetricItem(BaseModel):
    concept_id: UUID
    concept_name: str
    mastery_score: float
    trend_state: str  # IMPROVING, STABLE, REQUIRING_ATTENTION
    total_attempts: int
    successful_attempts: int
    consecutive_mistakes: int
    last_assessed_at: Optional[datetime] = None

class MistakeDistributionItem(BaseModel):
    mistake_type: str
    count: int

class DailyActivityPoint(BaseModel):
    date: str
    count: int

class ActivityEventItem(BaseModel):
    id: UUID
    event_type: str
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    created_at: datetime
    payload: dict[str, Any]

class ProjectAnalyticsOverview(BaseModel):
    overall_mastery: float
    mastery_status: str
    total_quizzes_completed: int
    average_quiz_score: float
    total_questions_answered: int
    accuracy_rate: float
    streak_days: int
    total_materials: int
    total_chunks: int
    total_concepts: int
    ai_queries_count: int

class ProjectAnalyticsOut(BaseModel):
    overview: ProjectAnalyticsOverview
    concept_metrics: list[ConceptMetricItem]
    quiz_history: list[QuizHistoryPoint]
    mastery_timeline: list[MasteryTimelinePoint]
    mistake_distribution: list[MistakeDistributionItem]
    daily_activity: list[DailyActivityPoint]
    recent_events: list[ActivityEventItem]

class ProjectLeaderboardItem(BaseModel):
    project_id: UUID
    project_name: str
    space_name: str
    average_mastery: float
    quizzes_count: int
    materials_count: int

class GlobalAnalyticsOverview(BaseModel):
    total_spaces: int
    total_projects: int
    total_materials: int
    total_quizzes_completed: int
    platform_average_mastery: float
    overall_accuracy_rate: float
    streak_days: int
    total_ai_interactions: int

class GlobalAnalyticsOut(BaseModel):
    overview: GlobalAnalyticsOverview
    projects_leaderboard: list[ProjectLeaderboardItem]
    daily_activity: list[DailyActivityPoint]
    recent_events: list[ActivityEventItem]
