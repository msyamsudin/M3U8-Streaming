import os
import sys
from .config import MPV_PATHS

# -------------------------------------------------
#  Setup PATH for libmpv before importing mpv
# -------------------------------------------------
dll_found = False
for p in MPV_PATHS:
    dll = os.path.join(p, "libmpv-2.dll")
    if os.path.exists(dll):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        dll_found = True
        break

if not dll_found:
    print("Warning: libmpv-2.dll not found in expected paths. 'import mpv' might fail.")

import mpv

class MpvPlayer:
    def __init__(self, wid=None):
        self.mpv = None
        self.wid = wid
        self._init_mpv()
        
    def _init_mpv(self):
        try:
            self.mpv = mpv.MPV(
                wid=str(self.wid) if self.wid else None,
                input_default_bindings=True,
                input_vo_keyboard=True,
                osc=True,
                keep_open=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MPV: {e}")

    def play(self, url, headers=None, user_agent=None):
        if not self.mpv: return
        
        options = {}
        if user_agent:
            options['user_agent'] = user_agent
        if headers:
            # Format headers as "Key: Value,Key2: Value2"
            header_str = ",".join([f"{k}: {v}" for k, v in headers.items()])
            options['http_header_fields'] = header_str
            
        # Apply options
        for k, v in options.items():
            setattr(self.mpv, k, v)
            
        self.mpv.play(url)

    def pause(self):
        if self.mpv:
            self.mpv.pause = not self.mpv.pause
            return self.mpv.pause
        return False

    def stop(self):
        if self.mpv:
            self.mpv.stop()

    def seek(self, value, mode="relative"):
        if self.mpv:
            self.mpv.command("seek", value, mode)

    def set_volume(self, value):
        if self.mpv:
            self.mpv.volume = value

    def get_time_pos(self):
        return self.mpv.time_pos if self.mpv else None

    def get_duration(self):
        return self.mpv.duration if self.mpv else None

    def set_wid(self, wid):
        if self.mpv:
            self.mpv.wid = str(wid)

    def terminate(self):
        if self.mpv:
            self.mpv.terminate()

    # -------------------------------------------------
    #  New Features
    # -------------------------------------------------
    def start_recording(self, filepath):
        """Start recording the current stream to a file."""
        if self.mpv:
            # Use stream-record property
            self.mpv.stream_record = filepath

    def stop_recording(self):
        """Stop recording."""
        if self.mpv:
            self.mpv.stream_record = ""

    def get_video_tracks(self):
        """Get list of available video tracks (quality)."""
        if not self.mpv: return []
        return self.mpv.track_list

    def set_video_track(self, track_id):
        """Set video track by ID."""
        if self.mpv:
            self.mpv.vid = track_id
    
    def get_demuxer_cache_state(self):
        """Get demuxer cache state including network speed."""
        if self.mpv:
            try:
                return self.mpv.demuxer_cache_state
            except:
                return None
        return None

    def get_buffered_time(self):
        """Get the buffered time position."""
        if self.mpv:
            try:
                # demuxer-cache-time returns the timestamp of the last buffered packet
                return self.mpv.demuxer_cache_time
            except:
                return None
        return None
        
    def is_seekable(self):
        """Check if the current stream is seekable."""
        if self.mpv:
            try:
                return self.mpv.seekable
            except:
                return False
        return False
