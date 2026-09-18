from typing import Any

class RecommendationEvaluator:
    """
    Evaluator for Recommendation Generation:
    - Relevance: Alignment with learner deficits, mistakes, and goals.
    - Actionability: Clear, actionable suggestions (e.g. review material, take quiz).
    - Specificity: Avoids generic placeholders when specific weak concepts exist.
    """

    def evaluate_case(
        self,
        case: dict[str, Any],
        actual_recommendation_title: str,
        actual_recommendation_reasoning: str,
        actual_action: str
    ) -> dict[str, Any]:
        expected_action = case.get("expected_action")
        must_mention = case.get("must_mention", [])
        is_generic_forbidden = case.get("is_generic_forbidden", True)

        combined_text = (actual_recommendation_title + " " + actual_recommendation_reasoning).lower()

        # 1. Action Alignment
        action_match = (actual_action == expected_action)

        # 2. Targeted Concept Mention
        mentioned_count = sum(1 for kw in must_mention if kw.lower() in combined_text)
        concept_match = (mentioned_count == len(must_mention)) if must_mention else True

        # 3. Specificity vs Generic Placeholders
        is_generic = "continue comprehensive learning loop" in combined_text.lower()
        non_generic_ok = not (is_generic and is_generic_forbidden)

        passed = action_match and concept_match and non_generic_ok

        score = 0.0
        if action_match:
            score += 0.4
        if concept_match:
            score += 0.4
        if non_generic_ok:
            score += 0.2
        score = round(score, 4)

        failure_reasons = []
        if not action_match:
            failure_reasons.append(f"Action mismatch: expected {expected_action}, got {actual_action}")
        if not concept_match:
            failure_reasons.append(f"Missing expected target concept mentions: {must_mention}")
        if not non_generic_ok:
            failure_reasons.append("Generic fallback generated when specific weak concepts were present.")

        return {
            "case_id": case["case_id"],
            "score": score,
            "passed": passed,
            "metrics": {
                "action_match": action_match,
                "concept_match": concept_match,
                "non_generic_ok": non_generic_ok,
                "mentioned_count": mentioned_count,
                "total_required_mentions": len(must_mention)
            },
            "failure_reason": "; ".join(failure_reasons) if failure_reasons else None
        }

recommendation_evaluator = RecommendationEvaluator()
