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


class IndoorWindow:

    def __init__(self, parent, records, get_records_func=None):
        self.parent = parent
        self.get_records_func = get_records_func
        self.window = tk.Toplevel(parent)
        self.window.title("Анализ данных - Помещение")
        self.window.geometry("1000x800")
        self.window.minsize(900, 700)

        self.records = records
        self.current_data = records[-1] if records else None
        self.auto_update = True

        self.cond_risk = tk.StringVar(value="--")
        self.mold_risk = tk.StringVar(value="--")

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

        self.events_container = None
        self.rec_container = None

        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_analysis()
        self.start_auto_update()

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
            if self.get_records_func:
                self.records = self.get_records_func(2)
                self.update_analysis()
            self.schedule_update()

    def stop_auto_update(self):
        self.auto_update = False

    def on_closing(self):
        self.stop_auto_update()
        self.window.destroy()

    def load_recommendations(self):
        rec_file = os.path.join(RECOMMENDATIONS_DIR, 'recommendations_indoor.json')
        try:
            with open(rec_file, 'r', encoding='utf-8') as f:
                self.rec_data = json.load(f)
        except FileNotFoundError:
            self.rec_data = {
                "default": {"text": "Рекомендации не загружены", "icon": "⚠️"}
            }

    def setup_ui(self):
        title = ttk.Label(self.scrollable_frame, text="РЕЖИМ: ПОМЕЩЕНИЕ",
                          font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=15)

        ttk.Separator(self.scrollable_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky='ew', pady=5)

        self.setup_current_data()
        self.setup_statistics()
        self.setup_microclimate()
        self.setup_trends()
        self.setup_events()
        self.setup_recommendations()

        self.update_time_var = tk.StringVar(value="Последнее обновление: только что")
        update_label = ttk.Label(self.scrollable_frame, textvariable=self.update_time_var,
                                 font=("Arial", 10, "italic"))
        update_label.grid(row=21, column=0, columnspan=2, pady=5)

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

    def setup_microclimate(self):
        micro_frame = ttk.LabelFrame(self.scrollable_frame, text="ОЦЕНКА МИКРОКЛИМАТА", padding=10)
        micro_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        micro_frame.columnconfigure(1, weight=1)

        self.temp_rating = tk.StringVar(value="--")
        self.hum_rating = tk.StringVar(value="--")
        self.cond_risk = tk.StringVar(value="--")
        self.mold_risk = tk.StringVar(value="--")

        ttk.Label(micro_frame, text="Температура:", font=("Arial", 11)).grid(row=0, column=0, sticky='w')
        ttk.Label(micro_frame, textvariable=self.temp_rating, font=("Arial", 11, "bold")).grid(row=0, column=1, sticky='w')

        ttk.Label(micro_frame, text="Влажность:", font=("Arial", 11)).grid(row=1, column=0, sticky='w')
        ttk.Label(micro_frame, textvariable=self.hum_rating, font=("Arial", 11, "bold")).grid(row=1, column=1, sticky='w')

        ttk.Label(micro_frame, text="Риск конденсации:", font=("Arial", 11)).grid(row=2, column=0, sticky='w')
        ttk.Label(micro_frame, textvariable=self.cond_risk, font=("Arial", 11, "bold")).grid(row=2, column=1, sticky='w')

        ttk.Label(micro_frame, text="Риск плесени:", font=("Arial", 11)).grid(row=3, column=0, sticky='w')
        ttk.Label(micro_frame, textvariable=self.mold_risk, font=("Arial", 11, "bold")).grid(row=3, column=1, sticky='w')

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
        events_frame = ttk.LabelFrame(self.scrollable_frame, text="НАБЛЮДАЕМЫЕ ЯВЛЕНИЯ В ПОМЕЩЕНИИ", padding=10)
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

    def calculate_dew_point(self, T, H):
        a = 17.27
        b = 237.7
        alpha = (a * T) / (b + T) + math.log(H / 100)
        Td = (b * alpha) / (a - alpha)
        return Td

    def get_season(self):
        month = datetime.now().month
        return "winter" if month in [10, 11, 12, 1, 2, 3, 4] else "summer"

    def evaluate_temperature(self, T: float, season: str) -> str:
        if season == "winter":
            if 20 <= T <= 22:
                return "Оптимально"
            elif 18 <= T < 20 or 22 < T <= 24:
                return "Допустимо"
            elif T < 18:
                return "Неудовлетворительно (слишком холодно)"
            else:
                return "Неудовлетворительно (слишком жарко)"
        else:
            if 22 <= T <= 25:
                return "Оптимально"
            elif 20 <= T < 22 or 25 < T <= 28:
                return "Допустимо"
            elif T < 20:
                return "Неудовлетворительно (слишком холодно)"
            else:
                return "Неудовлетворительно (слишком жарко)"

    def if_too_hot(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False
        T = self.records[-1]['temperature']
        season = self.get_season()
        if season == "winter":
            return T > 24.0
        else:
            return T > 28.0

    def if_too_cold(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False
        T = self.records[-1]['temperature']
        season = self.get_season()
        if season == "winter":
            return T < 18.0
        else:
            return T < 20.0

    def evaluate_humidity(self, H, season):
        if season == "winter":
            if 30 <= H <= 45:
                return "Оптимально"
            elif 45 < H <= 60:
                return "Сухо"
            elif H < 30:
                return "Неудовлетворительно (слишком сухо)"
            else:
                return "Неудовлетворительно (слишком влажно)"
        else:
            if 30 <= H <= 60:
                return "Оптимально"
            elif 60 < H <= 65:
                return "Допустимо"
            elif H < 30:
                return "Неудовлетворительно (слишком сухо)"
            else:
                return "Неудовлетворительно (слишком влажно)"

    def is_too_wet(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False
        H = self.records[-1]['humidity']
        season = self.get_season()
        if season == "winter":
            return H > 60.0
        else:
            return H > 65.0

    def is_too_dry(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False
        H = self.records[-1]['humidity']
        return H < 30.0

    def heat_index(self, T_c: float, RH: float) -> float:
        T_f = T_c * 9.0 / 5.0 + 32.0
        HI = (-42.379 + 2.04901523 * T_f + 10.14333127 * RH -
              0.22475541 * T_f * RH - 0.00683783 * T_f * T_f -
              0.05481717 * RH * RH + 0.00122874 * T_f * T_f * RH +
              0.00085282 * T_f * RH * RH - 0.00000199 * T_f * T_f * RH * RH)
        if 13 > RH and 80 <= T_f <= 112:
            adjustment = ((13 - RH) / 4.0) * math.sqrt((17 - abs(T_f - 95)) / 17.0)
            HI -= adjustment
        if RH > 85 and 80 <= T_f <= 87:
            adjustment = ((RH - 85) / 10.0) * ((87 - T_f) / 5.0)
            HI += adjustment
        if HI < 80:
            HI = 0.5 * (T_f + 61.0 + ((T_f - 68.0) * 1.2) + (RH * 0.094))
        return (HI - 32.0) * 5.0 / 9.0

    def if_stuffy(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False
        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        if H <= 0 or H > 100:
            return False
        hi = self.heat_index(T, H)
        return hi >= 27.0

    def H_mold(self, T: float) -> float:
        h = 0.20 * T * T - 0.9 * T + 20
        return min(h, 100.0)

    def H_cond(self, T: float) -> float:
        h = 0.09924 * T * T + 1.7653 * T + 25
        return min(h, 100.0)

    def if_condensation(self) -> bool:
        if not self.records:
            return False
        T = self.records[-1]['temperature']
        H = self.records[-1]['humidity']
        if T < 0.0:
            return False
        h_cond = self.H_cond(T)
        return H >= h_cond

    def if_mold(self) -> bool:
        if not self.records:
            return False
        T = self.records[-1]['temperature']
        H = self.records[-1]['humidity']
        if T < 0.0:
            return False
        h_mold = self.H_mold(T)
        return H >= h_mold

    def is_temp_increase(self) -> bool:
        if not self.records or len(self.records) < 2:
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
        delta_T = current_T - prev_record['temperature']
        return delta_T > 3.0

    def is_temp_decrease(self) -> bool:
        if not self.records or len(self.records) < 2:
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
        delta_T = current_T - prev_record['temperature']
        return delta_T < -3.0

    def if_humidity_increase(self) -> bool:
        if not self.records or len(self.records) < 2:
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
        delta_H = current_H - prev_record['humidity']
        return delta_H > 10.0

    def if_humidity_decrease(self) -> bool:
        if not self.records or len(self.records) < 2:
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
        delta_H = current_H - prev_record['humidity']
        return delta_H < -10.0

    def collect_events(self, T, H, P, Td, T_trend, H_trend, P_trend, season):
        events = []
        if self.if_too_hot():
            events.append("Слишком жарко")
        if self.if_too_cold():
            events.append("Слишком холодно")
        if self.is_temp_increase():
            events.append("Резкий рост температуры")
        if self.is_temp_decrease():
            events.append("Резкое падение температуры")
        if self.is_too_wet():
            events.append("Слишком влажно")
        if self.is_too_dry():
            events.append("Слишком сухо")
        if self.if_humidity_increase():
            events.append("Резкий рост влажности")
        if self.if_humidity_decrease():
            events.append("Резкое падение влажности")
        if self.if_stuffy():
            events.append("Душно в помещении")
        if self.if_condensation():
            events.append("Возможна конденсация")
        if self.if_mold():
            events.append("Риск образования плесени")
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

            self.temp_rating.set("--")
            self.hum_rating.set("--")
            self.cond_risk.set("--")
            self.mold_risk.set("--")

            self.trend_t.set("--")
            self.trend_h.set("--")
            self.trend_p.set("--")

            for widget in self.events_container.winfo_children():
                widget.destroy()
            ttk.Label(self.events_container, text="Нет данных для анализа", font=("Arial", 12, "italic")).pack(pady=10)

            for widget in self.rec_container.winfo_children():
                widget.destroy()
            ttk.Label(self.rec_container, text="Нет рекомендаций", font=("Arial", 12, "italic")).pack(pady=10)

            self.update_time_var.set("Нет достаточных данных для анализа")
            self.window.update_idletasks()
            self.window.update()
            return

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        dt = last['datetime']
        season = self.get_season()

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

        self.temp_rating.set(self.evaluate_temperature(T, season))
        self.hum_rating.set(self.evaluate_humidity(H, season))

        cond_risk_text = "Высокий" if self.if_condensation() else "Низкий"
        mold_risk_text = "Высокий" if self.if_mold() else "Низкий"
        self.cond_risk.set(cond_risk_text)
        self.mold_risk.set(mold_risk_text)

        events = self.collect_events(T, H, P, Td, T_trend, H_trend, P_trend, season)

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

        recommendations = []
        for event in events:
            found = False
            for category in self.rec_data.values():
                if event in category:
                    rec = category[event]
                    recommendations.append(f"{rec.get('icon', '•')} {rec['text']}")
                    found = True
                    break
            if not found:
                recommendations.append(f"• {event}")

        for widget in self.rec_container.winfo_children():
            widget.destroy()

        if recommendations:
            for rec_line in recommendations:
                frame = ttk.Frame(self.rec_container)
                frame.pack(fill='x', pady=6, padx=5)

                icon = rec_line[:2].strip() if len(rec_line) > 2 else "•"
                text_part = rec_line[2:].strip() if len(rec_line) > 2 else rec_line

                ttk.Label(frame, text=icon, font=("Segoe UI Emoji", 16)).pack(side='left', padx=(0, 10))
                ttk.Label(frame, text=text_part, wraplength=580, justify='left').pack(side='left', expand=True, fill='x')
        else:
            ttk.Label(self.rec_container, text="Рекомендаций нет", font=("Arial", 12, "italic")).pack(pady=10)

        self.update_time_var.set(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
        self.window.update_idletasks()
        self.window.update()