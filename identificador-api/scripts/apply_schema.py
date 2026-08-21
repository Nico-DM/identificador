"""Apply schema/001_init.sql using DATABASE_URL from the environment."""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "001_init.sql"

sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def main() -> int:
    from db.config import connection_params, db_enabled

    if not db_enabled():
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not SCHEMA.is_file():
        print(f"No existe {SCHEMA}", file=sys.stderr)
        return 1

    from typing import cast

    import psycopg
    from psycopg.abc import Query

    sql = SCHEMA.read_text(encoding="utf-8")
    with psycopg.connect(**connection_params()) as conn:
        with conn.cursor() as cur:
            cur.execute(cast(Query, sql))
        conn.commit()
    print(f"Schema applied from {SCHEMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
