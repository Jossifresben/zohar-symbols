# Web-app plan — controller rulings (2026-10-11)

Decisions taken on the user's behalf while executing docs/superpowers/plans/2026-10-11-web-app.md, with cost if wrong. Deferred minors follow.

## Rulings
- Ruling: strings.json is created in Task 1 (with the keys T1 needs) and extended by every task; T8 completes it and adds the leak tests — why: avoids retrofitting t() into six templates — cost if wrong: none.
- Ruling: Task 1 conftest fixture appends a Ra'aya Meheimna section for folio 20b to the fixture wikitext (in the test, not the shared fixture file) so stream rendering is testable from Task 2 on.
- Ruling: Render builds the DB at deploy time from the revision lockfile (needs network + Atlas pushed); alternative (release asset) deferred — cost if wrong: slower/failing deploy, visible.
- Ruling: node partner metric = count(distinct passages containing a symbol of each node) — plan's "sum over symbol pairs" was wrong. Gloss fallback wording neutral: "{label}: appears in {n} passages of the Zohar; its commonest companion is {partner} ({m} passages together)." Search: register a Python-side casefold+accent-strip function on the connection and compare folded forms. scholars_pairs(lang). partners() drops pmi.
- Ruling: g.lang derived from request.path prefix (/es) — robust on 404 and static; header links use absolute endpoints (site.home / site_es.home) built from g.lang via a helper `lang_url(endpoint, **values)` in i18n.py (Task 8 keeps it) — cost if wrong: none.
- Ruling: the Sitra Aḥra border uses a token `--red-dim` = rgba of --red (no new hex).
- Ruling: Events card capped at 20 like the others; "+N more" for events goes to /search?kind=event → requires `search` to accept `kind` filter; small addition, ruled in.
- Ruling: highlight preserves separators (split with captured separators; advance position only on Hebrew-bearing pieces); page's own symbol wins on co-tagged tokens; strata chip → "Across {n} strata"; Aramaic text tagged lang="arc", Hebrew labels lang="he".
- Ruling: pillar is None for ein_sof and sitra_ahra (chip omitted); Spanish transliteration convention = the j-convention (Jésed, Jojmá, Netzaj, Maljut, Tzadik → "Tsadik"? no: keep "Tzadik" as the common Spanish form; standardise on one spelling "Tzadik").
- Ruling: EN switcher from an ES page targets `/?lang=en` style explicit param? No — cleaner: a `/lang/<code>?next=<path>` endpoint that sets the cookie and redirects; switch_url points there for the root/404 fallback case only; deep links keep direct URLs. switch_url builds query via urlencode, never kwargs.
- Ruling: deferred to follow-ups with ledger entries — Home node filter (v1.1), TEI export (v1.1), tradition section (plan 3: gloss content), node-page caching (42 ms, under budget) — cost if wrong: spec §6 partially delivered; documented.
- Ruling: Atlas pinned to commit 6e5f715 in pyproject (the packaging commit; it must still be PUSHED by the user); a committed `data/tables.v0.1.0.sha256` is checked after the build-time pipeline run and the deploy fails on mismatch; render.yaml gains healthCheckPath /healthz.
- Ruling: Spanish "Compañeros" (collides with the Ḥavraya) → "Acompañantes" across the partners panel and gloss fallback; EN stays "Partners".
- Ruling: caveat text stays as the user approved it even though glosses are computed today (plan 3 makes it true); orientation copy tweaked to not over-promise.

## Deferred minors
- Task 1: minor (deferred): check_same_thread=False unnecessary; `all` shadows builtin; coverage gaps (ZOHAR_DB env, teardown, t() KeyError)
- Task 2: minor (deferred): aliases NULL guard; nearest_symbols ids only; NODE_ORDER drops unknown nodes silently; lang unvalidated in column-name interpolation; folio() per-paragraph queries; search ranking ties; roman() KeyError outside 1–3; strings.json reformat noise
- Task 3: minor (deferred): tap targets <44px; kind-filter dead without JS (hide until JS); stale counts under filter; singular "1 symbols"; test order assertion via data-cluster
- Task 3: minor (deferred): switch_url drops query strings (one-liner: pass request.args) — carry into Task 8; /search?kind= prefills the box with the kind; test_events_cap_links_to_kind_search weak
- Task 4: minor (deferred): multi-word aliases highlight first word only; translation attribution line edge case (null model_id) — plan 3; states alphabetical order; `strata` ordering semantic
- Task 4: minor (deferred): gloss fallback ES '(n pasajes juntos)' vs panel 'juntos en n pasajes' — align in Task 8
- Task 5: minor (deferred): focus-ring test is a substring check; BRIEF_PATHS comment cites transient process context
- Task 6: minor (deferred): folio_neighbours scans all passages in Python (3 ms) — two index seeks would be cleaner; folio() N+1 (10 ms on 106 paras); lone "Next" link sits left; vacuous "Ra" assertion; para uniqueness per folio-side unverified
- Task 7: minor (deferred): token_shares() scans 832k rows per request (cache in Task 9); 29 bare revids shown without page names
- Task 8: minor (deferred): secure cookie needs ProxyFix behind Render's TLS proxy — carry into Task 10; switch_url hardcodes "home"
- Task 9: minor (deferred): perf test times the first request (no warm pass); two tautological cache assertions; symbols_table per request on Scholars; _meta context processor reads live vs cached meta; cache immutability by convention

## Deferred spec items
- Home node filter (v1.1) · TEI export (v1.1) · tradition section on symbol pages (plan 3) · node-page caching (42 ms, under budget)
