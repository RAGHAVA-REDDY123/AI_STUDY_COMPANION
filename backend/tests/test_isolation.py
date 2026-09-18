import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.retrieval_service import RetrievalService
from app.services.citation_service import citation_service
from app.services.tutor_service import TutorService
from app.models.project import Project
from app.models.user import User

@pytest.mark.asyncio
async def test_project_a_retrieves_only_project_a_chunks():
    """Test 1: Project A query retrieves Project A chunks."""
    project_a_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = [
        {
            "id": uuid.uuid4(),
            "material_id": uuid.uuid4(),
            "page_number": 14,
            "chunk_index": 0,
            "section_title": "Gradient Descent",
            "document_title": "ML_Notes.pdf",
            "content": "Gradient descent minimizes the empirical loss objective iteratively.",
            "vector_similarity": 0.88,
            "fts_rank": 0.5
        }
    ]
    mock_exec_result = MagicMock()
    mock_exec_result.mappings.return_value = mock_mappings
    mock_db.execute.return_value = mock_exec_result

    retrieval_svc = RetrievalService(mock_db)
    chunks, has_evidence = await retrieval_svc.retrieve(
        project_id=project_a_id,
        query="Explain gradient descent"
    )

    assert has_evidence is True
    assert len(chunks) == 1
    assert chunks[0]["document_title"] == "ML_Notes.pdf"
    assert chunks[0]["page_number"] == 14

    # Verify project_id was passed to SQL query parameters
    call_args = mock_db.execute.call_args_list[0]
    sql_params = call_args[0][1]
    assert sql_params["project_id"] == str(project_a_id)

@pytest.mark.asyncio
async def test_project_a_never_leaks_project_b_chunks():
    """Test 2: Project B contains a semantically better matching chunk. Project A query must NOT retrieve it."""
    project_a_id = uuid.uuid4()
    project_b_id = uuid.uuid4()

    mock_db = AsyncMock()
    
    # Simulate DB returning empty because Project A has no matching chunks,
    # even though Project B would match if queried.
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = []
    mock_exec_result = MagicMock()
    mock_exec_result.mappings.return_value = mock_mappings
    mock_db.execute.return_value = mock_exec_result

    retrieval_svc = RetrievalService(mock_db)
    chunks, has_evidence = await retrieval_svc.retrieve(
        project_id=project_a_id,
        query="Explain OS Kernel Page Tables"
    )

    # In Project A, evidence must be False
    assert has_evidence is False
    assert len(chunks) == 0

    # Ensure SQL strictly enforced Project A
    call_args = mock_db.execute.call_args_list[0]
    sql_params = call_args[0][1]
    assert sql_params["project_id"] == str(project_a_id)
    assert sql_params["project_id"] != str(project_b_id)

@pytest.mark.asyncio
async def test_unauthorized_user_access_guard():
    """Test 3: Unauthorized user attempting Project A retrieval receives authorization failure."""
    from app.api.deps import verify_project_access
    from fastapi import HTTPException

    user_a = User(id=uuid.uuid4(), email="user_a@test.com")
    user_b = User(id=uuid.uuid4(), email="user_b@test.com")
    project_a = Project(id=uuid.uuid4(), user_id=user_a.id, name="Project A")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    # User B queries Project A in DB -> not found for user B
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await verify_project_access(
            project_id=project_a.id,
            current_user=user_b,
            db=mock_db
        )
    assert exc_info.value.status_code == 404

def test_project_a_citation_cannot_point_to_project_b_material():
    """Test 5: Project A citation cannot point to Project B material."""
    project_a_metadata = [
        {"document_title": "Machine_Learning.pdf", "page_number": 10, "snippet": "Neural net layers"}
    ]
    
    # LLM hallucinates or cites material from Project B
    llm_output = "Operating systems manage processes [Source: OS_Notes.pdf — Page 42]."
    
    verified = citation_service.validate_citations(llm_output, project_a_metadata)
    
    # OS_Notes.pdf from Project B must be rejected because it is not in Project A's retrieved metadata
    assert not any(c["document_title"] == "OS_Notes.pdf" for c in verified)

@pytest.mark.asyncio
async def test_unsupported_question_in_project_a_triggers_calibrated_refusal():
    """Test 6: Question whose answer exists only in Project B produces insufficient-evidence refusal when asked in Project A."""
    project_a = Project(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Project A", learning_goal="Learn ML")
    user_a = User(id=project_a.user_id, email="student@test.com")

    mock_db = AsyncMock()
    # Return zero chunks in Project A
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = []
    mock_exec_result = MagicMock()
    mock_exec_result.mappings.return_value = mock_mappings
    mock_db.execute.return_value = mock_exec_result

    tutor_svc = TutorService(mock_db)
    
    events = []
    async for event in tutor_svc.generate_grounded_response_stream(
        project=project_a,
        user=user_a,
        query="How does Linux virtual memory management work?"
    ):
        events.append(event)

    full_output = "".join(events)
    # Must trigger calibrated refusal
    assert "couldn't find enough information" in full_output or "cannot find sufficient evidence" in full_output
    assert "Linux virtual memory" in full_output
