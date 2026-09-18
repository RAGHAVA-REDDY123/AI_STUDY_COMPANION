from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import Project
from app.models.mastery import ConceptMastery, GrowthState
from app.models.recommendation import Recommendation, RecommendationStatus
from app.schemas.mastery import ConceptMasteryOut, ProjectGrowthSummaryOut
from app.schemas.recommendation import RecommendationOut

router = APIRouter(prefix="/projects/{project_id}", tags=["Mastery, Growth & Recommendations"])

@router.get("/mastery", response_model=list[ConceptMasteryOut])
async def list_concept_mastery(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(ConceptMastery).where(
        ConceptMastery.project_id == project.id,
        ConceptMastery.user_id == current_user.id
    ).order_by(ConceptMastery.mastery_score.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # Enrich with concept name
    out = []
    for r in records:
        out.append({
            "id": r.id,
            "concept_id": r.concept_id,
            "concept_name": r.concept.name if r.concept else "Unknown",
            "mastery_score": r.mastery_score,
            "trend_state": r.trend_state,
            "total_attempts": r.total_attempts,
            "consecutive_mistakes": r.consecutive_mistakes,
            "last_assessed_at": r.last_assessed_at
        })
    return out

@router.get("/growth", response_model=ProjectGrowthSummaryOut)
async def get_growth_summary(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    CRITICAL PRD REQUIREMENT: Growth Analysis.
    Categorizes concepts into Improving, Stable, and Requiring Attention.
    """
    stmt = select(ConceptMastery).where(
        ConceptMastery.project_id == project.id,
        ConceptMastery.user_id == current_user.id
    )
    records = (await db.execute(stmt)).scalars().all()
    
    improving, stable, attention = [], [], []
    for r in records:
        item = {
            "id": r.id,
            "concept_id": r.concept_id,
            "concept_name": r.concept.name if r.concept else "Unknown",
            "mastery_score": r.mastery_score,
            "trend_state": r.trend_state,
            "total_attempts": r.total_attempts,
            "consecutive_mistakes": r.consecutive_mistakes,
            "last_assessed_at": r.last_assessed_at
        }
        if r.trend_state == GrowthState.IMPROVING:
            improving.append(item)
        elif r.trend_state == GrowthState.REQUIRING_ATTENTION:
            attention.append(item)
        else:
            stable.append(item)
            
    return {
        "improving": improving,
        "stable": stable,
        "requiring_attention": attention
    }

@router.get("/recommendations", response_model=list[RecommendationOut])
async def list_recommendations(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Answers: 'What should I do next?'
    """
    stmt = select(Recommendation).where(
        Recommendation.project_id == project.id,
        Recommendation.user_id == current_user.id
    ).order_by(Recommendation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
