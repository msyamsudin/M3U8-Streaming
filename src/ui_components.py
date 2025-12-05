import tkinter as tk
import os
from .config import COLORS

class StyledButton(tk.Button):
    def __init__(self, master, bg_color=None, **kwargs):
        super().__init__(master, **kwargs)
        self.default_bg = bg_color if bg_color else COLORS['control_bg']
        self.config(
            bg=self.default_bg,
            fg=COLORS['text'],
            activebackground=COLORS['button_active'],
            activeforeground=COLORS['text'],
            relief=tk.FLAT,
            bd=0,
            cursor='hand2'
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = COLORS['button_hover']

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.default_bg

class TitleBarButton(tk.Button):
    def __init__(self, master, text="", command=None, bg_color=None, hover_color=None, **kwargs):
        super().__init__(master, text=text, command=command, **kwargs)
        self.default_bg = bg_color if bg_color else COLORS['bg']
        self.hover_bg = hover_color if hover_color else COLORS['button_hover']
        self.config(
            bg=self.default_bg,
            fg=COLORS['text'],
            activebackground=self.hover_bg,
            activeforeground=COLORS['text'],
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            font=('Segoe UI', 10),
            width=5
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def on_enter(self, e):
        self['bg'] = self.hover_bg

    def on_leave(self, e):
        self['bg'] = self.default_bg

class CustomTitleBar(tk.Frame):
    def __init__(self, master, title="M3U8 Player", **kwargs):
        super().__init__(master, bg=COLORS['bg'], height=30, **kwargs)
        self.pack_propagate(False)
        self.master = master
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Title Icon (optional, just a symbol)
        self.icon_label = tk.Label(self, text="▶", bg=COLORS['bg'], fg=COLORS['accent'], font=('Segoe UI', 10, 'bold'))
        self.icon_label.pack(side=tk.LEFT, padx=(10, 5))

        # Title Text
        self.title_label = tk.Label(self, text=title, bg=COLORS['bg'], fg=COLORS['text'], font=('Segoe UI', 9))
        self.title_label.pack(side=tk.LEFT, padx=5)

        # Window Controls
        self.close_btn = TitleBarButton(self, text="✕", command=self.close_window, hover_color="#ff4444")
        self.close_btn.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.max_btn = TitleBarButton(self, text="▢", command=self.maximize_restore_window)
        self.max_btn.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.min_btn = TitleBarButton(self, text="—", command=self.minimize_window)
        self.min_btn.pack(side=tk.RIGHT, fill=tk.Y)

        # Bindings for Dragging
        self.bind('<Button-1>', self.start_drag)
        self.bind('<B1-Motion>', self.do_drag)
        self.bind('<Double-Button-1>', self.maximize_restore_window)
        
        # Bind children to propagate drag (except buttons)
        for widget in [self.icon_label, self.title_label]:
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.do_drag)
            widget.bind('<Double-Button-1>', self.maximize_restore_window)

    def start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def do_drag(self, event):
        if self.master.state() == 'zoomed':
            return
            
        # Add a small threshold to discern click from drag
        if abs(event.x - self._drag_start_x) > 5 or abs(event.y - self._drag_start_y) > 5:
            from ctypes import windll
            self.master.update_idletasks()
            hwnd = windll.user32.GetParent(self.master.winfo_id())
            windll.user32.ReleaseCapture()
            windll.user32.PostMessageW(hwnd, 0xA1, 2, 0)

    def maximize_restore_window(self, event=None):
        if self.master.state() == 'zoomed':
            self.master.state('normal')
            self.max_btn.config(text="▢")
        else:
            self.master.state('zoomed')
            self.max_btn.config(text="❐")

    def minimize_window(self):
        self.master.state('iconic')

    def close_window(self):
        self.master.event_generate("<<CloseRequest>>") # Decouple


class RoundedButton(tk.Canvas):
    def __init__(self, master, text="", command=None, width=120, height=35, corner_radius=10, 
                 bg="white", fg="black", hover_bg="#eeeeee", active_bg="#cccccc", **kwargs):
        super().__init__(master, width=width, height=height, bg=master['bg'], highlightthickness=0, **kwargs)
        
        self.command = command
        self.text = text
        self.corner_radius = corner_radius
        self.bg_normal = bg
        self.fg_normal = fg
        self.bg_hover = hover_bg
        self.bg_active = active_bg
        
        self.current_bg = self.bg_normal
        self.is_pressed = False
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = int(self['width'])
        h = int(self['height'])
        r = self.corner_radius
        
        # Draw rounded rectangle
        self.create_rounded_rect(0, 0, w, h, r, fill=self.current_bg, outline="")
        
        # Draw text
        self.create_text(w/2, h/2, text=self.text, fill=self.fg_normal, font=('Segoe UI', 10, 'bold'))
        
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1,
            x1+r, y1,
            x2-r, y1,
            x2-r, y1,
            x2, y1,
            x2, y1+r,
            x2, y1+r,
            x2, y2-r,
            x2, y2-r,
            x2, y2,
            x2-r, y2,
            x2-r, y2,
            x1+r, y2,
            x1+r, y2,
            x1, y2,
            x1, y2-r,
            x1, y2-r,
            x1, y1+r,
            x1, y1+r,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def on_enter(self, e):
        self.current_bg = self.bg_hover
        self.draw()

    def on_leave(self, e):
        self.current_bg = self.bg_normal
        self.is_pressed = False
        self.draw()

    def on_press(self, e):
        self.is_pressed = True
        self.current_bg = self.bg_active
        self.draw()

    def on_release(self, e):
        if self.is_pressed:
            self.is_pressed = False
            self.current_bg = self.bg_hover
            self.draw()
            if self.command:
                self.command()

class PrimaryButton(RoundedButton):
    def __init__(self, master, text="", command=None, **kwargs):
        bg_normal = COLORS.get('load_btn_bg', '#007ACC')
        bg_hover = COLORS.get('load_btn_hover', '#0098FF')
        bg_active = COLORS.get('load_btn_active', '#005FA3')
        fg = COLORS.get('load_btn_fg', '#ffffff')
        
        super().__init__(master, text=text, command=command, 
                        bg=bg_normal, fg=fg, hover_bg=bg_hover, active_bg=bg_active,
                        width=120, height=32, corner_radius=16, **kwargs)

from .utils import extract_expiration, get_remaining_time

from .utils import extract_expiration, get_remaining_time, get_status_color
import tkinter.ttk as ttk

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=kwargs.get('bg', 'black'), highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get('bg', 'black'))

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Mousewheel scrolling
        self.bind_mouse_scroll(self.canvas)
        self.bind_mouse_scroll(self.scrollable_frame)

    def on_canvas_configure(self, event):
        # Resize the inner frame to match the canvas width
        self.canvas.itemconfig("frame", width=event.width)

    def bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

