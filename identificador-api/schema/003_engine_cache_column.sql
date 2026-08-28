-- Añade columna engine y usa clave primaria compuesta (url_hash, engine).
-- Rehashea image_url_hash solo con la URL (sin mezclar el motor en el hash).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE image_engine_cache ADD COLUMN IF NOT EXISTS engine TEXT;

UPDATE image_engine_cache
SET engine = 'google_reverse_image'
WHERE engine IS NULL;

UPDATE image_engine_cache
SET image_url_hash = encode(digest(trim(image_url), 'sha256'), 'hex')
WHERE image_url IS NOT NULL;

ALTER TABLE image_engine_cache ALTER COLUMN engine SET NOT NULL;

DELETE FROM image_engine_cache a
USING image_engine_cache b
WHERE a.image_url_hash = b.image_url_hash
  AND a.engine = b.engine
  AND a.created_at < b.created_at;

DO $$
DECLARE
  pk_columns INT;
BEGIN
  SELECT COUNT(*) INTO pk_columns
  FROM information_schema.key_column_usage
  WHERE table_schema = 'public'
    AND table_name = 'image_engine_cache'
    AND constraint_name = (
      SELECT tc.constraint_name
      FROM information_schema.table_constraints tc
      WHERE tc.table_schema = 'public'
        AND tc.table_name = 'image_engine_cache'
        AND tc.constraint_type = 'PRIMARY KEY'
      LIMIT 1
    );

  IF pk_columns IS NULL OR pk_columns < 2 THEN
    ALTER TABLE image_engine_cache DROP CONSTRAINT IF EXISTS image_engine_cache_pkey;
    ALTER TABLE image_engine_cache ADD PRIMARY KEY (image_url_hash, engine);
  END IF;
END $$;
