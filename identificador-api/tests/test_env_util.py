import os
from unittest.mock import patch

from env_util import (
    env_str,
    parse_bool,
    parse_float,
    parse_positive_int,
    parse_safe_search,
)


class TestParsePositiveInt:
    def test_valid_value(self):
        assert parse_positive_int("42", 10) == 42

    def test_empty_returns_fallback(self):
        assert parse_positive_int("", 10) == 10
        assert parse_positive_int(None, 10) == 10
        assert parse_positive_int("  ", 10) == 10

    def test_non_numeric_returns_fallback(self):
        assert parse_positive_int("abc", 10) == 10

    def test_zero_or_negative_returns_fallback(self):
        assert parse_positive_int("0", 10) == 10
        assert parse_positive_int("-5", 10) == 10


class TestParseBool:
    def test_truthy_values(self):
        for value in ("1", "true", "yes", "on", "TRUE", " Yes "):
            assert parse_bool(value, False) is True

    def test_falsy_values(self):
        for value in ("0", "false", "no", "off", "FALSE"):
            assert parse_bool(value, True) is False

    def test_empty_returns_fallback(self):
        assert parse_bool("", True) is True
        assert parse_bool(None, False) is False

    def test_unknown_returns_fallback(self):
        assert parse_bool("maybe", True) is True
        assert parse_bool("maybe", False) is False


class TestParseFloat:
    def test_valid_value(self):
        assert parse_float("3.14", 0.0) == 3.14

    def test_bounds(self):
        assert parse_float("5", 0.0, minimum=1.0, maximum=10.0) == 5.0
        assert parse_float("0.5", 2.0, minimum=1.0) == 2.0
        assert parse_float("15", 2.0, maximum=10.0) == 2.0

    def test_invalid_returns_fallback(self):
        assert parse_float("abc", 1.5) == 1.5
        assert parse_float("", 1.5) == 1.5


class TestParseSafeSearch:
    def test_none_defaults_true(self):
        assert parse_safe_search(None) is True

    def test_bool_passthrough(self):
        assert parse_safe_search(True) is True
        assert parse_safe_search(False) is False

    def test_string_truthy(self):
        assert parse_safe_search("true") is True
        assert parse_safe_search("1") is True

    def test_string_falsy(self):
        assert parse_safe_search("false") is False
        assert parse_safe_search("0") is False

    def test_unknown_string_defaults_true(self):
        assert parse_safe_search("maybe") is True


class TestEnvStr:
    def test_reads_env_var(self):
        with patch.dict(os.environ, {"TEST_VAR": "  hello  "}):
            assert env_str("TEST_VAR") == "hello"

    def test_default_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_str("MISSING_VAR", "default") == "default"
