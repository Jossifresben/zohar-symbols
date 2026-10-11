"""Two runs over the fixture must produce byte-identical tables.json (Review Focus #5)."""
import json
from pathlib import Path
from pipeline.segment import segment_page
from pipeline.lemmatise import lemmatise, load_overrides
from pipeline.tag import load_kinnuyim, tag
from pipeline.compute import compute_all
from pipeline.build import build

ROOT = Path(__file__).parent.parent


def _run(tmp: Path) -> bytes:
    fix = (Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8")
    passages = [p.__dict__ for p in segment_page(fix, 1, "Bereshit", "t")]
    raw = {"pages": [{"title": "t", "revid": 1}], "passages": passages}
    tokens = lemmatise(passages, load_overrides(ROOT / "seeds" / "zohar_overrides.tsv"), ROOT / "vendor" / "atlas_roots", tmp / "w")
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    mentions = tag(tokens, syms)
    computed = compute_all(raw, tokens, mentions, syms)
    build(raw, tokens, mentions, computed, syms, tmp / "z.sqlite", tmp / "t.json")
    return (tmp / "t.json").read_bytes()


def test_determinism(tmp_path):
    assert _run(tmp_path / "a") == _run(tmp_path / "b")
