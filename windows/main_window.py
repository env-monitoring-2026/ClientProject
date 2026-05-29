#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import matplotlib
from utils.logger import log_info, log_error

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
from datetime import datetime, timedelta
import json
import os

from config.settings import (
    ICON_DIR, POLL_INTERVAL, TIMEOUT, MAX_RETRIES, CLIENT_CONFIG_FILE
)
from utils.ftp_client import  download_data_file, download_latest_diag

from utils.device_data_manager import device_data_manager
from windows.street_window import StreetWindow
from windows.indoor_window import IndoorWindow
from windows.custom_window import CustomWindow
from windows.diagnostic_window import DiagnosticWindow
from windows.config_window import ConfigWindow
from windows.mode_editor import ModeEditor

from config.settings import MODES_DIR


class ModeManager:

    def __init__(self):
        os.makedirs(MODES_DIR, exist_ok=True)


    def get_modes(self):
        modes = []
        if os.path.exists(self.MODE_DIR):
            for f in os.listdir(self.MODE_DIR):
                if f.endswith('.json'):
                    modes.append(f[:-5])
        return modes

    def load_mode(self, name):
        path = os.path.join(self.MODE_DIR, f"{name}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_mode(self, name, data):
        path = os.path.join(self.MODE_DIR, f"{name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_mode(self, name):
        path = os.path.join(self.MODE_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


class MonitoringWindow:
    def __init__(self, device_name):
        self.device_name = device_name
        self.config = self.load_client_config()
        self.ftp_device_dir = f"devices/{device_name}"

        self.root = tk.Tk()
        self.root.title(f"Мониторинг параметров окружающей среды - {device_name}")
        self.root.state('zoomed')

        self.latest_diag = None
        self.update_id = None
        self.all_records = []
        self.last_reset_timestamp = None
        self.next_reset_time = None

        self.next_reset_time = self.config.get('next_reset_time')

        self.schedule_log_cleanup()
        self.load_icons()
        self.mode_manager = ModeManager()
        self.ui_elements = {}

        self.setup_ui()
        self.start_updates()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def load_client_config(self):
        if os.path.exists(CLIENT_CONFIG_FILE):
            try:
                with open(CLIENT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"work_dir": "", "reset_interval": 3600, "last_reset": None}

    def save_client_config(self, config):
        try:
            with open(CLIENT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_icons(self):
        def load_icon_big(name, size=(80, 80)):
            path = os.path.join(ICON_DIR, name)
            try:
                if os.path.exists(path):
                    img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
                    return ImageTk.PhotoImage(img)
            except:
                pass
            return None

        self.icon_street_big = load_icon_big("street.png")
        self.icon_house_big = load_icon_big("house.png")
        self.icon_settings_big = load_icon_big("settings.png")
        self.back_icon = load_icon_big("back.png")
        self.icon_config = load_icon_big("config.png")
        self.icon_diag = load_icon_big("diag.png")
        self.icon_calendar = load_icon_big("calendar.png")
        self.icon_log_server = load_icon_big("log_server.png")
        self.icon_log_client = load_icon_big("log_client.png")

    def setup_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        self.fig = plt.figure(figsize=(16, 9), facecolor='white')
        gs = GridSpec(4, 3, height_ratios=[1, 3, 0.5, 0.5], hspace=0.3, top=0.92, bottom=0.08)

        self.ax_top = self.fig.add_subplot(gs[0, :])
        self.ax_top.axis('off')
        self.ui_elements['title'] = self.ax_top.text(0.5, 0.7, "ТЕКУЩИЕ ДАННЫЕ", ha='center', va='center',
                                                     fontsize=18, weight='bold', transform=self.ax_top.transAxes)
        self.ui_elements['time'] = self.ax_top.text(0.5, 0.4, "(по состоянию на --:--)", ha='center', va='center',
                                                    fontsize=16, style='italic', transform=self.ax_top.transAxes)
        self.ui_elements['temp'] = self.ax_top.text(0.2, 0.0, "Температура: -- °C", ha='center', fontsize=16)
        self.ui_elements['hum'] = self.ax_top.text(0.5, 0.0, "Влажность: -- %", ha='center', fontsize=16)
        self.ui_elements['press'] = self.ax_top.text(0.8, 0.0, "Давление: -- мм рт.ст.", ha='center', fontsize=16)

        self.ax_temp = self.fig.add_subplot(gs[1, 0])
        self.ax_hum = self.fig.add_subplot(gs[1, 1])
        self.ax_press = self.fig.add_subplot(gs[1, 2])
        for ax, t, y in zip([self.ax_temp, self.ax_hum, self.ax_press],
                            ["Температура", "Влажность", "Давление"],
                            ["°C", "%", "мм рт.ст."]):
            ax.set_title(t, fontsize=16, weight='bold')
            ax.set_ylabel(y, fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
            ax.tick_params(axis='x', rotation=45, labelsize=10)

        self.ui_elements['line_temp'], = self.ax_temp.plot([], [], 'r-', linewidth=2)
        self.ui_elements['line_hum'], = self.ax_hum.plot([], [], 'g-', linewidth=2)
        self.ui_elements['line_press'], = self.ax_press.plot([], [], 'b-', linewidth=2)

        self.ax_stat_temp = self.fig.add_subplot(gs[2, 0])
        self.ax_stat_hum = self.fig.add_subplot(gs[2, 1])
        self.ax_stat_press = self.fig.add_subplot(gs[2, 2])
        for ax in [self.ax_stat_temp, self.ax_stat_hum, self.ax_stat_press]:
            ax.axis('off')

        self.ui_elements['stat_temp'] = self.ax_stat_temp.text(0.5, 0.5,
                                                               "Температура\nмин: --\nмакс: --\nсреднее: --",
                                                               ha='center', va='center',
                                                               fontsize=16, linespacing=1.5,
                                                               transform=self.ax_stat_temp.transAxes)
        self.ui_elements['stat_hum'] = self.ax_stat_hum.text(0.5, 0.5,
                                                             "Влажность\nмин: --\nмакс: --\nсреднее: --", ha='center',
                                                             va='center',
                                                             fontsize=16, linespacing=1.5,
                                                             transform=self.ax_stat_hum.transAxes)
        self.ui_elements['stat_press'] = self.ax_stat_press.text(0.5, 0.5,
                                                                 "Давление\nмин: --\nмакс: --\nсреднее: --",
                                                                 ha='center', va='center',
                                                                 fontsize=16, linespacing=1.5,
                                                                 transform=self.ax_stat_press.transAxes)

        self.ax_buttons = self.fig.add_subplot(gs[3, :])
        self.ax_buttons.axis('off')
        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.add_buttons()
        self.update_dashboard()

    def add_buttons(self):
        left_panel = tk.Frame(self.canvas.get_tk_widget(), bg='#f0f0f0', relief='flat', bd=0)
        left_panel.place(relx=0.02, rely=0.5, anchor=tk.W)

        back_btn = tk.Button(left_panel, text="Назад", image=self.back_icon, compound=tk.TOP,
                             font=("Arial", 10), bg='#f0f0f0', relief='flat',
                             command=self.back_to_device_selector, width=100, height=100)
        back_btn.pack(pady=10, padx=10)

        config_btn = tk.Button(left_panel, text="КОНФИГУРАЦИЯ", image=self.icon_config,
                               compound=tk.TOP, font=("Arial", 10), bg='#f0f0f0', relief='flat',
                               command=self.open_config_window, width=100, height=100)
        config_btn.pack(pady=10, padx=10)

        diag_btn = tk.Button(left_panel, text="ДИАГНОСТИКА", image=self.icon_diag,
                             compound=tk.TOP, font=("Arial", 10), bg='#f0f0f0', relief='flat',
                             command=self.open_diagnostic_window, width=100, height=100)
        diag_btn.pack(pady=10, padx=10)

        right_panel = tk.Frame(self.canvas.get_tk_widget(), bg='#f0f0f0', relief='flat', bd=0)
        right_panel.place(relx=0.98, rely=0.5, anchor=tk.E)

        calendar_btn = tk.Button(right_panel, text="СУТОЧНЫЙ\nФАЙЛ", image=self.icon_calendar,
                                 compound=tk.TOP, font=("Arial", 10), bg='#f0f0f0', relief='flat',
                                 command=self.download_daily_file, width=100, height=100)
        calendar_btn.pack(pady=10, padx=10)

        log_server_btn = tk.Button(right_panel, text="ЛОГ\nСЕРВЕРА", image=self.icon_log_server,
                                   compound=tk.TOP, font=("Arial", 10), bg='#f0f0f0', relief='flat',
                                   command=self.download_server_log, width=100, height=100)
        log_server_btn.pack(pady=10, padx=10)

        log_client_btn = tk.Button(right_panel, text="ЛОГ\nКЛИЕНТА", image=self.icon_log_client,
                                   compound=tk.TOP, font=("Arial", 10), bg='#f0f0f0', relief='flat',
                                   command=self.download_client_log, width=100, height=100)
        log_client_btn.pack(pady=10, padx=10)

        bf = ttk.Frame(self.canvas.get_tk_widget())
        bf.place(relx=0.5, rely=0.9, anchor=tk.CENTER)
        ttk.Label(bf, text="РАСШИРЕННЫЙ АНАЛИЗ ДАННЫХ", font=("Arial", 24, "bold")).grid(row=0, column=0, columnspan=3,
                                                                                         pady=15)
        ttk.Button(bf, text="УЛИЦА", image=self.icon_street_big, compound=tk.TOP, style='Big.TButton',
                   command=self.open_street_window).grid(row=1, column=0, padx=30)
        ttk.Button(bf, text="ПОМЕЩЕНИЕ", image=self.icon_house_big, compound=tk.TOP, style='Big.TButton',
                   command=self.open_indoor_window).grid(row=1, column=1, padx=30)
        ttk.Button(bf, text="НАСТРАИВАЕМЫЙ", image=self.icon_settings_big, compound=tk.TOP, style='Big.TButton',
                   command=self.show_custom_menu).grid(row=1, column=2, padx=30)

        style = ttk.Style()
        style.configure('Big.TButton', font=('Arial', 16))

    def reset_display(self):
        now_ts = datetime.now().timestamp()

        self.last_reset_timestamp = now_ts

        reset_interval = self.config.get("reset_interval", 3600)
        self.next_reset_time = now_ts + reset_interval
        self.config['next_reset_time'] = self.next_reset_time
        device_data_manager.set_config(self.device_name, self.config)

        self.all_records = []
        try:
            device_data_manager.set_records(self.device_name, self.all_records)
        except:
            pass

        for ln in ['line_temp', 'line_hum', 'line_press']:
            if ln in self.ui_elements:
                self.ui_elements[ln].set_data([], [])
        for ax in [self.ax_temp, self.ax_hum, self.ax_press]:
            ax.relim()
            ax.autoscale_view()

        if 'stat_temp' in self.ui_elements:
            self.ui_elements['stat_temp'].set_text("Температура\nмин: --\nмакс: --\nсреднее: --")
        if 'stat_hum' in self.ui_elements:
            self.ui_elements['stat_hum'].set_text("Влажность\nмин: --\nмакс: --\nсреднее: --")
        if 'stat_press' in self.ui_elements:
            self.ui_elements['stat_press'].set_text("Давление\nмин: --\nмакс: --\nсреднее: --")
        if 'time' in self.ui_elements:
            self.ui_elements['time'].set_text("(по состоянию на --:--)")
        if 'temp' in self.ui_elements:
            self.ui_elements['temp'].set_text("Температура: -- °C")
        if 'hum' in self.ui_elements:
            self.ui_elements['hum'].set_text("Влажность: -- %")
        if 'press' in self.ui_elements:
            self.ui_elements['press'].set_text("Давление: -- мм рт.ст.")

        self.fig.canvas.draw_idle()
        log_info(
            f"Сброс выполнен. Следующий сброс в {datetime.fromtimestamp(self.next_reset_time).strftime('%H:%M:%S')}")

    def check_reset_needed(self):
        if not self.config.get("work_dir"):
            return
        if not self.all_records:
            return

        now_ts = datetime.now().timestamp()
        reset_interval = self.config.get("reset_interval", 3600)

        if self.next_reset_time is None:
            self.next_reset_time = now_ts + reset_interval
            self.config['next_reset_time'] = self.next_reset_time
            device_data_manager.set_config(self.device_name, self.config)
            return

        if now_ts >= self.next_reset_time:
            log_info(f"Автоматический сброс по истечении {reset_interval // 60} минут")
            self.save_snapshot()
            self.reset_display()

    def save_snapshot(self):
        work = self.config.get("work_dir")
        if not work or not os.path.exists(work):
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            self.ax_temp.figure.savefig(os.path.join(work, f"temp_{ts}.png"), dpi=100, bbox_inches='tight')
            self.ax_hum.figure.savefig(os.path.join(work, f"hum_{ts}.png"), dpi=100, bbox_inches='tight')
            self.ax_press.figure.savefig(os.path.join(work, f"press_{ts}.png"), dpi=100, bbox_inches='tight')
            if self.all_records:
                with open(os.path.join(work, f"data_{ts}.txt"), 'w', encoding='utf-8') as f:
                    f.write("# timestamp,temperature,humidity,pressure\n")
                    for r in self.all_records:
                        f.write(
                            f"{r['datetime'].timestamp():.3f},{r['temperature']:.2f},{r['humidity']:.2f},{r['pressure']:.2f}\n")
        except:
            pass

    def update_dashboard(self):
        if not self.root or not self.root.winfo_exists():
            return

        self.check_reset_needed()
        if not self.all_records:
            self.fig.canvas.draw_idle()
            return

        recent = self.all_records
        last = recent[-1]
        self.ui_elements['time'].set_text(f"(по состоянию на {last['datetime'].strftime('%H:%M')})")
        self.ui_elements['temp'].set_text(f"Температура: {last['temperature']:.1f} °C")
        self.ui_elements['hum'].set_text(f"Влажность: {last['humidity']:.1f} %")
        self.ui_elements['press'].set_text(f"Давление: {last['pressure']:.1f} мм рт.ст.")

        x = mdates.date2num([r['datetime'] for r in recent])
        self.ui_elements['line_temp'].set_data(x, [r['temperature'] for r in recent])
        self.ui_elements['line_hum'].set_data(x, [r['humidity'] for r in recent])
        self.ui_elements['line_press'].set_data(x, [r['pressure'] for r in recent])

        for ax in [self.ax_temp, self.ax_hum, self.ax_press]:
            ax.relim()
            ax.autoscale_view()
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        from utils.stats import calculate_stats
        stats = calculate_stats(recent)
        if stats:
            self.ui_elements['stat_temp'].set_text(
                f"Температура\nмин: {stats['temp']['min']:.1f}°C\nмакс: {stats['temp']['max']:.1f}°C\nсреднее: {stats['temp']['avg']:.1f}°C")
            self.ui_elements['stat_hum'].set_text(
                f"Влажность\nмин: {stats['hum']['min']:.1f}%\nмакс: {stats['hum']['max']:.1f}%\nсреднее: {stats['hum']['avg']:.1f}%")
            self.ui_elements['stat_press'].set_text(
                f"Давление\nмин: {stats['press']['min']:.1f} мм рт.ст.\nмакс: {stats['press']['max']:.1f} мм рт.ст.\nсреднее: {stats['press']['avg']:.1f} мм рт.ст.")

        self.fig.canvas.draw_idle()

    def check_and_update(self):
        if not self.root or not self.root.winfo_exists():
            return

        try:
            new_records = download_data_file(self.device_name, since_timestamp=self.last_reset_timestamp)
            if new_records:
                self.all_records = new_records
                self.latest_diag = download_latest_diag(self.device_name)
                self.update_dashboard()
        except Exception as e:
            log_error(f"Update error: {e}")

        if self.root and self.root.winfo_exists():
            self.update_id = self.root.after(POLL_INTERVAL * 1000, self.check_and_update)

    def start_updates(self):
        self.root.after(1000, self.check_and_update)

    def on_closing(self):
        try:
            device_data_manager.set_records(self.device_name, self.all_records)
            device_data_manager.set_latest_diag(self.device_name, self.latest_diag)
            device_data_manager.set_config(self.device_name, self.config)
        except:
            pass
        if hasattr(self, 'update_id') and self.update_id:
            try:
                self.root.after_cancel(self.update_id)
            except:
                pass
        self.root.destroy()

    def update_config(self, new_config):
        old_interval = self.config.get("reset_interval", 3600)
        new_interval = new_config.get("reset_interval", 3600)

        self.config = new_config

        if old_interval != new_interval:
            reset_interval = new_interval
            self.next_reset_time = datetime.now().timestamp() + reset_interval
            self.config['next_reset_time'] = self.next_reset_time
            device_data_manager.set_config(self.device_name, self.config)
            log_info(
                f"Интервал сброса изменён: {old_interval // 60} → {new_interval // 60} минут, следующий сброс в {datetime.fromtimestamp(self.next_reset_time).strftime('%H:%M:%S')}")
        else:
            device_data_manager.set_config(self.device_name, self.config)
            log_info(f"Конфигурация обновлена (таймер сброса не изменился)")

    def schedule_log_cleanup(self):
        self.cleanup_logs()
        self.root.after(86400000, self.schedule_log_cleanup)

    def cleanup_logs(self):
        from utils.logger import cleanup_old_logs, LOG_DIR
        from config.settings import CLIENT_LOG_RETENTION_DAYS
        log_file = os.path.join(LOG_DIR, "client.log")
        deleted = cleanup_old_logs(log_file, CLIENT_LOG_RETENTION_DAYS)
        if deleted > 0:
            log_info(f"Лог очищен: удалено {deleted} устаревших записей")

    def open_street_window(self):
        StreetWindow(self.root, self.all_records[-120:] if self.all_records else [], self.get_recent_records)

    def open_indoor_window(self):
        IndoorWindow(self.root, self.all_records[-120:] if self.all_records else [], self.get_recent_records)

    def get_recent_records(self, hours=2):
        if not self.all_records:
            return []
        if hours is None:
            return self.all_records.copy()
        cutoff = datetime.now() - timedelta(hours=hours)
        return [r for r in self.all_records if r['datetime'] >= cutoff]

    def show_custom_menu(self):
        menu = tk.Menu(self.root, tearoff=0, font=("Arial", 16))
        for m in self.mode_manager.get_modes():
            sub = tk.Menu(menu, tearoff=0, font=("Arial", 16))
            sub.add_command(label="Открыть", command=lambda mm=m: self.open_custom_window(mm))
            sub.add_command(label="Редактировать", command=lambda mm=m: self.edit_mode(mm))
            sub.add_command(label="Удалить", command=lambda mm=m: self.delete_mode(mm))
            menu.add_cascade(label=m, menu=sub)
        if self.mode_manager.get_modes():
            menu.add_separator()
        menu.add_command(label="Создать новый режим...", command=self.create_new_mode)
        menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def open_custom_window(self, name):
        mode = self.mode_manager.load_mode(name)
        CustomWindow(self.root, self.all_records[-120:] if self.all_records else [], mode, self.get_recent_records)

    def edit_mode(self, name):
        ModeEditor(self.root, self.mode_manager, name)

    def delete_mode(self, name):
        if messagebox.askyesno("Подтверждение", f"Удалить режим '{name}'?"):
            self.mode_manager.delete_mode(name)

    def create_new_mode(self):
        ModeEditor(self.root, self.mode_manager)

    def open_diagnostic_window(self):
        DiagnosticWindow(self.root, self.device_name, self.latest_diag)

    def open_config_window(self):
        ConfigWindow(self.root, self.device_name, parent_callback=self)

    def back_to_device_selector(self):
        if messagebox.askyesno("Подтверждение", "Вернуться к выбору устройства?\nТекущие данные будут сохранены."):
            try:
                device_data_manager.set_records(self.device_name, self.all_records)
                device_data_manager.set_latest_diag(self.device_name, self.latest_diag)
                device_data_manager.set_config(self.device_name, self.config)
            except:
                pass
            if hasattr(self, 'update_id') and self.update_id:
                try:
                    self.root.after_cancel(self.update_id)
                except:
                    pass
            self.root.destroy()
            from windows.device_selector import DeviceSelector
            DeviceSelector()

    def download_daily_file(self):
        from utils.ftp_client import connect_ftp
        import tkinter as tk


        def load_available_dates():
            ftp = connect_ftp()
            if not ftp:
                return {}

            try:
                ftp.cwd(self.ftp_device_dir)

                base_dir = ftp.pwd()

                years = []
                try:
                    years = ftp.nlst()
                except:
                    pass

                available = {}
                for year in years:
                    if year in ['archive', 'diag_archive']:
                        continue

                    try:
                        ftp.cwd(year)
                        months = ftp.nlst()

                        for month in months:
                            if month in ['archive', 'diag_archive']:
                                continue

                            try:
                                ftp.cwd(month)
                                files = ftp.nlst()

                                for f in files:
                                    if f.endswith('.txt') and len(f) == 14:
                                        date_str = f[:-4]
                                        available[date_str] = True

                                ftp.cwd('..')
                            except:
                                try:
                                    ftp.cwd('..')
                                except:
                                    pass
                                continue

                        ftp.cwd(base_dir)
                    except:
                        try:
                            ftp.cwd(base_dir)
                        except:
                            pass
                        continue

                return available
            except Exception as e:
                log_error(f"Ошибка загрузки списка суточных файлов: {e}")
                return {}
            finally:
                try:
                    ftp.quit()
                except:
                    pass

        def get_month_name_en(month_num):
            months = ["jan", "feb", "mar", "apr", "may", "jun",
                      "jul", "aug", "sep", "oct", "nov", "dec"]
            return months[month_num - 1]

        def do_download():
            selected_date = cal.get_date()

            year, month, day = selected_date.split('-')
            month_name = get_month_name_en(int(month))
            remote_path = f"{self.ftp_device_dir}/{year}/{month_name}/{selected_date}.txt"
            local_path = os.path.join(os.path.expanduser("~"), "Downloads", f"{self.device_name}_{selected_date}.txt")

            ftp = connect_ftp()
            if not ftp:
                messagebox.showerror("Ошибка", "Не удалось подключиться к FTP")
                return

            try:
                with open(local_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                messagebox.showinfo("Успех", f"Файл сохранён в:\n{local_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось скачать файл:\n{e}")
            finally:
                try:
                    ftp.quit()
                except:
                    pass
            top.destroy()

        available_dates = load_available_dates()

        top = tk.Toplevel(self.root)
        top.title("Выбор даты")
        top.geometry("350x300")
        top.resizable(False, False)

        try:
            from tkcalendar import Calendar

            cal = Calendar(
                top,
                selectmode='day',
                date_pattern='yyyy-mm-dd',
                showweeknumbers=False,
                weekendbackground='lightgray',
                foreground='black',
                normalbackground='white',
                weekendforeground='black',
                selectbackground='blue',
                selectforeground='white',
                headersbackground='lightgray',
                headersforeground='black',
                background='white',
                bordercolor='lightgray',
                othermonthforeground='gray',
                othermonthbackground='white',
                selectborderwidth=1
            )

            for date_str in available_dates:
                try:
                    cal.calevent_create(datetime.strptime(date_str, '%Y-%m-%d'), 'available', 'available')
                except:
                    pass

            cal.tag_config('available', background='lightgreen', foreground='black')

            cal.pack(pady=10)

            info_label = ttk.Label(top, text="Зелёные дни — файл есть\nБелые — файла нет",
                                   font=("Arial", 9), foreground="gray")
            info_label.pack(pady=5)

            btn_frame = ttk.Frame(top)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Скачать", command=do_download).pack(side='left', padx=5)
            ttk.Button(btn_frame, text="Отмена", command=top.destroy).pack(side='left', padx=5)

        except ImportError:
            ttk.Label(top, text="Библиотека tkcalendar не установлена\npip install tkcalendar",
                      font=("Arial", 10), foreground="red").pack(pady=20)
            ttk.Button(top, text="Закрыть", command=top.destroy).pack()

    def get_month_name(self, month):
        months = ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
        return months[month - 1]

    def download_server_log(self):
        from utils.ftp_client import connect_ftp

        ftp = connect_ftp()
        if not ftp:
            messagebox.showerror("Ошибка", "Не удалось подключиться к FTP")
            return

        try:
            local_path = os.path.join(os.path.expanduser("~"), "Downloads", f"{self.device_name}_server.log")
            remote_path = f"{self.ftp_device_dir}/server.log"

            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)

            messagebox.showinfo("Успех", f"Лог сервера сохранён в:\n{local_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скачать лог сервера:\n{e}")
        finally:
            try:
                ftp.quit()
            except:
                pass

    def download_client_log(self):
        import shutil

        local_log_path = os.path.join("logs", "client.log")

        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "client.log")

        if not os.path.exists(local_log_path):
            messagebox.showerror("Ошибка", "Лог клиента не найден. Возможно, логирование не включено.")
            return

        try:
            shutil.copy2(local_log_path, downloads_path)
            messagebox.showinfo("Успех", f"Лог клиента сохранён в:\n{downloads_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать лог клиента:\n{e}")