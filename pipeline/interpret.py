"""Model-inferred interpretations of the translated passages ("What this passage means"), via the Batch API.

One request per passage returns both languages. The model gets the passage, its neighbours, our English
translation, the passage's keys (image -> usual sefirah, from the seed) and, in the grounded variant,
the classical commentary on the folio as unseen background. Code computes every count and cost.

    python -m pipeline.interpret pilot [--n 10] --submit        # each passage grounded and plain, for a blind review
    python -m pipeline.interpret collect <batch_id> --name pilot
    python -m pipeline.interpret review pilot                   # blind A/B page under work/interpret/
"""
import argparse
import html
import json
import re
import random
import sys
from pathlib import Path

from . import commentary
from .translate import (CONTEXT_RADIUS, EFFORT, MODEL, connect, collect, cost_usd, submit,  # noqa: F401
                        surfaced_ids, _all_tokens)

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "interpret"

PROMPT_VERSION = "i2"   # i1: pilot; i2: hard 200-word cap, plain (no commentary)
VARIANTS = ("grounded", "plain")
MAX_COMMENTARY_CHARS = 12000   # per work, per folio-side

INSTRUCTIONS = """You write short explanations of Zohar passages for a bilingual website for curious readers who know nothing about Kabbalah. The site already shows the Aramaic text and a translation; your text sits under them with the heading "What this passage means".

Write what the passage means:
- 120 to 200 words in each language, never more than 200. Plain, warm, precise prose for an intelligent reader; no jargon left unexplained.
- Say what happens in the passage: who speaks, which verse is being read, what move the passage makes.
- Explain what its images stand for. You are given the passage's keys (image -> the sefirah it usually stands for). Use them, but follow the passage itself when it identifies an image differently.
- The first time you name a sefirah or a technical term, gloss it in a few words (for example: Binah, divine understanding, the "upper mother").
- Say why it matters: the idea or experience the passage points at.
- Where the passage is genuinely open, say so ("one way to read this…"). Do not present one school's reading as the only meaning. Do not use later Kabbalistic terminology (partzufim, tzimtzum, Arikh Anpin, Zeir Anpin) unless the passage itself uses the term.
- Teshuvah (תשובה, תיובתא): keep the word, Teshuvah / Teshuvá, glossed as "the return of the he" / "el retorno de la he". Never "repentance" or "arrepentimiento".
- Do not cite, quote or name commentators, books or schools. Do not invent quotations. Quote the passage only briefly, if at all.
- Do not preach and do not give devotional instructions.
- Write the Spanish natively (neutral peninsular Spanish, «» quotation marks), not as a translation of the English.

Output exactly this, nothing else:
### EN
<the English text>
### ES
<the Spanish text>"""

GROUNDING_NOTE = ("Background: classical commentary on this folio-side, in Hebrew. Use it only to understand the passage "
                  "better; it may discuss other paragraphs of the folio. Do not mention, quote or name it.")


def system_blocks() -> list[dict]:
    return [{"type": "text", "text": INSTRUCTIONS}]


def keys(conn, pid: str) -> list[str]:
    seen, out = set(), []
    for r in conn.execute("""select s.id, s.label_en, s.node, m.matched_form from mention m join symbol s on s.id=m.symbol_id
                             where m.passage_id=? order by m.position""", (pid,)):
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(f"{r['matched_form']} ({r['label_en']}) -> {r['node']}")
    return out


def user_content(conn, pid: str, grounded: bool) -> str:
    p = conn.execute("select * from passage where id=?", (pid,)).fetchone()
    folio = conn.execute("select id, text_ar from passage where volume=? and folio=? and side=? order by para",
                         (p["volume"], p["folio"], p["side"])).fetchall()
    i = next(k for k, r in enumerate(folio) if r["id"] == pid)
    window = folio[max(0, i - CONTEXT_RADIUS): i + CONTEXT_RADIUS + 1]
    ctx = "\n\n".join(("[TARGET] " if r["id"] == pid else "") + r["text_ar"] for r in window)
    tr = conn.execute("select text from translation where passage_id=? and lang='en'", (pid,)).fetchone()
    parts = [f"Passage {pid}."]
    if p["verse_ref"]:
        parts.append(f"The folio comments on {p['verse_ref']}.")
    parts += ["Context (neighbouring paragraphs):\n" + ctx,
              "TARGET passage:\n" + p["text_ar"],
              "Our English translation of the target:\n" + (tr["text"] if tr else "(none)"),
              "Keys (image -> usual sefirah):\n" + ("\n".join(keys(conn, pid)) or "(none)")]
    if grounded:
        com = commentary.for_folio(p["volume"], p["folio"], p["side"])
        if com:
            body = "\n\n".join(f"[{name}]\n" + "\n".join(segs)[:MAX_COMMENTARY_CHARS] for name, segs in com.items())
            parts.append(GROUNDING_NOTE + "\n\n" + body)
    return "\n\n".join(parts)


