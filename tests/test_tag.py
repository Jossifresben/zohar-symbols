# tests/test_tag.py
from pathlib import Path
import pytest
from pipeline.tag import load_kinnuyim, tag, strip_proclitics, SeedError
from pipeline.lemmatise import tokenize

SEEDS = Path(__file__).parent.parent / "seeds" / "kinnuyim.tsv"


def _toks(pid, text, root_for=None):
    root_for = root_for or {}
    return [dict(passage_id=pid, position=i, surface=w, root=root_for.get(w), stem=None,
                 confidence=0.9 if w in root_for else 0.0, source="aramaic_core")
            for i, w in enumerate(tokenize(text))]


def test_seed_loads_and_validates():
    syms = load_kinnuyim(SEEDS)
    ids = [s.id for s in syms]
    assert len(ids) == len(set(ids))
    assert all(s.aliases_surface for s in syms)
    moon = next(s for s in syms if s.id == "moon")
    assert moon.states["diminished"] == ["זער", "מעט", "גלות"]


def test_proclitic_forms_match():
    assert strip_proclitics("וסיהרא") == ["וסיהרא", "סיהרא"]
    assert strip_proclitics("ודסיהרא") == ["ודסיהרא", "דסיהרא", "סיהרא"]
    syms = load_kinnuyim(SEEDS)
    m = tag(_toks("p", "שמשא וסיהרא בסיהרא"), syms)
    moons = [x for x in m if x["symbol_id"] == "moon"]
    assert [x["position"] for x in moons] == [1, 2]
    assert moons[0]["via"] == "surface"


def test_root_alias_matches_when_surface_does_not():
    syms = load_kinnuyim(SEEDS)
    from aramaic_core.characters import hebrew_to_syriac
    toks = _toks("p", "בזווגייהו", root_for={"בזווגייהו": hebrew_to_syriac("זוג")})
    m = tag(toks, syms)
    assert m and m[0]["symbol_id"] == "coupling" and m[0]["via"] == "root"


def test_multiword_alias():
    syms = load_kinnuyim(SEEDS)
    m = tag(_toks("p", "בחקל תפוחין קדישין"), syms)
    assert any(x["symbol_id"] == "apple_orchard" and x["matched_form"] == "חקל תפוחין" for x in m)


def test_bad_seed_raises(tmp_path):
    bad = tmp_path / "k.tsv"
    bad.write_text("id\tlabel_en\tlabel_es\tlabel_ar\tkind\tnode\taliases_surface\taliases_root\tstates\tseed_source\n"
                   "x\tX\tX\tX\tobject\tnowhere\tא\t\t \ts\n", encoding="utf-8")
    with pytest.raises(SeedError):
        load_kinnuyim(bad)


# --- additions beyond the brief: precision guards ---

def test_final_letters_folded_in_roots():
    syms = load_kinnuyim(SEEDS)
    from aramaic_core.characters import hebrew_to_syriac
    moon = next(s for s in syms if s.id == "moon")
    assert moon.states_syriac["full"][0] == hebrew_to_syriac("שלמ")


def test_full_surface_wins_over_proclitic_reading():
    """שמיא is Heaven, not ש+מיא Water; כלבא is Dog, not כ+לבא Heart; שבת is not ש+בת."""
    syms = load_kinnuyim(SEEDS)
    m = tag(_toks("p", "שמיא כלבא שבת"), syms)
    assert {(x["position"], x["symbol_id"]) for x in m} == {(0, "heaven"), (1, "dog"), (2, "sabbath")}


def test_tokens_inside_multiword_match_not_tagged_singly():
    syms = load_kinnuyim(SEEDS)
    m = tag(_toks("p", "כנסת ישראל וימא עלאה"), syms)
    assert {(x["position"], x["symbol_id"]) for x in m} == {(0, "knesset_yisrael"), (2, "upper_sea")}


def test_rabbi_names_not_tagged():
    syms = load_kinnuyim(SEEDS)
    m = tag(_toks("p", "רבי אבא ור׳ יצחק אבא"), syms)
    assert [(x["position"], x["symbol_id"]) for x in m] == [(4, "abba")]


def test_trailing_punctuation_ignored():
    syms = load_kinnuyim(SEEDS)
    toks = [dict(passage_id="p", position=0, surface="סיהרא?!", root=None, stem=None,
                 confidence=0.0, source="none")]
    assert [x["symbol_id"] for x in tag(toks, syms)] == ["moon"]
