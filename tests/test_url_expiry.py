"""Unit test untuk deteksi masa berlaku URL."""
import base64
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.url_expiry import (  # noqa: E402
    analyze_url_expiry,
    apply_expiry_fields,
    expiry_badge,
    expiry_tooltip,
    format_remaining,
    url_expiry_fields,
)

NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
EPOCH = int(NOW.timestamp())


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class TestUrlExpiryDetection(unittest.TestCase):
    def test_epoch_seconds(self):
        info = analyze_url_expiry(f"https://host/stream.m3u8?expires={EPOCH + 3600}")
        self.assertEqual(info["expires_at"], NOW + timedelta(hours=1))
        self.assertEqual(info["source"], "expires")
        self.assertFalse(info["opaque"])

    def test_epoch_milliseconds(self):
        info = analyze_url_expiry(f"https://host/stream.m3u8?exp={(EPOCH + 600) * 1000}")
        self.assertEqual(info["expires_at"], NOW + timedelta(minutes=10))

    def test_iso_timestamp(self):
        info = analyze_url_expiry("https://host/stream.m3u8?expiry=2026-10-20T12:00:00Z")
        self.assertEqual(info["expires_at"], NOW + timedelta(days=1))

    def test_aws_signed_url(self):
        url = (
            "https://bucket/stream.m3u8"
            "?X-Amz-Date=20261019T120000Z&X-Amz-Expires=3600&X-Amz-Signature=abc"
        )
        info = analyze_url_expiry(url)
        self.assertEqual(info["expires_at"], NOW + timedelta(hours=1))
        self.assertEqual(info["source"], "X-Amz-Expires")

    def test_google_signed_url(self):
        url = (
            "https://storage.example/stream.m3u8"
            "?X-Goog-Date=20261019T120000Z&X-Goog-Expires=1800&X-Goog-Signature=abc"
        )
        info = analyze_url_expiry(url)
        self.assertEqual(info["expires_at"], NOW + timedelta(minutes=30))
        self.assertEqual(info["source"], "X-Goog-Expires")

    def test_cloudfront_policy(self):
        policy = {
            "Statement": [
                {
                    "Resource": "https://cdn.example/stream.m3u8",
                    "Condition": {"DateLessThan": {"AWS:EpochTime": EPOCH + 7200}},
                }
            ]
        }
        encoded = base64.b64encode(json.dumps(policy).encode("utf-8")).decode("ascii")
        info = analyze_url_expiry(
            f"https://cdn.example/stream.m3u8?Policy={quote(encoded)}&Signature=x&Key-Pair-Id=y"
        )
        self.assertEqual(info["expires_at"], NOW + timedelta(hours=2))
        self.assertEqual(info["source"], "policy:DateLessThan")

    def test_jwt_token(self):
        header = _b64url(b'{"alg":"HS256","typ":"JWT"}')
        payload = _b64url(json.dumps({"exp": EPOCH + 900}).encode("utf-8"))
        info = analyze_url_expiry(f"https://host/stream.m3u8?token={header}.{payload}.sig")
        self.assertEqual(info["expires_at"], NOW + timedelta(minutes=15))
        self.assertEqual(info["source"], "token:jwt:exp")

    def test_akamai_token(self):
        info = analyze_url_expiry(
            f"https://host/stream.m3u8?hdnts=exp={EPOCH + 1800}~acl=/*~hmac=abc"
        )
        self.assertEqual(info["expires_at"], NOW + timedelta(minutes=30))
        self.assertEqual(info["source"], "hdnts:token:exp")

    def test_relative_duration_with_start(self):
        info = analyze_url_expiry(f"https://host/stream.m3u8?st={EPOCH}&expires_in=600")
        self.assertEqual(info["expires_at"], NOW + timedelta(minutes=10))

    def test_opaque_token_is_marked_unknown(self):
        opaque = "b3BhcXVlLXRva2VuOmNpcGhlcnRleHQ"
        info = analyze_url_expiry(f"https://host/stream.m3u8?token={opaque}")
        self.assertIsNone(info["expires_at"])
        self.assertTrue(info["opaque"])

    def test_plain_url_has_no_expiry(self):
        info = analyze_url_expiry("https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8")
        self.assertIsNone(info["expires_at"])
        self.assertFalse(info["opaque"])

    def test_fields_ready_for_history(self):
        fields = url_expiry_fields(f"https://host/stream.m3u8?expires={EPOCH + 60}")
        self.assertEqual(fields["expiry_source"], "expires")
        self.assertTrue(fields["expires_at"].startswith("2026-10-19T12:01:00"))

    def test_apply_expiry_fields_migrates_old_entry(self):
        entry = {
            "url": f"https://host/stream.m3u8?expires={EPOCH + 60}",
            "timestamp": (NOW - timedelta(hours=2)).isoformat(),
        }
        self.assertTrue(apply_expiry_fields(entry))
        self.assertIn("expires_at", entry)
        self.assertEqual(entry["first_seen"], entry["timestamp"])
        self.assertFalse(apply_expiry_fields(entry))


