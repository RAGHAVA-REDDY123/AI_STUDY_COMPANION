from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import Project
from app.models.quiz import Quiz, Question, QuestionAnswer, QuizStatus
from app.schemas.quiz import (
    QuizCreateRequest,
    QuizStartResponse,
    QuestionPublicOut,
    QuizStateOut,
    AnswerSubmitRequest,
    AnswerEvaluationOut,
    NextQuestionOut,
    QuizResultsOut,
    QuizOut,
    QuizResultOut,
    QuizSubmitPayload
)
from app.services.quiz_service import QuizService

router = APIRouter(tags=["Adaptive Quiz"])

def _to_question_public(q: Question) -> QuestionPublicOut:
    return QuestionPublicOut(
        id=q.id,
        quiz_id=q.quiz_id,
        concept_id=q.concept_id,
        concept_name=q.concept.name if getattr(q, "concept", None) else None,
        question_type=q.question_type,
        difficulty=q.difficulty,
        question_order=q.question_order,
        prompt=q.prompt,
        options=q.options or []
    )

# --- PRD Step 1: Start Quiz (POST /api/v1/projects/{project_id}/quizzes) ---

@router.post("/projects/{project_id}/quizzes", response_model=QuizStartResponse, status_code=status.HTTP_201_CREATED)
async def start_adaptive_quiz(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: Optional[QuizCreateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    PRD 18: Start an adaptive quiz session inside current project boundary.
    Determines initial concept and difficulty, retrieves project RAG context,
    and returns Question 1.
    """
    quiz_svc = QuizService(db)
    req = payload or QuizCreateRequest()
    quiz, first_q = await quiz_svc.start_quiz(
        project=project,
        user=current_user,
        question_count=req.question_count,
        question_types=req.question_types
    )
    return QuizStartResponse(
        quiz_id=quiz.id,
        question_number=1,
        total_questions=quiz.total_questions,
        question=_to_question_public(first_q)
    )

# --- PRD Step 2: Get Current Quiz State (GET /api/v1/quizzes/{quiz_id}) ---

@router.get("/quizzes/{quiz_id}", response_model=QuizStateOut)
async def get_quiz_state(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    PRD 19: Query quiz progress and active pending question.
    Enforces project/quiz ownership and never exposes correct answers before submission.
    """
    quiz_svc = QuizService(db)
    state = await quiz_svc.get_quiz_state(quiz_id=quiz_id, user=current_user)
    current_q = state["current_question"]
    return QuizStateOut(
        quiz_id=state["quiz_id"],
        project_id=state["project_id"],
        status=state["status"],
        total_questions=state["total_questions"],
        completed_questions=state["completed_questions"],
        score_percentage=state["score_percentage"],
        current_question=_to_question_public(current_q) if current_q else None
    )

# --- Current Question (GET /api/v1/quizzes/{quiz_id}/questions/current) ---

@router.get("/quizzes/{quiz_id}/questions/current", response_model=Optional[QuestionPublicOut])
async def get_current_question(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    quiz_svc = QuizService(db)
    q = await quiz_svc.get_current_question(quiz_id=quiz_id, user=current_user)
    return _to_question_public(q) if q else None

# --- PRD Step 3: Submit Answer (POST /api/v1/quizzes/{quiz_id}/questions/{question_id}/answer) ---

@router.post("/quizzes/{quiz_id}/questions/{question_id}/answer", response_model=AnswerEvaluationOut)
async def submit_question_answer(
    quiz_id: UUID,
    question_id: UUID,
    payload: AnswerSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    PRD 20-24: Submit answer for immediate evaluation.
    Deterministic evaluation for MCQ; Rubric evaluation via Gemini 2.5 Flash for Open-Ended.
    Records mistakes, updates concept mastery, and advances question state.
    """
    quiz_svc = QuizService(db)
    result = await quiz_svc.submit_question_answer(
        quiz_id=quiz_id,
        question_id=question_id,
        user=current_user,
        user_answer=payload.user_answer
    )
    return result

# --- PRD Step 4: Next Question (POST /api/v1/quizzes/{quiz_id}/next) ---

@router.post("/quizzes/{quiz_id}/next", response_model=NextQuestionOut)
async def get_or_generate_next_question(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    PRD 25: Recalculates concept practice priorities and difficulty using accumulated evidence.
    Generates and returns next question, or indicates quiz is ready for completion.
    """
    quiz_svc = QuizService(db)
    next_q, is_completed = await quiz_svc.generate_next_question(quiz_id=quiz_id, user=current_user)
    
    state = await quiz_svc.get_quiz_state(quiz_id=quiz_id, user=current_user)
    q_num = state["completed_questions"] + 1 if next_q else state["completed_questions"]

    return NextQuestionOut(
        quiz_id=quiz_id,
        question_number=q_num,
        total_questions=state["total_questions"],
        is_completed=is_completed,
        question=_to_question_public(next_q) if next_q else None
    )

# --- PRD Step 5: Complete Quiz (POST /api/v1/quizzes/{quiz_id}/complete) ---

@router.post("/quizzes/{quiz_id}/complete", response_model=QuizResultsOut)
async def complete_quiz(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    PRD 26-29: Finalizes quiz, evaluates overall performance, identifies strengths & attention areas,
    updates Growth state, and triggers actionable Recommendations.
    """
    quiz_svc = QuizService(db)
    results = await quiz_svc.complete_quiz(quiz_id=quiz_id, user=current_user)
    return results

# --- PRD Results (GET /api/v1/quizzes/{quiz_id}/results) ---

@router.get("/quizzes/{quiz_id}/results", response_model=QuizResultsOut)
async def get_quiz_results(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    quiz_svc = QuizService(db)
    return await quiz_svc.complete_quiz(quiz_id=quiz_id, user=current_user)

# --- Legacy Backwards-Compatible Routes ---

@router.post("/projects/{project_id}/quizzes/generate", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def legacy_generate_quiz(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    quiz_svc = QuizService(db)
    return await quiz_svc.generate_quiz_for_project(project=project, user=current_user)

@router.get("/projects/{project_id}/quizzes/{quiz_id}", response_model=QuizOut)
async def legacy_get_quiz(
    quiz_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == quiz_id, Quiz.project_id == project.id)
    )
    quiz = (await db.execute(stmt)).scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz

@router.post("/projects/{project_id}/quizzes/{quiz_id}/submit", response_model=QuizResultOut)
async def legacy_submit_quiz(
    quiz_id: UUID,
    payload: QuizSubmitPayload,
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    quiz_svc = QuizService(db)
    return await quiz_svc.evaluate_submission(
        quiz_id=quiz_id,
        payload=payload,
        project=project,
        user=current_user,
        background_tasks=background_tasks
    )
