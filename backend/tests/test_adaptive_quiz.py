import asyncio
import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState
from app.models.quiz import Question, QuestionType, QuestionDifficulty, MistakeType
from app.services.quiz.adaptive_engine import AdaptiveEngine
from app.services.quiz.question_validator import QuestionValidator
from app.services.quiz.answer_evaluator import AnswerEvaluator
from app.services.quiz.mastery_integration import MasteryIntegration

def test_adaptive_concept_prioritization():
    """
    Verifies that AdaptiveEngine assigns highest practice priority to concepts
    with larger mastery gaps and recent error signals over high-mastery concepts.
    """
    async def _run():
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        quiz_id = uuid.uuid4()

        c1 = Concept(id=uuid.uuid4(), project_id=project_id, name="Linear Regression", description="Basic regression", importance_score=0.9)
        c2 = Concept(id=uuid.uuid4(), project_id=project_id, name="Regularization", description="L1/L2 penalties", importance_score=0.95)

        m1 = ConceptMastery(project_id=project_id, concept_id=c1.id, user_id=user_id, mastery_score=85.0, total_attempts=5, consecutive_mistakes=0)
        m2 = ConceptMastery(project_id=project_id, concept_id=c2.id, user_id=user_id, mastery_score=40.0, total_attempts=3, consecutive_mistakes=2)

        mock_db = AsyncMock()

        mock_res_concepts = MagicMock()
        mock_res_concepts.scalars.return_value.all.return_value = [c1, c2]

        mock_res_masteries = MagicMock()
        mock_res_masteries.scalars.return_value.all.return_value = [m1, m2]

        mock_res_mistakes = MagicMock()
        mock_res_mistakes.all.return_value = [(c2.id, 3)]  # 3 mistakes on Regularization

        mock_res_answers = MagicMock()
        mock_res_answers.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            mock_res_concepts,
            mock_res_masteries,
            mock_res_mistakes,
            mock_res_answers
        ]

        engine = AdaptiveEngine(mock_db)
        selected_concept, difficulty, priority = await engine.select_target_concept_and_difficulty(
            project_id=project_id,
            user_id=user_id,
            quiz_id=quiz_id,
            recent_question_concept_ids=[]
        )

        # Regularization (c2) must be selected because of high mastery gap (40%) and 3 mistakes
        assert selected_concept.id == c2.id
        assert selected_concept.name == "Regularization"
        # Difficulty should be EASY or foundational because mastery < 45% and consecutive mistakes >= 2
        assert difficulty == QuestionDifficulty.EASY

    asyncio.run(_run())

def test_question_validator_mcq_formatting():
    """Verifies MCQ schema validation, option formatting, and correct answer key resolution."""
    raw = {
        "question_type": "MCQ",
        "question": "What is the primary effect of L1 regularization on model weights?",
        "options": [
            "A. It encourages sparsity by zeroing small weights",
            "B. It guarantees monotonic loss convergence",
            "C. It doubles the gradient update step",
            "D. It replaces analytical derivatives with permutations"
        ],
        "correct_answer": "Option A",
        "explanation": "L1 penalty (Lasso) drives uninformative weights to exactly zero."
    }

    validated = QuestionValidator.validate_and_format_mcq(raw, existing_prompts=[])
    assert validated["question_type"] == QuestionType.MCQ
    assert validated["correct_answer"] == "A"
    assert len(validated["options"]) == 4
    assert validated["options"][0]["key"] == "A"
    assert "sparsity" in validated["options"][0]["text"]

def test_question_validator_rejects_duplicates():
    """Verifies that duplicate questions are rejected."""
    existing = ["What is the primary effect of L1 regularization on model weights?"]
    raw = {
        "question_type": "MCQ",
        "question": "What is the primary effect of L1 regularization on model weights?",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "A",
        "explanation": "Explanation"
    }

    with pytest.raises(ValueError, match="Duplicate question detected"):
        QuestionValidator.validate_and_format_mcq(raw, existing_prompts=existing)

def test_deterministic_mcq_evaluation():
    """Verifies deterministic MCQ grading without calling LLM."""
    q = Question(
        id=uuid.uuid4(),
        quiz_id=uuid.uuid4(),
        question_type=QuestionType.MCQ,
        difficulty=QuestionDifficulty.MEDIUM,
        prompt="Sample MCQ Question",
        options=[{"key": "A", "text": "Correct"}, {"key": "B", "text": "Wrong"}],
        correct_answer="A",
        explanation="Option A is supported by source notes."
    )

    # Correct submission
    res_correct = AnswerEvaluator._evaluate_mcq(q, "A")
    assert res_correct["is_correct"] is True
    assert res_correct["score"] == 1.0
    assert res_correct["mistake_info"] is None
    assert "✓ Correct" in res_correct["feedback"]

    # Incorrect submission
    res_wrong = AnswerEvaluator._evaluate_mcq(q, "B")
    assert res_wrong["is_correct"] is False
    assert res_wrong["score"] == 0.0
    assert res_wrong["mistake_info"] is not None
    assert res_wrong["mistake_info"]["mistake_type"] == "CONCEPTUAL_MISUNDERSTANDING"
    assert "✗ Incorrect" in res_wrong["feedback"]

def test_mastery_integration_damped_updates():
    """Verifies that mastery update damping prevents wild single-question leaps and logs history."""
    async def _run():
        mock_db = AsyncMock()
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        question_id = uuid.uuid4()

        concept = Concept(id=uuid.uuid4(), project_id=project_id, name="Gradient Descent")

        existing_mastery = ConceptMastery(
            project_id=project_id,
            concept_id=concept.id,
            user_id=user_id,
            mastery_score=60.0,
            confidence=0.5,
            total_attempts=4,
            successful_attempts=3,
            consecutive_mistakes=0
        )

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = existing_mastery
        mock_db.execute.return_value = mock_res

        integration = MasteryIntegration(mock_db)

        # Learner gets 100% on a HARD question
        before, after, updated = await integration.update_concept_mastery(
            project_id=project_id,
            user_id=user_id,
            concept=concept,
            difficulty=QuestionDifficulty.HARD,
            score=1.0,
            quiz_id=quiz_id,
            question_id=question_id
        )

        assert before == 60.0
        # Score must increase, but be damped (e.g. <= +18 points bound)
        assert after > 60.0
        assert after <= 78.0
        assert updated.total_attempts == 5
        assert updated.successful_attempts == 4
        assert updated.consecutive_mistakes == 0

        # Ensure a MasteryHistoryPoint was added
        assert mock_db.add.called

    asyncio.run(_run())
