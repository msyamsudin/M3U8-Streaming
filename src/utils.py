import json
import os
from datetime import datetime

HISTORY_FILE = "history.json"

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

def load_history():
    """Load playback history from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(url, name=None):
    """Save a URL to history, avoiding duplicates at the top."""
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
    
    # Remove existing entry with same URL if exists
    history = [h for h in history if h['url'] != url]
    
    # Add to top
    history.insert(0, entry)
    
    # Limit to 50 entries
    history = history[:50]
    
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def update_history_progress(url, position):
    """Update the last playback position for a URL."""
    history = load_history()
    found = False
    for item in history:
        if item['url'] == url:
            item['last_position'] = position
            item['timestamp'] = datetime.now().isoformat()
            found = True
            break
    
    if found:
        write_history(history)

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
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def get_unique_filename(base_path, filename):
    """Get a unique filename by appending a counter if file exists."""
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(base_path, new_filename)):
        new_filename = f"{name}_{counter}{ext}"
        counter += 1
    return new_filename
