"""Deteksi masa berlaku link streaming langsung dari URL.

Banyak penyedia menaruh waktu kedaluwarsa di query string (``expires=``),
di dalam JWT (``token=``), atau di policy CDN (CloudFront/Akamai). Token
yang sepenuhnya opaque - misalnya ``iv:ciphertext`` terenkripsi - tidak
bisa dibaca tanpa kunci server, sehingga hasilnya ditandai ``opaque`` dan
UI menampilkan "Expiry unknown" alih-alih menebak.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_EPOCH_MIN = 946684800.0    # 2000-01-01T00:00:00Z
_EPOCH_MAX = 4102444800.0   # 2100-01-01T00:00:00Z

# Token opaque tidak menyimpan expiry yang bisa dibaca. Untuk link Patreaction,
# masa aktif biasanya 24 jam; nilai ini dipakai sebagai estimasi berlabel "~".
DEFAULT_OPAQUE_TOKEN_TTL_SECONDS = 24 * 60 * 60

# Nama parameter yang umum dipakai untuk waktu kedaluwarsa absolut.
_EXPIRY_PARAMS = (
    "expires",
    "expire",
    "expiry",
    "exp",
    "expires_at",
    "expiresat",
    "expiration",
    "expiration_date",
    "valid_until",
    "validuntil",
    "valid_to",
    "until",
    "e",
)

# Parameter yang biasanya berisi token opaque atau JWT.
_TOKEN_PARAMS = ("hdnts", "hdntl", "hdnta", "hdntc", "__token__", "token", "jwt")

# Parameter awal berlaku, dipakai untuk token berdurasi relatif.
_START_PARAMS = ("st", "start", "starts", "start_time", "starttime", "issued_at", "iat")

_RELATIVE_PARAMS = ("expires_in", "expiresin", "ttl", "lifetime")


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Ubah epoch (detik/ms/us/ns) atau string ISO menjadi datetime UTC."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if value is None:
        return None

    text = str(value).strip().strip("\"'")
    if not text:
        return None

    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        try:
            number = float(text)
        except ValueError:
            return None
        # Normalisasi satuan yang lebih kecil dari detik.
        if number > 1e17:
            number /= 1e9
        elif number > 1e14:
            number /= 1e6
        elif number > 1e11:
            number /= 1e3
        if not (_EPOCH_MIN <= number <= _EPOCH_MAX):
            return None
        return datetime.fromtimestamp(number, tz=timezone.utc)

    iso = text
    if iso.endswith(("Z", "z")):
        iso = iso[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _decode_base64(value: str) -> Optional[bytes]:
    text = value.strip()
    if not text:
        return None
    text += "=" * (-len(text) % 4)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return decoder(text)
        except (binascii.Error, ValueError):
            continue
    return None


def _expiry_from_jwt(token: str) -> Optional[datetime]:
    parts = token.split(".")
    if len(parts) < 3:
        return None
    payload = _decode_base64(parts[1])
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("exp", "expires", "expiry", "expires_at"):
        if key in data:
            parsed = _coerce_datetime(data[key])
            if parsed is not None:
                return parsed
    return None


def _expiry_from_policy(value: str) -> Optional[datetime]:
    """Ambil ``DateLessThan`` dari CloudFront custom policy (base64 JSON)."""
    payload = _decode_base64(value)
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    statements = data.get("Statement")
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list):
        return None

    found = []
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        condition = statement.get("Condition") or {}
        if not isinstance(condition, dict):
            continue
        for key in ("DateLessThan", "DateLessThanEquals"):
            item = condition.get(key)
            if isinstance(item, dict):
                raw_time = (
                    item.get("AWS:EpochTime")
                    or item.get("epochTime")
                    or next(iter(item.values()), None)
                )
            else:
                raw_time = item
            parsed = _coerce_datetime(raw_time)
            if parsed is not None:
                found.append(parsed)
    return min(found) if found else None


def _expiry_from_token(value: str) -> tuple[Optional[datetime], str]:
    """Coba baca expiry dari JWT, token Akamai, atau payload base64 JSON."""
    parsed = _expiry_from_jwt(value)
    if parsed is not None:
        return parsed, "jwt:exp"

    text = value.strip()
    match = re.search(r"(?:^|[~&;])exp=(\d{9,19})", text)
    if match:
        parsed = _coerce_datetime(match.group(1))
        if parsed is not None:
            return parsed, "token:exp"

    payload = _decode_base64(text)
    if payload:
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        if isinstance(data, dict):
            for key in ("exp", "expires", "expiry", "expires_at"):
                if key in data:
                    parsed = _coerce_datetime(data[key])
                    if parsed is not None:
                        return parsed, f"token:{key}"

        decoded = payload.decode("utf-8", "ignore")
        match = re.search(r'"(?:exp|expires|expiry)"\s*:\s*"?(\d{9,19})', decoded)
        if not match:
            match = re.search(r"(?:^|[~&;])exp=(\d{9,19})", decoded)
        if match:
            parsed = _coerce_datetime(match.group(1))
            if parsed is not None:
                return parsed, "token:exp"

    return None, ""


def _parse_query(raw: str) -> Dict[str, str]:
    """Parser query sederhana yang mempertahankan ``+`` pada base64.

    ``urllib.parse.parse_qs`` mengubah ``+`` menjadi spasi. Token base64
    kadang tidak di-encode, jadi parsing manual lebih aman di sini.
    """
    from urllib.parse import unquote

    values: Dict[str, str] = {}
    for chunk in raw.split("&"):
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        key = unquote(key).strip().lower()
        if key:
            values[key] = unquote(value)
    return values


def _relative_expiry(date_value: Optional[str], seconds_value: Optional[str]) -> Optional[datetime]:
    start = _coerce_datetime(date_value)
    if start is None or seconds_value is None:
        return None
    try:
        seconds = float(seconds_value)
    except (TypeError, ValueError):
        return None
    if seconds < 0 or seconds > 10 * 365 * 24 * 3600:
        return None
    return start + timedelta(seconds=seconds)


def analyze_url_expiry(url: str) -> Dict[str, Any]:
    """Analisis URL dan kembalikan metadata kedaluwarsa.

    Hasil berupa dict dengan kunci:
    - ``expires_at``: datetime UTC atau ``None``
    - ``source``: asal informasi (mis. ``expires``, ``jwt:exp``)
    - ``opaque``: ``True`` bila URL memakai token yang tidak bisa dibaca
    """
    result: Dict[str, Any] = {"expires_at": None, "source": "", "opaque": False}
    if not url:
        return result

    try:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
    except ValueError:
        return result

    raw_query = "&".join(part for part in (parts.query, parts.fragment) if part)
    if not raw_query:
        return result
    query = _parse_query(raw_query)

    # 1. AWS Signature V4 / GCS signed URL: durasi relatif + tanggal mulai.
    for seconds_key, date_key, label in (
        ("x-amz-expires", "x-amz-date", "X-Amz-Expires"),
        ("x-goog-expires", "x-goog-date", "X-Goog-Expires"),
    ):
        parsed = _relative_expiry(query.get(date_key), query.get(seconds_key))
        if parsed is not None:
            return {"expires_at": parsed, "source": label, "opaque": False}

    # 2. CloudFront custom policy.
    for key in ("policy", "cloudfront-policy"):
        if key in query:
            parsed = _expiry_from_policy(query[key])
            if parsed is not None:
                return {"expires_at": parsed, "source": f"{key}:DateLessThan", "opaque": False}

    # 3. Parameter kedaluwarsa absolut yang umum.
    for name in _EXPIRY_PARAMS:
        if name in query:
            parsed = _coerce_datetime(query[name])
            if parsed is not None:
                return {"expires_at": parsed, "source": name, "opaque": False}

    # 4. Durasi relatif dengan waktu mulai yang eksplisit.
    start = None
    start_name = ""
    for name in _START_PARAMS:
        if name in query:
            start = _coerce_datetime(query[name])
            if start is not None:
                start_name = name
                break
    if start is not None:
        for name in _RELATIVE_PARAMS:
            if name not in query:
                continue
            try:
                seconds = float(query[name])
            except (TypeError, ValueError):
                continue
            if 0 <= seconds <= 10 * 365 * 24 * 3600:
                return {
                    "expires_at": start + timedelta(seconds=seconds),
                    "source": f"{name} from {start_name}",
                    "opaque": False,
                }

    # 5. Token: JWT/Akamai/base64 JSON. Bila tidak terbaca, token dianggap opaque.
    for name in _TOKEN_PARAMS:
        value = query.get(name)
        if not value:
            continue
        parsed, source = _expiry_from_token(value)
        if parsed is not None:
            return {"expires_at": parsed, "source": f"{name}:{source}", "opaque": False}
        result["opaque"] = True

    return result


def url_expiry_fields(url: str) -> Dict[str, str]:
    """Metadata siap simpan untuk history.json (kosong bila tidak terdeteksi)."""
    info = analyze_url_expiry(url)
    expires_at = info.get("expires_at")
    if not isinstance(expires_at, datetime):
        return {}
    return {
        "expires_at": expires_at.isoformat(),
        "expiry_source": str(info.get("source") or ""),
    }


def apply_expiry_fields(entry: Dict[str, Any]) -> bool:
    """Lengkapi entry history lama dengan metadata expiry dan ``first_seen``."""
    if not isinstance(entry, dict):
        return False

    changed = False
    if not entry.get("first_seen"):
        timestamp = entry.get("timestamp")
        if timestamp:
            entry["first_seen"] = timestamp
            changed = True

    if not entry.get("expires_at"):
        fields = url_expiry_fields(str(entry.get("url") or ""))
        if fields:
            entry.update(fields)
            changed = True
    return changed


def _now(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    coerced = _coerce_datetime(now)
    return coerced or datetime.now(timezone.utc)


def remaining_seconds(expires_at: Any, now: Optional[datetime] = None) -> Optional[float]:
    parsed = _coerce_datetime(expires_at)
    if parsed is None:
        return None
    return (parsed - _now(now)).total_seconds()


def _format_seconds(seconds: float) -> str:
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    minutes = total // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = total // 3600
    minutes = (total % 3600) // 60
    if hours < 24:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    days = hours // 24
    hours = hours % 24
    return f"{days}d {hours}h" if hours else f"{days}d"


def format_remaining(expires_at: Any, now: Optional[datetime] = None) -> str:
    seconds = remaining_seconds(expires_at, now)
    if seconds is None:
        return "unknown"
    if seconds <= 0:
        return "expired"
    return _format_seconds(seconds)


def _coerce_local_datetime(value: Any) -> Optional[datetime]:
    """Parse timestamp history (naive = waktu lokal) menjadi datetime UTC."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.astimezone().astimezone(timezone.utc)
        return value.astimezone(timezone.utc)
    if value is None:
        return None

    text = str(value).strip().strip("\"'")
    if not text:
        return None
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return _coerce_datetime(text)

    iso = text
    if iso.endswith(("Z", "z")):
        iso = iso[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone().astimezone(timezone.utc)
    return parsed.astimezone(timezone.utc)


def _entry_start_time(entry: Dict[str, Any]) -> Optional[datetime]:
    return _coerce_local_datetime(entry.get("first_seen") or entry.get("timestamp"))


def _opaque_estimate(entry: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Optional[datetime]:
    """Estimasi expiry untuk token opaque: first_seen + 24 jam."""
    if info is None:
        info = analyze_url_expiry(str(entry.get("url") or ""))
    if not info.get("opaque"):
        return None
    started = _entry_start_time(entry)
    if started is None:
        return None
    return started + timedelta(seconds=DEFAULT_OPAQUE_TOKEN_TTL_SECONDS)


def expiry_badge(entry: Dict[str, Any], now: Optional[datetime] = None) -> tuple[str, str]:
    """Teks badge + tone warna untuk satu entry history."""
    if not isinstance(entry, dict):
        return "No expiry", "none"

    seconds = remaining_seconds(entry.get("expires_at"), now)
    if seconds is not None:
        if seconds <= 0:
            return "Expired", "expired"
        tone = "soon" if seconds <= 3600 else "ok"
        return f"{_format_seconds(seconds)} left", tone

    info = analyze_url_expiry(str(entry.get("url") or ""))
    if info.get("opaque"):
        estimated = _opaque_estimate(entry, info)
        if estimated is not None:
            estimated_seconds = remaining_seconds(estimated, now)
            if estimated_seconds is not None:
                if estimated_seconds <= 0:
                    return "~Expired", "expired"
                return f"~{_format_seconds(estimated_seconds)} left", "estimate"
        return "Unknown", "unknown"
    return "No expiry", "none"


def expiry_tooltip(entry: Dict[str, Any]) -> str:
    """Tooltip berisi waktu absolut dan sumber informasi kedaluwarsa."""
    if not isinstance(entry, dict):
        return ""

    parsed = _coerce_datetime(entry.get("expires_at"))
    if parsed is not None:
        source = str(entry.get("expiry_source") or "")
        if not source:
            source = str(analyze_url_expiry(str(entry.get("url") or "")).get("source") or "")
        local_time = parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        tooltip = f"Expires: {local_time}"
        if source:
            tooltip += f"\nSource: {source}"
        return tooltip

    info = analyze_url_expiry(str(entry.get("url") or ""))
    if info.get("opaque"):
        estimated = _opaque_estimate(entry, info)
        if estimated is not None:
            local_time = estimated.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            hours = DEFAULT_OPAQUE_TOKEN_TTL_SECONDS // 3600
            return (
                f"Estimated expiry: {local_time}\n"
                f"Token is opaque; estimate uses a {hours}h TTL from when the link was added."
            )
        return "Expiry unknown: token is opaque, only the server can validate its lifetime."
    return "No expiry information found in the URL."
