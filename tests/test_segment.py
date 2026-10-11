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


def _seg(wt):
    return segment_page(wt, volume=1, parasha="x", page_title="p")


def _sec(body, f="כ א"):
    return f"<קטע התחלה=דף {f}/>\n{body}\n<קטע סוף=דף {f}/>"


def test_bad_side_tag_raises():
    with pytest.raises(SegmentError) as e:
        _seg("<קטע התחלה=דף כ ג/>x\n<קטע סוף=דף כ ג/>")
    assert "<unparsed>" in str(e.value)


def test_tolerant_tags_and_geresh_numeral():
    ps = _seg("<קטע התחלה = דף כ\"א א />x\n<קטע סוף = דף כ\"א א />")
    assert ps[0].folio == 21


def test_template_line_does_not_split_paragraph():
    ps = _seg(_sec("text\n{{הערה|x}}\ntext"))
    assert [p.text_ar for p in ps] == ["text text"]


def test_links_keep_label_and_category_removed_inside_section():
    ps = _seg(_sec("[[קטגוריה:ספר הזהר]]\nא [[יעקב|יעקב אבינו]] ב [[משה]]"))
    assert len(ps) == 1
    assert ps[0].text_ar == "א יעקב אבינו ב משה"
    assert "קטגוריה" not in ps[0].text_ar


def test_ref_and_comment_removed():
    ps = _seg(_sec("א<ref name=a>הערה</ref> ב<ref x/> <!-- c --> ג"))
    assert ps[0].text_ar == "א ב ג"


def test_deep_nesting_removed_and_tz_extra_arg():
    assert clean_wikitext("א {{a|{{b|{{c|{{d}}}}}}}} ב") == "א ב"
    assert clean_wikitext("{{צ|a|b}} x") == "a x"


def test_unbalanced_braces_raise():
    with pytest.raises(SegmentError) as e:
        _seg(_sec("א {{הערה|x ב"))
    assert "unbalanced" in str(e.value)


def test_repeated_folio_continues_numbering():
    stats = {}
    wt = _sec("x\n\nw") + "\n=== heading ===\n" + _sec("y\n\nz")
    ps = segment_page(wt, 1, "X", "t", stats)
    assert [p.id for p in ps] == ["1.020a.01", "1.020a.02", "1.020a.03", "1.020a.04"]
    assert [p.para for p in ps] == [1, 2, 3, 4]
    assert stats["continued"] == 1


def test_unclosed_variant_raises():
    with pytest.raises(SegmentError) as e:
        _seg(_sec('א (נ"א ב\n\nג) ד'))
    assert "variant" in str(e.value)


def test_small_wrapped_variant_reading_is_dropped():
    wt = '<קטע התחלה=דף א ב/>\nאמר ואמר (<small>נ"א, ומה אדמה לך</small>), בכל יומא.\n<קטע סוף=דף א ב/>\n'
    [p] = segment_page(wt, 1, "X", "t")
    assert "נ\"א" not in p.text_ar and "בכל יומא" in p.text_ar


def test_overlay_sections_are_ignored_and_stripped():
    wt = ('<קטע התחלה=דף א א/>\n<קטע התחלה=בראשית א א/>\nטקסט\n<קטע סוף=בראשית א א/>\n'
          '<קטע התחלה=שבועות 1/>עוד<קטע סוף=שבועות 1/>\n<קטע סוף=דף א א/>\n')
    [p] = segment_page(wt, 1, "X", "t")
    assert "קטע" not in p.text_ar and "טקסט" in p.text_ar


def test_stray_duplicate_start_tag_only_for_listed_label():
    wt = '<קטע התחלה=דף א א/>\n==כותרת==\n<קטע התחלה=דף א א/>טקסט\n<קטע סוף=דף א א/>\n'
    import pytest
    from pipeline.segment import SegmentError
    with pytest.raises(SegmentError):
        segment_page(wt, 1, "X", "t")
    [p] = segment_page(wt, 1, "X", "זוהר חלק א")
    assert p.text_ar == "טקסט"


def test_repeated_section_with_identical_text_raises():
    with pytest.raises(SegmentError) as e:
        _seg(_sec("x") + "\n=== h ===\n" + _sec("x"))
    assert "duplicate text in repeated section" in str(e.value)
