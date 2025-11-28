import tkinter as tk
from .config import COLORS

class StyledButton(tk.Button):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.config(
            bg=COLORS['button_bg'],
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
            self['bg'] = COLORS['button_bg']

class PrimaryButton(StyledButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Use colors from config
        self.bg_normal = COLORS.get('load_btn_bg', '#007ACC')
        self.bg_hover = COLORS.get('load_btn_hover', '#0098FF')
        self.bg_active = COLORS.get('load_btn_active', '#005FA3')
        
        self.config(
            bg=self.bg_normal,
            fg=COLORS.get('load_btn_fg', '#ffffff'),
            activebackground=self.bg_active,
            activeforeground=COLORS.get('load_btn_fg', '#ffffff')
        )
        
    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.bg_hover

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.bg_normal

class HistoryPanel(tk.Frame):
    def __init__(self, master, load_callback, delete_callback, clear_callback):
        super().__init__(master, bg=COLORS['bg'])
        self.load_callback = load_callback
        self.delete_callback = delete_callback
        self.clear_callback = clear_callback
        
        # Header
        header = tk.Frame(self, bg=COLORS['header_bg'])
        header.pack(fill=tk.X)
        
        tk.Label(header, text="History", bg=COLORS['header_bg'], fg=COLORS['text'], font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5, pady=2)
        
        StyledButton(header, text="Clear All", command=self.clear_callback, font=('Segoe UI', 8)).pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Listbox with Scrollbar
        list_frame = tk.Frame(self, bg=COLORS['bg'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, bg=COLORS['list_bg'], fg=COLORS['text'],
                                 selectbackground=COLORS['button_active'], selectforeground=COLORS['text'],
                                 relief=tk.FLAT, bd=0, yscrollcommand=self.scrollbar.set,
                                 font=('Segoe UI', 9))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.listbox.yview)
        
        # Bindings
        self.listbox.bind('<Double-Button-1>', self.on_double_click)
        self.listbox.bind('<Delete>', self.on_delete_key)
        
    def update_history(self, history_items):
        self.listbox.delete(0, tk.END)
        for item in history_items:
            name = item.get('title') or item['url']
            if len(name) > 80: name = name[:77] + "..."
            self.listbox.insert(tk.END, f" {name}")
            
    def on_double_click(self, event):
        selection = self.listbox.curselection()
        if selection:
            # Get full URL from history data (not just the display text)
            # This requires the parent to handle the mapping, but for now we assume the index matches
            # A better way is to pass the full history list to this component
            from .utils import load_history # Import here to avoid circular dependency if possible, or pass data
            history = load_history()
            if 0 <= selection[0] < len(history):
                url = history[selection[0]]['url']
                self.load_callback(url)

    def on_delete_key(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            self.delete_callback(index)

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
        
        # Track dimensions
        track_h = 8
        y1 = cy - (track_h / 2)
        y2 = cy + (track_h / 2)
        
        # Background track (Rounded)
        self.create_rectangle(0, y1, w, y2, fill=COLORS['seekbar_bg'], outline="", tags="track")
        # Add rounded caps for background? Simple rectangle is fine for now or we can use a line with capstyle
        
        # Buffer track
        if self.buffer > 0:
            bw = (self.buffer / 100) * w
            self.create_rectangle(0, y1, bw, y2, fill=COLORS['text_gray'], outline="")
            
        # Progress track
        if self.progress > 0:
            pw = (self.progress / 100) * w
            self.create_rectangle(0, y1, pw, y2, fill=COLORS['accent'], outline="")
            
            # Thumb (Vertical Pill)
            thumb_w = 6
            thumb_h = 16
            tx1 = pw - (thumb_w / 2)
            tx2 = pw + (thumb_w / 2)
            ty1 = cy - (thumb_h / 2)
            ty2 = cy + (thumb_h / 2)
            
            # Ensure thumb stays within bounds visually if needed, but centering on progress is standard
            self.create_rectangle(tx1, ty1, tx2, ty2, fill=COLORS['text'], outline=COLORS['accent'], width=1)

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
