import os
import sys

# -------------------------------------------------
#  MPV detection & PATH setup
# -------------------------------------------------
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MPV_PATHS = [
    BASE_DIR,                                # folder EXE (PyInstaller) atau script asli
    os.path.join(BASE_DIR, "mpv"),           # jika pengguna menaruh DLL di subfolder "mpv"
    r"C:\mpv",
    r"C:\Program Files\mpv",
    r"C:\Program Files (x86)\mpv",
]

# -------------------------------------------------
#  MPC-HC Style Colors (Dark Theme)
# -------------------------------------------------
COLORS = {
    'bg': '#0f0f0f',              # Deep black background
    'menu_bg': '#0f0f0f',         # Menu bar background
    'toolbar_bg': '#0f0f0f',      # Toolbar background
    'control_bg': '#0a0a0a',      # Control panel background (very dark for overlay effect)
    'video_bg': '#000000',        # Video area
    'button_bg': '#2d2d2d',       # Button background (visible on transparent)
    'button_hover': '#3d3d3d',    # Button hover
    'button_active': '#4d4d4d',   # Button active
    'text': '#ffffff',            # White text
    'text_gray': '#aaaaaa',       # Gray text
    'border': '#000000',          # Border color
    'seekbar': '#007ACC',         # Seekbar (Reference match)
    'seekbar_bg': '#3d3d3d',      # Seekbar background
    'entry_bg': '#2d2d2d',        # Entry field background
    'entry_fg': '#ffffff',        # Entry field text
    'record_active': '#ff4444',   # Red for recording
    'header_bg': '#1a1a1a',       # Header background
    'list_bg': '#0f0f0f',         # Listbox background
    'accent': '#007ACC',          # Accent color
    'load_btn_bg': '#007ACC',     # Load Stream Button Background
    'load_btn_fg': '#ffffff',     # Load Stream Button Text
    'load_btn_hover': '#0098FF',  # Load Stream Button Hover
    'load_btn_active': '#005FA3', # Load Stream Button Active
    'speed_fg': '#007ACC',        # Speed indicator text color
    'status_ready_fg': '#aaaaaa', # Status Ready text color
    'status_loading_fg': '#ffffff', # Status Loading text color
    'status_playing_fg': '#007ACC', # Status Playing text color (blue)
    'status_paused_fg': '#FFA500',  # Status Paused text color (orange)
    'status_stopped_fg': '#FF0000', # Status Stopped text color (red)
}

# -------------------------------------------------
#  User Agents
# -------------------------------------------------
USER_AGENTS = {
    "Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
}

# -------------------------------------------------
#  Cache Tuning Defaults
# -------------------------------------------------
CACHE_SETTINGS = {
    "max_bytes": 100,       # MB
    "max_back_bytes": 100,   # MB
    "pause_refresh_threshold": 300, # Seconds (5 minutes)
}
