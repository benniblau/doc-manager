import concurrent.futures
import glob
import os

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from doc_manager.config import settings
from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.pdf_reader import extract_text


def scanner_node(state: GraphState) -> dict:
    source_folder = state["source_folder"]
    recursive = state.get("recursive", False)
    max_workers = state.get("max_agents", settings.MAX_AGENTS)

    if recursive:
        pattern_lower = os.path.join(source_folder, "**", "*.pdf")
        pattern_upper = os.path.join(source_folder, "**", "*.PDF")
        pdf_files = sorted(
            set(glob.glob(pattern_lower, recursive=True) + glob.glob(pattern_upper, recursive=True))
        )
    else:
        pattern_lower = os.path.join(source_folder, "*.pdf")
        pattern_upper = os.path.join(source_folder, "*.PDF")
        pdf_files = sorted(set(glob.glob(pattern_lower) + glob.glob(pattern_upper)))

    documents = [None] * len(pdf_files)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.description}"),
    ) as progress:
        task = progress.add_task("", total=len(pdf_files))

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(pdf_files)) if pdf_files else 1) as executor:
            future_to_idx = {executor.submit(extract_text, path): i for i, path in enumerate(pdf_files)}
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                path = pdf_files[idx]
                text, is_readable, error = future.result()
                documents[idx] = DocumentMetadata(
                    file_path=path,
                    raw_text=text if is_readable else None,
                    is_readable=is_readable,
                    parse_error=error,
                )
                progress.update(task, advance=1, description=os.path.basename(path))

    return {
        "documents": documents,
        "total_docs": len(documents),
        "current_phase": "analyze",
    }
