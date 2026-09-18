import json
from typing import Any, Optional
from uuid import UUID

from app.models.project import Project
from app.models.concept import Concept
from app.models.quiz import Question, QuestionType
from app.services.ai import ai_service

class AnswerEvaluator:
    """
    Evaluator for learner quiz answers.
    - Evaluates MCQs strictly deterministically without LLM overhead.
    - Evaluates Open-Ended responses via Gemini 2.5 Flash against pedagogical multi-factor rubrics.
    """

    @staticmethod
    async def evaluate(
        project: Project,
        question: Question,
        concept: Optional[Concept],
        user_answer: str,
        source_context_snippets: list[str]
    ) -> dict[str, Any]:
        """
        Evaluates learner response.
        Returns:
        {
            "is_correct": bool,
            "score": float,  # 0.0 to 1.0
            "feedback": str,
            "evaluation": dict,
            "mistake_info": Optional[dict]
        }
        """
        if question.question_type == QuestionType.MCQ:
            return AnswerEvaluator._evaluate_mcq(question, user_answer)
        else:
            return await AnswerEvaluator._evaluate_open_ended(
                project=project,
                question=question,
                concept=concept,
                user_answer=user_answer,
                source_context_snippets=source_context_snippets
            )

    @staticmethod
    def _evaluate_mcq(question: Question, user_answer: str) -> dict[str, Any]:
        submitted_clean = user_answer.strip().upper()
        correct_clean = question.correct_answer.strip().upper()

        # Deterministic equality check
        is_correct = (submitted_clean == correct_clean)
        score = 1.0 if is_correct else 0.0

        if is_correct:
            feedback = (
                f"✓ Correct!\n\n"
                f"What you understood:\n"
                f"- Successfully identified the key principle.\n\n"
                f"Explanation:\n{question.explanation}"
            )
            evaluation = {
                "understanding": 1.0,
                "accuracy": 1.0,
                "relevance": 1.0,
                "reasoning": 1.0,
                "key_concepts_covered": ["Correct Option Selected"],
                "missing_concepts": [],
                "overall_score": 1.0,
                "feedback": feedback
            }
            mistake_info = None
        else:
            feedback = (
                f"✗ Incorrect. Selected: Option {submitted_clean} | Correct: Option {correct_clean}\n\n"
                f"What was missing:\n"
                f"- The chosen option does not reflect the core principle.\n\n"
                f"Explanation:\n{question.explanation}\n\n"
                f"How to improve:\nReview the concept foundations and distinguish between contrasting mechanism properties."
            )
            evaluation = {
                "understanding": 0.0,
                "accuracy": 0.0,
                "relevance": 0.7,
                "reasoning": 0.2,
                "key_concepts_covered": [],
                "missing_concepts": ["Correct conceptual differentiator"],
                "overall_score": 0.0,
                "feedback": feedback
            }
            mistake_info = {
                "mistake_type": "CONCEPTUAL_MISUNDERSTANDING",
                "mistake_description": f"Chose option {submitted_clean} instead of {correct_clean}. Review: {question.explanation[:120]}"
            }

        return {
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "evaluation": evaluation,
            "mistake_info": mistake_info
        }

    @staticmethod
    async def _evaluate_open_ended(
        project: Project,
        question: Question,
        concept: Optional[Concept],
        user_answer: str,
        source_context_snippets: list[str]
    ) -> dict[str, Any]:
        # Pre-check for empty / trivial responses
        trimmed = user_answer.strip()
        if len(trimmed) < 10:
            feedback = (
                "What you understood:\n"
                "- Response too brief to establish comprehension.\n\n"
                "What is missing:\n"
                "- Conceptual definition and explanation of operational mechanism.\n\n"
                "How to improve:\n"
                "Provide a complete sentence explaining what the concept does and how it applies."
            )
            return {
                "is_correct": False,
                "score": 0.1,
                "feedback": feedback,
                "evaluation": {
                    "understanding": 0.1,
                    "accuracy": 0.1,
                    "relevance": 0.2,
                    "reasoning": 0.0,
                    "key_concepts_covered": [],
                    "missing_concepts": question.expected_concepts or ["Core definition"],
                    "overall_score": 0.1,
                    "feedback": feedback
                },
                "mistake_info": {
                    "mistake_type": "PARTIAL_UNDERSTANDING",
                    "mistake_description": "Response was minimal or incomplete."
                }
            }

        concept_title = concept.name if concept else "Target Concept"
        context_str = "\n---\n".join(source_context_snippets) if source_context_snippets else question.explanation
        expected_str = ", ".join(question.expected_concepts) if question.expected_concepts else "Core definition and application"

        system_instruction = (
            "You are a rigorous pedagogical evaluator for an AI learning companion. "
            "You evaluate open-ended conceptual explanations strictly against the provided reference answer and project material.\n"
            "DO NOT award high scores for verbosity or generic filler. Grade strictly on technical substance, precision, and expected concepts.\n"
            "Return strictly valid JSON matching the requested schema."
        )

        prompt = f"""
PROJECT: {project.name}
TARGET CONCEPT: {concept_title}
QUESTION: {question.prompt}
EXPECTED KEY CONCEPTS: {expected_str}
REFERENCE ANSWER: {question.correct_answer}
RUBRIC GUIDANCE: {question.explanation}

SOURCE MATERIAL EVIDENCE:
{context_str}

LEARNER ANSWER:
\"\"\"{trimmed}\"\"\"

Evaluate the learner answer across:
1. Understanding (0.0 to 1.0)
2. Accuracy (0.0 to 1.0)
3. Relevance (0.0 to 1.0)
4. Reasoning (0.0 to 1.0)
5. Overall score (0.0 to 1.0)
6. Key concepts covered (list of strings)
7. Missing concepts (list of strings)
8. Formulate constructive feedback formatted with clear sections:
   - What you understood
   - What is missing
   - How to improve

Return JSON matching this schema:
{{
  "understanding": 0.85,
  "accuracy": 0.80,
  "relevance": 0.90,
  "reasoning": 0.75,
  "overall_score": 0.82,
  "key_concepts_covered": ["..."],
  "missing_concepts": ["..."],
  "what_you_understood": "Clear summary of accurately explained points",
  "what_is_missing": "Explicit details, nuances, or mechanisms omitted",
  "how_to_improve": "Targeted advice for deepening understanding"
}}
"""

        try:
            res = await ai_service.generate_structured(
                prompt=prompt,
                system_instruction=system_instruction,
                feature="ASSESSMENT",
                operation="evaluate_answer"
            )
            understanding = float(res.get("understanding", 0.7))
            accuracy = float(res.get("accuracy", 0.7))
            relevance = float(res.get("relevance", 0.7))
            reasoning = float(res.get("reasoning", 0.7))
            overall_score = float(res.get("overall_score", (understanding + accuracy + relevance + reasoning) / 4.0))
            overall_score = max(0.0, min(1.0, round(overall_score, 2)))

            key_covered = res.get("key_concepts_covered", [])
            missing = res.get("missing_concepts", [])

            understood_txt = res.get("what_you_understood", "Accurately noted relevant principles.")
            missing_txt = res.get("what_is_missing", "Review key trade-offs.")
            improve_txt = res.get("how_to_improve", "Review source materials and practice applying the formula.")

            formatted_feedback = (
                f"What you understood:\n{understood_txt}\n\n"
                f"What is missing:\n{missing_txt}\n\n"
                f"How to improve:\n{improve_txt}"
            )

            is_correct = overall_score >= 0.70
            evaluation_payload = {
                "understanding": understanding,
                "accuracy": accuracy,
                "relevance": relevance,
                "reasoning": reasoning,
                "key_concepts_covered": key_covered,
                "missing_concepts": missing,
                "overall_score": overall_score,
                "feedback": formatted_feedback
            }

            mistake_info = None
            if overall_score < 0.70:
                m_type = "MISSING_CONCEPT" if missing else "CONCEPTUAL_MISUNDERSTANDING"
                if reasoning < 0.5:
                    m_type = "REASONING_ERROR"
                elif accuracy < 0.5:
                    m_type = "FACTUAL_ERROR"

                mistake_info = {
                    "mistake_type": m_type,
                    "mistake_description": f"Score {int(overall_score * 100)}%: {missing_txt[:120]}"
                }

            return {
                "is_correct": is_correct,
                "score": overall_score,
                "feedback": formatted_feedback,
                "evaluation": evaluation_payload,
                "mistake_info": mistake_info
            }

        except Exception as e:
            print(f"[AnswerEvaluator] LLM evaluation fallback: {e}", flush=True)
            # Fallback heuristic evaluation
            covered = [c for c in (question.expected_concepts or []) if c.lower() in trimmed.lower()]
            missing = [c for c in (question.expected_concepts or []) if c.lower() not in trimmed.lower()]
            score = 0.85 if len(trimmed) > 50 and len(covered) > 0 else 0.50

            feedback = (
                f"What you understood:\n"
                f"- Addressed the prompt with {len(trimmed.split())} words.\n\n"
                f"What is missing:\n"
                f"- Deep coverage of: {', '.join(missing) if missing else 'None'}\n\n"
                f"How to improve:\n"
                f"Compare your response with the reference answer: {question.correct_answer[:100]}..."
            )

            is_correct = score >= 0.70
            return {
                "is_correct": is_correct,
                "score": score,
                "feedback": feedback,
                "evaluation": {
                    "understanding": score,
                    "accuracy": score,
                    "relevance": 0.8,
                    "reasoning": score,
                    "key_concepts_covered": covered,
                    "missing_concepts": missing,
                    "overall_score": score,
                    "feedback": feedback
                },
                "mistake_info": {
                    "mistake_type": "PARTIAL_UNDERSTANDING",
                    "mistake_description": f"Partial response missing: {', '.join(missing[:2])}"
                } if not is_correct else None
            }
