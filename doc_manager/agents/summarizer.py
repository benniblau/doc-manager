import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from openai import OpenAI
from rich.console import Console

from doc_manager.config import settings
from doc_manager.state import DocumentMetadata, GraphState
from doc_manager.tools.file_ops import write_text

console = Console()


def _load_system_prompt() -> str:
    md_path = Path(__file__).parent.parent.parent / "agents" / "summarizer.md"
    text = md_path.read_text(encoding="utf-8")
    match = re.search(r"## System Prompt\n\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return match.group(1).strip() if match else text


def _format_doc(doc: DocumentMetadata) -> str:
    lines = [f"- Datei: {os.path.basename(doc.file_path)}"]
    if doc.doc_type:
        lines.append(f"  Typ: {doc.doc_type}")
    if doc.date:
        lines.append(f"  Datum: {doc.date}")
    if doc.sender:
        lines.append(f"  Absender: {doc.sender}")
    if doc.recipient:
        lines.append(f"  Empfänger: {doc.recipient}")
    if doc.amount is not None:
        lines.append(f"  Betrag: {doc.amount} {doc.currency}")
    if doc.invoice_number:
        lines.append(f"  Rechnungsnr.: {doc.invoice_number}")
    if doc.project_ref:
        lines.append(f"  Projektreferenz: {doc.project_ref}")
    if doc.summary:
        lines.append(f"  Zusammenfassung: {doc.summary}")
    return "\n".join(lines)


def _generate_summary(client: OpenAI, system_prompt: str, subfolder: str, docs: list[DocumentMetadata]) -> str:
    doc_list = "\n\n".join(_format_doc(d) for d in docs)
    user_content = f"Ordner: {subfolder}\nAnzahl Dokumente: {len(docs)}\n\n{doc_list}"

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
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            if attempt == 1:
                return f"<!-- Zusammenfassung konnte nicht generiert werden: {e} -->"
    return ""


def summarizer_node(state: GraphState) -> dict:
    documents = state["documents"]
    output_folder = state["output_folder"]
    dry_run = state["dry_run"]
    today = date.today().isoformat()

    # Group documents by target subfolder
    by_subfolder: dict[str, list[DocumentMetadata]] = defaultdict(list)
    for doc in documents:
        by_subfolder[doc.target_subfolder or "unknown"].append(doc)

    if dry_run:
        console.print(f"\n[dim]Summarizer (dry run): would write SUMMARY.md to {len(by_subfolder)} folder(s):[/]")
        for subfolder in sorted(by_subfolder):
            count = len(by_subfolder[subfolder])
            console.print(f"  [dim]• {subfolder}/ ({count} doc(s))[/]")
        return {"current_phase": "done"}

    client = OpenAI(base_url=settings.model_base_url, api_key="none")
    system_prompt = _load_system_prompt()
    errors = []

    for subfolder, docs in sorted(by_subfolder.items()):
        console.print(f"[bold green]Summarizer[/] generating summary for [cyan]{subfolder}[/] ({len(docs)} doc(s))")
        content = _generate_summary(client, system_prompt, subfolder, docs)

        header = f"# Zusammenfassung: {subfolder}\n\n_Erstellt: {today} · {len(docs)} Dokument(e)_\n\n"
        summary_path = os.path.join(output_folder, subfolder, "SUMMARY.md")
        try:
            write_text(summary_path, header + content + "\n")
            console.print(f"  [green]✓[/] {summary_path}")
        except Exception as e:
            msg = f"summarizer: failed to write {summary_path}: {e}"
            console.print(f"  [red]✗[/] {msg}")
            errors.append(msg)

    return {"current_phase": "done", "errors": errors}