class TestExpiryFormatting(unittest.TestCase):
    def test_format_remaining(self):
        self.assertEqual(format_remaining(NOW + timedelta(seconds=45), NOW), "45s")
        self.assertEqual(format_remaining(NOW + timedelta(minutes=10), NOW), "10m")
        self.assertEqual(format_remaining(NOW + timedelta(minutes=90), NOW), "1h 30m")
        self.assertEqual(format_remaining(NOW + timedelta(hours=2), NOW), "2h")
        self.assertEqual(format_remaining(NOW + timedelta(days=1, hours=2), NOW), "1d 2h")
        self.assertEqual(format_remaining(NOW - timedelta(seconds=1), NOW), "expired")
        self.assertEqual(format_remaining(None, NOW), "unknown")

    def test_badge_tone(self):
        two_hours = {"expires_at": (NOW + timedelta(hours=2)).isoformat()}
        soon = {"expires_at": (NOW + timedelta(minutes=30)).isoformat()}
        expired = {"expires_at": (NOW - timedelta(minutes=1)).isoformat()}
        self.assertEqual(expiry_badge(two_hours, NOW), ("2h left", "ok"))
        self.assertEqual(expiry_badge(soon, NOW), ("30m left", "soon"))
        self.assertEqual(expiry_badge(expired, NOW), ("Expired", "expired"))

    def test_badge_for_opaque_and_plain_url(self):
        opaque = {"url": "https://host/x.m3u8?token=not-a-readable-token"}
        plain = {"url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"}
        self.assertEqual(expiry_badge(opaque, NOW), ("Unknown", "unknown"))
        self.assertEqual(expiry_badge(plain, NOW), ("No expiry", "none"))

    def test_badge_estimates_opaque_ttl_from_first_seen(self):
        recent = {
            "url": "https://host/x.m3u8?token=opaque",
            "first_seen": (NOW - timedelta(hours=1)).isoformat(),
        }
        old = {
            "url": "https://host/x.m3u8?token=opaque",
            "first_seen": (NOW - timedelta(hours=25)).isoformat(),
        }
        self.assertEqual(expiry_badge(recent, NOW), ("~23h left", "estimate"))
        self.assertEqual(expiry_badge(old, NOW), ("~Expired", "expired"))

    def test_estimate_uses_local_naive_history_timestamp(self):
        local_now = NOW.astimezone()
        entry = {
            "url": "https://host/x.m3u8?token=opaque",
            "first_seen": (local_now - timedelta(hours=1)).replace(tzinfo=None).isoformat(),
        }
        self.assertEqual(expiry_badge(entry, local_now), ("~23h left", "estimate"))

    def test_tooltip_for_opaque_estimate(self):
        entry = {
            "url": "https://host/x.m3u8?token=opaque",
            "first_seen": (NOW - timedelta(hours=1)).isoformat(),
        }
        tooltip = expiry_tooltip(entry)
        self.assertIn("Estimated expiry:", tooltip)
        self.assertIn("24h TTL", tooltip)

    def test_tooltip_contains_absolute_time_and_source(self):
        entry = {
            "url": "https://host/x.m3u8",
            "expires_at": (NOW + timedelta(hours=1)).isoformat(),
            "expiry_source": "exp",
        }
        tooltip = expiry_tooltip(entry)
        self.assertIn("Expires:", tooltip)
        self.assertIn("Source: exp", tooltip)


if __name__ == "__main__":
    unittest.main()
