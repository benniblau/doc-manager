from rich.console import Console

from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.file_ops import sanitize_filename

console = Console()


def _subfolder(doc: DocumentMetadata) -> str:
    sender = sanitize_filename((doc.sender or "unknown").strip()).lower()
    doc_type = sanitize_filename((doc.doc_type or "unknown").strip()).lower()
    return f"{sender}/{doc_type}"


def taxonomy_node(state: GraphState) -> dict:
    documents = state["documents"]
    updated_docs = []

    console.print("[bold yellow]Taxonomy[/] — organising by sender → type...")
    for doc in documents:
        updated_docs.append(doc.model_copy(update={"target_subfolder": _subfolder(doc)}))

    return {
        "documents": updated_docs,
        "taxonomy": {},
        "errors": [],
        "current_phase": "write",
    }
