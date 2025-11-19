# Fix libmpv Detection

The user is experiencing an `OSError` because `python-mpv` attempts to load `libmpv-2.dll` immediately upon import, but the directory containing the DLL hasn't been added to the system `PATH` yet. The current implementation attempts to add it in the `__init__` method of the `MpvPlayer` class, which is too late.

## User Review Required
> [!IMPORTANT]
> This change modifies the module-level execution order in `src/player_core.py` to modify the `PATH` environment variable before importing `mpv`.

## Proposed Changes

### Core Logic
#### [MODIFY] [player_core.py](file:///d:/04_SOFTWARE/Script/06_GITHUB/M3U8-Streaming/src/player_core.py)
- Move the DLL detection and `PATH` update logic from `_init_mpv` to the module level, before `import mpv`.
- Ensure `import mpv` happens *after* `os.environ["PATH"]` has been updated.

## Verification Plan

### Manual Verification
- Run `main.py` and verify that the application starts without the `OSError`.
