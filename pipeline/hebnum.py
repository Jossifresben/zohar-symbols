"""Hebrew numerals as Wikisource writes them: no geresh, טו/טז for 15/16."""

_VALUES = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90,
    "ק": 100, "ר": 200, "ש": 300, "ת": 400,
}
_HUNDREDS = [(400, "ת"), (300, "ש"), (200, "ר"), (100, "ק")]
_TENS = [(90, "צ"), (80, "פ"), (70, "ע"), (60, "ס"), (50, "נ"), (40, "מ"), (30, "ל"), (20, "כ"), (10, "י")]
_ONES = "אבגדהוזחט"


def heb_to_int(s: str) -> int:
    if not s or any(c not in _VALUES for c in s):
        raise ValueError(f"not a Hebrew numeral: {s!r}")
    return sum(_VALUES[c] for c in s)


def int_to_heb(n: int) -> str:
    if n <= 0 or n >= 1000:
        raise ValueError(f"out of range: {n}")
    out = ""
    for v, c in _HUNDREDS:
        while n >= v:
            out += c
            n -= v
    if n == 15:
        return out + "טו"
    if n == 16:
        return out + "טז"
    for v, c in _TENS:
        if n >= v:
            out += c
            n -= v
            break
    if n:
        out += _ONES[n - 1]
    return out
