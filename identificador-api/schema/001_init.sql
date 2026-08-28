-- Esquema inicial Identificador (Supabase / Postgres).
-- Ejecutar en Supabase → SQL Editor, o: psql "$DATABASE_URL" -f schema/001_init.sql

-- Búsquedas en curso o recientes (reemplaza estado en memoria del API)
CREATE TABLE IF NOT EXISTS searches (
  search_id UUID PRIMARY KEY,
  status TEXT NOT NULL,
  phase TEXT NOT NULL DEFAULT 'static',
  image_url TEXT NOT NULL,
  results JSONB,
  raw_results JSONB,
  error TEXT,
  processed_urls INT NOT NULL DEFAULT 0,
  total_urls INT NOT NULL DEFAULT 0,
  static_total_urls INT NOT NULL DEFAULT 0,
  match_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  pending_dynamic JSONB NOT NULL DEFAULT '[]'::jsonb,
  deep_search_available BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_searches_created_at ON searches (created_at);
CREATE INDEX IF NOT EXISTS idx_searches_status ON searches (status);

-- Caché de scraping por URL normalizada
CREATE TABLE IF NOT EXISTS url_scrape_cache (
  url_normalized TEXT PRIMARY KEY,
  platform TEXT,
  date_utc TIMESTAMPTZ,
  score REAL,
  source TEXT,
  extractor TEXT,
  confidence TEXT,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_url_scrape_scraped_at ON url_scrape_cache (scraped_at);

-- Caché de respuesta del motor de búsqueda inversa por URL de imagen y motor
CREATE TABLE IF NOT EXISTS image_engine_cache (
  image_url_hash TEXT NOT NULL,
  image_url TEXT NOT NULL,
  engine TEXT NOT NULL,
  engine_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (image_url_hash, engine)
);

CREATE INDEX IF NOT EXISTS idx_image_engine_created_at ON image_engine_cache (created_at);

-- Caché de análisis completo por URL de imagen (evita re-scrapear todo)
CREATE TABLE IF NOT EXISTS image_analysis_cache (
  cache_key TEXT PRIMARY KEY,
  image_url TEXT NOT NULL,
  safe_search BOOLEAN NOT NULL DEFAULT true,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_analysis_created_at ON image_analysis_cache (created_at);

-- RLS: tablas no expuestas al cliente web; el backend usa DATABASE_URL (rol postgres).
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE url_scrape_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_engine_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_analysis_cache ENABLE ROW LEVEL SECURITY;
