from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.quiz import Quiz
from app.models.mastery import ConceptMastery
from app.models.concept import Concept
from app.models.event import ActivityEvent
from app.models.learner_context import LearnerContext
from app.models.observability import (
    AIUsageLog,
    RetrievalLog,
    AIEvaluationRun,
    AIEvaluationResult,
    BackgroundJob,
    JobStatus
)
from app.schemas.admin import (
    AIUsageOut,
    AdminPlatformStatsOut,
    BackgroundJobOut,
    AIOverviewOut,
    RetrievalLogOut,
    AIEvaluationRunOut,
    AIEvaluationRunDetailOut,
    EvaluationRunRequest,
    AdminUserSummaryOut,
    AdminUserJourneyDetailOut,
    ActivityEventAdminItem,
    ActivityEventAdminResponse
)
from evaluations.services.evaluation_service import EvaluationService
from evaluations.services.regression_service import RegressionService

router = APIRouter(prefix="/admin", tags=["Admin Dashboard & AI Observability"])

# --- 1. Basic Stats & Legacy Endpoints ---

@router.get("/stats", response_model=AdminPlatformStatsOut)
async def get_admin_stats(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    spaces_count = (await db.execute(select(func.count(Space.id)))).scalar() or 0
    projects_count = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    materials_count = (await db.execute(select(func.count(Material.id)))).scalar() or 0
    
    total_tokens = (await db.execute(select(func.sum(AIUsageLog.total_tokens)))).scalar() or 0
    total_cost = (await db.execute(select(func.sum(AIUsageLog.estimated_cost_usd)))).scalar() or 0.0
    
    active_jobs = (await db.execute(
        select(func.count(BackgroundJob.id)).where(BackgroundJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]))
    )).scalar() or 0

    failed_jobs = (await db.execute(
        select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.FAILED)
    )).scalar() or 0

    return {
        "total_users": users_count,
        "total_spaces": spaces_count,
        "total_projects": projects_count,
        "total_materials": materials_count,
        "total_ai_tokens": total_tokens,
        "total_estimated_cost_usd": float(total_cost),
        "active_background_jobs": active_jobs,
        "failed_background_jobs": failed_jobs
    }

@router.get("/ai-telemetry", response_model=list[AIUsageOut])
async def list_ai_telemetry(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50
):
    stmt = select(AIUsageLog).order_by(AIUsageLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/jobs", response_model=list[BackgroundJobOut])
async def list_background_jobs(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50
):
    stmt = select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

# --- 2. Advanced AI Engineering Observability Endpoints ---

@router.get("/ai/overview", response_model=AIOverviewOut)
async def get_ai_overview(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    total_reqs = (await db.execute(select(func.count(AIUsageLog.id)))).scalar() or 0
    success_reqs = (await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.status_code == "SUCCESS")
    )).scalar() or 0
    failed_reqs = (await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.status_code == "FAILED")
    )).scalar() or 0

    avg_latency = (await db.execute(select(func.avg(AIUsageLog.latency_ms)))).scalar() or 0.0
    total_toks = (await db.execute(select(func.sum(AIUsageLog.total_tokens)))).scalar() or 0
    total_cost = (await db.execute(select(func.sum(AIUsageLog.estimated_cost_usd)))).scalar() or 0.0

    # Requests by Feature
    feat_rows = (await db.execute(
        select(AIUsageLog.feature, func.count(AIUsageLog.id)).group_by(AIUsageLog.feature)
    )).all()
    requests_by_feature = {row[0]: row[1] for row in feat_rows}

    # Requests by Model
    model_rows = (await db.execute(
        select(AIUsageLog.model_name, func.count(AIUsageLog.id)).group_by(AIUsageLog.model_name)
    )).all()
    requests_by_model = {row[0]: row[1] for row in model_rows}

    # Errors by Type
    err_rows = (await db.execute(
        select(AIUsageLog.error_type, func.count(AIUsageLog.id))
        .where(AIUsageLog.error_type.isnot(None))
        .group_by(AIUsageLog.error_type)
    )).all()
    errors_by_type = {row[0]: row[1] for row in err_rows}

    # Recent Requests over Time (group by day/hour for chart)
    recent_logs = (await db.execute(
        select(AIUsageLog)
        .order_by(AIUsageLog.created_at.asc())
        .limit(100)
    )).scalars().all()

    requests_over_time = []
    latency_distribution = []
    for log in recent_logs:
        t_label = log.created_at.strftime("%H:%M:%S")
        requests_over_time.append({
            "time": t_label,
            "tokens": log.total_tokens or 0,
            "latency_ms": log.latency_ms,
            "feature": log.feature,
            "status": log.status_code
        })
        latency_distribution.append({
            "request_id": log.request_id or str(log.id)[:8],
            "feature": log.feature,
            "latency_ms": log.latency_ms,
            "model": log.model_name
        })

    success_rate = round((success_reqs / total_reqs * 100), 2) if total_reqs > 0 else 100.0

    return {
        "total_requests": total_reqs,
        "success_requests": success_reqs,
        "failed_requests": failed_reqs,
        "success_rate": success_rate,
        "avg_latency_ms": round(float(avg_latency), 1),
        "total_tokens": total_toks,
        "total_estimated_cost_usd": float(total_cost),
        "requests_by_feature": requests_by_feature,
        "requests_by_model": requests_by_model,
        "errors_by_type": errors_by_type,
        "requests_over_time": requests_over_time[-40:],
        "latency_distribution": latency_distribution[-30:]
    }

