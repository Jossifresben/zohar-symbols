"""Wikitext of a parasha page → passages keyed by Mantua folio and paragraph."""
import re
from dataclasses import dataclass

from .hebnum import heb_to_int

BOOKS = {"בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus",
         "במדבר": "Numbers", "דברים": "Deuteronomy"}

_NUM = r"([א-ת\"׳״]+)"
_START = re.compile(r"<\s*קטע\s+התחלה\s*=\s*דף\s+" + _NUM + r"\s+([אב])\s*/\s*>")
_END = re.compile(r"<\s*קטע\s+סוף\s*=\s*דף\s+" + _NUM + r"\s+([אב])\s*/\s*>")
# Folio sections only: the page also carries overlay sections (e.g. "שבועות 1",
# "בראשית א א") that mark verses/readings, not Mantua folios.
_RAW_START = re.compile(r"<\s*קטע\s+התחלה\s*=\s*דף")
_SECTION_TAG = re.compile(r"<\s*קטע\s+(?:התחלה|סוף)\s*=[^>]*/>")
_MM = re.compile(r"\{\{ממ\|([^|}]+)\|([א-ת]+)(?:\|([א-ת]+))?\}\}")
_TZ = re.compile(r"\{\{צ\|([^|{}]*)(?:\|[^{}]*)?\}\}")
_SHIN = re.compile(r"\{\{ש\}\}")
_ANY_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
# Real markup also wraps the reading: (<small>נ"א, ...</small>)
_VARIANT_OPEN = r"\((?:<small>\s*)?(?:נ\"א|ס\"א|נ״א|ס״א)"
# Known limit: a variant reading containing nested parentheses is not handled.
_VARIANT = re.compile(_VARIANT_OPEN + r"[^)\n]*\)")
_VARIANT_LEFT = re.compile(_VARIANT_OPEN)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_DROP_LINK = re.compile(r"\[\[(?:קטגוריה|קובץ):[^\]]*\]\]")
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_TAG = re.compile(r"</?(?:small|big|br|ref|span|div)[^>]*>")
_BOLD = re.compile(r"'''?")
_WS = re.compile(r"[ \t]+")


# One-off Wikisource typos: (page_title, label) whose start tag is duplicated
# (a stray tag before the heading, then the real one). The stray tag is skipped.
_LABEL_FIXES = {("זוהר חלק א", "א א")}


class SegmentError(Exception):
    def __init__(self, page_title: str, label: str, reason: str):
        super().__init__(f"{page_title}: section {label!r}: {reason}")
        self.page_title, self.label, self.reason = page_title, label, reason


@dataclass(frozen=True)
class Passage:
    id: str
    volume: int
    folio: int
    side: str
    para: int
    parasha: str
    text_ar: str
    verse_ref: str | None


def _verse_ref(block: str) -> str | None:
    m = _MM.search(block)
    if not m:
        return None
    book = BOOKS.get(m.group(1).strip())
    if not book:
        return None
    ch = heb_to_int(m.group(2))
    if m.group(3):
        return f"{book} {ch}:{heb_to_int(m.group(3))}"
    return f"{book} {ch}"


def clean_wikitext(s: str) -> str:
    s = _COMMENT.sub("", s)
    s = _REF.sub("", s)
    s = _SECTION_TAG.sub("", s)
    s = _VARIANT.sub("", s)
    s = _TZ.sub(lambda m: m.group(1), s)
    s = _SHIN.sub("\n\n", s)
    while True:
        t = _ANY_TEMPLATE.sub("", s)
        if t == s:
            break
        s = t
    s = _DROP_LINK.sub("", s)
    s = _LINK.sub(lambda m: m.group(1), s)
    s = _TAG.sub("", s)
    s = _BOLD.sub("", s)
    s = _WS.sub(" ", s)
    return "\n".join(line.strip() for line in s.split("\n")).strip()


def _paragraphs(block: str, page_title: str, label: str) -> list[str]:
    out = []
    for raw in re.split(r"\n\s*\n", block):
        for piece in _SHIN.split(raw):
            cleaned = clean_wikitext(piece)
            if "{{" in cleaned or "}}" in cleaned:
                raise SegmentError(page_title, label, "unbalanced template braces")
            if _VARIANT_LEFT.search(cleaned):
                raise SegmentError(page_title, label, "unclosed variant reading")
            text = " ".join(ln for ln in cleaned.split("\n") if ln.strip())
            if text:
                out.append(text)
    return out


def _num(s: str) -> int:
    return heb_to_int(re.sub(r"[\"׳״]", "", s))


def segment_page(wikitext: str, volume: int, parasha: str, page_title: str,
                 stats: dict | None = None) -> list[Passage]:
    """A repeated (folio, side) on one page continues paragraph numbering;
    stats['continued'] counts such repeats."""
    passages: list[Passage] = []
    seen: dict[tuple[int, str], int] = {}
    pos = 0
    n_matched = 0
    while True:
        m = _START.search(wikitext, pos)
        if not m:
            break
        label = f"{m.group(1)} {m.group(2)}"
        e = _END.search(wikitext, m.end())
        nxt = _START.search(wikitext, m.end())
        if (e and nxt and nxt.start() < e.start() and (page_title, label) in _LABEL_FIXES
                and (nxt.group(1), nxt.group(2)) == (m.group(1), m.group(2))):
            n_matched += 1  # stray duplicate start tag: accounted for, then skipped
            pos = nxt.start()
            continue
        if not e or (nxt and nxt.start() < e.start()):
            raise SegmentError(page_title, label, "unclosed section")
        if (e.group(1), e.group(2)) != (m.group(1), m.group(2)):
            raise SegmentError(page_title, label, f"closed by {e.group(1)} {e.group(2)}")
        n_matched += 1
        block = wikitext[m.end():e.start()]
        folio = _num(m.group(1))
        side = "a" if m.group(2) == "א" else "b"
        base = seen.get((folio, side), 0)
        if base and stats is not None:
            stats["continued"] = stats.get("continued", 0) + 1
        vref = _verse_ref(block)
        for i, text in enumerate(_paragraphs(block, page_title, label), start=base + 1):
            passages.append(Passage(
                id=f"{volume}.{folio:03d}{side}.{i:02d}", volume=volume, folio=folio,
                side=side, para=i, parasha=parasha, text_ar=text, verse_ref=vref))
            seen[(folio, side)] = i
        pos = e.end()
    n_raw = len(_RAW_START.findall(wikitext))
    if n_raw != n_matched:
        raise SegmentError(page_title, "<unparsed>", f"{n_raw} start tags, {n_matched} parsed")
    return passages
