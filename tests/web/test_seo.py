import re


def _meta(html, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), html)
    return m.group(1) if m else None


def test_home_meta_and_alternates(client):
    html = client.get("/").get_data(as_text=True)
    assert _meta(html, "description").startswith("A computed dictionary")
    assert '<link rel="canonical" href="https://zohar.digital/">' in html
    assert 'hreflang="es" href="https://zohar.digital/es/"' in html and 'hreflang="x-default" href="https://zohar.digital/"' in html
    assert _meta(html, "og:image") == "https://zohar.digital/static/og/og-en.png" and _meta(html, "twitter:card") == "summary_large_image"
    es = client.get("/es/").get_data(as_text=True)
    assert _meta(es, "og:image").endswith("og-es.png") and _meta(es, "og:locale") == "es_ES"
    assert _meta(es, "description").startswith("Diccionario computado")


def test_symbol_passage_node_descriptions(client):
    s = client.get("/symbol/matronita").get_data(as_text=True)
    assert "in the Zohar, a symbol of" in _meta(s, "description") and _meta(s, "og:title").startswith("Matronita")
    assert '<link rel="canonical" href="https://zohar.digital/symbol/matronita">' in s
    p = client.get("/es/passage/1.020b.002").get_data(as_text=True)
    assert _meta(p, "description").startswith("Zohar I:20b")
    n = client.get("/sefirah/malkhut").get_data(as_text=True)
    assert "sefirah" in _meta(n, "description")


def test_search_and_404_are_noindex(client):
    assert '<meta name="robots" content="noindex">' in client.get("/search?q=moon").get_data(as_text=True)
    assert '<meta name="robots" content="noindex">' in client.get("/symbol/nope").get_data(as_text=True)


def test_sitemap_and_robots(client):
    r = client.get("/sitemap.xml")
    xml = r.get_data(as_text=True)
    assert r.mimetype == "application/xml"
    assert "<loc>https://zohar.digital/symbol/matronita</loc>" in xml and "<loc>https://zohar.digital/es/symbol/matronita</loc>" in xml
    assert "<loc>https://zohar.digital/passage/1.020b.002</loc>" in xml and 'hreflang="x-default"' in xml
    rb = client.get("/robots.txt").get_data(as_text=True)
    assert "Sitemap: https://zohar.digital/sitemap.xml" in rb and "Disallow: /lang/" in rb


def test_og_images_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "web" / "static" / "og"
    for lang in ("en", "es"):
        data = (root / f"og-{lang}.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(data[16:20], "big") == 1200 and int.from_bytes(data[20:24], "big") == 630
