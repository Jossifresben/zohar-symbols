# tests/test_fetch.py
from pathlib import Path
from pipeline.fetch import load_parashot, build_raw
from pipeline.wikisource import PageText

SEEDS = Path(__file__).parent.parent / "seeds" / "parashot.tsv"


def test_parashot_seed_is_consistent():
    rows = load_parashot(SEEDS)
    # 29 numbered pages (the index has no "חלק טז") + the omissions page
    assert len(rows) >= 30
    vol_by_book = {"Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 3, "Deuteronomy": 3}
    for r in rows:
        assert r["volume"] == vol_by_book[r["book"]], r
    assert len({r["page_title"] for r in rows}) == len(rows)


def test_build_raw_from_fixture(tmp_path: Path):
    fix = (Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8")
    pages = [("זוהר חלק ב", 1, "Bereshit", PageText("זוהר חלק ב", 5, "2026-10-01T00:00:00Z", fix))]
    out = build_raw(pages)
    assert out["pages"][0]["revid"] == 5
    assert len(out["passages"]) == 4
    assert out["passages"][0]["id"] == "1.020a.01"


def _page(title, revid, *paras):
    body = "\n\n".join(paras)
    wt = f"<קטע התחלה=דף כ א/>\n{body}\n<קטע סוף=דף כ א/>\n"
    return PageText(title, revid, "2026-10-01T00:00:00Z", wt)


def test_folio_split_across_pages_is_renumbered():
    pages = [
        ("זוהר חלק ב", 1, "Bereshit", _page("זוהר חלק ב", 1, "אחד", "שנים")),
        ("זוהר חלק ג", 1, "Noach", _page("זוהר חלק ג", 2, "שלשה", "ארבעה")),
    ]
    out = build_raw(pages)
    ids = [p["id"] for p in out["passages"]]
    assert ids == ["1.020a.01", "1.020a.02", "1.020a.03", "1.020a.04"]
    assert [p["para"] for p in out["passages"]] == [1, 2, 3, 4]
    assert out["passages"][2]["parasha"] == "Noach"
    assert out["split_folios"] == 1
