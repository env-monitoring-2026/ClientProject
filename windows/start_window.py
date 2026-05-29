#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from config.settings import ICON_DIR
from windows.device_selector import DeviceSelector


class StartWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Мониторинг параметров окружающей среды")
        self.root.geometry("700x500")
        self.center_window()
        main_frame = ttk.Frame(self.root, padding=50)
        main_frame.pack(fill=tk.BOTH, expand=True)
        welcome_text = "Вас приветствует Система удалённого мониторинга\nпараметров окружающей среды.\n\nНажмите ниже, чтобы продолжить"
        ttk.Label(main_frame, text=welcome_text, font=("Arial", 16), justify='center').pack(expand=True)

        self.btn_photo = None
        pusk_path = os.path.join(ICON_DIR, "pusk.jpeg")
        try:
            if os.path.exists(pusk_path):
                img = Image.open(pusk_path).resize((80, 80), Image.Resampling.LANCZOS)
                self.btn_photo = ImageTk.PhotoImage(img)
        except:
            pass

        ttk.Button(main_frame, text="ПРОДОЛЖИТЬ", image=self.btn_photo, compound=tk.TOP,
                   command=self.start_monitoring).pack(pady=20)
        self.root.mainloop()

    def center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def start_monitoring(self):
        self.root.destroy()
        DeviceSelector()