import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.user import User
from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState
from app.models.quiz import QuizMistake
from app.models.learner_context import LearnerContext
from app.models.chunk import DocumentChunk
from app.models.material import Material
from app.schemas.cheat_sheet import (
    CheatSheetResponse,
    ExamTrapItem,
    CoreFormulaItem,
    HighYieldConceptItem,
    RapidFireQAItem,
    CrammingChecklistItem,
)
from app.services.ai import ai_service
from app.services.event_service import event_service

logger = logging.getLogger(__name__)

CHEAT_SHEET_CACHE: Dict[str, Dict[str, Any]] = {}

CHEAT_SHEET_SYSTEM_PROMPT = """You are an elite academic tutor and exam preparation specialist.
Your mission is to generate an intensely dense, high-yield, personalized Exam Revision Cheat Sheet.

Key Rules:
1. PERSONALIZED TRAPS: Prioritize the student's ACTUAL recorded misconceptions and quiz mistakes. Highlight the subtle traps examiners use to test these concepts.
2. CORE FORMULAS & RULES: Extract high-yield equations, laws, and foundational theorems from the course materials. Explain notation concisely and cite the exact page.
3. CITATIONS: Use exact page numbers from the provided chunks (e.g. Page 14).
4. HIGH DENSITY & ACTIVE RECALL: Keep explanations punchy, authoritative, and direct. Avoid generic filler.

Return ONLY valid JSON strictly adhering to:
{
  "personalized_traps": [
    {
      "misconception_title": "Short title",
      "what_student_missed": "What mistake was made or faulty intuition occurred",
      "exam_trap_warning": "Warning on how exam questions trick students on this",
      "correct_mental_model": "Definitive correct rule to apply",
      "source_page": 14,
      "concept_name": "Concept name"
    }
  ],
  "core_formulas": [
    {
      "name": "Formula or Law Name",
      "formula_or_rule": "Mathematical notation or algorithmic rule",
      "plain_explanation": "Intuitive breakdown of terms",
      "source_citation": "Source: Notes — Page 14",
      "page_number": 14
    }
  ],
  "high_yield_concepts": [
    {
      "concept_name": "Concept Name",
      "key_takeaway": "Dense 1-sentence exam rule",
      "page_number": 14
    }
  ],
  "rapid_fire_qa": [
    {
      "question": "Quick recall exam question",
      "quick_answer": "Punchy 1-sentence answer",
      "key_term": "Core technical keyword"
    }
  ],
  "cramming_checklist": [
    {
      "id": "c1",
      "task": "Revision task description",
      "is_critical": true,
      "estimated_mins": 5,
      "concept_name": "Concept Name"
    }
  ]
}
"""

class CheatSheetService:
    """
    Synthesizes project study notes, atomic concepts, and the student's real quiz mistakes
    into a personalized, high-yield Exam Revision Cheat Sheet.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_generate_cheat_sheet(
        self,
        project: Project,
        user: User,
        force_regenerate: bool = False
    ) -> CheatSheetResponse:
        cache_key = f"{project.id}_{user.id}"
        if not force_regenerate and cache_key in CHEAT_SHEET_CACHE:
            cached = CHEAT_SHEET_CACHE[cache_key]
            # Cache valid for 30 minutes
            if time.time() - cached["cached_at"] < 1800:
                return cached["data"]

        start_time = time.time()

        # 1. Fetch Concepts and Masteries
        concept_stmt = select(Concept).where(Concept.project_id == project.id)
        concepts = (await self.db.execute(concept_stmt)).scalars().all()

        mastery_stmt = select(ConceptMastery).where(
            ConceptMastery.project_id == project.id,
            ConceptMastery.user_id == user.id
        )
        all_masteries = (await self.db.execute(mastery_stmt)).scalars().all()
        masteries = {}
        for m in all_masteries:
            masteries[str(m.concept_id)] = m
            if m.concept and m.concept.name:
                masteries[m.concept.name.lower()] = m

        # 2. Fetch LearnerContext (diagnosed misconceptions & weaknesses)
        context_stmt = select(LearnerContext).where(
            LearnerContext.project_id == project.id,
            LearnerContext.user_id == user.id
        )
        learner_ctx = (await self.db.execute(context_stmt)).scalar_one_or_none()

        # 3. Fetch recent Quiz Mistakes
        mistake_stmt = (
            select(QuizMistake)
            .where(QuizMistake.project_id == project.id, QuizMistake.user_id == user.id)
            .order_by(QuizMistake.created_at.desc())
            .limit(6)
        )
        mistakes = (await self.db.execute(mistake_stmt)).scalars().all()

        # 4. Fetch Sample Document Chunks & Primary Material ID
        mat_stmt = select(Material).where(Material.project_id == project.id).order_by(Material.created_at.desc())
        materials = (await self.db.execute(mat_stmt)).scalars().all()
        primary_material_id = str(materials[0].id) if materials else ""

        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project.id)
            .order_by(DocumentChunk.page_number.asc())
            .limit(10)
        )
        chunks = (await self.db.execute(chunk_stmt)).scalars().all()

        # Compute Exam Readiness Score
        scores = [m.mastery_score for m in all_masteries]
        avg_mastery = int(sum(scores) / len(scores)) if scores else 50
        penalties = sum(5 for m in all_masteries if m.consecutive_mistakes >= 1)
        exam_readiness = max(15, min(98, avg_mastery - penalties))

        # Context summary strings for AI
        diagnosed_misconceptions = learner_ctx.diagnosed_misconceptions if learner_ctx else []
        weak_list = learner_ctx.weaknesses if learner_ctx else []

        mistake_summary = "\n".join([
            f"- Mistake: {m.mistake_description} (User answer: '{m.user_answer or 'Incorrect'}')"
            for m in mistakes
        ]) or "No recent quiz mistakes recorded."

        misconception_summary = "\n".join([
            f"- Diagnosed Misconception on {m.get('concept', 'Topic')}: {m.get('diagnosis', '')}"
            for m in diagnosed_misconceptions
        ]) or "No cognitive misconceptions diagnosed yet."

        chunk_snippets = "\n\n".join([
            f"[Page {c.page_number} | {c.section_title or 'Section'}]\n{c.content[:350]}"
            for c in chunks
        ]) or "Course notes summary: Fundamentals of " + (project.name or "Domain")

        concept_list_str = ", ".join([c.name for c in concepts]) if concepts else project.name

        prompt = f"""Generate the high-yield Exam Revision Cheat Sheet for:
