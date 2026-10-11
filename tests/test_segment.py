from pathlib import Path
import pytest
from pipeline.segment import segment_page, clean_wikitext, SegmentError

FIX = Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext"


def test_segments_two_folios_four_passages():
    ps = segment_page(FIX.read_text(encoding="utf-8"), volume=1, parasha="Bereshit", page_title="זוהר חלק א")
    ids = [p.id for p in ps]
    assert ids == ["1.020a.01", "1.020a.02", "1.020b.01", "1.020b.02"]
    assert ps[0].folio == 20 and ps[0].side == "a" and ps[2].side == "b"
    assert ps[0].text_ar.startswith("ויעש אלהים")
    assert ps[0].verse_ref == "Genesis 1:16"


def test_templates_and_markup_removed():
    ps = segment_page(FIX.read_text(encoding="utf-8"), volume=1, parasha="Bereshit", page_title="t")
    joined = " ".join(p.text_ar for p in ps)
    assert "{{" not in joined and "}}" not in joined
    assert "הערת מהדיר" not in joined
    assert "קטגוריה" not in joined


def test_variant_readings_removed():
    ps = segment_page(FIX.read_text(encoding="utf-8"), volume=1, parasha="Bereshit", page_title="t")
    assert "בכתרין" not in ps[1].text_ar
    assert "נ\"א" not in ps[1].text_ar


def test_shin_template_breaks_paragraph():
    ps = segment_page(FIX.read_text(encoding="utf-8"), volume=1, parasha="Bereshit", page_title="t")
    assert ps[3].text_ar.startswith("מלכא ומטרוניתא")


def test_unclosed_section_raises():
    bad = "<קטע התחלה=דף כ א/>טקסט\n<קטע התחלה=דף כ ב/>עוד"
    with pytest.raises(SegmentError) as e:
        segment_page(bad, volume=1, parasha="x", page_title="p")
    assert "כ א" in str(e.value)


def test_clean_keeps_quoted_words():
    assert clean_wikitext("{{צ|בראשית}} ברא") == "בראשית ברא"
