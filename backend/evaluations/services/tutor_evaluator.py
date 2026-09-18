import re
from typing import Any
from app.services.citation_service import citation_service

class TutorEvaluator:
    """
    Evaluator for Tutor responses:
    - Accuracy: Key concepts and factual correctness.
    - Groundedness: Whether the response is supported by project evidence.
    - Citation Correctness: Verified sources and page numbers vs hallucinated citations.
    - Unsupported Handling: Calibrated refusal on out-of-scope or adversarial queries.
    """

    REFUSAL_PATTERNS = [
        "cannot find sufficient evidence",
        "couldn't find enough information",
        "uploaded project notes",
        "available project materials do not cover",
        "do not contain sufficient evidence"
    ]

    def evaluate_case(self, case: dict[str, Any], actual_response: str) -> dict[str, Any]:
        resp_lower = actual_response.lower()
        is_supported = case.get("is_supported", True)

        # 1. Unsupported Question Refusal Check
        if not is_supported:
            refused = any(p in resp_lower for p in self.REFUSAL_PATTERNS)
            forbidden_leaked = any(fk.lower() in resp_lower for fk in case.get("forbidden_keywords", []))

            score = 1.0 if (refused and not forbidden_leaked) else 0.0
            passed = score >= 0.8

            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "refusal_detected": refused,
                    "forbidden_leaked": forbidden_leaked,
                    "unsupported_handling_score": score
                },
                "failure_reason": None if passed else "Failed calibrated refusal: response hallucinated an answer or leaked forbidden tokens."
            }

        # 2. Supported Question: Accuracy Keyword Check
        expected_keywords = case.get("expected_answer_keywords", [])
        matched_kw = [kw for kw in expected_keywords if kw.lower() in resp_lower]
        accuracy_score = (len(matched_kw) / len(expected_keywords)) if expected_keywords else 1.0

        # 3. Citation Correctness Check
        mock_retrieved = [
            {"document_title": src, "page_number": case.get("expected_page", 1), "snippet": "..."}
            for src in case.get("expected_sources", [])
        ]
        citation_eval = citation_service.validate_citations_detailed(actual_response, mock_retrieved)
        citation_score = citation_eval.get("citation_correctness_score", 1.0)

        # 4. Groundedness Score (combination of accuracy and citation grounding)
        groundedness_score = round(0.6 * accuracy_score + 0.4 * citation_score, 4)
        overall_score = round((accuracy_score + citation_score + groundedness_score) / 3.0, 4)
        passed = overall_score >= 0.70

        return {
            "case_id": case["case_id"],
            "score": overall_score,
            "passed": passed,
            "metrics": {
                "accuracy_score": round(accuracy_score, 4),
                "groundedness_score": groundedness_score,
                "citation_score": citation_score,
                "matched_keywords": matched_kw,
                "total_expected_keywords": len(expected_keywords),
                "citation_report": citation_eval
            },
            "failure_reason": None if passed else f"Insufficient groundedness or accuracy: score {overall_score} < 0.70"
        }

tutor_evaluator = TutorEvaluator()
