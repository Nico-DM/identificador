from env_util import env_str
from psycopg.conninfo import conninfo_to_dict


def database_url() -> str:
    return env_str("DATABASE_URL")


def database_password() -> str:
    return env_str("DATABASE_PASSWORD")


def cache_ttl_seconds() -> int:
    return int(env_str("CACHE_TTL_SECONDS", str(7 * 24 * 3600)))


def connection_params() -> dict:
    url = database_url()
    if not url:
        return {}
    params = conninfo_to_dict(url)
    password = database_password()
    if password:
        params["password"] = password
    return params


def db_enabled() -> bool:
    if env_str("DISABLE_DATABASE").lower() in ("1", "true", "yes"):
        return False
    return bool(database_url())