class HistoryItemRow(tk.Frame):
    def __init__(self, master, item_data, load_callback, delete_callback, index, **kwargs):
        bg_color = kwargs.get('bg', COLORS['bg'])
        super().__init__(master, **kwargs)
        self.item_data = item_data
        self.load_callback = load_callback
        self.delete_callback = delete_callback
        self.index = index
        self.default_bg = bg_color
        self.hover_bg = COLORS.get('button_hover', '#333333')
        
        self.config(bg=self.default_bg, pady=8, padx=10)
        
        # Extract data
        url = item_data.get('url', '')
        name = item_data.get('title') or url
        if len(name) > 60: name = name[:57] + "..."
        
        exp_timestamp = extract_expiration(url)
        remaining = get_remaining_time(exp_timestamp)
        status_color = get_status_color(exp_timestamp) or COLORS['accent']
        
        # 1. Status Dot (Canvas)
        self.dot_canvas = tk.Canvas(self, width=10, height=10, bg=self.default_bg, highlightthickness=0)
        self.dot_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self.dot_canvas.create_oval(2, 2, 8, 8, fill=status_color, outline="")
        
        # 2. Title/URL
        self.lbl_title = tk.Label(self, text=name, bg=self.default_bg, fg=COLORS['text'], 
                                 font=('Segoe UI', 9), anchor="w")
        self.lbl_title.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 3. Right Side Container (Time + Actions)
        self.right_frame = tk.Frame(self, bg=self.default_bg)
        self.right_frame.pack(side=tk.RIGHT)
        
        # Time Label
        time_text = remaining if remaining else ""
        time_fg = status_color if remaining != "Expired" else "#666666"
        self.lbl_time = tk.Label(self.right_frame, text=time_text, bg=self.default_bg, fg=time_fg,
                                font=('Segoe UI', 9))
        self.lbl_time.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Actions Frame (Hidden by default)
        self.actions_frame = tk.Frame(self.right_frame, bg=self.default_bg)
        # Don't pack initially
        
        # Copy Button
        self.btn_copy = tk.Label(self.actions_frame, text="❐", bg=self.default_bg, fg=COLORS['text_gray'],
                                cursor="hand2", font=('Segoe UI', 10))
        self.btn_copy.pack(side=tk.LEFT, padx=5)
        self.btn_copy.bind("<Button-1>", self.copy_to_clipboard)
        
        # Delete Button
        self.btn_delete = tk.Label(self.actions_frame, text="🗑", bg=self.default_bg, fg=COLORS['text_gray'],
                                  cursor="hand2", font=('Segoe UI', 10))
        self.btn_delete.pack(side=tk.LEFT, padx=5)
        self.btn_delete.bind("<Button-1>", lambda e: self.delete_callback(self.index))
        
        # Bindings for Hover
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # Bind children to propagate hover
        for widget in [self.lbl_title, self.lbl_time, self.right_frame, self.dot_canvas]:
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)
            
        # Click to load
        self.bind("<Button-1>", lambda e: self.load_callback(url))
        self.lbl_title.bind("<Button-1>", lambda e: self.load_callback(url))
        self.dot_canvas.bind("<Button-1>", lambda e: self.load_callback(url))

    def on_enter(self, event):
        self.config(bg=self.hover_bg)
        self.lbl_title.config(bg=self.hover_bg)
        self.lbl_time.config(bg=self.hover_bg)
        self.right_frame.config(bg=self.hover_bg)
        self.actions_frame.config(bg=self.hover_bg)
        self.btn_copy.config(bg=self.hover_bg)
        self.btn_delete.config(bg=self.hover_bg)
        self.dot_canvas.config(bg=self.hover_bg)
        
        # Show actions, hide time (or show both? Image shows time AND actions)
        # Image shows: [Title] ... [Time] [Copy] [Delete]
        # So we pack actions to the LEFT of time, or just pack them in right_frame
        
        # Re-pack logic for right frame
        self.lbl_time.pack_forget()
        self.actions_frame.pack(side=tk.RIGHT, padx=(10, 0))
        self.lbl_time.pack(side=tk.RIGHT, padx=(10, 0))

    def on_leave(self, event):
        # Check if mouse is still inside the widget
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        width = self.winfo_width()
        height = self.winfo_height()
        
        if not (widget_x <= x <= widget_x + width and widget_y <= y <= widget_y + height):
            self.config(bg=self.default_bg)
            self.lbl_title.config(bg=self.default_bg)
            self.lbl_time.config(bg=self.default_bg)
            self.right_frame.config(bg=self.default_bg)
            self.actions_frame.config(bg=self.default_bg)
            self.btn_copy.config(bg=self.default_bg)
            self.btn_delete.config(bg=self.default_bg)
            self.dot_canvas.config(bg=self.default_bg)
            
            self.actions_frame.pack_forget()
            
    def copy_to_clipboard(self, event):
        self.clipboard_clear()
        self.clipboard_append(self.item_data.get('url', ''))
        # Optional: Flash feedback

