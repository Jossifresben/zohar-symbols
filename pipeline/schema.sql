CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE passage (
  id TEXT PRIMARY KEY, volume INTEGER NOT NULL, folio INTEGER NOT NULL, side TEXT NOT NULL,
  para INTEGER NOT NULL, parasha TEXT NOT NULL, stratum TEXT NOT NULL,
  text_ar TEXT NOT NULL, verse_ref TEXT, token_count INTEGER NOT NULL
);
CREATE TABLE token (
  passage_id TEXT NOT NULL REFERENCES passage(id), position INTEGER NOT NULL,
  surface TEXT NOT NULL, root TEXT, stem TEXT, confidence REAL NOT NULL, source TEXT NOT NULL,
  PRIMARY KEY (passage_id, position)
);
CREATE TABLE symbol (
  id TEXT PRIMARY KEY, label_en TEXT NOT NULL, label_es TEXT NOT NULL, label_ar TEXT NOT NULL,
  kind TEXT NOT NULL, node TEXT NOT NULL, aliases TEXT NOT NULL,
  gloss_en TEXT, gloss_es TEXT, moves_en TEXT, moves_es TEXT, seed_source TEXT NOT NULL,
  count_raw INTEGER NOT NULL, count_resolved INTEGER NOT NULL, count_passages INTEGER NOT NULL
);
CREATE TABLE mention (
  symbol_id TEXT NOT NULL REFERENCES symbol(id), passage_id TEXT NOT NULL REFERENCES passage(id),
  position INTEGER NOT NULL, matched_form TEXT NOT NULL, via TEXT NOT NULL
);
CREATE INDEX mention_symbol ON mention(symbol_id);
CREATE INDEX mention_passage ON mention(passage_id);
CREATE TABLE cooccurrence (
  symbol_a TEXT NOT NULL, symbol_b TEXT NOT NULL, passages_together INTEGER NOT NULL,
  pmi REAL NOT NULL, tables_version TEXT NOT NULL, PRIMARY KEY (symbol_a, symbol_b)
);
CREATE TABLE state (
  symbol_id TEXT NOT NULL, state_label TEXT NOT NULL, marker_roots TEXT NOT NULL,
  passage_id TEXT NOT NULL, PRIMARY KEY (symbol_id, state_label, passage_id)
);
CREATE TABLE surfaced (symbol_id TEXT NOT NULL, rank INTEGER NOT NULL, passage_id TEXT NOT NULL,
  PRIMARY KEY (symbol_id, rank));
CREATE TABLE translation (
  passage_id TEXT NOT NULL, lang TEXT NOT NULL, text TEXT NOT NULL, model_id TEXT NOT NULL,
  prompt_hash TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (passage_id, lang)
);
CREATE TABLE gloss (
  symbol_id TEXT NOT NULL, source TEXT NOT NULL, locus TEXT NOT NULL,
  summary_en TEXT NOT NULL, summary_es TEXT NOT NULL, PRIMARY KEY (symbol_id, source, locus)
);
