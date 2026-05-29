#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import ftplib
import time

from config.auth import FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS
from config.settings import TIMEOUT, MAX_RETRIES
from utils.logger import log_error


DIAG_INTERVAL_MINUTES = 50


class DiagnosticWindow:

    MCC_COUNTRIES = {
        250: "Россия",
    }


    MNC_OPERATORS = {
        1: "МТС",
        2: "Мегафон",
        20: "t2",
        99: "Билайн",
    }


    OPERATION_MODES = {
        "Online": "В сети",
        "Offline": "Вне сети",
        "Factory Test Mode": "Заводской тестовый режим",
        "Reset": "Перезапуск",
        "Low Power Mode": "Режим пониженного энергопотребления",
    }

    def __init__(self, parent, device_name, diag_data=None):
        self.parent = parent
        self.device_name = device_name
        self.diag_data = diag_data or {}

        self.window = tk.Toplevel(parent)
        self.window.title(f"Диагностика устройства - {device_name}")
        self.window.geometry("700x750")
        self.window.minsize(650, 700)

        self.center_window()
        self.setup_ui()

        self.auto_update()

    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def connect_ftp(self):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ftp = ftplib.FTP()
                ftp.connect(FTP_HOST, FTP_PORT, timeout=TIMEOUT)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd("devices")  # перешли в devices (работает)
                ftp.cwd(self.device_name)  # перешли в папку устройства (относительно devices)
                return ftp
            except Exception as e:
                log_error(f"Ошибка FTP-подключения (попытка {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(2)
        return None

    def get_diag_file_info(self):
        try:
            ftp = self.connect_ftp()
            if not ftp:
                return None, None, None

            lines = []

            def callback(data):
                lines.append(data.decode('utf-8', errors='ignore'))

            try:
                ftp.retrbinary("RETR diag.txt", callback)
                ftp.quit()
            except Exception as e:
                log_error(f"Ошибка скачивания diag.txt для {self.device_name}: {e}")
                return None, None, None

            content = ''.join(lines)
            last_record = None
            last_timestamp = None

            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) >= 9:
                        try:
                            timestamp = float(parts[0])
                            last_timestamp = datetime.fromtimestamp(timestamp)
                            last_record = {
                                'timestamp': last_timestamp,
                                'system_mode': parts[1] if len(parts) > 1 else "N/A",
                                'operation_mode': parts[2] if len(parts) > 2 else "N/A",
                                'mcc': parts[3] if len(parts) > 3 else "",
                                'mnc': parts[4] if len(parts) > 4 else "",
                                'rssi': parts[5] if len(parts) > 5 else "",
                                'voltage': parts[6] if len(parts) > 6 else "",
                                'temperature': parts[7] if len(parts) > 7 else "",
                                'uart': parts[8] if len(parts) > 8 else "",
                            }
                        except Exception as e:
                            log_error(f"Ошибка парсинга строки: {e}")
                            continue

            next_diag_time = None
            if last_timestamp:
                next_diag_time = last_timestamp + timedelta(minutes=DIAG_INTERVAL_MINUTES)

            return last_record, last_timestamp, next_diag_time

        except Exception as e:
            log_error(f"Diag load error for {self.device_name}: {e}")
            return None, None, None

    def get_country_name(self, mcc):
        try:
            mcc_val = int(mcc)
            country = self.MCC_COUNTRIES.get(mcc_val)
            if country:
                return f"{country} (код {mcc_val})"
            else:
                return f"Неизвестно (код {mcc_val})"
        except (ValueError, TypeError):
            return "Неизвестно"

    def get_operator_name(self, mcc, mnc):
        try:
            mcc_val = int(mcc)
            mnc_val = int(mnc)
            if mcc_val == 250:
                operator = self.MNC_OPERATORS.get(mnc_val)
                if operator:
                    return f"{operator} (код {mnc_val})"
                else:
                    return f"Прочие/неизвестно (код {mnc_val})"
            else:
                return f"Код {mnc_val}"
        except (ValueError, TypeError):
            return "Неизвестно"

    def get_operation_mode_ru(self, mode):
        return self.OPERATION_MODES.get(mode, mode)

    def rssi_quality_description(self, rssi):
        try:
            rssi_val = int(rssi)
            if rssi_val >= -51:
                return "Отличный"
            elif -70 <= rssi_val < -51:
                return "Очень хороший"
            elif -80 <= rssi_val < -70:
                return "Хороший"
            elif -90 <= rssi_val < -80:
                return "Средний"
            elif -100 <= rssi_val < -90:
                return "Слабый"
            elif rssi_val < -100:
                return "Очень слабый"
            else:
                return "Неизвестно"
        except:
            return "Ошибка данных"

    def format_time_to_next(self, next_time):
        if not next_time:
            return "—"

        now = datetime.now()
        if next_time <= now:
            return "Ожидается..."

        delta = next_time - now
        total_minutes = int(delta.total_seconds() / 60)

        if total_minutes < 1:
            return "Менее 1 минуты"
        else:
            return f"~{total_minutes} мин"

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title = ttk.Label(main_frame, text=f"ДИАГНОСТИКА УСТРОЙСТВА\n{self.device_name}",
                          font=("Arial", 16, "bold"), justify='center')
        title.grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Separator(main_frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=10)

        time_frame = ttk.LabelFrame(main_frame, text="ВРЕМЯ ДИАГНОСТИКИ", padding=10)
        time_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5, padx=5)

        self.last_time_var = tk.StringVar(value="—")
        ttk.Label(time_frame, text="Последняя диагностика:", font=("Arial", 11)).grid(row=0, column=0, sticky='w')
        ttk.Label(time_frame, textvariable=self.last_time_var, font=("Arial", 11, "bold")).grid(row=0, column=1,
                                                                                                sticky='w', padx=10)

        self.next_time_var = tk.StringVar(value="—")
        ttk.Label(time_frame, text="До следующей диагностики:", font=("Arial", 11)).grid(row=1, column=0, sticky='w',
                                                                                         pady=5)
        ttk.Label(time_frame, textvariable=self.next_time_var, font=("Arial", 11, "bold")).grid(row=1, column=1,
                                                                                                sticky='w', padx=10)

        ttk.Label(time_frame, text=f"(диагностика каждые {DIAG_INTERVAL_MINUTES} минут)",
                  font=("Arial", 9, "italic"), foreground="gray").grid(row=2, column=0, columnspan=2, sticky='w',
                                                                       pady=2)

        ttk.Separator(main_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)



        voltage_frame = ttk.LabelFrame(main_frame, text="Напряжение", padding=10)
        voltage_frame.grid(row=4, column=0, sticky='nsew', pady=5, padx=5)
        self.voltage_var = tk.StringVar(value="--")
        ttk.Label(voltage_frame, textvariable=self.voltage_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        temp_frame = ttk.LabelFrame(main_frame, text="Температура устройства", padding=10)
        temp_frame.grid(row=4, column=1, sticky='nsew', pady=5, padx=5)
        self.temp_var = tk.StringVar(value="--")
        ttk.Label(temp_frame, textvariable=self.temp_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        uart_frame = ttk.LabelFrame(main_frame, text="UART скорость", padding=10)
        uart_frame.grid(row=5, column=0, sticky='nsew', pady=5, padx=5)
        self.uart_var = tk.StringVar(value="--")
        ttk.Label(uart_frame, textvariable=self.uart_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        mode_frame = ttk.LabelFrame(main_frame, text="Тип сети", padding=10)
        mode_frame.grid(row=5, column=1, sticky='nsew', pady=5, padx=5)
        self.mode_var = tk.StringVar(value="--")
        ttk.Label(mode_frame, textvariable=self.mode_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        opmode_frame = ttk.LabelFrame(main_frame, text="Состояние модема", padding=10)
        opmode_frame.grid(row=6, column=0, sticky='nsew', pady=5, padx=5)
        self.opmode_var = tk.StringVar(value="--")
        ttk.Label(opmode_frame, textvariable=self.opmode_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        country_frame = ttk.LabelFrame(main_frame, text="Страна", padding=10)
        country_frame.grid(row=6, column=1, sticky='nsew', pady=5, padx=5)
        self.country_var = tk.StringVar(value="--")
        ttk.Label(country_frame, textvariable=self.country_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        operator_frame = ttk.LabelFrame(main_frame, text="Оператор", padding=10)
        operator_frame.grid(row=7, column=0, sticky='nsew', pady=5, padx=5)
        self.operator_var = tk.StringVar(value="--")
        ttk.Label(operator_frame, textvariable=self.operator_var,
                  font=("Arial", 14, "bold")).pack(expand=True)


        rssi_frame = ttk.LabelFrame(main_frame, text="Уровень сигнала (RSSI)", padding=10)
        rssi_frame.grid(row=7, column=1, sticky='nsew', pady=5, padx=5)

        frame_rssi = ttk.Frame(rssi_frame)
        frame_rssi.pack(fill=tk.X, expand=True)

        self.rssi_var = tk.StringVar(value="--")
        ttk.Label(frame_rssi, textvariable=self.rssi_var,
                  font=("Arial", 14, "bold")).pack(side='left', padx=5)

        self.rssi_qual_var = tk.StringVar(value="")
        ttk.Label(frame_rssi, textvariable=self.rssi_qual_var,
                  font=("Arial", 11, "italic")).pack(side='left', padx=10)


        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def update_display(self, last_record, last_timestamp, next_diag_time):
        if last_timestamp:
            self.last_time_var.set(last_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.last_time_var.set("—")

        self.next_time_var.set(self.format_time_to_next(next_diag_time))

        if not last_record:
            self.voltage_var.set("--")
            self.temp_var.set("--")
            self.uart_var.set("--")
            self.mode_var.set("--")
            self.opmode_var.set("--")
            self.country_var.set("--")
            self.operator_var.set("--")
            self.rssi_var.set("--")
            self.rssi_qual_var.set("")
            return

        if last_record.get('voltage'):
            self.voltage_var.set(f"{last_record['voltage']} V")
        else:
            self.voltage_var.set("--")

        if last_record.get('temperature'):
            self.temp_var.set(f"{last_record['temperature']} °C")
        else:
            self.temp_var.set("--")

        if last_record.get('uart'):
            self.uart_var.set(f"{last_record['uart']} baud")
        else:
            self.uart_var.set("--")

        if last_record.get('system_mode'):
            self.mode_var.set(last_record['system_mode'])
        else:
            self.mode_var.set("--")

        if last_record.get('operation_mode'):
            self.opmode_var.set(self.get_operation_mode_ru(last_record['operation_mode']))
        else:
            self.opmode_var.set("--")

        if last_record.get('mcc'):
            self.country_var.set(self.get_country_name(last_record['mcc']))
        else:
            self.country_var.set("--")

        if last_record.get('mcc') and last_record.get('mnc'):
            self.operator_var.set(self.get_operator_name(last_record['mcc'], last_record['mnc']))
        else:
            self.operator_var.set("--")

        if last_record.get('rssi'):
            try:
                rssi_val = int(last_record['rssi'])
                self.rssi_var.set(f"{rssi_val} dBm")
                self.rssi_qual_var.set(self.rssi_quality_description(rssi_val))
            except:
                self.rssi_var.set("--")
                self.rssi_qual_var.set("Ошибка данных")
        else:
            self.rssi_var.set("--")
            self.rssi_qual_var.set("")

    def refresh_data(self):
        last_record, last_timestamp, next_diag_time = self.get_diag_file_info()
        self.update_display(last_record, last_timestamp, next_diag_time)

    def auto_update(self):
        self.refresh_data()
        self.window.after(60000, self.auto_update)