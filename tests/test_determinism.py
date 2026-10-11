"""Two runs over the fixture must produce byte-identical tables.json (Review Focus #5)."""
import json
from pathlib import Path
from pipeline.segment import segment_page
from pipeline.lemmatise import lemmatise, load_overrides
from pipeline.tag import load_kinnuyim, tag
from pipeline.compute import cooccurrence, detect_states, assign_strata, surfaced_passages, resolve_counts, load_strata
from pipeline.build import build

ROOT = Path(__file__).parent.parent


def _run(tmp: Path) -> bytes:
    fix = (Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8")
    passages = [p.__dict__ for p in segment_page(fix, 1, "Bereshit", "t")]
    raw = {"pages": [{"title": "t", "revid": 1}], "passages": passages}
    tokens = lemmatise(passages, load_overrides(ROOT / "seeds" / "zohar_overrides.tsv"), ROOT / "vendor" / "atlas_roots", tmp / "w")
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    mentions = tag(tokens, syms)
    cooc = cooccurrence(mentions, len(passages))
    strata = assign_strata(passages, load_strata(ROOT / "seeds" / "strata.tsv"))
    tbp = {}
    for t in tokens:
        tbp.setdefault(t["passage_id"], []).append(t)
    computed = dict(cooccurrence=cooc, symbol_counts=resolve_counts(mentions, cooc, syms),
                    states=detect_states(mentions, tokens, syms), strata=strata,
                    surfaced={s.id: surfaced_passages(s.id, mentions, cooc, tbp, strata) for s in syms})
    build(raw, tokens, mentions, computed, syms, tmp / "z.sqlite", tmp / "t.json")
    return (tmp / "t.json").read_bytes()


def test_determinism(tmp_path):
    assert _run(tmp_path / "a") == _run(tmp_path / "b")
