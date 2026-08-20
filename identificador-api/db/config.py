import os

from psycopg.conninfo import conninfo_to_dict, make_conninfo


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def database_url() -> str:
    return _env("DATABASE_URL")


def database_password() -> str:
    return _env("DATABASE_PASSWORD")


def cache_ttl_seconds() -> int:
    return int(_env("CACHE_TTL_SECONDS", str(7 * 24 * 3600)))


def connection_params() -> dict:
    url = database_url()
    if not url:
        return {}
    params = conninfo_to_dict(url)
    password = database_password()
    if password:
        params["password"] = password
    return params


def connection_string() -> str:
    params = connection_params()
    if not params:
        return ""
    return make_conninfo("", **params)


def db_enabled() -> bool:
    if _env("DISABLE_DATABASE").lower() in ("1", "true", "yes"):
        return False
    return bool(database_url())
