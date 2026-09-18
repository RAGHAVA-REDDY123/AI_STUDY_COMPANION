import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.project import Project
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.models.mastery import ConceptMastery
from app.services.retrieval_service import RetrievalService
from app.services.context_builder import context_builder
from app.services.citation_service import citation_service
from app.services.ai import ai_service, ai_request_scope
from app.ai.prompts import TUTOR_SYSTEM_PROMPT

class TutorService:
    """
    Project-Scoped Grounded AI Tutor Service.
    Orchestrates user authorization, hybrid project retrieval, evidence-grounded
    context building, Gemini 2.5 Flash streaming, backend citation verification,
    and end-to-end AI request telemetry under a unified request_id.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = RetrievalService(db)

    async def _fetch_project_learning_context(self, project_id: UUID, user_id: UUID) -> str:
        """Fetches project-isolated mastery weak spots, diagnosed misconceptions, and preferences."""
        from app.models.concept import Concept
        from app.models.learner_context import LearnerContext

        # 1. Concept masteries with concept names
        stmt = (
            select(ConceptMastery, Concept.name)
            .join(Concept, ConceptMastery.concept_id == Concept.id)
            .where(
                ConceptMastery.project_id == project_id,
                ConceptMastery.user_id == user_id
            )
            .order_by(ConceptMastery.mastery_score.asc())
            .limit(3)
        )
        rows = (await self.db.execute(stmt)).all()
        weak_str = ", ".join(f"{name} ({m.mastery_score}% mastery, {m.consecutive_mistakes} consecutive errors)" for m, name in rows) if rows else "No specific deficits"

        # 2. Diagnosed misconceptions from LearnerContext (PRD §11 & §13)
        ctx_stmt = select(LearnerContext).where(
            LearnerContext.project_id == project_id,
            LearnerContext.user_id == user_id
        )
        l_ctx = (await self.db.execute(ctx_stmt)).scalar_one_or_none()
        diag_str = ""
        if l_ctx and l_ctx.diagnosed_misconceptions:
            top_diag = l_ctx.diagnosed_misconceptions[:2]
            diag_str = " | Active Diagnosed Misconceptions: " + "; ".join(f"{d.get('concept_name')}: {d.get('title')}" for d in top_diag)

        return f"Weak Concepts: {weak_str}{diag_str}"

    async def generate_grounded_response_stream(
        self,
        project: Project,
        user: User,
        query: str,
        conversation_id: Optional[UUID] = None
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        request_id = f"tutor_{uuid.uuid4().hex[:12]}"

        with ai_request_scope(
            request_id=request_id,
            user_id=user.id,
            project_id=project.id,
            feature="TUTOR",
            operation="generate_stream",
            model=settings.GEMINI_MODEL,
            prompt_version=settings.PROMPT_VERSION_TUTOR,
            retrieval_version=settings.RETRIEVAL_VERSION
        ):
            # 1. Fetch or initialize conversation (strictly project-scoped)
            history_messages = []
            if not conversation_id:
                convo = Conversation(
                    project_id=project.id,
                    user_id=user.id,
                    title=query[:40] + "..." if len(query) > 40 else query
                )
                self.db.add(convo)
                await self.db.commit()
                await self.db.refresh(convo)
                conversation_id = convo.id
            else:
                # Fetch recent conversation history (last 6 messages) for multi-turn continuity
                hist_stmt = (
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.desc())
                    .limit(6)
                )
                history_records = (await self.db.execute(hist_stmt)).scalars().all()
                history_messages = list(reversed(history_records))

            # 2. Context-Aware Retrieval (Augment query if user asks follow-up)
            retrieval_query = query
            if history_messages and len(query.split()) < 10:
                last_user_turn = next((m.content for m in reversed(history_messages) if m.role == MessageRole.USER), "")
                if last_user_turn:
                    retrieval_query = f"{last_user_turn} {query}"

            # Strict Project-Isolated Hybrid Retrieval with Tracing
            chunks, has_evidence = await self.retrieval_service.retrieve(
                project_id=project.id,
                query=retrieval_query,
                top_k=20,
                final_k=6,
                request_id=request_id,
                user_id=user.id
            )
            if not has_evidence and retrieval_query != query:
                chunks, has_evidence = await self.retrieval_service.retrieve(
                    project_id=project.id,
                    query=query,
                    top_k=20,
                    final_k=6,
                    request_id=request_id,
                    user_id=user.id
                )

            # 3. Context Building & Deduplication
            context_evidence, retrieved_metadata = context_builder.build_context(chunks)

            # 4. Record User Message
            user_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=query
            )
            self.db.add(user_msg)
            await self.db.commit()

            # Emit init event to client with unified request_id
            yield f"event: init\ndata: {json.dumps({'conversation_id': str(conversation_id), 'request_id': request_id})}\n\n"

            # 5. Mandatory Calibrated Refusal if evidence is insufficient
            if not has_evidence:
                refusal_text = (
                    f"I couldn't find enough information about '{query}' in the materials for this project. "
                    "The current project notes do not contain sufficient evidence to answer this. "
                    "Would you like to review your uploaded materials, or upload additional notes on this topic?"
                )
                yield f"event: chunk\ndata: {json.dumps({'text': refusal_text})}\n\n"
                yield f"event: citations\ndata: {json.dumps({'citations': []})}\n\n"
                latency_ms = int((time.time() - start_time) * 1000)
                yield f"event: done\ndata: {json.dumps({'tokens': 40, 'latency_ms': latency_ms})}\n\n"

                asst_msg = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=refusal_text,
                    citations=[],
                    is_unsupported_refusal=True,
                    tokens_used=40,
                    latency_ms=latency_ms
                )
                self.db.add(asst_msg)

                # Persist telemetry for refusal
                await ai_service.log_usage(
                    db=self.db,
                    feature="TUTOR",
                    operation="calibrated_refusal",
                    latency_ms=latency_ms,
                    input_tokens=len(query) // 4,
                    output_tokens=len(refusal_text) // 4,
                    total_tokens=(len(query) + len(refusal_text)) // 4,
                    status_code="SUCCESS",
                    request_id=request_id,
                    user_id=user.id,
                    project_id=project.id,
                    prompt_version=settings.PROMPT_VERSION_TUTOR,
                    metadata_json={"is_unsupported_refusal": True, "evidence_found": False}
                )

                from app.services.event_service import event_service, EventType
                await event_service.log_event(
                    db=self.db,
                    user_id=user.id,
                    project_id=project.id,
                    event_type=EventType.TUTOR_INTERACTION,
                    payload={"query_preview": query[:80], "is_refusal": True, "citations_count": 0},
                    auto_commit=False
                )

                await self.db.commit()
                return

            # 6. Stream Initial Citations metadata
            initial_citations = [
                {
                    "material_id": str(m.get("material_id", "")),
                    "document_title": m["document_title"],
                    "page_number": m["page_number"],
                    "section_title": m["section_title"],
                    "snippet": m["snippet"]
                }
                for m in retrieved_metadata
            ]
            yield f"event: citations\ndata: {json.dumps({'citations': initial_citations})}\n\n"

            # 7. Grounded LLM Stream via Gemini 2.5 Flash
            from app.services.tutor_tools import AVAILABLE_TOOLS_DOC, tutor_tools_executor
            import re

            weak_spots = await self._fetch_project_learning_context(project.id, user.id)
            system_instruction = TUTOR_SYSTEM_PROMPT.format(
                learning_goal=project.learning_goal or "Mastering project curriculum",
                known_weaknesses=weak_spots,
                context_chunks=context_evidence,
                user_query=query
            ) + "\n\n" + AVAILABLE_TOOLS_DOC

            full_response = ""
            history_text = "\n".join([
                f"{'Student' if m.role == MessageRole.USER else 'Tutor'}: {m.content[:350]}"
                for m in history_messages
            ]) if history_messages else "No prior dialogue in this session."

            prompt_with_data_boundary = (
                f"<context_evidence>\n{context_evidence}\n</context_evidence>\n\n"
                f"<conversation_history>\n{history_text}\n</conversation_history>\n\n"
                f"<user_query>\n{query}\n</user_query>\n\n"
                "Answer the student's question maintaining conversational continuity with the dialogue history above, "
                "while strictly grounding all factual explanations in the provided evidence. Cite sources as [Source: <Title> — Page <X>]."
            )

            stream_error = None
            try:
                async for token in ai_service.generate_stream(
                    prompt=prompt_with_data_boundary,
                    system_instruction=system_instruction
                ):
                    full_response += token
                    yield f"event: chunk\ndata: {json.dumps({'text': token})}\n\n"
            except Exception as e:
                stream_error = str(e)
                err_msg = f"\n[The AI service is temporarily busy. Please try again in a moment.]"
                full_response += err_msg
                yield f"event: chunk\ndata: {json.dumps({'text': err_msg})}\n\n"

            # PRD §8 Controlled Structured Tool Calling Execution
            tool_calls_executed = []
            tool_matches = re.findall(r'<<<TOOL_CALL:(.*?)>>>', full_response, re.DOTALL)
            for match in tool_matches:
                try:
                    tool_data = json.loads(match.strip())
                    t_name = tool_data.get("tool")
                    t_args = tool_data.get("arguments", {})
                    if t_name:
                        yield f"event: tool_call\ndata: {json.dumps({'tool': t_name, 'arguments': t_args})}\n\n"
                        t_res = await tutor_tools_executor.execute_tool(self.db, project.id, user.id, t_name, t_args)
                        yield f"event: tool_result\ndata: {json.dumps({'tool': t_name, 'result': t_res})}\n\n"
                        tool_calls_executed.append({"tool": t_name, "arguments": t_args, "result": t_res})
                except Exception as ex:
                    pass

            # Smart user query intent fallback
            q_lower = query.lower()
            if any(k in q_lower for k in ["quiz me", "test me", "practice quiz", "take a quiz"]) and not any(t["tool"] == "trigger_remedial_quiz" for t in tool_calls_executed):
                t_res = await tutor_tools_executor.execute_tool(self.db, project.id, user.id, "trigger_remedial_quiz", {"concept_name": query})
                yield f"event: tool_call\ndata: {json.dumps({'tool': 'trigger_remedial_quiz', 'arguments': {'concept_name': query}})}\n\n"
                yield f"event: tool_result\ndata: {json.dumps({'tool': 'trigger_remedial_quiz', 'result': t_res})}\n\n"
                tool_calls_executed.append({"tool": "trigger_remedial_quiz", "arguments": {"concept_name": query}, "result": t_res})
            elif any(k in q_lower for k in ["my mastery", "how am i doing", "check mastery"]) and not any(t["tool"] == "check_concept_mastery" for t in tool_calls_executed):
                t_res = await tutor_tools_executor.execute_tool(self.db, project.id, user.id, "check_concept_mastery", {"concept_name": query})
                yield f"event: tool_call\ndata: {json.dumps({'tool': 'check_concept_mastery', 'arguments': {'concept_name': query}})}\n\n"
                yield f"event: tool_result\ndata: {json.dumps({'tool': 'check_concept_mastery', 'result': t_res})}\n\n"
                tool_calls_executed.append({"tool": "check_concept_mastery", "arguments": {"concept_name": query}, "result": t_res})

            clean_response = re.sub(r'<<<TOOL_CALL:.*?>>>', '', full_response).strip()

            latency_ms = int((time.time() - start_time) * 1000)
            yield f"event: done\ndata: {json.dumps({'tokens': len(clean_response or full_response) // 4, 'latency_ms': latency_ms})}\n\n"

            # 8. Backend Citation Validation
            citation_report = citation_service.validate_citations_detailed(
                clean_response or full_response,
                retrieved_metadata
            )
            validated_citations = citation_service.validate_citations(
                clean_response or full_response,
                retrieved_metadata
            )

            # 9. Persist Assistant Message and Centralized Observability Log
            input_est = len(prompt_with_data_boundary) // 4
            output_est = max(10, len(clean_response or full_response) // 4)

            asst_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=clean_response or full_response,
                citations=validated_citations,
                is_unsupported_refusal=False,
                tokens_used=output_est,
                latency_ms=latency_ms
            )
            self.db.add(asst_msg)

            await ai_service.log_usage(
                db=self.db,
                feature="TUTOR",
                operation="generate_stream",
                latency_ms=latency_ms,
                input_tokens=input_est,
                output_tokens=output_est,
                total_tokens=input_est + output_est,
                status_code="FAILED" if stream_error else "SUCCESS",
                error_type="PROVIDER_ERROR" if stream_error else None,
                error_details=stream_error,
                request_id=request_id,
                user_id=user.id,
                project_id=project.id,
                prompt_version=settings.PROMPT_VERSION_TUTOR,
                metadata_json={
                    "citation_metrics": citation_report,
                    "retrieved_chunks_count": len(chunks)
                }
            )

            from app.services.event_service import event_service, EventType
            await event_service.log_event(
                db=self.db,
                user_id=user.id,
                project_id=project.id,
                event_type=EventType.TUTOR_INTERACTION,
                payload={
                    "query_preview": query[:80],
                    "citations_count": len(validated_citations),
                    "tokens_used": input_est + output_est,
                    "latency_ms": latency_ms
                },
                auto_commit=False
            )

            await self.db.commit()
