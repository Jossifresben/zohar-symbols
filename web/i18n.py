"""UI strings (strings.json) and the `t()` template helper. g.lang is set per request in web/views/__init__.py (URL prefix)."""
import json
from pathlib import Path

from flask import g, redirect, request, url_for

STRINGS_PATH = Path(__file__).parent / "strings.json"
COOKIE_MAX_AGE = 365 * 24 * 3600  # one year


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
        """The current page in `lang`, query string included; falls back to the home page when there is no
        matching endpoint (404s)."""
        ep = request.endpoint
        if ep and ep.split(".")[0] in ("site", "site_es"):
            # Path arguments win over same-named query keys; "_"-keys would be url_for options, not query.
            args = {k: v for k, v in request.args.to_dict(flat=False).items() if not k.startswith("_")}
            args.update(request.view_args or {})
            return url_for(("site_es." if lang == "es" else "site.") + ep.split(".")[-1], **args)
        return "/es/" if lang == "es" else "/"

    @app.before_request
    def _remembered_language():
        """Only the bare root honours the cookie; deep links are never redirected, and Accept-Language is ignored."""
        if request.path == "/" and request.cookies.get("lang") == "es":
            return redirect("/es/", code=302)

    @app.after_request
    def _remember_language(response):
        """Every HTML page (200 or 404) remembers its language; redirects, static files and the API do not."""
        if response.mimetype == "text/html" and not 300 <= response.status_code < 400 and request.endpoint != "static":
            response.set_cookie("lang", g.get("lang", "en"), max_age=COOKIE_MAX_AGE, path="/", samesite="Lax")
        if request.path == "/":
            response.vary.add("Cookie")
        return response

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
