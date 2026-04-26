from langgraph.graph import StateGraph, END

from doc_manager.state import GraphState
from doc_manager.agents.scanner import scanner_node
from doc_manager.agents.orchestrator import orchestrator_node
from doc_manager.agents.analyst import analyst_sub_node
from doc_manager.agents.collector import collector_node
from doc_manager.agents.taxonomy import taxonomy_node
from doc_manager.agents.writer import writer_node
from doc_manager.agents.organizer import organizer_node


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("scanner",      scanner_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("analyst_sub",  analyst_sub_node)
    g.add_node("collector",    collector_node)
    g.add_node("taxonomy",     taxonomy_node)
    g.add_node("writer",       writer_node)
    g.add_node("organizer",    organizer_node)

    g.set_entry_point("scanner")
    g.add_edge("scanner",      "orchestrator")
    # orchestrator uses Command(goto=[Send(...)]) — no add_edge needed for its fan-out
    g.add_edge("analyst_sub",  "collector")
    g.add_edge("collector",    "taxonomy")
    g.add_edge("taxonomy",     "writer")
    g.add_edge("writer",       "organizer")
    g.add_edge("organizer",    END)

    return g.compile()
