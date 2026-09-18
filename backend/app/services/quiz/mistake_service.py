from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import QuizMistake, MistakeType

class MistakeService:
    """
    Mistake Recording Service.
    Persists structured diagnostic evidence of learner errors to inform adaptive selection
    and growth analysis. Strictly project-isolated.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_mistake(
        self,
        project_id: UUID,
        user_id: UUID,
        quiz_id: UUID,
        question_id: UUID,
        concept_id: Optional[UUID],
        mistake_type_str: str,
        description: str,
        user_answer: str
    ) -> QuizMistake:
        # Convert mistake type string to Enum safely
        try:
            m_type = MistakeType(mistake_type_str)
        except ValueError:
            m_type = MistakeType.CONCEPTUAL_MISUNDERSTANDING

        mistake = QuizMistake(
            project_id=project_id,
            user_id=user_id,
            quiz_id=quiz_id,
            question_id=question_id,
            concept_id=concept_id,
            mistake_type=m_type,
            mistake_description=description,
            user_answer=user_answer,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(mistake)
        await self.db.flush()
        return mistake
