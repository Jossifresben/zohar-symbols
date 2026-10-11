import importlib
import sys


def test_wsgi_app_is_proxyfixed(monkeypatch, fixture_db):
    monkeypatch.setenv("ZOHAR_DB", str(fixture_db))
    sys.modules.pop("web.wsgi", None)
    mod = importlib.import_module("web.wsgi")
    assert callable(mod.app)
    assert mod.app.wsgi_app.__class__.__name__ == "ProxyFix"
    sys.modules.pop("web.wsgi", None)
