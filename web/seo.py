"""Search and sharing: canonical / hreflang URLs for the meta tags, sitemap.xml and robots.txt."""
from flask import Response, g, request, url_for

from . import db, queries

SITE = "https://zohar.digital"
STATIC_PAGES = ["home", "tree", "scholars", "about"]


def page_url(lang: str) -> str | None:
    """The current page's path in `lang` (no query string, no cookie redirect); None off the site blueprints."""
    ep = request.endpoint or ""
    if g.get("noindex") or ep.split(".")[0] not in ("site", "site_es"):
        return None
    name = ep.split(".")[-1]
    if name == "search" or (name == "home" and request.args):   # search results are not canonical pages
        return None
    return url_for(("site_es." if lang == "es" else "site.") + name, **(request.view_args or {}))


def _pair(endpoint: str, **values) -> tuple[str, str]:
    return (url_for("site." + endpoint, **values), url_for("site_es." + endpoint, **values))


def sitemap() -> Response:
    pairs = [_pair(p) for p in STATIC_PAGES]
    pairs += [_pair("symbol", sid=r["id"]) for r in db.all("select id from symbol order by id")]
    pairs += [_pair("node", nid=n) for n in queries.NODE_ORDER]
    pairs += [_pair("passage", pid=r["id"]) for r in db.all("select id from passage order by volume, folio, side, para, id")]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for en, es in pairs:
        alt = (f'<xhtml:link rel="alternate" hreflang="en" href="{SITE}{en}"/>'
               f'<xhtml:link rel="alternate" hreflang="es" href="{SITE}{es}"/>'
               f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{en}"/>')
        out += [f"<url><loc>{SITE}{en}</loc>{alt}</url>", f"<url><loc>{SITE}{es}</loc>{alt}</url>"]
    out.append("</urlset>")
    return Response("\n".join(out), mimetype="application/xml")


def robots() -> Response:
    body = f"User-agent: *\nAllow: /\nDisallow: /lang/\nDisallow: /search\nDisallow: /es/search\n\nSitemap: {SITE}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


def register(app) -> None:
    app.jinja_env.globals["page_url"] = page_url
    app.jinja_env.globals["site_origin"] = SITE
    app.add_url_rule("/sitemap.xml", "sitemap", sitemap)
    app.add_url_rule("/robots.txt", "robots", robots)
