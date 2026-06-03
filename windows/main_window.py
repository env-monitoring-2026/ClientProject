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
    ICON_DIR, POLL_INTERVAL, CLIENT_CONFIG_FILE
)
from utils.ftp_client import download_data_file, download_latest_diag, connect_ftp

from utils.device_data_manager import device_data_manager
from windows.street_window import StreetWindow
from windows.indoor_window import IndoorWindow
from windows.custom_window import CustomWindow
from windows.diagnostic_window import DiagnosticWindow
from windows.config_window import ConfigWindow
from windows.mode_editor import ModeEditor

from config.settings import MODES_DIR

from utils.scaling import init_scaling, scale, scale_x, scale_y, scale_font_size, get_scale_min


class ModeManager:
    def __init__(self):
        self.MODE_DIR = MODES_DIR
        os.makedirs(self.MODE_DIR, exist_ok=True)

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

        init_scaling(self.root)

        self.latest_diag = None
        self.update_id = None
        self.all_records = []
        self.last_reset_timestamp = None
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

    def load_icons(self):
        def load_icon_big(name, size=(80, 80)):
            path = os.path.join(ICON_DIR, name)
            try:
                if os.path.exists(path):
                    scaled_size = (scale_x(size[0]), scale_y(size[1]))
                    img = Image.open(path).resize(scaled_size, Image.Resampling.LANCZOS)
                    return ImageTk.PhotoImage(img)
            except:
                pass
            return None

        self.icon_street_big = load_icon_big("street.png")
        self.icon_house_big = load_icon_big("house.png")
        self.icon_settings_big = load_icon_big("settings.png")
        self.back_icon = load_icon_big("back.png", (100, 100))
        self.icon_config = load_icon_big("config.png", (100, 100))
        self.icon_diag = load_icon_big("diag.png", (100, 100))
        self.icon_calendar = load_icon_big("calendar.png", (100, 100))
        self.icon_log_server = load_icon_big("log_server.png", (100, 100))
        self.icon_log_client = load_icon_big("log_client.png", (100, 100))

    def setup_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main)
        top_frame.pack(fill=tk.X, pady=scale(3))

        title_label = ttk.Label(top_frame, text="ТЕКУЩИЕ ДАННЫЕ",
                                font=("Arial", scale_font_size(18), "bold"))
        title_label.pack()

        self.time_label = ttk.Label(top_frame, text="(по состоянию на --:--)",
                                    font=("Arial", scale_font_size(14), "italic"))
        self.time_label.pack()

        data_frame = ttk.Frame(top_frame)
        data_frame.pack(pady=scale(3))

        self.temp_label = ttk.Label(data_frame, text="Температура: -- °C",
                                    font=("Arial", scale_font_size(14)))
        self.temp_label.pack(side=tk.LEFT, padx=scale(20))

        self.hum_label = ttk.Label(data_frame, text="Влажность: -- %",
                                   font=("Arial", scale_font_size(14)))
        self.hum_label.pack(side=tk.LEFT, padx=scale(20))

        self.press_label = ttk.Label(data_frame, text="Давление: -- мм рт.ст.",
                                     font=("Arial", scale_font_size(14)))
        self.press_label.pack(side=tk.LEFT, padx=scale(20))

        scale_min = get_scale_min()

        fig_width = scale_x(16)
        fig_height = scale_y(8.5)

        self.fig = plt.figure(figsize=(fig_width, fig_height), facecolor='white')

        gs = GridSpec(3, 3, height_ratios=[2.8, 0.7, 0.4], hspace=0.2, top=0.96, bottom=0.06)

        self.ax_temp = self.fig.add_subplot(gs[0, 0])
        self.ax_hum = self.fig.add_subplot(gs[0, 1])
        self.ax_press = self.fig.add_subplot(gs[0, 2])

        for ax, t, y in zip([self.ax_temp, self.ax_hum, self.ax_press],
                            ["Температура", "Влажность", "Давление"],
                            ["°C", "%", "мм рт.ст."]):
            ax.set_title(t, fontsize=scale_font_size(14), weight='bold')
            ax.set_ylabel(y, fontsize=scale_font_size(11))
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
            ax.tick_params(axis='x', rotation=45, labelsize=scale_font_size(9))

        self.line_temp, = self.ax_temp.plot([], [], 'r-', linewidth=2)
        self.line_hum, = self.ax_hum.plot([], [], 'g-', linewidth=2)
        self.line_press, = self.ax_press.plot([], [], 'b-', linewidth=2)

        self.ax_stat_temp = self.fig.add_subplot(gs[1, 0])
        self.ax_stat_hum = self.fig.add_subplot(gs[1, 1])
        self.ax_stat_press = self.fig.add_subplot(gs[1, 2])
        for ax in [self.ax_stat_temp, self.ax_stat_hum, self.ax_stat_press]:
            ax.axis('off')

        if scale_min < 0.8:
            stat_font_size = scale_font_size(11)
            stat_linespacing = 1.2
        else:
            stat_font_size = scale_font_size(13)
            stat_linespacing = 1.3

        self.stat_temp_label = self.ax_stat_temp.text(0.5, 0.42,
                                                      "Температура\nмин: --\nмакс: --\nсреднее: --",
                                                      ha='center', va='center',
                                                      fontsize=stat_font_size, linespacing=stat_linespacing,
                                                      transform=self.ax_stat_temp.transAxes)
        self.stat_hum_label = self.ax_stat_hum.text(0.5, 0.42,
                                                    "Влажность\nмин: --\nмакс: --\nсреднее: --",
                                                    ha='center', va='center',
                                                    fontsize=stat_font_size, linespacing=stat_linespacing,
                                                    transform=self.ax_stat_hum.transAxes)
        self.stat_press_label = self.ax_stat_press.text(0.5, 0.42,
                                                        "Давление\nмин: --\nмакс: --\nсреднее: --",
                                                        ha='center', va='center',
                                                        fontsize=stat_font_size, linespacing=stat_linespacing,
                                                        transform=self.ax_stat_press.transAxes)

        self.ax_buttons = self.fig.add_subplot(gs[2, :])
        self.ax_buttons.axis('off')

        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.add_buttons()
        self.update_dashboard()

    def add_buttons(self):
        btn_font = ("Arial", scale_font_size(9))

        btn_width = scale(110)
        btn_height = scale(135)

        left_panel = tk.Frame(self.canvas.get_tk_widget(), bg='#f0f0f0', relief='flat', bd=0)
        left_panel.place(relx=0.0, rely=0.5, anchor=tk.W, x=scale(5))

        back_btn = tk.Button(left_panel, text="Назад", image=self.back_icon, compound=tk.TOP,
                             font=btn_font, bg='#f0f0f0', relief='flat',
                             command=self.back_to_device_selector,
                             width=btn_width, height=btn_height)
        back_btn.pack(pady=scale(15), padx=scale(8))

        config_btn = tk.Button(left_panel, text="КОНФИГУРАЦИЯ", image=self.icon_config,
                               compound=tk.TOP, font=btn_font, bg='#f0f0f0', relief='flat',
                               command=self.open_config_window,
                               width=btn_width, height=btn_height)
        config_btn.pack(pady=scale(15), padx=scale(8))

        diag_btn = tk.Button(left_panel, text="ДИАГНОСТИКА", image=self.icon_diag,
                             compound=tk.TOP, font=btn_font, bg='#f0f0f0', relief='flat',
                             command=self.open_diagnostic_window,
                             width=btn_width, height=btn_height)
        diag_btn.pack(pady=scale(15), padx=scale(8))

        right_panel = tk.Frame(self.canvas.get_tk_widget(), bg='#f0f0f0', relief='flat', bd=0)
        right_panel.place(relx=1.0, rely=0.5, anchor=tk.E, x=-scale(5))

        btn_height_right = scale(135)

        calendar_btn = tk.Button(right_panel, text="СУТОЧНЫЙ\nФАЙЛ", image=self.icon_calendar,
                                 compound=tk.TOP, font=btn_font, bg='#f0f0f0', relief='flat',
                                 command=self.download_daily_file,
                                 width=btn_width, height=btn_height_right)
        calendar_btn.pack(pady=scale(15), padx=scale(8))

        log_server_btn = tk.Button(right_panel, text="ЛОГ\nСЕРВЕРА", image=self.icon_log_server,
                                   compound=tk.TOP, font=btn_font, bg='#f0f0f0', relief='flat',
                                   command=self.download_server_log,
                                   width=btn_width, height=btn_height_right)
        log_server_btn.pack(pady=scale(15), padx=scale(8))

        log_client_btn = tk.Button(right_panel, text="ЛОГ\nКЛИЕНТА", image=self.icon_log_client,
                                   compound=tk.TOP, font=btn_font, bg='#f0f0f0', relief='flat',
                                   command=self.download_client_log,
                                   width=btn_width, height=btn_height_right)
        log_client_btn.pack(pady=scale(15), padx=scale(8))

        bottom_frame = tk.Frame(self.canvas.get_tk_widget(), bg='#f0f0f0')
        bottom_frame.place(relx=0.5, rely=1.0, anchor=tk.S, y=-scale(10))

        ttk.Label(bottom_frame, text="РАСШИРЕННЫЙ АНАЛИЗ ДАННЫХ",
                  font=("Arial", scale_font_size(14), "bold")).pack(pady=scale(2))

        btn_bottom_frame = ttk.Frame(bottom_frame)
        btn_bottom_frame.pack(pady=scale(3))

        street_btn = ttk.Button(btn_bottom_frame, text="УЛИЦА", image=self.icon_street_big,
                                compound=tk.TOP, style='Big.TButton',
                                command=self.open_street_window)
        street_btn.pack(side=tk.LEFT, padx=scale(25))

        indoor_btn = ttk.Button(btn_bottom_frame, text="ПОМЕЩЕНИЕ", image=self.icon_house_big,
                                compound=tk.TOP, style='Big.TButton',
                                command=self.open_indoor_window)
        indoor_btn.pack(side=tk.LEFT, padx=scale(25))

        custom_btn = ttk.Button(btn_bottom_frame, text="НАСТРАИВАЕМЫЙ", image=self.icon_settings_big,
                                compound=tk.TOP, style='Big.TButton',
                                command=self.show_custom_menu)
        custom_btn.pack(side=tk.LEFT, padx=scale(25))

        style = ttk.Style()
        style.configure('Big.TButton', font=('Arial', scale_font_size(14)))

    def reset_display(self):
        now_ts = datetime.now().timestamp()
        self.last_reset_timestamp = now_ts
        reset_interval = self.config.get("reset_interval", 3600)
        self.next_reset_time = now_ts + reset_interval
        self.config['next_reset_time'] = self.next_reset_time
        device_data_manager.set_config(self.device_name, self.config)
        self.all_records = []

        self.line_temp.set_data([], [])
        self.line_hum.set_data([], [])
        self.line_press.set_data([], [])

        for ax in [self.ax_temp, self.ax_hum, self.ax_press]:
            ax.relim()
            ax.autoscale_view()

        self.stat_temp_label.set_text("Температура\nмин: --\nмакс: --\nсреднее: --")
        self.stat_hum_label.set_text("Влажность\nмин: --\nмакс: --\nсреднее: --")
        self.stat_press_label.set_text("Давление\nмин: --\nмакс: --\nсреднее: --")

        self.time_label.config(text="(по состоянию на --:--)")
        self.temp_label.config(text="Температура: -- °C")
        self.hum_label.config(text="Влажность: -- %")
        self.press_label.config(text="Давление: -- мм рт.ст.")

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
        except Exception as e:
            log_error(f"Ошибка сохранения снапшота: {e}")

    def update_dashboard(self):
        if not self.root or not self.root.winfo_exists():
            return
        self.check_reset_needed()
        if not self.all_records:
            self.fig.canvas.draw_idle()
            return

        recent = self.all_records
        last = recent[-1]

        self.time_label.config(text=f"(по состоянию на {last['datetime'].strftime('%H:%M')})")
        self.temp_label.config(text=f"Температура: {last['temperature']:.1f} °C")
        self.hum_label.config(text=f"Влажность: {last['humidity']:.1f} %")
        self.press_label.config(text=f"Давление: {last['pressure']:.1f} мм рт.ст.")

        x = mdates.date2num([r['datetime'] for r in recent])
        self.line_temp.set_data(x, [r['temperature'] for r in recent])
        self.line_hum.set_data(x, [r['humidity'] for r in recent])
        self.line_press.set_data(x, [r['pressure'] for r in recent])

        for ax in [self.ax_temp, self.ax_hum, self.ax_press]:
            ax.relim()
            ax.autoscale_view()
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        from utils.stats import calculate_stats
        stats = calculate_stats(recent)
        if stats:
            self.stat_temp_label.set_text(
                f"Температура\nмин: {stats['temp']['min']:.1f}°C\nмакс: {stats['temp']['max']:.1f}°C\nсреднее: {stats['temp']['avg']:.1f}°C")
            self.stat_hum_label.set_text(
                f"Влажность\nмин: {stats['hum']['min']:.1f}%\nмакс: {stats['hum']['max']:.1f}%\nсреднее: {stats['hum']['avg']:.1f}%")
            self.stat_press_label.set_text(
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
            log_info(f"Интервал сброса изменён: {old_interval // 60} → {new_interval // 60} минут")

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
        menu = tk.Menu(self.root, tearoff=0, font=("Arial", scale_font_size(14)))
        for m in self.mode_manager.get_modes():
            sub = tk.Menu(menu, tearoff=0, font=("Arial", scale_font_size(14)))
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
        top.geometry(f"{scale(350)}x{scale(300)}")
        top.resizable(False, False)

        try:
            from tkcalendar import Calendar
            cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd', showweeknumbers=False,
                           weekendbackground='lightgray', foreground='black', normalbackground='white',
                           weekendforeground='black', selectbackground='blue', selectforeground='white',
                           headersbackground='lightgray', headersforeground='black', background='white',
                           bordercolor='lightgray', othermonthforeground='gray', othermonthbackground='white',
                           selectborderwidth=1)
            for date_str in available_dates:
                try:
                    cal.calevent_create(datetime.strptime(date_str, '%Y-%m-%d'), 'available', 'available')
                except:
                    pass
            cal.tag_config('available', background='lightgreen', foreground='black')
            cal.pack(pady=scale(10))

            info_label = ttk.Label(top, text="Зелёные дни — файл есть\nБелые — файла нет",
                                   font=("Arial", scale_font_size(9)), foreground="gray")
            info_label.pack(pady=scale(5))

            btn_frame = ttk.Frame(top)
            btn_frame.pack(pady=scale(10))
            ttk.Button(btn_frame, text="Скачать", command=do_download).pack(side='left', padx=scale(5))
            ttk.Button(btn_frame, text="Отмена", command=top.destroy).pack(side='left', padx=scale(5))
        except ImportError:
            ttk.Label(top, text="Библиотека tkcalendar не установлена\npip install tkcalendar",
                      font=("Arial", scale_font_size(10)), foreground="red").pack(pady=scale(20))
            ttk.Button(top, text="Закрыть", command=top.destroy).pack()

    def download_server_log(self):
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
            messagebox.showerror("Ошибка", "Лог клиента не найден")
            return
        try:
            shutil.copy2(local_log_path, downloads_path)
            messagebox.showinfo("Успех", f"Лог клиента сохранён в:\n{downloads_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать лог клиента:\n{e}")