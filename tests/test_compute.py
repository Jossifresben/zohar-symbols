# tests/test_compute.py
import json
from pathlib import Path
from aramaic_core.characters import hebrew_to_syriac
from pipeline.segment import segment_page
from pipeline.lemmatise import tokenize
from pipeline.tag import load_kinnuyim, tag
from pipeline.compute import cooccurrence, detect_states, assign_strata, surfaced_passages, resolve_counts, load_strata

FIXD = Path(__file__).parent / "fixtures"
SEEDS = Path(__file__).parent.parent / "seeds"


def _pipeline():
    ps = segment_page((FIXD / "bereshit_20a.wikitext").read_text(encoding="utf-8"), 1, "Bereshit", "t")
    passages = [p.__dict__ for p in ps]
    roots = {"ואזעירי": hebrew_to_syriac("זער")}
    tokens = [dict(passage_id=p["id"], position=i, surface=w, root=roots.get(w), stem=None,
                   confidence=0.9 if w in roots else 0.0, source="x")
              for p in passages for i, w in enumerate(tokenize(p["text_ar"]))]
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    return passages, tokens, syms, tag(tokens, syms)


def test_cooccurrence_matches_hand_count():
    exp = json.loads((FIXD / "expected_20a.json").read_text(encoding="utf-8"))
    _, _, _, mentions = _pipeline()
    got = {(c["a"], c["b"]): c["passages_together"] for c in cooccurrence(mentions)}
    for e in exp["cooccurrence"]:
        assert got[(e["a"], e["b"])] == e["passages_together"], e
    assert all(c["a"] < c["b"] for c in cooccurrence(mentions))


def test_states_detected_by_marker_root():
    exp = json.loads((FIXD / "expected_20a.json").read_text(encoding="utf-8"))
    _, tokens, syms, mentions = _pipeline()
    got = [s for s in detect_states(mentions, tokens, syms) if s["symbol_id"] == "moon"]
    assert got == exp["states"]


def test_strata_assignment():
    rows = load_strata(SEEDS / "strata.tsv")
    passages = [dict(id="3.130a.01", volume=3, folio=130, side="a"),
                dict(id="1.020a.01", volume=1, folio=20, side="a"),
                dict(id="3.145a.02", volume=3, folio=145, side="a"),
                dict(id="3.145b.01", volume=3, folio=145, side="b")]
    s = assign_strata(passages, rows)
    assert s["3.130a.01"] == "idra_rabba" and s["1.020a.01"] == "main"
    assert s["3.145a.02"] == "idra_rabba" and s["3.145b.01"] == "main"


def test_surfaced_is_deterministic_and_bounded():
    passages, tokens, syms, mentions = _pipeline()
    cooc = cooccurrence(mentions)
    tbp = {}
    for t in tokens:
        tbp.setdefault(t["passage_id"], []).append(t)
    strata = {p["id"]: "main" for p in passages}
    a = surfaced_passages("moon", mentions, cooc, tbp, strata, k=6)
    b = surfaced_passages("moon", mentions, cooc, tbp, strata, k=6)
    assert a == b and 0 < len(a) <= 3 and a[0] == "1.020b.01"  # densest: 2 moons + sun in 16 words


def test_ambiguous_alias_raw_and_resolved():
    passages, tokens, syms, mentions = _pipeline()
    cooc = cooccurrence(mentions)
    counts = resolve_counts(mentions, cooc, syms)
    assert counts["moon"]["raw"] == 4 and counts["moon"]["passages"] == 3
    assert counts["moon"]["resolved"] <= counts["moon"]["raw"]