Project Name: {project.name}
Learning Goal: {project.learning_goal or "Complete Curriculum Mastery"}
Course Concepts: {concept_list_str}

Student Performance Profile:
- Current Average Mastery: {avg_mastery}%
- Weak Concepts: {', '.join(weak_list) if weak_list else 'None specified'}
- Recent Quiz Mistakes:
{mistake_summary}
- Diagnosed Misconceptions:
{misconception_summary}

Course Notes Evidence Excerpts:
{chunk_snippets}

Synthesize a comprehensive, high-yield cheat sheet in the specified JSON schema.
"""

        ai_res = None
        try:
            ai_res_obj = await ai_service.generate_structured(
                prompt=prompt,
                system_instruction=CHEAT_SHEET_SYSTEM_PROMPT,
                max_output_tokens=4096,
                feature="CHEAT_SHEET",
                db=self.db,
                project_id=project.id,
                user_id=user.id
            )
            ai_res = ai_res_obj.get("data")
        except Exception as e:
            logger.warning(f"[CheatSheetService] AI generation error ({e}), using deterministic synthesis fallback")

        # Extract or synthesize items
        personalized_traps = []
        if ai_res and "personalized_traps" in ai_res and isinstance(ai_res["personalized_traps"], list):
            for t in ai_res["personalized_traps"]:
                personalized_traps.append(ExamTrapItem(
                    misconception_title=t.get("misconception_title", "Concept Misconception"),
                    what_student_missed=t.get("what_student_missed", "Common procedural error"),
                    exam_trap_warning=t.get("exam_trap_warning", "Exam questions often present this distractor."),
                    correct_mental_model=t.get("correct_mental_model", "Apply the core definition strictly."),
                    source_page=t.get("source_page") or (chunks[0].page_number if chunks else 1),
                    concept_name=t.get("concept_name")
                ))

        # Fallback traps if none returned or student had mistakes
        if not personalized_traps:
            for c in concepts[:3]:
                m_obj = masteries.get(c.name.lower())
                score = round(float(m_obj.mastery_score), 1) if m_obj else 50.0
                personalized_traps.append(ExamTrapItem(
                    misconception_title=f"Exam Trap: {c.name}",
                    what_student_missed=f"Tendency to confuse edge-case behavior when mastery is at {score}%.",
                    exam_trap_warning=f"Questions on {c.name} typically test boundary conditions and subtle assumptions.",
                    correct_mental_model=f"Anchor your reasoning in: {c.description[:120]}...",
                    source_page=chunks[0].page_number if chunks else 1,
                    concept_name=c.name
                ))

        core_formulas = []
        if ai_res and "core_formulas" in ai_res and isinstance(ai_res["core_formulas"], list):
            for f in ai_res["core_formulas"]:
                p_num = f.get("page_number") or (chunks[0].page_number if chunks else 1)
                core_formulas.append(CoreFormulaItem(
                    name=f.get("name", "Core Principle"),
                    formula_or_rule=f.get("formula_or_rule", "Rule / Invariant"),
                    plain_explanation=f.get("plain_explanation", "Intuitive formulation"),
                    source_citation=f.get("source_citation", f"Source: Materials — Page {p_num}"),
                    page_number=p_num,
                    material_id=primary_material_id
                ))

        if not core_formulas:
            for i, c in enumerate(concepts[:4]):
                p_num = chunks[i].page_number if i < len(chunks) else 1
                core_formulas.append(CoreFormulaItem(
                    name=f"{c.name} Principle",
                    formula_or_rule=f"Definition({c.name}) == Invariant",
                    plain_explanation=c.description[:140],
                    source_citation=f"Source: Study Material — Page {p_num}",
                    page_number=p_num,
                    material_id=primary_material_id
                ))

        high_yield_concepts = []
        ai_hy_map = {item.get("concept_name", "").lower(): item.get("key_takeaway", "") for item in ai_res.get("high_yield_concepts", [])} if ai_res else {}

        for c in concepts:
            m_obj = masteries.get(c.name.lower())
            m_score = round(float(m_obj.mastery_score), 1) if m_obj else 50.0
            t_state = m_obj.trend_state.value if m_obj else "STABLE"
            takeaway = ai_hy_map.get(c.name.lower()) or f"Crucial definition: {c.description[:110]}."
            high_yield_concepts.append(HighYieldConceptItem(
                concept_name=c.name,
                mastery_score=m_score,
                trend_state=t_state,
                importance_score=c.importance_score or 0.85,
                key_takeaway=takeaway,
                page_number=chunks[0].page_number if chunks else 1
            ))

        rapid_fire_qa = []
        if ai_res and "rapid_fire_qa" in ai_res and isinstance(ai_res["rapid_fire_qa"], list):
            for qa in ai_res["rapid_fire_qa"]:
                rapid_fire_qa.append(RapidFireQAItem(
                    question=qa.get("question", "What is the core takeaway?"),
                    quick_answer=qa.get("quick_answer", "Key principle."),
                    key_term=qa.get("key_term", "Key Concept")
                ))

        if not rapid_fire_qa:
            for c in concepts[:5]:
                rapid_fire_qa.append(RapidFireQAItem(
                    question=f"What defines {c.name} in one sentence?",
                    quick_answer=c.description,
                    key_term=c.name
                ))

        cramming_checklist = []
        if ai_res and "cramming_checklist" in ai_res and isinstance(ai_res["cramming_checklist"], list):
            for i, item in enumerate(ai_res["cramming_checklist"]):
                cramming_checklist.append(CrammingChecklistItem(
                    id=f"chk_{i+1}",
                    task=item.get("task", f"Review key principles"),
                    is_critical=item.get("is_critical", False),
                    estimated_mins=item.get("estimated_mins", 5),
                    concept_name=item.get("concept_name")
                ))

        if not cramming_checklist:
            for i, c in enumerate(concepts[:6]):
                m_obj = masteries.get(c.name.lower())
                is_crit = bool(m_obj and (m_obj.consecutive_mistakes >= 1 or m_obj.mastery_score < 60))
                cramming_checklist.append(CrammingChecklistItem(
                    id=f"chk_{i+1}",
                    task=f"Review definition and applications of {c.name}",
                    is_critical=is_crit,
                    estimated_mins=3 if not is_crit else 7,
                    concept_name=c.name
                ))

        response = CheatSheetResponse(
            project_id=str(project.id),
            project_name=project.name,
            learning_goal=project.learning_goal or "Course Mastery",
            exam_readiness_score=exam_readiness,
            generated_at=datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC"),
            total_concepts_covered=len(concepts),
            critical_traps_count=len(personalized_traps),
            personalized_traps=personalized_traps,
            core_formulas=core_formulas,
            high_yield_concepts=high_yield_concepts,
            rapid_fire_qa=rapid_fire_qa,
            cramming_checklist=cramming_checklist
        )

        # Cache response
        CHEAT_SHEET_CACHE[cache_key] = {
            "cached_at": time.time(),
            "data": response
        }

        # Telemetry & Event Logging
        latency_ms = int((time.time() - start_time) * 1000)
        try:
            await ai_service.log_usage(
                db=self.db,
                feature="CHEAT_SHEET",
                operation="generate_cheat_sheet",
                latency_ms=latency_ms,
                input_tokens=len(prompt) // 4,
                output_tokens=800,
                total_tokens=(len(prompt) // 4) + 800,
                status_code="SUCCESS",
                user_id=user.id,
                project_id=project.id,
                prompt_version="cheat_sheet_v1.0",
                metadata_json={"exam_readiness": exam_readiness, "traps_count": len(personalized_traps)}
            )
            await event_service.log_event(
                db=self.db,
                user_id=user.id,
                project_id=project.id,
                event_type="CHEAT_SHEET_GENERATED",
                payload={"exam_readiness": exam_readiness, "formulas_count": len(core_formulas)}
            )
        except Exception:
            pass

        return response