class HistoryPanel(tk.Frame):
    def __init__(self, master, load_callback, delete_callback, clear_callback):
        super().__init__(master, bg=COLORS['bg'])
        self.load_callback = load_callback
        self.delete_callback = delete_callback
        self.clear_callback = clear_callback
        
        # Header
        header = tk.Frame(self, bg=COLORS['header_bg'])
        header.pack(fill=tk.X)
        
        tk.Label(header, text="History", bg=COLORS['header_bg'], fg=COLORS['text'], font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=10, pady=8)
        
        StyledButton(header, text="Clear All", command=self.clear_callback, font=('Segoe UI', 8)).pack(side=tk.RIGHT, padx=10, pady=8)
        
        # Separator
        tk.Frame(self, bg="#333333", height=1).pack(fill=tk.X)
        
        # Scrollable List
        self.list_container = ScrollableFrame(self, bg=COLORS['bg'])
        self.list_container.pack(fill=tk.BOTH, expand=True)
        
    def update_history(self, history_items):
        # Clear existing items
        for widget in self.list_container.scrollable_frame.winfo_children():
            widget.destroy()
            
        # Populate
        for i, item in enumerate(history_items):
            row = HistoryItemRow(self.list_container.scrollable_frame, item, 
                               self.load_callback, self.delete_callback, i,
                               bg=COLORS['bg'])
            row.pack(fill=tk.X, expand=True)
            # Bind mouse scroll to row and its children
            self.list_container.bind_mouse_scroll(row)
            self.list_container.bind_mouse_scroll(row.lbl_title)
            self.list_container.bind_mouse_scroll(row.right_frame)
            self.list_container.bind_mouse_scroll(row.lbl_time)

