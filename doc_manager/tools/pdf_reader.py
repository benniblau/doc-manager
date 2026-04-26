import base64
import io
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


_VISION_PROMPT = (
    "Transcribe all text visible in this document image. "
    "Output only the text content, preserving the layout as closely as possible. "
    "Do not add explanations or comments."
)


def _extract_with_vision(pdf_path: str) -> str:
    """Convert each PDF page to an image and send to a vision LLM via Ollama's native API.

    Uses Ollama's /api/chat endpoint (not the OpenAI-compat layer) because GGUF vision
    models require the native `images` field for proper tokenisation.

    Requires pdf2image (pip install pdf2image) and poppler (brew/apt install poppler-utils).
    """
    import requests
    from pdf2image import convert_from_path
    from doc_manager.config import settings

    # Derive the Ollama base URL (strip /v1 suffix if present)
    base = settings.VISION_MODEL_URL.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    chat_url = f"{base}/api/chat"

    images = convert_from_path(pdf_path, dpi=72, last_page=settings.VISION_MAX_PAGES)
    pages = []

    for image in images:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        payload = {
            "model": settings.VISION_MODEL_NAME,
            "messages": [{
                "role": "user",
                "content": _VISION_PROMPT,
                "images": [b64],
            }],
            "stream": False,
            "options": {"num_predict": 2048, "num_ctx": settings.VISION_NUM_CTX},
        }
        resp = requests.post(chat_url, json=payload, timeout=settings.VISION_REQUEST_TIMEOUT)
        resp.raise_for_status()
        text = (resp.json().get("message", {}).get("content") or "").strip()
        if text:
            pages.append(text)

    return "\n\n---PAGE BREAK---\n\n".join(pages)


def extract_text(pdf_path: str) -> tuple[str, bool, Optional[str]]:
    """Extract text from a PDF. Returns (text, is_readable, error_message).

    Extraction chain (each step only runs if the previous yielded no text):
      1. pdfplumber       — embedded text layer
      2. ocrmypdf         — Tesseract OCR with deskew/clean (requires ocrmypdf system package)
      3. vision LLM       — page images sent to a multimodal model (requires VISION_MODEL_URL in .env)
    """
    try:
        # 1. Embedded text
        full_text = _extract_with_pdfplumber(pdf_path)
        if full_text.strip():
            return (full_text, True, None)

        # 2. Tesseract via ocrmypdf
        ocr_error = None
        if shutil.which("ocrmypdf"):
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

            if result.returncode in (0, 6):
                full_text = _extract_with_pdfplumber(ocr_path)
                if full_text.strip():
                    return (full_text, True, None)
                ocr_error = "no_text_extracted after OCR"
            else:
                ocr_error = f"ocrmypdf error (code {result.returncode}): {result.stderr.strip()}"
        else:
            ocr_error = "ocrmypdf not installed"

        # 3. Vision LLM fallback
        from doc_manager.config import settings
        if settings.VISION_MODEL_URL:
            try:
                full_text = _extract_with_vision(pdf_path)
                if full_text.strip():
                    return (full_text, True, None)
                return ("", False, "no_text_extracted after vision OCR")
            except Exception as e:
                return ("", False, f"vision OCR failed: {e}")

        return ("", False, ocr_error or "no_text_extracted")

    except subprocess.TimeoutExpired:
        return ("", False, "ocrmypdf timed out after 120s")
    except Exception as e:
        return ("", False, str(e))
