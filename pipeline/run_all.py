"""Run every stage in order. fetch is cached; pass --refetch to clear the cache."""
import argparse
import shutil
from pathlib import Path

from . import build, compute, fetch, lemmatise, tag

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--refetch", action="store_true")
    a = ap.parse_args(argv)
    if a.refetch:
        shutil.rmtree(ROOT / "raw" / "cache", ignore_errors=True)
    fetch.main(["--only", str(a.only)] if a.only else [])
    lemmatise.main([])
    tag.main([])
    compute.main([])
    build.main([])


if __name__ == "__main__":
    main()
