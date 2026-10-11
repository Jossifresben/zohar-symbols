"""UI strings (strings.json) and the `t()` template helper. g.lang is set per request in web/views/__init__.py (URL prefix)."""
import json
from pathlib import Path

from flask import g, request, url_for

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

    def lang_url(endpoint: str, **values) -> str:
        """Absolute endpoint in the current language's blueprint (works on 404 pages too)."""
        return url_for(("site_es." if g.get("lang") == "es" else "site.") + endpoint, **values)

    def switch_url(lang: str) -> str:
        """The current page in `lang`; falls back to the home page when there is no matching endpoint."""
        ep = request.endpoint
        if ep and ep.split(".")[0] in ("site", "site_es"):
            return url_for(("site_es." if lang == "es" else "site.") + ep.split(".")[-1], **(request.view_args or {}))
        return "/es/" if lang == "es" else "/"

    app.jinja_env.globals.update(t=t, lang_url=lang_url, switch_url=switch_url)


_CACHE: dict = {}


def get_string(key: str, lang: str, **kw) -> str:
    """Request-free lookup with the same semantics as `t` (a missing key raises KeyError)."""
    if "strings" not in _CACHE:
        _CACHE["strings"] = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))
    entry = _CACHE["strings"].get(key)
    if entry is None:
        raise KeyError(key)
    return entry.get(lang, entry["en"]).format(**kw)
