# CLAUDE.md

## Project overview

Python CLI that organises PDF documents using a local LLM. Five LangGraph agents run in a linear pipeline: Scanner → Analyst → Taxonomy → Writer → Organizer. Entry point is `main.py`.

## Commands

```bash
# Run with venv
venv/bin/python3 main.py <folder> [--dry-run] [--copy] [--verbose]

# Install deps
venv/bin/pip install -e .
```

## Architecture

### State

`doc_manager/state.py` defines two types:
- `DocumentMetadata` (Pydantic model) — per-document data, populated incrementally across agents
- `GraphState` (TypedDict) — full pipeline state; `documents` is a plain `list` (each node replaces it entirely); `errors` uses `Annotated[list, operator.add]` to accumulate across nodes

### Agent responsibilities

| File | LLM | Notes |
|---|---|---|
| `doc_manager/agents/scanner.py` | — | Globs PDFs, calls `tools/pdf_reader.py` |
| `doc_manager/agents/analyst.py` | ✓ | One call per document; system prompt loaded from `agents/analyst.md` |
| `doc_manager/agents/taxonomy.py` | — | Deterministic `sender/type` rule; no LLM call |
| `doc_manager/agents/writer.py` | — | Template rendering only; writes to a `tempfile.mkdtemp` dir |
| `doc_manager/agents/organizer.py` | — | Moves/copies files; in dry-run prints rich table instead |

### LLM client

The OpenAI SDK is used against a local vLLM server. Key details:
- `MODEL_URL` is normalised to end with `/v1` in `config.py:model_base_url`
- Qwen3 runs in thinking mode by default; `ENABLE_THINKING=false` disables it via `chat_template_kwargs` (vLLM-specific, passed through `extra_body`)
- `enable_thinking` as a bare top-level body field causes the server to hang — always use `chat_template_kwargs`
- The `enable_thinking` flag in the request body (not in `chat_template_kwargs`) also causes a hang — do not use it

### Agent markdown files

`agents/*.md` serve dual purpose: human documentation AND runtime system prompts. The Analyst loads its system prompt by extracting the text block under `## System Prompt` in `agents/analyst.md`. Edit the markdown to change LLM behaviour.

## Key constraints

- **No `operator.add` on `documents`** — each agent returns the full updated list; using a reducer would duplicate documents across nodes
- **`enable_thinking` hangs the server** — only `chat_template_kwargs: {enable_thinking: bool}` works on this vLLM instance
- **pdfplumber over pymupdf** — better extraction from German financial docs with mixed table/text layouts
- **Taxonomy is deterministic** — it was intentionally simplified from an LLM-based proposal to a fixed `sender/type` rule for predictability
- **Writer uses tempfile** — markdown files are written to a temp dir; the Organizer copies them to their final destination alongside the PDFs

## Environment

```
MODEL_URL=http://10.10.1.180:8888/    # local vLLM server, /v1 appended automatically
MODEL_NAME=Qwen3.6
ENABLE_THINKING=false                  # true = slower but more thorough reasoning
```
