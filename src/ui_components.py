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
