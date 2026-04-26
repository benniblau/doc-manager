import os
from datetime import date

from rich.console import Console
from rich.table import Table

from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.file_ops import copy_file, ensure_dir, move_file, sanitize_filename, write_text

console = Console()


def _build_stem(doc: DocumentMetadata) -> str | None:
    """Build a filename stem from document metadata: <Date>_<Type>_<Sender>.
    Returns None if any field is missing — caller should fall back to original filename."""
    if not doc.date or not doc.doc_type or not doc.sender:
        return None
    return f"{sanitize_filename(doc.date)}_{sanitize_filename(doc.doc_type)}_{sanitize_filename(doc.sender)}"


def _dest_path(output_folder: str, subfolder: str, doc: DocumentMetadata, ext: str) -> str:
    stem = _build_stem(doc) or sanitize_filename(os.path.splitext(os.path.basename(doc.file_path))[0])
    base = os.path.join(output_folder, subfolder, f"{stem}{ext}")
    # Avoid overwriting an existing file with a different source
    if not os.path.exists(base):
        return base
    original_stem = sanitize_filename(os.path.splitext(os.path.basename(doc.file_path))[0])
    candidate = os.path.join(output_folder, subfolder, f"{stem}_{original_stem}{ext}")
    if not os.path.exists(candidate):
        return candidate
    counter = 2
    while True:
        candidate = os.path.join(output_folder, subfolder, f"{stem}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _build_index(documents: list[DocumentMetadata], source_folder: str, today: str) -> str:
    lines = [
        "# Document Index",
        "",
        f"Generated: {today}  ",
        f"Source: `{source_folder}`  ",
        f"Total documents: {len(documents)}",
        "",
        "| Subfolder | Filename | Type | Date | Sender | Amount |",
        "|---|---|---|---|---|---|",
    ]
    for doc in sorted(documents, key=lambda d: (d.target_subfolder or "", os.path.basename(d.file_path))):
        amount = f"{doc.amount} {doc.currency}" if doc.amount is not None else "—"
        lines.append(
            f"| {doc.target_subfolder or '—'} "
            f"| {os.path.basename(doc.file_path)} "
            f"| {doc.doc_type or '—'} "
            f"| {doc.date or '—'} "
            f"| {doc.sender or '—'} "
            f"| {amount} |"
        )
    return "\n".join(lines) + "\n"


def organizer_node(state: GraphState) -> dict:
    output_folder = state["output_folder"]
    dry_run = state["dry_run"]
    copy_mode = state["copy_mode"]
    documents = state["documents"]
    today = date.today().isoformat()

    if dry_run:
        table = Table(title="Planned Operations (dry run)", show_lines=True)
        table.add_column("Action", style="cyan")
        table.add_column("Source")
        table.add_column("Destination")
        for doc in documents:
            subfolder = doc.target_subfolder or "unknown"
            pdf_dest = _dest_path(output_folder, subfolder, doc, ".pdf")
            md_dest = _dest_path(output_folder, subfolder, doc, ".md")
            action = "COPY" if copy_mode else "MOVE"
            table.add_row(action, doc.file_path, pdf_dest)
            if doc.markdown_path:
                table.add_row(action, doc.markdown_path, md_dest)
        console.print(table)
        return {"documents": documents, "current_phase": "done"}

    ensure_dir(output_folder)
    transfer = copy_file if copy_mode else move_file
    updated_docs = []

    for doc in documents:
        subfolder = doc.target_subfolder or "unknown"
        pdf_dest = _dest_path(output_folder, subfolder, doc, ".pdf")
        md_dest = _dest_path(output_folder, subfolder, doc, ".md")

        try:
            transfer(doc.file_path, pdf_dest)
        except Exception as e:
            console.print(f"[red]Failed to transfer {doc.file_path}: {e}[/]")
            pdf_dest = doc.file_path

        if doc.markdown_path and os.path.exists(doc.markdown_path):
            try:
                copy_file(doc.markdown_path, md_dest)
            except Exception as e:
                console.print(f"[red]Failed to copy markdown {doc.markdown_path}: {e}[/]")
                md_dest = doc.markdown_path

        updated_docs.append(doc.model_copy(update={
            "final_pdf_path": pdf_dest,
            "markdown_path": md_dest,
        }))

    index_path = os.path.join(output_folder, "_index.md")
    write_text(index_path, _build_index(updated_docs, state["source_folder"], today))
    console.print(f"[green]Index written to {index_path}[/]")

    return {"documents": updated_docs, "current_phase": "done"}
