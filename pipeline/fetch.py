# pipeline/fetch.py
"""Fetch every parasha page from Wikisource and segment into passages."""
import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .report import write_report
from .segment import segment_page
from .version import TABLES_VERSION
from .wikisource import PageText, fetch_page

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"


def load_parashot(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        r["volume"] = int(r["volume"])
    return rows


def build_raw(pages: list[tuple[str, int, str, PageText]]) -> dict:
    """Segment pages in order. A Mantua folio may straddle two parasha pages;
    the later page's paragraphs continue the numbering (recorded in split_folios)."""
    out = {"tables_version": TABLES_VERSION,
           "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "pages": [], "passages": [], "split_folios": 0, "continued_folios": 0}
    max_para: dict[tuple[int, int, str], int] = {}
    split: set[tuple[int, int, str]] = set()
    for title, volume, parasha, pt in pages:
        out["pages"].append({"title": title, "revid": pt.revid, "timestamp": pt.timestamp,
                             "volume": volume, "parasha": parasha})
        stats: dict = {}
        passages = [asdict(p) for p in segment_page(pt.wikitext, volume, parasha, title, stats)]
        out["continued_folios"] += stats.get("continued", 0)
        offsets = {}
        for p in passages:
            key = (p["volume"], p["folio"], p["side"])
            if key not in offsets:
                offsets[key] = max_para.get(key, 0)
                if offsets[key]:
                    split.add(key)
            if offsets[key]:
                p["para"] += offsets[key]
                p["id"] = f"{p['volume']}.{p['folio']:03d}{p['side']}.{p['para']:02d}"
        for p in passages:
            key = (p["volume"], p["folio"], p["side"])
            max_para[key] = max(max_para.get(key, 0), p["para"])
        out["passages"] += passages
    out["split_folios"] = len(split)
    return out


def write_sources_md(out: dict, path: Path) -> None:
    lines = ["# Sources", "", f"Fetched {out['fetched_at']} from https://he.wikisource.org (CC BY-SA 4.0).", "",
             "| page | revid | timestamp |", "|---|---|---|"]
    lines += [f"| {p['title']} | {p['revid']} | {p['timestamp']} |" for p in out["pages"]]
    lines += ["", "זוהר השמטות excluded in v0.1: folios span volumes."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None, help="fetch only the first N parasha pages")
    args = ap.parse_args(argv)
    rows = load_parashot(ROOT / "seeds" / "parashot.tsv")
    if args.only:
        rows = rows[:args.only]
    pages = [(r["page_title"], r["volume"], r["parasha"], fetch_page(r["page_title"], RAW / "cache"))
             for r in rows]
    out = build_raw(pages)
    RAW.mkdir(exist_ok=True)
    (RAW / f"zohar.v{TABLES_VERSION}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    write_sources_md(out, DATA / "SOURCES.md")
    folios = {(p["volume"], p["folio"], p["side"]) for p in out["passages"]}
    write_report(RAW / "report.md", "fetch", [
        ("pages", len(out["pages"])), ("folios", len(folios)), ("passages", len(out["passages"])),
        ("empty passages", sum(1 for p in out["passages"] if not p["text_ar"])),
        ("folios split across pages", out["split_folios"]),
        ("folios continued within a page", out["continued_folios"]),
    ])


if __name__ == "__main__":
    main()
