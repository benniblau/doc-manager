from math import ceil

from langgraph.types import Command, Send
from rich.console import Console

from doc_manager.state import GraphState

console = Console()


def orchestrator_node(state: GraphState) -> Command:
    docs = state["documents"]
    max_agents = state.get("max_agents", 4)

    if not docs:
        console.print("[dim]Orchestrator: no documents to analyze, skipping.[/]")
        return Command(goto="collector")

    n = min(max_agents, len(docs))
    chunk_size = ceil(len(docs) / n)
    chunks = [docs[i:i + chunk_size] for i in range(0, len(docs), chunk_size)]

    console.print(
        f"[bold]Orchestrator:[/] {len(docs)} document(s) → "
        f"{len(chunks)} agent(s) × ~{chunk_size} doc(s) each"
    )

    return Command(goto=[
        Send("analyst_sub", {
            "chunk": chunk,
            "verbose": state["verbose"],
            "agent_index": idx,
        })
        for idx, chunk in enumerate(chunks)
    ])
