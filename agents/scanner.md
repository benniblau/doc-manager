# Scanner Agent

## Role
Discovers all PDF files in the given source folder and extracts their raw text content using pdfplumber.

## Responsibilities
- Recursively find all `.pdf` / `.PDF` files under `source_folder`
- Extract text content page by page, preserving page breaks with `---PAGE BREAK---` separators
- Flag image-only or encrypted PDFs as unreadable (they still flow through the pipeline)
- Report extraction statistics to the user via rich progress bar

## Inputs
- `source_folder: str` — absolute path to scan

## Outputs
Updates `GraphState` with:
- `documents: list[DocumentMetadata]` — each entry has `file_path`, `raw_text`, `is_readable`, `parse_error` populated
- `total_docs: int`
- `current_phase: "analyze"`

## Error Handling
| Scenario | Behavior |
|---|---|
| Encrypted PDF | `is_readable=False`, `parse_error="encrypted"` |
| Image-only PDF (no extractable text) | `is_readable=False`, `parse_error="no_text_extracted"` |
| Missing/inaccessible file | Skipped, error logged |

## No LLM calls
This agent performs purely local operations.
