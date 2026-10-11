import re


def test_home_renders_clusters_and_moon(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'href="/symbol/moon"' in html and "סיהרא" in html
    assert html.index("malkhut") < html.index("tiferet")  # Shekhinah cluster first
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
        hrefs = set(re.findall(r'<a class="(?:chip|more|orient)[^"]*" [^>]*?href="([^"]+)"', html))
        assert hrefs
        for h in hrefs:
            assert client.get(h).status_code == 200, h


def test_events_not_duplicated_in_node_cards(client):
    html = client.get("/").get_data(as_text=True)
    node_part = html.split('data-cluster="events"')[0]
    assert 'class="chip" data-kind="event"' not in node_part
