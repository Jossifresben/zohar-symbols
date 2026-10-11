# tests/test_compute.py
import json
from pathlib import Path
from aramaic_core.characters import hebrew_to_syriac
from pipeline.segment import segment_page
from pipeline.lemmatise import tokenize
from pipeline.tag import Symbol, load_kinnuyim, tag
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
    cooc = cooccurrence(mentions, 4)
    got = {(c["a"], c["b"]): c["passages_together"] for c in cooc}
    assert got == {(e["a"], e["b"]): e["passages_together"] for e in exp["cooccurrence"]}  # no extras
    assert all(c["a"] < c["b"] for c in cooc)
    assert sorted({m["passage_id"] for m in mentions if m["symbol_id"] == "moon"}) == exp["passages_with_moon"]


def test_pmi_over_all_passages():
    _, _, _, mentions = _pipeline()
    pmi = {(c["a"], c["b"]): c["pmi"] for c in cooccurrence(mentions, 4)}
    assert pmi[("moon", "sun")] == 0.415           # log2(2*4 / (3*2))
    assert pmi[("king", "matronita")] == 2.0       # log2(1*4 / (1*1))


def test_states_detected_by_marker_root():
    exp = json.loads((FIXD / "expected_20a.json").read_text(encoding="utf-8"))
    _, tokens, syms, mentions = _pipeline()
    got = [s for s in detect_states(mentions, tokens, syms) if s["symbol_id"] == "moon"]
    assert got == exp["states"]


def test_strata_assignment():
    rows = load_strata(SEEDS / "strata.tsv")
    passages = [dict(id="3.130a.001", volume=3, folio=130, side="a"),
                dict(id="1.020a.001", volume=1, folio=20, side="a"),
                dict(id="3.145a.002", volume=3, folio=145, side="a"),
                dict(id="3.145b.001", volume=3, folio=145, side="b"),
                dict(id="3.127a.001", volume=3, folio=127, side="a"),
                dict(id="3.127b.001", volume=3, folio=127, side="b")]
    s = assign_strata(passages, rows)
    assert s["3.130a.001"] == "idra_rabba" and s["1.020a.001"] == "main"
    assert s["3.145a.002"] == "idra_rabba" and s["3.145b.001"] == "main"
    assert s["3.127a.001"] == "main" and s["3.127b.001"] == "idra_rabba"


def test_surfaced_is_deterministic_and_bounded():
    passages, tokens, syms, mentions = _pipeline()
    cooc = cooccurrence(mentions, len(passages))
    tbp = {}
    for t in tokens:
        tbp.setdefault(t["passage_id"], []).append(t)
    strata = {p["id"]: "main" for p in passages}
    a = surfaced_passages("moon", mentions, cooc, tbp, strata, k=6)
    b = surfaced_passages("moon", mentions, cooc, tbp, strata, k=6)
    assert a == b and 0 < len(a) <= 3 and a[0] == "1.020b.001"  # densest: 2 moons + sun in 18 tokens


def test_ambiguous_alias_raw_and_resolved():
    passages, tokens, syms, mentions = _pipeline()
    cooc = cooccurrence(mentions, len(passages))
    counts = resolve_counts(mentions, cooc, syms)
    assert counts["moon"]["raw"] == 4 and counts["moon"]["passages"] == 3
    assert counts["moon"]["resolved"] <= counts["moon"]["raw"]


def test_surfaced_takes_one_per_stratum_before_density():
    mentions = [dict(symbol_id="x", passage_id=p, position=0, matched_form="x", via="surface")
                for p in ("p1", "p2", "p3")]
    tbp = {"p1": [{}] * 2, "p2": [{}] * 3, "p3": [{}] * 10}   # density: p1 > p2 > p3
    strata = {"p1": "main", "p2": "main", "p3": "idra_rabba"}
    assert surfaced_passages("x", mentions, [], tbp, strata, k=2) == ["p1", "p3"]
    assert surfaced_passages("x", mentions, [], tbp, strata, k=3) == ["p1", "p3", "p2"]


def _sym(id_, node, alias):
    return Symbol(id=id_, label_en=id_, label_es=id_, label_ar=alias, kind="object", node=node,
                  aliases_surface=[alias], aliases_root=[], states={}, seed_source="test")


def test_resolution_by_same_node_support():
    syms = [_sym("night_a", "gevurah", "ליליא"), _sym("night_b", "malkhut", "ליליא"),
            _sym("left", "gevurah", "שמאלא"), _sym("moon", "malkhut", "סיהרא")]
    m = lambda s, p, i, f="ליליא": dict(symbol_id=s, passage_id=p, position=i, matched_form=f, via="surface")
    mentions = [
        m("night_a", "P1", 0), m("night_b", "P1", 0), m("night_a", "P1", 2), m("night_b", "P1", 2),
        m("left", "P1", 1, "שמאלא"),                       # gevurah support -> night_a wins P1
        m("night_a", "P2", 0), m("night_b", "P2", 0), m("moon", "P2", 1, "סיהרא"),  # malkhut -> night_b wins P2
        m("night_a", "P3", 0), m("night_b", "P3", 0),      # no support -> tie, both keep
    ]
    c = resolve_counts(mentions, cooccurrence(mentions, 3), syms)
    assert c["night_a"] == dict(raw=4, resolved=3, passages=3)
    assert c["night_b"] == dict(raw=4, resolved=2, passages=3)
    assert c["left"] == dict(raw=1, resolved=1, passages=1)
    assert c["moon"] == dict(raw=1, resolved=1, passages=1)


def test_detect_states_skips_unknown_symbol():
    _, tokens, syms, mentions = _pipeline()
    ghost = dict(symbol_id="not_in_seed", passage_id="1.020a.002", position=0, matched_form="x", via="surface")
    assert detect_states(mentions + [ghost], tokens, syms) == detect_states(mentions, tokens, syms)


def test_labelled_stream_is_its_stratum_and_overrides_ranges():
    rows = load_strata(SEEDS / "strata.tsv")
    passages = [dict(id="3.130a.001", volume=3, folio=130, side="a", stream="raaya_meheimna"),
                dict(id="3.130a.002", volume=3, folio=130, side="a", stream="main"),
                dict(id="1.100a.001", volume=1, folio=100, side="a", stream="midrash_haneelam"),
                dict(id="1.100a.002", volume=1, folio=100, side="a", stream="main")]
    s = assign_strata(passages, rows)
    assert s == {"3.130a.001": "raaya_meheimna", "3.130a.002": "idra_rabba",
                 "1.100a.001": "midrash_haneelam", "1.100a.002": "main"}
    assert {r["stratum"] for r in rows} == {"idra_rabba", "idra_zuta"}
