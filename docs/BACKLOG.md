# Backlog

Deferred work, most likely first. Dates are when the item was parked.

## Interpretations: follow-ups

Done 2026-10-12: 677 of 678 translated passages have "What this passage means" in EN and ES (prompt `i2`, plain, Claude Fable 5.1; 20 via Claude Code sub-agents, 658 via the Batch API for $32.53; pilot $1.31).

- `3.128a.014` (Idra Rabba): the model refused; no interpretation. Retry with a reworded request or write one by hand in `data/interpretation_overrides.tsv`.
- Length runs over the 200-word target (up to ~270); accepted. Tighten in a later prompt version if it matters.
- The grounded variant (Sefaria commentary as background) is kept in `pipeline/commentary.py` / `work/commentary/` if the hardest strata need it.

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
