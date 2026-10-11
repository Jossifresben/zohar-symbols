"""UI strings (strings.json) and the `t()` template helper. g.lang is set per request in web/views/__init__.py (URL prefix)."""
import json
from pathlib import Path

from flask import g

STRINGS_PATH = Path(__file__).parent / "strings.json"


def init_i18n(app) -> None:
    strings = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))

    def t(key: str, **kw) -> str:
        entry = strings.get(key)
        if entry is None:
            if app.testing:
                raise KeyError(key)
            return key
        return entry[g.get("lang", "en")].format(**kw)

    @app.context_processor
    def _ctx():
        return {"lang": g.get("lang", "en")}

    app.jinja_env.globals["t"] = t


_CACHE: dict = {}


def get_string(key: str, lang: str, **kw) -> str:
    """Request-free lookup with the same semantics as `t` (a missing key raises KeyError)."""
    if "strings" not in _CACHE:
        _CACHE["strings"] = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))
    entry = _CACHE["strings"].get(key)
    if entry is None:
        raise KeyError(key)
    return entry.get(lang, entry["en"]).format(**kw)
