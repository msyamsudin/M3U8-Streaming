import tkinter as tk
from tkinter import ttk
from .config import COLORS

class StyledButton(tk.Button):
    def __init__(self, master, **kwargs):
        config = {
            'bg': COLORS['button_bg'],
            'fg': COLORS['text'],
            'relief': tk.FLAT,
            'bd': 0,
            'padx': 12,
            'pady': 6,
            'cursor': 'hand2',
            'font': ('Segoe UI', 9),
            'activebackground': COLORS['button_hover'],
            'activeforeground': COLORS['text']
        }
        config.update(kwargs)
        super().__init__(master, **config)

class HistoryPanel(tk.Frame):
    def __init__(self, master, on_play_callback, on_delete_callback, on_clear_callback, **kwargs):
        super().__init__(master, bg=COLORS['bg'], **kwargs)
        self.on_play_callback = on_play_callback
        self.on_delete_callback = on_delete_callback
        self.on_clear_callback = on_clear_callback
        
        # Header
        header = tk.Frame(self, bg=COLORS['menu_bg'])
        header.pack(fill=tk.X)
        tk.Label(header, text="History", bg=COLORS['menu_bg'], fg=COLORS['text'],
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=10, pady=5)
        
        # Listbox with scrollbar
        list_frame = tk.Frame(self, bg=COLORS['bg'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.listbox = tk.Listbox(list_frame, bg=COLORS['entry_bg'], fg=COLORS['text'],
                                  selectbackground=COLORS['button_active'],
                                  selectforeground=COLORS['text'],
                                  relief=tk.FLAT, bd=0, highlightthickness=0)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.bind('<Double-Button-1>', self._on_double_click)
        self.listbox.bind('<Return>', self._on_double_click)
        
        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, pady=5, padx=5)
        
        StyledButton(btn_frame, text="Delete", command=self._on_delete_btn).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        StyledButton(btn_frame, text="Clear All", command=self._on_clear_btn).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        self.history_data = []

    def update_history(self, history_list):
        self.history_data = history_list
        self.listbox.delete(0, tk.END)
        for item in history_list:
            # Display name if available, else URL
            display = item.get('name') or item.get('url')
            self.listbox.insert(tk.END, f"• {display}")

    def _on_double_click(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.history_data):
                url = self.history_data[index]['url']
                self.on_play_callback(url)

    def _on_delete_btn(self):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            self.on_delete_callback(index)

    def _on_clear_btn(self):
        self.on_clear_callback()

import math

class LoadingSpinner:
    def __init__(self, master, size=50, color='#00FF00', bg_color=None, **kwargs):
        self.master = master
        self.size = size
        self.color = color
        self.is_spinning = False
        self.timer_id = None
        self.window = None
        self.canvas = None
        self.arc = None
        self.angle = 0
        
        # Transparency key
        self.trans_color = '#ff00ff' # Magenta

    def start(self):
        if not self.is_spinning:
            self.is_spinning = True
            self._create_window()
            self._animate()
            
            # Bind to master events
            self.bind_id_config = self.master.bind('<Configure>', self._update_position, add="+")
            self.bind_id_map = self.master.bind('<Map>', self._on_master_map, add="+")
            self.bind_id_unmap = self.master.bind('<Unmap>', self._on_master_unmap, add="+")

    def stop(self):
        self.is_spinning = False
        if self.timer_id:
            self.master.after_cancel(self.timer_id)
            self.timer_id = None
        
        if self.window:
            self.window.destroy()
            self.window = None
            
        # Unbind
        for attr in ['bind_id_config', 'bind_id_map', 'bind_id_unmap']:
            if hasattr(self, attr):
                try:
                    event = {'bind_id_config': '<Configure>', 'bind_id_map': '<Map>', 'bind_id_unmap': '<Unmap>'}[attr]
                    self.master.unbind(event, getattr(self, attr))
                except: pass

    def _create_window(self):
        if self.window: return
        
        self.window = tk.Toplevel(self.master)
        self.window.overrideredirect(True)
        # Remove global topmost, use transient to keep above master but below other apps
        self.window.transient(self.master)
        
        # Set transparency
        try:
            self.window.wm_attributes('-transparentcolor', self.trans_color)
        except:
            pass # Not supported on all OS
            
        self.window.config(bg=self.trans_color)
        
        self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, 
                                bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()
        
        self._update_position()

    def _on_master_map(self, event):
        if self.window:
            self.window.deiconify()
            self._update_position()

    def _on_master_unmap(self, event):
        if self.window:
            self.window.withdraw()

    def _update_position(self, event=None):
        if not self.window or not self.is_spinning: return
        
        # Calculate center of master
        try:
            # Ensure master is mapped
            if not self.master.winfo_ismapped(): 
                self.window.withdraw()
                return
            
            self.window.deiconify()
            
            mw = self.master.winfo_width()
            mh = self.master.winfo_height()
            mx = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
            
            x = mx + (mw - self.size) // 2
            y = my + (mh - self.size) // 2
            
            self.window.geometry(f"{self.size}x{self.size}+{x}+{y}")
            # Lift above master, but don't force global topmost
            self.window.lift()
        except: pass

    def _animate(self):
        if self.is_spinning and self.window and self.canvas:
            self.angle = (self.angle - 10) % 360
            
            if self.arc:
                self.canvas.delete(self.arc)
                
            self.arc = self.canvas.create_arc(
                4, 4, self.size-4, self.size-4,
                start=self.angle, extent=120,
                style=tk.ARC, width=4, outline=self.color
            )
            
            self.timer_id = self.master.after(30, self._animate)
