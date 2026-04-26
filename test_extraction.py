"""Test the three-stage extraction chain and vision model connectivity."""
import os

os.environ.setdefault("MODEL_URL", "http://10.10.1.180:8888/")

from doc_manager.config import settings
from doc_manager.tools.pdf_reader import extract_text, _extract_with_vision
from openai import OpenAI

# ── Stage 1+2: pdfplumber + ocrmypdf ─────────────────────────────────────────
print("=== Stage 1+2: pdfplumber + ocrmypdf ===\n")
results = []
for name in sorted(os.listdir("example-docs")):
    if not name.lower().endswith(".pdf"):
        continue
    path = f"example-docs/{name}"
    text, readable, err = extract_text.__wrapped__(path) if hasattr(extract_text, "__wrapped__") else extract_text(path)
    results.append((readable, name, len(text), err))
    tag = "OK" if readable else "--"
    print(f"{tag} | {len(text):>6} chars | {(err or ''):40} | {name}")

readable_count = sum(r[0] for r in results)
print(f"\n{len(results)} PDFs total — {readable_count} readable, {len(results) - readable_count} unreadable\n")

# ── Stage 3: Ollama connectivity ──────────────────────────────────────────────
print("=== Stage 3: Ollama connectivity ===\n")
print(f"URL  : {settings.vision_model_base_url}")
print(f"Model: {settings.VISION_MODEL_NAME}")
print(f"Timeout: {settings.VISION_REQUEST_TIMEOUT}s\n")

try:
    client = OpenAI(base_url=settings.vision_model_base_url, api_key="ollama")
    models = client.models.list()
    names = [m.id for m in models.data]
    print(f"Ollama reachable. Models available: {names}")
    if settings.VISION_MODEL_NAME in names:
        print(f"Configured model '{settings.VISION_MODEL_NAME}' is loaded.")
    else:
        print(f"WARNING: '{settings.VISION_MODEL_NAME}' not in model list — may need to pull it first.")
except Exception as e:
    print(f"Ollama unreachable: {e}")
    raise SystemExit(1)

# ── Stage 3: Vision OCR on the scanned PDF ────────────────────────────────────
scanned = next(
    (f"example-docs/{r[1]}" for r in results if not r[0]), None
)
if not scanned:
    # All readable — use the smallest PDF to still validate end-to-end
    scanned = min(
        (f"example-docs/{r[1]}" for r in results),
        key=lambda p: os.path.getsize(p)
    )
    print(f"\nAll PDFs already readable — testing vision on smallest file: {os.path.basename(scanned)}")
else:
    print(f"\nRunning vision OCR on unreadable file: {os.path.basename(scanned)}")

print(f"(timeout: {settings.VISION_REQUEST_TIMEOUT}s — this may take a while on Jetson Orin)\n")
try:
    text = _extract_with_vision(scanned)
    print(f"Vision response: {len(text)} chars")
    print(f"Preview:\n{text[:400]}")
except Exception as e:
    print(f"Vision OCR failed: {e}")
