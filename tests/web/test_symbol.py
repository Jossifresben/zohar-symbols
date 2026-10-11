import re


def test_symbol_page_moon(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    assert "Moon" in html and "סיהרא" in html
    assert 'href="/symbol/sun"' in html            # top partner bar
    assert "full" in html and "diminished" in html  # declared states
    assert 'href="/passage/1.020b.001"' in html     # surfaced card
    assert "not yet translated" in html.lower() or "sin traducir" in html.lower()


def test_symbol_page_zero_mentions(client):
    r = client.get("/symbol/mouth_of_river")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "not yet found" in html.lower()
    assert 'class="bar' not in html  # no partners, no strata bars


def test_unknown_symbol_404_with_suggestions(client):
    r = client.get("/symbol/mooon")
    assert r.status_code == 404 and 'href="/symbol/moon"' in r.get_data(as_text=True)


def test_non_symbol_404_still_renders(client):
    r = client.get("/zzzzzz/qqqqqq")
    assert r.status_code == 404 and "Nothing here" in r.get_data(as_text=True)


def test_highlight_filter(app):
    from web.views import highlight
    out = highlight("שמשא וסיהרא הוו", [dict(position=1, symbol_id="moon", matched_form="סיהרא")])
    assert '<a class="mention" href="/symbol/moon">וסיהרא</a>' in out and out.startswith("שמשא ")


def test_highlight_filter_es_prefix_and_escape(app):
    from flask import g
    from web.views import highlight
    with app.test_request_context("/es/"):
        g.lang = "es"
        out = highlight("שמשא <b>וסיהרא</b>", [dict(position=0, symbol_id="moon", matched_form="שמשא")])
    assert '<a class="mention" href="/es/symbol/moon">שמשא</a>' in out and "<b>" not in out


def test_symbol_page_numbers(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    assert "4 passages" in html                   # count_passages chip
    assert "3 passages together" in html          # top partner (sun)
    assert "3 passages without a state marker" in html


def test_evidence_bar_widths_are_integers(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    widths = re.findall(r'class="bar[^"]*"[^>]*style="width:([^%"]*)%', html)
    assert widths
    for w in widths:
        assert w.isdigit() and 0 <= int(w) <= 100


def test_stream_label_on_raaya_card(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    card = html.split('href="/passage/1.020b.003"')[1].split("</article>")[0]
    assert "Ra&#39;aya Meheimna" in card or "Ra'aya Meheimna" in card


def test_symbol_page_es_has_no_english_ui(client):
    html = client.get("/es/symbol/moon").get_data(as_text=True)
    for word in ("Appears alongside", "How it moves", "Partners", "States", "Read it", "Where in the book",
                 "For scholars", "passages", "not yet translated", "Main body", "Co-occurrence"):
        assert word not in html, word
    assert "Aparece junto a" in html and "Léelo" in html


def test_symbol_links_resolve(client):
    for prefix in ("", "/es"):
        html = client.get(f"{prefix}/symbol/moon").get_data(as_text=True)
        hrefs = set(re.findall(r'href="(/[^"#]*)', html))
        for h in hrefs:
            if h.startswith("/static/"):
                continue
            assert client.get(h).status_code == 200, h


def test_partners_return_node(app):
    from web import queries
    with app.app_context():
        ps = queries.partners("moon", "en")
    assert ps and all("node" in p for p in ps)


def _fixture_texts(app):
    from web import db
    with app.app_context():
        return [r["text_ar"] for r in db.all("select text_ar from passage")]


def test_highlight_reproduces_text_without_mentions(app):
    from markupsafe import escape
    from web.views import highlight
    texts = _fixture_texts(app)
    assert texts
    for text in texts:
        assert highlight(text, []) == escape(text)


def test_highlight_reproduces_real_passages():
    import sqlite3
    from pathlib import Path
    from markupsafe import escape
    from web.views import highlight
    import pytest
    path = Path(__file__).resolve().parents[2] / "data" / "zohar.sqlite"
    if not path.exists():
        pytest.skip("real database not built")
    con = sqlite3.connect(path)
    texts = [r[0] for r in con.execute("select text_ar from passage order by random() limit 50")]
    for text in texts:
        assert highlight(text, []) == escape(text)


def test_highlight_positions_match_tokenize_on_real_text(app):
    """Every mention's wrapped text is the pipeline's matched token (positions agree with tokenize)."""
    from web import queries
    from web.views import highlight
    from pipeline.lemmatise import tokenize
    with app.app_context():
        for pid in ("1.020a.001", "1.020a.002", "1.020b.001", "1.020b.002", "1.020b.003"):
            p = queries.passage(pid, "en")
            toks = tokenize(p["text_ar"])
            out = str(highlight(p["text_ar"], p["mentions"]))
            assert out.count('class="mention"') == len({m["position"] for m in p["mentions"]})
            for m in p["mentions"]:
                assert f'>{toks[m["position"]]}</a>' in out or toks[m["position"]].replace("״", '"') in out


def test_highlight_keeps_punctuation_and_ignores_out_of_range():
    from web.views import highlight
    text = "כי הוא חלקך בחיים-- דא הוא שמשא, בסיהרא (שם ב יא). ר' אבא"
    out = str(highlight(text, [dict(position=7, symbol_id="moon", matched_form="סיהרא"),
                               dict(position=99, symbol_id="sun", matched_form="x")]))
    assert 'שמשא, <a class="mention" href="/symbol/moon">בסיהרא</a> (שם ב יא).' in out
    assert "/symbol/sun" not in out and "ר&#39; אבא" in out


def test_highlight_prefers_page_symbol_on_cotagged_token():
    from web.views import highlight
    ms = [dict(position=0, symbol_id="zz", matched_form="a"), dict(position=0, symbol_id="moon", matched_form="a")]
    assert 'href="/symbol/moon"' in str(highlight("סיהרא", ms))          # first by id
    assert 'href="/symbol/zz"' in str(highlight("סיהרא", ms, prefer="zz"))


def test_states_order_and_strata_chip(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    assert html.index(">full<") < html.index(">diminished<")
    assert "Across 2 strata" in html or "Across 3 strata" in html or "Only in" in html
    assert 'aria-label="Breadcrumb"' in html
