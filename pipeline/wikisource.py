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


def fetch_page(title: str, cache_dir: Path, session=None) -> PageText:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = _cache_path(cache_dir, title)
    if cp.exists():
        return PageText(**json.loads(cp.read_text(encoding="utf-8")))
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = UA
    r = session.get(API, params={
        "action": "query", "prop": "revisions", "titles": title,
        "rvprop": "ids|timestamp|content", "rvslots": "main", "format": "json",
        "formatversion": "1",
    }, timeout=60)
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page or "revisions" not in page:
        raise LookupError(f"Wikisource page not found: {title}")
    rev = page["revisions"][0]
    pt = PageText(title=page["title"], revid=int(rev["revid"]),
                  timestamp=rev["timestamp"], wikitext=rev["slots"]["main"]["content"])
    cp.write_text(json.dumps(asdict(pt), ensure_ascii=False), encoding="utf-8")
    return pt
