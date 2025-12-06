import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog
import threading
import os
import requests
from datetime import datetime

from .config import COLORS, USER_AGENTS
from .player_core import MpvPlayer
from .ui_components import StyledButton, PrimaryButton, HistoryPanel, LoadingSpinner, BufferedScale, CustomTitleBar, apply_custom_window_style, show_custom_error, show_custom_warning, show_custom_info, ask_custom_yes_no
from .utils import format_time, load_history, save_history, get_unique_filename, write_history, update_history_progress, get_history_item, load_settings, save_settings

class M3U8StreamingPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 Player")
        # Center the window
        w, h = 1000, 600
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.configure(bg=COLORS['border']) # Use border color for root backbone
        
        # --- Custom Title Bar Setup (Windows) ---
        self.setup_custom_window()
        # ----------------------------------------
        
        # State
        self.player = None
        self.is_playing = False
        self.is_seeking = False
        self.is_fullscreen = False
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

        # Settings
        self.settings = load_settings()

        # Initialize UI first (fast)
        self.setup_styles()
        self.setup_title_bar()
        self.setup_menu()
        self.setup_ui()
        self.setup_bindings()
        
        # Load History (fast)
        self.refresh_history()
        
        # Remove focus from buttons on startup
        self.root.focus_set()
        
        # Defer MPV initialization to after UI is displayed
        self.root.after(100, self._init_player_async)
    
    def _init_player_async(self):
        """Initialize MPV player after UI is ready for faster startup."""
        try:
            self.player = MpvPlayer(wid=self.video_canvas.winfo_id())
        except Exception as e:
            show_custom_error(self.root, "Error", str(e))
            return

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

    def setup_custom_window(self):
        """Remove Windows title bar but keep resizing and taskbar presence using ctypes."""
        apply_custom_window_style(self.root, enable_resize=True)

    def setup_title_bar(self):
        self.title_bar = CustomTitleBar(self.root, title="M3U8 Player")
        self.title_bar.pack(side=tk.TOP, fill=tk.X, padx=1, pady=0)
        self.root.bind("<<CloseRequest>>", lambda e: self.on_closing())
        
        # Main content container (with border padding effect from root)
        self.content_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))

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
        self.root.bind("<F1>", lambda e: self.show_shortcuts_dialog())
        self.root.bind("<Configure>", self.on_window_resize)
        
        # ALT key to toggle menu bar (use KeyRelease to avoid double trigger)
        self.root.bind("<KeyRelease-Alt_L>", lambda e: self.toggle_menu_bar())
        self.root.bind("<KeyRelease-Alt_R>", lambda e: self.toggle_menu_bar())
        
        # Video Canvas Bindings
        self.video_canvas.bind("<Button-1>", self.start_drag)
        self.video_canvas.bind("<B1-Motion>", self.do_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.video_canvas.bind("<Double-Button-1>", lambda e: self.handle_double_click())

    def setup_menu(self):
        # Menu visibility state
        self.menu_visible = False
        self.last_menu_toggle = 0  # Debounce timestamp
        
        # Custom Menu Bar Container (hidden by default)
        self.menu_bar = tk.Frame(self.content_frame, bg=COLORS['menu_bg'])
        # Don't pack initially - hidden by default
        
        # Separator Line
        self.menu_separator = tk.Frame(self.content_frame, bg=COLORS['button_active'], height=1)
        # Don't pack initially - hidden by default
        
        # Right: All menus and buttons
        self.menu_right = tk.Frame(self.menu_bar, bg=COLORS['menu_bg'])
        self.menu_right.pack(side=tk.RIGHT, padx=5)
        
        # File Menu
        self.file_btn = tk.Menubutton(self.menu_right, text="File", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                     activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                     bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.file_btn.pack(side=tk.LEFT, padx=2)
        
        file_menu = Menu(self.file_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        file_menu.add_command(label="Open URL... (Ctrl+O)", command=self.show_open_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.file_btn.config(menu=file_menu)
        
        # View Menu
        self.view_btn = tk.Menubutton(self.menu_right, text="View", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                     activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                     bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.view_btn.pack(side=tk.LEFT, padx=2)
        
        view_menu = Menu(self.view_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        view_menu.add_command(label="Fullscreen (F)", command=self.toggle_fullscreen)
        self.always_on_top_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top)
        self.view_btn.config(menu=view_menu)

        # Help Menu
        self.help_btn = tk.Menubutton(self.menu_right, text="Help", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                     activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                     bd=0, relief=tk.FLAT, font=('Segoe UI', 9))
        self.help_btn.pack(side=tk.LEFT, padx=2)
        
        help_menu = Menu(self.help_btn, tearoff=0, bg=COLORS['menu_bg'], fg=COLORS['text'])
        help_menu.add_command(label="Keyboard Shortcuts (F1)", command=self.show_shortcuts_dialog)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about_dialog)
        self.help_btn.config(menu=help_menu)

        # History Button (styled like Menubutton)
        self.history_btn = tk.Button(self.menu_right, text="History", bg=COLORS['menu_bg'], fg=COLORS['text'],
                                    activebackground=COLORS['button_hover'], activeforeground=COLORS['text'],
                                    bd=0, relief=tk.FLAT, font=('Segoe UI', 9), command=self.toggle_history)
        self.history_btn.pack(side=tk.LEFT, padx=2)


    def setup_ui(self):
        # Main container (Horizontal for History Panel)
        self.main_container = tk.Frame(self.content_frame, bg=COLORS['bg'])
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
        
        # Placeholder Overlay (shown when idle)
        self.setup_video_placeholder()
        
        # Loading Spinner
        self.spinner = LoadingSpinner(self.video_frame, size=60, color='#00FF00', bg_color=COLORS['video_bg'], root_window=self.root)
        
        # Control Panel
        self.setup_control_panel()

        # Right side (History) - Initially hidden
        self.history_panel = HistoryPanel(self.main_container, self.load_from_history, 
                                        self.delete_history_item, self.clear_history)
    
    def setup_video_placeholder(self):
        """Create placeholder overlay for video area when idle"""
        self.placeholder_frame = tk.Frame(self.video_frame, bg=COLORS['video_bg'])
        self.placeholder_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Play icon (using Unicode triangle)
        icon_label = tk.Label(self.placeholder_frame, text="▶", 
                             bg=COLORS['video_bg'], fg=COLORS['text_gray'],
                             font=('Segoe UI', 80))
        icon_label.pack(pady=(0, 20))
        
        # Instructions
        text1 = tk.Label(self.placeholder_frame, 
                        text="Enter a stream URL and click Load Stream",
                        bg=COLORS['video_bg'], fg=COLORS['text_gray'],
                        font=('Segoe UI', 11))
        text1.pack()
        
    def setup_config_panel(self):
        self.config_panel = tk.Frame(self.player_area, bg=COLORS['bg'], relief=tk.FLAT, bd=0)
        self.config_panel.pack(fill=tk.X, padx=10, pady=10)
        
        # Row 1: Stream URL (full width) + Load Button
        row1 = tk.Frame(self.config_panel, bg=COLORS['bg'])
        row1.pack(fill=tk.X, pady=(0, 8))
        
        # Label inline
        tk.Label(row1, text="Stream URL:", bg=COLORS['bg'], fg=COLORS['text_gray'], font=('Segoe UI', 9), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 8))
        
        url_frame = tk.Frame(row1, bg=COLORS['bg'])
        url_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.url_entry = tk.Entry(url_frame, font=('Segoe UI', 10), bg=COLORS['entry_bg'], fg=COLORS['entry_fg'], 
                                 insertbackground=COLORS['text'], relief=tk.FLAT, bd=1)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        
        # Configure placeholder
        self.url_entry.insert(0, "Enter M3U8 stream URL...")
        self.url_entry.config(fg=COLORS['text_gray'])
        self.url_entry.bind('<FocusIn>', self._on_url_focus_in)
        self.url_entry.bind('<FocusOut>', self._on_url_focus_out)
        
        PrimaryButton(url_frame, text="Load Stream", command=self.load_and_play_stream).pack(side=tk.RIGHT)
        
        # Row 2: Referer + User Agent (side by side)
        row2 = tk.Frame(self.config_panel, bg=COLORS['bg'])
        row2.pack(fill=tk.X)
        
        # Referer (left half)
        ref_frame = tk.Frame(row2, bg=COLORS['bg'])
        ref_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        tk.Label(ref_frame, text="Referer:", bg=COLORS['bg'], fg=COLORS['text_gray'], font=('Segoe UI', 9), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 8))
        self.referer_entry = tk.Entry(ref_frame, font=('Segoe UI', 9), bg=COLORS['entry_bg'], fg=COLORS['entry_fg'], 
                                     insertbackground=COLORS['text'], relief=tk.FLAT, bd=1)
        self.referer_entry.insert(0, "https://www.patreon.com")
        self.referer_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        # User Agent (right half)
        ua_frame = tk.Frame(row2, bg=COLORS['bg'])
        ua_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        tk.Label(ua_frame, text="User Agent:", bg=COLORS['bg'], fg=COLORS['text_gray'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.ua_var = tk.StringVar(value="Chrome")
        ua_combo = ttk.Combobox(ua_frame, textvariable=self.ua_var, values=list(USER_AGENTS.keys()), 
                                state="readonly", font=('Segoe UI', 9))
        ua_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def copy_url(self):
        if self.current_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_url)
            show_custom_info(self.root, "Copied", "Stream URL copied to clipboard")
    
    def _on_url_focus_in(self, event):
        if self.url_entry.get() == "Enter M3U8 stream URL...":
            self.url_entry.delete(0, tk.END)
            self.url_entry.config(fg=COLORS['entry_fg'])
    
    def _on_url_focus_out(self, event):
        if not self.url_entry.get().strip():
            self.url_entry.insert(0, "Enter M3U8 stream URL...")
            self.url_entry.config(fg=COLORS['text_gray'])
        
    def setup_control_panel(self):
        self.control_panel = tk.Frame(self.player_area, bg=COLORS['control_bg'], bd=0)
        self.control_panel.pack(fill=tk.X, side=tk.BOTTOM, pady=0)
        
        # Single Row Container
        self.ctrl_frame = tk.Frame(self.control_panel, bg=COLORS['control_bg'])
        self.ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 1. Time (Left)
        time_frame = tk.Frame(self.ctrl_frame, bg=COLORS['control_bg'])
        time_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.time_label_left = tk.Label(time_frame, text="00:00:00", bg=COLORS['control_bg'], fg=COLORS['text'], font=('Segoe UI', 10))
        self.time_label_left.pack(side=tk.LEFT)
        tk.Label(time_frame, text=" / ", bg=COLORS['control_bg'], fg=COLORS['text_gray'], font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.time_label_right = tk.Label(time_frame, text="00:00:00", bg=COLORS['control_bg'], fg=COLORS['text_gray'], font=('Segoe UI', 10))
        self.time_label_right.pack(side=tk.LEFT)
        
        # 2. Controls (Right) - Packed first so they stick to right
        controls_right = tk.Frame(self.ctrl_frame, bg=COLORS['control_bg'])
        controls_right.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Skip Back
        StyledButton(controls_right, text="⏮", command=lambda: self.skip(-10), width=4, font=('Segoe UI', 14)).pack(side=tk.LEFT, padx=2)
        
        # Play/Pause (Blue Accent)
        self.play_btn = StyledButton(controls_right, text="▶", command=self.toggle_play_pause, width=4, font=('Segoe UI', 14))
        self.play_btn.pack(side=tk.LEFT, padx=8)
        
        # Skip Forward
        StyledButton(controls_right, text="⏭", command=lambda: self.skip(10), width=4, font=('Segoe UI', 14)).pack(side=tk.LEFT, padx=2)
        
        # Volume Group
        self.vol_frame = tk.Frame(controls_right, bg=COLORS['control_bg'])
        self.vol_frame.pack(side=tk.LEFT, padx=(15, 0))
        
        self.mute_btn = StyledButton(self.vol_frame, text="🔊", command=self.toggle_mute, width=3, font=('Segoe UI', 15))
        self.mute_btn.pack(side=tk.LEFT, pady=(0, 3))
        
        # Volume Slider Container for Animation
        self.vol_target_width = 140  # Target width for slider + label
        self.vol_anim_job = None
        
        self.vol_slider_container = tk.Frame(self.vol_frame, bg=COLORS['control_bg'], width=0, height=25)
        self.vol_slider_container.pack_propagate(False) # Important for manual width control
        self.vol_slider_container.pack(side=tk.LEFT, padx=0) # Start hidden (width=0)

        self.volume_var = tk.IntVar(value=100)
        # Use BufferedScale for volume
        self.volume_scale = BufferedScale(self.vol_slider_container, command=self.on_volume_change, width=80, height=20)
        self.volume_scale.set_progress(100)
        self.volume_scale.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.volume_label = tk.Label(self.vol_slider_container, text="100%", bg=COLORS['control_bg'], 
                                     fg=COLORS['text_gray'], font=('Segoe UI', 9), width=4)
        self.volume_label.pack(side=tk.LEFT, padx=(0, 5))

        # Bind hover events
        for widget in [self.vol_frame, self.mute_btn, self.volume_scale, self.volume_label, self.vol_slider_container]:
            widget.bind("<Enter>", self.on_volume_enter)
            widget.bind("<Leave>", self.on_volume_leave)
        
        # Fullscreen
        StyledButton(controls_right, text="⛶", command=self.toggle_fullscreen, width=4, font=('Segoe UI', 14)).pack(side=tk.LEFT, padx=(10, 0), pady=(0, 3))
        # We pack this last with fill=tk.X and expand=True
        seek_frame = tk.Frame(self.ctrl_frame, bg=COLORS['control_bg'])
        seek_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_scale = BufferedScale(seek_frame, command=self.on_seek_end)
        self.progress_scale.pack(fill=tk.X, expand=True)

        # Initialize hidden/extra controls
        self.volume_hide_timer = None
        
        # Quality Combo
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(controls_right, textvariable=self.quality_var, state="readonly", width=10)
        self.quality_combo.bind("<<ComboboxSelected>>", self.on_quality_change)
        
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
        else:
            self.history_panel.pack_forget()

    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top_var.get())
    
    def toggle_menu_bar(self):
        """Toggle menu bar visibility with ALT key."""
        import time
        current_time = time.time()
        
        # Debounce - ignore if called within 200ms
        if current_time - self.last_menu_toggle < 0.2:
            return
        self.last_menu_toggle = current_time
        
        if self.menu_visible:
            self.menu_bar.pack_forget()
            self.menu_separator.pack_forget()
            self.menu_visible = False
        else:
            # Pack at top, before other content
            self.menu_bar.pack(side=tk.TOP, fill=tk.X, before=self.main_container)
            self.menu_separator.pack(side=tk.TOP, fill=tk.X, before=self.main_container)
            self.menu_visible = True
        
        # Force UI update
        self.root.update_idletasks()

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
        if ask_custom_yes_no(self.root, "Confirm", "Are you sure you want to clear all history?"):
            write_history([])
            self.refresh_history()

    def load_and_play_stream(self):
        url = self.url_entry.get().strip()
        ref = self.referer_entry.get().strip()
        ua = USER_AGENTS[self.ua_var.get()]

        # Check if URL is placeholder or empty
        if not url or url == "Enter M3U8 stream URL...":
            show_custom_warning(self.root, "Warning", "Please enter a valid URL")
            return
        
        self.current_url = url
        self.spinner.start()
        
        # Hide placeholder overlay
        if hasattr(self, 'placeholder_frame'):
            self.placeholder_frame.place_forget()
        
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
                self.root.after(0, lambda: show_custom_error(self.root, "Error", f"HTTP {r.status_code}"))
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
                    # Only show spinner if not manually paused
                    is_paused = self.player.mpv.pause if self.player and self.player.mpv else False
                    if value and not is_paused:
                        self.root.after(0, self.spinner.start)
                    else:
                        self.root.after(0, self.spinner.stop)
                        
                @self.player.mpv.property_observer('paused-for-cache')
                def on_paused_for_cache(name, value):
                    if self.is_closing: return
                    # Only show spinner if not manually paused
                    is_paused = self.player.mpv.pause if self.player and self.player.mpv else False
                    if value and not is_paused:
                        self.root.after(0, self.spinner.start)
                    else:
                        self.root.after(0, self.spinner.stop)
                
                @self.player.mpv.property_observer('eof-reached')
                def on_eof_reached(name, value):
                    if self.is_closing: return
                    if value:
                        self.root.after(0, self.stop_stream)
                
        except Exception as e:
            self.root.after(0, lambda: show_custom_error(self.root, "Error", str(e)))

    def _on_play_start(self):
        self.play_btn.config(text="⏸")
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
            
            # Pause player while user decides
            if self.player and self.player.mpv:
                self.player.mpv.pause = True
                self.play_btn.config(text="▶")
            
            if ask_custom_yes_no(self.root, "Resume Playback", f"Resume from {formatted}?"):
                self._retry_seek(pos)
            
            # Resume playback after decision
            if self.player and self.player.mpv:
                self.player.mpv.pause = False
                self.play_btn.config(text="⏸")

    def _retry_seek(self, pos, attempt=1):
        """Try to seek to the position, retrying if MPV is not ready."""
        try:
            self.player.seek(pos, "absolute")
        except Exception as e:
            if attempt <= 3:
                print(f"Seek failed (attempt {attempt}): {e}. Retrying in 1s...")
                self.root.after(1000, lambda: self._retry_seek(pos, attempt + 1))
            else:
                show_custom_error(self.root, "Error", f"Failed to resume playback after multiple attempts.\n{e}")

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
        if not self.current_url:
            show_custom_warning(self.root, "Warning", "Please load a URL first")
            return

        if self.player and self.player.pause():
            self.play_btn.config(text="▶")
            self.spinner.stop() # Ensure spinner is hidden when paused
        else:
            self.play_btn.config(text="⏸")

    def stop_stream(self):
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.play_btn.config(text="▶")
            self.spinner.stop()
            
            # Save progress before stopping
            try:
                pos = self.player.get_time_pos()
                if pos: update_history_progress(self.current_url, pos)
            except: pass
            
            self.time_label_left.config(text="00:00:00")
            self.time_label_left.config(text="00:00:00")
            self.progress_scale.set_progress(0)
            self.progress_scale.set_buffer(0)



    def skip(self, seconds):
        if self.player: self.player.seek(seconds)

    def on_seek_move(self, value):
        pass

    def on_seek_end(self, value):
        if self.player:
            dur = self.player.get_duration()
            if dur:
                t = (value / 100.0) * dur
                self.player.seek(t, "absolute")

    def toggle_mute(self):
        if not self.player: return
        vol = self.volume_scale.progress
        if vol > 0:
            self.previous_volume = vol
            self.volume_scale.set_progress(0)
            self.player.set_volume(0)
            self.mute_btn.config(text="🔇")
            self.volume_label.config(text="0%")
        else:
            self.volume_scale.set_progress(self.previous_volume)
            self.player.set_volume(int(self.previous_volume))
            self.mute_btn.config(text="🔊")
            self.volume_label.config(text=f"{int(self.previous_volume)}%")

    def on_volume_change(self, val):
        if self.player:
            v = int(float(val))
            self.player.set_volume(v)
            self.volume_label.config(text=f"{v}%")
            self.mute_btn.config(text="🔇" if v == 0 else "🔊")

    def format_speed(self, bytes_per_sec):
        """Format network speed in KB/s or MB/s."""
        if bytes_per_sec < 1024 * 1024:  # < 1 MB/s
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

    def update_player_info(self):
        if self.player and self.is_playing:
            try:
                cur = self.player.get_time_pos()
                dur = self.player.get_duration()
                if cur is not None and dur and not self.is_seeking:
                    self.time_label_left.config(text=format_time(cur))
                    self.time_label_right.config(text=format_time(dur))
                    self.time_label_left.config(text=format_time(cur))
                    self.time_label_right.config(text=format_time(dur))
                    self.progress_scale.set_progress((cur / dur) * 100)
                    
                    # Update buffer
                    buf = self.player.get_buffered_time()
                    if buf:
                        self.progress_scale.set_buffer((buf / dur) * 100)
                    
                    # Save progress every 5 seconds approx (modulo check)
                    if int(cur) % 5 == 0:
                        update_history_progress(self.current_url, cur)
                
                # Update network speed indicator (on spinner during buffering)
                cache_state = self.player.get_demuxer_cache_state()
                if cache_state and isinstance(cache_state, dict):
                    raw_rate = cache_state.get('raw-input-rate', 0)
                    if raw_rate and raw_rate > 0:
                        speed_text = self.format_speed(raw_rate)
                        self.spinner.set_speed(speed_text)
                    else:
                        self.spinner.set_speed("")
                else:
                    self.spinner.set_speed("")
            except: pass
        self.root.after(1000, self.update_player_info)

    def on_volume_enter(self, event):
        if self.volume_hide_timer:
            self.root.after_cancel(self.volume_hide_timer)
            self.volume_hide_timer = None
        
        # Animate open
        self.animate_volume_width(self.vol_target_width)

    def on_volume_leave(self, event):
        if self.volume_hide_timer:
            self.root.after_cancel(self.volume_hide_timer)
        self.volume_hide_timer = self.root.after(300, self.hide_volume_controls)

    def hide_volume_controls(self):
        # Check if mouse is really outside the volume frame
        x, y = self.root.winfo_pointerxy()
        widget_x = self.vol_frame.winfo_rootx()
        widget_y = self.vol_frame.winfo_rooty()
        widget_w = self.vol_frame.winfo_width()
        widget_h = self.vol_frame.winfo_height()
        
        # Add a small buffer/margin to prevent flickering at edges
        margin = 10
        if not (widget_x - margin <= x <= widget_x + widget_w + margin and 
                widget_y - margin <= y <= widget_y + widget_h + margin):
            # Animate close
            self.animate_volume_width(0)

    def animate_volume_width(self, target_width):
        if self.vol_anim_job:
            self.root.after_cancel(self.vol_anim_job)
            self.vol_anim_job = None

        current_width = self.vol_slider_container.winfo_width()
        
        if current_width == target_width:
            return

        # Determine step size for smooth animation
        diff = target_width - current_width
        step = diff / 5  # Move 1/5th of the distance each step
        
        if abs(step) < 1:
            step = 1 if diff > 0 else -1
            
        new_width = int(current_width + step)
        
        # Snap to target if close enough
        if (diff > 0 and new_width >= target_width) or (diff < 0 and new_width <= target_width):
            new_width = target_width

        self.vol_slider_container.config(width=new_width)
        
        if new_width != target_width:
            self.vol_anim_job = self.root.after(10, lambda: self.animate_volume_width(target_width))


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
        self.possible_click = True # Assume it's a click until moved
    
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
            self.possible_click = False # It's definitely a drag now
            
            # Switch to system dragging for smooth performance (prevents ghosting)
            from ctypes import windll
            self.root.update_idletasks()
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            windll.user32.ReleaseCapture()
            windll.user32.PostMessageW(hwnd, 0xA1, 2, 0)
    
    def stop_drag(self, event):
        """Stop window drag when user releases mouse button."""
        # Don't process in fullscreen mode
        if self.is_fullscreen:
            return
            
        # If it was a possible click (didn't drag far enough), trigger click handler
        if self.possible_click:
            self.handle_click()
            
        # Reset drag state
        self.is_dragging = False
        self.possible_click = False

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
        self.menu_separator.pack_forget()

        # Hide Custom Title Bar
        if hasattr(self, 'title_bar'):
            self.title_bar.pack_forget()
            
        # Remove Content Frame Padding (for true fullscreen)
        if hasattr(self, 'content_frame'):
            self.content_frame.pack_configure(padx=0, pady=0)
        
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
        
        # Restore menu bar only if it was visible before fullscreen
        if self.menu_visible:
            self.menu_bar.pack(side=tk.TOP, fill=tk.X, before=self.main_container)
            self.menu_separator.pack(side=tk.TOP, fill=tk.X, before=self.main_container)
        
        # Restore Custom Title Bar (Packed First)
        if hasattr(self, 'title_bar'):
             self.title_bar.pack(side=tk.TOP, fill=tk.X, before=self.content_frame, padx=1, pady=(1, 0))
             
        # Restore Content Frame Padding
        if hasattr(self, 'content_frame'):
            self.content_frame.pack_configure(padx=1, pady=(0, 1))

        # Restore panels if they were enabled
        if self.show_config:
            self.config_panel.pack(fill=tk.X, side=tk.TOP, before=self.video_frame, padx=4, pady=4)
            
        if self.show_history:
            self.history_panel.pack(side=tk.BOTTOM, fill=tk.X)
            
        # Re-apply custom window styles (remove default title bar again)
        # Tkinter often resets this when toggling fullscreen/state
        self.root.after(100, self.setup_custom_window)

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

    def show_shortcuts_dialog(self):
        """Display keyboard shortcuts dialog"""
        dialog = tk.Toplevel(self.root)
        
        # Apply custom style
        # Apply custom style
        apply_custom_window_style(dialog, enable_resize=False)
            
        dialog.configure(bg=COLORS['border']) # Border color
        
        # Custom Title Bar for Dialog
        title_bar = CustomTitleBar(dialog, title="Keyboard Shortcuts")
        title_bar.min_btn.pack_forget() # No minimize for modal
        title_bar.max_btn.pack_forget() # No maximize for modal
        title_bar.pack(side=tk.TOP, fill=tk.X, padx=1, pady=0)
        dialog.bind("<<CloseRequest>>", lambda e: dialog.destroy()) # Bind close
        
        # Content Frame
        content_frame = tk.Frame(dialog, bg=COLORS['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))
        
        # Make it modal
        dialog.lift()   # Replaces transient to avoid freeze with overrideredirect
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header = tk.Frame(content_frame, bg=COLORS['header_bg']) # Changed dialog -> content_frame
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="⌨️ Keyboard Shortcuts", bg=COLORS['header_bg'], fg=COLORS['text'],
                font=('Segoe UI', 12, 'bold')).pack(pady=15, padx=20, anchor=tk.W)
        
        # Shortcuts list
        shortcuts_frame = tk.Frame(content_frame, bg=COLORS['bg']) # Changed dialog -> content_frame
        shortcuts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        shortcuts = [
            ("Playback", ""),
            ("Space", "Play / Pause"),
            ("→ (Right Arrow)", "Skip Forward 10 seconds"),
            ("← (Left Arrow)", "Skip Backward 10 seconds"),
            ("", ""),
            ("View", ""),
            ("F", "Toggle Fullscreen"),
            ("Escape", "Exit Fullscreen"),
            ("H", "Toggle History Panel"),
            ("", ""),
            ("Video Controls", ""),
            ("Single Click", "Play / Pause (on video)"),
            ("Double Click", "Toggle Fullscreen (on video)"),
            ("", ""),
            ("Other", ""),
            ("Ctrl+O", "Open Stream URL Dialog"),
            ("F1", "Show Keyboard Shortcuts"),
        ]
        
        for key, action in shortcuts:
            row = tk.Frame(shortcuts_frame, bg=COLORS['bg'])
            row.pack(fill=tk.X, pady=2)
            
            if not action:  # Category header
                if key:  # Skip empty rows
                    tk.Label(row, text=key, bg=COLORS['bg'], fg=COLORS['accent'],
                            font=('Segoe UI', 10, 'bold'), anchor=tk.W).pack(side=tk.LEFT)
            else:
                # Key
                key_label = tk.Label(row, text=key, bg=COLORS['button_bg'], fg=COLORS['text'],
                                    font=('Consolas', 9), width=20, anchor=tk.W, padx=8, pady=4)
                key_label.pack(side=tk.LEFT, padx=(0, 10))
                
                # Action
                tk.Label(row, text=action, bg=COLORS['bg'], fg=COLORS['text_gray'],
                        font=('Segoe UI', 9), anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        

        
        # Bind Escape to close
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
    def show_about_dialog(self):
        """Display about dialog"""
        dialog = tk.Toplevel(self.root)
        
        # Apply custom style
        # Apply custom style
        apply_custom_window_style(dialog, enable_resize=False)
            
        dialog.configure(bg=COLORS['border'])
        
        # Custom Title Bar for Dialog
        title_bar = CustomTitleBar(dialog, title="About")
        title_bar.min_btn.pack_forget()
        title_bar.max_btn.pack_forget()
        title_bar.pack(side=tk.TOP, fill=tk.X, padx=1, pady=0)
        dialog.bind("<<CloseRequest>>", lambda e: dialog.destroy())
        
        # Content Frame
        
        content_frame = tk.Frame(dialog, bg=COLORS['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))

        dialog.geometry("500x360")
        dialog.resizable(False, False)
        
        # Make it modal
        dialog.lift()   # Replaces transient to avoid freeze with overrideredirect
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Content
        content = tk.Frame(content_frame, bg=COLORS['bg']) # Changed dialog -> content_frame
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # App Icon/Title
        tk.Label(content, text="▶", bg=COLORS['bg'], fg=COLORS['accent'],
                font=('Segoe UI', 48)).pack(pady=(0, 10))
        
        tk.Label(content, text="M3U8 Streaming Player", bg=COLORS['bg'], fg=COLORS['text'],
                font=('Segoe UI', 14, 'bold')).pack(pady=(0, 5))
        
        tk.Label(content, text="Version 1.0.0", bg=COLORS['bg'], fg=COLORS['text_gray'],
                font=('Segoe UI', 9)).pack(pady=(0, 20))
        
        tk.Label(content, text="A powerful and modern M3U8 stream player\nwith advanced playback controls.",
                bg=COLORS['bg'], fg=COLORS['text_gray'],
                font=('Segoe UI', 9), justify=tk.CENTER).pack(pady=(0, 20))
        

        
        # Bind Escape to close
        dialog.bind("<Escape>", lambda e: dialog.destroy())

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
