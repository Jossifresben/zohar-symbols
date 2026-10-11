from pathlib import Path
import pytest
from pipeline.segment import segment_page, clean_wikitext, SegmentError

FIX = Path(__file__).parent / "fixtures" / "bereshit_20a.wikitext"


def test_segments_two_folios_four_passages():
    ps = segment_page(FIX.read_text(encoding="utf-8"), volume=1, parasha="Bereshit", page_title="זוהר חלק א")
    ids = [p.id for p in ps]
    assert ids == ["1.020a.001", "1.020a.002", "1.020b.001", "1.020b.002"]
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
    assert "unclassified section label" in str(e.value)


def test_malformed_tag_raises():
    with pytest.raises(SegmentError) as e:
        _seg("<קטע התחלה=דף כ א>x\n<קטע סוף=דף כ א/>")
    assert "<unparsed>" in str(e.value)


def test_tolerant_tags_and_geresh_numeral():
    ps = _seg("<קטע התחלה = דף כ\"א א />א\n<קטע סוף = דף כ\"א א />")
    assert ps[0].folio == 21


def test_template_line_does_not_split_paragraph():
    ps = _seg(_sec("טקסט\n{{הערה|x}}\nטקסט"))
    assert [p.text_ar for p in ps] == ["טקסט טקסט"]


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
    wt = _sec("א\n\nב") + "\n=== heading ===\n" + _sec("ג\n\nד")
    ps = segment_page(wt, 1, "X", "t", stats)
    assert [p.id for p in ps] == ["1.020a.001", "1.020a.002", "1.020a.003", "1.020a.004"]
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


def test_stray_start_tag_with_text_before_the_real_one_raises():
    wt = '<קטע התחלה=דף א א/>\nמלה\n<קטע התחלה=דף א א/>טקסט\n<קטע סוף=דף א א/>\n'
    with pytest.raises(SegmentError, match="stray start tag is followed by text"):
        segment_page(wt, 1, "X", "זוהר חלק א")


def test_repeated_section_with_identical_text_raises():
    with pytest.raises(SegmentError) as e:
        _seg(_sec("א") + "\n=== h ===\n" + _sec("א"))
    assert "duplicate text in repeated section" in str(e.value)


def test_text_carrying_templates_keep_their_text():
    assert clean_wikitext("אתקרי {{גמט דגש|עסטיראה}} ו{{קיצור|ב\"ד|בית דין}} {{הערה|note}}x") == 'אתקרי עסטיראה וב"ד x'
    assert clean_wikitext("א{{'}} {{צ|{{קו תחתי|מראת}} אלהי\"ם}}") == "א' מראת אלהי\"ם"
    assert clean_wikitext("{{מצ|תהלים|קלה|ד|כי יעקב בחר}} y") == "כי יעקב בחר y"


def test_variant_wrapped_in_bold_is_removed():
    assert clean_wikitext("אמר (''' ס\"א x''') ב".replace("''' ", "'''")) == "אמר ב"


def test_folio_label_with_parasha_suffix():
    wt = ("<קטע התחלה=דף לה ב - צו/>אאא<קטע סוף=דף לה ב - צו/>\n"
          "<קטע התחלה=דף לה ב - שמיני/>בבב<קטע סוף=דף לה ב - שמיני/>")
    ps = _seg(wt)
    assert [p.id for p in ps] == ["1.035b.001", "1.035b.002"]


def test_known_typo_fix_must_match_exactly_once():
    from pipeline.segment import _TEXT_FIXES
    for (title, old) in _TEXT_FIXES:
        with pytest.raises(SegmentError, match="known typo"):
            segment_page(_sec("nothing here"), 1, "X", title)
        with pytest.raises(SegmentError, match="known typo"):
            segment_page(_sec(old + " " + old), 1, "X", title)


def test_unclosed_note_fix_keeps_resuming_zohar_text():
    wt = _sec("א{{הערה|הנה {{צ|כי לי (המתוק מדבש)}} - הא אינון קדישין. וכתיב בהו בלוים")
    ps = segment_page(wt, 1, "X", "זוהר חלק כה")
    assert "הערה" not in ps[0].text_ar and "הנה" not in ps[0].text_ar
    assert ps[0].text_ar == "א - הא אינון קדישין. וכתיב בהו בלוים"


def test_anchor_template_dropped_and_tikkun_girsa_keeps_printed_reading():
    assert clean_wikitext("{{עוגן|בריך שמיה}} אמר") == "אמר"
    assert clean_wikitext("{{תיקון גירסה|מטיבו|משיכו}} דיינא") == "מטיבו דיינא"


# --- text streams (R1-R3) ---

