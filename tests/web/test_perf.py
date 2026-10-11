import time
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parent.parent.parent / "data" / "zohar.sqlite"
needs_real = pytest.mark.skipif(not REAL.exists(), reason="real database not built")
PAGES = ["/", "/es/", "/symbol/moon", "/symbol/holy_one", "/sefirah/malkhut", "/scholars", "/es/scholars", "/healthz"]


@pytest.fixture(scope="module")
def real_client():
    from web import create_app
    app = create_app(str(REAL))
    app.config["TESTING"] = True
    return app.test_client()


def test_cached_returns_warm_values_and_rejects_unknown(client):
    from web import queries
    app = client.application
    with app.app_context():
        assert queries.cached("meta") == app.config["CACHE"]["meta"]
        assert queries.cached("nodes_with_symbols", "es")[0]["node"] == "keter"
        assert queries.cached("scholars_pairs", "en") is not None
        for k in ("token_shares", "passage_totals", "alias_count"):
            queries.cached(k)
        with pytest.raises(KeyError):
            queries.cached("nope")
        with pytest.raises(KeyError):
            queries.cached("nodes_with_symbols", "fr")


def test_requests_do_not_recompute_cached_queries(client, monkeypatch):
    from web import queries
    def boom(*a, **k):
        raise AssertionError("recomputed per request")
    for name in ("token_shares", "passage_totals", "alias_count", "scholars_pairs", "nodes_with_symbols", "meta"):
        monkeypatch.setattr(queries, name, boom)
    assert client.get("/").status_code == 200
    assert client.get("/es/scholars").status_code == 200


def test_healthz_reports_cache_warm_ms(client):
    j = client.get("/healthz").get_json()
    assert j["ok"] is True and isinstance(j["cache_warm_ms"], (int, float)) and j["cache_warm_ms"] >= 0


@needs_real
def test_home_and_symbol_render_fast(real_client):
    for path in PAGES:
        t0 = time.perf_counter()
        r = real_client.get(path)
        dt = time.perf_counter() - t0
        assert r.status_code == 200 and dt < 0.3, (path, dt)


@needs_real
def test_real_db_symbol_and_node_pages_all_render(real_client):
    from web import db, queries
    with real_client.application.app_context():
        sids = [r["id"] for r in db.all("select id from symbol")]
    assert len(sids) == 139
    for sid in sids:
        assert real_client.get(f"/symbol/{sid}").status_code == 200, sid
    assert len(queries.NODE_ORDER) == 12
    for nid in queries.NODE_ORDER:
        assert real_client.get(f"/sefirah/{nid}").status_code == 200, nid
