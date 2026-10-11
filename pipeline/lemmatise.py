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
_SPLIT = re.compile(r"[\s.,:;()\[\]\"'״׳]+")


def tokenize(text: str) -> list[str]:
    return [w for w in _SPLIT.split(text) if w]


def load_overrides(path: Path) -> dict[str, tuple[str, str | None]]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            stem = (r.get("stem") or "").strip() or None
            out[r["surface"].strip()] = (hebrew_to_syriac(r["root"].strip()), stem)
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
            if surface in overrides:
                root, stem = overrides[surface]
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