STREAMS_FIX = Path(__file__).parent / "fixtures" / "streams.wikitext"


def _streams(stats=None):
    return segment_page(STREAMS_FIX.read_text(encoding="utf-8"), 3, "Emor", "t", stats)


def test_stream_sections_continue_the_folio_numbering_in_fixed_order():
    ps = _streams()
    got = sorted((p.id, p.stream) for p in ps)
    # main first, then raaya_meheimna, then midrash_haneelam, though the page has MhN before RM
    assert got == [("3.088a.001", "main"), ("3.088a.002", "main"),
                   ("3.088b.001", "main"), ("3.088b.002", "raaya_meheimna"),
                   ("3.088b.003", "raaya_meheimna"), ("3.088b.004", "midrash_haneelam")]
    assert next(p for p in ps if p.id == "3.088b.002").text_ar.startswith("פקודא")


def test_parasha_prefixed_label_is_main_stream():
    ps = _streams()
    assert [p.stream for p in ps if p.folio == 88 and p.side == "a"] == ["main", "main"]
    assert ps[0].verse_ref == "Leviticus 21:1"


def test_placeholder_note_section_is_dropped():
    stats = {}
    ps = _streams(stats)
    assert stats["placeholders"] == 1
    assert not any("הדף מכיל" in p.text_ar for p in ps)
    assert not any(p.stream == "raaya_meheimna" and p.side == "a" for p in ps)


def test_heading_lines_and_image_links_dropped():
    ps = _streams()
    joined = " ".join(p.text_ar for p in ps)
    assert "פתח רבי יצחק" not in joined and "=" not in joined
    assert "200px" not in joined and "center" not in joined
    assert ps[0].text_ar.endswith("רבי יצחק פתח ואמר זכאין אינון ישראל.")
    assert clean_wikitext("א [[קובץ:x.png||35px|]] ב [[תמונה:y.png|20px]] ג [[:קטגוריה:ז]] ד") == "א ב ג ד"
    assert clean_wikitext("== כותרת ==\nטקסט") == "טקסט"


def test_paragraph_without_hebrew_letter_is_dropped():
    assert [p.text_ar for p in _seg(_sec("א\n\n. , ;\n\n[]\n\nב"))] == ["א", "ב"]


def test_tag_inside_html_comment_is_ignored():
    ps = _streams()
    assert not any(p.folio == 99 for p in ps)
    assert [p.text_ar for p in _seg(_sec("<!-- <קטע התחלה=דף ל א/> -->א"))] == ["א"]


def test_label_classification():
    from pipeline.segment import classify_label, Label
    assert classify_label('רע"מ דף פח ב') == Label("raaya_meheimna", 88, "b", "פח ב")
    assert classify_label('אמור רע"מ דף פח א').stream == "raaya_meheimna"
    assert classify_label('רע"מ ואתחנן דף רע ב').stream == "raaya_meheimna"
    assert classify_label("רעיא מהימנא דף כה א").stream == "raaya_meheimna"
    assert classify_label("מדרש הנעלם דף צט ב").stream == "midrash_haneelam"
    assert classify_label("סתרי תורה דף עד א").stream == "sitrei_torah"
    assert classify_label("רזא דרזין דף עד א").stream == "raza_derazin"
    assert classify_label("תוספתא דף סב ב").stream == "tosefta"
    assert classify_label("מתניתין דף עד א").stream == "matnitin"
    assert classify_label('ד"א דף קעז ב').stream == "other"
    assert classify_label("אמור דף פח א").stream == "main"
    assert classify_label("דף לה ב - צו").stream == "main"
    for overlay in ("בראשית א א", "שבועות 3", "ספרא דצניעותא הקדמה", "ספרא דצניעותא ג"):
        assert classify_label(overlay) is None
    for bad in ("פלוני דף כ א", "דף כ א - פלוני", "קטע חדש", 'תוספתא רע"מ דף כ א'):
        with pytest.raises(SegmentError):
            classify_label(bad)


def test_unknown_label_fails_the_page():
    with pytest.raises(SegmentError, match="unclassified section label"):
        _seg(_sec("א") + "<קטע התחלה=משהו אחר/>ב<קטע סוף=משהו אחר/>")


def test_section_closed_by_another_stream_raises():
    with pytest.raises(SegmentError, match="closed by"):
        _seg('<קטע התחלה=תוספתא דף כ א/>א<קטע סוף=דף כ א/>')


def test_end_tag_without_start_raises():
    with pytest.raises(SegmentError, match="end tag without a start"):
        _seg(_sec("א") + "ב<קטע סוף=דף כ ב/>")
