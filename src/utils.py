import json
import os
from datetime import datetime
import time

HISTORY_FILE = "history.json"
SETTINGS_FILE = "settings.json"


def _write_json_atomic(path: str, data) -> None:
    """Write JSON atomically: write to a temp file, then replace the target.

    ``os.replace`` is atomic on Windows, so a crash mid-write can never leave
    a truncated/corrupt destination file.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def format_time(secs):
    """Format seconds into HH:MM:SS string."""
    if secs is None:
        return "00:00:00"
    try:
        secs = int(secs)
    except:
        return "00:00:00"
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_clock(seconds):
    """Format seconds as MM:SS or HH:MM:SS (jam dihilangkan bila nol)."""
    if seconds is None or seconds < 0:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def load_history():
    """Load playback history from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        # Jangan diam-diam menimpa file korup: backup dulu agar data lama
        # tidak hilang permanen saat penulisan berikutnya.
        print(f"[warn] {HISTORY_FILE} corrupt ({exc}); backing up and starting fresh")
        try:
            os.replace(HISTORY_FILE, f"{HISTORY_FILE}.bak-{int(time.time())}")
        except OSError:
            pass
        return []

def save_history(url, name=None, meta=None):
    """Save a URL to history, avoiding duplicates at the top.

    ``meta`` (optional) carries per-entry request metadata (referer,
    user_agent, headers) so it can be restored later.
    """
    history = load_history()
    
    # Check for existing position
    last_pos = 0
    for h in history:
        if h['url'] == url:
            last_pos = h.get('last_position', 0)
            break
            
    # Create entry
    entry = {
        "url": url,
        "name": name or url,
        "timestamp": datetime.now().isoformat(),
        "last_position": last_pos
    }
    if meta:
        entry["referer"] = meta.get("referer", "")
        entry["user_agent"] = meta.get("user_agent", "")
        entry["headers"] = meta.get("headers", {})
    
    # Remove existing entry with same URL if exists
    history = [h for h in history if h['url'] != url]
    
    # Add to top
    history.insert(0, entry)
    
    # Limit to 50 entries
    history = history[:50]
    
    try:
        _write_json_atomic(HISTORY_FILE, history)
    except Exception as e:
        print(f"Error saving history: {e}")

def get_history_item(url):
    """Get history item by URL."""
    history = load_history()
    for item in history:
        if item['url'] == url:
            return item
    return None

def write_history(history):
    """Write the entire history list to file."""
    try:
        _write_json_atomic(HISTORY_FILE, history)
    except Exception as e:
        print(f"Error saving history: {e}")

def load_settings():
    """Load settings from JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[warn] {SETTINGS_FILE} corrupt ({exc}); backing up and using defaults")
        try:
            os.replace(SETTINGS_FILE, f"{SETTINGS_FILE}.bak-{int(time.time())}")
        except OSError:
            pass
        return {}

def save_settings(settings):
    """Save settings to JSON file."""
    try:
        _write_json_atomic(SETTINGS_FILE, settings)
    except Exception as e:
        print(f"Error saving settings: {e}")
