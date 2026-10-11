"""Run every stage in order. fetch reads the cache at the revisions in seeds/wikisource_revisions.json;
--refetch clears the cache and re-locks every page to its latest revision."""
import argparse
from pathlib import Path

from . import build, compute, fetch, lemmatise, tag

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--refetch", action="store_true")
    a = ap.parse_args(argv)
    fetch.main((["--only", str(a.only)] if a.only else []) + (["--refetch"] if a.refetch else []))
    lemmatise.main([])
    tag.main([])
    compute.main([])
    build.main([])


if __name__ == "__main__":
    main()
