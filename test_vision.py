"""Focused vision model test: connectivity + OCR on the scanned PDF."""
import base64, io, os, requests
os.environ.setdefault("MODEL_URL", "http://10.10.1.180:8888/")

from dotenv import load_dotenv
load_dotenv()

from doc_manager.config import settings
from pdf2image import convert_from_path

SCANNED_PDF = "example-docs/5. AZ Aufmaß_Korrektur_1.pdf"

print(f"Vision model : {settings.VISION_MODEL_NAME}")
print(f"Ollama URL   : {settings.VISION_MODEL_URL}")
print(f"Timeout      : {settings.VISION_REQUEST_TIMEOUT}s\n")

base = settings.VISION_MODEL_URL.rstrip("/").rstrip("/v1").rstrip("/")

# 1. Model info
print("── Model info (/api/show) ────────────────────")
try:
    r = requests.post(f"{base}/api/show", json={"name": settings.VISION_MODEL_NAME}, timeout=10)
    info = r.json()
    details = info.get("details", {})
    print(f"  Family   : {details.get('family', '?')}")
    print(f"  Format   : {details.get('format', '?')}")
    print(f"  Params   : {details.get('parameter_size', '?')}")
    # Check if model has vision/mmproj capability
    model_info = info.get("model_info", {})
    has_vision = any("vision" in k or "clip" in k or "mmproj" in k for k in model_info.keys())
    projector = info.get("projector_info", {})
    print(f"  Has vision keys : {has_vision}")
    print(f"  Projector info  : {projector or 'none'}")
except Exception as e:
    print(f"  Failed: {e}")

# 2. Text-only call to confirm the model works at all
print("\n── Text-only call ───────────────────────────")
try:
    r = requests.post(f"{base}/api/chat", json={
        "model": settings.VISION_MODEL_NAME,
        "messages": [{"role": "user", "content": "Reply with just the word OK."}],
        "stream": False,
        "options": {"num_predict": 5},
    }, timeout=60)
    r.raise_for_status()
    reply = r.json().get("message", {}).get("content", "?")
    print(f"  ✓ Model responds to text: {reply!r}")
except Exception as e:
    print(f"  ✗ Text call failed: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"    Body: {e.response.text[:300]}")

# 3. Vision call with small test image (1x1 white pixel)
print("\n── Minimal vision call (1×1 pixel) ──────────")
try:
    from PIL import Image
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    tiny_b64 = base64.b64encode(buf.getvalue()).decode()

    r = requests.post(f"{base}/api/chat", json={
        "model": settings.VISION_MODEL_NAME,
        "messages": [{"role": "user", "content": "What colour is this image?", "images": [tiny_b64]}],
        "stream": False,
        "options": {"num_predict": 20},
    }, timeout=120)
    print(f"  Status: {r.status_code}")
    if r.ok:
        reply = r.json().get("message", {}).get("content", "?")
        print(f"  ✓ Vision works: {reply!r}")
    else:
        print(f"  ✗ Error body: {r.text[:400]}")
except Exception as e:
    print(f"  ✗ Vision call failed: {e}")

# 4. Vision OCR — page 1 only as a quick functional test
print(f"\n── Vision OCR page 1 of scanned PDF ─────────")
print(f"  File: {os.path.basename(SCANNED_PDF)}")
try:
    from pdf2image import convert_from_path
    images = convert_from_path(SCANNED_PDF, dpi=72, first_page=1, last_page=1)
    buf = io.BytesIO()
    images[0].save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"  Image size: {images[0].size[0]}×{images[0].size[1]} px  ({len(b64)//1024} KB base64)")
    print(f"  Sending to vision model (num_ctx=4096)...")

    r = requests.post(f"{base}/api/chat", json={
        "model": settings.VISION_MODEL_NAME,
        "messages": [{"role": "user",
                      "content": "Transcribe all text visible in this document image. Output only the text, no comments.",
                      "images": [b64]}],
        "stream": False,
        "options": {"num_predict": 1024, "num_ctx": 4096},
    }, timeout=settings.VISION_REQUEST_TIMEOUT)
    if r.ok:
        text = r.json().get("message", {}).get("content", "").strip()
        print(f"  ✓ {len(text)} chars\n")
        print(text[:600])
    else:
        print(f"  ✗ {r.status_code}: {r.text[:300]}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
