from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]

# One Ra'aya Meheimna section appended to the shared fixture: becomes passage 1.020b.003.
RAAYA_SECTION = "\n<קטע התחלה=רע\"מ דף כ ב/>\nפקודא דא לאתעסקא באורייתא בכל יומא. סיהרא ושמשא.\n<קטע סוף=רע\"מ דף כ ב/>\n"


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory) -> Path:
    """A real sqlite built from the Bereshit fixture through every pipeline stage."""
    from pipeline.segment import segment_page
    from pipeline.lemmatise import lemmatise, load_overrides
    from pipeline.tag import load_kinnuyim, tag
    from pipeline.compute import compute_all
    from pipeline.build import build
    tmp = tmp_path_factory.mktemp("webdb")
    fix = (ROOT / "tests" / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8") + RAAYA_SECTION
    passages = [p.__dict__ for p in segment_page(fix, 1, "Bereshit", "t")]
    raw = {"pages": [{"title": "t", "revid": 1}], "passages": passages}
    tokens = lemmatise(passages, load_overrides(ROOT / "seeds" / "zohar_overrides.tsv"), ROOT / "vendor" / "atlas_roots", tmp / "w")
    syms = load_kinnuyim(ROOT / "seeds" / "kinnuyim.tsv")
    mentions = tag(tokens, syms)
    computed = compute_all(raw, tokens, mentions, syms)
    build(raw, tokens, mentions, computed, syms, tmp / "z.sqlite", tmp / "t.json")
    return tmp / "z.sqlite"


@pytest.fixture()
def app(fixture_db):
    from web import create_app
    a = create_app(str(fixture_db))
    a.config["TESTING"] = True
    return a


@pytest.fixture()
def client(app):
    return app.test_client()
