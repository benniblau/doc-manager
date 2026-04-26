# CLAUDE.md

## Project overview

Python CLI that organises PDF documents using a local LLM. A LangGraph pipeline runs in two phases: a linear outer pipeline (Scanner → Orchestrator → Collector → Taxonomy → Writer → Organizer) and a parallel inner fan-out (Orchestrator fans out to N `analyst_sub` agents, Collector merges results). Entry point is `main.py`.

## Commands

```bash
# Run with venv
venv/bin/python3 main.py <folder> --output <dest> [--dry-run] [--verbose] [--recursive]

# Install deps
venv/bin/pip install -e .

# Install ocrmypdf for scanned PDF support (optional)
brew install ocrmypdf          # macOS
apt install ocrmypdf           # Debian/Ubuntu
```

## Architecture

### State

`doc_manager/state.py` defines two types:
- `DocumentMetadata` (Pydantic model) — per-document data, populated incrementally across agents
- `GraphState` (TypedDict) — full pipeline state:
  - `documents` — plain `list`; each outer node replaces it entirely (no reducer)
  - `analysed_docs` — `Annotated[list, operator.add]`; accumulates results from parallel analyst sub-agents; merged back into `documents` by the collector
  - `errors` — `Annotated[list, operator.add]`; accumulates across all nodes including parallel sub-agents
  - `max_agents` — int; read from config, controls parallelism for both scanner threads and analyst fan-out

### Pipeline

```
scanner → orchestrator ──Send×N──► analyst_sub (parallel) → collector → taxonomy → writer → organizer
```

### Agent responsibilities

| File | LLM | Notes |
|---|---|---|
| `doc_manager/agents/scanner.py` | — | Globs PDFs (top-level by default, `--recursive` for subfolders); reads files in parallel via `ThreadPoolExecutor(MAX_AGENTS)` |
| `doc_manager/agents/orchestrator.py` | — | Divides documents into N batches; returns `Command(goto=[Send("analyst_sub", ...)])` to fan out |
| `doc_manager/agents/analyst.py` | ✓ | `analyst_sub_node` processes one batch; one LLM call per document; system prompt from `agents/analyst.md` |
| `doc_manager/agents/collector.py` | — | Merges `analysed_docs` (accumulated from all sub-agents) back into `documents`; sorts by `file_path` to restore deterministic order |
| `doc_manager/agents/taxonomy.py` | — | Deterministic `sender/type` rule; no LLM call |
| `doc_manager/agents/writer.py` | — | Template rendering only; writes to a `tempfile.mkdtemp` dir |
| `doc_manager/agents/organizer.py` | — | Copies files to explicitly provided output folder (source never modified); renames to `<Date>_<Type>_<Sender>` — falls back to original filename if any field is missing; in dry-run prints rich table instead |

### LLM client

The OpenAI SDK is used against a local vLLM server. Key details:
- `MODEL_URL` is normalised to end with `/v1` in `config.py:model_base_url`
- Qwen3 runs in thinking mode by default; `ENABLE_THINKING=false` disables it via `chat_template_kwargs` (vLLM-specific, passed through `extra_body`)
- `enable_thinking` as a bare top-level body field causes the server to hang — always use `chat_template_kwargs`
- The `enable_thinking` flag in the request body (not in `chat_template_kwargs`) also causes a hang — do not use it

### Agent markdown files

`agents/*.md` serve dual purpose: human documentation AND runtime system prompts. The Analyst loads its system prompt by extracting the text block under `## System Prompt` in `agents/analyst.md`. Edit the markdown to change LLM behaviour.

## Key constraints

- **No `operator.add` on `documents`** — each outer node returns the full updated list; use `analysed_docs` (which does use `operator.add`) as the accumulator for parallel sub-agent results, then move them into `documents` in the collector
- **`enable_thinking` hangs the server** — only `chat_template_kwargs: {enable_thinking: bool}` works on this vLLM instance
- **pdfplumber over pymupdf** — better extraction from German financial docs with mixed table/text layouts
- **OCR fallback via ocrmypdf** — if pdfplumber extracts no text, `tools/pdf_reader.py` shells out to `ocrmypdf` (`--deskew --clean --language deu+eng`) and re-extracts from the resulting PDF; gracefully skipped if `ocrmypdf` is not installed; exit code 6 (already has text layer) is treated as success
- **Output folder is required** — `--output <dest>` must be explicitly provided; there is no default; source folder is never modified
- **Files are always copied, never moved** — the `--copy` flag no longer exists; the organizer always copies so the source remains intact
- **Filename template `<Date>_<Type>_<Sender>`** — the organizer renames both the PDF and its markdown sidecar using sanitized metadata; if any of the three fields is missing the original filename is kept unchanged; collision handling appends the original stem then a numeric counter
- **Taxonomy is deterministic** — it was intentionally simplified from an LLM-based proposal to a fixed `sender/type` rule for predictability
- **Writer uses tempfile** — markdown files are written to a temp dir; the Organizer copies them to their final destination alongside the PDFs

## Environment

```
MODEL_URL=http://localhost:8000/    # local vLLM server, /v1 appended automatically
MODEL_NAME=your-model-name
ENABLE_THINKING=false               # true = slower but more thorough reasoning
MAX_AGENTS=4                        # parallel analyst sub-agents and scanner threads; tune to vLLM concurrency capacity
```
