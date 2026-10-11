"""Wikitext of a parasha page → passages keyed by Mantua folio and paragraph."""
import re
from dataclasses import dataclass

from .hebnum import heb_to_int

BOOKS = {"בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus",
         "במדבר": "Numbers", "דברים": "Deuteronomy"}

_NUM = r"([א-ת\"׳״]+)"
# an optional " - <parasha>" suffix labels a folio shared by two parashot (e.g. "דף לה ב - צו")
_SUFFIX = r"(?:\s+-\s+[^/<>]+?)?"
_START = re.compile(r"<\s*קטע\s+התחלה\s*=\s*דף\s+" + _NUM + r"\s+([אב])" + _SUFFIX + r"\s*/\s*>")
_END = re.compile(r"<\s*קטע\s+סוף\s*=\s*דף\s+" + _NUM + r"\s+([אב])" + _SUFFIX + r"\s*/\s*>")
# Folio sections only: the page also carries overlay sections (e.g. "שבועות 1",
# "בראשית א א") that mark verses/readings, not Mantua folios.
_RAW_START = re.compile(r"<\s*קטע\s+התחלה\s*=\s*דף")
_SECTION_TAG = re.compile(r"<\s*קטע\s+(?:התחלה|סוף)\s*=[^>]*/>")
_MM = re.compile(r"\{\{ממ\|([^|}]+)\|([א-ת]+)(?:\|([א-ת]+))?\}\}")
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
_LABEL_FIXES = {("זוהר חלק א", "א א"), ("זוהר חלק ג", "נט ב"),
                ("זוהר חלק יז", "קעט ב")}


# One-off Wikisource markup typos, fixed before segmenting: (page_title, old) -> new.
# Each `old` must occur exactly once on its page or segmenting fails loudly.
_TEXT_FIXES = {
    # variant reading "(ס"א נחש זוטא" is never closed; the reading is two words
    ("זוהר חלק י", 'נחש אחרא (ס"א נחש זוטא,'): 'נחש אחרא (ס"א נחש זוטא),',
    # editor's Hebrew note {{הערה| is never closed; it ends at "(המתוק מדבש)}}" and the
    # Aramaic Zohar text resumes with "הא אינון קדישין" (III 146b)
    ("זוהר חלק כה", "(המתוק מדבש)}} - הא אינון קדישין"): "(המתוק מדבש)}}}} - הא אינון קדישין",
    # single-brace typo inside a gematria template (an angel name that must stay)
    ("זוהר חלק יז", '{{גמט דגש{גדרי"ה}}'): '{{גמט דגש|גדרי"ה}}',
    # editor's note closed with "))" instead of "}}"
    ("זוהר חלק יז", 'עיי"ש]))'): 'עיי"ש]}}',
    # template closed with "PP" instead of "}}"
    ("זוהר חלק יז", "ויחר אפי בהם ואכלםPP,"): "ויחר אפי בהם ואכלם}},",
}


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


# Templates that carry Zohar text: name -> index of the argument that is the text.
# Every other template (notes, citations, layout marks) is dropped with its content.
_KEEP_ARG = {"צ": 0, "גמט": 0, "גמט דגש": 0, "קו תחתי": 0, "גדול": 0, "מר": 0,
             "ב": 0, "קיצור": 0, "תיקון גירסה": 0, "תיקון": 0, 'קו"כ': 0, 'כו"ק': 0, "מצ": 3}


def _split_args(inner: str) -> list[str]:
    """Split on | outside [[links]]."""
    args, cur, depth = [], [], 0
    i = 0
    while i < len(inner):
        two = inner[i:i + 2]
        if two == "[[":
            depth += 1; cur.append(two); i += 2
        elif two == "]]" and depth:
            depth -= 1; cur.append(two); i += 2
        elif inner[i] == "|" and not depth:
            args.append("".join(cur)); cur = []; i += 1
        else:
            cur.append(inner[i]); i += 1
    args.append("".join(cur))
    return args


def _template_text(m: re.Match) -> str:
    args = _split_args(m.group(0)[2:-2])
    name = args[0].strip()
    if name == "'":
        return "'"  # the geresh template
    idx = _KEEP_ARG.get(name)
    if idx is None or idx + 1 >= len(args):
        return ""
    return args[idx + 1]


def clean_wikitext(s: str) -> str:
    s = _COMMENT.sub("", s)
    s = _REF.sub("", s)
    s = _SECTION_TAG.sub("", s)
    s = _BOLD.sub("", s)  # before variants: some are wrapped in bold markup
    s = _VARIANT.sub("", s)
    s = _SHIN.sub("\n\n", s)
    while True:  # innermost templates first, so nesting like {{צ|{{קו תחתי|x}} y}} keeps its text
        t = _ANY_TEMPLATE.sub(_template_text, s)
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


def passage_id(volume: int, folio: int, side: str, para: int) -> str:
    return f"{volume}.{folio:03d}{side}.{para:02d}"


def segment_page(wikitext: str, volume: int, parasha: str, page_title: str,
                 stats: dict | None = None) -> list[Passage]:
    """A repeated (folio, side) on one page continues paragraph numbering;
    stats['continued'] counts such repeats."""
    for (title, old), new in _TEXT_FIXES.items():
        if title == page_title:
            if wikitext.count(old) != 1:
                raise SegmentError(page_title, "<fix>", f"known typo not found exactly once: {old!r}")
            wikitext = wikitext.replace(old, new)
    passages: list[Passage] = []
    seen: dict[tuple[int, str], int] = {}
    texts: dict[tuple[int, str], set[str]] = {}
    nsec: dict[tuple[int, str], int] = {}
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
        key = (folio, side)
        base = seen.get(key, 0)
        nsec[key] = nsec.get(key, 0) + 1
        if base and stats is not None:
            stats["continued"] = stats.get("continued", 0) + 1
            stats.setdefault("continued_keys", {})[f"{volume}.{folio:03d}{side}"] = nsec[key]
        vref = _verse_ref(block)
        prior = set(texts.get(key, ()))
        for i, text in enumerate(_paragraphs(block, page_title, label), start=base + 1):
            if base and text in prior:
                raise SegmentError(page_title, label, "duplicate text in repeated section")
            passages.append(Passage(
                id=passage_id(volume, folio, side, i), volume=volume, folio=folio,
                side=side, para=i, parasha=parasha, text_ar=text, verse_ref=vref))
            texts.setdefault(key, set()).add(text)
            seen[key] = i
        pos = e.end()
    n_raw = len(_RAW_START.findall(wikitext))
    if n_raw != n_matched:
        raise SegmentError(page_title, "<unparsed>", f"{n_raw} start tags, {n_matched} parsed")
    return passages
