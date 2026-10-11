# Changelog

## tables 0.1.0 — 2026-10-11
- First full build of the Zohar main body (3 volumes, Mantua pagination) from Hebrew Wikisource: 29 parasha pages, 1,607 folio-sides, 13,915 passages, 725,418 tokens. `זוהר השמטות` excluded.
- Symbol seed: 139 symbols, 362 surface aliases (Cordovero gate 23, Gikatilla, Zohar usage). 138 have at least one mention; `mouth_of_river` (פומא דנהרא) has none in the main body.
- Mentions: 47,979 (47,695 by surface, 284 by root); 5,443 co-occurrence pairs (PMI over all passages); 226 state rows.
- Strata (conventional ranges): main 11,616; Ra'aya Meheimna 867; Idra Rabba 656; Midrash ha-Ne'lam 566; Idra Zuta 150; Sitrei Torah 60 passages.
- Tokens with root: 70.2% (confidence ≥ 0.8: 54.9%). Empty-root overrides (function words, divine names, abbreviations) are counted as known non-lexical, not as roots.
- Text fixes: templates that carry Zohar text (gematria, abbreviation expansions, underlined or enlarged words) are kept instead of dropped; folio labels with a parasha suffix (`דף לה ב - צו`) parse; five one-off Wikisource typos are patched in `pipeline/segment.py` with a comment each.
- Known gaps: 31 folio-sides absent from the Wikisource pages (e.g. vol. 3, 275b-282b; vol. 2, 1a-b and 158a-b) and Tosefta sections (`תוספתא דף ...`) are not read.
- Not yet: Zohar Chadash, Tikkunei Zohar, translations, glosses.
