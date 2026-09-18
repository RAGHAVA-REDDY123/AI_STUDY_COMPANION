import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState
from app.models.quiz import QuizMistake, QuestionAnswer, Question
from app.models.recommendation import Recommendation, RecommendationAction, RecommendationStatus
from app.models.learner_context import LearnerContext
from app.services.retrieval_service import RetrievalService
from app.services.ai import ai_service
from app.services.event_service import event_service

logger = logging.getLogger(__name__)

DIAGNOSTIC_PROMPT_TEMPLATE = """You are a senior diagnostic learning scientist analyzing a student's repeated misconceptions.
The student has failed multiple consecutive assessment questions on the concept: "{concept_name}".

Student Assessment Evidence:
{evidence_text}

Perform cognitive diagnosis and return JSON matching this schema:
{{
  "misconception_title": "Concise 3-6 word label of the misunderstanding",
  "diagnosis": "2-3 sentences diagnosing the exact logical flaw, faulty assumption, or missing concept",
  "remediation_action": "Clear, actionable study instruction to overcome this gap",
  "search_query": "3-5 technical keywords to look up the relevant explanation in the course notes"
}}
"""

class RemediationService:
    """
    PRD §13 Intelligent Background Workflows:
    Repeated Mistake -> Identify Pattern -> Update Learning Context -> Generate Targeted Recommendation.
    """

    @staticmethod
    async def diagnose_repeated_mistakes_task(project_id_str: str, user_id_str: str, concept_id_str: str):
        """
        Asynchronous background task invoked when consecutive_mistakes >= 2.
        Executes without blocking the user's quiz or evaluation flow.
        """
        project_id = UUID(project_id_str)
        user_id = UUID(user_id_str)
        concept_id = UUID(concept_id_str)

        start_time = time.time()
        logger.info(f"[Remediation Worker] Initiating diagnosis for concept {concept_id} (User {user_id})")

        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch Concept details
                concept = (await db.execute(select(Concept).where(Concept.id == concept_id))).scalar_one_or_none()
                if not concept:
                    logger.warning(f"[Remediation Worker] Concept {concept_id} not found")
                    return

                # 2. Fetch recent mistakes
                mistake_stmt = (
                    select(QuizMistake)
                    .where(
                        QuizMistake.project_id == project_id,
                        QuizMistake.user_id == user_id,
                        QuizMistake.concept_id == concept_id
                    )
                    .order_by(QuizMistake.created_at.desc())
                    .limit(4)
                )
                mistakes = (await db.execute(mistake_stmt)).scalars().all()

                # Also fetch question answers
                ans_stmt = (
                    select(QuestionAnswer, Question)
                    .join(Question, QuestionAnswer.question_id == Question.id)
                    .where(
                        QuestionAnswer.user_id == user_id,
                        Question.concept_id == concept_id,
                        QuestionAnswer.is_correct == False
                    )
                    .order_by(QuestionAnswer.answered_at.desc())
                    .limit(4)
                )
                ans_rows = (await db.execute(ans_stmt)).all()

                evidence_items = []
                for idx, (qa, q) in enumerate(ans_rows):
                    evidence_items.append(
                        f"Item {idx + 1}:\n"
                        f"- Question: {q.prompt}\n"
                        f"- Student Answer: {qa.user_answer}\n"
                        f"- Expected Correct: {q.correct_answer}\n"
                        f"- Explanation: {q.explanation}\n"
                    )

                if not evidence_items and not mistakes:
                    logger.info(f"[Remediation Worker] Insufficient error history to diagnose concept {concept.name}")
                    return

                evidence_text = "\n".join(evidence_items) if evidence_items else f"User flagged {len(mistakes)} mistakes on {concept.name}."

                # 3. LLM Diagnostic Reasoning
                prompt = DIAGNOSTIC_PROMPT_TEMPLATE.format(
                    concept_name=concept.name,
                    evidence_text=evidence_text
                )

                try:
                    diag_json = await ai_service.provider.generate_structured(
                        prompt=prompt,
                        system_instruction="You are a rigorous diagnostic cognitive evaluation model. Respond strictly in valid JSON.",
                        temperature=0.1
                    )
                except Exception as e:
                    logger.error(f"[Remediation Worker] AI structured diagnostic failed: {e}")
                    diag_json = {
                        "misconception_title": f"Misconception in {concept.name}",
                        "diagnosis": f"The student repeatedly struggles with foundational principles of {concept.name}.",
                        "remediation_action": f"Review foundational sections covering {concept.name} and test again.",
                        "search_query": concept.name
                    }

                misconception_title = diag_json.get("misconception_title", f"Gap in {concept.name}")
                diagnosis_text = diag_json.get("diagnosis", "")
                remediation_action = diag_json.get("remediation_action", "")
                search_query = diag_json.get("search_query", concept.name)

                # 4. Search Project Materials for Citation Anchoring
                retrieval_service = RetrievalService(db)
                chunks, has_evidence = await retrieval_service.retrieve(
                    project_id=project_id,
                    query=search_query,
                    top_k=5,
                    final_k=1,
                    user_id=user_id
                )

                doc_title = "Study Materials"
                page_num = 1
                snippet = ""
                if chunks:
                    best_chunk = chunks[0]
                    doc_title = best_chunk.get("document_title", "Uploaded Material")
                    page_num = best_chunk.get("page_number", 1)
                    snippet = best_chunk.get("content", "")[:200]

                citation_ref = f"[Source: {doc_title} — Page {page_num}]"

                # 5. Persist High-Priority Targeted Recommendation
                rec_title = f"Remediate: {misconception_title}"
                rec_reasoning = (
                    f"{diagnosis_text} "
                    f"Recommended Action: Review {citation_ref} to correct this misconception before attempting the next assessment."
                )

                recommendation = Recommendation(
                    project_id=project_id,
                    user_id=user_id,
                    concept_id=concept_id,
                    title=rec_title,
                    reasoning=rec_reasoning,
                    action_type=RecommendationAction.REVISE_CONCEPT,
                    target_payload={
                        "material_id": str(chunks[0].get("material_id", "")) if chunks else "",
                        "concept_id": str(concept_id),
                        "concept_name": concept.name,
                        "citation": citation_ref,
                        "document_title": doc_title,
                        "page_number": page_num,
                        "snippet": snippet,
                        "diagnosis": diagnosis_text,
                        "remediation_action": remediation_action
                    },
                    status=RecommendationStatus.PENDING,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(recommendation)

                # 6. Update Persistent Learner Context (PRD §11)
                ctx_stmt = select(LearnerContext).where(
                    LearnerContext.project_id == project_id,
                    LearnerContext.user_id == user_id
                )
                learner_ctx = (await db.execute(ctx_stmt)).scalar_one_or_none()
                if not learner_ctx:
                    learner_ctx = LearnerContext(
                        project_id=project_id,
                        user_id=user_id,
                        strengths=[],
                        weaknesses=[concept.name],
                        diagnosed_misconceptions=[],
                        tutor_preferences={"explanation_style": "intuitive_with_examples"}
                    )
                    db.add(learner_ctx)
                else:
                    if concept.name not in (learner_ctx.weaknesses or []):
                        learner_ctx.weaknesses = list(set((learner_ctx.weaknesses or []) + [concept.name]))

                misconception_entry = {
                    "concept_id": str(concept_id),
                    "concept_name": concept.name,
                    "title": misconception_title,
                    "diagnosis": diagnosis_text,
                    "citation": citation_ref,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                curr_misconceptions = list(learner_ctx.diagnosed_misconceptions or [])
                curr_misconceptions.insert(0, misconception_entry)
                learner_ctx.diagnosed_misconceptions = curr_misconceptions[:10]  # retain top 10
                learner_ctx.updated_at = datetime.now(timezone.utc)

                # 7. Log Activity Event
                await event_service.log_event(
                    db=db,
                    user_id=user_id,
                    project_id=project_id,
                    event_type="REPEATED_MISTAKE_DIAGNOSED",
                    payload={
                        "concept_name": concept.name,
                        "misconception": misconception_title,
                        "citation": citation_ref,
                        "page_number": page_num
                    },
                    auto_commit=False
                )

                # 8. Observability Usage Log
                latency_ms = int((time.time() - start_time) * 1000)
                await ai_service.log_usage(
                    db=db,
                    feature="REPEATED_MISTAKE_WORKFLOW",
                    operation="diagnose_misconception",
                    latency_ms=latency_ms,
                    input_tokens=len(prompt) // 4,
                    output_tokens=len(str(diag_json)) // 4,
                    total_tokens=(len(prompt) + len(str(diag_json))) // 4,
                    status_code="SUCCESS",
                    user_id=user_id,
                    project_id=project_id,
                    metadata_json={
                        "concept_name": concept.name,
                        "misconception_title": misconception_title,
                        "citation_ref": citation_ref
                    }
                )

                await db.commit()
                logger.info(f"[Remediation Worker] Successfully created targeted recommendation for {concept.name} -> {rec_title}")

            except Exception as e:
                logger.error(f"[Remediation Worker] Workflow failed: {e}", exc_info=True)
                await db.rollback()

remediation_service = RemediationService()
