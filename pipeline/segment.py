"""Wikitext of a parasha page → passages keyed by Mantua folio and paragraph."""
import re
from dataclasses import dataclass

from .hebnum import heb_to_int

BOOKS = {"בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus",
         "במדבר": "Numbers", "דברים": "Deuteronomy"}

_START = re.compile(r"<קטע התחלה=דף ([א-ת]+) ([אב])/>")
_END = re.compile(r"<קטע סוף=דף ([א-ת]+) ([אב])/>")
_MM = re.compile(r"\{\{ממ\|([^|}]+)\|([א-ת]+)(?:\|([א-ת]+))?\}\}")
_TZ = re.compile(r"\{\{צ\|([^}]*)\}\}")
_SHIN = re.compile(r"\{\{ש\}\}")
_ANY_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_VARIANT = re.compile(r"\((?:נ\"א|ס\"א|נ״א|ס״א)[^)]*\)")
_LINK = re.compile(r"\[\[[^\]]*\]\]")
_TAG = re.compile(r"</?(?:small|big|br|ref|span|div)[^>]*>")
_BOLD = re.compile(r"'''?")
_WS = re.compile(r"[ \t]+")


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
    s = _VARIANT.sub("", s)
    s = _TZ.sub(lambda m: m.group(1), s)
    s = _SHIN.sub("\n\n", s)
    s = _ANY_TEMPLATE.sub("", s)
    s = _ANY_TEMPLATE.sub("", s)  # nested once more
    s = _LINK.sub("", s)
    s = _TAG.sub("", s)
    s = _BOLD.sub("", s)
    s = _WS.sub(" ", s)
    return "\n".join(line.strip() for line in s.split("\n")).strip()


def _paragraphs(block: str) -> list[str]:
    cleaned = clean_wikitext(block)
    paras = [p.strip() for p in re.split(r"\n\s*\n", cleaned)]
    return [p.replace("\n", " ") for p in paras if p]


def segment_page(wikitext: str, volume: int, parasha: str, page_title: str) -> list[Passage]:
    passages: list[Passage] = []
    pos = 0
    while True:
        m = _START.search(wikitext, pos)
        if not m:
            break
        label = f"{m.group(1)} {m.group(2)}"
        e = _END.search(wikitext, m.end())
        nxt = _START.search(wikitext, m.end())
        if not e or (nxt and nxt.start() < e.start()):
            raise SegmentError(page_title, label, "unclosed section")
        if (e.group(1), e.group(2)) != (m.group(1), m.group(2)):
            raise SegmentError(page_title, label, f"closed by {e.group(1)} {e.group(2)}")
        block = wikitext[m.end():e.start()]
        folio = heb_to_int(m.group(1))
        side = "a" if m.group(2) == "א" else "b"
        vref = _verse_ref(block)
        for i, text in enumerate(_paragraphs(block), start=1):
            passages.append(Passage(
                id=f"{volume}.{folio:03d}{side}.{i:02d}", volume=volume, folio=folio,
                side=side, para=i, parasha=parasha, text_ar=text, verse_ref=vref))
        pos = e.end()
    return passages
