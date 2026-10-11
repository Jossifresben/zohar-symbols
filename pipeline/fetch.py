# pipeline/fetch.py
"""Fetch every parasha page from Wikisource and segment into passages."""
import argparse
import csv
import json
import shutil
from collections import Counter
from statistics import median
from dataclasses import asdict
from pathlib import Path

from .lemmatise import tokenize
from .report import write_report
from .segment import STREAMS, _stream_key, renumber, segment_page
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
    """Segment pages in order, then number paragraphs per folio-side over all pages (main stream
    first, then the other streams; see segment.renumber). A folio-side stream that straddles two
    parasha pages continues on the later page (split_detail); within-page repeats: continued_detail."""
    out = {"tables_version": TABLES_VERSION,
           "pages": [], "passages": [], "split_folios": 0, "continued_folios": 0, "placeholders": 0,
           "split_detail": {}, "continued_detail": {}}
    texts: dict[tuple, set[str]] = {}
    first_page: dict[tuple, str] = {}
    for title, volume, parasha, pt in pages:
        out["pages"].append({"title": title, "revid": pt.revid, "timestamp": pt.timestamp,
                             "volume": volume, "parasha": parasha})
        stats: dict = {}
        passages = [asdict(p) for p in segment_page(pt.wikitext, volume, parasha, title, stats)]
        out["continued_folios"] += stats.get("continued", 0)
        out["placeholders"] += stats.get("placeholders", 0)
        out["continued_detail"].update(stats.get("continued_keys", {}))
        for p in passages:
            key = (p["volume"], p["folio"], p["side"], p["stream"])
            if first_page.setdefault(key, title) != title:
                out["split_detail"][_stream_key(*key)] = f"{first_page[key]} → {title}"
                if p["text_ar"] in texts[key]:
                    raise ValueError(f"{title}: {_stream_key(*key)}: duplicate text in repeated section")
        for p in passages:
            texts.setdefault((p["volume"], p["folio"], p["side"], p["stream"]), set()).add(p["text_ar"])
        out["passages"] += passages
    renumber(out["passages"])
    out["split_folios"] = len(out["split_detail"])
    out["sources_as_of"] = max((p["timestamp"] for p in out["pages"]), default="")
    return out


def write_sources_md(out: dict, path: Path) -> None:
    lines = ["# Sources", "", f"Source revisions as of {out['sources_as_of']} from https://he.wikisource.org (CC BY-SA 4.0).", "",
             "| page | revid | timestamp |", "|---|---|---|"]
    lines += [f"| {p['title']} | {p['revid']} | {p['timestamp']} |" for p in out["pages"]]
    lines += ["", "`parasha` is a page-level label: a Wikisource parasha page may cover several parashot "
              "or an inserted unit (Idra, Sitrei Torah).", "", "זוהר השמטות excluded in v0.1: folios span volumes."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def size_outliers(passages: list[dict], factor: int = 3) -> list[tuple[str, str]]:
    """Folio-sides (all streams) whose paragraph or token count exceeds factor × the corpus median:
    the signature of two folios merged under one label, or of a missed section boundary."""
    paras, toks = Counter(), Counter()
    for p in passages:
        k = f"{p['volume']}.{p['folio']:03d}{p['side']}"
        paras[k] += 1
        toks[k] += len(tokenize(p["text_ar"]))
    if not paras:
        return []
    mp, mt = median(paras.values()), median(toks.values())
    return [(f"size outlier: {k}", f"{paras[k]} paras, {toks[k]} tokens") for k in sorted(paras)
            if paras[k] > factor * mp or toks[k] > factor * mt]


def report_rows(out: dict) -> list[tuple[str, object]]:
    folios = {(p["volume"], p["folio"], p["side"]) for p in out["passages"]}
    rows: list[tuple[str, object]] = [
        ("pages", len(out["pages"])), ("folios", len(folios)), ("passages", len(out["passages"])),
        ("empty passages", sum(1 for p in out["passages"] if not p["text_ar"])),
        ("folios split across pages", out["split_folios"]),
        ("folios continued within a page", out["continued_folios"]),
        ("placeholder sections dropped", out.get("placeholders", 0)),
    ]
    streams = Counter(p.get("stream", "main") for p in out["passages"])
    rows += [(f"passages: {s}", streams[s]) for s in STREAMS if streams[s]]
    rows += size_outliers(out["passages"])
    rows += [(f"continued: {k}", n) for k, n in out["continued_detail"].items()]
    rows += [(f"split across pages: {k}", v) for k, v in out["split_detail"].items()]
    return rows


LOCKFILE = ROOT / "seeds" / "wikisource_revisions.json"


def load_lock(path: Path) -> dict[str, int]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_lock(path: Path, lock: dict[str, int]) -> None:
    path.write_text(json.dumps(dict(sorted(lock.items())), ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def fetch_locked(titles: list[str], cache_dir: Path, lock_path: Path, refetch: bool = False,
                 session=None) -> list[PageText]:
    """Fetch each title at its locked revision. A title missing from the lockfile is fetched at its
    latest revision and added. refetch clears the cache and re-locks every title to its latest."""
    old = load_lock(lock_path)
    if refetch:
        shutil.rmtree(cache_dir, ignore_errors=True)
    lock = {k: v for k, v in old.items() if k not in titles} if refetch else dict(old)
    out = []
    for t in titles:
        pt = fetch_page(t, cache_dir, session=session, revid=lock.get(t))
        lock[t] = pt.revid
        out.append(pt)
    if lock != old:
        write_lock(lock_path, lock)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None, help="fetch only the first N parasha pages")
    ap.add_argument("--refetch", action="store_true",
                    help="clear the cache and lock every page to its latest revision")
    args = ap.parse_args(argv)
    rows = load_parashot(ROOT / "seeds" / "parashot.tsv")
    if args.only:
        rows = rows[:args.only]
    texts = fetch_locked([r["page_title"] for r in rows], RAW / "cache", LOCKFILE, args.refetch)
    pages = [(r["page_title"], r["volume"], r["parasha"], pt) for r, pt in zip(rows, texts)]
    out = build_raw(pages)
    RAW.mkdir(exist_ok=True)
    (RAW / f"zohar.v{TABLES_VERSION}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    write_sources_md(out, DATA / "SOURCES.md")
    write_report(RAW / "report.md", "fetch", report_rows(out))


if __name__ == "__main__":
    main()
