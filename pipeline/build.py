"""Write data/zohar.sqlite and data/tables.v{N}.json from the stage outputs."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .lemmatise import tokenize
from .report import headline, read_report, write_sections
from .tag import Symbol, load_kinnuyim
from . import translations
from .version import TABLES_VERSION

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def _marker_roots(sym: dict, s: dict) -> str | None:
    """Comma-joined marker roots, or None if computed.json is stale vs the seed."""
    symbol = sym.get(s["symbol_id"])
    roots = symbol.states.get(s["state_label"]) if symbol else None
    return None if roots is None else ",".join(roots)


def aliases_field(s: Symbol) -> str:
    """symbol.aliases: "surface1;surface2|root1;root2"."""
    return ";".join(s.aliases_surface) + "|" + ";".join(s.aliases_root_seed)


def count_stale_states(computed: dict, symbols: list[Symbol]) -> int:
    sym = {s.id: s for s in symbols}
    return sum(1 for s in computed["states"] if _marker_roots(sym, s) is None)


def build(raw: dict, tokens: list[dict], mentions: list[dict], computed: dict,
          symbols: list[Symbol], out_sqlite: Path, out_json: Path,
          translations: list[tuple] | None = None, interpretations: list[tuple] | None = None) -> None:
    out_sqlite.parent.mkdir(parents=True, exist_ok=True)
    if out_sqlite.exists():
        out_sqlite.unlink()
    con = sqlite3.connect(out_sqlite)
    con.executescript(SCHEMA)
    strata = computed["strata"]
    con.executemany("insert into passage values (?,?,?,?,?,?,?,?,?,?,?)", [
        (p["id"], p["volume"], p["folio"], p["side"], p["para"], p["parasha"], p.get("stream", "main"),
         strata.get(p["id"], "main"),
         p["text_ar"], p.get("verse_ref"), len(tokenize(p["text_ar"]))) for p in raw["passages"]])
    con.executemany("insert into token values (?,?,?,?,?,?,?)", [
        (t["passage_id"], t["position"], t["surface"], t["root"], t["stem"], t["confidence"], t["source"]) for t in tokens])
    counts = computed["symbol_counts"]
    con.executemany("insert into symbol values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        (s.id, s.label_en, s.label_es, s.label_ar, s.kind, s.node, aliases_field(s),
         None, None, None, None, s.seed_source,
         counts.get(s.id, {}).get("raw", 0), counts.get(s.id, {}).get("resolved", 0), counts.get(s.id, {}).get("passages", 0))
        for s in symbols])
    con.executemany("insert into mention values (?,?,?,?,?)", [
        (m["symbol_id"], m["passage_id"], m["position"], m["matched_form"], m["via"]) for m in mentions])
    con.executemany("insert into cooccurrence values (?,?,?,?,?)", [
        (c["a"], c["b"], c["passages_together"], c["pmi"], TABLES_VERSION) for c in computed["cooccurrence"]])
    sym = {s.id: s for s in symbols}
    con.executemany("insert into state_decl values (?,?,?)", [
        (s.id, label, ",".join(roots)) for s in symbols for label, roots in s.states.items()])
    con.executemany("insert into state values (?,?,?,?)", [
        (s["symbol_id"], s["state_label"], _marker_roots(sym, s) or "", s["passage_id"])
        for s in computed["states"]])
    con.executemany("insert into surfaced values (?,?,?)", [
        (sid, i, pid) for sid, pids in computed["surfaced"].items() for i, pid in enumerate(pids)])
    con.executemany("insert into translation values (?,?,?,?,?,?)", translations or [])
    con.executemany("insert into interpretation values (?,?,?,?,?,?)", interpretations or [])
    con.executemany("insert into meta values (?,?)", [
        ("tables_version", TABLES_VERSION),
        ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ("source_revids", json.dumps([p["revid"] for p in raw["pages"]])),
    ])
    bad = con.execute("pragma foreign_key_check").fetchall()
    if bad:
        raise ValueError(f"foreign key violations: {bad[:5]} ({len(bad)} total)")
    con.commit()
    con.close()
    j = dict(computed)
    j["tables_version"] = TABLES_VERSION
    j["symbols"] = [dict(id=s.id, label_en=s.label_en, label_es=s.label_es, label_ar=s.label_ar, kind=s.kind,
                         node=s.node, aliases=s.aliases_surface, aliases_root=s.aliases_root_seed,
                         states=s.states, seed_source=s.seed_source) for s in symbols]
    out_json.write_text(json.dumps(j, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def main(argv=None) -> None:
    work = ROOT / "work"
    raw = json.loads((ROOT / "raw" / f"zohar.v{TABLES_VERSION}.json").read_text(encoding="utf-8"))
    tokens = [json.loads(l) for l in (work / "tokens.jsonl").open(encoding="utf-8")]
    mentions = [json.loads(l) for l in (work / "mentions.jsonl").open(encoding="utf-8")]
    computed = json.loads((work / "computed.json").read_text(encoding="utf-8"))
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    out_sqlite = ROOT / "data" / "zohar.sqlite"
    tr_rows, tr_stats = translations.load(ROOT / "data" / f"translations.v{TABLES_VERSION}.jsonl",
                                          ROOT / "data" / "translation_overrides.tsv", raw["passages"])
    in_rows, in_stats = translations.load(ROOT / "data" / f"interpretations.v{TABLES_VERSION}.jsonl",
                                          ROOT / "data" / "interpretation_overrides.tsv", raw["passages"],
                                          kind="interpretations")
    build(raw, tokens, mentions, computed, syms, out_sqlite, ROOT / "data" / f"tables.v{TABLES_VERSION}.json",
          translations=tr_rows, interpretations=in_rows)
    build_rows = [
        ("passages", len(raw["passages"])), ("tokens", len(tokens)), ("mentions", len(mentions)),
        ("symbols", len(syms)), ("pairs", len(computed["cooccurrence"])),
        ("tokens with root", sum(1 for t in tokens if t["root"])),
        ("non-lexical by override (empty root)", sum(1 for t in tokens if not t["root"] and t["source"] == "override")),
        ("no root, unknown", sum(1 for t in tokens if not t["root"] and t["source"] != "override")),
        ("confidence ≥ 0.8", sum(1 for t in tokens if t["confidence"] >= 0.8)),
        ("state rows", len(computed["states"])),
        ("state rows stale vs seed (marker_roots empty)", count_stale_states(computed, syms)),
        ("declared states", sum(len(s.states) for s in syms)),
        *tr_stats.items(),
        *in_stats.items(),
    ]
    # raw/ and work/ are not committed: their headline rows travel with the tables in data/report.md
    stages = [ROOT / "raw" / "report.md", work / "lemmatise.report.md", work / "tag.report.md",
              work / "compute.report.md"]
    sections = [(f"build {TABLES_VERSION}", build_rows)]
    for path in stages:
        title, rows = read_report(path)
        sections.append((title, headline(rows)))
    write_sections(ROOT / "data" / "report.md", sections)


if __name__ == "__main__":
    main()
