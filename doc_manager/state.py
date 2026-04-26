import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    file_path: str
    raw_text: Optional[str] = None
    is_readable: bool = True
    parse_error: Optional[str] = None

    doc_type: Optional[str] = None
    date: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "EUR"
    invoice_number: Optional[str] = None
    project_ref: Optional[str] = None
    summary: Optional[str] = None

    target_subfolder: Optional[str] = None
    markdown_path: Optional[str] = None
    final_pdf_path: Optional[str] = None


class GraphState(TypedDict):
    source_folder: str
    output_folder: str
    dry_run: bool
    verbose: bool
    recursive: bool
    max_agents: int
    # Each node replaces the full list; errors accumulate across nodes
    documents: list[DocumentMetadata]
    # Accumulator for parallel analyst sub-agents; merged into documents by collector
    analysed_docs: Annotated[list[DocumentMetadata], operator.add]
    taxonomy: Optional[dict[str, str]]
    errors: Annotated[list[str], operator.add]
    current_phase: str
    total_docs: int
    processed_docs: int
