#!/usr/bin/env python3
"""Aplica schema/001_init.sql usando DATABASE_URL del entorno."""

from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "001_init.sql"

sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def main() -> int:
    from db.config import connection_params, db_enabled

    if not db_enabled():
        print("DATABASE_URL no está definida.", file=sys.stderr)
        return 1
    if not SCHEMA.is_file():
        print(f"No existe {SCHEMA}", file=sys.stderr)
        return 1

    import psycopg

    sql = SCHEMA.read_text(encoding="utf-8")
    with psycopg.connect(**connection_params()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"Esquema aplicado desde {SCHEMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
