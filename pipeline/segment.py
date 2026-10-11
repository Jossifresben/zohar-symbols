"""Wikitext of a parasha page → passages keyed by Mantua folio and paragraph."""
import re
from dataclasses import dataclass

from .hebnum import heb_to_int

BOOKS = {"בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus",
         "במדבר": "Numbers", "דברים": "Deuteronomy"}

_NUM = r"([א-ת\"׳״]+)"
_TAG_ANY = re.compile(r"<\s*קטע\s+(התחלה|סוף)\s*=\s*([^/<>]*?)\s*/\s*>")
# A folio-stream label: optional stream/parasha prefix, "דף N S", optional " - <parasha>" suffix
# (a folio shared by two parashot, e.g. "דף לה ב - צו").
_FOLIO_LABEL = re.compile(r"^(?:(?P<prefix>.+?)\s+)?דף\s+(?P<num>[א-ת\"׳״]+)\s+(?P<side>[אב])"
                          r"(?:\s*-\s*(?P<suffix>.+))?$")
# Overlay sections mark verses, readings or a named unit inside folio sections; stripped, not counted.
_OVERLAY_LABEL = re.compile(r"^(?:(?:בראשית|שמות|ויקרא|במדבר|דברים)\s+[א-ת\"׳״]+\s+[א-ת\"׳״]+"
                            r"|שבועות\s+\d+|ספרא דצניעותא(?:\s+\S+)?)$")
# Fixed order: paragraph numbering of a folio-side runs main first, then streams in this order.
STREAMS = ("main", "raaya_meheimna", "midrash_haneelam", "sitrei_torah", "raza_derazin",
           "tosefta", "matnitin", "other")
_STREAM_WORDS = {'רע"מ': "raaya_meheimna", "רע״מ": "raaya_meheimna", "רעיא מהימנא": "raaya_meheimna",
                 "מדרש הנעלם": "midrash_haneelam", "סתרי תורה": "sitrei_torah",
                 "רזא דרזין": "raza_derazin", "תוספתא": "tosefta", "מתניתין": "matnitin",
                 'ד"א': "other", "ד״א": "other"}
# A parasha name as label prefix or suffix means the main stream.
PARASHA_NAMES = frozenset("""בראשית נח לך לך וירא חיי שרה תולדות ויצא וישלח וישב מקץ ויגש ויחי
שמות וארא בא בשלח יתרו משפטים תרומה תצוה כי תשא ויקהל פקודי
ויקרא צו שמיני תזריע מצורע אחרי מות קדושים אמור בהר בחקותי בחקתי
במדבר נשא בהעלותך שלח קרח חוקת חקת בלק פינחס פנחס מטות מסעי
דברים ואתחנן עקב ראה שופטים תצא כי תצא תבוא כי תבוא נצבים וילך האזינו""".split()) | {
    "לך לך", "חיי שרה", "כי תשא", "אחרי מות", "כי תצא", "כי תבוא", "וזאת הברכה"}
