import json


def test_scholars_page(client):
    html = client.get("/scholars").get_data(as_text=True)
    assert "PMI" in html and "tables_version" in html.lower()
    assert "We are not scholars" in html
    assert "/api/pairs.csv" in html and "/api/meta.json" in html
    assert "[DOI pending]" in html
    assert html.count('data-copy=') == 3 and "app.js" in html
    assert "data/SOURCES.md" in html and "CC BY-SA 4.0" in html


def test_scholars_page_es_has_no_english_ui(client):
    html = client.get("/es/scholars").get_data(as_text=True)
    assert "No somos especialistas" in html
    assert "We are not scholars" not in html and "Provenance" not in html and "Method" not in html


def test_scholars_counts_from_data(client):
    import re
    html = client.get("/scholars").get_data(as_text=True)
    assert re.search(r'data-n="passages">\d+<', html) and re.search(r'data-n="symbols">\d+<', html) and re.search(r'data-n="with_root">\d+<', html)


def test_about_pages(client):
    assert "No somos" in client.get("/es/about").get_data(as_text=True)
    en = client.get("/about").get_data(as_text=True)
    assert "0009-0000-2026-0836" in en and "issues/new" in en and "We are not scholars" in en
    assert 'href="/about"' in client.get("/").get_data(as_text=True)


def test_api_symbol_csv_and_json(client):
    r = client.get("/api/symbol/moon.csv")
    assert r.status_code == 200 and r.mimetype == "text/csv"
    raw = r.get_data()
    assert raw.startswith(b"\xef\xbb\xbf# tables_version=")
    text = raw.decode("utf-8-sig").splitlines()
    assert text[1] == "passage_id,citation,position,matched_form,via"
    assert "1.020a.001" in raw.decode() and len(text) == 2 + 5
    j = client.get("/api/symbol/moon.json").get_json()
    assert j["tables_version"] and len(j["mentions"]) == 5 and len({m["passage_id"] for m in j["mentions"]}) == 4 and j["symbol"]["id"] == "moon"
    assert set(j["mentions"][0]) == {"passage_id", "citation", "position", "matched_form", "via"}


def test_api_hebrew_unescaped(client):
    body = client.get("/api/symbols.json").get_data(as_text=True)
    assert "סיהרא" not in body or "\\u05" not in body
    assert "\\u05" not in body


def test_api_unknown_404_json(client):
    r = client.get("/api/symbol/nope.json")
    assert r.status_code == 404 and r.get_json()["error"] and r.get_json()["tables_version"]
    assert client.get("/api/symbol/nope.csv").status_code == 404


def test_api_meta_pairs_symbols(client):
    m = client.get("/api/meta.json").get_json()
    assert m["tables_version"] and m["tables_version"] == m["meta"]["tables_version"]
    p = client.get("/api/pairs.csv")
    assert p.mimetype == "text/csv" and p.get_data().startswith(b"\xef\xbb\xbf# tables_version=")
    assert p.get_data(as_text=True).splitlines()[1].lstrip("﻿") == "symbol_a,symbol_b,passages_together,pmi"
    s = client.get("/api/symbols.json").get_json()
    assert s["tables_version"] and {x["id"] for x in s["symbols"]} >= {"moon", "sun"}


def test_queries_new(app):
    from web import queries
    with app.app_context():
        sh = queries.token_shares()
        assert sh["with_root"] > 0 and sh["tokens"] == sh["with_root"] + sh["non_lexical"] + sh["unknown"] and 0 <= sh["conf_high"] <= sh["tokens"]
        assert len(queries.symbol_mentions("moon", "en")) == 5
        assert any(r["id"] == "moon" for r in queries.symbols_table("en"))
        assert queries.all_pairs() is not None and queries.alias_count() > 0
