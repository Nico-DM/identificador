from models import DateCandidate
from publication_scorer import (
    _StaticPhaseOutcome,
    classify_context,
    deserialize_pending_outcome,
    detect_platform,
    merge_publications,
    normalize_url,
    score_candidate,
    select_best_candidate,
    serialize_pending_outcome,
)
from tests.helpers import utc_dt


class TestNormalizeUrl:
    def test_strips_tracking_params(self):
        url = "https://example.com/page?utm_source=twitter&id=1"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "id=1" in result

    def test_strips_fragment(self):
        url = "https://example.com/page#section"
        result = normalize_url(url)
        assert "#" not in result


class TestDetectPlatform:
    def test_youtube(self):
        assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
        assert detect_platform("https://youtu.be/abc") == "youtube"

    def test_reddit(self):
        assert detect_platform("https://reddit.com/r/test") == "reddit"

    def test_x_twitter(self):
        assert detect_platform("https://x.com/user/status/1") == "x"
        assert detect_platform("https://twitter.com/user") == "x"

    def test_unknown(self):
        assert detect_platform("https://example.com/page") == "unknown"


class TestClassifyContext:
    def test_embed_path(self):
        flags = classify_context("https://example.com/embed/video", "unknown")
        assert flags["is_embed"] is True

    def test_comment_path(self):
        flags = classify_context("https://example.com/post/comment/1", "unknown")
        assert flags["is_comment"] is True

    def test_profile_instagram(self):
        flags = classify_context("https://instagram.com/username", "instagram")
        assert flags["is_profile"] is True

    def test_reddit_comment_not_flagged(self):
        flags = classify_context("https://reddit.com/r/test/comments/abc", "reddit")
        assert flags["is_comment"] is False


class TestScoreCandidate:
    def test_ld_json_scores_high(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="ld+json",
            raw="",
            extractor="static",
            url="https://example.com",
        )
        score = score_candidate(candidate, "unknown", {})
        assert score >= 0.5

    def test_comment_penalty(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="ld+json",
            raw="",
            extractor="static",
            url="https://example.com",
        )
        base = score_candidate(candidate, "unknown", {})
        penalized = score_candidate(
            candidate, "unknown", {"is_comment": True}
        )
        assert penalized < base

    def test_score_never_negative(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="plain-text",
            raw="",
            extractor="static",
            url="https://example.com",
        )
        score = score_candidate(
            candidate,
            "unknown",
            {"is_comment": True, "is_reply": True, "is_share": True},
        )
        assert score >= 0.0


class TestSelectBestCandidate:
    def test_empty_returns_none(self):
        assert select_best_candidate([]) is None

    def test_picks_highest_score_above_threshold(self):
        candidates = [
            DateCandidate(
                date=utc_dt(2024, 1, 1),
                source="meta",
                raw="",
                extractor="static",
                url="https://a.com",
                score=0.3,
            ),
            DateCandidate(
                date=utc_dt(2024, 2, 1),
                source="ld+json",
                raw="",
                extractor="static",
                url="https://b.com",
                score=0.8,
            ),
        ]
        best = select_best_candidate(candidates)
        assert best is not None
        assert best.score == 0.8

    def test_falls_back_to_all_when_below_threshold(self):
        candidates = [
            DateCandidate(
                date=utc_dt(2024, 3, 1),
                source="plain-text",
                raw="",
                extractor="static",
                url="https://a.com",
                score=0.1,
            ),
            DateCandidate(
                date=utc_dt(2024, 1, 1),
                source="plain-text",
                raw="",
                extractor="static",
                url="https://b.com",
                score=0.05,
            ),
        ]
        best = select_best_candidate(candidates, threshold=0.45)
        assert best is not None
        assert best.date == utc_dt(2024, 1, 1)


class TestMergePublications:
    def test_merges_by_url(self):
        existing = [
            {
                "link": "https://example.com/a",
                "score": 0.3,
                "confidence": "provisional",
                "created_utc": None,
            }
        ]
        updates = [
            {
                "link": "https://example.com/a",
                "score": 0.8,
                "confidence": "confirmed",
                "created_utc": utc_dt(2024, 6, 1),
            }
        ]
        merged = merge_publications(existing, updates)
        assert len(merged) == 1
        assert merged[0]["score"] == 0.8

    def test_adds_new_urls(self):
        existing = [{"link": "https://a.com", "score": 0.5}]
        updates = [{"link": "https://b.com", "score": 0.6}]
        merged = merge_publications(existing, updates)
        assert len(merged) == 2


class TestPendingOutcomeSerialization:
    def test_roundtrip(self):
        best = DateCandidate(
            date=utc_dt(2024, 5, 10, 14, 0, 0),
            source="meta",
            raw="2024-05-10",
            extractor="static",
            url="https://example.com/post",
            score=0.6,
            flags={"is_embed": False},
        )
        outcome = _StaticPhaseOutcome(
            result={"link": "https://example.com/post", "source": "google"},
            url="https://example.com/post",
            platform="unknown",
            static_candidates=[best],
            best_static=best,
            needs_dynamic=True,
            publication=None,
        )
        data = serialize_pending_outcome(outcome)
        restored = deserialize_pending_outcome(data)
        assert restored.url == outcome.url
        assert restored.needs_dynamic is True
        assert restored.best_static is not None
        assert restored.best_static.score == 0.6
