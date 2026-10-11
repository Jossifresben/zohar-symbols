"""Tokens with roots: aramaic_core's extractor, overridden by seeds/zohar_overrides.tsv."""
import argparse
import csv
import json
import re
from pathlib import Path

from aramaic_core import AramaicCorpus, RootExtractor
from aramaic_core.characters import hebrew_to_syriac

from .report import write_report
from .version import TABLES_VERSION

ROOT = Path(__file__).resolve().parent.parent
_HEB = "\u05d0-\u05ea"
_HEB_RE = re.compile(f"[{_HEB}]")
_SPLIT = re.compile(r"[\s.,:;()\[\]\"'\u05f4\u05f3]+")
# a quote mark flanked by Hebrew letters is intra-word (gershayim); a single
# trailing geresh after a Hebrew letter (ר', ר׳) belongs to the word too
_GERSHAYIM = re.compile(f"(?<=[{_HEB}])[\"\u05f4](?=[{_HEB}])")
_GERESH = re.compile(f"(?<=[{_HEB}])['\u05f3](?![{_HEB}])")
_PROCLITICS = "ודבלכמש"
FINALS = str.maketrans("ךםןףץ", "כמנפצ")


def tokenize(text: str) -> list[str]:
    """Split into words; keep Hebrew abbreviation marks (gershayim/geresh) inside words,
    normalised to ״ and ׳; drop tokens with no Hebrew letter."""
    text = _GERSHAYIM.sub("\ue000", text)  # private-use placeholders survive the split
    text = _GERESH.sub("\ue001", text)
    out = []
    for w in _SPLIT.split(text):
        w = w.replace("\ue000", "\u05f4").replace("\ue001", "\u05f3")
        if w and _HEB_RE.search(w):
            out.append(w)
    return out


def proclitic_candidates(surface: str) -> list[str]:
    """The surface itself, then with one and two leading proclitics stripped (remainder >= 2 chars)."""
    cands = [surface]
    if len(surface) >= 3 and surface[0] in _PROCLITICS:
        cands.append(surface[1:])
        if len(surface) >= 4 and surface[1] in _PROCLITICS:
            cands.append(surface[2:])
    return cands


def load_overrides(path: Path) -> dict[str, tuple[str | None, str | None]]:
    """surface -> (canonical Syriac root or None for a known non-lexical token, stem)."""
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            surface = r["surface"].strip()
            if surface in out:
                raise ValueError(f"duplicate override surface: {surface!r}")
            raw_root = (r.get("root") or "").strip().translate(FINALS)
            root = hebrew_to_syriac(raw_root) if raw_root else None
            if root is not None and not all("\u0700" <= ch <= "\u074f" for ch in root):
                raise ValueError(f"override root for {surface!r} is not pure Syriac: {raw_root!r}")
            if raw_root and (root is None or len(root) != len(raw_root)):
                raise ValueError(f"override root for {surface!r} has unconvertible letters: {raw_root!r}")
            stem = (r.get("stem") or "").strip() or None
            out[surface] = (root, stem)
    return out


def _write_atlas_csv(passages: list[dict], path: Path) -> None:
    """aramaic_core reads corpora as CSV: book_order,book,chapter,verse,reference,syriac."""
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["book_order", "book", "chapter", "verse", "reference", "syriac"])
        for i, p in enumerate(passages):
            w.writerow([1, "Zohar", 1, i + 1, p["id"], p["text_ar"]])


def lemmatise(passages: list[dict], overrides: dict, data_dir: Path, tmp_dir: Path) -> list[dict]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tmp_dir / "zohar_atlas.csv"
    _write_atlas_csv(passages, csv_path)
    corpus = AramaicCorpus()
    corpus.add_corpus("zohar", "Zohar", str(csv_path))
    ex = RootExtractor(corpus, data_dir=str(data_dir))
    ex.build_index()
    tokens = []
    for p in passages:
        for pos, surface in enumerate(tokenize(p["text_ar"])):
            hit = next((c for c in proclitic_candidates(surface) if c in overrides), None)
            if hit is not None:
                root, stem = overrides[hit]
                tokens.append(dict(passage_id=p["id"], position=pos, surface=surface, root=root,
                                   stem=stem, confidence=1.0, source="override"))
                continue
            rc = ex.lookup_word_root_with_confidence(surface)
            if rc is None:
                tokens.append(dict(passage_id=p["id"], position=pos, surface=surface, root=None,
                                   stem=None, confidence=0.0, source="none"))
            else:
                tokens.append(dict(passage_id=p["id"], position=pos, surface=surface, root=rc[0],
                                   stem=ex.lookup_word_stem(surface), confidence=float(rc[1]),
                                   source="aramaic_core"))
    return tokens


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "raw" / f"zohar.v{TABLES_VERSION}.json"))
    args = ap.parse_args(argv)
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    overrides = load_overrides(ROOT / "seeds" / "zohar_overrides.tsv")
    work = ROOT / "work"
    toks = lemmatise(raw["passages"], overrides, ROOT / "vendor" / "atlas_roots", work / "tmp")
    with (work / "tokens.jsonl").open("w", encoding="utf-8") as f:
        for t in toks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    from collections import Counter
    low = Counter(t["surface"] for t in toks if t["confidence"] < 0.5)
    rows = [("tokens", len(toks)),
            ("with root", sum(1 for t in toks if t["root"])),
            ("override", sum(1 for t in toks if t["source"] == "override")),
            ("confidence ≥ 0.8", sum(1 for t in toks if t["confidence"] >= 0.8)),
            ("confidence < 0.5", sum(1 for t in toks if t["confidence"] < 0.5))]
    rows += [(f"low-conf #{i+1}: {s}", n) for i, (s, n) in enumerate(low.most_common(50))]
    write_report(work / "lemmatise.report.md", "lemmatise", rows)


if __name__ == "__main__":
    main()
