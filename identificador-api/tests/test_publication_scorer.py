from unittest.mock import patch

from models import DateCandidate
from publication_scorer import (
    _needs_dynamic,
    _resolve_with_dynamic,
    _sort_publications,
    _StaticPhaseOutcome,
    classify_context,
    deserialize_pending_outcome,
    detect_platform,
    domain_authority_score,
    merge_publications,
    normalize_url,
    score_candidate,
    select_best_candidate,
    serialize_pending_outcome,
)
from scrape_config import SCRAPE_STATIC_CONFIDENCE_THRESHOLD
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

    def test_artstation(self):
        assert detect_platform("https://www.artstation.com/artwork/abc") == "artstation"

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
    def test_htmldate_scores_above_ld_json(self):
        htmldate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="htmldate",
            raw="2024-01-01",
            extractor="static",
            url="https://example.com",
        )
        ld_json = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="ld+json",
            raw="",
            extractor="static",
            url="https://example.com",
        )
        assert score_candidate(htmldate, "unknown", {}) > score_candidate(
            ld_json, "unknown", {}
        )

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


class TestDomainAuthority:
    def test_artist_platform_scores_high(self):
        assert domain_authority_score("https://www.deviantart.com/deevad/art/Watcher") == 1.0

    def test_wikipedia_is_penalized_as_repost(self):
        wiki = domain_authority_score("https://en.wikipedia.org/wiki/Test")
        defaultish = domain_authority_score("https://example.com/post/1")
        assert wiki < defaultish

    def test_pinterest_scores_lower_than_artist_platform(self):
        da = domain_authority_score("https://www.deviantart.com/deevad/art/Watcher")
        pin = domain_authority_score("https://www.pinterest.com/pin/1")
        assert da > pin

    def test_pixiv_scores_as_artist_platform(self):
        assert domain_authority_score("https://www.pixiv.net/en/artworks/1") == 0.95

    def test_sort_prefers_authoritative_source(self):
        publications = [
            {
                "link": "https://www.pinterest.com/pin/1",
                "confidence": "confirmed",
                "created_utc": utc_dt(2010, 1, 1),
                "score": 0.9,
                "engine_rank": 1,
            },
            {
                "link": "https://www.deviantart.com/deevad/art/Watcher",
                "confidence": "provisional",
                "created_utc": utc_dt(2020, 1, 1),
                "score": 0.2,
                "engine_rank": 2,
            },
        ]
        _sort_publications(publications)
        assert publications[0]["link"].startswith("https://www.deviantart.com")

    def test_sort_prefers_older_date_over_engine_rank(self):
        publications = [
            {
                "link": "https://www.youtube.com/watch?v=recent",
                "confidence": "confirmed",
                "created_utc": utc_dt(2026, 10, 11),
                "score": 0.95,
                "engine_rank": 1,
            },
            {
                "link": "https://example.com/older-post",
                "confidence": "confirmed",
                "created_utc": utc_dt(2017, 1, 3),
                "score": 0.75,
                "engine_rank": 8,
            },
        ]
        _sort_publications(publications)
        assert publications[0]["link"] == "https://example.com/older-post"


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


class TestNeedsDynamic:
    def test_low_score_always_needs_dynamic(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="plain-text",
            raw="",
            extractor="static",
            url="https://example.com",
            score=0.1,
        )
        assert _needs_dynamic("unknown", candidate) is True
        assert _needs_dynamic("instagram", candidate) is True

    def test_high_score_non_js_skips_dynamic(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="htmldate",
            raw="",
            extractor="static",
            url="https://example.com",
            score=SCRAPE_STATIC_CONFIDENCE_THRESHOLD,
        )
        assert _needs_dynamic("unknown", candidate) is False

    def test_js_platform_still_needs_dynamic_with_high_static(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="meta",
            raw="",
            extractor="static",
            url="https://www.deviantart.com/x/art/1",
            score=0.9,
        )
        assert _needs_dynamic("deviantart", candidate) is True
        assert _needs_dynamic("instagram", candidate) is True

    def test_cached_dynamic_extractor_skips_rescan(self):
        candidate = DateCandidate(
            date=utc_dt(2024, 1, 1),
            source="time",
            raw="",
            extractor="dynamic",
            url="https://instagram.com/p/abc",
            score=0.7,
        )
        assert _needs_dynamic("instagram", candidate) is False


class TestResolveWithDynamicCache:
    def test_caches_winning_dynamic_candidate(self):
        outcome = _StaticPhaseOutcome(
            result={"link": "https://instagram.com/p/abc", "source": "google"},
            url="https://instagram.com/p/abc",
            platform="instagram",
            static_candidates=[],
            best_static=None,
            needs_dynamic=True,
            publication=None,
        )
        dynamic_hit = DateCandidate(
            date=utc_dt(2023, 6, 1),
            source="time",
            raw="2023-06-01",
            extractor="dynamic",
            url="https://instagram.com/p/abc",
        )
        with (
            patch(
                "publication_scorer.fetch_dynamic_candidates",
                return_value=[dynamic_hit],
            ),
            patch("publication_scorer.set_url_scrape_cache") as mock_cache,
        ):
            pub = _resolve_with_dynamic(outcome)

        assert pub is not None
        assert pub["confidence"] in {"confirmed", "provisional"}
        mock_cache.assert_called_once()
        assert mock_cache.call_args.kwargs["extractor"] == "dynamic"
