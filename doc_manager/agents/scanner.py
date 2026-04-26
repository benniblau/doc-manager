import glob
import os

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.pdf_reader import extract_text


def scanner_node(state: GraphState) -> dict:
    source_folder = state["source_folder"]

    pattern_lower = os.path.join(source_folder, "**", "*.pdf")
    pattern_upper = os.path.join(source_folder, "**", "*.PDF")
    pdf_files = sorted(
        set(glob.glob(pattern_lower, recursive=True) + glob.glob(pattern_upper, recursive=True))
    )

    documents = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.description}"),
    ) as progress:
        task = progress.add_task("", total=len(pdf_files))
        for path in pdf_files:
            progress.update(task, description=os.path.basename(path))
            text, is_readable, error = extract_text(path)
            documents.append(DocumentMetadata(
                file_path=path,
                raw_text=text if is_readable else None,
                is_readable=is_readable,
                parse_error=error,
            ))
            progress.advance(task)

    return {
        "documents": documents,
        "total_docs": len(documents),
        "current_phase": "analyze",
    }
