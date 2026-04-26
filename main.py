import os
import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _ping_llm(model_url: str, model_name: str, timeout: int) -> None:
    from openai import OpenAI
    client = OpenAI(base_url=model_url, api_key="none")
    try:
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=timeout,
        )
    except Exception as e:
        raise click.ClickException(
            f"Cannot reach LLM at {model_url} (model: {model_name})\n"
            f"Error: {e}\n"
            "Check that your local model server is running and MODEL_URL in .env is correct."
        )


@click.command()
@click.argument("source_folder", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--output", "-o", default=None,
              help="Output folder. Defaults to <source_folder>/_organized")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview planned file operations without moving anything")
@click.option("--copy", is_flag=True, default=False,
              help="Copy files instead of moving them")
@click.option("--model-url", envvar="MODEL_URL", default=None,
              help="LLM API base URL (overrides .env)")
@click.option("--model-name", envvar="MODEL_NAME", default=None,
              help="LLM model name (overrides .env)")
@click.option("--verbose", "-v", is_flag=True, default=False,
              help="Show LLM responses and debug info")
@click.option("--recursive", "-r", is_flag=True, default=False,
              help="Scan all subfolders of the source folder")
def main(source_folder, output, dry_run, copy, model_url, model_name, verbose, recursive):
    """Organize PDF documents using a local LLM multi-agent pipeline."""
    from dotenv import load_dotenv
    load_dotenv()

    # Allow CLI flags to override .env
    if model_url:
        os.environ["MODEL_URL"] = model_url
    if model_name:
        os.environ["MODEL_NAME"] = model_name

    # Import settings after env is set
    from doc_manager.config import settings

    output_folder = output or os.path.join(source_folder, "_organized")

    console.print(f"[bold]Document Manager[/]")
    console.print(f"  Source : {source_folder}")
    console.print(f"  Output : {output_folder}")
    console.print(f"  Model  : {settings.MODEL_NAME} @ {settings.MODEL_URL}")
    console.print(f"  Mode   : {'dry-run' if dry_run else 'copy' if copy else 'move'}")
    console.print(f"  Scan   : {'recursive' if recursive else 'top-level only'}")
    console.print(f"  Agents : {settings.MAX_AGENTS} parallel")
    console.print()

    console.print("[dim]Checking LLM connection...[/]")
    _ping_llm(settings.model_base_url, settings.MODEL_NAME, timeout=10)
    console.print("[green]LLM reachable.[/]\n")

    from doc_manager.graph import build_graph
    graph = build_graph()

    initial_state = {
        "source_folder": source_folder,
        "output_folder": output_folder,
        "dry_run": dry_run,
        "copy_mode": copy,
        "verbose": verbose,
        "recursive": recursive,
        "max_agents": settings.MAX_AGENTS,
        "documents": [],
        "analysed_docs": [],
        "taxonomy": None,
        "errors": [],
        "current_phase": "scan",
        "total_docs": 0,
        "processed_docs": 0,
    }

    result = graph.invoke(initial_state)

    # Summary table
    documents = result.get("documents", [])
    errors = result.get("errors", [])

    console.print()
    table = Table(title="Results", show_lines=False)
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Type", style="green")
    table.add_column("Date")
    table.add_column("Sender")
    table.add_column("Subfolder")
    table.add_column("Readable")

    for doc in documents:
        import os as _os
        table.add_row(
            _os.path.basename(doc.file_path),
            doc.doc_type or "—",
            doc.date or "—",
            (doc.sender or "—")[:30],
            doc.target_subfolder or "—",
            "[green]yes[/]" if doc.is_readable else "[red]no[/]",
        )
    console.print(table)

    if errors:
        console.print(f"\n[yellow]Warnings / errors ({len(errors)}):[/]")
        for err in errors:
            console.print(f"  [yellow]•[/] {err}")

    total = len(documents)
    readable = sum(1 for d in documents if d.is_readable)
    console.print(f"\n[bold]Done.[/] {total} documents processed ({readable} readable, {total - readable} unreadable).")
    if not dry_run:
        console.print(f"Output: {output_folder}")


if __name__ == "__main__":
    main()
