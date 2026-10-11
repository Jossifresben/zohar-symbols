# Backlog

Deferred work, most likely first. Dates are when the item was parked.

## Interpretations: "What this passage means" (parked 2026-10-11, budget)

A plain-language EN/ES interpretation under each translated passage, 120–200 words, labelled "Interpretation inferred by Claude Fable 5.1, not a traditional commentary, not reviewed by specialists", with the "report a problem" link. No citations shown to the reader.

- **Built:** `pipeline/commentary.py` caches the Sefaria text (public domain, Hebrew) of Ohr HaChamah and Mikdash Melekh for the folio-sides of the translated passages under `work/commentary/` (not committed, not displayed). 471 of the 678 translated passages have commentary on their folio-side (Ohr HaChamah 344 of 422 folio-sides, Mikdash Melekh 294). `pipeline/interpret.py` (prompt `i1`) builds one request per passage returning both languages.
- **Pilot done:** 10 passages, each in two variants (commentary as unseen background vs. without), $1.31. Blind A/B page: `work/interpret/pilot_review.html` (rebuild with `python -m pipeline.interpret review pilot`); the key is `work/interpret/pilot_key.json`. All 20 well-formed; no later-Kabbalah terms, no commentator names. Length ran 201–238 words: tighten in `i2`.
- **Review (2026-10-11):** blind first pass then a re-read: 5 grounded, 5 plain. Side-by-side reading of three pairs found equal accuracy, plain often more concrete. **Decision: plain for all passages** (no commentary in the request); grounding is not worth the ~50% extra. The commentary cache stays available if the hardest strata (Idrot, Sitrei Torah) ever need it.
- **Next:** prompt `i2` (hard cap of 200 words per language) → full run, plain, 678 passages, about $32 → export to `data/interpretations.v*.jsonl` with the translations' provenance and staleness check → `interpretation` table → section under the translation on the passage page.
- **Budget:** needs about $40 of API headroom (org monthly spend limit, Console → Billing).

## Text and segmentation

- Merge a paragraph split by a folio break: `3.253b.013` is one word ("אלין") whose sentence continues in `3.254a.005` (zohar.com Pinchas ¶790). Renumbers ids: next tables version.
- III 116a–b: no passage is numbered there; most likely a printed numbering skip (commentaries silent, 115b normal length). Confirm against a scan of the Mantua print.
- Nikud: dropped. No openly licensed vocalized Zohar exists (zohar.com and Sefaria's 2013 vocalized edition are not clearable).

## Content

- Review table of all 139 symbol labels, EN and ES (after the Teshuvah correction).
- Symbol glosses and Ask (spec §7: strict cited answer first, then a visibly marked model reading). Parked 2026-10-11 for budget. Ask is the only live model call: about $0.15–0.30 per uncached question with Fable (both layers), about a day of work. Needs an API key on Render: use a separate Console workspace and key with its own monthly spend limit (e.g. $20); when spent, Ask falls back to the retrieved links. Consider a cheaper model for Layer 1. Do the interpretations first.
- `/read` contents page (parashot and folios).
- Scholarly spot-checks: strata boundaries (Midrash ha-Ne'lam, addenda), seed sefirah assignments marked "Zohar usage".

## v1.1

- Home: filter by sefirah.
- TEI export.
- Zohar Chadash, Tikkunei Zohar.
