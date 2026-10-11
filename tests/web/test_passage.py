import re


def test_passage_page_context_and_links(client):
    html = client.get("/passage/1.020b.002").get_data(as_text=True)
    assert "Zohar I:20b" in html and 'id="p2"' in html and 'href="/symbol/matronita"' in html
    assert 'href="/passage/1.020a.001#p1"' in html   # prev folio-side exists in the fixture
    assert re.search(r'<article class="para focus" id="p2"', html)
    assert 'heb pc-ar" lang="arc" dir="rtl"' in html and 'dir="rtl"' in html


def test_folio_symbols_list(client):
    html = client.get("/passage/1.020b.002").get_data(as_text=True)
    assert "Symbols in this folio" in html and "font-size:16px" in html


def test_passage_prev_next_within_folio(app):
    from web import queries as q
    with app.app_context():
        assert q.folio_neighbours(1, 20, "b") == ("1.020a.001", None)
        assert q.folio_neighbours(1, 20, "a") == (None, "1.020b.001")
        assert len(q.folio(1, 20, "b", "en")) == 3


def test_neighbours_skip_missing_folios(app):
    from web import queries as q
    with app.app_context():
        # 20a..20b are the only folio-sides: nothing at 19b / 21a is invented
        assert q.folio_neighbours(1, 21, "a") == ("1.020b.001", None)
        assert q.folio_neighbours(1, 19, "b") == (None, "1.020a.001")


def test_stream_passage_has_heading(client):
    html = client.get("/passage/1.020b.003").get_data(as_text=True)
    assert 'id="p3"' in html and "Ra" in html
    assert 'class="stream-h label"' in html
    main = client.get("/passage/1.020b.001").get_data(as_text=True)
    assert main.count('class="stream-h label"') == 2  # main heading, then the Ra'aya Meheimna paragraph of the same folio


def test_translation_attribution_or_not_translated(client):
    html = client.get("/passage/1.020b.001").get_data(as_text=True)
    assert "Translated by" in html or "not yet translated" in html


def test_es_page_has_no_english_ui(client):
    html = client.get("/es/passage/1.020b.002").get_data(as_text=True)
    assert "Símbolos en este folio" in html
    assert "Symbols in this folio" not in html and "Previous" not in html
    assert 'href="/es/passage/1.020a.001#p1"' in html


def test_passage_url_appends_para_fragment(app):
    from flask import g
    with app.test_request_context("/"):
        g.lang = "en"
        assert app.jinja_env.globals["passage_url"]("1.020b.002") == "/passage/1.020b.002#p2"
        g.lang = "es"
        assert app.jinja_env.globals["passage_url"]("1.020b.002") == "/es/passage/1.020b.002#p2"


def test_symbol_cards_use_fragment(client):
    html = client.get("/symbol/matronita").get_data(as_text=True)
    assert re.search(r'class="pc-cite" href="/passage/[^"#]+#p\d+"', html)


def test_unknown_passage_404(client):
    r = client.get("/passage/9.999z.999")
    assert r.status_code == 404
    assert "No such passage." in r.get_data(as_text=True)
    html = r.get_data(as_text=True)
    assert 'href="/passage/1.020a.001"' in html and "Zohar I:20a" in html  # fallback: the first passage
    assert "<h1" in html
    r = client.get("/es/passage/9.999z.999")
    assert "Ese pasaje no existe." in r.get_data(as_text=True)


def test_missing_passage_in_existing_folio_suggests_siblings(client):
    html = client.get("/passage/1.020b.099").get_data(as_text=True)
    assert 'href="/passage/1.020b.001"' in html and 'href="/passage/1.020a.001"' in html
    assert "Zohar I:20b" in html and "Zohar I:20a" in html
    html = client.get("/es/passage/1.020b.099").get_data(as_text=True)
    assert 'href="/es/passage/1.020b.001"' in html


def test_stream_headings_on_every_change():
    from flask import Flask
    from jinja2 import FileSystemLoader
    env = Flask(__name__, template_folder=str(__import__("pathlib").Path(__file__).resolve().parents[2] / "web" / "templates")).jinja_env
    tpl = env.from_string("""{% set ns = namespace(cur=none) %}{% for q in paras %}{% if q.stream != ns.cur %}{% set ns.cur = q.stream %}[{{ q.stream }}]{% endif %}{% endfor %}""")
    out = tpl.render(paras=[dict(stream=s) for s in ("main", "main", "raaya_meheimna", "raaya_meheimna", "main")])
    assert out == "[main][raaya_meheimna][main]"


def test_passage_page_headings_include_main(client):
    html = client.get("/passage/1.020b.002").get_data(as_text=True)
    assert html.count('class="stream-h label"') >= 2
    assert ">Main text<" in html and ">Ra&#39;aya Meheimna<" in html or ">Ra'aya Meheimna<" in html
    assert ">Texto principal<" in client.get("/es/passage/1.020b.002").get_data(as_text=True)
