import json
import os
import re
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from doc_manager.config import settings
from doc_manager.state import DocumentMetadata, GraphState

console = Console()


def _load_system_prompt() -> str:
    agents_dir = Path(__file__).parent.parent.parent / "agents"
    md_path = agents_dir / "analyst.md"
    text = md_path.read_text(encoding="utf-8")
    # Extract the block between "## System Prompt" and the next "##"
    match = re.search(r"## System Prompt\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _parse_json_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _analyze_one(client: OpenAI, system_prompt: str, doc: DocumentMetadata, verbose: bool) -> dict:
    if doc.is_readable and doc.raw_text:
        user_content = f"Dokument:\n\n{doc.raw_text[:settings.MAX_TEXT_CHARS]}"
    else:
        filename = os.path.basename(doc.file_path)
        user_content = (
            f"Kein Text extrahierbar, nur Dateiname verfügbar: {filename}\n"
            f"Fehler: {doc.parse_error or 'unbekannt'}"
        )

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=settings.TEMPERATURE,
                max_tokens=1024,
                timeout=settings.REQUEST_TIMEOUT * (attempt + 1),
                extra_body={"chat_template_kwargs": {"enable_thinking": settings.ENABLE_THINKING}},
            )
            raw = response.choices[0].message.content or ""
            if verbose:
                print(f"\n[analyst] {os.path.basename(doc.file_path)}: {raw[:200]}")
            return _parse_json_response(raw)
        except Exception as e:
            if attempt == 1:
                return {"_error": str(e)}
    return {}


def analyst_node(state: GraphState) -> dict:
    verbose = state.get("verbose", False)
    client = OpenAI(
        base_url=settings.model_base_url,
        api_key="none",
    )
    system_prompt = _load_system_prompt()
    updated_docs = []
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Analyzing"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.description}"),
    ) as progress:
        task = progress.add_task("", total=len(state["documents"]))
        for doc in state["documents"]:
            progress.update(task, description=os.path.basename(doc.file_path))
            result = _analyze_one(client, system_prompt, doc, verbose)

            if "_error" in result:
                errors.append(f"analyst: {doc.file_path}: {result['_error']}")
                updated_docs.append(doc.model_copy(update={"doc_type": "unknown"}))
            else:
                amount = result.get("amount")
                if amount is not None:
                    try:
                        amount = float(amount)
                    except (TypeError, ValueError):
                        amount = None
                updated_docs.append(doc.model_copy(update={
                    "doc_type": result.get("doc_type") or "unknown",
                    "date": result.get("date"),
                    "sender": result.get("sender"),
                    "recipient": result.get("recipient"),
                    "amount": amount,
                    "currency": result.get("currency", "EUR"),
                    "invoice_number": result.get("invoice_number"),
                    "project_ref": result.get("project_ref"),
                    "summary": result.get("summary"),
                }))
            progress.advance(task)

    return {
        "documents": updated_docs,
        "errors": errors,
        "current_phase": "taxonomy",
        "processed_docs": len(updated_docs),
    }


def analyst_sub_node(state: dict) -> dict:
    """Processes one batch of documents. Receives {chunk, verbose, agent_index} from orchestrator via Send."""
    chunk: list[DocumentMetadata] = state["chunk"]
    verbose: bool = state.get("verbose", False)
    agent_index: int = state.get("agent_index", 0)
    label = f"[bold green]Agent {agent_index + 1}[/]"

    console.print(f"{label} starting — {len(chunk)} document(s)")

    client = OpenAI(base_url=settings.model_base_url, api_key="none")
    system_prompt = _load_system_prompt()
    updated_docs = []
    errors = []

    for i, doc in enumerate(chunk, 1):
        filename = os.path.basename(doc.file_path)
        console.print(f"  {label} [{i}/{len(chunk)}] analyzing [cyan]{filename}[/]")
        result = _analyze_one(client, system_prompt, doc, verbose)

        if "_error" in result:
            errors.append(f"analyst: {doc.file_path}: {result['_error']}")
            updated_docs.append(doc.model_copy(update={"doc_type": "unknown"}))
        else:
            amount = result.get("amount")
            if amount is not None:
                try:
                    amount = float(amount)
                except (TypeError, ValueError):
                    amount = None
            updated_docs.append(doc.model_copy(update={
                "doc_type": result.get("doc_type") or "unknown",
                "date": result.get("date"),
                "sender": result.get("sender"),
                "recipient": result.get("recipient"),
                "amount": amount,
                "currency": result.get("currency", "EUR"),
                "invoice_number": result.get("invoice_number"),
                "project_ref": result.get("project_ref"),
                "summary": result.get("summary"),
            }))

    console.print(f"{label} done — {len(updated_docs)} document(s) analyzed")
    return {"analysed_docs": updated_docs, "errors": errors}
