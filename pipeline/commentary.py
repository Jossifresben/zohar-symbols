"""Classical commentary on the folio-sides of the translated passages, fetched from Sefaria.

Background for the model's interpretations only: it is not shown on the site and not part of
the tables. Both works are public domain on Sefaria (Hebrew), addressed Volume.Daf.

    python -m pipeline.commentary fetch            # cache every surfaced folio-side under work/commentary/
"""
import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

from .translate import connect, surfaced_ids

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "work" / "commentary"
API = "https://www.sefaria.org/api/texts/{title}.{vol}.{daf}?context=0"
VERSIONS = "https://www.sefaria.org/api/texts/versions/{title}"

# Sefaria title -> name given to the model
WORKS = {"Ohr_HaChammah_on_Zohar": "Ohr HaChamah", "Mikdash_Melekh_on_Zohar": "Mikdash Melekh"}


def daf(volume: int, folio: int, side: str) -> str:
    return f"{volume}.{folio}{side}"


def clean(html: str) -> str:
    """Sefaria segment HTML -> plain text (bold lemma kept as plain words)."""
    text = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", " ", text).strip()


def _flatten(x) -> list[str]:
    if isinstance(x, str):
        return [x] if x.strip() else []
    return [s for y in (x or []) for s in _flatten(y)]


def fetch_folio(title: str, key: str, sleep: float = 0.2) -> list[str]:
    path = CACHE / title / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    vol, d = key.split(".")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(API.format(title=title, vol=vol, daf=d), timeout=60) as r:
                data = json.load(r)
            break
        except (TimeoutError, OSError):
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    segs = [clean(s) for s in _flatten(data.get("he"))]
    segs = [s for s in segs if s]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
    time.sleep(sleep)
    return segs


def for_folio(volume: int, folio: int, side: str) -> dict[str, list[str]]:
    """Cached commentary for one folio-side: {work name: [segment, ...]}, works with no text left out."""
    key = daf(volume, folio, side)
    out = {}
    for title, name in WORKS.items():
        path = CACHE / title / f"{key}.json"
        segs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        if segs:
            out[name] = segs
    return out


def surfaced_folios(conn) -> list[tuple[int, int, str]]:
    ids = surfaced_ids(conn)
    q = ",".join("?" * len(ids))
    return [tuple(r) for r in conn.execute(
        f"select distinct volume, folio, side from passage where id in ({q}) order by volume, folio, side", ids)]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch"])
    ap.parse_args(argv)
    conn = connect()
    folios = surfaced_folios(conn)
    for title in WORKS:
        with urllib.request.urlopen(VERSIONS.format(title=title), timeout=30) as r:
            versions = [dict(lang=v.get("language"), title=v.get("versionTitle"), license=v.get("license"))
                        for v in json.load(r)]
        (CACHE / title).mkdir(parents=True, exist_ok=True)
        (CACHE / title / "_versions.json").write_text(json.dumps(versions, ensure_ascii=False, indent=1), encoding="utf-8")
    with_text = {t: 0 for t in WORKS}
    for v, f, s in folios:
        for title in WORKS:
            with_text[title] += bool(fetch_folio(title, daf(v, f, s)))
    print(json.dumps({"folio_sides": len(folios), "with_text": with_text}, indent=1))


if __name__ == "__main__":
    main()