def custom_id(pid: str, variant: str) -> str:
    return f"{pid.replace('.', '-')}__both__{variant}"   # parsed by translate.parse_custom_id: lang="both", effort slot=variant


def build_request(conn, pid: str, variant: str) -> dict:
    return {"custom_id": custom_id(pid, variant),
            "params": {"model": MODEL, "max_tokens": 16000, "system": system_blocks(),
                       "output_config": {"effort": EFFORT},
                       "messages": [{"role": "user", "content": user_content(conn, pid, variant == "grounded")}]}}


def split_langs(text: str) -> dict | None:
    """'### EN ... ### ES ...' -> {'en':..., 'es':...}; None if the shape is wrong."""
    if "### EN" not in text or "### ES" not in text:
        return None
    en = text.split("### EN", 1)[1].split("### ES", 1)[0].strip()
    es = text.split("### ES", 1)[1].strip()
    return {"en": en, "es": es} if en and es else None


def has_commentary(conn, pid: str) -> bool:
    p = conn.execute("select volume, folio, side from passage where id=?", (pid,)).fetchone()
    return bool(commentary.for_folio(p["volume"], p["folio"], p["side"]))


def pilot_ids(conn, n: int = 10) -> list[str]:
    """Every k-th surfaced passage whose folio-side has commentary: spread across the book, so the grounded
    and plain variants actually differ."""
    ids = [pid for pid in surfaced_ids(conn) if has_commentary(conn, pid)]
    step = max(1, len(ids) // n)
    return ids[::step][:n]


def review(name: str) -> Path:
    """Blind A/B page: for each passage the two variants in random order; the key is a separate file."""
    conn = connect()
    rows = [json.loads(line) for line in (WORK / f"{name}_results.jsonl").open(encoding="utf-8")]
    by_pid: dict[str, dict] = {}
    for r in rows:
        if r["status"] == "succeeded":
            by_pid.setdefault(r["passage_id"], {})[r["effort"]] = split_langs(r["text"]) or {"en": r["text"], "es": ""}
    rnd = random.Random(20261011)
    key, cards = {}, []
    for pid in sorted(by_pid):
        order = list(VARIANTS)
        rnd.shuffle(order)
        key[pid] = {"A": order[0], "B": order[1]}
        p = conn.execute("select text_ar from passage where id=?", (pid,)).fetchone()
        tr = conn.execute("select lang, text from translation where passage_id=?", (pid,)).fetchall()
        trs = {t["lang"]: t["text"] for t in tr}
        cols = "".join(
            f"<div class='v'><h3>{lab}</h3>" + "".join(
                f"<p class='{lg}'>{html.escape(by_pid[pid].get(variant, {}).get(lg, '(missing)'))}</p>" for lg in ("en", "es"))
            + "</div>" for lab, variant in (("A", order[0]), ("B", order[1])))
        cards.append(f"<section><h2>{pid} <a href='http://localhost:5055/passage/{pid}'>open</a></h2>"
                     f"<p class='ar' dir='rtl' lang='arc'>{html.escape(p['text_ar'])}</p>"
                     f"<details><summary>Translation</summary><p>{html.escape(trs.get('en', ''))}</p></details>"
                     f"<div class='ab'>{cols}</div></section>")
    page = ("<!doctype html><meta charset='utf-8'><title>Interpretation pilot</title><style>"
            "body{font:16px/1.55 Georgia,serif;max-width:1200px;margin:24px auto;padding:0 16px;color:#222}"
            "h2{font-size:18px;margin-top:40px;border-top:1px solid #ccc;padding-top:16px}"
            ".ar{font-size:20px;color:#7a5c12}.ab{display:grid;grid-template-columns:1fr 1fr;gap:24px}"
            ".v h3{margin:8px 0}.es{color:#444}@media(max-width:800px){.ab{grid-template-columns:1fr}}</style>"
            "<h1>Interpretation pilot: blind A/B</h1><p>For each passage, A and B are the two variants in random order "
            "(one had the classical commentary as background, one did not). Note which you prefer and why; "
            "the key is in pilot_key.json.</p>" + "".join(cards))
    out = WORK / f"{name}_review.html"
    out.write_text(page, encoding="utf-8")
    (WORK / f"{name}_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return out


CHUNKS = WORK / "chunks"
BANNED = ("Zeir Anpin", "Zeʿir Anpin", "Arikh Anpin", "partzuf", "tzimtzum", "repentance", "arrepentimiento")  # any case
BANNED_NAMES = ("Ohr HaChamah", "Or HaJamá", "Mikdash Melekh", "Cordovero", "Luria", "Vital", "Ashlag", "Sulam")  # exact
                                                                                       # case, whole word ("vital soul" is fine)
MAX_WORDS = 200


def write_chunks(conn, size: int = 20) -> int:
    """Plain requests for Claude Code sub-agents: chunk_000 starts with the pilot passages, so they can be compared."""
    CHUNKS.mkdir(parents=True, exist_ok=True)
    first = pilot_ids(conn, 10)
    rest = [pid for pid in surfaced_ids(conn) if pid not in first]
    ids = first + rest
    (CHUNKS / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    n = 0
    for k in range(0, len(ids), size):
        items = [{"passage_id": pid, "content": user_content(conn, pid, grounded=False)} for pid in ids[k:k + size]]
        (CHUNKS / f"chunk_{n:03d}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    return n


LENGTH_TOLERANCE = 275   # the prompt asks for at most 200 words; the model runs over by 5–30%, which a reader won't notice
IDRA_TERMS = ("Zeir Anpin", "Zeʿir Anpin", "Arikh Anpin")   # allowed when the passage itself says אנפין / אפין


def check(text: str, source: str = "") -> str | None:
    """None if an interpretation passes the code checks, else the reason."""
    s = split_langs(text)
    if not s:
        return "shape"
    for lg in ("en", "es"):
        if len(s[lg].split()) > LENGTH_TOLERANCE:
            return f"{lg} {len(s[lg].split())} words"
    in_source = "אנפין" in source or "אפין" in source
    hit = [b for b in BANNED if b.lower() in text.lower() and not (in_source and b in IDRA_TERMS)]
    hit += [n for n in BANNED_NAMES if re.search(rf"\b{re.escape(n)}\b", text)]
    return f"banned: {hit}" if hit else None


def ingest(chunk: int, model: str = MODEL) -> dict:
    """Validate a sub-agent's results for one chunk and append the passing rows to cc_results.jsonl."""
    from .translate import source_hash
    conn = connect()
    want = [x["passage_id"] for x in json.loads((CHUNKS / f"chunk_{chunk:03d}.json").read_text(encoding="utf-8"))]
    got = {}
    for line in (CHUNKS / f"chunk_{chunk:03d}_results.jsonl").open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            got[r["passage_id"]] = r["text"]
    done = {json.loads(l)["passage_id"] for l in (WORK / "cc_results.jsonl").open(encoding="utf-8")} \
        if (WORK / "cc_results.jsonl").exists() else set()
    ok, failed = [], {}
    for pid in want:
        if pid not in got:
            failed[pid] = "missing"
            continue
        src_text = conn.execute("select text_ar from passage where id=?", (pid,)).fetchone()["text_ar"]
        why = check(got[pid], src_text)
        if why:
            failed[pid] = why
            continue
        if pid in done:
            continue
        src = conn.execute("select text_ar from passage where id=?", (pid,)).fetchone()["text_ar"]
        ok.append(dict(passage_id=pid, lang="both", effort="plain", status="succeeded", stop_reason="end_turn",
                       model=model, via="claude-code-subagent", text=got[pid].strip(),
                       source_hash=source_hash(src), prompt_version=PROMPT_VERSION))
    with (WORK / "cc_results.jsonl").open("a", encoding="utf-8") as fh:
        for r in ok:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"chunk": chunk, "accepted": len(ok), "failed": failed}


def export(names: list[str], created_at: str = "2026-10-12") -> str:
    """Write the committed interpretations file: one row per (passage, language), from cc_results and the
    named batch result sets; a row must pass check(). Later sources override earlier ones."""
    from .version import TABLES_VERSION
    conn = connect()
    rows, rejected = {}, {}
    sources = [WORK / "cc_results.jsonl"] + [WORK / f"{n}_results.jsonl" for n in names]
    for path in sources:
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["status"] != "succeeded" or r.get("stop_reason") != "end_turn" or not r.get("text"):
                rejected[r["passage_id"]] = r.get("stop_reason") or r["status"]
                continue
            src = conn.execute("select text_ar from passage where id=?", (r["passage_id"],)).fetchone()
            why = check(r["text"], src["text_ar"] if src else "")
            if why:
                rejected[r["passage_id"]] = why
                continue
            rejected.pop(r["passage_id"], None)
            for lg, text in split_langs(r["text"]).items():
                rows[(r["passage_id"], lg)] = dict(passage_id=r["passage_id"], lang=lg, text=text, model=r["model"],
                                                  prompt_version=r["prompt_version"], source_hash=r["source_hash"],
                                                  created_at=created_at)
    out = ROOT / "data" / f"interpretations.v{TABLES_VERSION}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for k in sorted(rows):
            f.write(json.dumps(rows[k], ensure_ascii=False, sort_keys=True) + "\n")
    return f"{len(rows)} interpretations -> {out}; rejected: {rejected}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot")
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--submit", action="store_true")
    c = sub.add_parser("collect")
    c.add_argument("batch_id")
    c.add_argument("--name", default="pilot")
    r = sub.add_parser("review")
    r.add_argument("name")
    fu = sub.add_parser("full", help="plain requests for every surfaced passage not yet in cc_results.jsonl")
    fu.add_argument("--name", default="full")
    fu.add_argument("--stratum", help="instead: every translated passage of this stratum with no interpretation yet")
    fu.add_argument("--min-tokens", type=int, default=12)
    fu.add_argument("--submit", action="store_true")
    ch = sub.add_parser("chunks")
    ch.add_argument("--size", type=int, default=20)
    ex = sub.add_parser("export")
    ex.add_argument("names", nargs="*", default=["full"])
    ig = sub.add_parser("ingest")
    ig.add_argument("chunk", type=int)
    a = ap.parse_args(argv)
    WORK.mkdir(parents=True, exist_ok=True)
    conn = connect()
    if a.cmd == "pilot":
        reqs = [build_request(conn, pid, v) for pid in pilot_ids(conn, a.n) for v in VARIANTS]
        (WORK / "pilot_requests.json").write_text(json.dumps(reqs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(reqs)} requests -> {WORK / 'pilot_requests.json'}")
        if a.submit:
            bid = submit(reqs)
            (WORK / "pilot_batch_id").write_text(bid)
            print(f"submitted batch {bid}")
    elif a.cmd == "collect":
        rows = collect(a.batch_id, conn, PROMPT_VERSION)
        with (WORK / f"{a.name}_results.jsonl").open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        ok = [x for x in rows if x["status"] == "succeeded"]
        bad_shape = [x["passage_id"] for x in ok if not split_langs(x.get("text", ""))]
        cost = sum(x["cost_usd"] for x in ok)
        per_variant = {v: round(sum(x["cost_usd"] for x in ok if x["effort"] == v), 4) for v in VARIANTS}
        n_pass = len({x["passage_id"] for x in ok}) or 1
        all_ids = surfaced_ids(conn)
        summary = dict(requests=len(rows), succeeded=len(ok), bad_shape=bad_shape, cost_usd=round(cost, 4),
                       cost_by_variant=per_variant,
                       projected_full_grounded_usd=round(per_variant["grounded"] / n_pass * len(all_ids), 2),
                       projected_full_plain_usd=round(per_variant["plain"] / n_pass * len(all_ids), 2),
                       projected_basis=f"{len(all_ids)} passages, one request each (EN+ES)")
        (WORK / f"{a.name}_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        json.dump(summary, sys.stdout, indent=1)
        print()
    elif a.cmd == "full":
        done = {json.loads(l)["passage_id"] for l in (WORK / "cc_results.jsonl").open(encoding="utf-8")} \
            if (WORK / "cc_results.jsonl").exists() else set()
        if a.stratum:
            ids = [r[0] for r in conn.execute(
                "select p.id from passage p where p.stratum = ? and p.token_count >= ? "
                "and p.id in (select passage_id from translation) and p.id not in (select passage_id from interpretation) "
                "order by p.volume, p.folio, p.side, p.para, p.id", (a.stratum, a.min_tokens))]
        else:
            ids = [pid for pid in surfaced_ids(conn) if pid not in done]
        reqs = [build_request(conn, pid, "plain") for pid in ids]
        (WORK / f"{a.name}_requests.json").write_text(json.dumps(reqs, ensure_ascii=False), encoding="utf-8")
        print(f"{len(reqs)} requests ({len(done)} already done) -> {a.name}")
        if a.submit:
            bid = submit(reqs)
            (WORK / f"{a.name}_batch_id").write_text(bid)
            print(f"submitted batch {bid}")
    elif a.cmd == "export":
        print(export(a.names))
    elif a.cmd == "chunks":
        print(f"{write_chunks(conn, a.size)} chunks -> {CHUNKS}")
    elif a.cmd == "ingest":
        print(json.dumps(ingest(a.chunk), ensure_ascii=False, indent=1))
    else:
        print(review(a.name))


if __name__ == "__main__":
    main()
