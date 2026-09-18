import uuid
import pytest
from app.services.chunking_service import chunking_service
from app.models.material import Material, MaterialStatus, ProcessingStage

def test_semantic_chunking_bounds_and_page_retention():
    """Verify semantic chunker enforces bounds and strictly preserves 1-indexed page numbers."""
    project_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    pages = [
        {
            "page_number": 1,
            "text": (
                "Introduction to Neural Networks.\n\n"
                "Artificial neural networks are computational models inspired by biological neural systems. "
                "They consist of interconnected layers of artificial neurons that process input signals and pass activations forward. "
                "The fundamental goal is to approximate non-linear functions mapped from feature spaces to target outputs.\n\n"
                "Training involves optimizing weight parameters using backpropagation and gradient-based algorithms."
            )
        },
        {
            "page_number": 2,
            "text": (
                "Optimization Strategies.\n\n"
                "Stochastic gradient descent calculates gradients on mini-batches of data, providing computational efficiency "
                "and noise that helps escape saddle points in non-convex loss surfaces.\n\n"
                "Adaptive optimizers such as Adam scale step sizes individually for each parameter based on first and second moments."
            )
        }
    ]

    chunks, stats = chunking_service.chunk_document_pages(
        project_id=project_id,
        material_id=material_id,
        user_id=user_id,
        document_title="ML_Textbook.pdf",
        pages_data=pages
    )

    assert len(chunks) >= 2
    assert stats["chunk_count"] == len(chunks)
    assert stats["page_count"] == 2

    # Check page numbers
    page_numbers = {c["page_number"] for c in chunks}
    assert 1 in page_numbers
    assert 2 in page_numbers

    for c in chunks:
        # Check project isolation metadata
        assert c["project_id"] == project_id
        assert c["material_id"] == material_id
        assert c["document_title"] == "ML_Textbook.pdf"
        assert len(c["content"]) >= chunking_service.min_size
        assert len(c["content"]) <= chunking_service.max_size + 100
        assert len(c["content_hash"]) == 64

def test_material_stage_progression_representation():
    """Verify Material model supports explicit stage progression lifecycle."""
    mat = Material(
        project_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        filename="Test_Doc.pdf",
        file_path="/storage/test.pdf",
        file_hash="abc123hash",
        file_size_bytes=2048,
        status=MaterialStatus.QUEUED,
        current_stage=ProcessingStage.QUEUED
    )

    assert mat.status == MaterialStatus.QUEUED
    assert mat.current_stage == ProcessingStage.QUEUED

    # Transition through stages
    stages = [
        ProcessingStage.EXTRACTING,
        ProcessingStage.CHUNKING,
        ProcessingStage.EMBEDDING,
        ProcessingStage.INDEXING,
        ProcessingStage.READY
    ]
    for stage in stages:
        mat.current_stage = stage
        assert mat.current_stage == stage

    mat.status = MaterialStatus.READY
    assert mat.status == MaterialStatus.READY
