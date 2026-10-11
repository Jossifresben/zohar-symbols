"""Deploy gate: the rebuilt tables must hash to the value committed in data/tables.v<version>.sha256.

Run after `python -m pipeline.run_all`. Exits 0 on a match, 1 (with a message) on a mismatch or a missing file.
"""
import hashlib
import sys
from pathlib import Path

from .version import TABLES_VERSION

ROOT = Path(__file__).resolve().parent.parent


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(data_dir: Path = ROOT / "data", version: str = TABLES_VERSION) -> int:
    tables = data_dir / f"tables.v{version}.json"
    sha_file = data_dir / f"tables.v{version}.sha256"
    for f in (tables, sha_file):
        if not f.exists():
            print(f"check_tables: missing {f}", file=sys.stderr)
            return 1
    expected = sha_file.read_text(encoding="utf-8").split()[0].lower()
    actual = sha256_of(tables)
    if actual != expected:
        print(f"check_tables: {tables.name} does not match the committed hash.\n  expected {expected}\n  actual   {actual}\n"
              "The rebuilt tables differ from the committed release (pinned sources, seeds or Atlas changed?). "
              "If the change is intended, bump the tables version and commit the new hash.", file=sys.stderr)
        return 1
    print(f"check_tables: {tables.name} OK ({actual[:12]}…)")
    return 0


def main(argv=None) -> int:
    return check()


if __name__ == "__main__":
    sys.exit(main())
