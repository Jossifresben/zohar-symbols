# Backlog

Deferred work, most likely first. Dates are when the item was parked.

## Interpretations: follow-ups

Done 2026-10-12: 677 of 678 translated passages have "What this passage means" in EN and ES (prompt `i2`, plain, Claude Fable 5.1; 20 via Claude Code sub-agents, 658 via the Batch API for $32.53; pilot $1.31).

- `3.128a.014` (Idra Rabba): the model refused; no interpretation. Retry with a reworded request or write one by hand in `data/interpretation_overrides.tsv`.
- Length runs over the 200-word target (up to ~270); accepted. Tighten in a later prompt version if it matters.
- The grounded variant (Sefaria commentary as background) is kept in `pipeline/commentary.py` / `work/commentary/` if the hardest strata need it.

## Idra Zuta, complete (parked 2026-10-12, budget)

Make the Idra Zuta (III 287b–296b, 141 passages) the first unit readable in full. 41 passages are translated and interpreted; 100 are not.

- **Ready:** `python -m pipeline.translate stratum --stratum idra_zuta --name idra_zuta --submit` (200 requests, ≈ $10), then export `full_a full_b fix_teshuvah idra_zuta`, `run_all`, then `python -m pipeline.interpret full --stratum idra_zuta --name idra_zuta --submit` (97 passages of ≥ 12 words, ≈ $5), export `full idra_zuta`, `run_all`. Needs the API spend limit at ≈ $165 (Console → Billing).
- **The Idrot page** (`/idrot`) is built: what each Assembly is, its range and counts, its most-mentioned images, its translated passages.
- **Other English translations checked (2026-10-12):**
  - Michal Ricardo, *Idra Zuta, The Small Gathering*, on Sefaria: complete (180 paragraphs), CC BY, aligns with our text (95% token match; 10 of its paragraphs straddle two of our passages). Not used as our text: it weaves the Lurianic commentary into the translation ("Keter of Arich Anpin", "that is, Yesod"), which breaks the site's rule of keeping images as images, and may derive from the Sulam's paraphrase (unclear rights). Possible link-out from Idra passages, labelled as a commentary-based translation.
  - zoharonline.org (Elizeu A.S., English via Portuguese): reserved rights, no bulk reuse without written permission. Not usable; at most a link.
- **Idea, not scheduled:** the Idrot compared with the rest of the Zohar (rate per 10,000 words, keyness, partners), using the strata we already have.

## Tikkunei ha-Zohar (evaluated 2026-10-12, not scheduled)

A separate corpus, kept apart from the Zohar's counts. Sources: Hebrew Wikisource "תיקוני זהר" (full text and 296 folio pages, CC BY-SA, same pipeline); Sefaria "Tikkunei Zohar - Vocalized" (Public Domain, with nikud). Not usable: Sefaria's Constantinople 1740 edition and David Solomon's English (both CC BY-NC). Value: a computed comparison of how the same images behave in the Zohar, the Ra'aya Meheimna and the Tikkunim (rates, keyness, partners, sefirah names nearby); genre and seed-list bias are the caveats. About 1–2 days; translations extra.

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
- Zohar Chadash (Tikkunei Zohar: see above).
