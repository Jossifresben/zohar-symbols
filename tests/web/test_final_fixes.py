"""Final whole-branch review fixes: licence footer, number format, copy, a11y, Spanish partners."""
import re


def test_footer_states_the_licence_not_public_domain(app):
    for path in ("/", "/es/", "/symbol/nope"):
        html = app.test_client().get(path).get_data(as_text=True)
        foot = html.split('<footer class="site-footer">')[1]
        assert "CC BY-SA 4.0" in foot
        assert "public domain" not in foot and "dominio público" not in foot


def test_num_filter_thousands_separators(app):
    from flask import g, render_template_string
    with app.test_request_context("/"):
        g.lang = "en"
        assert render_template_string("{{ 15909|num }}|{{ 7|num }}") == "15,909|7"
        g.lang = "es"
        assert render_template_string("{{ 15909|num }}|{{ 1234567|num }}") == "15.909|1.234.567"


def test_partners_spanish_word_is_not_havraya(app):
    es = app.test_client().get("/es/symbol/moon").get_data(as_text=True)
    assert "Acompañantes" in es and "Compañeros" not in es
    en = app.test_client().get("/symbol/moon").get_data(as_text=True)
    assert ">Partners<" in en


def test_orientation_copy_makes_no_translation_claim(app):
    en = app.test_client().get("/").get_data(as_text=True)
    assert "in the original Aramaic" in en and "in translation" not in en and "(coming soon)" in en
    es = app.test_client().get("/es/").get_data(as_text=True)
    assert "arameo original" in es and "(próximamente)" in es and "traducido" not in es


def test_a11y_headings_and_nav_labels(app):
    for path in ("/ask", "/es/ask", "/nope", "/passage/9.999z.999", "/sefirah/nope"):
        html = app.test_client().get(path).get_data(as_text=True)
        assert len(re.findall(r"<h1[ >]", html)) == 1, path
        assert re.search(r'<nav class="site-nav" aria-label="(Site|Sitio)"', html), path
    html = app.test_client().get("/nope").get_data(as_text=True)
    assert '<a href="/">Back to the home page</a>' in html
    html = app.test_client().get("/passage/1.020b.002").get_data(as_text=True)
    assert '<nav class="folio-nav" aria-label="Folio navigation"' in html


def test_tree_hebrew_text_is_tagged(app):
    html = app.test_client().get("/tree").get_data(as_text=True)
    assert 'lang="he"' in html and html.count('lang="he"') >= 11


def test_state_marker_roots_joined_with_middots(app):
    html = app.test_client().get("/symbol/moon").get_data(as_text=True)
    assert not re.search(r'<span class="heb muted"[^>]*>[^<]*,', html)


def test_tap_targets_css():
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "web" / "static" / "app.css").read_text(encoding="utf-8")
    assert re.search(r"\.site-nav a\{[^}]*min-height:44px", css) and re.search(r"\.lang-btn\{[^}]*min-height:44px", css)
