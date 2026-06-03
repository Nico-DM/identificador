from contextlib import contextmanager
from typing import Iterator

from db.config import connection_params

_pool = None


def _get_conn():
    global _pool
    import psycopg
    from psycopg.rows import dict_row

    if _pool is None or _pool.closed:
        _pool = psycopg.connect(**connection_params(), row_factory=dict_row, autocommit=False)
    return _pool


@contextmanager
def db_cursor() -> Iterator:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