# A section whose whole content is an editor's note that the folio has no text in this stream.
_PLACEHOLDER = re.compile(r"^\((?=[^()]*(?:רעיא מהימנא|זהר|זוהר))(?=[^()]*(?:דף|פרשת|אין))[^()]*\)$")
_RAW_TAG = re.compile(r"<\s*קטע\s+(?:התחלה|סוף)")
_SECTION_TAG = re.compile(r"<\s*קטע\s+(?:התחלה|סוף)\s*=[^>]*/>")
_HEBREW = re.compile(r"[א-ת]")
_HEADING = re.compile(r"^[ \t]*=+[^=\n].*?=+[ \t]*$", re.M)
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
_DROP_LINK = re.compile(r"\[\[\s*:?\s*(?:קטגוריה|קובץ|תמונה|file|image)\s*:[^\]]*\]\]", re.I)
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
    # --- section-tag typos (found when the stream sections were first parsed) ---
    # Midrash ha-Ne'lam I 99b is restarted after a heading without being closed
    ("זוהר חלק ה", "ההר הטוב.\n\n===מדרש הנעלם - אמר רבי חייא אמר רב==="):
        "ההר הטוב.<קטע סוף=מדרש הנעלם דף צט ב/>\n\n===מדרש הנעלם - אמר רבי חייא אמר רב===",
    # Midrash ha-Ne'lam I 117a is closed as 117b (no 117b section exists)
    ("זוהר חלק ה", "<קטע סוף=מדרש הנעלם דף קיז ב/>"): "<קטע סוף=מדרש הנעלם דף קיז א/>",
    # the second part of I 134a (start of Toldot) has an end tag but no start tag
    ("זוהר חלק ו", "{{ממ זהר משולב|א|קלד|א}}{{צ|ואלה תולדות יצחק"):
        "{{ממ זהר משולב|א|קלד|א}}<קטע התחלה=דף קלד א/>{{צ|ואלה תולדות יצחק",
    # four Tosefta sections (I 232a-234a) are closed with the main-stream label
    ("זוהר חלק י", "מאן דמפשפש <קטע סוף=דף רלב א/>"): "מאן דמפשפש <קטע סוף=תוספתא דף רלב א/>",
    ("זוהר חלק י", "(עד כאן תוספתא): <קטע סוף=דף רלב ב/>"): "(עד כאן תוספתא): <קטע סוף=תוספתא דף רלב ב/>",
    ("זוהר חלק י", "סומקא נחתא, <קטע סוף=דף רלג ב/>"): "סומקא נחתא, <קטע סוף=תוספתא דף רלג ב/>",
    ("זוהר חלק י", "(עד כאן תוספתא): <קטע סוף=דף רלד א/>"): "(עד כאן תוספתא): <קטע סוף=תוספתא דף רלד א/>",
    # main II 194b encloses the Ki Tisa Ra'aya Meheimna (II 187b-188a); Vayakhel resumes 194b
    ("זוהר חלק יז", "אמן ואמן:\n\n==רעיא מהימנא - כי תשא=="):
        "אמן ואמן:<קטע סוף=דף קצד ב/>\n\n==רעיא מהימנא - כי תשא==",
    ("זוהר חלק יז", "==פרשת ויקהל==\n\n{{צ|ויקהל משה את כל עדת בני ישראל"):
        "==פרשת ויקהל==\n\n<קטע התחלה=דף קצד ב/>{{צ|ויקהל משה את כל עדת בני ישראל",
    # a quotation template is opened twice and closed once (III 244b, Ra'aya Meheimna)
    ("זוהר חלק כח", "מן {{צ|'''ה'''מוציא}}"): "מן '''ה'''מוציא}}",
    # quotation templates never closed (III 246a, III 255b) and a single-brace opening (III 281a)
    ("זוהר חלק כח", "{{צ|ארבעה משמרות הוי הלילה. ו"): "{{צ|ארבעה משמרות הוי הלילה}}. ו",
    ("זוהר חלק כח", "{{צ|והחיות רצוא ושוב? כאור"): "{{צ|והחיות רצוא ושוב}}? כאור",
    ("זוהר חלק כט", "{ממ|ויקרא|כה|מט}}"): "{{ממ|ויקרא|כה|מט}}",
    # Ra'aya Meheimna placeholders III 66a, 66b are closed as 62a, 62b
    ("זוהר חלק כב", '<קטע התחלה=רע"מ דף סו א/>(הדף מכיל רק זוהר ללא רעיא מהימנא)<קטע סוף=רע"מ דף סב א/>'):
        '<קטע התחלה=רע"מ דף סו א/>(הדף מכיל רק זוהר ללא רעיא מהימנא)<קטע סוף=רע"מ דף סו א/>',
    ("זוהר חלק כב", '<קטע התחלה=רע"מ דף סו ב/>(הדף מכיל רק זוהר ללא רעיא מהימנא)<קטע סוף=רע"מ דף סב ב/>'):
        '<קטע התחלה=רע"מ דף סו ב/>(הדף מכיל רק זוהר ללא רעיא מהימנא)<קטע סוף=רע"מ דף סו ב/>',
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
    stream: str = "main"


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
    s = _HEADING.sub("", s)  # section headings are not stored in v0.1
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
            if _HEBREW.search(text):  # punctuation- or markup-only leftovers are not passages
                out.append(text)
    return out


def _num(s: str) -> int:
    return heb_to_int(re.sub(r"[\"׳״]", "", s))


def passage_id(volume: int, folio: int, side: str, para: int) -> str:
    return f"{volume}.{folio:03d}{side}.{para:03d}"


@dataclass(frozen=True)
class Label:
    stream: str
    folio: int
    side: str
    key: str  # "<num> <side>" as written, for _LABEL_FIXES


def _strip_word(prefix: str, word: str) -> tuple[str, bool]:
    pat = re.compile(r"(?:^|\s)" + re.escape(word) + r"(?=\s|$)")
    new = pat.sub(" ", prefix)
    return " ".join(new.split()), new != prefix


def classify_label(label: str, page_title: str = "") -> Label | None:
    """A <קטע> label -> its folio stream (Label), None for an overlay; anything else fails loudly."""
    label = " ".join(label.split())
    m = _FOLIO_LABEL.match(label)
    if m:
        prefix, stream = m.group("prefix") or "", "main"
        for word, s in _STREAM_WORDS.items():
            prefix, hit = _strip_word(prefix, word)
            if hit:
                if stream != "main":
                    raise SegmentError(page_title, label, "two stream names in one label")
                stream = s
        if prefix and prefix not in PARASHA_NAMES:
            raise SegmentError(page_title, label, f"unknown label prefix {prefix!r}")
        suffix = (m.group("suffix") or "").strip()
        if suffix and suffix not in PARASHA_NAMES:
            raise SegmentError(page_title, label, f"unknown label suffix {suffix!r}")
        return Label(stream, _num(m.group("num")), "a" if m.group("side") == "א" else "b",
                     f"{m.group('num')} {m.group('side')}")
    if _OVERLAY_LABEL.match(label):
        return None
    raise SegmentError(page_title, label, "unclassified section label")


