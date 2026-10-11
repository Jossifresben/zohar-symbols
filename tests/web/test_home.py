import re


def test_home_renders_clusters_and_moon(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'href="/symbol/moon"' in html and "סיהרא" in html
    order = re.findall(r'data-cluster="(\w+)"', html)
    assert order.index("malkhut") < order.index("tiferet")  # Shekhinah cluster first
    assert order[0] == "malkhut"
    assert 'class="chip" data-kind="event"' in html


def test_search(client):
    r = client.get("/search?q=moon")
    assert r.status_code == 200 and 'href="/symbol/moon"' in r.get_data(as_text=True)


def test_search_empty_is_home(client):
    r = client.get("/search?q=")
    assert r.status_code == 200 and "The Zohar speaks in images" in r.get_data(as_text=True)


def test_home_es_prefix(client):
    assert client.get("/es/").status_code == 200


def test_home_es_titles(client):
    html = client.get("/es/").get_data(as_text=True)
    assert "La Shejiná" in html and "The Shekhinah" not in html
    assert 'href="/es/symbol/moon"' in html


def test_every_chip_and_card_link_resolves(client):
    for prefix in ("", "/es"):
        html = client.get(f"{prefix}/").get_data(as_text=True)
        hrefs = set(re.findall(r'<a class="(?:chip|more|card orient-card)[^"]*"[^>]*?href="([^"]+)"', html))
        assert hrefs
        for h in hrefs:
            assert client.get(h).status_code == 200, h


def test_events_not_duplicated_in_node_cards(client):
    html = client.get("/").get_data(as_text=True)
    node_part = html.split('data-cluster="events"')[0]
    assert 'class="chip" data-kind="event"' not in node_part


def test_orientation_cards_in_links(client):
    html = client.get("/").get_data(as_text=True)
    hrefs = set(re.findall(r'<a class="(?:chip|more|card orient-card)[^"]*"[^>]*?href="([^"]+)"', html))
    assert {"/tree", "/ask"} <= hrefs and any(h.startswith("/passage/") for h in hrefs)


def test_404_in_es_is_spanish(client):
    html = client.get("/es/nope").get_data(as_text=True)
    assert "Símbolos" in html and 'lang="es"' in html
    assert 'href="/es/ask"' in html  # header links stay in Spanish on 404


def test_switch_url(client):
    html = client.get("/symbol/moon").get_data(as_text=True)
    assert 'href="/es/symbol/moon" hreflang="es"' in html
    html = client.get("/es/symbol/moon").get_data(as_text=True)
    assert 'href="/symbol/moon" hreflang="en"' in html
    html = client.get("/es/nope").get_data(as_text=True)
    assert 'href="/" hreflang="en"' in html and 'href="/es/" hreflang="es"' in html


def test_search_by_kind(client):
    html = client.get("/search?kind=event").get_data(as_text=True)
    assert "Events" in html and "The Zohar speaks in images" in html
    assert client.get("/search?kind=bogus").status_code == 200


def test_events_cap_links_to_kind_search(app):
    from web.views.home import build_clusters, TOP_N
    with app.test_request_context("/"):
        ev = [c for c in build_clusters("en") if c["key"] == "events"][0]["parts"][0]
        assert len(ev["chips"]) <= TOP_N and ev["more"] == max(0, ev["total"] - TOP_N)


def test_stubs_have_no_english_in_es(client):
    assert "Pronto podrás" in client.get("/es/ask").get_data(as_text=True)
