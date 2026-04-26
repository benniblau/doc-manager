from typing import Optional
import pdfplumber


def extract_text(pdf_path: str) -> tuple[str, bool, Optional[str]]:
    """Extract text from a PDF. Returns (text, is_readable, error_message)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    pages.append(text.strip())
            full_text = "\n\n---PAGE BREAK---\n\n".join(pages)
            if not full_text.strip():
                return ("", False, "no_text_extracted")
            return (full_text, True, None)
    except Exception as e:
        return ("", False, str(e))