@router.get("/ai/usage", response_model=list[AIUsageOut])
async def list_ai_usage_logs(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    feature: Optional[str] = None,
    model_name: Optional[str] = None,
    status_code: Optional[str] = None,
    request_id: Optional[str] = None,
    project_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    stmt = select(AIUsageLog)
    if feature:
        stmt = stmt.where(AIUsageLog.feature == feature.upper())
    if model_name:
        stmt = stmt.where(AIUsageLog.model_name == model_name)
    if status_code:
        stmt = stmt.where(AIUsageLog.status_code == status_code.upper())
    if request_id:
        stmt = stmt.where(AIUsageLog.request_id == request_id)
    if project_id:
        stmt = stmt.where(AIUsageLog.project_id == project_id)

    stmt = stmt.order_by(AIUsageLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/ai/usage/{request_id}")
async def get_ai_request_trace(
    request_id: str,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    usage_stmt = select(AIUsageLog).where(AIUsageLog.request_id == request_id)
    usage = (await db.execute(usage_stmt)).scalars().all()
    if not usage:
        raise HTTPException(status_code=404, detail="Request ID not found in AI usage telemetry.")

    retrieval_stmt = select(RetrievalLog).where(RetrievalLog.request_id == request_id)
    retrievals = (await db.execute(retrieval_stmt)).scalars().all()

    return {
        "request_id": request_id,
        "usage_logs": [AIUsageOut.model_validate(u) for u in usage],
        "retrieval_logs": [RetrievalLogOut.model_validate(r) for r in retrievals]
    }

@router.get("/ai/retrieval", response_model=list[RetrievalLogOut])
async def list_retrieval_logs(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=100)
):
    stmt = select(RetrievalLog)
    if project_id:
        stmt = stmt.where(RetrievalLog.project_id == project_id)
    stmt = stmt.order_by(RetrievalLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/ai/errors", response_model=list[AIUsageOut])
async def list_ai_errors(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    error_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    stmt = select(AIUsageLog).where(AIUsageLog.status_code == "FAILED")
    if error_type:
        stmt = stmt.where(AIUsageLog.error_type == error_type)
    stmt = stmt.order_by(AIUsageLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

# --- 3. Evaluation & Regression Endpoints ---

@router.get("/ai/evaluations", response_model=list[AIEvaluationRunOut])
async def list_evaluation_runs(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    evaluation_type: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100)
):
    stmt = select(AIEvaluationRun)
    if evaluation_type:
        stmt = stmt.where(AIEvaluationRun.evaluation_type == evaluation_type.upper())
    stmt = stmt.order_by(AIEvaluationRun.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/ai/evaluations/{run_id}", response_model=AIEvaluationRunDetailOut)
async def get_evaluation_run_detail(
    run_id: UUID,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = (
        select(AIEvaluationRun)
        .where(AIEvaluationRun.id == run_id)
        .options(selectinload(AIEvaluationRun.results))
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run

@router.post("/ai/evaluations/run", response_model=AIEvaluationRunOut)
async def trigger_evaluation_run(
    payload: EvaluationRunRequest,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    service = EvaluationService(db)
    eval_run = await service.run_suite(
        suite_type=payload.evaluation_type,
        run_name=payload.run_name
    )
    return eval_run

@router.get("/ai/evaluations/compare")
async def compare_evaluation_runs(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    run_a: UUID = Query(..., description="Baseline Run ID"),
    run_b: UUID = Query(..., description="Target Run ID")
):
    service = RegressionService(db)
    try:
        comparison = await service.compare_runs(run_a, run_b)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- 4. Learner Journeys & Platform Activity Audit (PRD §16, §17) ---

@router.get("/users", response_model=list[AdminUserSummaryOut])
async def list_admin_users(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    PRD §16: Lists all registered learners with comprehensive aggregates
    (Spaces, Projects, Quizzes, Average Mastery %, Total AI Spend).
    """
    users_stmt = select(User).order_by(User.created_at.desc())
    users = (await db.execute(users_stmt)).scalars().all()

    summary_list = []
    for u in users:
        spaces_count = (await db.execute(
            select(func.count(Space.id)).where(Space.user_id == u.id)
        )).scalar() or 0

        projects_count = (await db.execute(
            select(func.count(Project.id)).where(Project.user_id == u.id)
        )).scalar() or 0

        quizzes_count = (await db.execute(
            select(func.count(Quiz.id)).where(Quiz.user_id == u.id)
        )).scalar() or 0

        avg_mastery = (await db.execute(
            select(func.avg(ConceptMastery.mastery_score)).where(ConceptMastery.user_id == u.id)
        )).scalar() or 0.0

        ai_stats = (await db.execute(
            select(
                func.sum(AIUsageLog.total_tokens),
                func.sum(AIUsageLog.estimated_cost_usd)
            ).where(AIUsageLog.user_id == u.id)
        )).first()

        total_tokens = (ai_stats[0] if ai_stats and ai_stats[0] else 0)
        total_cost = float(ai_stats[1] if ai_stats and ai_stats[1] else 0.0)

        summary_list.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_active": u.is_active,
            "created_at": u.created_at,
            "spaces_count": spaces_count,
            "projects_count": projects_count,
            "quizzes_taken": quizzes_count,
            "average_mastery": round(float(avg_mastery), 1),
            "total_ai_tokens": total_tokens,
            "total_ai_cost": round(total_cost, 4)
        })

    return summary_list


@router.get("/users/{user_id}/journey", response_model=AdminUserJourneyDetailOut)
async def get_user_learning_journey(
    user_id: UUID,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    PRD §16, §17: Complete individual learner drill-down.
    Inspects user spaces, projects, concept mastery status, quiz outcomes,
    diagnosed cognitive flaws, and AI consumption.
    """
    target_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Spaces & Projects
    spaces_res = (await db.execute(
        select(Space).where(Space.user_id == user_id).order_by(Space.created_at.desc())
    )).scalars().all()
    spaces = [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "visual_tag": s.visual_tag,
            "created_at": s.created_at.isoformat()
        }
        for s in spaces_res
    ]

    projects_res = (await db.execute(
        select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
    )).scalars().all()
    projects = [
        {
            "id": str(p.id),
            "space_id": str(p.space_id),
            "name": p.name,
            "learning_goal": p.learning_goal,
            "created_at": p.created_at.isoformat()
        }
        for p in projects_res
    ]

    # 2. Concept Mastery Breakdown
    mastery_stmt = (
        select(ConceptMastery, Concept.name.label("concept_name"), Concept.importance_score)
        .join(Concept, ConceptMastery.concept_id == Concept.id)
        .where(ConceptMastery.user_id == user_id)
        .order_by(ConceptMastery.mastery_score.asc())
    )
    mastery_rows = (await db.execute(mastery_stmt)).all()
    mastery_breakdown = [
        {
            "concept_id": str(row[0].concept_id),
            "project_id": str(row[0].project_id),
            "concept_name": row[1],
            "importance_score": row[2],
            "mastery_score": row[0].mastery_score,
            "total_attempts": row[0].total_attempts,
            "consecutive_mistakes": row[0].consecutive_mistakes,
            "growth_state": row[0].trend_state.value if hasattr(row[0].trend_state, "value") else str(row[0].trend_state),
            "updated_at": row[0].updated_at.isoformat() if row[0].updated_at else None
        }
        for row in mastery_rows
    ]

    # 3. Quiz History
    quizzes_res = (await db.execute(
        select(Quiz).where(Quiz.user_id == user_id).order_by(Quiz.started_at.desc()).limit(20)
    )).scalars().all()
    quiz_history = [
        {
            "id": str(q.id),
            "project_id": str(q.project_id),
            "title": f"Quiz ({q.total_questions} Qs)",
            "score": round(float(q.score_percentage or q.overall_score or 0.0), 1),
            "status": q.status.value if hasattr(q.status, "value") else str(q.status),
            "created_at": q.started_at.isoformat()
        }
        for q in quizzes_res
    ]

    # 4. AI Usage stats
    ai_rows = (await db.execute(
        select(AIUsageLog).where(AIUsageLog.user_id == user_id)
    )).scalars().all()
    total_tokens = sum(l.total_tokens or 0 for l in ai_rows)
    total_cost = sum(l.estimated_cost_usd or 0.0 for l in ai_rows)
    feature_counts: dict[str, int] = {}
    for l in ai_rows:
        feature_counts[l.feature] = feature_counts.get(l.feature, 0) + 1

    ai_usage = {
        "total_requests": len(ai_rows),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "feature_breakdown": feature_counts
    }

    # 5. Diagnosed Misconceptions (LearnerContext)
    learner_contexts = (await db.execute(
        select(LearnerContext).where(LearnerContext.user_id == user_id)
    )).scalars().all()
    all_misconceptions = []
    for lc in learner_contexts:
        for m in (lc.diagnosed_misconceptions or []):
            all_misconceptions.append({
                "project_id": str(lc.project_id),
                **(m if isinstance(m, dict) else {"text": str(m)})
            })

    # 6. Recent Activity
    recent_events_res = (await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.user_id == user_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(15)
    )).scalars().all()
    recent_activity = [
        {
            "id": str(e.id),
            "project_id": str(e.project_id) if e.project_id else None,
            "event_type": e.event_type,
            "payload": e.payload,
            "created_at": e.created_at.isoformat()
        }
        for e in recent_events_res
    ]

    return {
        "user": {
            "id": str(target_user.id),
            "email": target_user.email,
            "full_name": target_user.full_name,
            "role": target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role),
            "created_at": target_user.created_at.isoformat()
        },
        "spaces": spaces,
        "projects": projects,
        "mastery_breakdown": mastery_breakdown,
        "quiz_history": quiz_history,
        "ai_usage": ai_usage,
        "diagnosed_misconceptions": all_misconceptions,
        "recent_activity": recent_activity
    }


@router.get("/activity", response_model=ActivityEventAdminResponse)
async def list_admin_activities(
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    PRD §16, §17: Filterable platform activity audit log.
    Enables administrators to filter events across users, projects, and specific event types.
    """
    stmt = (
        select(
            ActivityEvent,
            User.email.label("user_email"),
            Project.name.label("project_name")
        )
        .outerjoin(User, ActivityEvent.user_id == User.id)
        .outerjoin(Project, ActivityEvent.project_id == Project.id)
    )

    count_stmt = select(func.count(ActivityEvent.id))

    if user_id:
        stmt = stmt.where(ActivityEvent.user_id == user_id)
        count_stmt = count_stmt.where(ActivityEvent.user_id == user_id)
    if project_id:
        stmt = stmt.where(ActivityEvent.project_id == project_id)
        count_stmt = count_stmt.where(ActivityEvent.project_id == project_id)
    if event_type:
        stmt = stmt.where(ActivityEvent.event_type == event_type)
        count_stmt = count_stmt.where(ActivityEvent.event_type == event_type)

    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(ActivityEvent.created_at.desc()).offset(offset).limit(limit)
    results = (await db.execute(stmt)).all()

    items = []
    for event, u_email, p_name in results:
        items.append({
            "id": event.id,
            "user_id": event.user_id,
            "user_email": u_email,
            "project_id": event.project_id,
            "project_name": p_name,
            "event_type": event.event_type,
            "payload": event.payload or {},
            "created_at": event.created_at
        })

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

