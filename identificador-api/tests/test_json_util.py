from datetime import datetime

from db.json_util import from_jsonable, to_jsonable
from tests.helpers import utc_dt


class TestJsonUtil:
    def test_none_roundtrip(self):
        assert to_jsonable(None) is None
        assert from_jsonable(None) is None

    def test_datetime_encoding(self):
        dt = utc_dt(2024, 6, 15, 12, 30, 0)
        encoded = to_jsonable({"created": dt})
        assert encoded["created"] == "2024-06-15T12:30:00"

    def test_datetime_decoding(self):
        data = {"created": "2024-06-15T12:30:00"}
        decoded = from_jsonable(data)
        assert isinstance(decoded["created"], datetime)
        assert decoded["created"] == utc_dt(2024, 6, 15, 12, 30, 0)

    def test_nested_structure(self):
        dt = utc_dt(2024, 1, 1)
        original = {"items": [{"date": dt}, {"name": "test"}]}
        roundtripped = from_jsonable(to_jsonable(original))
        assert isinstance(roundtripped["items"][0]["date"], datetime)
        assert roundtripped["items"][1]["name"] == "test"

    def test_non_date_string_unchanged(self):
        data = {"title": "hello-world"}
        assert from_jsonable(data) == data
