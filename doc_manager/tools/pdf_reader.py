import shutil
import subprocess
import tempfile
from typing import Optional

import pdfplumber


def _extract_with_pdfplumber(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages.append(text.strip())
        return "\n\n---PAGE BREAK---\n\n".join(pages)


def extract_text(pdf_path: str) -> tuple[str, bool, Optional[str]]:
    """Extract text from a PDF. Returns (text, is_readable, error_message).

    Falls back to ocrmypdf for image-only PDFs when no embedded text is found.
    Requires ocrmypdf installed on the system (brew install ocrmypdf).
    """
    try:
        full_text = _extract_with_pdfplumber(pdf_path)
        if full_text.strip():
            return (full_text, True, None)

        # No embedded text — attempt OCR fallback
        if not shutil.which("ocrmypdf"):
            return ("", False, "no_text_extracted; ocrmypdf not installed")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            ocr_path = tmp.name

        result = subprocess.run(
            [
                "ocrmypdf",
                "--language", "deu+eng",
                "--deskew",
                "--clean",
                "--oversample", "400",
                "--tesseract-pagesegmode", "6",
                "--tesseract-oem", "1",
                "--output-type", "pdf",
                "--quiet",
                pdf_path,
                ocr_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode not in (0, 6):  # 6 = already has text layer, treat as ok
            return ("", False, f"ocrmypdf error (code {result.returncode}): {result.stderr.strip()}")

        full_text = _extract_with_pdfplumber(ocr_path)
        if not full_text.strip():
            return ("", False, "no_text_extracted after OCR")

        return (full_text, True, None)

    except subprocess.TimeoutExpired:
        return ("", False, "ocrmypdf timed out after 120s")
    except Exception as e:
        return ("", False, str(e))
