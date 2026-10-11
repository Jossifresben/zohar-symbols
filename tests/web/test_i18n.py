"""Bilingual completeness: catalogue integrity, language cookie, switcher, and no-leak checks on every page."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
STRINGS = json.loads((WEB / "strings.json").read_text(encoding="utf-8"))

PAGES = ["/", "/search?q=moon", "/search?kind=event", "/symbol/moon", "/symbol/mouth_of_river",
         "/sefirah/malkhut", "/sefirah/ein_sof", "/tree", "/passage/1.020b.002", "/scholars", "/about", "/ask",
         "/symbol/nope", "/sefirah/nope", "/passage/9.999z.999"]
NOT_FOUND = {"/symbol/nope", "/sefirah/nope", "/passage/9.999z.999"}

# Unmistakable English UI words that must never reach a Spanish page (outside Hebrew/Aramaic and symbol labels).
EN_UI = ["Passages", "passages", "Partners", "States", "Read it", "Read", "Scholars", "scholars", "Where",
         "alongside", "Symbols", "Search", "Previous", "Next", "About", "Method", "Exports", "Cite", "Licences",
         "not yet", "coming soon", "Coming soon", "Results for", "Did you mean", "Nothing here", "Download",
         "Persons", "Objects", "Qualities", "Events", "Filter", "Breadcrumb", "Provenance", "Tables", "Strongest",
         "Caveat", "Copy", "Translated by", "Ask", "How it moves", "Also with", "Appears", "Right pillar",
         "Left pillar", "Middle pillar", "The Other Side", "home page", "Report a problem", "Who", "What this is",
         "No such", "Main body", "Across", "Only in"]
# And the reverse: Spanish UI words that must never reach an English page.
ES_UI = ["Pasajes", "pasajes", "Acompañantes", "Léelo", "Anterior", "Siguiente", "especialistas", "Símbolos",
         "Buscar", "Preguntar", "Leer", "Método", "Citar", "Licencias", "Acerca de", "Estados", "Próximamente",
         "Quizá", "Sucesos", "Columna", "Cómo se mueve", "sin traducir"]


def _visible_ui(html: str) -> str:
    """Page text minus what is legitimately bilingual: the wordmark, Hebrew/Aramaic, symbol chips and labels,
    the cross-language label line, scripts and attributes other than aria-label/placeholder/title."""
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r'<span class="wm-sub">.*?</span>', " ", html, flags=re.S)
    html = re.sub(r'<(span|p|h\d)[^>]*class="[^"]*\bheb\b[^"]*"[^>]*>.*?</\1>', " ", html, flags=re.S)
    html = re.sub(r'<a class="(chip|mention|top-partner|pc-cite)[^"]*"[^>]*>.*?</a>', " ", html, flags=re.S)
    html = re.sub(r'<p class="also muted">.*?</p>', " ", html, flags=re.S)
    html = re.sub(r'<span class="bar-label">.*?</span>', " ", html, flags=re.S)
    html = re.sub(r'<p class="pc-tr"[^>]*>.*?</p>', " ", html, flags=re.S)        # translations (model output)
    html = re.sub(r'<p class="claim display">.*?</p>', " ", html, flags=re.S)     # gloss: may quote labels
    html = re.sub(r'<p id="cite" class="cite[^"]*">.*?</p>', " ", html, flags=re.S)  # citations: the work's title
    html = re.sub(r'<pre id="cite-\w+">.*?</pre>', " ", html, flags=re.S)
    html = re.sub(r'hreflang="\w+">[A-Z]{2}<', ">", html)                          # EN | ES switcher
    keep = " ".join(re.findall(r'(?:aria-label|placeholder|title)="([^"]*)"', html))
    text = re.sub(r"<[^>]+>", " ", html)
    return text + " " + keep


def _found(words, text):
    return [w for w in words if re.search(r"(?<![\wÀ-ÿ])" + re.escape(w) + r"(?![\wÀ-ÿ])", text)]


def _get(client, path):
    client.delete_cookie("lang")
    return client.get(path)


# --- catalogue ---------------------------------------------------------------------------------------------

def test_every_key_has_both_languages_non_empty():
    for k, v in STRINGS.items():
        assert set(v) == {"en", "es"}, k
        assert v["en"].strip() and v["es"].strip(), k


def test_placeholders_match_between_languages():
    for k, v in STRINGS.items():
        assert set(re.findall(r"{(\w+)}", v["en"])) == set(re.findall(r"{(\w+)}", v["es"])), k


def _sources():
    files = list((WEB / "templates").glob("*.html")) + list((WEB / "templates").glob("*.svg"))
    files += list((WEB / "views").glob("*.py")) + list(WEB.glob("*.py"))
    return {f: f.read_text(encoding="utf-8") for f in files}


def _dynamic_families():
    from pipeline.segment import STREAMS
    from web import queries
    return {
        "node_": queries.NODE_ORDER, "node_intro_": queries.NODE_ORDER, "pillar_": sorted({v for v in queries.PILLAR.values() if v}),
        "kind_": queries.KINDS, "kind_one_": queries.KINDS, "state_": queries.STATE_ORDER,
        "stream_": list(STREAMS), "stratum_": list(STREAMS) + ["idra_rabba", "idra_zuta"],
        "sch_m_": ["corpus", "lemma", "tag", "cooc", "states", "surf", "resolve"],
        "sch_cite_": ["bibtex", "chicago", "sbl"], "src_": queries.SEED_SOURCES,
        "book_": [b.lower() for b in __import__("web.views", fromlist=["BOOKS"]).BOOKS],
    }


_CALL_KEY = r"\b(?:t|get_string)\(\s*['\"]([a-z0-9_]+)['\"](?!\s*~)"
_CALL_ELSE_KEY = r"\b(?:t|get_string)\(\s*['\"][a-z0-9_]+['\"]\s+if\s+[^()]*?\s+else\s+['\"]([a-z0-9_]+)['\"]"
_KWARG_KEY = r"\b(?:msg|title|message)=['\"]([a-z0-9_]+)['\"]"     # render_template(..., msg="key") in views
_DEFAULT_KEY = r"\|default\(\s*['\"]([a-z0-9_]+)['\"]\s*\)"         # t(msg|default('key')) in templates


def _referenced_literals():
    """(file, key) for every literal key: first arg of t()/get_string() (and the else-branch of an inline
    conditional there), render_template kwargs msg=/title=/message= in Python, |default('…') in templates,
    plus the title/blurb keys of the home CLUSTERS table."""
    out = set()
    for f, src in _sources().items():
        pats = [_CALL_KEY, _CALL_ELSE_KEY] + ([_KWARG_KEY] if f.suffix == ".py" else [_DEFAULT_KEY])
        for pat in pats:
            out |= {(f.name, k) for k in re.findall(pat, src)}
    from web.views.home import CLUSTERS
    out |= {("home.CLUSTERS", k) for c in CLUSTERS for k in c[3:] if k}
    return out


def test_every_referenced_key_exists():
    missing = {(f, k) for f, k in _referenced_literals() if k not in STRINGS}
    for prefix, suffixes in _dynamic_families().items():
        for s in suffixes:
            if prefix + s not in STRINGS:
                missing.add(("dynamic", prefix + s))
    assert not missing, sorted(missing)


def test_dynamic_families_match_the_code():
    found = set()
    for src in _sources().values():
        found |= set(re.findall(r"\bt\(\s*['\"]([a-z][a-z0-9_]*_)['\"]\s*~", src))
        found |= set(re.findall(r"\b(?:t|get_string)\(\s*f['\"]([a-z][a-z0-9_]*_)\{", src))
    assert found == set(_dynamic_families()), found ^ set(_dynamic_families())


def test_no_dead_keys():
    literals = {k for _, k in _referenced_literals()}
    dynamic = {p + s for p, ss in _dynamic_families().items() for s in ss}
    dead = sorted(k for k in STRINGS if k not in literals and k not in dynamic)
    assert not dead, dead


def test_missing_key_raises_in_testing(app):
    with app.test_request_context("/"):
        with pytest.raises(KeyError):
            app.jinja_env.globals["t"]("no_such_key")


# --- cookie and redirect -----------------------------------------------------------------------------------

def test_cookie_set_to_current_language(client):
    r = client.get("/es/symbol/moon")
    c = r.headers.get("Set-Cookie", "")
    assert "lang=es" in c and "Path=/" in c and "SameSite=Lax" in c and "Max-Age=31536000" in c and "HttpOnly" in c
    r = client.get("/symbol/moon")
    assert "lang=en" in r.headers.get("Set-Cookie", "")


def test_root_redirects_to_es_when_cookie_says_es(client):
    client.set_cookie("lang", "es")
    r = client.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/es/")


def test_deep_links_never_redirect_on_cookie(client):
    client.set_cookie("lang", "es")
    for p in ["/symbol/moon", "/tree", "/search?q=moon", "/scholars"]:
        assert client.get(p).status_code == 200, p


def test_root_without_cookie_is_english_regardless_of_accept_language(client):
    r = client.get("/", headers={"Accept-Language": "es-ES,es;q=0.9"})
    assert r.status_code == 200
    assert '<html lang="en">' in r.get_data(as_text=True)


def test_root_with_cookie_en_stays(client):
    client.set_cookie("lang", "en")
    assert client.get("/").status_code == 200


# --- switcher ----------------------------------------------------------------------------------------------

def test_switcher_carries_path(client):
    assert 'href="/es/symbol/moon"' in _get(client, "/symbol/moon").get_data(as_text=True)
    assert 'href="/symbol/moon"' in _get(client, "/es/symbol/moon").get_data(as_text=True)


def test_switcher_carries_query_string(client):
    html = _get(client, "/search?kind=event").get_data(as_text=True)
    assert 'href="/es/search?kind=event" hreflang="es"' in html
    html = _get(client, "/es/search?kind=event").get_data(as_text=True)
    assert 'href="/search?kind=event" hreflang="en"' in html
    html = _get(client, "/es/search?q=luna").get_data(as_text=True)
    assert 'href="/search?q=luna" hreflang="en"' in html


def test_switcher_survives_hostile_query_strings(client):
    for q in ["?sid=other", "?_scheme=ftp", "?_external=1&_anchor=x", "?pid=1", "?endpoint=x", "?_external=1",
              "?_anchor=a", "?_method=POST"]:
        r = _get(client, "/symbol/moon" + q)
        assert r.status_code == 200, q
        assert re.search(r'href="/es/symbol/moon[?"]', r.get_data(as_text=True)), q


def test_switcher_keeps_query_keys_verbatim(client):
    html = _get(client, "/search?q=moon&_anchor=a&endpoint=x").get_data(as_text=True)
    assert 'href="/es/search?q=moon&amp;_anchor=a&amp;endpoint=x" hreflang="es"' in html


@pytest.mark.parametrize("start", ["/es/", "/es/nope", "/es/symbol/nope", "/es/sefirah/nope"])
def test_switching_to_english_escapes_the_root_redirect(client, start):
    r = client.get(start)                                   # sets lang=es
    href = re.search(r'href="([^"]+)" hreflang="en"', r.get_data(as_text=True)).group(1).replace("&amp;", "&")
    r = client.get(href, follow_redirects=True)
    # /es/ and /es/nope land on the EN home; a matched route that 404s switches to its own EN 404, which is right
    assert r.status_code == (404 if start.count("/") == 3 else 200) and '<html lang="en">' in r.get_data(as_text=True), href
    assert client.get_cookie("lang").value == "en"
    assert client.get("/").status_code == 200              # and the root no longer bounces to /es/


def test_deep_link_switcher_stays_direct(client):
    assert 'href="/symbol/moon" hreflang="en"' in _get(client, "/es/symbol/moon").get_data(as_text=True)


def test_lang_endpoint_sets_cookie_and_redirects(client):
    r = client.get("/lang/es?next=/es/tree")
    assert r.status_code == 302 and r.headers["Location"].endswith("/es/tree")
    c = r.headers["Set-Cookie"]
    assert "lang=es" in c and "HttpOnly" in c and "SameSite=Lax" in c and "Path=/" in c


@pytest.mark.parametrize("nxt", ["//evil.example/", "https://evil.example/", "/\\evil.example", "evil", "",
                                 "javascript:alert(1)", "/\r\nSet-Cookie:x=1"])
def test_lang_endpoint_rejects_offsite_next(client, nxt):
    from urllib.parse import quote
    r = client.get("/lang/en?next=" + quote(nxt, safe=""))
    assert r.status_code == 302
    loc = r.headers["Location"]
    assert loc in ("/", "http://localhost/"), (nxt, loc)


def test_lang_endpoint_rejects_unknown_code(client):
    assert client.get("/lang/fr?next=/").status_code == 404


def test_root_redirect_keeps_query_string(client):
    client.set_cookie("lang", "es")
    r = client.get("/?utm=x&a=1")
    assert r.status_code == 302 and r.headers["Location"].endswith("/es/?utm=x&a=1")


def test_cookie_secure_follows_scheme(client):
    assert "Secure" not in client.get("/symbol/moon").headers["Set-Cookie"]
    r = client.get("/symbol/moon", base_url="https://localhost")
    assert "Secure" in r.headers["Set-Cookie"] and "HttpOnly" in r.headers["Set-Cookie"]


# --- html lang, title, leaks ------------------------------------------------------------------------------

@pytest.mark.parametrize("page", PAGES)
def test_html_lang_and_localised_title(client, page):
    en = _get(client, page)
    es = _get(client, "/es" + page)
    assert en.status_code == es.status_code == (404 if page in NOT_FOUND else 200), page
    en_html, es_html = en.get_data(as_text=True), es.get_data(as_text=True)
    assert '<html lang="en">' in en_html and '<html lang="es">' in es_html
    en_title = re.search(r"<title>(.*?)</title>", en_html, re.S).group(1)
    es_title = re.search(r"<title>(.*?)</title>", es_html, re.S).group(1)
    assert not _found(EN_UI, es_title), (page, es_title)
    assert not _found(ES_UI, en_title), (page, en_title)


@pytest.mark.parametrize("page", PAGES)
def test_spanish_pages_have_no_english_ui(client, page):
    r = _get(client, "/es" + page)
    assert "wm-sub" not in r.get_data(as_text=True)  # wordmark is just Zohar + זֹהַר
    leaks = _found(EN_UI, _visible_ui(r.get_data(as_text=True)))
    assert not leaks, (page, leaks)


@pytest.mark.parametrize("page", PAGES)
def test_english_pages_have_no_spanish_ui(client, page):
    r = _get(client, page)
    leaks = _found(ES_UI, _visible_ui(r.get_data(as_text=True)))
    assert not leaks, (page, leaks)


# --- gloss fallback ----------------------------------------------------------------------------------------

def test_gloss_fallback_pluralises(app):
    from web import queries
    with app.app_context():
        ones = queries.rows("select id from symbol where count_passages=1 and coalesce(gloss_es,'')=''")
        if not ones:
            pytest.skip("no single-passage symbol without a gloss in the fixture")
        for r in ones:
            g_es = queries.symbol(r["id"], "es")["gloss"]
            g_en = queries.symbol(r["id"], "en")["gloss"]
            assert "1 pasaje" in g_es and "1 pasajes" not in g_es, g_es
            assert "1 passage" in g_en and "1 passages" not in g_en, g_en
            assert "pasajes juntos" not in g_es


def test_gloss_fallback_spanish_word_order(app):
    from web import queries
    with app.app_context():
        ids = [r["id"] for r in queries.rows("select id from symbol where count_passages>1 and coalesce(gloss_es,'')=''")]
        glosses = [queries.symbol(i, "es")["gloss"] for i in ids]
    with_partner = [g for g in glosses if "acompañante" in g]
    if not with_partner:
        pytest.skip("no fallback gloss with a partner in the fixture")
    for g in with_partner:
        assert re.search(r"\(juntos en 1 pasaje\)|\(juntos en \d+ pasajes\)", g), g
