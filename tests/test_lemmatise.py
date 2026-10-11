from pathlib import Path
import pytest
from aramaic_core.characters import hebrew_to_syriac
from pipeline.lemmatise import tokenize, lemmatise, load_overrides, proclitic_candidates

VENDOR = Path(__file__).parent.parent / "vendor" / "atlas_roots"
SEEDS = Path(__file__).parent.parent / "seeds" / "zohar_overrides.tsv"


def test_tokenize_strips_punctuation():
    assert tokenize("שמשא וסיהרא, בקיומא (חד) הוו.") == ["שמשא", "וסיהרא", "בקיומא", "חד", "הוו"]


def test_override_wins(tmp_path):
    passages = [{"id": "1.020a.001", "text_ar": "שמשא וסיהרא הוו"}]
    toks = lemmatise(passages, load_overrides(SEEDS), VENDOR, tmp_path)
    by_surface = {t["surface"]: t for t in toks}
    assert by_surface["וסיהרא"]["source"] == "override"
    assert by_surface["וסיהרא"]["confidence"] == 1.0
    assert by_surface["וסיהרא"]["root"]  # non-empty canonical root


def test_unknown_word_kept_with_none(tmp_path):
    passages = [{"id": "1.020a.001", "text_ar": "קקקקק"}]
    toks = lemmatise(passages, {}, VENDOR, tmp_path)
    assert toks[0]["root"] is None and toks[0]["confidence"] == 0.0 and toks[0]["source"] == "none"


def test_positions_are_sequential(tmp_path):
    passages = [{"id": "p", "text_ar": "א ב ג"}]
    toks = lemmatise(passages, {}, VENDOR, tmp_path)
    assert [t["position"] for t in toks] == [0, 1, 2]


def test_tokenize_gershayim_and_geresh():
    assert tokenize('אמר ר"ש הקב"ה ברא') == ["אמר", "ר״ש", "הקב״ה", "ברא"]
    assert tokenize("ר' שמעון") == ["ר׳", "שמעון"]
    assert tokenize("ר׳ שמעון") == ["ר׳", "שמעון"]
    assert tokenize('אמר "שלום"') == ["אמר", "שלום"]  # unflanked quotes separate


def test_tokenize_drops_non_hebrew_tokens():
    assert tokenize("אמר - -- — … ? ברא * 12") == ["אמר", "ברא"]


def test_proclitic_candidates():
    assert proclitic_candidates("ושמשא") == ["ושמשא", "שמשא", "משא"]
    assert proclitic_candidates("ולמלכא") == ["ולמלכא", "למלכא", "מלכא"]
    assert proclitic_candidates("ומ") == ["ומ"]  # too short to strip
    assert proclitic_candidates("ספרא") == ["ספרא"]


def test_prefixed_surface_hits_bare_override(tmp_path):
    ov = load_overrides(SEEDS)
    toks = lemmatise([{"id": "p", "text_ar": "ומטרוניתא למלכא"}], ov, VENDOR, tmp_path)
    assert [t["source"] for t in toks] == ["override", "override"]
    assert toks[0]["surface"] == "ומטרוניתא" and toks[0]["root"] == hebrew_to_syriac("מטרן")
    assert toks[1]["root"] == hebrew_to_syriac("מלך") and toks[1]["confidence"] == 1.0


def test_override_root_is_canonical_and_final_folded():
    ov = load_overrides(SEEDS)
    assert ov["סיהרא"][0] == hebrew_to_syriac("סהר")
    assert ov["מלכא"][0] == hebrew_to_syriac("מלכ")  # final ך folded to כ


def test_duplicate_surface_raises(tmp_path):
    p = tmp_path / "o.tsv"
    p.write_text("surface\troot\tstem\tnote\nמלכא\tמלך\t \t\nמלכא\tמלך\t \t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_overrides(p)


def test_non_hebrew_root_rejected(tmp_path):
    p = tmp_path / "o.tsv"
    p.write_text("surface\troot\tstem\tnote\nמלכא\tabc\t \t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_overrides(p)


def test_empty_root_override(tmp_path):
    ov = load_overrides(SEEDS)
    toks = lemmatise([{"id": "p", "text_ar": 'הקב"ה'}], ov, VENDOR, tmp_path)
    assert toks[0]["surface"] == "הקב״ה"
    assert (toks[0]["root"], toks[0]["confidence"], toks[0]["source"]) == (None, 1.0, "override")


def test_override_root_matches_extractor_key(tmp_path):
    passages = [{"id": "p", "text_ar": "סיהרא"}]
    plain = lemmatise(passages, {}, VENDOR, tmp_path)[0]
    over = lemmatise(passages, load_overrides(SEEDS), VENDOR, tmp_path)[0]
    assert plain["source"] == "aramaic_core" and plain["root"] == over["root"]
