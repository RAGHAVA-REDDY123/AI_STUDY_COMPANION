import pytest
from app.services.citation_service import citation_service

def test_extract_citations_from_text():
    sample_text = (
        "Relational databases use B-trees for indexing [Source: Database Systems — Page 42]. "
        "Transactions maintain ACID properties [Source: Advanced DBMS — Page 108]."
    )
    citations = citation_service.extract_citations_from_text(sample_text)
    assert len(citations) == 2
    assert citations[0]["document_title"] == "Database Systems"
    assert citations[0]["page_number"] == 42
    assert citations[1]["document_title"] == "Advanced DBMS"
    assert citations[1]["page_number"] == 108


def test_validate_citations_matches_retrieved_evidence():
    sample_text = (
        "Query optimization determines the most efficient execution plan "
        "[Source: Database Systems — Page 42]."
    )
    retrieved_metadata = [
        {"document_title": "Database Systems", "page_number": 42, "snippet": "Query optimization plan."},
        {"document_title": "Database Systems", "page_number": 43, "snippet": "Execution trees."}
    ]

    verified = citation_service.validate_citations(sample_text, retrieved_metadata)
    assert len(verified) == 1
    assert verified[0]["document_title"] == "Database Systems"
    assert verified[0]["page_number"] == 42
    assert verified[0]["is_verified"] is True
    assert verified[0]["snippet"] == "Query optimization plan."


def test_validate_citations_rejects_hallucinated_page():
    # LLM hallucinates Page 99 which was NOT in retrieved metadata
    sample_text = (
        "Indexing can speed up queries dramatically [Source: Database Systems — Page 99]."
    )
    retrieved_metadata = [
        {"document_title": "Database Systems", "page_number": 12, "snippet": "Indexing basics."}
    ]

    verified = citation_service.validate_citations(sample_text, retrieved_metadata)
    # The hallucinated page 99 is rejected; fallback picks the actual retrieved primary source
    assert len(verified) == 1
    assert verified[0]["page_number"] == 12
    assert verified[0]["document_title"] == "Database Systems"


def test_validate_citations_rejects_fabricated_document_title():
    # LLM cites a document that does NOT exist in the retrieved evidence
    sample_text = (
        "Quantum computing replaces bits with qubits [Source: Quantum Physics — Page 5]."
    )
    retrieved_metadata = [
        {"document_title": "Database Systems", "page_number": 1, "snippet": "Introduction to Databases."}
    ]

    verified = citation_service.validate_citations(sample_text, retrieved_metadata)
    # Quantum Physics is rejected; fallback links to the project's actual retrieved source
    assert len(verified) == 1
    assert verified[0]["document_title"] == "Database Systems"
    assert verified[0]["page_number"] == 1


def test_validate_citations_fallback_when_tags_omitted():
    # When the LLM answers factually without explicit bracket citations
    sample_text = "Normalization eliminates data redundancy and prevents update anomalies."
    retrieved_metadata = [
        {"document_title": "Database Normalization", "page_number": 5, "snippet": "1NF, 2NF, 3NF"}
    ]

    verified = citation_service.validate_citations(sample_text, retrieved_metadata)
    assert len(verified) == 1
    assert verified[0]["document_title"] == "Database Normalization"
    assert verified[0]["page_number"] == 5
    assert verified[0]["is_verified"] is True
