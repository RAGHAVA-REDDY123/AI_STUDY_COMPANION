from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.user import User
from app.models.concept import Concept
from app.models.chunk import DocumentChunk
from app.models.quiz import (
    Quiz, Question, QuestionAnswer, QuizStatus,
    QuestionType, QuestionDifficulty, QuizMistake, MistakeType
)
from app.models.mastery import ConceptMastery, GrowthState, MasteryHistoryPoint
from app.models.recommendation import Recommendation, RecommendationAction, RecommendationStatus
from app.models.event import ActivityEvent
from app.schemas.quiz import QuizSubmitPayload
from app.services.quiz.adaptive_engine import AdaptiveEngine
from app.services.quiz.question_generator import QuestionGenerator
from app.services.quiz.answer_evaluator import AnswerEvaluator
from app.services.quiz.mistake_service import MistakeService
from app.services.quiz.mastery_integration import MasteryIntegration
from app.services.ai import ai_service

class QuizService:
    """
    End-to-End Adaptive Quiz Service.
    Orchestrates evidence-based question generation, deterministic/AI rubric evaluation,
    mastery tracking, mistake logging, growth updates, and recommendation generation.
    Enforces strict project-level isolation at every step.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.adaptive_engine = AdaptiveEngine(db)
        self.question_generator = QuestionGenerator(db)
        self.answer_evaluator = AnswerEvaluator()
        self.mistake_service = MistakeService(db)
        self.mastery_integration = MasteryIntegration(db)

    # --- Step 1: Start Quiz & Generate First Adaptive Question ---

    async def start_quiz(
        self,
        project: Project,
        user: User,
        question_count: int = 5,
        question_types: Optional[list[QuestionType]] = None
    ) -> tuple[Quiz, Question]:
        """
        Initializes an adaptive quiz and generates Question 1 grounded in project evidence.
        """
        allowed_types = question_types or [QuestionType.MCQ, QuestionType.OPEN_ENDED]

        # 1. Create Quiz entity
        new_quiz = Quiz(
            project_id=project.id,
            user_id=user.id,
            status=QuizStatus.IN_PROGRESS,
            total_questions=question_count,
            completed_questions=0,
            score_percentage=0.0,
            overall_score=0.0,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(new_quiz)
        await self.db.flush()

        # 2. Select initial concept & difficulty adaptively
        concept, difficulty, _ = await self.adaptive_engine.select_target_concept_and_difficulty(
            project_id=project.id,
            user_id=user.id,
            quiz_id=new_quiz.id,
            recent_question_concept_ids=[]
        )

        if not concept:
            # Fallback concept if project has no ingested concepts yet
            concept_stmt = select(Concept).where(Concept.project_id == project.id).limit(1)
            concept = (await self.db.execute(concept_stmt)).scalar_one_or_none()
            if not concept:
                # Create a baseline concept for this project
                concept = Concept(
                    project_id=project.id,
                    name=f"{project.name} Foundations",
                    description=project.learning_goal,
                    importance_score=0.9
                )
                self.db.add(concept)
                await self.db.flush()

        # Choose question format (MCQ for Q1 is standard entry point)
        q_type = QuestionType.MCQ if QuestionType.MCQ in allowed_types else allowed_types[0]

        # 3. Generate Question 1 via project-scoped RAG + Gemini 2.5 Flash
        q_data, chunk_ids = await self.question_generator.generate_question(
            project=project,
            concept=concept,
            difficulty=difficulty,
            question_type=q_type,
            current_mastery_score=50.0,
            recent_mistake_descriptions=[],
            existing_prompts=[]
        )

        first_question = Question(
            quiz_id=new_quiz.id,
            project_id=project.id,
            concept_id=concept.id,
            question_type=q_data["question_type"],
            difficulty=q_data["difficulty"],
            question_order=1,
            prompt=q_data["prompt"],
            options=q_data.get("options", []),
            correct_answer=q_data["correct_answer"],
            explanation=q_data["explanation"],
            expected_concepts=q_data.get("expected_concepts", []),
            source_chunk_ids=chunk_ids,
            status="PENDING"
        )
        self.db.add(first_question)

        # 4. Activity event logging
        self._log_activity(
            user_id=user.id,
            project_id=project.id,
            event_type="QUIZ_STARTED",
            payload={"quiz_id": str(new_quiz.id), "total_questions": question_count}
        )
        self._log_activity(
            user_id=user.id,
            project_id=project.id,
            event_type="QUESTION_GENERATED",
            payload={"quiz_id": str(new_quiz.id), "question_order": 1, "concept": concept.name}
        )

        await self.db.commit()
        await self.db.refresh(new_quiz)
        await self.db.refresh(first_question)

        return new_quiz, first_question

    # --- Step 2: Get Current Quiz State & Active Question ---

    async def get_quiz_state(self, quiz_id: UUID, user: User) -> dict[str, Any]:
        stmt = (
            select(Quiz)
            .options(selectinload(Quiz.questions), selectinload(Quiz.answers))
            .where(Quiz.id == quiz_id)
        )
        quiz = (await self.db.execute(stmt)).scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
        if quiz.user_id != user.id and getattr(user, "role", None) != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Find current active unanswered question
        current_q = None
        for q in sorted(quiz.questions, key=lambda x: x.question_order):
            if q.status == "PENDING":
                current_q = q
                break

        return {
            "quiz_id": quiz.id,
            "project_id": quiz.project_id,
            "status": quiz.status,
            "total_questions": quiz.total_questions,
            "completed_questions": quiz.completed_questions,
            "score_percentage": quiz.score_percentage,
            "current_question": current_q
        }

    async def get_current_question(self, quiz_id: UUID, user: User) -> Optional[Question]:
        state = await self.get_quiz_state(quiz_id, user)
        return state["current_question"]

    # --- Step 3: Submit Answer & Evaluate ---

    async def submit_question_answer(
        self,
        quiz_id: UUID,
        question_id: UUID,
        user: User,
        user_answer: str
    ) -> dict[str, Any]:
        """
        Evaluates answer, records mistakes, updates mastery, and advances quiz state.
        """
        # 1. Fetch Question & Quiz with strict user/project verification
        stmt_q = (
            select(Question)
            .options(selectinload(Question.concept), selectinload(Question.quiz))
            .where(Question.id == question_id, Question.quiz_id == quiz_id)
        )
        question = (await self.db.execute(stmt_q)).scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        quiz = question.quiz
        if quiz.user_id != user.id and getattr(user, "role", None) != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 2. Prevent duplicate answer submission
        stmt_existing = select(QuestionAnswer).where(
            QuestionAnswer.question_id == question.id,
            QuestionAnswer.quiz_id == quiz.id
        )
        if (await self.db.execute(stmt_existing)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question has already been answered")

        # Fetch Project
        project_stmt = select(Project).where(Project.id == quiz.project_id)
        project = (await self.db.execute(project_stmt)).scalar_one()

        # Retrieve source context snippets for open-ended rubric grounding
        context_snippets = []
        if question.source_chunk_ids:
            chunk_stmt = select(DocumentChunk.content).where(
                DocumentChunk.id.in_([UUID(cid) if isinstance(cid, str) else cid for cid in question.source_chunk_ids]),
                DocumentChunk.project_id == project.id
            )
            chunks = (await self.db.execute(chunk_stmt)).scalars().all()
            context_snippets = [c for c in chunks if c]

        # 3. Evaluate answer
        eval_result = await self.answer_evaluator.evaluate(
            project=project,
            question=question,
            concept=question.concept,
            user_answer=user_answer,
            source_context_snippets=context_snippets
        )

        is_correct = eval_result["is_correct"]
        score = eval_result["score"]
        feedback = eval_result["feedback"]
        rubric_eval = eval_result["evaluation"]

        # 4. Record Mistake if error occurred
        if eval_result.get("mistake_info"):
            m_info = eval_result["mistake_info"]
            await self.mistake_service.record_mistake(
                project_id=project.id,
                user_id=user.id,
                quiz_id=quiz.id,
                question_id=question.id,
                concept_id=question.concept_id,
                mistake_type_str=m_info["mistake_type"],
                description=m_info["mistake_description"],
                user_answer=user_answer
            )

        # 5. Update Mastery & log history point
        m_before = 50.0
        m_after = 50.0
        if question.concept:
            m_before, m_after, _ = await self.mastery_integration.update_concept_mastery(
                project_id=project.id,
                user_id=user.id,
                concept=question.concept,
                difficulty=question.difficulty,
                score=score,
                quiz_id=quiz.id,
                question_id=question.id
            )

        # 6. Persist Answer
        qa = QuestionAnswer(
            question_id=question.id,
            quiz_id=quiz.id,
            project_id=project.id,
            user_id=user.id,
            user_answer=user_answer,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            evaluation=rubric_eval,
            rubric_feedback=rubric_eval,
            answered_at=datetime.now(timezone.utc)
        )
        self.db.add(qa)

        # 7. Update Question & Quiz state
        question.status = "ANSWERED"
        quiz.completed_questions += 1

        # Activity logging
        self._log_activity(
            user_id=user.id,
            project_id=project.id,
            event_type="QUESTION_ANSWERED",
            payload={"quiz_id": str(quiz.id), "question_id": str(question.id), "score": score}
        )
        self._log_activity(
            user_id=user.id,
            project_id=project.id,
            event_type="QUESTION_CORRECT" if is_correct else "QUESTION_INCORRECT",
            payload={"quiz_id": str(quiz.id), "question_id": str(question.id)}
        )

        await self.db.commit()

        return {
            "question_id": question.id,
            "is_correct": is_correct,
            "score": score,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "feedback": feedback,
            "evaluation": rubric_eval,
            "concept_name": question.concept.name if question.concept else "General",
            "concept_mastery_before": m_before,
            "concept_mastery_after": m_after
        }

    # --- Step 4: Generate Next Question Adaptively ---

    async def generate_next_question(self, quiz_id: UUID, user: User) -> tuple[Optional[Question], bool]:
        """
        Determines next question adaptively based on latest evidence.
        Returns (question, is_completed).
        """
        stmt = (
            select(Quiz)
            .options(selectinload(Quiz.questions), selectinload(Quiz.answers))
            .where(Quiz.id == quiz_id)
        )
        quiz = (await self.db.execute(stmt)).scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
        if quiz.user_id != user.id and getattr(user, "role", None) != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 1. Check if there's already an active unanswered question
        for q in sorted(quiz.questions, key=lambda x: x.question_order):
            if q.status == "PENDING":
                return q, False

        # 2. Check completion
        if quiz.completed_questions >= quiz.total_questions:
            return None, True

        project_stmt = select(Project).where(Project.id == quiz.project_id)
        project = (await self.db.execute(project_stmt)).scalar_one()

        # 3. Gather evidence from existing questions in this session
        existing_prompts = [q.prompt for q in quiz.questions]
        asked_concept_ids = [q.concept_id for q in quiz.questions if q.concept_id]

        # Fetch recent mistakes for prompt grounding
        stmt_mistakes = (
            select(QuizMistake.mistake_description)
            .where(QuizMistake.quiz_id == quiz.id)
            .order_by(desc(QuizMistake.created_at))
            .limit(3)
        )
        recent_mistakes = (await self.db.execute(stmt_mistakes)).scalars().all()

        # 4. Adaptive Selection of Concept & Difficulty
        target_concept, difficulty, _ = await self.adaptive_engine.select_target_concept_and_difficulty(
            project_id=project.id,
            user_id=user.id,
            quiz_id=quiz.id,
            recent_question_concept_ids=asked_concept_ids
        )

        # Vary format: alternate between MCQ and OPEN_ENDED
        next_order = quiz.completed_questions + 1
        # Alternate MCQ and Open-ended; Question 3 or later can be open-ended
        question_type = QuestionType.OPEN_ENDED if next_order % 2 == 0 else QuestionType.MCQ

        # Fetch target concept mastery
        m_score = 50.0
        if target_concept:
            m_stmt = select(ConceptMastery.mastery_score).where(
                ConceptMastery.project_id == project.id,
                ConceptMastery.concept_id == target_concept.id,
                ConceptMastery.user_id == user.id
            )
            m_val = (await self.db.execute(m_stmt)).scalar_one_or_none()
            if m_val is not None:
                m_score = m_val

        # 5. Generate Question
        q_data, chunk_ids = await self.question_generator.generate_question(
            project=project,
            concept=target_concept,
            difficulty=difficulty,
            question_type=question_type,
            current_mastery_score=m_score,
            recent_mistake_descriptions=recent_mistakes,
            existing_prompts=existing_prompts
        )

        next_q = Question(
            quiz_id=quiz.id,
            project_id=project.id,
            concept_id=target_concept.id if target_concept else None,
            question_type=q_data["question_type"],
            difficulty=q_data["difficulty"],
            question_order=next_order,
            prompt=q_data["prompt"],
            options=q_data.get("options", []),
            correct_answer=q_data["correct_answer"],
            explanation=q_data["explanation"],
            expected_concepts=q_data.get("expected_concepts", []),
            source_chunk_ids=chunk_ids,
            status="PENDING"
        )
        self.db.add(next_q)

        self._log_activity(
            user_id=user.id,
            project_id=project.id,
            event_type="QUESTION_GENERATED",
            payload={
                "quiz_id": str(quiz.id),
                "question_order": next_order,
                "concept": target_concept.name if target_concept else "General"
            }
        )

        await self.db.commit()
        await self.db.refresh(next_q)

        return next_q, False

    # --- Step 5: Complete Quiz & Generate Recommendations ---

    async def complete_quiz(self, quiz_id: UUID, user: User) -> dict[str, Any]:
        """
        Finalizes quiz, calculates aggregate statistics, identifies strengths & attention areas,
        updates Growth state, and generates actionable Recommendations.
        """
        stmt = (
            select(Quiz)
            .options(
                selectinload(Quiz.questions).selectinload(Question.concept),
                selectinload(Quiz.answers)
            )
            .where(Quiz.id == quiz_id)
        )
        quiz = (await self.db.execute(stmt)).scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
        if quiz.user_id != user.id and getattr(user, "role", None) != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 1. Calculate Results
        answers = quiz.answers
        total_attempted = len(answers)
        total_correct = sum(1 for a in answers if a.is_correct)
        avg_score = (sum(a.score for a in answers) / total_attempted) if total_attempted else 0.0
        final_percentage = round(avg_score * 100.0, 1)

        now = datetime.now(timezone.utc)
        quiz.status = QuizStatus.COMPLETED
        quiz.completed_at = now
        quiz.score_percentage = final_percentage
        quiz.overall_score = final_percentage

        # 2. Track concept performance in this quiz
        concept_scores: dict[UUID, list[float]] = {}
        concept_names: dict[UUID, str] = {}
        for a in answers:
            # Find question
            q = next((item for item in quiz.questions if item.id == a.question_id), None)
            if q and q.concept_id:
                if q.concept_id not in concept_scores:
                    concept_scores[q.concept_id] = []
                concept_scores[q.concept_id].append(a.score)
                if q.concept:
                    concept_names[q.concept_id] = q.concept.name

        # 3. Analyze Strengths vs Attention Areas
        strengths = []
        attention_areas = []
        for c_id, scores in concept_scores.items():
            name = concept_names.get(c_id, "Core Concept")
            c_avg = sum(scores) / len(scores)
            if c_avg >= 0.75:
                strengths.append(name)
            elif c_avg < 0.60:
                attention_areas.append(name)

        # 4. Fetch Mastery changes before vs after quiz
        mastery_changes = []
        for c_id in concept_scores.keys():
            m_stmt = select(ConceptMastery).where(
                ConceptMastery.project_id == quiz.project_id,
                ConceptMastery.concept_id == c_id,
                ConceptMastery.user_id == user.id
            )
            curr_mastery = (await self.db.execute(m_stmt)).scalar_one_or_none()
            if curr_mastery:
                # Find first history point for this quiz session
                hp_stmt = (
                    select(MasteryHistoryPoint.score_snapshot)
                    .where(
                        MasteryHistoryPoint.mastery_id == curr_mastery.id,
                        MasteryHistoryPoint.quiz_id == quiz.id
                    )
                    .order_by(MasteryHistoryPoint.recorded_at.asc())
                    .limit(1)
                )
                first_snap = (await self.db.execute(hp_stmt)).scalar_one_or_none()
                before_val = first_snap if first_snap is not None else curr_mastery.mastery_score
                after_val = curr_mastery.mastery_score

                mastery_changes.append({
                    "concept_id": c_id,
                    "concept_name": concept_names.get(c_id, "Concept"),
                    "before": round(before_val, 1),
                    "after": round(after_val, 1),
                    "delta": round(after_val - before_val, 1)
                })

        # 5. Generate Actionable Recommendation
        rec_id = None
        rec_title = None
        rec_text = None
        rec_action = RecommendationAction.REVIEW_MATERIAL

        if attention_areas:
            primary_weakness = attention_areas[0]
            rec_title = f"Review Foundational Notes on {primary_weakness}"
            rec_text = (
                f"Your performance on {primary_weakness} indicated misconceptions or missing key concepts. "
                f"Reviewing the uploaded materials and attempting targeted follow-up practice will solidify understanding."
            )
            rec_action = RecommendationAction.REVIEW_MATERIAL
        elif strengths:
            top_strength = strengths[0]
            rec_title = f"Advance to Applied Scenarios in {top_strength}"
            rec_text = (
                f"You demonstrated solid mastery ({final_percentage}%) on {top_strength}. "
                f"Continue challenging yourself with advanced case studies or ask the Tutor open-ended exploratory questions."
            )
            rec_action = RecommendationAction.TAKE_QUIZ
        else:
            rec_title = "Continue Comprehensive Learning Loop"
            rec_text = "Practice questions regularly to reinforce long-term memory and bridge conceptual gaps."
            rec_action = RecommendationAction.TAKE_QUIZ

        # Persist Recommendation
        rec = Recommendation(
            project_id=quiz.project_id,
            user_id=user.id,
            concept_id=list(concept_scores.keys())[0] if concept_scores else None,
            title=rec_title,
            reasoning=rec_text,
            action_type=rec_action,
            target_payload={"quiz_id": str(quiz.id), "suggested_action": rec_title},
            status=RecommendationStatus.PENDING,
            created_at=now
        )
        self.db.add(rec)
        await self.db.flush()
        rec_id = rec.id

        # Observability: Record Recommendation Telemetry
        await ai_service.log_usage(
            db=self.db,
            feature="RECOMMENDATION",
            operation="generate_recommendation",
            latency_ms=15,
            input_tokens=len(str(concept_scores)) // 4,
            output_tokens=len(rec_text or "") // 4,
            total_tokens=(len(str(concept_scores)) + len(rec_text or "")) // 4,
            status_code="SUCCESS",
            user_id=user.id,
            project_id=quiz.project_id,
            metadata_json={"recommendation_id": str(rec_id), "action_type": rec_action.value}
        )

        # 6. Activity Events
        self._log_activity(
            user_id=user.id,
            project_id=quiz.project_id,
            event_type="QUIZ_COMPLETED",
            payload={
                "quiz_id": str(quiz.id),
                "score": final_percentage,
                "questions_attempted": total_attempted,
                "questions_correct": total_correct
            }
        )
        for mc in mastery_changes:
            self._log_activity(
                user_id=user.id,
                project_id=quiz.project_id,
                event_type="MASTERY_UPDATED",
                payload={
                    "concept_name": mc["concept_name"],
                    "before": mc["before"],
                    "after": mc["after"],
                    "delta": mc["delta"]
                }
            )
        self._log_activity(
            user_id=user.id,
            project_id=quiz.project_id,
            event_type="RECOMMENDATION_GENERATED",
            payload={"quiz_id": str(quiz.id), "recommendation_id": str(rec_id), "title": rec_title}
        )

        await self.db.commit()

        return {
            "quiz_id": quiz.id,
            "project_id": quiz.project_id,
            "status": quiz.status,
            "score": final_percentage,
            "questions_attempted": total_attempted,
            "questions_correct": total_correct,
            "concepts_assessed": len(concept_scores),
            "strengths": strengths,
            "attention_areas": attention_areas,
            "mastery_changes": mastery_changes,
            "recommendation": rec_text,
            "recommendation_action": rec_action.value,
            "recommendation_id": rec_id
        }

    # --- Backwards Compatibility Helpers ---

    async def generate_quiz_for_project(self, project: Project, user: User) -> Quiz:
        """Legacy helper for single-batch 3-question generation."""
        quiz, _ = await self.start_quiz(project=project, user=user, question_count=3)
        # Eagerly generate 2 more questions to satisfy legacy expectations
        await self.generate_next_question(quiz.id, user)
        await self.generate_next_question(quiz.id, user)

        stmt = select(Quiz).options(selectinload(Quiz.questions)).where(Quiz.id == quiz.id)
        return (await self.db.execute(stmt)).scalar_one()

    async def evaluate_submission(
        self,
        quiz_id: UUID,
        payload: QuizSubmitPayload,
        project: Project,
        user: User,
        background_tasks: Any = None
    ) -> dict[str, Any]:
        """Legacy batch submission handler."""
        for item in payload.answers:
            await self.submit_question_answer(
                quiz_id=quiz_id,
                question_id=item.question_id,
                user=user,
                user_answer=item.user_answer
            )

        results = await self.complete_quiz(quiz_id, user)
        # Format matching legacy QuestionResultOut
        stmt_answers = (
            select(QuestionAnswer)
            .options(selectinload(QuestionAnswer.question))
            .where(QuestionAnswer.quiz_id == quiz_id)
        )
        answers = (await self.db.execute(stmt_answers)).scalars().all()
        results_list = []
        for a in answers:
            q = a.question
            results_list.append({
                "id": q.id,
                "prompt": q.prompt,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "user_answer": a.user_answer,
                "is_correct": a.is_correct,
                "score": a.score,
                "rubric_feedback": a.rubric_feedback or a.evaluation
            })

        return {
            "id": quiz_id,
            "project_id": project.id,
            "status": QuizStatus.COMPLETED,
            "score_percentage": results["score"],
            "completed_at": datetime.now(timezone.utc),
            "results": results_list
        }

    def _log_activity(self, user_id: UUID, project_id: UUID, event_type: str, payload: dict[str, Any]):
        evt = ActivityEvent(
            user_id=user_id,
            project_id=project_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(evt)
