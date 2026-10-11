# pipeline/report.py
from pathlib import Path

# per-item detail rows: kept in the stage reports (raw/, work/), left out of data/report.md
DETAIL_PREFIXES = ("continued: ", "split across pages: ", "low-conf #", "top #")


def _table(title: str, rows: list[tuple[str, object]]) -> list[str]:
    return [f"# {title}", "", "| item | value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows]


def write_report(path: Path, title: str, rows: list[tuple[str, object]]) -> None:
    write_sections(path, [(title, rows)])


def write_sections(path: Path, sections: list[tuple[str, list[tuple[str, object]]]]) -> None:
    lines: list[str] = []
    for title, rows in sections:
        if lines:
            lines.append("")
        lines += _table(title, rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_report(path: Path) -> tuple[str, list[tuple[str, str]]]:
    """Read back a report written by write_report: (title, rows)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].removeprefix("# ")
    rows = []
    for ln in lines[4:]:
        k, _, v = ln.strip().strip("|").rpartition(" | ")
        rows.append((k.strip(), v.strip()))
    return title, rows


def headline(rows: list[tuple[str, object]]) -> list[tuple[str, object]]:
    return [(k, v) for k, v in rows if not k.startswith(DETAIL_PREFIXES)]
