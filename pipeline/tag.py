"""Symbol mentions: match tokens against the kinnuyim seed by surface (with proclitics) or root."""
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aramaic_core.characters import hebrew_to_syriac

from .lemmatise import FINALS
from .lemmatise import proclitic_candidates as strip_proclitics  # one proclitic rule for both stages
from .report import write_report

ROOT = Path(__file__).resolve().parent.parent
NODES = {"ein_sof", "keter", "hokhmah", "binah", "hesed", "gevurah", "tiferet",
         "netzah", "hod", "yesod", "malkhut", "sitra_ahra"}
KINDS = {"person", "object", "quality", "event"}
# a word right after one of these is a sage's name (רבי אבא, ר׳ יצחק), not a symbol
_TITLES = {"רבי", "ר׳", "א״ר", "רב"}
# a double proclitic is only stripped when it is a real sequence; anything else (של+ים, מש+לבן) eats root letters
_DOUBLE_PROCLITICS = {"וד", "וב", "ול", "וכ", "ומ", "דב", "דל", "דכ", "דמ", "וש"}
# only these single proclitics may leave a two-letter remainder (בים, דגן — but not מגן)
_SHORT_OK = set("ובדל")
_NON_WORD_EDGES = re.compile(r"^[^א-ת]+|[^א-ת׳״]+$")

__all__ = ["Symbol", "SeedError", "load_kinnuyim", "strip_proclitics", "tag", "check_seed_roots", "main"]


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
    aliases_root_seed: list[str] = field(default_factory=list)  # Hebrew-script, as written in seed


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
    return hebrew_to_syriac(heb.translate(FINALS))


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
                aliases_root_seed=_split(r["aliases_root"]),
                states=states, seed_source=r["seed_source"],
                states_syriac={k: [_root_key(x) for x in v] for k, v in states.items()}))
            seen.add(r["id"])
    return syms


def _clean(surface: str) -> str:
    """Drop punctuation the tokenizer leaves on word edges (סיהרא?! -> סיהרא)."""
    return _NON_WORD_EDGES.sub("", surface)


def _candidates(surface: str) -> list[str]:
    """strip_proclitics, minus readings that would strip root letters."""
    out = []
    for c in strip_proclitics(surface):
        k = len(surface) - len(c)
        if k == 2 and (surface[:2] not in _DOUBLE_PROCLITICS or len(c) < 3):
            continue
        if k == 1 and len(c) < 3 and surface[0] not in _SHORT_OK:
            continue
        out.append(c)
    return out


def _is_title(surface: str) -> bool:
    return any(c in _TITLES for c in _candidates(_clean(surface)))


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
            if i in covered:  # no match starts inside a longer one already found
                continue
            cands = _candidates(surfaces[i])
            hits = [(words, sid) for words, sid in multi
                    if words[0] in cands and surfaces[i + 1:i + len(words)] == words[1:]]
            if not hits:
                continue
            n = max(len(w) for w, _ in hits)  # longest alias at this start wins
            for words, sid in hits:
                if len(words) == n:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=" ".join(words), via="surface"))
            covered.update(range(i, i + n))
        for i, t in enumerate(toks):
            if i in covered or (i > 0 and _is_title(surfaces[i - 1])):
                continue
            # the longest reading wins: שמיא is Heaven, not ש+מיא
            c = next((c for c in _candidates(surfaces[i]) if c in single), None)
            if c is not None:
                for sid in single[c]:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=c, via="surface"))
            elif t.get("root") and t["root"] in by_root:
                for sid in by_root[t["root"]]:
                    mentions.append(dict(symbol_id=sid, passage_id=pid, position=t["position"],
                                         matched_form=surfaces[i], via="root"))
    mentions.sort(key=lambda m: (m["passage_id"], m["position"], m["symbol_id"]))
    return mentions


def check_seed_roots(tokens: list[dict], symbols: list[Symbol]) -> None:
    """Every seeded alias root and state-marker root must occur among the token roots; a root that
    never occurs is a typo or a wrong transliteration, and would silently match nothing."""
    roots = {t["root"] for t in tokens if t.get("root")}
    bad = []
    for s in symbols:
        bad += [f"{s.id}: alias root {r}" for r in s.aliases_root if r not in roots]
        bad += [f"{s.id}: state {label} marker root {r}"
                for label, rs in s.states_syriac.items() for r in rs if r not in roots]
    if bad:
        raise SeedError("seeded roots never found among token roots: " + "; ".join(bad))


def main(argv=None) -> None:
    work = ROOT / "work"
    with (work / "tokens.jsonl").open(encoding="utf-8") as f:
        tokens = [json.loads(line) for line in f]
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    m = tag(tokens, syms)
    check_seed_roots(tokens, syms)
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
