import re
import fitz  # PyMuPDF
from typing import Any

class PDFService:
    """
    PyMuPDF Extraction Service.
    Extracts text page-by-page, normalizes text formatting, detects scanned pages,
    and strictly retains source page numbering.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # Fix hyphenated line breaks (e.g. "con-\nvergence" -> "convergence")
        cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        # Normalize multiple newlines and irregular spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        # Remove non-printable control characters
        cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch in ('\n', '\t'))
        return cleaned.strip()

    def extract_document_pages(self, file_path: str) -> dict[str, Any]:
        """
        Extracts pages from a PDF document.
        Returns:
            {
                "total_pages": int,
                "total_characters": int,
                "pages": [
                    {
                        "page_number": int, # 1-indexed
                        "text": str,
                        "is_scanned": bool,
                        "char_count": int
                    }
                ]
            }
        """
        doc = fitz.open(file_path)
        total_pages = len(doc)
        extracted_pages = []
        total_chars = 0

        for page_idx in range(total_pages):
            page_num = page_idx + 1  # 1-indexed
            page = doc.load_page(page_idx)
            raw_text = page.get_text() or ""
            cleaned = self.clean_text(raw_text)

            is_scanned = len(cleaned) < 50
            if is_scanned:
                # Scanned fallback flag (can integrate pytesseract if installed)
                cleaned = f"[Scanned Page {page_num} Excerpt: Content detected visually]"

            char_count = len(cleaned)
            total_chars += char_count

            extracted_pages.append({
                "page_number": page_num,
                "text": cleaned,
                "is_scanned": is_scanned,
                "char_count": char_count
            })

        doc.close()

        return {
            "total_pages": total_pages,
            "total_characters": total_chars,
            "pages": extracted_pages
        }

pdf_service = PDFService()
