import pytest
from app.schemas.cheat_sheet import (
    CheatSheetResponse,
    ExamTrapItem,
    CoreFormulaItem,
    HighYieldConceptItem,
    RapidFireQAItem,
    CrammingChecklistItem,
)

def test_cheat_sheet_schema_validation():
    trap = ExamTrapItem(
        misconception_title="L1 vs L2 Confusion",
        what_student_missed="Confused weight shrinkage with sparsity penalty",
        exam_trap_warning="Questions often ask which regularizer performs feature selection",
        correct_mental_model="L1 drives weights to exactly 0 (sparsity); L2 shrinks weights asymptotically",
        source_page=14,
        concept_name="Regularization"
    )
    formula = CoreFormulaItem(
        name="Weight Update Equation",
        formula_or_rule="w := w - η * ∇L(w)",
        plain_explanation="Weights step in direction opposite to loss gradient scaled by learning rate η",
        source_citation="Source: ML Notes — Page 14",
        page_number=14
    )
    concept = HighYieldConceptItem(
        concept_name="Gradient Descent",
        mastery_score=85,
        trend_state="IMPROVING",
        importance_score=0.95,
        key_takeaway="First-order optimization algorithm for finding loss function minima",
        page_number=14
    )
    qa = RapidFireQAItem(
        question="What does learning rate control?",
        quick_answer="The step size taken in the direction of the negative gradient",
        key_term="Learning Rate"
    )
    chk = CrammingChecklistItem(
        id="c1",
        task="Review Gradient Descent derivation",
        is_critical=True,
        estimated_mins=5,
        concept_name="Gradient Descent"
    )

    sheet = CheatSheetResponse(
        project_id="00000000-0000-0000-0000-000000000001",
        project_name="Machine Learning Foundations",
        learning_goal="Master optimization",
        exam_readiness_score=82,
        generated_at="Sep 18, 2026 • 16:00 UTC",
        total_concepts_covered=1,
        critical_traps_count=1,
        personalized_traps=[trap],
        core_formulas=[formula],
        high_yield_concepts=[concept],
        rapid_fire_qa=[qa],
        cramming_checklist=[chk]
    )

    assert sheet.exam_readiness_score == 82
    assert len(sheet.personalized_traps) == 1
    assert sheet.personalized_traps[0].source_page == 14
    assert sheet.core_formulas[0].page_number == 14
    assert sheet.rapid_fire_qa[0].key_term == "Learning Rate"
