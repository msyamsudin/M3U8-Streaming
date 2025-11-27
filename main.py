#!/usr/bin/env python3
import tkinter as tk
from src.app_gui import M3U8StreamingPlayer

def main():
    
    root = tk.Tk()
    app = M3U8StreamingPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
