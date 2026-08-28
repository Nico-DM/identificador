-- Renombra caché legacy (Google Lens / SerpAPI) a nombres genéricos de motor.
-- Ejecutar una vez en bases ya desplegadas con 001_init.sql anterior.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'image_lens_cache'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'image_engine_cache'
  ) THEN
    ALTER TABLE image_lens_cache RENAME TO image_engine_cache;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'image_engine_cache'
      AND column_name = 'serpapi_payload'
  ) THEN
    ALTER TABLE image_engine_cache RENAME COLUMN serpapi_payload TO engine_payload;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'idx_image_lens_created_at'
  ) THEN
    ALTER INDEX idx_image_lens_created_at RENAME TO idx_image_engine_created_at;
  END IF;
END $$;
