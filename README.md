# doc-manager

A CLI tool that scans a folder of PDF documents, uses a local LLM to understand their content, and reorganises them into a clean subfolder structure with markdown summaries.

## How it works

A LangGraph pipeline with a parallel fan-out for the LLM analysis step:

```
Scanner → Orchestrator ──×N──► Analyst sub-agents → Collector → Taxonomy → Writer → Organizer
```

| Agent | LLM | What it does |
|---|---|---|
| **Scanner** | — | Finds all PDFs, extracts raw text via pdfplumber; falls back to OCR via `ocrmypdf` for scanned images; reads files in parallel |
| **Orchestrator** | — | Splits documents into N batches and fans out to parallel analyst sub-agents |
| **Analyst** | ✓ | Each sub-agent processes its batch; one LLM call per document extracts type, date, sender, amount, summary |
| **Collector** | — | Merges results from all sub-agents back into a single ordered list |
| **Taxonomy** | — | Assigns `sender/type` subfolder deterministically |
| **Writer** | — | Renders a markdown summary file for each document |
| **Organizer** | — | Copies files into the output folder (source unchanged); renames to `<Date>_<Type>_<Sender>`; writes `_index.md` |

Output structure:
```
output/
├── _index.md
├── Acme_GmbH/
│   └── Rechnung/
│       ├── 2024-01-15_Rechnung_Acme_GmbH.pdf
│       └── 2024-01-15_Rechnung_Acme_GmbH.md
└── Musterfirma_AG/
    └── Bericht/
        ├── 2024-03-01_Bericht_Musterfirma_AG.pdf
        └── 2024-03-01_Bericht_Musterfirma_AG.md
```

If date, type, or sender cannot be extracted the original filename is kept.

## Requirements

- Python 3.11+
- A local LLM server with an OpenAI-compatible API (tested with vLLM + Qwen3)
- `ocrmypdf` for scanned image PDFs (optional): `brew install ocrmypdf` / `apt install ocrmypdf`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and fill in your model server details:

```bash
cp .env.example .env
```

## Configuration

All settings live in `.env`:

| Variable | Default | Description |
|---|---|---|
| `MODEL_URL` | — | Base URL of your LLM server, e.g. `http://localhost:8000/` |
| `MODEL_NAME` | — | Model name as registered on the server |
| `ENABLE_THINKING` | `false` | Set `true` to enable extended thinking mode if supported (slower, more accurate) |
| `MAX_AGENTS` | `4` | Number of parallel analyst sub-agents and scanner threads; tune to your vLLM concurrency capacity |
| `MAX_TEXT_CHARS` | `32000` | Max characters of PDF text sent to the LLM (~8k tokens) |
| `TEMPERATURE` | `0.1` | LLM sampling temperature |
| `REQUEST_TIMEOUT` | `120` | Per-request timeout in seconds |

The `/v1` path suffix is appended automatically if missing from `MODEL_URL`.

## Usage

```bash
# Preview planned operations without touching any files
python main.py example-docs/ --output ./organised --dry-run

# Organise into a specific output folder (source folder is never modified)
python main.py example-docs/ --output ./organised

# Also scan subfolders
python main.py example-docs/ --output ./organised --recursive

# Show LLM responses for debugging
python main.py example-docs/ --output ./organised --verbose
```

### Options

```
Arguments:
  SOURCE_FOLDER           Folder to scan for PDFs

Options:
  -o, --output PATH       Output folder (required)
  -r, --recursive         Also scan subfolders of SOURCE_FOLDER
  --dry-run               Preview without copying anything
  --model-url TEXT        LLM API base URL (overrides .env)
  --model-name TEXT       Model name (overrides .env)
  -v, --verbose           Show LLM responses
```

## Agent definitions

Each agent is documented in `agents/<name>.md`. The Analyst and Taxonomy agents load their system prompts directly from those files at runtime — editing the `.md` file changes the LLM behaviour without touching Python code.

## Unreadable PDFs

Scanned images and encrypted PDFs cannot have text extracted. They still flow through the pipeline: the Analyst uses the filename alone to infer metadata, and the markdown summary notes that extraction failed. They land in `unknown/unknown/` if no metadata can be inferred.
