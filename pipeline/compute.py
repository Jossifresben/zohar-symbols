# pipeline/compute.py
"""Deterministic tables: co-occurrence, states, strata, surfaced passages, resolved counts."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from .report import write_report
from .tag import Symbol, load_kinnuyim
from .version import TABLES_VERSION

ROOT = Path(__file__).resolve().parent.parent


def load_strata(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    for r in csv.DictReader(lines, delimiter="\t"):
        rows.append(dict(volume=int(r["volume"]), from_folio=int(r["from_folio"]), from_side=r["from_side"],
                         to_folio=int(r["to_folio"]), to_side=r["to_side"], stratum=r["stratum"]))
    return rows


def _key(folio: int, side: str) -> int:
    return folio * 2 + (0 if side == "a" else 1)


def assign_strata(passages: list[dict], rows: list[dict]) -> dict[str, str]:
    out = {}
    for p in passages:
        k = _key(p["folio"], p["side"])
        s = "main"
        for r in rows:
            if r["volume"] == p["volume"] and _key(r["from_folio"], r["from_side"]) <= k <= _key(r["to_folio"], r["to_side"]):
                s = r["stratum"]
                break
        out[p["id"]] = s
    return out


def _symbols_by_passage(mentions: list[dict]) -> dict[str, set[str]]:
    d = defaultdict(set)
    for m in mentions:
        d[m["passage_id"]].add(m["symbol_id"])
    return d


def cooccurrence(mentions: list[dict]) -> list[dict]:
    sbp = _symbols_by_passage(mentions)
    n = len(sbp)
    single = Counter()
    pair = Counter()
    for syms in sbp.values():
        for s in syms:
            single[s] += 1
        for a, b in combinations(sorted(syms), 2):
            pair[(a, b)] += 1
    out = []
    for (a, b), c in sorted(pair.items()):
        pmi = math.log2((c / n) / ((single[a] / n) * (single[b] / n))) if n else 0.0
        out.append(dict(a=a, b=b, passages_together=c, pmi=round(pmi, 4)))
    return out


def detect_states(mentions: list[dict], tokens: list[dict], symbols: list[Symbol]) -> list[dict]:
    roots_by_passage = defaultdict(set)
    for t in tokens:
        if t.get("root"):
            roots_by_passage[t["passage_id"]].add(t["root"])
    sym = {s.id: s for s in symbols}
    seen = set()
    out = []
    for m in mentions:
        s = sym[m["symbol_id"]]
        for label, roots in s.states_syriac.items():
            if (s.id, label, m["passage_id"]) in seen:
                continue
            if roots_by_passage[m["passage_id"]] & set(roots):
                out.append(dict(symbol_id=s.id, state_label=label, passage_id=m["passage_id"]))
                seen.add((s.id, label, m["passage_id"]))
    out.sort(key=lambda x: (x["symbol_id"], x["state_label"], x["passage_id"]))
    return out


def _top_partners(symbol_id: str, cooc: list[dict], k: int = 3) -> list[str]:
    rows = [(c["b"] if c["a"] == symbol_id else c["a"], c["passages_together"])
            for c in cooc if symbol_id in (c["a"], c["b"])]
    rows.sort(key=lambda x: (-x[1], x[0]))
    return [r[0] for r in rows[:k]]


def surfaced_passages(symbol_id: str, mentions: list[dict], cooc: list[dict],
                      tokens_by_passage: dict[str, list[dict]], strata: dict[str, str], k: int = 6) -> list[str]:
    partners = set(_top_partners(symbol_id, cooc))
    score = Counter()
    for m in mentions:
        if m["symbol_id"] == symbol_id:
            score[m["passage_id"]] += 2
        elif m["symbol_id"] in partners:
            score[m["passage_id"]] += 1
    cands = [pid for pid in score if any(m["symbol_id"] == symbol_id and m["passage_id"] == pid for m in mentions)]
    dens = {pid: score[pid] / max(1, len(tokens_by_passage.get(pid, []))) for pid in cands}
    ranked = sorted(cands, key=lambda pid: (-dens[pid], pid))
    chosen, used_strata = [], set()
    for pid in ranked:                      # one per stratum first
        st = strata.get(pid, "main")
        if st not in used_strata:
            chosen.append(pid)
            used_strata.add(st)
        if len(chosen) == k:
            return chosen
    for pid in ranked:                      # then fill by density
        if pid not in chosen:
            chosen.append(pid)
        if len(chosen) == k:
            break
    return chosen


def resolve_counts(mentions: list[dict], cooc: list[dict], symbols: list[Symbol]) -> dict:
    sym = {s.id: s for s in symbols}
    # alias word -> symbols sharing it
    shared = defaultdict(set)
    for s in symbols:
        for a in s.aliases_surface:
            shared[a].add(s.id)
    support = defaultdict(int)             # (symbol, passage) -> partner support
    sbp = _symbols_by_passage(mentions)
    pt = {(c["a"], c["b"]): c["passages_together"] for c in cooc}
    for pid, syms in sbp.items():
        for s in syms:
            support[(s, pid)] = sum(pt.get(tuple(sorted((s, o))), 0) for o in syms if o != s)
    raw, resolved, passages = Counter(), Counter(), defaultdict(set)
    for m in mentions:
        s = m["symbol_id"]
        raw[s] += 1
        passages[s].add(m["passage_id"])
        rivals = shared.get(m["matched_form"], set()) - {s}
        if rivals and any(support[(r, m["passage_id"])] > support[(s, m["passage_id"])] for r in rivals):
            continue
        resolved[s] += 1
    return {s.id: dict(raw=raw[s.id], resolved=resolved[s.id], passages=len(passages[s.id])) for s in symbols}


def main(argv=None) -> None:
    work = ROOT / "work"
    raw = json.loads((ROOT / "raw" / f"zohar.v{TABLES_VERSION}.json").read_text(encoding="utf-8"))
    tokens = [json.loads(l) for l in (work / "tokens.jsonl").open(encoding="utf-8")]
    mentions = [json.loads(l) for l in (work / "mentions.jsonl").open(encoding="utf-8")]
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    strata = assign_strata(raw["passages"], load_strata(ROOT / "seeds" / "strata.tsv"))
    cooc = cooccurrence(mentions)
    tbp = defaultdict(list)
    for t in tokens:
        tbp[t["passage_id"]].append(t)
    out = dict(
        tables_version=TABLES_VERSION,
        cooccurrence=cooc,
        symbol_counts=resolve_counts(mentions, cooc, syms),
        states=detect_states(mentions, tokens, syms),
        strata=dict(sorted(strata.items())),
        surfaced={s.id: surfaced_passages(s.id, mentions, cooc, tbp, strata) for s in sorted(syms, key=lambda s: s.id)},
    )
    (work / "computed.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    write_report(work / "compute.report.md", "compute", [
        ("pairs", len(cooc)), ("states", len(out["states"])),
        ("strata", dict(Counter(strata.values()))),
        ("symbols with < 6 surfaced", sum(1 for v in out["surfaced"].values() if len(v) < 6)),
    ])


if __name__ == "__main__":
    main()
