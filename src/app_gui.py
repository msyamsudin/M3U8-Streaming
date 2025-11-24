import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog
import threading
import os
import requests
from datetime import datetime

from .config import COLORS, USER_AGENTS
from .player_core import MpvPlayer
from .ui_components import StyledButton, HistoryPanel, LoadingSpinner
from .utils import format_time, load_history, save_history, get_unique_filename, write_history, update_history_progress, get_history_item

class M3U8StreamingPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 Player")
        self.root.geometry("1000x600")
        self.root.configure(bg=COLORS['bg'])
        
        # State
        self.player = None
        self.is_playing = False
        self.is_seeking = False
        self.is_fullscreen = False
        self.is_recording = False
        self.show_config = True
        self.show_history = False
        self.current_url = ""
        self.previous_volume = 100
        self.is_closing = False
        
        # Fullscreen state
        self.normal_geometry = None
        self.fullscreen_window = None
        self.fullscreen_video_frame = None
        self.hide_timer = None
        self.click_timer = None
        self.controls_visible = True
        
        # Drag state
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

        # Initialize UI
        self.setup_styles()
        self.setup_menu()
        self.setup_ui()
        self.setup_bindings()
        
        # Initialize Player
        try:
            self.player = MpvPlayer(wid=self.video_canvas.winfo_id())
        except Exception as e:
            messagebox.showerror("Error", str(e))

        # Bind MPV Mouse Events
        if self.player and self.player.mpv:
            @self.player.mpv.key_binding('MOUSE_BTN0')
            def on_mpv_click(state=None, name=None, char=None):
                self.root.after(0, self.handle_click)
                
            @self.player.mpv.key_binding('MOUSE_BTN0_DBL')
            def on_mpv_dbl_click(state=None, name=None, char=None):
                self.root.after(0, self.handle_double_click)
            
        # Start periodic updates
        self.update_player_info()
        
        # Load History
        self.refresh_history()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('MPC.Horizontal.TScale',
                       background=COLORS['toolbar_bg'],
                       troughcolor=COLORS['seekbar_bg'],
                       borderwidth=0)

        # Combobox Style
        style.map('TCombobox', fieldbackground=[('readonly', COLORS['entry_bg'])],
                              selectbackground=[('readonly', COLORS['button_active']), ('!readonly', COLORS['button_active'])],
                              selectforeground=[('readonly', COLORS['text']), ('!readonly', COLORS['text'])],
                              background=[('readonly', COLORS['entry_bg'])],
                              foreground=[('readonly', COLORS['entry_fg'])])
        
        style.configure('TCombobox', 
                       fieldbackground=COLORS['entry_bg'],
                       background=COLORS['button_bg'],
                       foreground=COLORS['entry_fg'],
                       arrowcolor=COLORS['text'],
                       darkcolor=COLORS['bg'],
                       lightcolor=COLORS['bg'],
                       bordercolor=COLORS['border'])

        # Combobox Popdown Styling
        self.root.option_add('*TCombobox*Listbox.background', COLORS['entry_bg'])
        self.root.option_add('*TCombobox*Listbox.foreground', COLORS['entry_fg'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', COLORS['button_active'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', COLORS['text'])
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 9))

        # Global Selection Styling
        self.root.option_add('*selectBackground', COLORS['button_active'])
        self.root.option_add('*selectForeground', COLORS['text'])

    def setup_bindings(self):
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<F>", lambda e: self.toggle_fullscreen())
        self.root.bind("<h>", lambda e: self.toggle_history())
        self.root.bind("<H>", lambda e: self.toggle_history())
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.root.bind("<Right>", lambda e: self.skip(10))
        self.root.bind("<Left>", lambda e: self.skip(-10))
        self.root.bind("<space>", lambda e: self.toggle_play_pause())
        self.root.bind("<Control-o>", lambda e: self.show_open_dialog())
        self.root.bind("<Control-O>", lambda e: self.show_open_dialog())
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Video Canvas Bindings
        self.video_canvas.bind("<Button-1>", self.start_drag)
        self.video_canvas.bind("<B1-Motion>", self.do_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.video_canvas.bind("<Double-Button-1>", lambda e: self.handle_double_click())

    def setup_menu(self):
        # Custom Menu Bar Container
        self.menu_bar = tk.Frame(self.root, bg=COLORS['menu_bg'])
        self.menu_bar.pack(side=tk.TOP, fill=tk.X)
        
        # Left: Menu Buttons
        self.menu_left = tk.Frame(self.menu_bar, bg=COLORS['menu_bg'])
        self.menu_left.pack(side=tk.LEFT)
        
        # File Menu
        self.file_btn = tk.Menubutton(self.menu_left, text="File", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                     activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                     bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.file_btn.pack(side=tk.LEFT, padx=2)
        
        file_menu = Menu(self.file_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        file_menu.add_command(label="Open URL... (Ctrl+O)", command=self.show_open_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.file_btn.config(menu=file_menu)
        
        # View Menu
        self.view_btn = tk.Menubutton(self.menu_left, text="View", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                     activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                     bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.view_btn.pack(side=tk.LEFT, padx=2)
        
        view_menu = Menu(self.view_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        view_menu.add_command(label="Fullscreen (F)", command=self.toggle_fullscreen)
        self.always_on_top_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top)
        self.view_btn.config(menu=view_menu)

        # History Menu
        self.history_btn = tk.Menubutton(self.menu_left, text="History", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                        activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                        bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.history_btn.pack(side=tk.LEFT, padx=2)
        
        history_menu = Menu(self.history_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        history_menu.add_checkbutton(label="Show History (H)", command=self.toggle_history)
        history_menu.add_separator()
        history_menu.add_command(label="Clear All History", command=self.clear_history)
        self.history_btn.config(menu=history_menu)
        
        # Right: Status Indicators
        self.menu_right = tk.Frame(self.menu_bar, bg=COLORS['menu_bg'])
        self.menu_right.pack(side=tk.RIGHT, padx=10)
        
        # Speed Label (Now first/left)
        self.speed_label = tk.Label(self.menu_right, text="", bg=COLORS['menu_bg'], 
                                   fg='#00FF00', font=('Consolas', 9, 'bold'))
        self.speed_label.pack(side=tk.LEFT, padx=(0, 5))

        # Separator
        tk.Label(self.menu_right, text="|", bg=COLORS['menu_bg'], fg=COLORS['text_gray'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

        # Status Label (Now second/right)
        self.status_label = tk.Label(self.menu_right, text="Ready", bg=COLORS['menu_bg'], fg=COLORS['text_gray'], font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT)

    def setup_ui(self):
        # Main container (Horizontal for History Panel)
        self.main_container = tk.Frame(self.root, bg=COLORS['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Left side (Player)
        self.player_area = tk.Frame(self.main_container, bg=COLORS['bg'])
        self.player_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)



        # Config Panel
        self.setup_config_panel()

        # Video Area
        self.video_frame = tk.Frame(self.player_area, bg=COLORS['video_bg'], relief=tk.SUNKEN, bd=2)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        self.video_canvas = tk.Frame(self.video_frame, bg=COLORS['video_bg'])
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Loading Spinner (Overlay)
        self.spinner = LoadingSpinner(self.video_frame, size=60, color='#00FF00', bg_color=COLORS['video_bg'])
        
        # Control Panel
        self.setup_control_panel()

        # Right side (History) - Initially hidden
        self.history_panel = HistoryPanel(self.main_container, self.load_from_history, 
                                        self.delete_history_item, self.clear_history)

    def setup_config_panel(self):
        self.config_panel = tk.Frame(self.player_area, bg=COLORS['bg'], relief=tk.GROOVE, bd=2)
        self.config_panel.pack(fill=tk.X, padx=4, pady=4)
        
        inner = tk.Frame(self.config_panel, bg=COLORS['bg'])
        inner.pack(fill=tk.BOTH, padx=10, pady=10)
        
        # Grid layout
        tk.Label(inner, text="Stream URL:", bg=COLORS['bg'], fg=COLORS['text'], font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = tk.Entry(inner, font=('Segoe UI', 9), bg=COLORS['entry_bg'], fg=COLORS['entry_fg'], insertbackground=COLORS['text'])
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        tk.Label(inner, text="Referer:", bg=COLORS['bg'], fg=COLORS['text'], font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.referer_entry = tk.Entry(inner, font=('Segoe UI', 9), bg=COLORS['entry_bg'], fg=COLORS['entry_fg'], insertbackground=COLORS['text'])
        self.referer_entry.insert(0, "https://www.patreon.com")
        self.referer_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        tk.Label(inner, text="User Agent:", bg=COLORS['bg'], fg=COLORS['text'], font=('Segoe UI', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ua_var = tk.StringVar(value="Chrome")
        ttk.Combobox(inner, textvariable=self.ua_var, values=list(USER_AGENTS.keys()), state="readonly").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        StyledButton(inner, text="Load Stream", command=self.load_and_play_stream).grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)
        
        inner.columnconfigure(1, weight=1)

    def setup_control_panel(self):
        self.control_panel = tk.Frame(self.player_area, bg=COLORS['control_bg'], relief=tk.RAISED, bd=1)
        self.control_panel.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Seekbar
        seek_frame = tk.Frame(self.control_panel, bg=COLORS['control_bg'])
        seek_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        
        self.time_label_left = tk.Label(seek_frame, text="00:00:00", bg=COLORS['control_bg'], fg=COLORS['text'], font=('Segoe UI', 8))
        self.time_label_left.pack(side=tk.LEFT, padx=(0, 8))
        
        self.progress_var = tk.DoubleVar()
        self.progress_scale = ttk.Scale(seek_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.progress_var, command=self.on_seek_move, style='MPC.Horizontal.TScale')
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_seek_end)
        
        self.time_label_right = tk.Label(seek_frame, text="00:00:00", bg=COLORS['control_bg'], fg=COLORS['text'], font=('Segoe UI', 8))
        self.time_label_right.pack(side=tk.LEFT, padx=(8, 0))
        
        # Controls Row
        ctrl_frame = tk.Frame(self.control_panel, bg=COLORS['control_bg'])
        ctrl_frame.pack(fill=tk.X, padx=8, pady=(4, 8))
        
        # Left: Playback
        left = tk.Frame(ctrl_frame, bg=COLORS['control_bg'])
        left.pack(side=tk.LEFT)
        
        StyledButton(left, text="Open", command=self.show_open_dialog).pack(side=tk.LEFT, padx=2)
        StyledButton(left, text="⮜", command=lambda: self.skip(-10), width=3).pack(side=tk.LEFT, padx=2)
        self.play_btn = StyledButton(left, text="▶", command=self.toggle_play_pause, width=4, font=('Segoe UI', 10))
        self.play_btn.pack(side=tk.LEFT, padx=2)
        StyledButton(left, text="■", command=self.stop_stream, width=3).pack(side=tk.LEFT, padx=2)
        StyledButton(left, text="⮞", command=lambda: self.skip(10), width=3).pack(side=tk.LEFT, padx=2)
        
        self.record_btn = StyledButton(left, text="● Rec", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=2)
        
        StyledButton(left, text="⛶", command=self.toggle_fullscreen, width=3).pack(side=tk.LEFT, padx=2)
        
        # Center: Quality Selector (Moved here from below)
        center = tk.Frame(ctrl_frame, bg=COLORS['control_bg'])
        center.pack(side=tk.LEFT, expand=True)
        
        # Quality Selector (Hidden initially)
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(center, textvariable=self.quality_var, state="readonly", width=15)
        self.quality_combo.bind("<<ComboboxSelected>>", self.on_quality_change)
        

        
        # Right: Volume
        right = tk.Frame(ctrl_frame, bg=COLORS['control_bg'])
        right.pack(side=tk.RIGHT)
        
        self.mute_btn = StyledButton(right, text="🔊", command=self.toggle_mute, width=3)
        self.mute_btn.pack(side=tk.LEFT, padx=2)
        
        self.volume_var = tk.IntVar(value=100)
        ttk.Scale(right, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var, command=self.on_volume_change, length=80, style='MPC.Horizontal.TScale').pack(side=tk.LEFT, padx=5)
        self.volume_label = tk.Label(right, text="100%", bg=COLORS['control_bg'], fg=COLORS['text'], font=('Segoe UI', 8), width=5)
        self.volume_label.pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    #  Logic
    # ------------------------------------------------------------------
    def show_open_dialog(self):
        if self.show_config:
            self.config_panel.pack_forget()
            self.show_config = False
        else:
            self.config_panel.pack(fill=tk.X, side=tk.TOP, before=self.video_frame, padx=4, pady=4)
            self.show_config = True
            self.url_entry.focus_set()

    def toggle_history(self):
        self.show_history = not self.show_history
        if self.show_history:
            self.history_panel.pack(side=tk.BOTTOM, fill=tk.X)
            self.history_panel.listbox.focus_set()
        else:
            self.history_panel.pack_forget()

    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top_var.get())

    def load_from_history(self, url):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self.load_and_play_stream()

    def refresh_history(self):
        history = load_history()
        self.history_panel.update_history(history)

    def delete_history_item(self, index):
        history = load_history()
        if 0 <= index < len(history):
            del history[index]
            write_history(history)
            self.refresh_history()

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all history?"):
            write_history([])
            self.refresh_history()

    def load_and_play_stream(self):
        url = self.url_entry.get().strip()
        ref = self.referer_entry.get().strip()
        ua = USER_AGENTS[self.ua_var.get()]

        if not url: return
        
        self.current_url = url
        self.status_label.config(text="Loading...", fg=COLORS['text'])
        self.spinner.start()
        
        # Save to history
        save_history(url)
        self.refresh_history()
        
        # Hide config
        if self.show_config:
            self.config_panel.pack_forget()
            self.show_config = False
            
        # Threaded load
        threading.Thread(target=self._load_thread, args=(url, ref, ua), daemon=True).start()

    def _load_thread(self, url, ref, ua):
        try:
            # Check URL validity first
            headers = {"Referer": ref, "User-Agent": ua}
            r = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            if r.status_code >= 400:
                self.root.after(0, lambda: messagebox.showerror("Error", f"HTTP {r.status_code}"))
                return

            if self.player:
                self.player.stop()
                self.player.play(url, headers={"Referer": ref}, user_agent=ua)
                
                self.is_playing = True
                self.root.after(0, self._on_play_start)
                
                # Observe buffering
                @self.player.mpv.property_observer('core-idle')
                def on_core_idle(name, value):
                    if self.is_closing: return
                    if value:
                        self.root.after(0, self.spinner.start)
                    else:
                        self.root.after(0, self.spinner.stop)
                        
                @self.player.mpv.property_observer('paused-for-cache')
                def on_paused_for_cache(name, value):
                    if self.is_closing: return
                    if value:
                        self.root.after(0, self.spinner.start)
                    else:
                        self.root.after(0, self.spinner.stop)
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _on_play_start(self):
        self.play_btn.config(text="⏸")
        self.status_label.config(text="Playing", fg='green')
        self.video_canvas.focus_set()
        
        # Update Quality List
        self.root.after(2000, self.update_quality_list)
        
        # Check for resume
        self.root.after(500, self.check_resume_playback)

    def check_resume_playback(self):
        item = get_history_item(self.current_url)
        if item and item.get('last_position', 0) > 5:
            pos = item['last_position']
            formatted = format_time(pos)
            if messagebox.askyesno("Resume Playback", f"Resume from {formatted}?"):
                self._retry_seek(pos)

    def _retry_seek(self, pos, attempt=1):
        """Try to seek to the position, retrying if MPV is not ready."""
        try:
            self.player.seek(pos, "absolute")
        except Exception as e:
            if attempt <= 3:
                print(f"Seek failed (attempt {attempt}): {e}. Retrying in 1s...")
                self.root.after(1000, lambda: self._retry_seek(pos, attempt + 1))
            else:
                messagebox.showerror("Error", f"Failed to resume playback after multiple attempts.\n{e}")

    def update_quality_list(self):
        if not self.player: return
        tracks = self.player.get_video_tracks()
        if not tracks: return
        
        # Filter video tracks
        video_tracks = [t for t in tracks if t['type'] == 'video']
        if len(video_tracks) > 1:
            values = [f"{t['id']}: {t.get('demux-h')}p ({t.get('codec')})" for t in video_tracks]
            self.quality_combo['values'] = values
            self.quality_combo.pack(pady=2) # Show combo
        else:
            self.quality_combo.pack_forget()

    def on_quality_change(self, event):
        selection = self.quality_combo.get()
        if selection:
            track_id = int(selection.split(':')[0])
            self.player.set_video_track(track_id)

    def toggle_play_pause(self):
        if self.player and self.player.pause():
            self.play_btn.config(text="▶")
            self.status_label.config(text="Paused", fg='orange')
        else:
            self.play_btn.config(text="⏸")
            self.status_label.config(text="Playing", fg='green')

    def stop_stream(self):
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.play_btn.config(text="▶")
            self.status_label.config(text="Stopped", fg='red')
            self.spinner.stop()
            
            # Save progress before stopping
            try:
                pos = self.player.get_time_pos()
                if pos: update_history_progress(self.current_url, pos)
            except: pass
            
            self.time_label_left.config(text="00:00:00")
            self.progress_var.set(0)
            
            if self.is_recording:
                self.toggle_recording()

    def toggle_recording(self):
        if not self.is_playing: return
        
        if not self.is_recording:
            # Start Recording
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            
            filename = f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ts"
            unique_filename = get_unique_filename("downloads", filename)
            filepath = os.path.join("downloads", unique_filename)
            
            self.player.start_recording(filepath)
            self.is_recording = True
            self.record_btn.config(bg=COLORS['record_active'], text="● Stop Rec")
            messagebox.showinfo("Recording Started", f"Recording to: {filepath}")
        else:
            # Stop Recording
            self.player.stop_recording()
            self.is_recording = False
            self.record_btn.config(bg=COLORS['button_bg'], text="● Rec")
            messagebox.showinfo("Recording Stopped", "Recording saved.")

    def skip(self, seconds):
        if self.player: self.player.seek(seconds)

    def on_seek_move(self, value):
        self.is_seeking = True
        if self.player:
            dur = self.player.get_duration()
            if dur:
                # Update time label with preview
                t = (float(value) / 100.0) * dur
                self.time_label_left.config(text=format_time(t))
    def on_seek_end(self, _):
        if self.player:
            dur = self.player.get_duration()
            if dur:
                t = (self.progress_var.get() / 100.0) * dur
                self.player.seek(t, "absolute")
        self.is_seeking = False

    def toggle_mute(self):
        if not self.player: return
        vol = self.volume_var.get()
        if vol > 0:
            self.previous_volume = vol
            self.volume_var.set(0)
            self.player.set_volume(0)
            self.mute_btn.config(text="🔇")
        else:
            self.volume_var.set(self.previous_volume)
            self.player.set_volume(self.previous_volume)
            self.mute_btn.config(text="🔊")

    def on_volume_change(self, val):
        if self.player:
            v = int(float(val))
            self.player.set_volume(v)
            self.volume_label.config(text=f"{v}%")
            self.mute_btn.config(text="🔇" if v == 0 else "🔊")

    def update_player_info(self):
        if self.player and self.is_playing:
            try:
                cur = self.player.get_time_pos()
                dur = self.player.get_duration()
                if cur is not None and dur and not self.is_seeking:
                    self.time_label_left.config(text=format_time(cur))
                    self.time_label_right.config(text=format_time(dur))
                    self.progress_var.set((cur / dur) * 100)
                    
                    # Save progress every 5 seconds approx (modulo check)
                    if int(cur) % 5 == 0:
                        update_history_progress(self.current_url, cur)
                
                # Update network speed indicator
                cache_state = self.player.get_demuxer_cache_state()
                if cache_state and isinstance(cache_state, dict):
                    raw_rate = cache_state.get('raw-input-rate', 0)
                    if raw_rate and raw_rate > 0:
                        speed_text = self.format_speed(raw_rate)
                        self.speed_label.config(text=f" {speed_text}")
                    else:
                        self.speed_label.config(text="")
                else:
                    self.speed_label.config(text="")
            except: pass
        else:
            # Hide speed indicator when not playing
            self.speed_label.config(text="")
        self.root.after(1000, self.update_player_info)

    # ------------------------------------------------------------------
    #  Click Handling
    # ------------------------------------------------------------------
    def handle_click(self, event=None):
        if self.click_timer:
            self.root.after_cancel(self.click_timer)
        self.click_timer = self.root.after(300, self.perform_single_click)

    def handle_double_click(self, event=None):
        if self.click_timer:
            self.root.after_cancel(self.click_timer)
            self.click_timer = None
        self.toggle_fullscreen()

    def perform_single_click(self):
        self.click_timer = None
        # Only toggle play/pause if user didn't drag
        if not self.is_dragging:
            self.toggle_play_pause()
    
    def format_speed(self, bytes_per_sec):
        """Format network speed in KB/s or MB/s."""
        if bytes_per_sec < 1024 * 1024:  # < 1 MB/s
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

    # ------------------------------------------------------------------
    #  Drag Window
    # ------------------------------------------------------------------
    def start_drag(self, event):
        """Start window drag when user presses mouse button on video area."""
        # Don't drag in fullscreen mode
        if self.is_fullscreen:
            self.handle_click()
            return
            
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.is_dragging = False  # Will be set to True if actual movement occurs
        
        # Still trigger click timer for single-click detection
        self.handle_click()
    
    def do_drag(self, event):
        """Perform window drag while mouse button is held and moved."""
        # Don't drag in fullscreen mode
        if self.is_fullscreen:
            return
            
        # Calculate movement
        delta_x = event.x - self.drag_start_x
        delta_y = event.y - self.drag_start_y
        
        # If moved more than 5 pixels, consider it a drag (not a click)
        if abs(delta_x) > 5 or abs(delta_y) > 5:
            self.is_dragging = True
            
            # Get current window position
            x = self.root.winfo_x() + delta_x
            y = self.root.winfo_y() + delta_y
            
            # Move window
            self.root.geometry(f"+{x}+{y}")
    
    def stop_drag(self, event):
        """Stop window drag when user releases mouse button."""
        # Don't process in fullscreen mode
        if self.is_fullscreen:
            return
            
        # Reset drag state after a short delay to allow click handler to check it
        self.root.after(50, lambda: setattr(self, 'is_dragging', False))

    # ------------------------------------------------------------------
    #  Fullscreen & Resize
    # ------------------------------------------------------------------
    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            self.enter_fullscreen()
        else:
            self.exit_fullscreen()

    def enter_fullscreen(self):
        self.normal_geometry = self.root.geometry()
        
        # Hide panels
        self.config_panel.pack_forget()
        self.history_panel.pack_forget()
        
        # Switch controls to overlay mode
        self.control_panel.pack_forget()
        self.controls_visible = False
        
        # Hide menu
        # Hide menu bar
        self.menu_bar.pack_forget()
        
        # Remove borders for clean look
        self.video_frame.config(bd=0, relief=tk.FLAT)
        self.video_frame.pack_configure(padx=0, pady=0)
        
        # Set fullscreen
        self.root.attributes('-fullscreen', True)
        self.is_fullscreen = True
        
        # Auto-hide bindings
        self.root.bind('<Motion>', self.on_fullscreen_motion)
        self.show_controls()
        self.schedule_hide_controls()

    def exit_fullscreen(self):
        self.root.attributes('-fullscreen', False)
        self.is_fullscreen = False
        
        # Restore borders
        self.video_frame.config(bd=2, relief=tk.SUNKEN)
        self.video_frame.pack_configure(padx=4, pady=4)
        
        # Remove auto-hide bindings
        self.root.unbind('<Motion>')
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
            self.hide_timer = None
            
        # Ensure controls are visible
        self.control_panel.place_forget()
        self.controls_visible = False
        self.show_controls()
        
        # Restore cursor
        self.root.config(cursor="")
        
        # Restore menu
        # Restore menu bar
        self.menu_bar.pack(side=tk.TOP, fill=tk.X, before=self.main_container)
        
        # Restore panels if they were enabled
        if self.show_config:
            self.config_panel.pack(fill=tk.X, side=tk.TOP, before=self.video_frame, padx=4, pady=4)
            
        if self.show_history:
            self.history_panel.pack(side=tk.BOTTOM, fill=tk.X)

    def on_fullscreen_motion(self, event):
        if not self.is_fullscreen: return
        
        # Show controls if mouse is at bottom 100px or if moving
        screen_height = self.root.winfo_screenheight()
        if event.y_root > screen_height - 100:
            self.show_controls()
            # Don't hide if hovering controls
            if self.hide_timer:
                self.root.after_cancel(self.hide_timer)
                self.hide_timer = None
        else:
            # If moving in upper area, show briefly then hide
            self.show_controls()
            self.schedule_hide_controls()

    def show_controls(self):
        self.root.config(cursor="")
        if not self.controls_visible:
            if self.is_fullscreen:
                self.control_panel.place(relx=0, rely=1, anchor='sw', relwidth=1)
                self.control_panel.lift()
            else:
                self.control_panel.pack(fill=tk.X, side=tk.BOTTOM)
            self.controls_visible = True

    def hide_controls(self):
        if self.controls_visible and self.is_fullscreen:
            self.control_panel.place_forget()
            self.control_panel.pack_forget()
            self.controls_visible = False
            self.root.config(cursor="none")

    def schedule_hide_controls(self):
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
        self.hide_timer = self.root.after(3000, self.hide_controls)

    def on_window_resize(self, event):
        # No longer needed to reparent player
        pass

    def on_closing(self):
        self.is_closing = True
        self.spinner.stop()
        
        if self.player:
            # Save final progress
            try:
                pos = self.player.get_time_pos()
                if pos: update_history_progress(self.current_url, pos)
            except: pass
            self.player.terminate()
        self.root.destroy()
