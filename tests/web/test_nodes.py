import re

from web import queries


def test_node_page_malkhut(client):
    html = client.get("/sefirah/malkhut").get_data(as_text=True)
    assert "מלכות" in html and 'href="/symbol/moon"' in html and 'href="/tree"' in html


def test_node_404_lists_valid_ids(client):
    r = client.get("/sefirah/nope")
    html = r.get_data(as_text=True)
    assert r.status_code == 404 and "/sefirah/malkhut" in html and "No such sefirah" in html


def test_tree_has_ten_links_and_provenance(client):
    html = client.get("/tree").get_data(as_text=True)
    assert html.count('href="/sefirah/') >= 11 and "1652" in html


def test_tree_twelve_distinct_links_and_a11y(client):
    html = client.get("/tree").get_data(as_text=True)
    assert len(set(re.findall(r'href="(/sefirah/[a-z_]+)"', html))) == 12
    assert 'role="img"' in html and 'aria-label="The Tree of Life as a map"' in html
    assert html.count("<line") == 22 and html.count("<circle") == 11


def test_all_node_pages_ok_both_languages(client):
    for prefix in ("", "/es"):
        for nid in queries.NODE_ORDER:
            assert client.get(f"{prefix}/sefirah/{nid}").status_code == 200, (prefix, nid)


def test_es_node_page_is_spanish(client):
    html = client.get("/es/sefirah/malkhut").get_data(as_text=True)
    assert "La décima sefirá" in html and "Maljut" in html
    assert "The tenth sefirah" not in html and "Appears alongside" not in html
    assert 'href="/es/symbol/moon"' in html and 'href="/es/tree"' in html


def test_es_tree_and_404(client):
    html = client.get("/es/tree").get_data(as_text=True)
    assert "El Árbol de la Vida como mapa" in html and "/es/sefirah/malkhut" in html
    r = client.get("/es/sefirah/nope")
    assert r.status_code == 404 and "No existe esa sefirá" in r.get_data(as_text=True)


def test_every_node_has_intro_both_languages():
    from web.i18n import get_string
    for nid in queries.NODE_ORDER:
        for lang in ("en", "es"):
            assert len(get_string(f"node_intro_{nid}", lang)) > 40
