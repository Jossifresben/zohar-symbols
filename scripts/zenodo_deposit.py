"""Deposit a tagged release on Zenodo through the REST API, metadata from .zenodo.json.

The token is read from the ZENODO_TOKEN environment variable and sent only as an
Authorization header to zenodo.org. Nothing is published without --publish.

    ZENODO_TOKEN=… python scripts/zenodo_deposit.py new v0.1.0 [--publish]
    ZENODO_TOKEN=… python scripts/zenodo_deposit.py newversion <record_id> v0.2.0 [--publish]

`new` creates the first record (and with it the concept DOI); `newversion` adds a version
under the same concept DOI. The record id of the latest version is written to .zenodo-record.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
API = "https://zenodo.org/api/deposit/depositions"


def headers() -> dict:
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        sys.exit("ZENODO_TOKEN is not set")
    return {"Authorization": f"Bearer {token}"}


def metadata(tag: str) -> dict:
    z = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    version = tag.lstrip("v")
    if z.get("version") != version:
        sys.exit(f".zenodo.json version {z.get('version')} != tag {tag}")
    return {"title": z["title"], "upload_type": z["upload_type"], "description": z["description"],
            "creators": z["creators"], "keywords": z["keywords"], "license": z["license"].lower(),
            "version": version, "language": z.get("language", "eng"), "access_right": z["access_right"],
            "related_identifiers": z["related_identifiers"]}


def archive(tag: str) -> Path:
    out = Path(tempfile.mkdtemp()) / f"zohar-symbols-{tag}.zip"
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", f"--prefix=zohar-symbols-{tag}/",
                    "-o", str(out), tag], check=True)
    return out


def ok(r: requests.Response) -> dict:
    if r.status_code >= 400:
        sys.exit(f"{r.request.method} {r.url} -> {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {}


def fill_and_publish(dep: dict, tag: str, publish: bool) -> dict:
    h = headers()
    for f in dep.get("files", []):   # a new version starts with the previous version's files
        ok(requests.delete(f"{API}/{dep['id']}/files/{f['id']}", headers=h))
    zp = archive(tag)
    with zp.open("rb") as fh:
        ok(requests.put(f"{dep['links']['bucket']}/{zp.name}", data=fh, headers=h))
    ok(requests.put(f"{API}/{dep['id']}", json={"metadata": metadata(tag)}, headers=h))
    if not publish:
        print(f"draft {dep['id']} ready: {dep['links']['html']} (rerun with --publish, or publish on the site)")
        return dep
    rec = ok(requests.post(f"{API}/{dep['id']}/actions/publish", headers=h))
    (ROOT / ".zenodo-record").write_text(str(rec["id"]) + "\n")
    print(json.dumps({"record": rec["id"], "doi": rec.get("doi"), "conceptdoi": rec.get("conceptdoi"),
                      "url": rec["links"].get("html")}, indent=1))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("tag")
    n.add_argument("--publish", action="store_true")
    v = sub.add_parser("newversion")
    v.add_argument("record_id")
    v.add_argument("tag")
    v.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    h = headers()
    if a.cmd == "new":
        dep = ok(requests.post(API, json={}, headers=h))
    else:
        r = ok(requests.post(f"{API}/{a.record_id}/actions/newversion", headers=h))
        dep = ok(requests.get(r["links"]["latest_draft"], headers=h))
    fill_and_publish(dep, a.tag, a.publish)


if __name__ == "__main__":
    main()
