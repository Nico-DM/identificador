-- Fase 2: caché compartida (Supabase/Postgres). Ejecutar en el SQL Editor del proyecto.

CREATE TABLE IF NOT EXISTS url_scrape_cache (
  url_normalized TEXT PRIMARY KEY,
  platform TEXT,
  date_utc TIMESTAMPTZ,
  score REAL,
  source TEXT,
  extractor TEXT,
  confidence TEXT,
  scraped_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_url_scrape_scraped_at ON url_scrape_cache (scraped_at);

CREATE TABLE IF NOT EXISTS image_lens_cache (
  image_url_hash TEXT PRIMARY KEY,
  image_url TEXT NOT NULL,
  serpapi_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
