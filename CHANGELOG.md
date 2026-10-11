# Changelog

## tables 0.1.0 — 2026-10-11
- First full build of the Zohar main body (3 volumes, Mantua pagination) from Hebrew Wikisource: 29 parasha pages, 1,607 folio-sides, 13,915 passages, 725,450 tokens. `זוהר השמטות` excluded.
- Symbol seed: 139 symbols, 362 surface aliases (Cordovero gate 23, Gikatilla, Zohar usage). 138 have at least one mention; `mouth_of_river` (פומא דנהרא) has none in the main body.
- Mentions: 47,980; 5,443 co-occurrence pairs (PMI over all passages); 226 state rows.
- Strata (conventional ranges): main 11,616; Ra'aya Meheimna 867; Idra Rabba 656; Midrash ha-Ne'lam 566; Idra Zuta 150; Sitrei Torah 60 passages.
- Tokens: 70.5% with root; 21.9% known non-lexical (empty-root override: function words, divine names, abbreviations); 7.5% unknown (no root). Confidence ≥ 0.8: 54.9%.
- Text fixes: templates that carry Zohar text (gematria, abbreviation expansions, underlined or enlarged words) are kept instead of dropped; folio labels with a parasha suffix (`דף לה ב - צו`) parse; five one-off Wikisource typos are patched in `pipeline/segment.py` with a comment each.
- Known gaps: 31 folio-sides absent from the Wikisource pages: vol. 1: 80b 81a 89b 118a 251b; vol. 2: 1a 1b 158a 158b 269b; vol. 3: 1a 1b 28a 29a 116a 116b 275b-282b. Tosefta sections (`תוספתא דף ...`) are skipped.
- Not yet: Zohar Chadash, Tikkunei Zohar, translations, glosses.
