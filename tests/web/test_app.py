import sqlite3


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["tables_version"]


def test_missing_db_raises(tmp_path):
    import pytest
    from web import create_app
    with pytest.raises(FileNotFoundError):
        create_app(str(tmp_path / "nope.sqlite"))


def test_fixture_has_stream_passage(fixture_db):
    con = sqlite3.connect(f"file:{fixture_db}?mode=ro", uri=True)
    try:
        row = con.execute("select stream from passage where id='1.020b.003'").fetchone()
    finally:
        con.close()
    assert row == ("raaya_meheimna",)


def test_base_layout_renders(client, fixture_db):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    con = sqlite3.connect(f"file:{fixture_db}?mode=ro", uri=True)
    try:
        version = con.execute("select value from meta where key='tables_version'").fetchone()[0]
    finally:
        con.close()
    assert "זֹהַר" in html and "/scholars" in html and f"v{version}" in html


def test_db_is_read_only(app):
    import sqlite3 as s
    import pytest
    from web import db
    with app.app_context():
        with pytest.raises(s.OperationalError):
            db.get_db().execute("create table x(a)")


def test_json_not_ascii_escaped(app):
    assert app.json.ensure_ascii is False


def test_env_db_fallback(fixture_db, monkeypatch):
    from web import create_app
    monkeypatch.setenv("ZOHAR_DB", str(fixture_db))
    assert create_app().config["DB_PATH"] == str(fixture_db)


def test_t_raises_keyerror_in_testing(app):
    import pytest
    with app.test_request_context("/"):
        app.preprocess_request()
        assert app.jinja_env.globals["t"]("nav_symbols") == "Symbols"
        with pytest.raises(KeyError):
            app.jinja_env.globals["t"]("no_such_key")
