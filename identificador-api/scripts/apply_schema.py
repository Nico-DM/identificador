"""Apply schema/*.sql migrations using DATABASE_URL from the environment."""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"

sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def main() -> int:
    from db.config import connection_params, db_enabled

    if not db_enabled():
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not SCHEMA_DIR.is_dir():
        print(f"No existe {SCHEMA_DIR}", file=sys.stderr)
        return 1

    from typing import cast

    import psycopg
    from psycopg.abc import Query

    migrations = sorted(SCHEMA_DIR.glob("*.sql"))
    if not migrations:
        print(f"No hay migraciones en {SCHEMA_DIR}", file=sys.stderr)
        return 1

    with psycopg.connect(**connection_params()) as conn:
        with conn.cursor() as cur:
            for path in migrations:
                sql = path.read_text(encoding="utf-8")
                cur.execute(cast(Query, sql))
                print(f"Applied {path.name}")
        conn.commit()
    print(f"Schema applied ({len(migrations)} migration(s)) from {SCHEMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
