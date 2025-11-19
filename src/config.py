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
    'bg': '#1a1a1a',              # Dark background
    'menu_bg': '#2d2d2d',         # Menu bar background (dark gray)
    'toolbar_bg': '#2d2d2d',      # Toolbar background (dark gray)
    'control_bg': '#1a1a1a',      # Control panel background (very dark)
    'video_bg': '#000000',        # Video area (black)
    'button_bg': '#3d3d3d',       # Button background (medium dark gray)
    'button_hover': '#4d4d4d',    # Button hover (lighter gray)
    'button_active': '#555555',   # Button active
    'text': '#e0e0e0',            # Light gray text
    'text_gray': '#999999',       # Gray text
    'border': '#000000',          # Border color (black)
    'seekbar': '#0078d7',         # Blue seekbar
    'seekbar_bg': '#3d3d3d',      # Seekbar background (dark gray)
    'entry_bg': '#2d2d2d',        # Entry field background
    'entry_fg': '#e0e0e0',        # Entry field text
    'record_active': '#ff4444',   # Red for recording
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
