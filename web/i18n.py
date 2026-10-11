"""UI strings (strings.json) and the `t()` template helper. g.lang is set per request in web/views/__init__.py (URL prefix)."""
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from flask import abort, g, redirect, request, url_for

STRINGS_PATH = Path(__file__).parent / "strings.json"
COOKIE_MAX_AGE = 365 * 24 * 3600  # one year
LANGS = ("en", "es")


def _set_lang_cookie(response, lang: str) -> None:
    response.set_cookie("lang", lang, max_age=COOKIE_MAX_AGE, path="/", samesite="Lax",
                        httponly=True, secure=request.is_secure)


def safe_next(nxt: str | None) -> str:
    """A same-site relative path starting with a single "/", else "/" (no scheme, host, backslash or control chars)."""
    if not nxt or not nxt.startswith("/") or nxt.startswith("//") or "\\" in nxt or re.search(r"[\x00-\x20\x7f]", nxt):
        return "/"
    parts = urlsplit(nxt)
    return nxt if not parts.scheme and not parts.netloc else "/"


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
        home = "/es/" if lang == "es" else "/"
        if ep and ep.split(".")[0] in ("site", "site_es") and ep.split(".")[-1] != "home":
            # Deep links switch directly (the target page resets the cookie). Query keys are never url_for kwargs.
            url = url_for(("site_es." if lang == "es" else "site.") + ep.split(".")[-1], **(request.view_args or {}))
            return url + ("?" + urlencode(list(request.args.lists()), doseq=True) if request.args else "")
        # Root and 404s go through /lang/ so the cookie is reset before "/" is reached (else "/" bounces to /es/).
        return url_for("set_lang", code=lang, next=home)

    @app.route("/lang/<code>")
    def set_lang(code):
        if code not in LANGS:
            abort(404)
        response = redirect(safe_next(request.args.get("next")), code=302)
        _set_lang_cookie(response, code)
        return response

    @app.before_request
    def _remembered_language():
        """Only the bare root honours the cookie; deep links are never redirected, and Accept-Language is ignored."""
        if request.path == "/" and request.cookies.get("lang") == "es":
            qs = request.query_string.decode("utf-8", "replace")
            return redirect("/es/" + ("?" + qs if qs else ""), code=302)

    @app.after_request
    def _remember_language(response):
        """Every HTML page (200 or 404) remembers its language; redirects, static files and the API do not."""
        if response.mimetype == "text/html" and not 300 <= response.status_code < 400 and request.endpoint != "static":
            _set_lang_cookie(response, g.get("lang", "en"))
        if request.path == "/":
            response.vary.add("Cookie")
        return response

    app.jinja_env.filters["num"] = lambda n: fmt_num(n, g.get("lang", "en"))
    app.jinja_env.globals.update(t=t, lang_url=lang_url, switch_url=switch_url)


def fmt_num(n, lang: str) -> str:
    """Thousands separators: 15,909 in English, 15.909 in Spanish."""
    s = f"{int(n):,}"
    return s.replace(",", ".") if lang == "es" else s


_CACHE: dict = {}


def get_string(key: str, lang: str, **kw) -> str:
    """Request-free lookup with the same semantics as `t` (a missing key raises KeyError)."""
    if "strings" not in _CACHE:
        _CACHE["strings"] = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))
    entry = _CACHE["strings"].get(key)
    if entry is None:
        raise KeyError(key)
    return entry.get(lang, entry["en"]).format(**kw)
