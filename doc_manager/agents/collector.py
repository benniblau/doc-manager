from rich.console import Console

from doc_manager.state import GraphState

console = Console()


def collector_node(state: GraphState) -> dict:
    """Merges parallel analyst results back into documents. Runs once after all sub-agents finish."""
    merged = sorted(state["analysed_docs"], key=lambda d: d.file_path)
    console.print(f"[dim]Collector: merged {len(merged)} document(s) from all agents.[/]")
    return {
        "documents": merged,
        "current_phase": "taxonomy",
        "processed_docs": len(merged),
    }
