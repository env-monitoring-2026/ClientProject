#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import ftplib
from config.auth import FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS, FTP_DIR
from config.settings import TIMEOUT
from utils.logger import log_error


class DeviceSelector:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Выбор устройства")
        self.root.geometry("600x550")
        self.center_window()

        self.selected_device = None
        self.devices = []

        self.setup_ui()
        self.load_devices()

        self.root.mainloop()

    def center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def connect_ftp(self):
        try:
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=TIMEOUT)
            ftp.login(FTP_USER, FTP_PASS)
            return ftp
        except Exception as e:
            log_error(f"Ошибка FTP-подключения: {e}")
            return None

    def load_devices(self):
        self.status_var.set("Загрузка списка устройств...")
        self.next_btn.config(state='disabled')
        self.device_combo.set("не выбрано")
        self.root.update_idletasks()

        ftp = self.connect_ftp()
        if not ftp:
            self.status_var.set("Ошибка подключения к FTP-серверу")
            return

        try:
            ftp.cwd("devices")
            items = ftp.nlst()
            self.devices = []

            EXCLUDED_DIRS = {"archive", "diag_archive"}

            for item in items:
                if item in EXCLUDED_DIRS or item.startswith('.'):
                    continue

                try:
                    ftp.cwd(item)
                    ftp.cwd("..")
                    self.devices.append(item)
                except:
                    pass

            ftp.quit()
        except Exception as e:
            log_error(f"Ошибка получения списка устройств: {e}")
            self.status_var.set("Ошибка получения списка устройств")
            return

        if self.devices:
            self.device_combo['values'] = ["не выбрано"] + self.devices
            self.status_var.set(f"Найдено устройств: {len(self.devices)}")
        else:
            self.device_combo['values'] = ["не выбрано"]
            self.status_var.set("Нет доступных устройств. Проверьте, что устройства созданы в папке devices.")

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=40)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main_frame,
                          text="Чтобы начать мониторинг,\nвыберите устройство, с которого хотите получать данные",
                          font=("Arial", 14), justify='center')
        title.pack(pady=(0, 30))

        select_frame = ttk.Frame(main_frame)
        select_frame.pack(pady=10)

        ttk.Label(select_frame, text="Выбранное устройство:", font=("Arial", 12)).pack(side='left', padx=10)

        self.device_combo = ttk.Combobox(select_frame, font=("Arial", 12), width=25, state='readonly')
        self.device_combo.pack(side='left', padx=10)
        self.device_combo.set("не выбрано")

        self.status_var = tk.StringVar(value="Загрузка списка устройств...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 10), foreground="gray")
        status_label.pack(pady=15)

        info_text = ("Чтобы иметь возможность выбрать конкретное устройство,\n"
                     "задайте для него произвольное имя в параметре DEVICE_NAME файла ftp_config.h - \n"
                     "конфигурационного файла встроенного ПО (прошивки) устройства.\n"
                     "Устройство будет доступно для выбора под заданным именем.\n"
                     "Важно: заданное имя не должно совпадать с именами других Ваших устройств."
                     )
        info_label = ttk.Label(main_frame, text=info_text, font=("Arial", 10),
                               foreground="gray", justify='center')
        info_label.pack(pady=20)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        style = ttk.Style()
        style.configure('Action.TButton', font=('Arial', 12))

        self.next_btn = ttk.Button(btn_frame, text="ДАЛЕЕ", command=self.start_monitoring,
                                   state='disabled', style='Action.TButton', width=15)
        self.next_btn.pack(side='left', padx=10)

        back_btn = ttk.Button(btn_frame, text="НАЗАД", command=self.back_to_welcome,
                              style='Action.TButton', width=15)
        back_btn.pack(side='left', padx=10)

        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_selected)
        self.device_combo.bind('<Return>', self.on_enter_pressed)

    def on_device_selected(self, event):
        selected = self.device_combo.get()
        if selected and selected != "не выбрано":
            self.next_btn.config(state='normal')
        else:
            self.next_btn.config(state='disabled')

    def on_enter_pressed(self, event):
        selected = self.device_combo.get()
        if selected and selected != "не выбрано" and selected in self.devices:
            self.start_monitoring()

    def back_to_welcome(self):
        self.root.destroy()
        from windows.start_window import StartWindow
        StartWindow()

    def start_monitoring(self):
        from windows.main_window import MonitoringWindow
        self.selected_device = self.device_combo.get()
        if not self.selected_device or self.selected_device == "не выбрано":
            messagebox.showwarning("Внимание", "Пожалуйста, выберите устройство")
            return

        if self.selected_device not in self.devices:
            messagebox.showerror("Ошибка", "Выбранное устройство недоступно")
            return

        self.root.destroy()
        MonitoringWindow(self.selected_device)