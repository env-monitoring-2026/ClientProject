#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from config.settings import ICON_DIR
from windows.device_selector import DeviceSelector
from utils.scaling import init_scaling, scale, scale_font_size, center_window


class StartWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Мониторинг параметров окружающей среды")

        init_scaling(self.root)

        width = scale(700)
        height = scale(500)
        self.root.geometry(f"{width}x{height}")
        center_window(self.root, width, height)

        main_frame = ttk.Frame(self.root, padding=scale(50))
        main_frame.pack(fill=tk.BOTH, expand=True)

        welcome_text = "Вас приветствует Система удалённого мониторинга\nпараметров окружающей среды.\n\nНажмите ниже, чтобы продолжить"

        welcome_label = ttk.Label(main_frame, text=welcome_text,
                                  font=("Arial", scale_font_size(16)),
                                  justify='center')
        welcome_label.pack(expand=True)

        self.btn_photo = None
        pusk_path = os.path.join(ICON_DIR, "pusk.jpeg")
        try:
            if os.path.exists(pusk_path):
                img = Image.open(pusk_path).resize((scale(80), scale(80)), Image.Resampling.LANCZOS)
                self.btn_photo = ImageTk.PhotoImage(img)
        except:
            pass

        btn = ttk.Button(main_frame, text="ПРОДОЛЖИТЬ", image=self.btn_photo,
                         compound=tk.TOP, command=self.start_monitoring)
        btn.pack(pady=scale(20))

        self.root.mainloop()

    def start_monitoring(self):
        self.root.destroy()
        DeviceSelector()