def _stream_key(volume: int, folio: int, side: str, stream: str) -> str:
    k = f"{volume}.{folio:03d}{side}"
    return k if stream == "main" else f"{k}/{stream}"


def renumber(passages: list[dict]) -> list[dict]:
    """Number paragraphs per (volume, folio, side): main stream first, then the other streams in
    STREAMS order; document order within a stream. The list keeps its order; dicts are updated."""
    order = sorted(range(len(passages)), key=lambda i: (
        passages[i]["volume"], passages[i]["folio"], passages[i]["side"],
        STREAMS.index(passages[i]["stream"]), i))
    n: dict[tuple[int, int, str], int] = {}
    for i in order:
        p = passages[i]
        key = (p["volume"], p["folio"], p["side"])
        n[key] = n.get(key, 0) + 1
        p["para"] = n[key]
        p["id"] = passage_id(p["volume"], p["folio"], p["side"], n[key])
    return passages


def segment_page(wikitext: str, volume: int, parasha: str, page_title: str,
                 stats: dict | None = None) -> list[Passage]:
    """A repeated (folio, side, stream) on one page continues that stream; stats['continued']
    counts such repeats, stats['placeholders'] the sections that only say a stream is absent."""
    for (title, old), new in _TEXT_FIXES.items():
        if title == page_title:
            if wikitext.count(old) != 1:
                raise SegmentError(page_title, "<fix>", f"known typo not found exactly once: {old!r}")
            wikitext = wikitext.replace(old, new)
    wikitext = _COMMENT.sub("", wikitext)  # a tag inside an HTML comment is not a section
    all_tags = list(_TAG_ANY.finditer(wikitext))
    n_raw = len(_RAW_TAG.findall(wikitext))
    if n_raw != len(all_tags):
        raise SegmentError(page_title, "<unparsed>", f"{n_raw} section tags, {len(all_tags)} well-formed")
    tags = []  # folio-stream tags in document order: (match, is_start, Label)
    for m in all_tags:
        lab = classify_label(m.group(2), page_title)
        if lab is not None:
            tags.append((m, m.group(1) == "התחלה", lab))
    stats = stats if stats is not None else {}
    found: list[dict] = []
    nsec: dict[tuple[int, str, str], int] = {}
    texts: dict[tuple[int, str, str], set[str]] = {}
    i = 0
    while i < len(tags):
        m, is_start, lab = tags[i]
        label = " ".join(m.group(2).split())
        if not is_start:
            raise SegmentError(page_title, label, "end tag without a start")
        nxt = tags[i + 1] if i + 1 < len(tags) else None
        if (nxt and nxt[1] and nxt[2] == lab and lab.stream == "main"
                and (page_title, lab.key) in _LABEL_FIXES):
            # stray duplicate start tag: skipped, but only if nothing but markup lies before the real one
            if _HEBREW.search(clean_wikitext(wikitext[m.end():nxt[0].start()])):
                raise SegmentError(page_title, label, "stray start tag is followed by text")
            i += 1
            continue
        if not nxt or nxt[1]:
            raise SegmentError(page_title, label, "unclosed section")
        e, _, elab = nxt
        if (elab.stream, elab.folio, elab.side) != (lab.stream, lab.folio, lab.side):
            raise SegmentError(page_title, label, f"closed by {' '.join(e.group(2).split())}")
        i += 2
        block = wikitext[m.end():e.start()]
        if _PLACEHOLDER.match(" ".join(clean_wikitext(block).split())):
            stats["placeholders"] = stats.get("placeholders", 0) + 1
            continue
        key = (lab.folio, lab.side, lab.stream)
        nsec[key] = nsec.get(key, 0) + 1
        if nsec[key] > 1:
            stats["continued"] = stats.get("continued", 0) + 1
            stats.setdefault("continued_keys", {})[_stream_key(volume, *key)] = nsec[key]
        vref = _verse_ref(block)
        prior = set(texts.get(key, ()))
        for text in _paragraphs(block, page_title, label):
            if nsec[key] > 1 and text in prior:
                raise SegmentError(page_title, label, "duplicate text in repeated section")
            found.append(dict(id="", volume=volume, folio=lab.folio, side=lab.side, para=0,
                              parasha=parasha, text_ar=text, verse_ref=vref, stream=lab.stream))
            texts.setdefault(key, set()).add(text)
    return [Passage(**p) for p in renumber(found)]
