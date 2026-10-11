import json, sqlite3
import pytest
from pathlib import Path
from pipeline.build import build
from pipeline.tag import load_kinnuyim

SEEDS = Path(__file__).parent.parent / "seeds"


def _tiny():
    raw = {"pages": [{"title": "t", "revid": 1}], "passages": [
        dict(id="1.020a.001", volume=1, folio=20, side="a", para=1, parasha="Bereshit",
             text_ar="שמשא וסיהרא", verse_ref="Genesis 1:16")]}
    tokens = [dict(passage_id="1.020a.001", position=0, surface="שמשא", root="x", stem=None, confidence=0.9, source="aramaic_core"),
              dict(passage_id="1.020a.001", position=1, surface="וסיהרא", root="y", stem=None, confidence=1.0, source="override")]
    mentions = [dict(symbol_id="sun", passage_id="1.020a.001", position=0, matched_form="שמשא", via="surface"),
                dict(symbol_id="moon", passage_id="1.020a.001", position=1, matched_form="סיהרא", via="surface")]
    computed = dict(cooccurrence=[dict(a="moon", b="sun", passages_together=1, pmi=0.0)],
                    symbol_counts={"moon": dict(raw=1, resolved=1, passages=1), "sun": dict(raw=1, resolved=1, passages=1)},
                    states=[], strata={"1.020a.001": "main"}, surfaced={"moon": ["1.020a.001"], "sun": ["1.020a.001"]})
    return raw, tokens, mentions, computed


def test_build_writes_all_tables(tmp_path):
    raw, tokens, mentions, computed = _tiny()
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")
    con = sqlite3.connect(tmp_path / "z.sqlite")
    names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"passage", "token", "symbol", "mention", "cooccurrence", "state", "surfaced", "translation", "gloss", "meta"} <= names
    assert con.execute("select token_count, stratum from passage").fetchone() == (2, "main")
    assert con.execute("select count_raw from symbol where id='moon'").fetchone() == (1,)
    assert con.execute("select value from meta where key='tables_version'").fetchone()[0]
    j = json.loads((tmp_path / "t.json").read_text(encoding="utf-8"))
    assert "symbols" in j and j["cooccurrence"][0]["a"] == "moon"
    assert "built_at" not in j


def test_build_is_idempotent(tmp_path):
    raw, tokens, mentions, computed = _tiny()
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    for _ in range(2):
        build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")
    con = sqlite3.connect(tmp_path / "z.sqlite")
    assert con.execute("select count(*) from passage").fetchone() == (1,)


def test_build_tolerates_stale_state(tmp_path):
    raw, tokens, mentions, computed = _tiny()
    computed["states"] = [dict(symbol_id="sun", state_label="no-such-state", passage_id="1.020a.001")]
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")
    con = sqlite3.connect(tmp_path / "z.sqlite")
    assert con.execute("select marker_roots from state").fetchone() == ("",)


def test_build_fails_on_dangling_foreign_key(tmp_path):
    raw, tokens, mentions, computed = _tiny()
    mentions = mentions + [dict(symbol_id="sun", passage_id="9.999z.99", position=0, matched_form="x", via="alias")]
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    with pytest.raises(ValueError, match="foreign key"):
        build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")


def test_declared_states_and_alias_roots_stored(tmp_path):
    raw, tokens, mentions, computed = _tiny()   # no state detected
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")
    con = sqlite3.connect(tmp_path / "z.sqlite")
    assert con.execute("select count(*) from state").fetchone() == (0,)
    assert con.execute("select marker_roots from state_decl where symbol_id='moon' and state_label='diminished'"
                       ).fetchone() == ("זער,מעט,גלו",)
    coupling = next(s for s in syms if s.id == "coupling")
    aliases = con.execute("select aliases from symbol where id='coupling'").fetchone()[0]
    surf, roots = aliases.split("|")
    assert surf.split(";") == coupling.aliases_surface and "זוג" in roots.split(";")


@pytest.mark.parametrize("table", ["surfaced", "cooccurrence", "state"])
def test_foreign_keys_cover_derived_tables(tmp_path, table):
    raw, tokens, mentions, computed = _tiny()
    if table == "surfaced":
        computed["surfaced"] = {"moon": ["9.999z.999"]}
    elif table == "cooccurrence":
        computed["cooccurrence"] = [dict(a="moon", b="no_such_symbol", passages_together=1, pmi=0.0)]
    else:
        computed["states"] = [dict(symbol_id="moon", state_label="diminished", passage_id="9.999z.999")]
    syms = load_kinnuyim(SEEDS / "kinnuyim.tsv")
    with pytest.raises(ValueError, match="foreign key"):
        build(raw, tokens, mentions, computed, syms, tmp_path / "z.sqlite", tmp_path / "t.json")
