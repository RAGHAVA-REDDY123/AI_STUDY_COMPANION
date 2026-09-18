import pytest
from evaluations.services.tutor_evaluator import tutor_evaluator
from evaluations.services.retrieval_evaluator import retrieval_evaluator
from evaluations.services.assessment_evaluator import assessment_evaluator
from evaluations.services.recommendation_evaluator import recommendation_evaluator

def test_tutor_evaluation_supported_case():
    """Verify tutor evaluation assigns high score when expected keywords and valid citations are present."""
    case = {
        "case_id": "test_01",
        "question": "Explain gradient descent.",
        "expected_answer_keywords": ["gradient", "loss", "iterative"],
        "expected_sources": ["ML_Foundations.pdf"],
        "expected_page": 2,
        "is_supported": True
    }
    good_response = (
        "Gradient descent iteratively updates parameters to minimize the loss function "
        "[Source: ML_Foundations.pdf — Page 2]."
    )
    result = tutor_evaluator.evaluate_case(case, good_response)
    assert result["passed"] is True
    assert result["score"] >= 0.70
    assert result["metrics"]["citation_score"] == 1.0

def test_tutor_evaluation_unsupported_refusal():
    """Verify tutor evaluation tests for zero-hallucination calibrated refusal."""
    case = {
        "case_id": "test_refusal",
        "question": "How do I make pasta carbonara?",
        "expected_sources": [],
        "is_supported": False,
        "forbidden_keywords": ["spaghetti", "bacon", "cheese"]
    }
    proper_refusal = (
        "I cannot find sufficient evidence in your uploaded project notes to answer 'How do I make pasta carbonara?'. "
        "The available project materials do not cover this topic."
    )
    res_pass = tutor_evaluator.evaluate_case(case, proper_refusal)
    assert res_pass["passed"] is True
    assert res_pass["score"] == 1.0

    hallucinated_answer = "Boil spaghetti for 10 minutes and fry bacon with cheese."
    res_fail = tutor_evaluator.evaluate_case(case, hallucinated_answer)
    assert res_fail["passed"] is False
    assert res_fail["score"] == 0.0

def test_retrieval_evaluation_metrics():
    """Verify RetrievalEvaluator accurately computes Recall@K, Precision@K, and MRR."""
    case = {
        "case_id": "ret_test",
        "query": "What is PCA?",
        "target_document": "PCA_Notes.pdf",
        "target_keywords": ["orthogonal", "variance"],
        "should_have_evidence": True
    }
    # Rank 0 is irrelevant, Rank 1 is relevant (document match), Rank 2 is irrelevant
    retrieved = [
        {"document_title": "Other.pdf", "content": "Intro to AI"},
        {"document_title": "PCA_Notes.pdf", "content": "Computes orthogonal projection."},
        {"document_title": "Unrelated.pdf", "content": "Database indexing."}
    ]
    eval_res = retrieval_evaluator.evaluate_case(case, retrieved, has_sufficient_evidence=True)
    assert eval_res["passed"] is True
    # Rank of first relevant is index 1 (1-based rank = 2) -> MRR = 1/2 = 0.5
    assert eval_res["metrics"]["mrr"] == 0.5
    assert eval_res["metrics"]["recall_at_k"] == 1.0
    # 1 relevant out of 3 = 0.3333
    assert 0.33 <= eval_res["metrics"]["precision_at_k"] <= 0.34

def test_assessment_adaptive_transitions():
    """Verify AssessmentEvaluator validates difficulty transitions."""
    case_escalate = {
        "case_id": "adapt_01",
        "evaluation_type": "adaptive_transition",
        "current_difficulty": "EASY",
        "recent_answers": [True, True, True],
        "mastery_score": 80.0,
        "expected_next_difficulty": "MEDIUM"
    }
    assert assessment_evaluator.evaluate_case(case_escalate)["passed"] is True

    case_deescalate = {
        "case_id": "adapt_02",
        "evaluation_type": "adaptive_transition",
        "current_difficulty": "HARD",
        "recent_answers": [False, False],
        "mastery_score": 30.0,
        "expected_next_difficulty": "EASY"
    }
    assert assessment_evaluator.evaluate_case(case_deescalate)["passed"] is True

def test_recommendation_evaluation_rejection_of_generic():
    """Verify RecommendationEvaluator rejects generic fallbacks when specific weak concepts exist."""
    case = {
        "case_id": "rec_test",
        "expected_action": "REVIEW_MATERIAL",
        "must_mention": ["Backpropagation"],
        "is_generic_forbidden": True
    }
    # Targeted recommendation
    good_title = "Review Foundational Notes on Backpropagation"
    good_reason = "Your recent quiz indicates missing chain rule steps in Backpropagation."
    res_good = recommendation_evaluator.evaluate_case(case, good_title, good_reason, "REVIEW_MATERIAL")
    assert res_good["passed"] is True

    # Generic fallback should fail
    generic_title = "Continue Comprehensive Learning Loop"
    generic_reason = "Practice questions regularly to reinforce long-term memory."
    res_bad = recommendation_evaluator.evaluate_case(case, generic_title, generic_reason, "TAKE_QUIZ")
    assert res_bad["passed"] is False
