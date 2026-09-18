from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.mastery import ConceptMastery, MasteryHistoryPoint
from app.models.quiz import Quiz, QuizStatus, QuestionAnswer, QuizMistake
from app.models.observability import AIUsageLog
from app.models.event import ActivityEvent
from app.schemas.analytics import (
    ProjectAnalyticsOut,
    ProjectAnalyticsOverview,
    ConceptMetricItem,
    QuizHistoryPoint,
    MasteryTimelinePoint,
    MistakeDistributionItem,
    DailyActivityPoint,
    ActivityEventItem,
    GlobalAnalyticsOut,
    GlobalAnalyticsOverview,
    ProjectLeaderboardItem,
)

router = APIRouter(tags=["Learning Analytics & Insights"])

def calculate_streak(event_dates: list[datetime]) -> int:
    """Calculates consecutive active days streak ending today or yesterday."""
    if not event_dates:
        return 0
    unique_days = sorted({d.date() for d in event_dates}, reverse=True)
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    if unique_days[0] != today and unique_days[0] != yesterday:
        return 0

    streak = 0
    expected_day = unique_days[0]
    for d in unique_days:
        if d == expected_day:
            streak += 1
            expected_day -= timedelta(days=1)
        else:
            break
    return streak

@router.get("/projects/{project_id}/analytics", response_model=ProjectAnalyticsOut)
async def get_project_analytics(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    PRD REQUIREMENT: Project Analytics.
    Provides project-level mastery trajectory, quiz performance, cognitive mistake breakdown,
    14-day study velocity, and live audit event trail.
    """
    # 1. Concept Masteries
    c_stmt = (
        select(ConceptMastery)
        .options(selectinload(ConceptMastery.concept))
        .where(
            ConceptMastery.project_id == project.id,
            ConceptMastery.user_id == current_user.id
        )
        .order_by(ConceptMastery.mastery_score.desc())
    )
    mastery_records = (await db.execute(c_stmt)).scalars().all()

    total_concepts = len(mastery_records)
    if total_concepts > 0:
        overall_mastery = sum(m.mastery_score for m in mastery_records) / total_concepts
    else:
        # Fallback: check total concepts defined for project
        total_concepts = (await db.execute(
            select(func.count(Concept.id)).where(Concept.project_id == project.id)
        )).scalar() or 0
        overall_mastery = 0.0

    mastery_status = (
        "Proficient (Mastered)" if overall_mastery >= 75.0
        else "Progressing (Developing)" if overall_mastery >= 45.0
        else "Foundational (Needs Practice)"
    )

    concept_metrics: list[ConceptMetricItem] = []
    for m in mastery_records:
        concept_metrics.append(ConceptMetricItem(
            concept_id=m.concept_id,
            concept_name=m.concept.name if m.concept else "Core Concept",
            mastery_score=round(m.mastery_score, 1),
            trend_state=m.trend_state.value if hasattr(m.trend_state, 'value') else str(m.trend_state),
            total_attempts=m.total_attempts,
            successful_attempts=m.successful_attempts,
            consecutive_mistakes=m.consecutive_mistakes,
            last_assessed_at=m.last_assessed_at
        ))

    # 2. Quiz Performance & History
    q_stmt = (
        select(Quiz)
        .where(
            Quiz.project_id == project.id,
            Quiz.user_id == current_user.id,
            Quiz.status == QuizStatus.COMPLETED
        )
        .order_by(Quiz.completed_at.asc())
    )
    quizzes = (await db.execute(q_stmt)).scalars().all()

    total_quizzes = len(quizzes)
    avg_quiz_score = (sum(q.score_percentage for q in quizzes) / total_quizzes) if total_quizzes > 0 else 0.0

    quiz_history: list[QuizHistoryPoint] = []
    for q in quizzes:
        completed_str = q.completed_at.strftime("%b %d, %H:%M") if q.completed_at else "Recent"
        # Count correct answers
        ans_stmt = select(func.count(QuestionAnswer.id)).where(
            QuestionAnswer.quiz_id == q.id,
            QuestionAnswer.is_correct == True
        )
        correct_count = (await db.execute(ans_stmt)).scalar() or 0
        quiz_history.append(QuizHistoryPoint(
            quiz_id=q.id,
            completed_at=completed_str,
            score_percentage=round(q.score_percentage, 1),
            total_questions=q.total_questions,
            correct_count=correct_count
        ))

    # Answers accuracy rate
    ans_total_stmt = select(func.count(QuestionAnswer.id)).where(
        QuestionAnswer.project_id == project.id,
        QuestionAnswer.user_id == current_user.id
    )
    total_answers = (await db.execute(ans_total_stmt)).scalar() or 0

    ans_correct_stmt = select(func.count(QuestionAnswer.id)).where(
        QuestionAnswer.project_id == project.id,
        QuestionAnswer.user_id == current_user.id,
        QuestionAnswer.is_correct == True
    )
    correct_answers = (await db.execute(ans_correct_stmt)).scalar() or 0
    accuracy_rate = round((correct_answers / total_answers * 100.0), 1) if total_answers > 0 else 0.0

    # 3. Materials & Chunks count
    mat_count = (await db.execute(
        select(func.count(Material.id)).where(Material.project_id == project.id)
    )).scalar() or 0

    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.project_id == project.id)
    )).scalar() or 0

    ai_queries = (await db.execute(
        select(func.count(AIUsageLog.id)).where(
            AIUsageLog.project_id == project.id,
            AIUsageLog.user_id == current_user.id
        )
    )).scalar() or 0

    # 4. Mastery Timeline Points
    hist_stmt = (
        select(MasteryHistoryPoint, Concept.name)
        .join(Concept, MasteryHistoryPoint.concept_id == Concept.id)
        .where(MasteryHistoryPoint.project_id == project.id)
        .order_by(MasteryHistoryPoint.recorded_at.asc())
        .limit(40)
    )
    hist_rows = (await db.execute(hist_stmt)).all()
    mastery_timeline = [
        MasteryTimelinePoint(
            date=row[0].recorded_at.strftime("%b %d, %H:%M"),
            concept_name=row[1],
            score=round(row[0].score_snapshot, 1)
        )
        for row in hist_rows
    ]

    # 5. Cognitive Mistake Distribution
    mistake_stmt = (
        select(QuizMistake.mistake_type, func.count(QuizMistake.id))
        .where(
            QuizMistake.project_id == project.id,
            QuizMistake.user_id == current_user.id
        )
        .group_by(QuizMistake.mistake_type)
    )
    mistake_rows = (await db.execute(mistake_stmt)).all()
    mistake_distribution = [
        MistakeDistributionItem(
            mistake_type=(m[0].value if hasattr(m[0], 'value') else str(m[0])).replace("_", " ").title(),
            count=m[1]
        )
        for m in mistake_rows
    ]

    # 6. Activity Events & Streak
    evt_stmt = (
        select(ActivityEvent)
        .where(
            ActivityEvent.project_id == project.id,
            ActivityEvent.user_id == current_user.id
        )
        .order_by(ActivityEvent.created_at.desc())
        .limit(100)
    )
    events = (await db.execute(evt_stmt)).scalars().all()
    streak_days = calculate_streak([e.created_at for e in events])

    # 14-day rolling activity
    now = datetime.now(timezone.utc)
    day_counts = defaultdict(int)
    for i in range(14):
        d_str = (now - timedelta(days=13 - i)).strftime("%b %d")
        day_counts[d_str] = 0

    for e in events:
        d_str = e.created_at.strftime("%b %d")
        if d_str in day_counts:
            day_counts[d_str] += 1

    daily_activity = [
        DailyActivityPoint(date=d, count=cnt)
        for d, cnt in day_counts.items()
    ]

    recent_events = [
        ActivityEventItem(
            id=e.id,
            event_type=e.event_type,
            project_id=e.project_id,
            project_name=project.name,
            created_at=e.created_at,
            payload=e.payload or {}
        )
        for e in events[:15]
    ]

    return ProjectAnalyticsOut(
        overview=ProjectAnalyticsOverview(
            overall_mastery=round(overall_mastery, 1),
            mastery_status=mastery_status,
            total_quizzes_completed=total_quizzes,
            average_quiz_score=round(avg_quiz_score, 1),
            total_questions_answered=total_answers,
            accuracy_rate=accuracy_rate,
            streak_days=streak_days,
            total_materials=mat_count,
            total_chunks=chunk_count,
            total_concepts=total_concepts,
            ai_queries_count=ai_queries
        ),
        concept_metrics=concept_metrics,
        quiz_history=quiz_history,
        mastery_timeline=mastery_timeline,
        mistake_distribution=mistake_distribution,
        daily_activity=daily_activity,
        recent_events=recent_events
    )

@router.get("/analytics/global", response_model=GlobalAnalyticsOut)
async def get_global_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    PRD REQUIREMENT: Global Analytics.
    Aggregates learning velocity, cross-space mastery leaderboard, and activity across all workspaces.
    """
    # Overview metrics
    total_spaces = (await db.execute(
        select(func.count(Space.id)).where(Space.user_id == current_user.id)
    )).scalar() or 0

    total_projects = (await db.execute(
        select(func.count(Project.id)).where(Project.user_id == current_user.id)
    )).scalar() or 0

    total_materials = (await db.execute(
        select(func.count(Material.id)).where(Material.user_id == current_user.id)
    )).scalar() or 0

    total_quizzes = (await db.execute(
        select(func.count(Quiz.id)).where(
            Quiz.user_id == current_user.id,
            Quiz.status == QuizStatus.COMPLETED
        )
    )).scalar() or 0

    avg_mastery = (await db.execute(
        select(func.avg(ConceptMastery.mastery_score)).where(ConceptMastery.user_id == current_user.id)
    )).scalar() or 0.0

    ans_total = (await db.execute(
        select(func.count(QuestionAnswer.id)).where(QuestionAnswer.user_id == current_user.id)
    )).scalar() or 0

    ans_correct = (await db.execute(
        select(func.count(QuestionAnswer.id)).where(
            QuestionAnswer.user_id == current_user.id,
            QuestionAnswer.is_correct == True
        )
    )).scalar() or 0
    accuracy_rate = round((ans_correct / ans_total * 100.0), 1) if ans_total > 0 else 0.0

    ai_interactions = (await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.user_id == current_user.id)
    )).scalar() or 0

    # User's all events for global streak and daily activity
    evt_stmt = (
        select(ActivityEvent)
        .where(ActivityEvent.user_id == current_user.id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(200)
    )
    events = (await db.execute(evt_stmt)).scalars().all()
    streak_days = calculate_streak([e.created_at for e in events])

    # Projects Leaderboard
    proj_stmt = (
        select(Project, Space.name)
        .join(Space, Project.space_id == Space.id)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects_with_space = (await db.execute(proj_stmt)).all()

    leaderboard: list[ProjectLeaderboardItem] = []
    for proj, s_name in projects_with_space:
        p_mastery = (await db.execute(
            select(func.avg(ConceptMastery.mastery_score)).where(
                ConceptMastery.project_id == proj.id,
                ConceptMastery.user_id == current_user.id
            )
        )).scalar() or 0.0

        p_quizzes = (await db.execute(
            select(func.count(Quiz.id)).where(
                Quiz.project_id == proj.id,
                Quiz.user_id == current_user.id,
                Quiz.status == QuizStatus.COMPLETED
            )
        )).scalar() or 0

        p_mats = (await db.execute(
            select(func.count(Material.id)).where(Material.project_id == proj.id)
        )).scalar() or 0

        leaderboard.append(ProjectLeaderboardItem(
            project_id=proj.id,
            project_name=proj.name,
            space_name=s_name,
            average_mastery=round(float(p_mastery), 1),
            quizzes_count=p_quizzes,
            materials_count=p_mats
        ))

    leaderboard.sort(key=lambda x: x.average_mastery, reverse=True)

    # 14-day rolling activity
    now = datetime.now(timezone.utc)
    day_counts = defaultdict(int)
    for i in range(14):
        d_str = (now - timedelta(days=13 - i)).strftime("%b %d")
        day_counts[d_str] = 0

    for e in events:
        d_str = e.created_at.strftime("%b %d")
        if d_str in day_counts:
            day_counts[d_str] += 1

    daily_activity = [
        DailyActivityPoint(date=d, count=cnt)
        for d, cnt in day_counts.items()
    ]

    recent_events = [
        ActivityEventItem(
            id=e.id,
            event_type=e.event_type,
            project_id=e.project_id,
            created_at=e.created_at,
            payload=e.payload or {}
        )
        for e in events[:15]
    ]

    return GlobalAnalyticsOut(
        overview=GlobalAnalyticsOverview(
            total_spaces=total_spaces,
            total_projects=total_projects,
            total_materials=total_materials,
            total_quizzes_completed=total_quizzes,
            platform_average_mastery=round(float(avg_mastery), 1),
            overall_accuracy_rate=accuracy_rate,
            streak_days=streak_days,
            total_ai_interactions=ai_interactions
        ),
        projects_leaderboard=leaderboard,
        daily_activity=daily_activity,
        recent_events=recent_events
    )
