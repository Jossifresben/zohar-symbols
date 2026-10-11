"""Write data/zohar.sqlite and data/tables.v{N}.json from the stage outputs."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .lemmatise import tokenize
from .report import write_report
from .tag import Symbol, load_kinnuyim
from .version import TABLES_VERSION

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def _marker_roots(sym: dict, s: dict) -> str | None:
    """Comma-joined marker roots, or None if computed.json is stale vs the seed."""
    symbol = sym.get(s["symbol_id"])
    roots = symbol.states.get(s["state_label"]) if symbol else None
    return None if roots is None else ",".join(roots)


def count_stale_states(computed: dict, symbols: list[Symbol]) -> int:
    sym = {s.id: s for s in symbols}
    return sum(1 for s in computed["states"] if _marker_roots(sym, s) is None)


def build(raw: dict, tokens: list[dict], mentions: list[dict], computed: dict,
          symbols: list[Symbol], out_sqlite: Path, out_json: Path) -> None:
    out_sqlite.parent.mkdir(parents=True, exist_ok=True)
    if out_sqlite.exists():
        out_sqlite.unlink()
    con = sqlite3.connect(out_sqlite)
    con.executescript(SCHEMA)
    strata = computed["strata"]
    con.executemany("insert into passage values (?,?,?,?,?,?,?,?,?,?)", [
        (p["id"], p["volume"], p["folio"], p["side"], p["para"], p["parasha"], strata.get(p["id"], "main"),
         p["text_ar"], p.get("verse_ref"), len(tokenize(p["text_ar"]))) for p in raw["passages"]])
    con.executemany("insert into token values (?,?,?,?,?,?,?)", [
        (t["passage_id"], t["position"], t["surface"], t["root"], t["stem"], t["confidence"], t["source"]) for t in tokens])
    counts = computed["symbol_counts"]
    con.executemany("insert into symbol values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        (s.id, s.label_en, s.label_es, s.label_ar, s.kind, s.node, ";".join(s.aliases_surface),
         None, None, None, None, s.seed_source,
         counts.get(s.id, {}).get("raw", 0), counts.get(s.id, {}).get("resolved", 0), counts.get(s.id, {}).get("passages", 0))
        for s in symbols])
    con.executemany("insert into mention values (?,?,?,?,?)", [
        (m["symbol_id"], m["passage_id"], m["position"], m["matched_form"], m["via"]) for m in mentions])
    con.executemany("insert into cooccurrence values (?,?,?,?,?)", [
        (c["a"], c["b"], c["passages_together"], c["pmi"], TABLES_VERSION) for c in computed["cooccurrence"]])
    sym = {s.id: s for s in symbols}
    con.executemany("insert or ignore into state values (?,?,?,?)", [
        (s["symbol_id"], s["state_label"], _marker_roots(sym, s) or "", s["passage_id"])
        for s in computed["states"]])
    con.executemany("insert into surfaced values (?,?,?)", [
        (sid, i, pid) for sid, pids in computed["surfaced"].items() for i, pid in enumerate(pids)])
    con.executemany("insert into meta values (?,?)", [
        ("tables_version", TABLES_VERSION),
        ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ("source_revids", json.dumps([p["revid"] for p in raw["pages"]])),
    ])
    con.commit()
    con.close()
    j = dict(computed)
    j["tables_version"] = TABLES_VERSION
    j["symbols"] = [dict(id=s.id, label_en=s.label_en, label_es=s.label_es, label_ar=s.label_ar, kind=s.kind,
                         node=s.node, aliases=s.aliases_surface, seed_source=s.seed_source) for s in symbols]
    out_json.write_text(json.dumps(j, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def main(argv=None) -> None:
    work = ROOT / "work"
    raw = json.loads((ROOT / "raw" / f"zohar.v{TABLES_VERSION}.json").read_text(encoding="utf-8"))
    tokens = [json.loads(l) for l in (work / "tokens.jsonl").open(encoding="utf-8")]
    mentions = [json.loads(l) for l in (work / "mentions.jsonl").open(encoding="utf-8")]
    computed = json.loads((work / "computed.json").read_text(encoding="utf-8"))
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    out_sqlite = ROOT / "data" / "zohar.sqlite"
    build(raw, tokens, mentions, computed, syms, out_sqlite, ROOT / "data" / f"tables.v{TABLES_VERSION}.json")
    write_report(ROOT / "data" / "report.md", f"build {TABLES_VERSION}", [
        ("passages", len(raw["passages"])), ("tokens", len(tokens)), ("mentions", len(mentions)),
        ("symbols", len(syms)), ("pairs", len(computed["cooccurrence"])),
        ("tokens with root", sum(1 for t in tokens if t["root"])),
        ("state rows", len(computed["states"])),
        ("state rows stale vs seed (marker_roots empty)", count_stale_states(computed, syms)),
    ])


if __name__ == "__main__":
    main()
