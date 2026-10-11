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
import random
import sys
from pathlib import Path

from . import commentary
from .translate import (CONTEXT_RADIUS, EFFORT, MODEL, connect, collect, cost_usd, submit,  # noqa: F401
                        surfaced_ids, _all_tokens)

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "interpret"

PROMPT_VERSION = "i1"
VARIANTS = ("grounded", "plain")
MAX_COMMENTARY_CHARS = 12000   # per work, per folio-side

INSTRUCTIONS = """You write short explanations of Zohar passages for a bilingual website for curious readers who know nothing about Kabbalah. The site already shows the Aramaic text and a translation; your text sits under them with the heading "What this passage means".

Write what the passage means:
- 120 to 200 words in each language. Plain, warm, precise prose for an intelligent reader; no jargon left unexplained.
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
    else:
        print(review(a.name))


if __name__ == "__main__":
    main()
