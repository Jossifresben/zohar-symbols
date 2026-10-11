# pipeline/report.py
from pathlib import Path


def write_report(path: Path, title: str, rows: list[tuple[str, object]]) -> None:
    lines = [f"# {title}", "", "| item | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
