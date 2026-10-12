def test_idrot_page_both_languages(client):
    html = client.get("/idrot").get_data(as_text=True)
    assert "The Idrot" in html and 'href="/idrot"' in html   # the fixture has no Idra passages: header and nav only
    es = client.get("/es/idrot").get_data(as_text=True)
    assert "Las Idrot" in es


def test_idra_query_shape(app):
    from web import queries as q
    with app.app_context():
        assert q.idra("idra_zuta", "en") is None   # none in the fixture


def test_idra_on_real_db():
    import pytest
    from pathlib import Path
    real = Path(__file__).resolve().parents[2] / "data" / "zohar.sqlite"
    if not real.exists():
        pytest.skip("real database not built")
    from web import create_app, queries as q
    app = create_app(str(real))
    with app.test_request_context("/idrot"):
        d = q.idra("idra_zuta", "en")
        assert d["passages"] == 141 and d["first_cite"] == "Zohar III:287b" and d["top_symbols"]
        assert d["translated"] == len(d["read"]) >= 41
    html = app.test_client().get("/es/idrot").get_data(as_text=True)
    assert "Idra Zutá" in html and "אדרא זוטא" in html and "Empezar a leer en Zohar III:287b" in html
