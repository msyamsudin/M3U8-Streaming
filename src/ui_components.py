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
    def __init__(self, parent, size=50, color="white", bg_color="black"):
        self.parent = parent
        self.size = size
        self.color = color
        self.bg_color = bg_color # Kept for compatibility, but we'll use a chroma key
        self.window = None
        self.canvas = None
        self.angle = 0
        self.is_spinning = False
        self.timer_id = None
        self.chroma_key = "#add123" # Distinct color for transparency

    def draw(self):
        if not self.canvas: return
        
        self.canvas.delete("all")
        w = self.size
        h = self.size
        
        start = self.angle
        extent = 60
        
        # Draw arcs with thicker width
        self.canvas.create_arc(5, 5, w-5, h-5, start=start, extent=extent, 
                              outline=self.color, width=4, style="arc")
        self.canvas.create_arc(5, 5, w-5, h-5, start=start+180, extent=extent, 
                              outline=self.color, width=4, style="arc")

    def spin(self):
        if self.is_spinning and self.canvas:
            self.angle = (self.angle + 20) % 360
            self.draw()
            self.timer_id = self.parent.after(50, self.spin)

    def start(self):
        if not self.is_spinning:
            self.is_spinning = True
            
            # Create Toplevel for transparency
            self.window = tk.Toplevel(self.parent)
            self.window.overrideredirect(True)
            self.window.attributes('-topmost', True)
            
            # Set transparency
            try:
                self.window.config(bg=self.chroma_key)
                self.window.wm_attributes('-transparentcolor', self.chroma_key)
            except:
                # Fallback for non-Windows or if transparency fails
                self.window.config(bg=self.bg_color)
            
            # Calculate position (Center of parent)
            self.update_position()
            
            # Bind to parent configure to update position
            self.parent.bind('<Configure>', self.update_position, add="+")
            
            self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, 
                                   bg=self.chroma_key, highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            self.spin()

    def update_position(self, event=None):
        if self.window and self.parent.winfo_exists():
            try:
                x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (self.size // 2)
                y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (self.size // 2)
                self.window.geometry(f"+{x}+{y}")
                self.window.lift()
            except: pass

    def stop(self):
        self.is_spinning = False
        if self.timer_id:
            self.parent.after_cancel(self.timer_id)
            self.timer_id = None
        
        if self.window:
            self.window.destroy()
            self.window = None
            self.canvas = None
            # Unbind is tricky because we used add="+", but since we destroy the window, 
            # the update_position check for self.window will fail gracefully.
            # Ideally we should unbind, but Tkinter doesn't make it easy to unbind specific functions.

class BufferedScale(tk.Canvas):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.command = command
        self.progress = 0.0  # 0 to 100
        self.buffer = 0.0    # 0 to 100
        
        self.config(bg=COLORS['control_bg'], highlightthickness=0, height=15)
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
        
        # Background track
        self.create_rectangle(0, cy-2, w, cy+2, fill=COLORS['seekbar_bg'], outline="")
        
        # Buffer track
        if self.buffer > 0:
            bw = (self.buffer / 100) * w
            self.create_rectangle(0, cy-2, bw, cy+2, fill=COLORS['text_gray'], outline="")
            
        # Progress track
        if self.progress > 0:
            pw = (self.progress / 100) * w
            self.create_rectangle(0, cy-2, pw, cy+2, fill=COLORS['accent'], outline="")
            
            # Thumb
            self.create_oval(pw-6, cy-6, pw+6, cy+6, fill=COLORS['text'], outline=COLORS['accent'])

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
