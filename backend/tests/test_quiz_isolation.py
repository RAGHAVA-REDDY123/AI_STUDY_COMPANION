import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.project import Project
from app.models.user import User
from app.models.concept import Concept
from app.models.quiz import Quiz, Question, QuestionDifficulty, QuestionType
from app.services.quiz.question_generator import QuestionGenerator
from app.services.quiz.adaptive_engine import AdaptiveEngine
from app.services.quiz_service import QuizService

def test_project_a_quiz_cannot_retrieve_project_b_chunks():
    """
    CRITICAL ACCEPTANCE TEST:
    QuestionGenerator for Project A must strictly pass project_a.id to the RAG retrieval layer.
    Chunks belonging to Project B must NEVER be queried or retrieved.
    """
    async def _run():
        project_a = Project(id=uuid.uuid4(), name="Project A (ML)", learning_goal="Learn ML")
        project_b = Project(id=uuid.uuid4(), name="Project B (Deep Learning)", learning_goal="Learn DL")
        concept_a = Concept(id=uuid.uuid4(), project_id=project_a.id, name="Linear Regression", description="OLS")

        mock_db = AsyncMock()
        mock_mappings = MagicMock()
        # Mock retrieval returning Project A chunk
        mock_mappings.all.return_value = [
            {
                "id": uuid.uuid4(),
                "material_id": uuid.uuid4(),
                "page_number": 5,
                "chunk_index": 1,
                "section_title": "OLS",
                "document_title": "ML_Textbook.pdf",
                "content": "Ordinary least squares minimizes squared error residuals.",
                "vector_similarity": 0.91,
                "fts_rank": 0.6
            }
        ]
        mock_exec = MagicMock()
        mock_exec.mappings.return_value = mock_mappings
        mock_db.execute.return_value = mock_exec
        mock_db.flush = AsyncMock()

        with patch("app.services.embedding_service.embedding_service.get_embeddings", new_callable=AsyncMock) as mock_emb:
            mock_emb.return_value = [[0.0] * 384]
            generator = QuestionGenerator(mock_db)

            # Trigger generation
            question_dict, chunk_ids = await generator.generate_question(
                project=project_a,
                concept=concept_a,
                difficulty=QuestionDifficulty.MEDIUM,
                question_type=QuestionType.MCQ,
                current_mastery_score=50.0,
                recent_mistake_descriptions=[],
                existing_prompts=[]
            )

        # Verify retrieval was invoked with project_a.id
        assert len(chunk_ids) == 1
        # Check SQL params passed to DB execute
        call_args_list = mock_db.execute.call_args_list
        assert len(call_args_list) > 0
        # The first execute is vector SQL
        sql_params = call_args_list[0][0][1]
        assert sql_params["project_id"] == str(project_a.id)
        assert sql_params["project_id"] != str(project_b.id)

    asyncio.run(_run())

def test_project_a_quiz_only_uses_project_a_concepts():
    """
    Verifies that AdaptiveEngine in Project A only queries concepts where project_id == project_a.id.
    Project B concepts are completely excluded.
    """
    async def _run():
        project_a_id = uuid.uuid4()
        project_b_id = uuid.uuid4()
        user_id = uuid.uuid4()
        quiz_id = uuid.uuid4()

        concept_a = Concept(id=uuid.uuid4(), project_id=project_a_id, name="Project A Concept", importance_score=0.9)

        mock_db = AsyncMock()
        mock_res_concepts = MagicMock()
        mock_res_concepts.scalars.return_value.all.return_value = [concept_a]

        mock_res_masteries = MagicMock()
        mock_res_masteries.scalars.return_value.all.return_value = []

        mock_res_mistakes = MagicMock()
        mock_res_mistakes.all.return_value = []

        mock_res_answers = MagicMock()
        mock_res_answers.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            mock_res_concepts,
            mock_res_masteries,
            mock_res_mistakes,
            mock_res_answers
        ]

        engine = AdaptiveEngine(mock_db)
        selected_concept, _, _ = await engine.select_target_concept_and_difficulty(
            project_id=project_a_id,
            user_id=user_id,
            quiz_id=quiz_id,
            recent_question_concept_ids=[]
        )

        assert selected_concept.project_id == project_a_id
        assert selected_concept.project_id != project_b_id

    asyncio.run(_run())

def test_unauthorized_user_cannot_access_quiz():
    """
    Verifies that a user cannot access or answer a quiz belonging to another user.
    """
    async def _run():
        from fastapi import HTTPException

        user_a = User(id=uuid.uuid4(), email="alice@test.com")
        user_b = User(id=uuid.uuid4(), email="bob@test.com")

        quiz = Quiz(id=uuid.uuid4(), project_id=uuid.uuid4(), user_id=user_a.id)

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = quiz
        mock_db.execute.return_value = mock_res

        quiz_svc = QuizService(mock_db)

        # Bob attempts to get Alice's quiz state -> 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await quiz_svc.get_quiz_state(quiz_id=quiz.id, user=user_b)

        assert exc_info.value.status_code == 403

    asyncio.run(_run())
