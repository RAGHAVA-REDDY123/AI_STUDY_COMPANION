import hashlib
import re
from typing import Any
from uuid import UUID
from app.core.config import settings

class ChunkingService:
    """
    Semantic Chunking Service with configurable safety limits and metadata preservation.
    Chunks documents based on paragraph and section boundaries while ensuring
    every chunk belongs to exactly one Project and retains its 1-indexed page number.
    """

    def __init__(self):
        self.target_size = settings.CHUNK_TARGET_SIZE
        self.min_size = settings.CHUNK_MIN_SIZE
        self.max_size = settings.CHUNK_MAX_SIZE
        self.overlap = settings.CHUNK_OVERLAP

    def _extract_section_title(self, paragraph: str) -> str:
        """Extracts potential heading from the beginning of a paragraph."""
        first_line = paragraph.strip().split("\n")[0].strip()
        if len(first_line) < 60 and (first_line.isupper() or first_line.endswith(":") or first_line.startswith("#")):
            return re.sub(r'^[#*\-:\s]+', '', first_line).strip()
        return "General Content"

    def chunk_document_pages(
        self,
        project_id: UUID,
        material_id: UUID,
        user_id: UUID,
        document_title: str,
        pages_data: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Segments page text into semantic units with strict boundaries and metadata.
        Returns:
            (chunk_dicts, statistics_dict)
        """
        chunks: list[dict[str, Any]] = []
        chunk_idx = 0
        total_characters = 0

        for page_info in pages_data:
            page_num = page_info["page_number"]
            page_text = page_info["text"]

            if not page_text.strip():
                continue

            # Split by double newlines into paragraphs
            raw_paragraphs = page_text.split("\n\n")
            current_chunk_text = ""
            current_section = "Introduction"

            for para in raw_paragraphs:
                para = para.strip()
                if not para:
                    continue

                section_candidate = self._extract_section_title(para)
                if section_candidate != "General Content":
                    current_section = section_candidate

                # If adding this paragraph exceeds target and we meet min size, save chunk
                if len(current_chunk_text) + len(para) > self.target_size and len(current_chunk_text) >= self.min_size:
                    chunk_content = current_chunk_text.strip()
                    c_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()
                    chunks.append({
                        "project_id": project_id,
                        "material_id": material_id,
                        "user_id": user_id,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "document_title": document_title,
                        "section_title": current_section,
                        "content": chunk_content,
                        "content_hash": c_hash,
                        "token_count": max(1, len(chunk_content) // 4)
                    })
                    total_characters += len(chunk_content)
                    chunk_idx += 1

                    # Keep overlap from the end of current chunk
                    if self.overlap > 0 and len(chunk_content) > self.overlap:
                        current_chunk_text = chunk_content[-self.overlap:] + " " + para
                    else:
                        current_chunk_text = para
                else:
                    if current_chunk_text:
                        current_chunk_text += "\n\n" + para
                    else:
                        current_chunk_text = para

                # Hard upper safety bound: if chunk exceeds max_size, force flush
                while len(current_chunk_text) >= self.max_size:
                    split_idx = current_chunk_text[:self.max_size].rfind(" ")
                    if split_idx <= self.min_size:
                        split_idx = self.max_size

                    chunk_content = current_chunk_text[:split_idx].strip()
                    c_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()
                    chunks.append({
                        "project_id": project_id,
                        "material_id": material_id,
                        "user_id": user_id,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "document_title": document_title,
                        "section_title": current_section,
                        "content": chunk_content,
                        "content_hash": c_hash,
                        "token_count": max(1, len(chunk_content) // 4)
                    })
                    total_characters += len(chunk_content)
                    chunk_idx += 1
                    current_chunk_text = current_chunk_text[split_idx:].strip()

            # Flush any remaining text on the page
            if current_chunk_text.strip() and len(current_chunk_text.strip()) >= self.min_size:
                chunk_content = current_chunk_text.strip()
                c_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()
                chunks.append({
                    "project_id": project_id,
                    "material_id": material_id,
                    "user_id": user_id,
                    "page_number": page_num,
                    "chunk_index": chunk_idx,
                    "document_title": document_title,
                    "section_title": current_section,
                    "content": chunk_content,
                    "content_hash": c_hash,
                    "token_count": max(1, len(chunk_content) // 4)
                })
                total_characters += len(chunk_content)
                chunk_idx += 1

        # Calculate statistics
        chunk_sizes = [len(c["content"]) for c in chunks] if chunks else [0]
        stats = {
            "page_count": len(pages_data),
            "chunk_count": len(chunks),
            "total_character_count": total_characters,
            "average_chunk_size": round(sum(chunk_sizes) / len(chunk_sizes), 1) if chunks else 0,
            "max_chunk_size": max(chunk_sizes) if chunks else 0
        }

        return chunks, stats

chunking_service = ChunkingService()
