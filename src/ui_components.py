import tkinter as tk
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
    def __init__(self, parent, size=60, color="white", bg_color="black", root_window=None):
        self.parent = parent
        self.root_window = root_window  # Main window for state tracking
        self.size = size
        self.color = "white" # Force white as per reference
        self.bg_color = bg_color
        self.window = None
        self.dimmer = None
        self.canvas = None
        self.angle = 0
        self.is_spinning = False
        self.timer_id = None
        self.chroma_key = "#add123"
        self.windows_hidden = False  # Track if windows are hidden due to minimize
        self.state_check_id = None  # Timer for state polling

    def draw(self):
        if not self.canvas: return
        
        self.canvas.delete("all")
        w = self.size
        h = self.size
        
        start = self.angle
        extent = 90 # Shorter arc for a cleaner look
        
        # Draw single thin white arc
        self.canvas.create_arc(4, 4, w-4, h-4, start=start, extent=extent, 
                              outline=self.color, width=3, style="arc")

    def spin(self):
        if self.is_spinning and self.canvas:
            self.angle = (self.angle - 15) % 360 # Counter-clockwise or Clockwise? Let's go Clockwise (negative)
            self.draw()
            self.timer_id = self.parent.after(30, self.spin) # Faster smooth animation

    def start(self):
        if not self.is_spinning:
            self.is_spinning = True
            
            # 1. Create Dimmer (Dark Overlay)
            self.dimmer = tk.Toplevel(self.parent)
            self.dimmer.overrideredirect(True)
            self.dimmer.config(bg='black')
            self.dimmer.attributes('-alpha', 0.5) # 50% opacity
            
            # 2. Create Spinner Window (Transparent)
            self.window = tk.Toplevel(self.parent)
            self.window.overrideredirect(True)
            # Don't use topmost - let it follow parent window's z-order
            
            # Set transparency for spinner
            try:
                self.window.config(bg=self.chroma_key)
                self.window.wm_attributes('-transparentcolor', self.chroma_key)
            except:
                self.window.config(bg=self.bg_color)
            
            # Calculate position
            self.update_position()
            
            # Bind to parent configure
            self.parent.bind('<Configure>', self.update_position, add="+")
            
            self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, 
                                   bg=self.chroma_key, highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Start window state polling
            if self.root_window:
                self.check_window_state()
            
            self.spin()

    def update_position(self, event=None):
        if self.parent.winfo_exists():
            try:
                # Parent geometry
                px = self.parent.winfo_rootx()
                py = self.parent.winfo_rooty()
                pw = self.parent.winfo_width()
                ph = self.parent.winfo_height()
                
                # Update Dimmer
                if self.dimmer:
                    self.dimmer.geometry(f"{pw}x{ph}+{px}+{py}")
                    self.dimmer.lift()
                
                # Update Spinner
                if self.window:
                    x = px + (pw // 2) - (self.size // 2)
                    y = py + (ph // 2) - (self.size // 2)
                    self.window.geometry(f"+{x}+{y}")
                    self.window.lift()
            except: pass

    def stop(self):
        self.is_spinning = False
        if self.timer_id:
            self.parent.after_cancel(self.timer_id)
            self.timer_id = None
        
        # Stop state polling
        if self.state_check_id:
            self.parent.after_cancel(self.state_check_id)
            self.state_check_id = None
        
        if self.window:
            self.window.destroy()
            self.window = None
            self.canvas = None
            
        if self.dimmer:
            self.dimmer.destroy()
            self.dimmer = None

    def check_window_state(self):
        """Periodically check if window is minimized or unfocused and hide/show spinner accordingly"""
        if not self.is_spinning or not self.root_window:
            return
        
        try:
            # Check if window is minimized (iconic state)
            is_minimized = self.root_window.state() == 'iconic'
            
            # Check if window has focus (is active)
            has_focus = self.root_window.focus_displayof() is not None
            
            # Hide spinner if minimized OR window doesn't have focus
            should_hide = is_minimized or not has_focus
            
            if should_hide and not self.windows_hidden:
                # Window minimized or lost focus - hide spinner
                if self.window and self.dimmer:
                    self.window.withdraw()
                    self.dimmer.withdraw()
                    self.windows_hidden = True
            elif not should_hide and self.windows_hidden:
                # Window restored and has focus - show spinner
                if self.window and self.dimmer:
                    self.dimmer.deiconify()
                    self.window.deiconify()
                    self.update_position()
                    self.windows_hidden = False
        except:
            pass
        
        # Continue polling every 200ms
        if self.is_spinning:
            self.state_check_id = self.parent.after(200, self.check_window_state)

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
        
        # Background track
        self.create_rectangle(0, y1, w, y2, fill=COLORS['seekbar_bg'], outline="", tags="track")
        
        # Buffer track
        if self.buffer > 0:
            bw = (self.buffer / 100) * w
            self.create_rectangle(0, y1, bw, y2, fill=COLORS['text_gray'], outline="")
            
        # Progress track
        if self.progress > 0:
            pw = (self.progress / 100) * w
            self.create_rectangle(0, y1, pw, y2, fill=COLORS['accent'], outline="")
            
            # Thumb (Circle)
            radius = 6
            tx1 = pw - radius
            tx2 = pw + radius
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
        if w > 0:
            x = max(0, min(w, event.x))
            self.progress = (x / w) * 100
            self.draw()
            # Optional: Call command while dragging for live seek
            # if self.command: self.command(self.progress)
