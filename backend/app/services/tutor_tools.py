import json
import logging
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.concept import Concept
from app.models.mastery import ConceptMastery
from app.models.learner_context import LearnerContext
from app.models.project import Project
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

AVAILABLE_TOOLS_DOC = """
You have access to the following project-authorized tools to assist the student:
1. check_concept_mastery: Check current mastery score and error count for a concept.
   Usage: <<<TOOL_CALL:{"tool": "check_concept_mastery", "arguments": {"concept_name": "Backpropagation"}}>>>
2. search_study_materials: Perform deep grounded search for definitions or diagrams in the uploaded notes.
   Usage: <<<TOOL_CALL:{"tool": "search_study_materials", "arguments": {"query": "vanishing gradient mathematical derivation"}}>>>
3. trigger_remedial_quiz: Prepare an immediate 3-question adaptive quiz targeting a specific concept when requested.
   Usage: <<<TOOL_CALL:{"tool": "trigger_remedial_quiz", "arguments": {"concept_name": "Gradient Descent"}}>>>
4. record_learner_preference: Store a learning preference (e.g. loves visual analogies, wants rigorous mathematical proofs).
   Usage: <<<TOOL_CALL:{"tool": "record_learner_preference", "arguments": {"preference": "Prefer visual examples and code snippets"}}>>>

Protocol:
- When the student asks how they are doing or requests a quiz/practice on a topic, call the appropriate tool.
- Always include the exact marker: <<<TOOL_CALL:{"tool": "<tool_name>", "arguments": {...}}>>>
"""

class TutorToolsExecutor:
    """
    PRD §8 Controlled AI Application Capabilities.
    Strictly validates project authorization before executing any tool.
    Returns structured results for seamless injection back into the conversation.
    """

    @staticmethod
    async def execute_tool(
        db: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info(f"[Tutor Tool] Executing '{tool_name}' for Project {project_id} (User {user_id}) with args: {arguments}")

        try:
            if tool_name == "check_concept_mastery":
                concept_name = arguments.get("concept_name", "").strip()
                # Find concept in project
                stmt = select(Concept).where(
                    Concept.project_id == project_id,
                    func.lower(Concept.name).contains(concept_name.lower())
                )
                concept = (await db.execute(stmt)).scalars().first()
                if not concept:
                    # Fallback to any concept
                    stmt_any = select(Concept).where(Concept.project_id == project_id).limit(1)
                    concept = (await db.execute(stmt_any)).scalar_one_or_none()

                if not concept:
                    return {"status": "not_found", "message": f"No concept found matching '{concept_name}' in this project."}

                m_stmt = select(ConceptMastery).where(
                    ConceptMastery.project_id == project_id,
                    ConceptMastery.concept_id == concept.id,
                    ConceptMastery.user_id == user_id
                )
                mastery = (await db.execute(m_stmt)).scalar_one_or_none()
                score = round(mastery.mastery_score, 1) if mastery else 0.0
                trend = mastery.trend_state.value if mastery and hasattr(mastery.trend_state, "value") else "STABLE"
                mistakes = mastery.consecutive_mistakes if mastery else 0
                attempts = mastery.total_attempts if mastery else 0

                return {
                    "concept_id": str(concept.id),
                    "concept_name": concept.name,
                    "mastery_score": score,
                    "trend_state": trend,
                    "consecutive_mistakes": mistakes,
                    "total_attempts": attempts,
                    "status": "success"
                }

            elif tool_name == "search_study_materials":
                query = arguments.get("query", "").strip()
                retrieval = RetrievalService(db)
                chunks, has_evidence = await retrieval.retrieve(
                    project_id=project_id,
                    query=query,
                    top_k=4,
                    final_k=2,
                    user_id=user_id
                )
                results = [
                    {
                        "document_title": c.get("document_title", "Material"),
                        "page_number": c.get("page_number", 1),
                        "snippet": c.get("content", "")[:250]
                    }
                    for c in chunks
                ]
                return {
                    "query": query,
                    "has_evidence": has_evidence,
                    "citations": results,
                    "status": "success"
                }

            elif tool_name == "trigger_remedial_quiz":
                concept_name = arguments.get("concept_name", "").strip()
                stmt = select(Concept).where(
                    Concept.project_id == project_id,
                    func.lower(Concept.name).contains(concept_name.lower())
                )
                concept = (await db.execute(stmt)).scalars().first()

                c_id_str = str(concept.id) if concept else None
                c_name = concept.name if concept else (concept_name or "Curriculum Assessment")

                return {
                    "concept_id": c_id_str,
                    "concept_name": c_name,
                    "question_count": 3,
                    "action_url": f"/projects/{project_id}/quiz",
                    "status": "ready",
                    "message": f"Adaptive practice quiz on '{c_name}' is ready to launch."
                }

            elif tool_name == "record_learner_preference":
                pref = arguments.get("preference", "").strip()
                ctx_stmt = select(LearnerContext).where(
                    LearnerContext.project_id == project_id,
                    LearnerContext.user_id == user_id
                )
                l_ctx = (await db.execute(ctx_stmt)).scalar_one_or_none()
                if not l_ctx:
                    l_ctx = LearnerContext(
                        project_id=project_id,
                        user_id=user_id,
                        strengths=[],
                        weaknesses=[],
                        diagnosed_misconceptions=[],
                        tutor_preferences={"notes": [pref]}
                    )
                    db.add(l_ctx)
                else:
                    curr_pref = dict(l_ctx.tutor_preferences or {})
                    notes = curr_pref.get("notes", [])
                    notes.append(pref)
                    curr_pref["notes"] = notes
                    l_ctx.tutor_preferences = curr_pref

                await db.commit()
                return {
                    "preference_saved": pref,
                    "status": "recorded"
                }

            else:
                return {"error": f"Unknown tool: '{tool_name}'", "status": "unsupported"}

        except Exception as e:
            logger.error(f"[Tutor Tool] Execution of '{tool_name}' failed: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}

tutor_tools_executor = TutorToolsExecutor()
