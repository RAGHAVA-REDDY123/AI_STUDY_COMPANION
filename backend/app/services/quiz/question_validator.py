import re
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError

from app.models.quiz import QuestionType, QuestionDifficulty

class RawMCQSchema(BaseModel):
    question_type: str = "MCQ"
    question: str = Field(..., min_length=10)
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=5)

class RawOpenEndedSchema(BaseModel):
    question_type: str = "OPEN_ENDED"
    question: str = Field(..., min_length=10)
    expected_concepts: list[str] = Field(..., min_length=1)
    reference_answer: str = Field(..., min_length=10)
    explanation: str = Field(..., min_length=5)

class QuestionValidator:
    """
    Validation layer for LLM-generated questions.
    Enforces strict Pydantic schemas, MCQ key constraints, duplicate rejection,
    and project boundaries.
    """

    @staticmethod
    def validate_and_format_mcq(
        raw_data: dict[str, Any],
        existing_prompts: list[str]
    ) -> dict[str, Any]:
        """
        Validates MCQ raw payload and converts into standard internal structure.
        """
        parsed = RawMCQSchema(**raw_data)
        question_text = parsed.question.strip()

        # 1. Duplicate check against existing question history
        QuestionValidator._assert_not_duplicate(question_text, existing_prompts)

        # 2. Format options into standard [{key: "A", text: "..."}]
        raw_options = parsed.options
        formatted_options = []
        keys = ["A", "B", "C", "D"]
        for idx, opt in enumerate(raw_options):
            clean_text = opt.strip()
            # If model included "A. " or "A) " in the text, strip it
            clean_text = re.sub(r"^[A-Da-d][.)]\s*", "", clean_text)
            formatted_options.append({"key": keys[idx], "text": clean_text})

        # 3. Resolve correct answer key
        raw_correct = parsed.correct_answer.strip()
        correct_key = None
        # Check if model gave key directly: "A" or "Option A"
        match = re.search(r"\b([A-D])\b", raw_correct, re.IGNORECASE)
        if match:
            correct_key = match.group(1).upper()
        else:
            # Check if model matched option text
            for opt in formatted_options:
                if opt["text"].lower() == raw_correct.lower():
                    correct_key = opt["key"]
                    break

        if not correct_key or correct_key not in keys:
            raise ValueError(f"MCQ correct_answer '{raw_correct}' does not match any option (A, B, C, D).")

        return {
            "question_type": QuestionType.MCQ,
            "prompt": question_text,
            "options": formatted_options,
            "correct_answer": correct_key,
            "explanation": parsed.explanation.strip(),
            "expected_concepts": []
        }

    @staticmethod
    def validate_and_format_open_ended(
        raw_data: dict[str, Any],
        existing_prompts: list[str]
    ) -> dict[str, Any]:
        """
        Validates open-ended question payload.
        """
        parsed = RawOpenEndedSchema(**raw_data)
        question_text = parsed.question.strip()

        QuestionValidator._assert_not_duplicate(question_text, existing_prompts)

        clean_expected = [c.strip() for c in parsed.expected_concepts if c and c.strip()]
        if not clean_expected:
            raise ValueError("Open-ended question must contain at least one expected concept.")

        return {
            "question_type": QuestionType.OPEN_ENDED,
            "prompt": question_text,
            "options": [],
            "correct_answer": parsed.reference_answer.strip(),
            "explanation": parsed.explanation.strip(),
            "expected_concepts": clean_expected
        }

    @staticmethod
    def _assert_not_duplicate(prompt: str, existing_prompts: list[str], threshold: float = 0.85) -> None:
        """
        Rejects exact or high-token-overlap duplicates.
        """
        prompt_tokens = set(prompt.lower().split())
        for existing in existing_prompts:
            if prompt.strip().lower() == existing.strip().lower():
                raise ValueError("Duplicate question detected: identical question was asked previously.")

            existing_tokens = set(existing.lower().split())
            if not prompt_tokens or not existing_tokens:
                continue

            jaccard = len(prompt_tokens & existing_tokens) / len(prompt_tokens | existing_tokens)
            if jaccard > threshold:
                raise ValueError(f"Semantic duplicate detected (Jaccard similarity {jaccard:.2f}).")
