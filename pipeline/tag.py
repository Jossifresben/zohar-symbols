"""Symbol mentions: match tokens against the kinnuyim seed by surface (with proclitics) or root."""
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aramaic_core.characters import hebrew_to_syriac

from .lemmatise import _FINALS
from .lemmatise import proclitic_candidates as strip_proclitics  # one proclitic rule for both stages
from .report import write_report

ROOT = Path(__file__).resolve().parent.parent
NODES = {"ein_sof", "keter", "hokhmah", "binah", "hesed", "gevurah", "tiferet",
         "netzah", "hod", "yesod", "malkhut", "sitra_ahra"}
KINDS = {"person", "object", "quality", "event"}
# a word right after one of these is a sage's name (רבי אבא, ר׳ יצחק), not a symbol
_TITLES = {"רבי", "ר׳"}
_NON_WORD_EDGES = re.compile(r"^[^א-ת]+|[^א-ת׳״]+$")

__all__ = ["Symbol", "SeedError", "load_kinnuyim", "strip_proclitics", "tag", "main"]


class SeedError(Exception):
    pass


@dataclass
class Symbol:
    id: str
    label_en: str
    label_es: str
    label_ar: str
    kind: str
    node: str
    aliases_surface: list[str]
    aliases_root: list[str]          # Syriac-script canonical roots
    states: dict[str, list[str]]     # label -> Hebrew-script roots (as written in seed)
    seed_source: str
    states_syriac: dict[str, list[str]] = field(default_factory=dict)


def _split(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def _parse_states(s: str) -> dict[str, list[str]]:
    out = {}
    for part in (s or "").split("|"):
        part = part.strip()
        if not part:
            continue
        label, _, roots = part.partition(":")
        out[label.strip()] = [r.strip() for r in roots.split(",") if r.strip()]
    return out


def _root_key(heb: str) -> str:
    """Hebrew-script root -> the Atlas's canonical Syriac key (finals folded first)."""
    return hebrew_to_syriac(heb.translate(_FINALS))


def load_kinnuyim(path: Path) -> list[Symbol]:
    syms, seen = [], set()
    with Path(path).open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["id"] in seen:
                raise SeedError(f"duplicate id {r['id']}")
            if r["node"] not in NODES:
                raise SeedError(f"{r['id']}: unknown node {r['node']}")
            if r["kind"] not in KINDS:
                raise SeedError(f"{r['id']}: unknown kind {r['kind']}")
            surf = _split(r["aliases_surface"])
            if not surf:
                raise SeedError(f"{r['id']}: no surface aliases")
            states = _parse_states(r.get("states", ""))
            syms.append(Symbol(
                id=r["id"], label_en=r["label_en"], label_es=r["label_es"], label_ar=r["label_ar"],
                kind=r["kind"], node=r["node"], aliases_surface=surf,
                aliases_root=[_root_key(x) for x in _split(r["aliases_root"])],
                states=states, seed_source=r["seed_source"],
                states_syriac={k: [_root_key(x) for x in v] for k, v in states.items()}))
            seen.add(r["id"])
    return syms


def _clean(surface: str) -> str:
    """Drop punctuation the tokenizer leaves on word edges (סיהרא?! -> סיהרא)."""
    return _NON_WORD_EDGES.sub("", surface)


def _is_title(surface: str) -> bool:
    return any(c in _TITLES for c in strip_proclitics(_clean(surface)))


def tag(tokens: list[dict], symbols: list[Symbol]) -> list[dict]:
    single: dict[str, list[str]] = {}       # alias word -> [symbol ids]
    multi: list[tuple[list[str], str]] = []  # (alias words, symbol id)
    by_root: dict[str, list[str]] = {}
    for s in symbols:
        for a in s.aliases_surface:
            words = a.split()
            if len(words) == 1:
                single.setdefault(a, []).append(s.id)
            else:
                multi.append((words, s.id))
        for r in s.aliases_root:
            by_root.setdefault(r, []).append(s.id)

    by_passage: dict[str, list[dict]] = {}
    for t in tokens:
        by_passage.setdefault(t["passage_id"], []).append(t)

    mentions = []
    for pid, toks in by_passage.items():
        toks.sort(key=lambda t: t["position"])
        surfaces = [_clean(t["surface"]) for t in toks]
        covered: set[int] = set()  # token indices inside a multi-word match
        for i, t in enumerate(toks):
            cands = strip_proclitics(surfaces[i])
            for words, sid in multi:
                n = len(words)
                if words[0] in cands and surfaces[i + 1:i + n] == words[1:]:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=" ".join(words), via="surface"))
                    covered.update(range(i, i + n))
        for i, t in enumerate(toks):
            if i in covered or (i > 0 and _is_title(surfaces[i - 1])):
                continue
            # the longest reading wins: שמיא is Heaven, not ש+מיא
            c = next((c for c in strip_proclitics(surfaces[i]) if c in single), None)
            if c is not None:
                for sid in single[c]:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=c, via="surface"))
            elif t.get("root") and t["root"] in by_root:
                for sid in by_root[t["root"]]:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=t["surface"], via="root"))
    mentions.sort(key=lambda m: (m["passage_id"], m["position"], m["symbol_id"]))
    return mentions


def main(argv=None) -> None:
    work = ROOT / "work"
    with (work / "tokens.jsonl").open(encoding="utf-8") as f:
        tokens = [json.loads(line) for line in f]
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    m = tag(tokens, syms)
    with (work / "mentions.jsonl").open("w", encoding="utf-8") as f:
        for x in m:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    c = Counter(x["symbol_id"] for x in m)
    via = Counter(x["via"] for x in m)
    rows = [("mentions", len(m)), ("via surface", via["surface"]), ("via root", via["root"]),
            ("symbols with ≥1 mention", len(c)),
            ("symbols with 0 mentions", len([s for s in syms if s.id not in c]))]
    rows += [(f"top #{i+1}: {sid}", n) for i, (sid, n) in enumerate(c.most_common(30))]
    rows += [(f"zero: {s.id}", 0) for s in syms if s.id not in c]
    write_report(work / "tag.report.md", "tag", rows)


if __name__ == "__main__":
    main()
