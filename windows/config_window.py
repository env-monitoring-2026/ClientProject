#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import ftplib
import time
import json
from utils.device_data_manager import device_data_manager
from config.auth import FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS
from config.settings import MAX_RETRIES, TIMEOUT, CLIENT_CONFIG_FILE
from utils.logger import log_error, log_info

from utils.scaling import scale, scale_x, scale_y, scale_font_size, center_window

SMS_CONFIG_FILE = "sms_config.txt"

MAIN_WINDOW_CONFIG_FILE = "main_window_config.txt"


class ConfigWindow:
    def __init__(self, root, device_name, parent_callback=None):
        self.root = root
        self.parent_callback = parent_callback
        self.window = tk.Toplevel(root)
        self.device_name = device_name
        self.window.title(f"Конфигурация системы - {device_name}")

        width = scale(900)
        height = scale(800)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(scale(850), scale(750))

        center_window(self.window, width, height)

        self.phone_var = tk.StringVar(value="+7")
        self.send_params_var = tk.BooleanVar(value=False)
        self.params_freq_var = tk.StringVar(value="3600")
        self.send_diagnostic_var = tk.BooleanVar(value=False)

        self.work_dir_var = tk.StringVar(value="")
        self.reset_freq_var = tk.StringVar(value="3600")

        self.load_configs()
        self.setup_ui()

    def browse_work_dir(self):
        directory = filedialog.askdirectory(
            title="Выберите рабочую директорию",
            initialdir=self.work_dir_var.get() or os.path.expanduser("~")
        )
        if directory:
            self.work_dir_var.set(directory)

    def connect_ftp(self):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ftp = ftplib.FTP()
                ftp.connect(FTP_HOST, FTP_PORT, timeout=TIMEOUT)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd(f"devices/{self.device_name}")
                return ftp
            except Exception as e:
                log_error(f"Ошибка FTP-подключения (попытка {attempt}): {e}")
                time.sleep(2)
        return None

    def upload_config_to_ftp(self):
        if not os.path.exists(SMS_CONFIG_FILE):
            log_error("Файл конфигурации не найден локально")
            return False

        ftp = self.connect_ftp()
        if not ftp:
            log_error("Не удалось подключиться к FTP")
            return False

        try:
            with open(SMS_CONFIG_FILE, 'rb') as f:
                ftp.storbinary('STOR sms_config.txt', f)
            ftp.quit()
            log_info(f"Конфигурация загружена на FTP-сервер для устройства {self.device_name}")
            return True
        except Exception as e:
            log_error(f"Ошибка загрузки на FTP: {e}")
            try:
                ftp.quit()
            except:
                pass
            return False

    def setup_ui(self):
        padding_main = scale(25)

        main_canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_frame = ttk.Frame(scrollable_frame, padding=padding_main)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_font = ("Arial", scale_font_size(18), "bold")
        label_font = ("Arial", scale_font_size(11))
        small_font = ("Arial", scale_font_size(9), "italic")
        warning_font = ("Arial", scale_font_size(10), "bold")

        title = ttk.Label(main_frame, text=f"КОНФИГУРАЦИЯ СИСТЕМЫ\nУстройство: {self.device_name}",
                          font=title_font, justify='center')
        title.grid(row=0, column=0, columnspan=2, pady=scale(15))

        ttk.Separator(main_frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=scale(10))

        sms_frame = ttk.LabelFrame(main_frame, text="КОНФИГУРАЦИЯ SMS", padding=scale(15))
        sms_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=scale(10))

        ttk.Label(sms_frame, text="Номер телефона:", font=label_font).grid(row=0, column=0, sticky='w', pady=scale(5))
        phone_entry = ttk.Entry(sms_frame, textvariable=self.phone_var, width=scale(20), font=label_font)
        phone_entry.grid(row=0, column=1, sticky='w', pady=scale(5), padx=scale(10))
        ttk.Label(sms_frame, text="+7XXXXXXXXXX (только цифры)", font=small_font).grid(row=1, column=1, sticky='w')

        ttk.Checkbutton(sms_frame, text="Отправлять SMS-сообщения о параметрах окружающей среды",
                        variable=self.send_params_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=scale(10))

        ttk.Label(sms_frame, text="Частота отправки:", font=label_font).grid(row=3, column=0, sticky='w', pady=scale(5))

        freq_frame = ttk.Frame(sms_frame)
        freq_frame.grid(row=3, column=1, sticky='w', pady=scale(5))

        frequencies = [("5 мин", "300"), ("10 мин", "600"), ("15 мин", "900"),
                       ("30 мин", "1800"), ("1 ч", "3600"), ("3 ч", "10800")]

        for i, (text, value) in enumerate(frequencies):
            rb = ttk.Radiobutton(freq_frame, text=text, variable=self.params_freq_var, value=value)
            rb.grid(row=i // 3, column=i % 3, sticky='w', padx=scale(10), pady=scale(2))

        ttk.Checkbutton(sms_frame, text="Отправлять диагностические SMS-сообщения",
                        variable=self.send_diagnostic_var).grid(row=4, column=0, columnspan=2, sticky='w',
                                                                pady=scale(10))

        ttk.Separator(main_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=scale(15))

        ftp_frame = ttk.LabelFrame(main_frame, text="КОНФИГУРАЦИЯ ГЛАВНОГО ОКНА", padding=scale(15))
        ftp_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=scale(10))

        ttk.Label(ftp_frame, text="Рабочая директория:", font=label_font).grid(row=0, column=0, sticky='w',
                                                                               pady=scale(5))

        dir_frame = ttk.Frame(ftp_frame)
        dir_frame.grid(row=0, column=1, sticky='w', pady=scale(5), padx=scale(10))

        dir_entry = ttk.Entry(dir_frame, textvariable=self.work_dir_var, width=scale(40), font=label_font)
        dir_entry.pack(side='left', padx=(0, scale(5)))

        browse_dir_btn = ttk.Button(dir_frame, text="Обзор...", command=self.browse_work_dir)
        browse_dir_btn.pack(side='left')

        ttk.Label(ftp_frame, text="Сюда будут сохраняться графики и файл data.txt",
                  font=small_font).grid(row=1, column=1, sticky='w')

        ttk.Label(ftp_frame, text="Время сброса окна:", font=label_font).grid(row=2, column=0, sticky='w',
                                                                              pady=scale(10))

        reset_frame = ttk.Frame(ftp_frame)
        reset_frame.grid(row=2, column=1, sticky='w', pady=scale(10))

        reset_options = [("30 мин", "1800"), ("1 ч", "3600"), ("3 ч", "10800"), ("6 ч", "21600"),
                         ("12 ч", "43200"), ("1 д", "86400"), ("3 д", "259200"), ("1 нед", "604800"),
                         ("2 нед", "1209600"), ("1 мес", "2592000")]

        for i, (text, value) in enumerate(reset_options):
            rb = ttk.Radiobutton(reset_frame, text=text, variable=self.reset_freq_var, value=value)
            rb.grid(row=i // 5, column=i % 5, sticky='w', padx=scale(10), pady=scale(2))

        ttk.Label(ftp_frame, text="По истечении времени графики сохраняются в рабочую директорию и строятся заново",
                  font=small_font, justify='left').grid(row=3, column=0, columnspan=2, sticky='w', pady=scale(5))

        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky='ew', pady=scale(15))

        warning_frame = ttk.Frame(main_frame)
        warning_frame.grid(row=6, column=0, columnspan=2, pady=scale(10), padx=scale(20))

        warning_text = "Эксплуатация системы возможна при температуре окружающей среды в пределах\n-40…+85°C и атмосферном давлении в пределах 225…825 мм рт.ст. (300…1100 гПа)!"
        warning_label = ttk.Label(warning_frame, text=warning_text,
                                  font=warning_font, foreground="red", justify='center')
        warning_label.pack()

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=scale(20))

        save_btn = ttk.Button(button_frame, text="СОХРАНИТЬ", command=self.save_and_close,
                              style='Action.TButton', width=scale(15))
        save_btn.pack(side='left', padx=scale(10))

        cancel_btn = ttk.Button(button_frame, text="ОТМЕНА", command=self.window.destroy,
                                style='Action.TButton', width=scale(15))
        cancel_btn.pack(side='left', padx=scale(10))

    def validate_phone(self, phone):
        cleaned = re.sub(r'[^\d+]', '', phone)
        return re.match(r'^\+7\d{10}$', cleaned) is not None

    def load_configs(self):
        if os.path.exists(SMS_CONFIG_FILE):
            try:
                with open(SMS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        if key == 'phone':
                            self.phone_var.set(value)
                        elif key == 'send_params':
                            self.send_params_var.set(value.lower() == 'true')
                        elif key == 'params_freq':
                            self.params_freq_var.set(value)
                        elif key == 'send_diagnostic':
                            self.send_diagnostic_var.set(value.lower() == 'true')
            except Exception as e:
                log_error(f"Ошибка загрузки SMS-конфигурации: {e}")

        if os.path.exists(MAIN_WINDOW_CONFIG_FILE):
            try:
                with open(MAIN_WINDOW_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        if key == 'work_dir':
                            self.work_dir_var.set(value)
                        elif key == 'reset_interval':
                            self.reset_freq_var.set(value)
            except Exception as e:
                log_error(f"Ошибка загрузки конфигурации главного окна: {e}")

    def save_configs(self):
        if self.send_params_var.get() or self.send_diagnostic_var.get():
            phone = self.phone_var.get().strip()
            if not self.validate_phone(phone):
                messagebox.showerror("Ошибка", "Некорректный номер телефона.\nИспользуйте формат +7XXXXXXXXXX")
                return False

        try:
            with open(SMS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"phone={self.phone_var.get().strip()}\n")
                f.write(f"send_params={str(self.send_params_var.get()).lower()}\n")
                f.write(f"params_freq={self.params_freq_var.get()}\n")
                f.write(f"send_diagnostic={str(self.send_diagnostic_var.get()).lower()}\n")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить SMS-конфигурацию:\n{e}")
            return False

        work_dir = self.work_dir_var.get().strip()
        if not work_dir:
            messagebox.showerror("Ошибка", "Не выбрана рабочая директория")
            return False
        if not os.path.exists(work_dir):
            messagebox.showerror("Ошибка", "Указанная директория не существует")
            return False

        try:
            with open(MAIN_WINDOW_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"work_dir={work_dir}\n")
                f.write(f"reset_interval={self.reset_freq_var.get()}\n")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию главного окна:\n{e}")
            return False

        return True

    def save_and_close(self):
        if not self.save_configs():
            return

        config = {
            "work_dir": self.work_dir_var.get().strip(),
            "reset_interval": int(self.reset_freq_var.get()),
            "last_reset": None
        }
        device_data_manager.set_config(self.device_name, config)

        client_config = {
            "work_dir": self.work_dir_var.get().strip(),
            "reset_interval": int(self.reset_freq_var.get()),
            "last_reset": None
        }
        with open(CLIENT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(client_config, f, ensure_ascii=False, indent=2)

        if self.parent_callback and hasattr(self.parent_callback, 'update_config'):
            self.parent_callback.update_config(config)

        if self.upload_config_to_ftp():
            messagebox.showinfo("Успех",
                                f"Конфигурация сохранена и загружена на FTP-сервер для устройства {self.device_name}.")
        else:
            messagebox.showwarning("Предупреждение",
                                   f"Конфигурация сохранена локально, но не загружена на FTP для устройства {self.device_name}.\n"
                                   "Проверьте подключение к серверу.")

        self.window.destroy()