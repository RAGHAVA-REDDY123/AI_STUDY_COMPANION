from typing import List, Optional
from pydantic import BaseModel, Field

class ExamTrapItem(BaseModel):
    misconception_title: str = Field(..., description="Short title of the misconception or error trap")
    what_student_missed: str = Field(..., description="Specific mistake or faulty reasoning recorded from student history")
    exam_trap_warning: str = Field(..., description="High-priority warning on how this concept is typically tested on exams")
    correct_mental_model: str = Field(..., description="The definitive, correct conceptual rule to apply")
    source_page: Optional[int] = Field(None, description="Page number in uploaded notes where this is explained")
    concept_name: Optional[str] = Field(None, description="Related concept name")

class CoreFormulaItem(BaseModel):
    name: str = Field(..., description="Name of the formula, law, algorithm, or mathematical principle")
    formula_or_rule: str = Field(..., description="Mathematical notation or formal rule representation")
    plain_explanation: str = Field(..., description="Plain-English intuition and variable breakdown")
    source_citation: str = Field(..., description="Citation string (e.g. Source: Notes.pdf — Page 14)")
    page_number: Optional[int] = Field(None, description="Cited page number")
    material_id: Optional[str] = Field(None, description="Material UUID for PDF jumping")

class HighYieldConceptItem(BaseModel):
    concept_name: str = Field(..., description="Name of the concept")
    mastery_score: float = Field(..., description="Current mastery percentage (0-100)")
    trend_state: str = Field(..., description="IMPROVING, STABLE, or REQUIRING_ATTENTION")
    importance_score: float = Field(..., description="Pedagogical importance score (0.0 to 1.0)")
    key_takeaway: str = Field(..., description="1-sentence dense exam takeaway")
    page_number: Optional[int] = Field(None, description="Primary supporting page number")

class RapidFireQAItem(BaseModel):
    question: str = Field(..., description="Concise active-recall exam question")
    quick_answer: str = Field(..., description="Punchy, authoritative 1-sentence answer")
    key_term: str = Field(..., description="Core technical term or keyword")

class CrammingChecklistItem(BaseModel):
    id: str = Field(..., description="Unique item ID")
    task: str = Field(..., description="Actionable revision checkpoint")
    is_critical: bool = Field(False, description="True if addressing a diagnosed weak concept")
    estimated_mins: int = Field(5, description="Estimated minutes required")
    concept_name: Optional[str] = Field(None, description="Associated concept")

class CheatSheetResponse(BaseModel):
    project_id: str
    project_name: str
    learning_goal: str
    exam_readiness_score: int = Field(..., description="Overall exam readiness score from 0 to 100")
    generated_at: str
    total_concepts_covered: int
    critical_traps_count: int
    personalized_traps: List[ExamTrapItem] = []
    core_formulas: List[CoreFormulaItem] = []
    high_yield_concepts: List[HighYieldConceptItem] = []
    rapid_fire_qa: List[RapidFireQAItem] = []
    cramming_checklist: List[CrammingChecklistItem] = []
