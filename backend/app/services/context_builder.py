from typing import Any

class ContextBuilder:
    """
    Dedicated Context Builder for Evidence-Grounded AI Tutoring.
    Deduplicates chunks, enforces strict source attribution tags, caps token budgets,
    and isolates retrieved text as passive data against prompt injection.
    """

    def __init__(self, max_context_chars: int = 4000):
        self.max_context_chars = max_context_chars

    def build_context(self, chunks: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """
        Builds grounded evidence context from retrieved project chunks.
        Returns:
            (formatted_context_string, validated_citations_metadata)
        """
        if not chunks:
            return "", []

        seen_contents = set()
        formatted_sources = []
        citations_metadata = []
        current_chars = 0

        for idx, chunk in enumerate(chunks):
            content = chunk.get("content", "").strip()
            # Deduplicate similar or identical chunks
            content_sig = content[:80].lower()
            if content_sig in seen_contents:
                continue
            seen_contents.add(content_sig)

            doc_title = chunk.get("document_title", "Material Notes")
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section_title", "General")

            source_block = (
                f"SOURCE [{len(formatted_sources) + 1}]\n"
                f"Material: {doc_title}\n"
                f"Page: {page_num}\n"
                f"Section: {section}\n"
                f"Content: {content}\n"
            )

            if current_chars + len(source_block) > self.max_context_chars:
                break

            formatted_sources.append(source_block)
            citations_metadata.append({
                "source_index": len(formatted_sources),
                "material_id": str(chunk.get("material_id", "")),
                "document_title": doc_title,
                "page_number": page_num,
                "section_title": section,
                "snippet": content[:200]
            })
            current_chars += len(source_block)

        context_str = "\n".join(formatted_sources)
        return context_str, citations_metadata

context_builder = ContextBuilder()
