from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState
from app.models.quiz import QuestionDifficulty, QuizMistake, Question, QuestionAnswer

class AdaptiveEngine:
    """
    Pedagogical Adaptive Engine.
    Evaluates multi-factor learner evidence to identify target concepts and difficulty
    where additional practice provides the highest learning value.
    Enforces strict project-level data boundary.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def select_target_concept_and_difficulty(
        self,
        project_id: UUID,
        user_id: UUID,
        quiz_id: UUID,
        recent_question_concept_ids: list[UUID],
        allowed_difficulties: Optional[list[QuestionDifficulty]] = None
    ) -> tuple[Optional[Concept], QuestionDifficulty, float]:
        """
        Selects target concept and evidence-based difficulty based on:
        1. Concept mastery score & confidence
        2. Recent mistake signals
        3. Recency of practice
        4. Assessment uncertainty (low attempt count)
        5. Concept importance
        6. Question history within current quiz session
        """
        # 1. Fetch all concepts in this project (strictly project-isolated)
        stmt_concepts = select(Concept).where(Concept.project_id == project_id)
        concepts = (await self.db.execute(stmt_concepts)).scalars().all()
        if not concepts:
            return None, QuestionDifficulty.MEDIUM, 0.0

        # 2. Fetch existing masteries for this user in this project
        stmt_masteries = select(ConceptMastery).where(
            ConceptMastery.project_id == project_id,
            ConceptMastery.user_id == user_id
        )
        masteries = {m.concept_id: m for m in (await self.db.execute(stmt_masteries)).scalars().all()}

        # 3. Fetch mistake counts per concept for this project & user
        stmt_mistakes = (
            select(QuizMistake.concept_id, func.count(QuizMistake.id))
            .where(
                QuizMistake.project_id == project_id,
                QuizMistake.user_id == user_id
            )
            .group_by(QuizMistake.concept_id)
        )
        mistake_counts = dict((await self.db.execute(stmt_mistakes)).all())

        # 4. Fetch recent quiz answers in current project for performance context
        stmt_recent_answers = (
            select(QuestionAnswer)
            .where(
                QuestionAnswer.project_id == project_id,
                QuestionAnswer.user_id == user_id
            )
            .order_by(desc(QuestionAnswer.answered_at))
            .limit(10)
        )
        recent_answers = (await self.db.execute(stmt_recent_answers)).scalars().all()
        recent_accuracy = (
            sum(1.0 for a in recent_answers if a.is_correct) / len(recent_answers)
            if recent_answers else 0.5
        )

        now = datetime.now(timezone.utc)
        scored_candidates: list[tuple[Concept, float]] = []

        for concept in concepts:
            m = masteries.get(concept.id)
            current_mastery = m.mastery_score if m else 50.0  # Cold-start prior
            attempts = m.total_attempts if m else 0
            consecutive_mistakes = m.consecutive_mistakes if m else 0
            last_assessed = m.last_assessed_at if m else None

            # Signal 1: Mastery gap (higher gap = higher need)
            # Normalize 0.0 - 1.0 (where 0% mastery -> gap 1.0, 100% mastery -> gap 0.0)
            mastery_gap = max(0.0, min(1.0, (100.0 - current_mastery) / 100.0))

            # Signal 2: Recent error & mistake signal
            concept_mistakes = mistake_counts.get(concept.id, 0)
            error_signal = min(1.0, (concept_mistakes * 0.25) + (consecutive_mistakes * 0.35))

            # Signal 3: Recency signal (concepts not assessed recently gain priority)
            if last_assessed:
                days_since = (now - last_assessed).total_seconds() / 86400.0
                recency_signal = min(1.0, days_since / 7.0)
            else:
                recency_signal = 0.8  # Unassessed concepts get high recency weight

            # Signal 4: Assessment uncertainty (few attempts = high uncertainty)
            uncertainty_signal = max(0.0, 1.0 - (attempts / 4.0))

            # Signal 5: Concept importance (from ingestion)
            importance_signal = max(0.1, min(1.0, concept.importance_score))

            # Signal 6: Penalty if already asked in current quiz session (ensures breadth)
            session_repetition_penalty = 0.0
            if concept.id in recent_question_concept_ids:
                freq = recent_question_concept_ids.count(concept.id)
                session_repetition_penalty = freq * 0.45

            # Multi-factor priority formula
            practice_priority = (
                (0.35 * mastery_gap)
                + (0.25 * error_signal)
                + (0.15 * recency_signal)
                + (0.15 * uncertainty_signal)
                + (0.10 * importance_signal)
                - session_repetition_penalty
            )
            practice_priority = max(0.01, practice_priority)
            scored_candidates.append((concept, practice_priority))

        # Sort concepts by highest practice priority
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        selected_concept, highest_priority = scored_candidates[0]

        # 5. Evidence-based Difficulty Selection
        target_mastery = masteries.get(selected_concept.id)
        concept_score = target_mastery.mastery_score if target_mastery else 50.0
        concept_mistakes = mistake_counts.get(selected_concept.id, 0)
        consecutive_errors = target_mastery.consecutive_mistakes if target_mastery else 0

        # Non-trivial evidence evaluation:
        # Case A: Low mastery or high consecutive mistakes -> Easy or foundational Medium
        if concept_score < 45.0 or consecutive_errors >= 2 or concept_mistakes >= 3:
            chosen_difficulty = QuestionDifficulty.EASY
        # Case B: High mastery (> 75%) and solid recent accuracy -> Hard for deeper synthesis
        elif concept_score >= 75.0 and recent_accuracy >= 0.70 and consecutive_errors == 0:
            chosen_difficulty = QuestionDifficulty.HARD
        # Case C: Mid-range or high mastery with recent conceptual mistakes -> Medium
        else:
            chosen_difficulty = QuestionDifficulty.MEDIUM

        if allowed_difficulties and chosen_difficulty not in allowed_difficulties:
            chosen_difficulty = allowed_difficulties[0]

        return selected_concept, chosen_difficulty, highest_priority

    @staticmethod
    def calculate_next_difficulty(
        current_difficulty: QuestionDifficulty,
        concept_mastery: float,
        recent_answers_correct: list[bool]
    ) -> QuestionDifficulty:
        """
        Difficulty transition calculator for unit testing, benchmarks, and adaptive evaluations.
        """
        recent_acc = (
            sum(1.0 for c in recent_answers_correct if c) / len(recent_answers_correct)
            if recent_answers_correct else 0.5
        )
        consecutive_wrong = 0
        for ans in reversed(recent_answers_correct):
            if not ans:
                consecutive_wrong += 1
            else:
                break

        if concept_mastery < 45.0 or consecutive_wrong >= 2:
            return QuestionDifficulty.EASY
        elif concept_mastery >= 75.0 and recent_acc >= 0.70 and consecutive_wrong == 0:
            if current_difficulty == QuestionDifficulty.EASY:
                return QuestionDifficulty.MEDIUM
            return QuestionDifficulty.HARD
        else:
            return QuestionDifficulty.MEDIUM