class LoadingSpinner:
    """
    Transparent rotating arc spinner using Toplevel overlay.
    Arc floats directly over video with no visible background.
    """
    def __init__(self, parent, size=60, color="white", bg_color="black", root_window=None):
        self.parent = parent
        self.size = size
        self.angle = 0
        self.is_spinning = False
        self.timer_id = None
        self.window = None
        self.canvas = None
        self.chroma_key = "#010101"  # Color to make transparent
        
    def _draw(self):
        """Draw the thin rotating arc."""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        w = self.size
        h = self.size
        padding = 6
        
        # Draw shadow arc (for visibility on light video)
        self.canvas.create_arc(
            padding + 2, padding + 2, w - padding + 2, h - padding + 2,
            start=self.angle, extent=90,
            outline='#222222', width=4, style="arc"
        )
        
        # Draw main white arc
        self.canvas.create_arc(
            padding, padding, w - padding, h - padding,
            start=self.angle, extent=90,
            outline='white', width=3, style="arc"
        )
    
    def _spin(self):
        """Animation loop."""
        if self.is_spinning and self.window:
            self.angle = (self.angle - 10) % 360
            self._draw()
            self._update_position()
            self.timer_id = self.parent.after(20, self._spin)
    
    def _update_position(self):
        """Keep spinner centered on parent."""
        if not self.window or not self.parent.winfo_exists():
            return
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw // 2) - (self.size // 2)
            y = py + (ph // 2) - (self.size // 2)
            self.window.geometry(f"{self.size}x{self.size}+{x}+{y}")
        except:
            pass
    
    def start(self):
        """Show transparent spinner overlay."""
        if self.is_spinning:
            return
            
        self.is_spinning = True
        self.angle = 0
        
        # Create transparent overlay window
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.config(bg=self.chroma_key)
        
        # Make chroma key color transparent (Windows)
        try:
            self.window.wm_attributes('-transparentcolor', self.chroma_key)
        except:
            pass
        
        # Create canvas
        self.canvas = tk.Canvas(self.window, width=self.size, height=self.size,
                               bg=self.chroma_key, highlightthickness=0)
        self.canvas.pack()
        
        self._update_position()
        self._spin()
    
    def stop(self):
        """Hide spinner."""
        self.is_spinning = False
        
        if self.timer_id:
            try:
                self.parent.after_cancel(self.timer_id)
            except:
                pass
            self.timer_id = None
        
        if self.window:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None
            self.canvas = None
    
    def destroy(self):
        """Clean up."""
        self.stop()

class BufferedScale(tk.Canvas):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.command = command
        self.progress = 0.0  # 0 to 100
        self.buffer = 0.0    # 0 to 100
        
        self.config(bg=COLORS['control_bg'], highlightthickness=0, height=20)
        self.bind('<Configure>', self.draw)
        self.bind('<Button-1>', self.on_click)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)
        
        self.is_dragging = False

    def set_progress(self, value):
        if not self.is_dragging:
            self.progress = max(0, min(100, value))
            self.draw()

    def set_buffer(self, value):
        self.buffer = max(0, min(100, value))
        self.draw()

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        cy = h / 2
        
        # Track dimensions (Thinner for sleek look)
        track_h = 4
        y1 = cy - (track_h / 2)
        y2 = cy + (track_h / 2)
        
        # Padding for thumb radius
        radius = 6
        padding = radius + 1
        
        # Available width for track
        track_w = w - (padding * 2)
        if track_w < 0: track_w = 0
        
        # Background track
        self.create_rectangle(padding, y1, padding + track_w, y2, fill=COLORS['seekbar_bg'], outline="", tags="track")
        
        # Buffer track
        if self.buffer > 0:
            bw = (self.buffer / 100) * track_w
            self.create_rectangle(padding, y1, padding + bw, y2, fill=COLORS['text_gray'], outline="")
            
        # Progress track
        if self.progress > 0:
            pw = (self.progress / 100) * track_w
            self.create_rectangle(padding, y1, padding + pw, y2, fill=COLORS['accent'], outline="")
            
            # Thumb (Circle)
            tx1 = padding + pw - radius
            tx2 = padding + pw + radius
            ty1 = cy - radius
            ty2 = cy + radius
            
            self.create_oval(tx1, ty1, tx2, ty2, fill='white', outline=COLORS['accent'], width=1)
        else:
            # Draw thumb at 0 position
            tx1 = padding - radius
            tx2 = padding + radius
            ty1 = cy - radius
            ty2 = cy + radius
            self.create_oval(tx1, ty1, tx2, ty2, fill='white', outline=COLORS['accent'], width=1)

    def on_click(self, event):
        self.is_dragging = True
        self.update_from_event(event)

    def on_drag(self, event):
        if self.is_dragging:
            self.update_from_event(event)

    def on_release(self, event):
        self.is_dragging = False
        if self.command:
            self.command(self.progress)

    def update_from_event(self, event):
        w = self.winfo_width()
        radius = 6
        padding = radius + 1
        track_w = w - (padding * 2)
        
        if track_w > 0:
            # Adjust x to be relative to the track start
            x = event.x - padding
            # Clamp x
            x = max(0, min(track_w, x))
            
            self.progress = (x / track_w) * 100
            self.draw()
            # Optional: Call command while dragging for live seek
            # if self.command: self.command(self.progress)

