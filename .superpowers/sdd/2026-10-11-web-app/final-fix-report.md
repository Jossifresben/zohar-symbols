# Final fix wave report

Atlas SHA pinned: 6e5f715534b0e386c75fdc2b321e9003ea276d3e

1. Footer licence: strings `footer_source` now "Text: Hebrew Wikisource (CC BY-SA 4.0)" / ES equivalent. Test: tests/web/test_final_fixes.py::test_footer_states_the_licence_not_public_domain.
2. Passage 404 suggestions: `_passage_suggestions` in web/views/__init__.py (own folio-side first passage, prev/next first passages via `folio_neighbours`, always the first passage); rendered as citation links in 404.html. Tests: test_unknown_passage_404, test_missing_passage_in_existing_folio_suggests_siblings.
3. `/es/search?kind=event`: box no longer prefilled (`q=""`, heading kept; results block shows when `q or heading`). Tests: test_search_by_kind, test_search_by_kind_es_does_not_prefill.
4. Reproducible deploy: pyproject pins Atlas @ full SHA; data/tables.v0.1.0.sha256; pipeline/check_tables.py (exit 1 on mismatch/missing); render.yaml buildCommand + healthCheckPath /healthz; README Deploy (EN/ES). Tests: tests/test_check_tables.py (match, tamper, missing, committed pair).
5. ES "Acompañantes": `partners`, `no_partners`, gloss_fallback, and the two method strings. Tests updated (test_i18n ES_UI, test_queries gloss, test_gloss_fallback_spanish_word_order) + test_partners_spanish_word_is_not_havraya.
6. Copy: orientation_read_body (no translation claim), Ask card "(coming soon)"/"(próximamente)"; caveat untouched. Test: test_orientation_copy_makes_no_translation_claim.
7. Stream headings on every stream change incl. main (`stream_main`; passage.html tracks current stream). Tests: test_stream_headings_on_every_change (synthetic main/stream/main), test_passage_page_headings_include_main; test_stream_passage_has_heading adjusted to 2 headings; test_i18n dynamic family now includes main.
8. `_meta` context processor reads `queries.cached("meta")`. Test: test_requests_do_not_recompute_cached_queries now also fails on any `from meta` SQL during requests.
9. BibTeX: `note = {DOI pending}`, no `doi =`; `cite.formats(meta, lang)` uses "Versión" in ES for Chicago/SBL. Tests: test_cite, test_scholars_page.
10. `num` Jinja filter + `i18n.fmt_num` (EN 15,909 / ES 15.909); applied on Scholars counts and pair table, node bars, symbol-page counts, and `passages_n` in glosses. Test: test_num_filter_thousands_separators (both languages).
11. a11y: h1 on 404 pages and /ask; "back home" link; aria-labels on both navs (`nav_site`, `nav_folio`); 44px min-height on nav links and lang buttons; `lang="he"` on tree SVG Hebrew; marker roots joined " · ". Tests: test_a11y_headings_and_nav_labels, test_tree_hebrew_text_is_tagged, test_state_marker_roots_joined_with_middots, test_tap_targets_css.
12. Scholars aliases: `queries.alias_split()` (cached as `alias_split`), label "{surfaces} forms + {roots} roots" / "formas" / "raíces" (`sch_forms_roots`; sch_p_counts rephrased "symbols and aliases (…)"). Test: test_scholars_counts_from_data.
13. Fresh client per language in test_every_chip_and_card_link_resolves and test_switch_url.
14. `sch_e_symbol` (EN/ES) documents the leading `# tables_version=` comment line and pandas `comment='#'`.
