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
    'control_bg': '#0f0f0f',      # Control panel background
    'video_bg': '#000000',        # Video area
    'button_bg': '#0f0f0f',       # Button background (transparent-ish)
    'button_hover': '#2d2d2d',    # Button hover
    'button_active': '#3d3d3d',   # Button active
    'text': '#ffffff',            # White text
    'text_gray': '#aaaaaa',       # Gray text
    'border': '#000000',          # Border color
    'seekbar': '#ff004d',         # Red/Pink seekbar (Reference match)
    'seekbar_bg': '#3d3d3d',      # Seekbar background
    'entry_bg': '#2d2d2d',        # Entry field background
    'entry_fg': '#ffffff',        # Entry field text
    'record_active': '#ff4444',   # Red for recording
    'header_bg': '#1a1a1a',       # Header background
    'list_bg': '#0f0f0f',         # Listbox background
    'accent': '#ff004d',          # Accent color
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
