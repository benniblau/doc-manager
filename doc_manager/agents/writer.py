import os
import tempfile
from datetime import date

from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.file_ops import sanitize_filename, write_text


_TEMPLATE = """\
# {filename}

## Metadata

| Field         | Value                    |
|---------------|--------------------------|
| Type          | {doc_type}               |
| Date          | {date}                   |
| Sender        | {sender}                 |
| Recipient     | {recipient}              |
| Amount        | {amount}                 |
| Invoice No.   | {invoice_number}         |
| Project       | {project_ref}            |

## Summary

{summary}

## Source

- Original file: `{filename}`
- Processed: {today}
"""

_UNREADABLE_NOTE = (
    "\n> **Note:** Text could not be extracted from this PDF "
    "(possibly a scanned image or encrypted file).\n"
)


def _dash(value) -> str:
    if value is None or str(value).strip() == "":
        return "—"
    return str(value)


def _render(doc: DocumentMetadata, today: str) -> str:
    filename = os.path.basename(doc.file_path)
    amount_str = f"{doc.amount} {doc.currency}" if doc.amount is not None else "—"
    content = _TEMPLATE.format(
        filename=filename,
        doc_type=_dash(doc.doc_type),
        date=_dash(doc.date),
        sender=_dash(doc.sender),
        recipient=_dash(doc.recipient),
        amount=amount_str,
        invoice_number=_dash(doc.invoice_number),
        project_ref=_dash(doc.project_ref),
        summary=_dash(doc.summary),
        today=today,
    )
    if not doc.is_readable:
        content = content.replace("## Summary\n", f"## Summary\n{_UNREADABLE_NOTE}\n")
    return content


def writer_node(state: GraphState) -> dict:
    today = date.today().isoformat()
    tmp_dir = tempfile.mkdtemp(prefix="doc_manager_")
    updated_docs = []

    for doc in state["documents"]:
        stem = sanitize_filename(os.path.splitext(os.path.basename(doc.file_path))[0])
        md_path = os.path.join(tmp_dir, f"{stem}.md")
        content = _render(doc, today)
        write_text(md_path, content)
        updated_docs.append(doc.model_copy(update={"markdown_path": md_path}))

    return {
        "documents": updated_docs,
        "current_phase": "organize",
    }
