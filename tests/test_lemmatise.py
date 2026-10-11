from pathlib import Path
from pipeline.lemmatise import tokenize, lemmatise, load_overrides

VENDOR = Path(__file__).parent.parent / "vendor" / "atlas_roots"
SEEDS = Path(__file__).parent.parent / "seeds" / "zohar_overrides.tsv"


def test_tokenize_strips_punctuation():
    assert tokenize("שמשא וסיהרא, בקיומא (חד) הוו.") == ["שמשא", "וסיהרא", "בקיומא", "חד", "הוו"]


def test_override_wins(tmp_path):
    passages = [{"id": "1.020a.01", "text_ar": "שמשא וסיהרא הוו"}]
    toks = lemmatise(passages, load_overrides(SEEDS), VENDOR, tmp_path)
    by_surface = {t["surface"]: t for t in toks}
    assert by_surface["וסיהרא"]["source"] == "override"
    assert by_surface["וסיהרא"]["confidence"] == 1.0
    assert by_surface["וסיהרא"]["root"]  # non-empty canonical root


def test_unknown_word_kept_with_none(tmp_path):
    passages = [{"id": "1.020a.01", "text_ar": "קקקקק"}]
    toks = lemmatise(passages, {}, VENDOR, tmp_path)
    assert toks[0]["root"] is None and toks[0]["confidence"] == 0.0 and toks[0]["source"] == "none"


def test_positions_are_sequential(tmp_path):
    passages = [{"id": "p", "text_ar": "א ב ג"}]
    toks = lemmatise(passages, {}, VENDOR, tmp_path)
    assert [t["position"] for t in toks] == [0, 1, 2]
