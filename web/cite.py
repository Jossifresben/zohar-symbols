"""Citation helpers: Zohar folio citations and the site's own citation formats."""

_ROMAN = {1: "I", 2: "II", 3: "III"}
AUTHOR = "Fresco Benaim, Jose"
TITLE = "Zohar Symbols: a computed dictionary of the Zohar's kinnuyim"
URL = "https://zohar.digital"
DOI = "[DOI pending]"


def roman(volume: int) -> str:
    return _ROMAN[volume]


def citation(volume: int, folio: int, side: str) -> str:
    return f"Zohar {roman(volume)}:{folio}{side}"


def formats(meta: dict) -> dict[str, str]:
    year = (meta.get("built_at") or "")[:4] or "2026"
    version = meta.get("tables_version") or "unversioned"
    return {
        "bibtex": (f"@misc{{zohar_symbols_{year},\n  author = {{{AUTHOR}}},\n  title = {{{TITLE}}},\n"
                   f"  year = {{{year}}},\n  version = {{{version}}},\n  url = {{{URL}}},\n  doi = {{{DOI}}}\n}}"),
        "chicago": f"Fresco Benaim, Jose. {year}. “{TITLE}.” Version {version}. {URL}. {DOI}.",
        "sbl": f"Fresco Benaim, Jose. {TITLE}. Version {version}. {year}. {URL}. {DOI}.",
    }