def apply_custom_window_style(window, enable_resize=False):
    """
    Remove Windows title bar.
    - If enable_resize=False (Dialogs): Use overrideredirect(True) for guaranteed removal.
    - If enable_resize=True (Main Window): Use ctypes to remove WS_CAPTION but keep resizing.
    """
    if not enable_resize:
        window.overrideredirect(True)
    
    if os.name == 'nt' and enable_resize:
        try:
            from ctypes import windll
            window.update_idletasks()
            hwnd = windll.user32.GetParent(window.winfo_id())
            # WS_CAPTION = 0x00C00000 -> Remove
            # WS_THICKFRAME = 0x00040000 -> Keep
            # WS_SYSMENU = 0x00080000 -> Keep for taskbar interaction
            style = windll.user32.GetWindowLongW(hwnd, -16) 
            style = (style & ~0x00C00000) | 0x00040000
            windll.user32.SetWindowLongW(hwnd, -16, style)
            windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
        except: pass

class CustomMessagebox(tk.Toplevel):
    def __init__(self, master, title, message, buttons, icon="info"):
        super().__init__(master, bg=COLORS['border']) # Border color backbone
        self.result = None
        
        # Apply style
        apply_custom_window_style(self)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self, title=title)
        self.title_bar.min_btn.pack_forget()
        self.title_bar.max_btn.pack_forget()
        self.title_bar.pack(side=tk.TOP, fill=tk.X, padx=1, pady=0)
        self.bind("<<CloseRequest>>", self.on_cancel)
        
        # Content
        content = tk.Frame(self, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))
        
        # Message Area (Row: Icon + Text)
        msg_frame = tk.Frame(content, bg=COLORS['bg'])
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=25)
        
        # Icon
        icon_char = "ℹ"
        icon_color = COLORS['text']
        if icon == "warning": 
            icon_char = "⚠"
            icon_color = COLORS['status_paused_fg'] # Orange
        elif icon == "error": 
            icon_char = "❌"
            icon_color = COLORS['status_stopped_fg'] # Red
        elif icon == "question":
            icon_char = "?"
            icon_color = COLORS['accent']
            
        tk.Label(msg_frame, text=icon_char, bg=COLORS['bg'], fg=icon_color, 
                 font=('Segoe UI', 32)).pack(side=tk.LEFT, padx=(0, 20), anchor="n")
                 
        tk.Label(msg_frame, text=message, bg=COLORS['bg'], fg=COLORS['text'],
                 font=('Segoe UI', 10), justify=tk.LEFT, wraplength=350).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(content, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        for btn_text in reversed(buttons): # Right align, so pack reversed
            cmd = lambda t=btn_text: self.on_click(t)
            
            # Button Styling
            if btn_text in ["OK", "Yes"]:
                # Primary Style
                btn = RoundedButton(btn_frame, text=btn_text, command=cmd, width=80, height=30,
                                  bg=COLORS['load_btn_bg'], hover_bg=COLORS['load_btn_hover'], 
                                  active_bg=COLORS['load_btn_active'], fg=COLORS['load_btn_fg'])
            else:
                # Secondary Style
                btn = RoundedButton(btn_frame, text=btn_text, command=cmd, width=80, height=30,
                                  bg=COLORS['button_bg'], hover_bg=COLORS['button_hover'],
                                  active_bg=COLORS['button_active'], fg=COLORS['text'])
            
            btn.pack(side=tk.RIGHT, padx=5)

        # Modal Setup
        self.lift()
        self.grab_set()
        
        # Center
        self.update_idletasks()
        w = max(400, self.winfo_width())
        h = max(180, self.winfo_height())
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        
    def on_click(self, value):
        self.result = value
        self.destroy()
        
    def on_cancel(self, event=None):
        self.result = None 
        self.destroy()

def show_custom_error(master, title, message):
    d = CustomMessagebox(master, title, message, buttons=["OK"], icon="error")
    master.wait_window(d)
    return d.result

def show_custom_warning(master, title, message):
    d = CustomMessagebox(master, title, message, buttons=["OK"], icon="warning")
    master.wait_window(d)
    return d.result

def show_custom_info(master, title, message):
    d = CustomMessagebox(master, title, message, buttons=["OK"], icon="info")
    master.wait_window(d)
    return d.result

def ask_custom_yes_no(master, title, message):
    d = CustomMessagebox(master, title, message, buttons=["Yes", "No"], icon="question")
    master.wait_window(d)
    return d.result == "Yes"
