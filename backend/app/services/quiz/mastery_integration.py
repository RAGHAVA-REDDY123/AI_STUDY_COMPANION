from datetime import datetime, timezone
import math
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState, MasteryHistoryPoint
from app.models.quiz import QuestionDifficulty

class MasteryIntegration:
    """
    Evidence-based Concept Mastery & Growth Integration.
    Updates concept mastery using damped Bayesian/EMA logic based on question difficulty,
    performance score, and attempt confidence. Records longitudinal history snapshots.
    Strictly project-isolated.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_concept_mastery(
        self,
        project_id: UUID,
        user_id: UUID,
        concept: Concept,
        difficulty: QuestionDifficulty,
        score: float,  # 0.0 to 1.0
        quiz_id: UUID,
        question_id: UUID
    ) -> tuple[float, float, ConceptMastery]:
        """
        Updates concept mastery with evidence from a single question.
        Returns: (before_score, after_score, updated_mastery_record)
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch or initialize mastery record
        stmt = select(ConceptMastery).where(
            ConceptMastery.project_id == project_id,
            ConceptMastery.concept_id == concept.id,
            ConceptMastery.user_id == user_id
        )
        mastery = (await self.db.execute(stmt)).scalar_one_or_none()

        if not mastery:
            # Cold start initialization based on first evidence
            initial_score = round(score * 100.0, 1)
            # Regress slightly toward prior 50.0 to avoid 0% or 100% on 1 attempt
            initial_score = round((0.6 * initial_score) + (0.4 * 50.0), 1)

            mastery = ConceptMastery(
                project_id=project_id,
                concept_id=concept.id,
                user_id=user_id,
                mastery_score=initial_score,
                confidence=0.35,
                trend_state=GrowthState.STABLE if score >= 0.70 else GrowthState.REQUIRING_ATTENTION,
                total_attempts=1,
                successful_attempts=1 if score >= 0.70 else 0,
                consecutive_mistakes=0 if score >= 0.70 else 1,
                last_assessed_at=now,
                last_practiced_at=now
            )
            self.db.add(mastery)
            await self.db.flush()

            # Record history point
            self._record_history(
                mastery_id=mastery.id,
                project_id=project_id,
                concept_id=concept.id,
                quiz_id=quiz_id,
                question_id=question_id,
                score=initial_score,
                now=now
            )
            return 50.0, initial_score, mastery

        before_score = mastery.mastery_score

        # 2. Difficulty weight calculation
        if difficulty == QuestionDifficulty.EASY:
            # Passing easy gives modest boost; failing easy hurts more
            diff_weight = 0.65 if score >= 0.70 else 1.25
        elif difficulty == QuestionDifficulty.HARD:
            # Passing hard gives large reward; failing hard is forgiven more
            diff_weight = 1.35 if score >= 0.70 else 0.70
        else:
            diff_weight = 1.00

        # 3. Damped learning rate based on attempt count
        attempts = mastery.total_attempts
        base_alpha = 0.28
        # More attempts -> lower alpha, preventing wild swings
        effective_alpha = max(0.12, min(0.38, base_alpha * (1.6 / math.sqrt(attempts + 1))))

        # 4. Target score delta
        # If learner scores 0.85, target is 85.0%
        target_score = score * 100.0
        delta = (target_score - before_score) * diff_weight * effective_alpha

        # Bound maximum delta per single question to [-18.0, +18.0]
        delta = max(-18.0, min(18.0, delta))
        after_score = round(max(0.0, min(100.0, before_score + delta)), 1)

        # 5. Update mastery fields
        mastery.mastery_score = after_score
        mastery.total_attempts += 1
        if score >= 0.70:
            mastery.successful_attempts += 1
            mastery.consecutive_mistakes = 0
        else:
            mastery.consecutive_mistakes += 1

        mastery.last_assessed_at = now
        mastery.last_practiced_at = now
        # Confidence increases asymptotically toward 0.95 with attempts
        mastery.confidence = min(0.95, round(0.40 + (0.55 * (1.0 - math.exp(-mastery.total_attempts / 5.0))), 2))

        # 6. Trend State determination
        if delta >= 2.0 and mastery.consecutive_mistakes == 0:
            mastery.trend_state = GrowthState.IMPROVING
        elif after_score < 55.0 or mastery.consecutive_mistakes >= 2:
            mastery.trend_state = GrowthState.REQUIRING_ATTENTION
            # PRD §13 Repeated Mistake Workflow Trigger
            if mastery.consecutive_mistakes >= 2:
                try:
                    import asyncio
                    from app.services.remediation_service import remediation_service
                    asyncio.create_task(
                        remediation_service.diagnose_repeated_mistakes_task(
                            project_id_str=str(project_id),
                            user_id_str=str(user_id),
                            concept_id_str=str(concept.id)
                        )
                    )
                except Exception as ex:
                    import logging
                    logging.getLogger(__name__).warning(f"Could not dispatch repeated mistake task: {ex}")
        else:
            mastery.trend_state = GrowthState.STABLE

        # 7. Record History snapshot
        self._record_history(
            mastery_id=mastery.id,
            project_id=project_id,
            concept_id=concept.id,
            quiz_id=quiz_id,
            question_id=question_id,
            score=after_score,
            now=now
        )

        return before_score, after_score, mastery

    def _record_history(
        self,
        mastery_id: UUID,
        project_id: UUID,
        concept_id: UUID,
        quiz_id: UUID,
        question_id: UUID,
        score: float,
        now: datetime
    ):
        hp = MasteryHistoryPoint(
            mastery_id=mastery_id,
            project_id=project_id,
            concept_id=concept_id,
            quiz_id=quiz_id,
            quiz_question_id=question_id,
            score_snapshot=score,
            source="QUIZ",
            trigger_event="QUIZ_ANSWER",
            recorded_at=now
        )
        self.db.add(hp)
