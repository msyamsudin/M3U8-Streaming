# Implementation Plan - M3U8 Streaming Player Enhancement

This plan outlines the steps to refactor the existing monolithic `app.py` into a modular structure and implement the requested features: Recording, Quality Selection, History, Drag & Drop, and UI improvements.

## User Review Required
> [!IMPORTANT]
> **Refactoring**: The application will be restructured into a `src/` directory. The main entry point will change from `app.py` to `main.py`.
> **Dependencies**: New features might require additional Python packages (e.g., `tkinterdnd2` for Drag & Drop).
> **Recording**: Recording will rely on MPV's internal dumping capabilities.

## Proposed Changes

### 1. Structural Refactoring
Move code from `app.py` into a modular `src/` package.

#### [NEW] [src/config.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/config.py)
- Store constants: `COLORS`, `MPV_PATHS`, `USER_AGENTS`.
- Default settings.

#### [NEW] [src/player_core.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/player_core.py)
- Wrapper class for `mpv.MPV`.
- Handle DLL loading and initialization.
- Methods for Play, Pause, Stop, Seek, Volume.
- **New**: Methods for `start_recording`, `stop_recording`, `get_quality_list`, `set_quality`.

#### [NEW] [src/ui_components.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/ui_components.py)
- Reusable UI widgets (e.g., styled buttons, panels).
- **New**: `HistoryPanel` class.

#### [NEW] [src/app_gui.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/app_gui.py)
- Main GUI class (formerly `M3U8StreamingPlayer`).
- Integrate `HistoryPanel`.
- Integrate `QualitySelector`.
- **New**: Drag & Drop handling.

#### [NEW] [src/utils.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/utils.py)
- Helper functions (time formatting, file operations).
- History management (load/save JSON).

#### [NEW] [main.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/main.py)
- New entry point.
- Checks dependencies and launches the app.

#### [DELETE] [app.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/app.py)
- Remove after successful refactor.

### 2. Feature Implementation

#### Recording / Downloading
- Add a "Record" button to the toolbar.
- Use MPV's `stream-record` property or `dump-stream` command.
- Save files to a `downloads/` folder with a timestamp.

#### Quality Selection
- Add a Combobox in the control panel.
- Query MPV for `track-list` (video).
- Allow switching video tracks on the fly.

#### History & Favorites
- Create `history.json` to store played URLs.
- Add a collapsible side panel (right side) to show history.
- Click to play from history.

#### UI/UX Improvements
- **Icons**: Use Unicode symbols with better fonts/sizes for now (to avoid asset complexity), or generate simple PNG icons if needed.
- **Always on Top**: Add a checkbox or menu item.
- **Loading**: Add a status label update for "Buffering...".

#### Documentation
- Create `README.md` with installation and usage instructions.

## Verification Plan

### Automated Tests
- None (UI application).

### Manual Verification
1.  **Launch**: Run `python main.py` and ensure it starts.
2.  **Playback**: Load an M3U8 URL and verify playback.
3.  **Refactor Check**: Ensure all buttons (Play, Pause, Seek, Volume) work as before.
4.  **Recording**: Click Record, wait 10s, Stop. Check if file exists in `downloads/` and is playable.
5.  **Quality**: Load a multi-bitrate stream, change quality, verify stream reloads/changes.
6.  **History**: Play a URL, close app, reopen. Check if URL is in history.
7.  **UI**: Test "Always on Top" and Fullscreen.
