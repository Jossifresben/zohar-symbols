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
