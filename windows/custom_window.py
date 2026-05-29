#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import json
import math
import os
from datetime import datetime, timedelta
from statistics import mean

from config.settings import RECOMMENDATIONS_DIR
from utils.stats import calculate_stats


class CustomWindow:

    def __init__(self, parent, records, mode_data, get_records_func=None):
        self.parent = parent
        self.get_records_func = get_records_func
        self.window = tk.Toplevel(parent)
        self.window.title(f"Анализ данных - {mode_data.get('name', 'Настраиваемый')}")
        self.window.geometry("1000x800")
        self.window.minsize(900, 700)

        self.records = records
        self.mode_data = mode_data

        self.min_temp = mode_data.get('t_min')
        self.max_temp = mode_data.get('t_max')
        self.crit_percent_temp = mode_data.get('t_crit')

        self.min_hum = mode_data.get('h_min')
        self.max_hum = mode_data.get('h_max')
        self.crit_percent_hum = mode_data.get('h_crit')

        self.min_press = mode_data.get('p_min')
        self.max_press = mode_data.get('p_max')
        self.crit_percent_press = mode_data.get('p_crit')

        self.auto_update = True
        self.load_recommendations()

        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_analysis()
        self.start_auto_update()

    def load_recommendations(self):
        rec_file = os.path.join(RECOMMENDATIONS_DIR, 'recommendations_custom.json')
        try:
            with open(rec_file, 'r', encoding='utf-8') as f:
                self.rec_data = json.load(f)
        except FileNotFoundError:
            self.rec_data = {
                "default": {"text": "Рекомендации не загружены", "icon": "⚠️"}
            }

    def setup_ui(self):
        # Заголовок
        title = ttk.Label(self.scrollable_frame, text=f"РЕЖИМ: {self.mode_data.get('name', 'Настраиваемый')}",
                          font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=15)

        ttk.Separator(self.scrollable_frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)

        self.setup_current_data()

        self.setup_statistics()

        self.setup_compliance()

        self.setup_trends()

        self.setup_events()

        self.setup_recommendations()

        self.update_time_var = tk.StringVar(value="Последнее обновление: только что")
        update_label = ttk.Label(self.scrollable_frame, textvariable=self.update_time_var,
                                 font=("Arial", 10, "italic"))
        update_label.grid(row=22, column=0, columnspan=2, pady=5)

    def setup_current_data(self):
        current_frame = ttk.LabelFrame(self.scrollable_frame, text="ТЕКУЩИЕ ДАННЫЕ", padding=10)
        current_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        current_frame.columnconfigure(1, weight=1)

        self.time_var = tk.StringVar(value="--:--")
        self.temp_var = tk.StringVar(value="--")
        self.hum_var = tk.StringVar(value="--")
        self.press_var = tk.StringVar(value="--")
        self.dew_var = tk.StringVar(value="--")

        ttk.Label(current_frame, text="Время измерения:", font=("Arial", 11)).grid(row=0, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.time_var, font=("Arial", 11, "bold")).grid(row=0, column=1, sticky='w')

        ttk.Label(current_frame, text="Температура:", font=("Arial", 11)).grid(row=1, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.temp_var, font=("Arial", 11, "bold")).grid(row=1, column=1, sticky='w')

        ttk.Label(current_frame, text="Влажность:", font=("Arial", 11)).grid(row=2, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.hum_var, font=("Arial", 11, "bold")).grid(row=2, column=1, sticky='w')

        ttk.Label(current_frame, text="Давление:", font=("Arial", 11)).grid(row=3, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.press_var, font=("Arial", 11, "bold")).grid(row=3, column=1, sticky='w')

        ttk.Label(current_frame, text="Точка росы:", font=("Arial", 11)).grid(row=4, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.dew_var, font=("Arial", 11, "bold")).grid(row=4, column=1, sticky='w')

    def setup_statistics(self):
        stats_frame = ttk.LabelFrame(self.scrollable_frame, text="СТАТИСТИКА ЗА ПОСЛЕДНИЙ ЧАС", padding=15)
        stats_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=10, pady=5)

        for i in range(3):
            stats_frame.columnconfigure(i, weight=1, minsize=180)

        ttk.Label(stats_frame, text="ТЕМПЕРАТУРА", font=("Arial", 11, "bold")).grid(row=0, column=0, pady=5)
        ttk.Label(stats_frame, text="ВЛАЖНОСТЬ", font=("Arial", 11, "bold")).grid(row=0, column=1, pady=5)
        ttk.Label(stats_frame, text="ДАВЛЕНИЕ", font=("Arial", 11, "bold")).grid(row=0, column=2, pady=5)

        self.t_min = tk.StringVar(value="--")
        self.t_max = tk.StringVar(value="--")
        self.t_avg = tk.StringVar(value="--")
        self.h_min = tk.StringVar(value="--")
        self.h_max = tk.StringVar(value="--")
        self.h_avg = tk.StringVar(value="--")
        self.p_min = tk.StringVar(value="--")
        self.p_max = tk.StringVar(value="--")
        self.p_avg = tk.StringVar(value="--")

        frame1 = ttk.Frame(stats_frame)
        frame1.grid(row=1, column=0, sticky='w', padx=10, pady=2)
        ttk.Label(frame1, text="мин:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame1, textvariable=self.t_min, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame2 = ttk.Frame(stats_frame)
        frame2.grid(row=2, column=0, sticky='w', padx=10, pady=2)
        ttk.Label(frame2, text="макс:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame2, textvariable=self.t_max, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame3 = ttk.Frame(stats_frame)
        frame3.grid(row=3, column=0, sticky='w', padx=10, pady=2)
        ttk.Label(frame3, text="среднее:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame3, textvariable=self.t_avg, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame4 = ttk.Frame(stats_frame)
        frame4.grid(row=1, column=1, sticky='w', padx=10, pady=2)
        ttk.Label(frame4, text="мин:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame4, textvariable=self.h_min, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame5 = ttk.Frame(stats_frame)
        frame5.grid(row=2, column=1, sticky='w', padx=10, pady=2)
        ttk.Label(frame5, text="макс:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame5, textvariable=self.h_max, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame6 = ttk.Frame(stats_frame)
        frame6.grid(row=3, column=1, sticky='w', padx=10, pady=2)
        ttk.Label(frame6, text="среднее:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame6, textvariable=self.h_avg, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame7 = ttk.Frame(stats_frame)
        frame7.grid(row=1, column=2, sticky='w', padx=10, pady=2)
        ttk.Label(frame7, text="мин:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame7, textvariable=self.p_min, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame8 = ttk.Frame(stats_frame)
        frame8.grid(row=2, column=2, sticky='w', padx=10, pady=2)
        ttk.Label(frame8, text="макс:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame8, textvariable=self.p_max, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

        frame9 = ttk.Frame(stats_frame)
        frame9.grid(row=3, column=2, sticky='w', padx=10, pady=2)
        ttk.Label(frame9, text="среднее:", font=("Arial", 11)).pack(side='left')
        ttk.Label(frame9, textvariable=self.p_avg, font=("Arial", 11, "bold")).pack(side='left', padx=(5, 0))

    def setup_compliance(self):
        comp_frame = ttk.LabelFrame(self.scrollable_frame, text="ОЦЕНКА СООТВЕТСТВИЯ НОРМАМ", padding=10)
        comp_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        comp_frame.columnconfigure(1, weight=1)

        self.temp_comp = tk.StringVar(value="--")
        self.hum_comp = tk.StringVar(value="--")
        self.press_comp = tk.StringVar(value="--")

        ttk.Label(comp_frame, text="Температура:", font=("Arial", 11)).grid(row=0, column=0, sticky='w')
        ttk.Label(comp_frame, textvariable=self.temp_comp, font=("Arial", 11, "bold")).grid(row=0, column=1, sticky='w')

        ttk.Label(comp_frame, text="Влажность:", font=("Arial", 11)).grid(row=1, column=0, sticky='w')
        ttk.Label(comp_frame, textvariable=self.hum_comp, font=("Arial", 11, "bold")).grid(row=1, column=1, sticky='w')

        ttk.Label(comp_frame, text="Давление:", font=("Arial", 11)).grid(row=2, column=0, sticky='w')
        ttk.Label(comp_frame, textvariable=self.press_comp, font=("Arial", 11, "bold")).grid(row=2, column=1, sticky='w')

    def setup_trends(self):
        trend_frame = ttk.LabelFrame(self.scrollable_frame, text="ТРЕНДЫ (за 3 часа)", padding=10)
        trend_frame.grid(row=5, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        trend_frame.columnconfigure(1, weight=1)

        self.trend_t = tk.StringVar(value="--")
        self.trend_h = tk.StringVar(value="--")
        self.trend_p = tk.StringVar(value="--")

        ttk.Label(trend_frame, text="Температура:", font=("Arial", 11)).grid(row=0, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_t, font=("Arial", 11, "bold")).grid(row=0, column=1, sticky='w')

        ttk.Label(trend_frame, text="Влажность:", font=("Arial", 11)).grid(row=1, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_h, font=("Arial", 11, "bold")).grid(row=1, column=1, sticky='w')

        ttk.Label(trend_frame, text="Давление:", font=("Arial", 11)).grid(row=2, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_p, font=("Arial", 11, "bold")).grid(row=2, column=1, sticky='w')

    def setup_events(self):
        events_frame = ttk.LabelFrame(self.scrollable_frame, text="НАБЛЮДАЕМЫЕ ЯВЛЕНИЯ", padding=10)
        events_frame.grid(row=6, column=0, columnspan=2, sticky='ew', padx=10, pady=5)

        self.events_container = ttk.Frame(events_frame)
        self.events_container.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Label(self.events_container, text="Нет наблюдаемых явлений", font=("Arial", 12, "italic")).pack(pady=10)

    def setup_recommendations(self):
        rec_frame = ttk.LabelFrame(self.scrollable_frame, text="РЕКОМЕНДАЦИИ", padding=10)
        rec_frame.grid(row=7, column=0, columnspan=2, sticky='ew', padx=10, pady=5)

        self.rec_container = ttk.Frame(rec_frame)
        self.rec_container.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Label(self.rec_container, text="Рекомендаций нет", font=("Arial", 12, "italic")).pack(pady=10)

    def on_closing(self):
        self.auto_update = False
        self.window.destroy()

    def refresh_data(self):
        if self.get_records_func:
            self.records = self.get_records_func()
        self.update_analysis()

    def start_auto_update(self):
        self.auto_update = True
        self.schedule_update()

    def schedule_update(self):
        if self.auto_update:
            self.window.after(60000, self.do_auto_update)

    def do_auto_update(self):
        if self.auto_update and self.window.winfo_exists():
            self.refresh_data()
            self.schedule_update()

    def calculate_dew_point(self, T, H):
        a = 17.27
        b = 237.7
        alpha = (a * T) / (b + T) + math.log(H / 100)
        Td = (b * alpha) / (a - alpha)
        return Td

    def if_temp_under_norm(self) -> bool:
        if not self.records or self.min_temp is None:
            return False
        return self.records[-1]['temperature'] < self.min_temp

    def if_temp_over_norm(self) -> bool:
        if not self.records or self.max_temp is None:
            return False
        return self.records[-1]['temperature'] > self.max_temp

    def if_hum_under_norm(self) -> bool:
        if not self.records or self.min_hum is None:
            return False
        return self.records[-1]['humidity'] < self.min_hum

    def if_hum_over_norm(self) -> bool:
        if not self.records or self.max_hum is None:
            return False
        return self.records[-1]['humidity'] > self.max_hum

    def if_press_under_norm(self) -> bool:
        if not self.records or self.min_press is None:
            return False
        return self.records[-1]['pressure'] < self.min_press

    def if_press_over_norm(self) -> bool:
        if not self.records or self.max_press is None:
            return False
        return self.records[-1]['pressure'] > self.max_press

    def if_temp_critical(self) -> bool:
        if not self.records or self.min_temp is None or self.max_temp is None or self.crit_percent_temp is None:
            return False
        return self.check_critical(self.records[-1]['temperature'], self.min_temp, self.max_temp, self.crit_percent_temp)

    def if_hum_critical(self) -> bool:
        if not self.records or self.min_hum is None or self.max_hum is None or self.crit_percent_hum is None:
            return False
        return self.check_critical(self.records[-1]['humidity'], self.min_hum, self.max_hum, self.crit_percent_hum)

    def if_press_critical(self) -> bool:
        if not self.records or self.min_press is None or self.max_press is None or self.crit_percent_press is None:
            return False
        return self.check_critical(self.records[-1]['pressure'], self.min_press, self.max_press, self.crit_percent_press)

    def if_temp_long_deviation(self) -> bool:
        if not self.records or self.min_temp is None or self.max_temp is None:
            return False

        last = self.records[-1]
        current_T = last['temperature']
        current_time = last['datetime']

        if self.min_temp <= current_T <= self.max_temp:
            return False

        time_limit = current_time - timedelta(hours=3)

        for r in reversed(self.records):
            if r['datetime'] < time_limit:
                break
            T = r['temperature']
            if self.min_temp <= T <= self.max_temp:
                return False
        return True

    def if_hum_long_deviation(self) -> bool:
        if not self.records or self.min_hum is None or self.max_hum is None:
            return False

        last = self.records[-1]
        current_H = last['humidity']
        current_time = last['datetime']

        if self.min_hum <= current_H <= self.max_hum:
            return False

        time_limit = current_time - timedelta(hours=3)

        for r in reversed(self.records):
            if r['datetime'] < time_limit:
                break
            H = r['humidity']
            if self.min_hum <= H <= self.max_hum:
                return False
        return True

    def if_press_long_deviation(self) -> bool:
        if not self.records or self.min_press is None or self.max_press is None:
            return False

        last = self.records[-1]
        current_P = last['pressure']
        current_time = last['datetime']

        if self.min_press <= current_P <= self.max_press:
            return False

        time_limit = current_time - timedelta(hours=3)

        for r in reversed(self.records):
            if r['datetime'] < time_limit:
                break
            P = r['pressure']
            if self.min_press <= P <= self.max_press:
                return False
        return True

    def if_temp_increase(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_T = last['temperature']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_T - prev_record['temperature'] > 3.0

    def if_temp_decrease(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_T = last['temperature']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_T - prev_record['temperature'] < -3.0

    def if_hum_increase(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_H = last['humidity']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_H - prev_record['humidity'] > 10.0

    def if_hum_decrease(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_H = last['humidity']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_H - prev_record['humidity'] < -10.0

    def if_press_increase(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_P = last['pressure']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_P - prev_record['pressure'] > 3.0

    def if_press_decrease(self) -> bool:
        if len(self.records) < 2:
            return False

        last = self.records[-1]
        current_P = last['pressure']
        current_time = last['datetime']

        time_3h_ago = current_time - timedelta(hours=3)
        prev_record = None

        for r in reversed(self.records):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                break

        if prev_record is None:
            return False

        return current_P - prev_record['pressure'] < -3.0

    def check_critical(self, value, min_val, max_val, crit_percent):
        if crit_percent is None or min_val is None or max_val is None:
            return False

        if value < min_val:
            deviation = (min_val - value) / min_val * 100
            return deviation > crit_percent
        elif value > max_val:
            deviation = (value - max_val) / max_val * 100
            return deviation > crit_percent
        return False

    def check_compliance(self, value, min_val, max_val) -> str:
        if min_val is None or max_val is None:
            return "Норма не задана"
        if value < min_val:
            return "Ниже нормы"
        elif value > max_val:
            return "Выше нормы"
        else:
            return "В норме"

    def collect_events(self, T, H, P, Td, T_trend, H_trend, P_trend):
        events = []

        if self.if_temp_under_norm():
            events.append("Температура ниже нормы")
        if self.if_temp_over_norm():
            events.append("Температура выше нормы")
        if self.if_hum_under_norm():
            events.append("Влажность ниже нормы")
        if self.if_hum_over_norm():
            events.append("Влажность выше нормы")
        if self.if_press_under_norm():
            events.append("Давление ниже нормы")
        if self.if_press_over_norm():
            events.append("Давление выше нормы")

        if self.if_temp_critical():
            events.append("Критическое отклонение температуры")
        if self.if_hum_critical():
            events.append("Критическое отклонение влажности")
        if self.if_press_critical():
            events.append("Критическое отклонение давления")

        if self.if_temp_increase():
            events.append("Резкий рост температуры")
        if self.if_temp_decrease():
            events.append("Резкое падение температуры")
        if self.if_hum_increase():
            events.append("Резкий рост влажности")
        if self.if_hum_decrease():
            events.append("Резкое падение влажности")
        if self.if_press_increase():
            events.append("Резкий рост давления")
        if self.if_press_decrease():
            events.append("Резкое падение давления")

        if self.if_temp_long_deviation():
            events.append("Длительное отклонение температуры")
        if self.if_hum_long_deviation():
            events.append("Длительное отклонение влажности")
        if self.if_press_long_deviation():
            events.append("Длительное отклонение давления")

        return events

    def update_analysis(self):
        if not self.records or len(self.records) < 2:
            self.time_var.set("--:--")
            self.temp_var.set("--")
            self.hum_var.set("--")
            self.press_var.set("--")
            self.dew_var.set("--")

            self.t_min.set("--")
            self.t_max.set("--")
            self.t_avg.set("--")
            self.h_min.set("--")
            self.h_max.set("--")
            self.h_avg.set("--")
            self.p_min.set("--")
            self.p_max.set("--")
            self.p_avg.set("--")

            self.temp_comp.set("--")
            self.hum_comp.set("--")
            self.press_comp.set("--")

            self.trend_t.set("--")
            self.trend_h.set("--")
            self.trend_p.set("--")

            for widget in self.events_container.winfo_children():
                widget.destroy()
            ttk.Label(self.events_container, text="Нет данных", font=("Arial", 12, "italic")).pack(pady=10)

            for widget in self.rec_container.winfo_children():
                widget.destroy()
            ttk.Label(self.rec_container, text="Нет рекомендаций", font=("Arial", 12, "italic")).pack(pady=10)

            self.update_time_var.set("Нет достаточных данных для анализа")
            return

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        dt = last['datetime']

        Td = self.calculate_dew_point(T, H)

        cutoff_time_3h = datetime.now() - timedelta(hours=3)
        oldest_in_window = None
        newest_in_window = None

        for r in self.records:
            if r['datetime'] >= cutoff_time_3h:
                if oldest_in_window is None or r['datetime'] < oldest_in_window['datetime']:
                    oldest_in_window = r
                if newest_in_window is None or r['datetime'] > newest_in_window['datetime']:
                    newest_in_window = r

        if oldest_in_window and newest_in_window and oldest_in_window != newest_in_window:
            P_trend = newest_in_window['pressure'] - oldest_in_window['pressure']
            T_trend = newest_in_window['temperature'] - oldest_in_window['temperature']
            H_trend = newest_in_window['humidity'] - oldest_in_window['humidity']

            self.trend_p.set(f"{P_trend:+.1f} мм рт.ст.")
            self.trend_t.set(f"{T_trend:+.1f} °C")
            self.trend_h.set(f"{H_trend:+.1f} %")
        else:
            self.trend_p.set("--")
            self.trend_t.set("--")
            self.trend_h.set("--")
            T_trend = 0.0
            H_trend = 0.0
            P_trend = 0.0

        self.time_var.set(dt.strftime("%H:%M"))
        self.temp_var.set(f"{T:.1f} °C")
        self.hum_var.set(f"{H:.1f} %")
        self.press_var.set(f"{P:.1f} мм рт.ст.")
        self.dew_var.set(f"{Td:.1f} °C")

        # ===== СТАТИСТИКА ЗА ПОСЛЕДНИЙ ЧАС =====
        cutoff_time_1h = datetime.now() - timedelta(hours=1)
        recent_records = [r for r in self.records if r['datetime'] >= cutoff_time_1h]

        if recent_records:
            stats = calculate_stats(recent_records)
            if stats:
                self.t_min.set(f"{stats['temp']['min']:.1f}°C")
                self.t_max.set(f"{stats['temp']['max']:.1f}°C")
                self.t_avg.set(f"{stats['temp']['avg']:.1f}°C")
                self.h_min.set(f"{stats['hum']['min']:.1f}%")
                self.h_max.set(f"{stats['hum']['max']:.1f}%")
                self.h_avg.set(f"{stats['hum']['avg']:.1f}%")
                self.p_min.set(f"{stats['press']['min']:.1f}")
                self.p_max.set(f"{stats['press']['max']:.1f}")
                self.p_avg.set(f"{stats['press']['avg']:.1f}")
        else:
            self.t_min.set("--")
            self.t_max.set("--")
            self.t_avg.set("--")
            self.h_min.set("--")
            self.h_max.set("--")
            self.h_avg.set("--")
            self.p_min.set("--")
            self.p_max.set("--")
            self.p_avg.set("--")

        temp_status = self.check_compliance(T, self.min_temp, self.max_temp)
        hum_status = self.check_compliance(H, self.min_hum, self.max_hum)
        press_status = self.check_compliance(P, self.min_press, self.max_press)

        temp_crit = self.if_temp_critical()
        hum_crit = self.if_hum_critical()
        press_crit = self.if_press_critical()

        self.temp_comp.set(f"{temp_status} {'(критично)' if temp_crit else ''}")
        self.hum_comp.set(f"{hum_status} {'(критично)' if hum_crit else ''}")
        self.press_comp.set(f"{press_status} {'(критично)' if press_crit else ''}")

        events = self.collect_events(T, H, P, Td, T_trend, H_trend, P_trend)

        for widget in self.events_container.winfo_children():
            widget.destroy()

        if events:
            for event in sorted(set(events)):
                frame = ttk.Frame(self.events_container)
                frame.pack(fill='x', pady=4, padx=5)

                icon = "•"
                for category in self.rec_data.values():
                    if event in category:
                        icon = category[event].get("icon", "•")
                        break

                ttk.Label(frame, text=icon, font=("Segoe UI Emoji", 16)).pack(side='left', padx=(0, 10))
                ttk.Label(frame, text=event, wraplength=580, justify='left').pack(side='left', expand=True, fill='x')
        else:
            ttk.Label(self.events_container, text="Нет наблюдаемых явлений", font=("Arial", 12, "italic")).pack(pady=10)

        for widget in self.rec_container.winfo_children():
            widget.destroy()

        if events:
            for event in events:
                found = False
                for category in self.rec_data.values():
                    if event in category:
                        rec = category[event]
                        icon = rec.get('icon', '')
                        text = rec['text']
                        frame = ttk.Frame(self.rec_container)
                        frame.pack(fill='x', pady=6, padx=5)
                        if icon:
                            ttk.Label(frame, text=icon, font=("Segoe UI Emoji", 16)).pack(side='left', padx=(0, 10))
                        ttk.Label(frame, text=text, wraplength=580, justify='left').pack(side='left', expand=True, fill='x')
                        found = True
                        break
                if not found:
                    frame = ttk.Frame(self.rec_container)
                    frame.pack(fill='x', pady=6, padx=5)
                    ttk.Label(frame, text=event, wraplength=580, justify='left').pack(side='left', expand=True, fill='x')
        else:
            ttk.Label(self.rec_container, text="Рекомендаций нет", font=("Arial", 12, "italic")).pack(pady=10)

        self.update_time_var.set(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
        self.window.update_idletasks()
        self.window.update()