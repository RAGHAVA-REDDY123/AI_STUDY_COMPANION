from typing import Any
from app.schemas.quiz import MCQOption, QuestionDifficulty
from app.services.quiz.adaptive_engine import AdaptiveEngine

class AssessmentEvaluator:
    """
    Evaluator for Quiz & Assessment subsystems:
    - Structured Output Reliability: Pydantic schema adherence.
    - Open-Ended Grading Soundness: Understanding, accuracy, relevance, reasoning.
    - Adaptive Behavior: Verification of mastery-based difficulty transitions.
    """

    def evaluate_case(self, case: dict[str, Any]) -> dict[str, Any]:
        eval_type = case.get("evaluation_type")

        # 1. MCQ Schema Validation Case
        if eval_type == "mcq_schema_validation":
            payload = case.get("payload", {})
            expected_valid = case.get("expected_valid", True)

            is_valid = True
            err_reason = None

            try:
                options = payload.get("options", [])
                if len(options) < 2 or len(options) > 5:
                    is_valid = False
                    err_reason = "Options count must be between 2 and 5"
                if not payload.get("prompt"):
                    is_valid = False
                    err_reason = "Prompt cannot be empty"
                if payload.get("correct_answer") not in [o.get("key") for o in options]:
                    is_valid = False
                    err_reason = "Correct answer key not in options"
            except Exception as e:
                is_valid = False
                err_reason = str(e)

            passed = (is_valid == expected_valid)
            score = 1.0 if passed else 0.0

            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "is_valid": is_valid,
                    "expected_valid": expected_valid,
                    "validation_error": err_reason
                },
                "failure_reason": None if passed else f"Schema validation outcome mismatch: got {is_valid}, expected {expected_valid}"
            }

        # 2. Open-Ended Rubric Output Schema Validation
        if eval_type == "open_ended_rubric_schema":
            rubric = case.get("rubric_output", {})
            expected_valid = case.get("expected_valid", True)

            required_fields = ["understanding", "accuracy", "relevance", "reasoning", "overall_score"]
            has_fields = all(f in rubric for f in required_fields)
            scores_valid = all(0.0 <= float(rubric.get(f, -1)) <= 1.0 for f in required_fields if f in rubric)

            actual_valid = has_fields and scores_valid
            passed = (actual_valid == expected_valid)
            score = 1.0 if passed else 0.0

            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "has_required_rubric_dimensions": has_fields,
                    "scores_bounded": scores_valid
                },
                "failure_reason": None if passed else "Rubric schema dimension check failed"
            }

        # 3. Adaptive Difficulty Transition
        if eval_type == "adaptive_transition":
            curr_diff = QuestionDifficulty(case["current_difficulty"])
            recent = case.get("recent_answers", [])
            mastery = case.get("mastery_score", 50.0)
            expected_next = case.get("expected_next_difficulty")

            # Test using AdaptiveEngine logic
            next_diff = AdaptiveEngine.calculate_next_difficulty(
                current_difficulty=curr_diff,
                concept_mastery=mastery,
                recent_answers_correct=recent
            )

            passed = (next_diff.value == expected_next)
            score = 1.0 if passed else 0.0

            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "current_difficulty": curr_diff.value,
                    "calculated_next_difficulty": next_diff.value,
                    "expected_next_difficulty": expected_next,
                    "mastery_score": mastery
                },
                "failure_reason": None if passed else f"Expected {expected_next}, but engine selected {next_diff.value}"
            }

        # 4. Open-Ended Grading Quality
        if eval_type == "open_ended_grading":
            student_ans = case.get("student_answer", "").lower()
            ref_expl = case.get("reference_explanation", "").lower()

            words_ref = set(ref_expl.split())
            words_stu = set(student_ans.split())
            overlap = len(words_ref.intersection(words_stu)) / len(words_ref) if words_ref else 0.5

            min_score = case.get("expected_score_min")
            max_score = case.get("expected_score_max")

            passed = True
            if min_score is not None and overlap < min_score:
                passed = False
            if max_score is not None and overlap > max_score:
                passed = False

            score = round(overlap, 4)
            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "overlap_score": score,
                    "min_expected": min_score,
                    "max_expected": max_score
                },
                "failure_reason": None if passed else f"Grading score {score} outside expected bounds [{min_score}, {max_score}]"
            }

        return {
            "case_id": case.get("case_id", "unknown"),
            "score": 0.0,
            "passed": False,
            "metrics": {},
            "failure_reason": f"Unknown evaluation_type '{eval_type}'"
        }

assessment_evaluator = AssessmentEvaluator()
