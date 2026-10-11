import re

from web import queries


def test_node_page_malkhut(client):
    html = client.get("/sefirah/malkhut").get_data(as_text=True)
    assert "מלכות" in html and 'href="/symbol/moon"' in html and 'href="/tree"' in html


def test_node_404_lists_valid_ids(client):
    r = client.get("/sefirah/nope")
    html = r.get_data(as_text=True)
    assert r.status_code == 404 and "/sefirah/malkhut" in html and "No such sefirah" in html


def test_tree_twelve_distinct_links_and_a11y(client):
    html = client.get("/tree").get_data(as_text=True)
    assert len(set(re.findall(r'href="(/sefirah/[a-z_]+)"', html))) == 12
    assert 'role="img"' in html and 'aria-label="Tree of Life diagram: ten sefirot joined by twenty-two paths"' in html
    assert html.count("<line") == 22 and html.count("<circle") == 11
    assert "1652" in html


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


# 22 paths of the Kircher/Golden Dawn layout, as in cosmicoach-astro-integrada/qabalah.py; the controller's Task 5 dispatch lists them.
BRIEF_PATHS = {frozenset(p) for p in [(1, 2), (1, 3), (1, 6), (2, 3), (2, 4), (2, 6), (3, 5), (3, 6), (4, 5), (4, 6), (4, 7), (5, 6),
                                      (5, 8), (6, 7), (6, 8), (6, 9), (7, 8), (7, 9), (7, 10), (8, 9), (8, 10), (9, 10)]}


def test_tree_paths_match_brief_and_render(client):
    from web.views import tree as tv
    assert len(tv.PATHS) == 22 and {frozenset(p) for p in tv.PATHS} == BRIEF_PATHS
    coord = {(round(x * 600), round(y * 800)): i + 1 for i, (_, x, y) in enumerate(tv.SEFIROT)}
    html = client.get("/tree").get_data(as_text=True)
    got = set()
    for x1, y1, x2, y2 in re.findall(r'<line x1="(\d+)" y1="(\d+)" x2="(\d+)" y2="(\d+)"', html):
        got.add(frozenset((coord[(int(x1), int(y1))], coord[(int(x2), int(y2))])))
    assert got == BRIEF_PATHS


def test_no_pillar_chip_outside_the_pillars(client):
    for nid in ("ein_sof", "sitra_ahra"):
        html = client.get(f"/sefirah/{nid}").get_data(as_text=True)
        assert "pillar" not in html.lower()
    assert "Middle pillar" in client.get("/sefirah/tiferet").get_data(as_text=True)


def test_tree_anchor_has_visible_focus_ring():
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "web" / "static" / "app.css").read_text(encoding="utf-8")
    assert ".tree-node:focus-visible{outline:" in css.replace(" {", "{")
