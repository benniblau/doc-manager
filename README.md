# doc-manager

A CLI tool that scans a folder of PDF documents, uses a local LLM to understand their content, and reorganises them into a clean subfolder structure with markdown summaries.

## How it works

Five LangGraph agents run in sequence:

| Agent | LLM | What it does |
|---|---|---|
| **Scanner** | — | Finds all PDFs, extracts raw text via pdfplumber |
| **Analyst** | ✓ | Extracts metadata per document: type, date, sender, amount, summary |
| **Taxonomy** | — | Assigns `sender/type` subfolder deterministically |
| **Writer** | — | Renders a markdown summary file for each document |
| **Organizer** | — | Moves/copies files into the new structure, writes `_index.md` |

Output structure:
```
output/
├── _index.md                    ← master index of all documents
├── acme_gmbh/
│   ├── rechnung/
│   │   ├── rechnung_1001.pdf
│   │   └── rechnung_1001.md
│   └── schlussrechnung/
│       ├── schlussrechnung_final.pdf
│       └── schlussrechnung_final.md
└── musterfirma_ag/
    └── bericht/
        ├── bericht_2024.pdf
        └── bericht_2024.md
```

## Requirements

- Python 3.11+
- A local LLM server with an OpenAI-compatible API (tested with vLLM + Qwen3)

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
| `MAX_TEXT_CHARS` | `32000` | Max characters of PDF text sent to the LLM (~8k tokens) |
| `TEMPERATURE` | `0.1` | LLM sampling temperature |
| `REQUEST_TIMEOUT` | `120` | Per-request timeout in seconds |

The `/v1` path suffix is appended automatically if missing from `MODEL_URL`.

## Usage

```bash
# Preview — no files are moved
python main.py example-docs/ --dry-run

# Copy files into a new organised folder (originals preserved)
python main.py example-docs/ --copy

# Move files into a custom output folder
python main.py example-docs/ --output ./organised

# Show LLM responses for debugging
python main.py example-docs/ --copy --verbose
```

### Options

```
Arguments:
  SOURCE_FOLDER         Folder to scan for PDFs

Options:
  -o, --output PATH     Output folder  [default: <source>/_organized]
  --dry-run             Preview without moving anything
  --copy                Copy instead of move
  --model-url TEXT      LLM API base URL (overrides .env)
  --model-name TEXT     Model name (overrides .env)
  -v, --verbose         Show LLM responses
```

## Agent definitions

Each agent is documented in `agents/<name>.md`. The Analyst and Taxonomy agents load their system prompts directly from those files at runtime — editing the `.md` file changes the LLM behaviour without touching Python code.

## Unreadable PDFs

Scanned images and encrypted PDFs cannot have text extracted. They still flow through the pipeline: the Analyst uses the filename alone to infer metadata, and the markdown summary notes that extraction failed. They land in `unknown/unknown/` if no metadata can be inferred.
