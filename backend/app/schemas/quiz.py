from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, Any
from datetime import datetime
from app.models.quiz import QuizStatus, QuestionType, QuestionDifficulty

# --- Client Request Models ---

class QuizCreateRequest(BaseModel):
    question_count: int = Field(default=5, ge=1, le=20, description="Total number of questions for this quiz session")
    question_types: list[QuestionType] = Field(
        default=[QuestionType.MCQ, QuestionType.OPEN_ENDED],
        description="Allowed question formats for adaptive selection"
    )

class AnswerSubmitRequest(BaseModel):
    user_answer: str = Field(..., min_length=1, description="Learner answer (option key for MCQ or explanation for open-ended)")

# Legacy submit payload
class AnswerSubmission(BaseModel):
    question_id: UUID
    user_answer: str

class QuizSubmitPayload(BaseModel):
    answers: list[AnswerSubmission]

# --- Client Response Models ---

class MCQOption(BaseModel):
    key: str
    text: str

class QuestionPublicOut(BaseModel):
    id: UUID
    quiz_id: UUID
    concept_id: Optional[UUID] = None
    concept_name: Optional[str] = None
    question_type: QuestionType
    difficulty: QuestionDifficulty
    question_order: int
    prompt: str
    options: list[dict[str, Any]] = []

    class Config:
        from_attributes = True

class QuizStartResponse(BaseModel):
    quiz_id: UUID
    question_number: int
    total_questions: int
    question: QuestionPublicOut

class QuizStateOut(BaseModel):
    quiz_id: UUID
    project_id: UUID
    status: QuizStatus
    total_questions: int
    completed_questions: int
    score_percentage: float
    current_question: Optional[QuestionPublicOut] = None

class AnswerEvaluationOut(BaseModel):
    question_id: UUID
    is_correct: bool
    score: float
    correct_answer: str
    explanation: str
    feedback: str
    evaluation: dict[str, Any] = {}
    concept_name: Optional[str] = None
    concept_mastery_before: Optional[float] = None
    concept_mastery_after: Optional[float] = None

class NextQuestionOut(BaseModel):
    quiz_id: UUID
    question_number: int
    total_questions: int
    is_completed: bool
    question: Optional[QuestionPublicOut] = None

class MasteryDelta(BaseModel):
    concept_id: UUID
    concept_name: str
    before: float
    after: float
    delta: float

class QuizResultsOut(BaseModel):
    quiz_id: UUID
    project_id: UUID
    status: QuizStatus
    score: float
    questions_attempted: int
    questions_correct: int
    concepts_assessed: int
    strengths: list[str] = []
    attention_areas: list[str] = []
    mastery_changes: list[MasteryDelta] = []
    recommendation: Optional[str] = None
    recommendation_action: Optional[str] = None
    recommendation_id: Optional[UUID] = None

# --- Legacy Backwards Compatibility Schemas ---

class QuestionOut(BaseModel):
    id: UUID
    quiz_id: UUID
    concept_id: Optional[UUID] = None
    question_type: QuestionType
    difficulty: QuestionDifficulty
    prompt: str
    options: list[dict[str, Any]] = []

    class Config:
        from_attributes = True

class QuestionResultOut(BaseModel):
    id: UUID
    prompt: str
    question_type: QuestionType
    difficulty: QuestionDifficulty
    correct_answer: str
    explanation: str
    user_answer: str
    is_correct: bool
    score: float
    rubric_feedback: dict[str, Any] = {}

class QuizOut(BaseModel):
    id: UUID
    project_id: UUID
    status: QuizStatus
    total_questions: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime]
    questions: list[QuestionOut] = []

    class Config:
        from_attributes = True

class QuizResultOut(BaseModel):
    id: UUID
    project_id: UUID
    status: QuizStatus
    score_percentage: float
    completed_at: Optional[datetime]
    results: list[QuestionResultOut] = []
