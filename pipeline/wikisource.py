"""Fetch one Hebrew Wikisource page's wikitext with its revision id, cached on disk."""
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

API = "https://he.wikisource.org/w/api.php"
UA = "zohar-symbols/0.1 (https://github.com/Jossifresben/zohar-symbols)"


@dataclass(frozen=True)
class PageText:
    title: str
    revid: int
    timestamp: str
    wikitext: str


def _cache_path(cache_dir: Path, title: str) -> Path:
    return cache_dir / (hashlib.sha1(title.encode("utf-8")).hexdigest() + ".json")


def fetch_page(title: str, cache_dir: Path, session=None, revid: int | None = None) -> PageText:
    """Latest revision of `title`, or exactly revision `revid` when given (a lockfile pin).
    The cache holds one revision per title; a cached revision other than `revid` is refetched."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = _cache_path(cache_dir, title)
    if cp.exists():
        pt = PageText(**json.loads(cp.read_text(encoding="utf-8")))
        if revid is None or pt.revid == revid:
            return pt
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = UA
    params = {"action": "query", "prop": "revisions", "rvprop": "ids|timestamp|content",
              "rvslots": "main", "format": "json", "formatversion": "2"}
    if revid is None:
        params["titles"] = title
    else:
        params["revids"] = str(revid)
    r = session.get(API, params=params, timeout=60)
    r.raise_for_status()
    q = r.json()["query"]
    if q.get("badrevids"):
        raise LookupError(f"Wikisource revision not found: {title} @ {revid}")
    page = q["pages"][0]
    if page.get("missing") or "revisions" not in page:
        raise LookupError(f"Wikisource page not found: {title}")
    rev = page["revisions"][0]
    pt = PageText(title=page["title"], revid=int(rev["revid"]),
                  timestamp=rev["timestamp"], wikitext=rev["slots"]["main"]["content"])
    if revid is not None and (pt.revid != revid or pt.title != title):
        raise LookupError(f"asked for {title} @ {revid}, got {pt.title} @ {pt.revid}")
    cp.write_text(json.dumps(asdict(pt), ensure_ascii=False), encoding="utf-8")
    return pt
