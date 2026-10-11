# tests/test_fetch.py
from pathlib import Path
import pytest
from pipeline.fetch import load_parashot, build_raw, report_rows
from pipeline.wikisource import PageText

SEEDS = Path(__file__).parent.parent / "seeds" / "parashot.tsv"


def test_parashot_seed_is_consistent():
    rows = load_parashot(SEEDS)
    # 29 numbered pages (the index has no "חלק טז"); זוהר השמטות excluded
    assert len(rows) == 29
    vol_by_book = {"Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 3, "Deuteronomy": 3}
    for r in rows:
        assert r["volume"] == vol_by_book[r["book"]], r
    for r in rows:
        assert "," not in r["parasha"] and " - " not in r["parasha"], r
    assert len({r["page_title"] for r in rows}) == len(rows)


def test_build_raw_from_fixture(tmp_path: Path):
    fix = (Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8")
    pages = [("זוהר חלק ב", 1, "Bereshit", PageText("זוהר חלק ב", 5, "2026-10-01T00:00:00Z", fix))]
    out = build_raw(pages)
    assert out["pages"][0]["revid"] == 5
    assert len(out["passages"]) == 4
    assert out["passages"][0]["id"] == "1.020a.001"


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
    assert ids == ["1.020a.001", "1.020a.002", "1.020a.003", "1.020a.004"]
    assert [p["para"] for p in out["passages"]] == [1, 2, 3, 4]
    assert out["passages"][2]["parasha"] == "Noach"
    assert out["split_folios"] == 1
    assert out["split_detail"] == {"1.020a": "זוהר חלק ב → זוהר חלק ג"}
    rows = dict(report_rows(out))
    assert rows["split across pages: 1.020a"] == "זוהר חלק ב → זוהר חלק ג"


def test_cross_page_identical_text_raises():
    pages = [
        ("זוהר חלק ב", 1, "Bereshit", _page("זוהר חלק ב", 1, "אחד", "שנים")),
        ("זוהר חלק ג", 1, "Noach", _page("זוהר חלק ג", 2, "אחד")),
    ]
    with pytest.raises(ValueError, match="duplicate text in repeated section"):
        build_raw(pages)


def test_within_page_continuation_listed_in_report():
    wt = ("<קטע התחלה=דף כ א/>\nאחד\n<קטע סוף=דף כ א/>\n=== כותרת ===\n"
          "<קטע התחלה=דף כ א/>\nשנים\n<קטע סוף=דף כ א/>\n")
    out = build_raw([("זוהר חלק ב", 1, "Bereshit", PageText("זוהר חלק ב", 1, "t", wt))])
    assert [p["id"] for p in out["passages"]] == ["1.020a.001", "1.020a.002"]
    assert dict(report_rows(out))["continued: 1.020a"] == 2


def test_sources_md_is_stable_across_runs(tmp_path: Path):
    from pipeline.fetch import write_sources_md
    fix = (Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext").read_text(encoding="utf-8")
    pages = [("זוהר חלק ב", 1, "Bereshit", PageText("זוהר חלק ב", 5, "2026-10-01T00:00:00Z", fix))]
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    write_sources_md(build_raw(pages), a)
    write_sources_md(build_raw(pages), b)
    assert a.read_text() == b.read_text()
    assert "Source revisions as of 2026-10-01T00:00:00Z" in a.read_text()


def test_streams_numbered_after_main_across_pages():
    a = PageText("א", 1, "t", "<קטע התחלה=דף כ א/>\nאחד\n<קטע סוף=דף כ א/>\n"
                 '<קטע התחלה=רע"מ דף כ א/>\nרעיא\n<קטע סוף=רע"מ דף כ א/>\n')
    b = PageText("ב", 2, "t", "<קטע התחלה=דף כ א/>\nשנים\n<קטע סוף=דף כ א/>\n")
    out = build_raw([("א", 1, "Bereshit", a), ("ב", 1, "Noach", b)])
    got = [(p["id"], p["stream"], p["text_ar"]) for p in out["passages"]]
    assert got == [("1.020a.001", "main", "אחד"), ("1.020a.003", "raaya_meheimna", "רעיא"),
                   ("1.020a.002", "main", "שנים")]
    assert out["split_detail"] == {"1.020a": "א → ב"}  # the RM stream did not straddle pages


def test_size_outliers_listed():
    from pipeline.fetch import size_outliers
    def ps(folio, n, words):
        return [dict(volume=1, folio=folio, side="a", text_ar=" ".join(["מלה"] * words)) for _ in range(n)]
    passages = ps(1, 2, 10) + ps(2, 2, 10) + ps(3, 2, 10) + ps(4, 7, 10) + ps(5, 1, 50)
    # median paras 2, median tokens 20: 4a has 7 > 6 paras (and 70 > 60 tokens); 5a has 50 tokens, not > 60
    assert size_outliers(passages) == [("size outlier: 1.004a", "7 paras, 70 tokens")]
    passages += ps(6, 1, 200)
    assert ("size outlier: 1.006a", "1 paras, 200 tokens") in size_outliers(passages)
