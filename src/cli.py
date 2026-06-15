"""Command-line entry point: run the pipeline over documents and write JSON output."""

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

import config
from graph import run_pipeline

_DOC_SUFFIXES = {".docx", ".pdf"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="docpipe", description="Document intelligence pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="process documents into output/*.json")
    run_p.add_argument("path", nargs="?", default=str(config.SAMPLES_DIR),
                       help="a document or a directory of documents")
    run_p.add_argument("--doc", help="process a single document (overrides path)")

    sub.add_parser("eval", help="score the pipeline against data/ground_truth.json")

    args = parser.parse_args()
    if args.command == "run":
        return _run(args)
    if args.command == "eval":
        import sys
        sys.path.insert(0, str(config.ROOT_DIR / "eval"))
        from evaluate import main as eval_main
        return eval_main()

    return 1


def _resolve_files(args) -> list[Path]:
    if args.doc:
        return [Path(args.doc)]
    path = Path(args.path)
    if path.is_dir():
        return sorted(f for f in path.iterdir() if f.suffix.lower() in _DOC_SUFFIXES)
    return [path]


def _run(args) -> int:
    console = Console()
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    table = Table(title="Pipeline results")
    for col in ("Document", "Type", "Conf", "Tags", "Retries", "Calls", "Sec"):
        table.add_column(col)

    for f in _resolve_files(args):
        result = run_pipeline(str(f))
        out_path = config.OUTPUT_DIR / f"{f.stem}.json"
        out_path.write_text(
            json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        m = result.pipeline_meta
        retried = sum(m.retries.values())
        table.add_row(
            f.name, result.classification.document_type,
            f"{result.classification.confidence:.2f}", str(len(result.tags)),
            str(retried), str(m.model_calls), f"{m.duration_seconds:.1f}",
        )
        console.print(f"[green]✓[/green] {f.name} → {out_path.name}")

    console.print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
