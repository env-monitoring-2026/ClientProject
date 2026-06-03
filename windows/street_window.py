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

from utils.scaling import scale, scale_font_size, center_window


class StreetWindow:

    def __init__(self, parent, records, get_records_func=None):
        self.parent = parent
        self.get_records_func = get_records_func
        self.window = tk.Toplevel(parent)
        self.window.title("Анализ данных - Улица")

        width = scale(1000)
        height = scale(800)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(scale(900), scale(700))
        center_window(self.window, width, height)

        self.records = records
        self.current_data = records[-1] if records else None
        self.auto_update = True

        self.load_recommendations()
        self.daily_precip_probs = {}

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
            self.refresh_data()
            self.schedule_update()

    def stop_auto_update(self):
        self.auto_update = False

    def on_closing(self):
        self.stop_auto_update()
        self.window.destroy()

    def load_recommendations(self):
        rec_file = os.path.join(RECOMMENDATIONS_DIR, 'recommendations_street.json')
        try:
            with open(rec_file, 'r', encoding='utf-8') as f:
                self.rec_data = json.load(f)
        except FileNotFoundError:
            self.rec_data = {
                "default": {"text": "Рекомендации не загружены", "icon": "⚠️"}
            }

    def setup_ui(self):
        title_font = ("Arial", scale_font_size(18), "bold")
        label_font = ("Arial", scale_font_size(11))
        bold_font = ("Arial", scale_font_size(11), "bold")
        small_font = ("Arial", scale_font_size(10), "italic")
        italic_font = ("Arial", scale_font_size(12), "italic")

        title = ttk.Label(self.scrollable_frame, text="РЕЖИМ: УЛИЦА",
                          font=title_font)
        title.grid(row=0, column=0, columnspan=2, pady=scale(15))

        ttk.Separator(self.scrollable_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky='ew', pady=scale(5))

        self.setup_current_data(label_font, bold_font)
        self.setup_statistics(label_font, bold_font)
        self.setup_weather_character(label_font, bold_font)
        self.setup_precipitation(label_font, bold_font)
        self.setup_trends(label_font, bold_font)
        self.setup_events(label_font, italic_font)
        self.setup_recommendations(label_font, italic_font)

        self.update_time_var = tk.StringVar(value="Последнее обновление: только что")
        update_label = ttk.Label(self.scrollable_frame, textvariable=self.update_time_var,
                                 font=small_font)
        update_label.grid(row=22, column=0, columnspan=2, pady=scale(5))

    def setup_current_data(self, label_font, bold_font):
        current_frame = ttk.LabelFrame(self.scrollable_frame, text="ТЕКУЩИЕ ДАННЫЕ",
                                       padding=scale(10))
        current_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))
        current_frame.columnconfigure(1, weight=1)

        self.time_var = tk.StringVar(value="--:--")
        self.temp_var = tk.StringVar(value="--")
        self.hum_var = tk.StringVar(value="--")
        self.press_var = tk.StringVar(value="--")
        self.dew_var = tk.StringVar(value="--")

        ttk.Label(current_frame, text="Время измерения:", font=label_font).grid(row=0, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.time_var, font=bold_font).grid(row=0, column=1, sticky='w')

        ttk.Label(current_frame, text="Температура:", font=label_font).grid(row=1, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.temp_var, font=bold_font).grid(row=1, column=1, sticky='w')

        ttk.Label(current_frame, text="Влажность:", font=label_font).grid(row=2, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.hum_var, font=bold_font).grid(row=2, column=1, sticky='w')

        ttk.Label(current_frame, text="Давление:", font=label_font).grid(row=3, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.press_var, font=bold_font).grid(row=3, column=1, sticky='w')

        ttk.Label(current_frame, text="Точка росы:", font=label_font).grid(row=4, column=0, sticky='w')
        ttk.Label(current_frame, textvariable=self.dew_var, font=bold_font).grid(row=4, column=1, sticky='w')

    def setup_statistics(self, label_font, bold_font):
        stats_frame = ttk.LabelFrame(self.scrollable_frame, text="СТАТИСТИКА ЗА ПОСЛЕДНИЙ ЧАС",
                                     padding=scale(15))
        stats_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))

        for i in range(3):
            stats_frame.columnconfigure(i, weight=1, minsize=scale(180))

        ttk.Label(stats_frame, text="ТЕМПЕРАТУРА", font=bold_font).grid(row=0, column=0, pady=scale(5))
        ttk.Label(stats_frame, text="ВЛАЖНОСТЬ", font=bold_font).grid(row=0, column=1, pady=scale(5))
        ttk.Label(stats_frame, text="ДАВЛЕНИЕ", font=bold_font).grid(row=0, column=2, pady=scale(5))

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
        frame1.grid(row=1, column=0, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame1, text="мин:", font=label_font).pack(side='left')
        ttk.Label(frame1, textvariable=self.t_min, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame2 = ttk.Frame(stats_frame)
        frame2.grid(row=2, column=0, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame2, text="макс:", font=label_font).pack(side='left')
        ttk.Label(frame2, textvariable=self.t_max, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame3 = ttk.Frame(stats_frame)
        frame3.grid(row=3, column=0, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame3, text="среднее:", font=label_font).pack(side='left')
        ttk.Label(frame3, textvariable=self.t_avg, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame4 = ttk.Frame(stats_frame)
        frame4.grid(row=1, column=1, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame4, text="мин:", font=label_font).pack(side='left')
        ttk.Label(frame4, textvariable=self.h_min, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame5 = ttk.Frame(stats_frame)
        frame5.grid(row=2, column=1, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame5, text="макс:", font=label_font).pack(side='left')
        ttk.Label(frame5, textvariable=self.h_max, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame6 = ttk.Frame(stats_frame)
        frame6.grid(row=3, column=1, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame6, text="среднее:", font=label_font).pack(side='left')
        ttk.Label(frame6, textvariable=self.h_avg, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame7 = ttk.Frame(stats_frame)
        frame7.grid(row=1, column=2, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame7, text="мин:", font=label_font).pack(side='left')
        ttk.Label(frame7, textvariable=self.p_min, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame8 = ttk.Frame(stats_frame)
        frame8.grid(row=2, column=2, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame8, text="макс:", font=label_font).pack(side='left')
        ttk.Label(frame8, textvariable=self.p_max, font=bold_font).pack(side='left', padx=(scale(5), 0))

        frame9 = ttk.Frame(stats_frame)
        frame9.grid(row=3, column=2, sticky='w', padx=scale(10), pady=scale(2))
        ttk.Label(frame9, text="среднее:", font=label_font).pack(side='left')
        ttk.Label(frame9, textvariable=self.p_avg, font=bold_font).pack(side='left', padx=(scale(5), 0))

    def setup_weather_character(self, label_font, bold_font):
        char_frame = ttk.LabelFrame(self.scrollable_frame, text="ХАРАКТЕР ВОЗДУШНЫХ МАСС", padding=scale(10))
        char_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))
        char_frame.columnconfigure(1, weight=1)

        self.weather_type = tk.StringVar(value="--")
        ttk.Label(char_frame, text="Тип:", font=label_font).grid(row=0, column=0, sticky='w')
        ttk.Label(char_frame, textvariable=self.weather_type, font=bold_font).grid(row=0, column=1, sticky='w')

    def setup_precipitation(self, label_font, bold_font):
        precip_frame = ttk.LabelFrame(self.scrollable_frame, text="ОСАДКИ", padding=scale(10))
        precip_frame.grid(row=5, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))

        self.precip_type = tk.StringVar(value="--")
        self.precip_prob = tk.StringVar(value="--")

        ttk.Label(precip_frame, text="Тип:", font=label_font).grid(row=0, column=0, sticky='w')
        ttk.Label(precip_frame, textvariable=self.precip_type, font=bold_font).grid(row=0, column=1, sticky='w')

        ttk.Label(precip_frame, text="Вероятность:", font=label_font).grid(row=1, column=0, sticky='w')
        ttk.Label(precip_frame, textvariable=self.precip_prob, font=bold_font).grid(row=1, column=1, sticky='w')

    def setup_trends(self, label_font, bold_font):
        trend_frame = ttk.LabelFrame(self.scrollable_frame, text="ТРЕНДЫ (за 3 часа)", padding=scale(10))
        trend_frame.grid(row=6, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))
        trend_frame.columnconfigure(1, weight=1)

        self.trend_p = tk.StringVar(value="--")
        self.trend_t = tk.StringVar(value="--")
        self.trend_h = tk.StringVar(value="--")

        ttk.Label(trend_frame, text="Давление:", font=label_font).grid(row=0, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_p, font=bold_font).grid(row=0, column=1, sticky='w')

        ttk.Label(trend_frame, text="Температура:", font=label_font).grid(row=1, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_t, font=bold_font).grid(row=1, column=1, sticky='w')

        ttk.Label(trend_frame, text="Влажность:", font=label_font).grid(row=2, column=0, sticky='w')
        ttk.Label(trend_frame, textvariable=self.trend_h, font=bold_font).grid(row=2, column=1, sticky='w')

    def setup_events(self, label_font, italic_font):
        events_frame = ttk.LabelFrame(self.scrollable_frame, text="НАБЛЮДАЕМЫЕ ПОГОДНЫЕ ЯВЛЕНИЯ", padding=scale(10))
        events_frame.grid(row=7, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))

        self.events_container = ttk.Frame(events_frame)
        self.events_container.pack(fill='both', expand=True, padx=scale(5), pady=scale(5))

        ttk.Label(self.events_container, text="Нет наблюдаемых явлений", font=italic_font).pack(pady=scale(10))

    def setup_recommendations(self, label_font, italic_font):
        rec_frame = ttk.LabelFrame(self.scrollable_frame, text="РЕКОМЕНДАЦИИ", padding=scale(10))
        rec_frame.grid(row=8, column=0, columnspan=2, sticky='ew', padx=scale(10), pady=scale(5))

        self.rec_container = ttk.Frame(rec_frame)
        self.rec_container.pack(fill='both', expand=True, padx=scale(5), pady=scale(5))

        ttk.Label(self.rec_container, text="Рекомендаций нет", font=italic_font).pack(pady=scale(10))

    def calculate_dew_point(self, T, H):
        a = 17.27
        b = 237.7
        alpha = (a * T) / (b + T) + math.log(H / 100)
        Td = (b * alpha) / (a - alpha)
        return Td

    def get_season(self):
        month = datetime.now().month
        return "winter" if month in [10, 11, 12, 1, 2, 3, 4] else "summer"

    def if_heat(self) -> bool:
        if not self.records:
            return False
        temperature = self.records[-1]['temperature']
        return temperature > 27.0

    def if_frost(self) -> bool:
        if not self.records:
            return False
        temperature = self.records[-1]['temperature']
        return temperature < -25.0

    def if_sharp_cold(self) -> bool:
        if len(self.records) < 2:
            return False

        now = self.records[-1]['datetime']
        current_temp = self.records[-1]['temperature']

        has_6h_data = False
        has_24h_data = False

        past_6h_record = None
        past_24h_record = None

        time_6h_ago = now - timedelta(hours=6)
        time_24h_ago = now - timedelta(hours=24)

        for r in reversed(self.records):
            if not has_6h_data and r['datetime'] <= time_6h_ago:
                past_6h_record = r
                has_6h_data = True
            if not has_24h_data and r['datetime'] <= time_24h_ago:
                past_24h_record = r
                has_24h_data = True
            if has_6h_data and has_24h_data:
                break

        if has_6h_data and past_6h_record is not None:
            delta_6h = current_temp - past_6h_record['temperature']
            if delta_6h < -5.0:
                return True

        if has_24h_data and past_24h_record is not None:
            delta_24h = current_temp - past_24h_record['temperature']
            if delta_24h < -10.0:
                return True

        return False

    def if_sharp_warming(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        now = self.records[-1]['datetime']
        current_temp = self.records[-1]['temperature']

        time_6h_ago = now - timedelta(hours=6)
        time_24h_ago = now - timedelta(hours=24)

        past_6h_record = None
        past_24h_record = None

        has_6h_data = False
        has_24h_data = False

        for r in reversed(self.records):
            if not has_6h_data and r['datetime'] <= time_6h_ago:
                past_6h_record = r
                has_6h_data = True
            if not has_24h_data and r['datetime'] <= time_24h_ago:
                past_24h_record = r
                has_24h_data = True
            if has_6h_data and has_24h_data:
                break

        if has_6h_data and past_6h_record is not None:
            delta_6h = current_temp - past_6h_record['temperature']
            if delta_6h > 5.0:
                return True

        if has_24h_data and past_24h_record is not None:
            delta_24h = current_temp - past_24h_record['temperature']
            if delta_24h > 10.0:
                return True

        return False

    def if_frosts(self) -> bool:
        if not self.records:
            return False

        now = self.records[-1]['datetime']
        today = now.date()

        time_24h_ago = now - timedelta(hours=24)
        temps_last_24h = [r['temperature'] for r in self.records if r['datetime'] >= time_24h_ago]

        if not temps_last_24h:
            return False

        t_min_last_24h = min(temps_last_24h)
        if t_min_last_24h > 0:
            return False

        day_temps = {}
        cutoff = now - timedelta(days=8)

        for r in self.records:
            if r['datetime'] < cutoff:
                continue
            day = r['datetime'].date()
            if day == today:
                continue
            day_temps.setdefault(day, []).append(r['temperature'])

        if len(day_temps) < 7:
            return False

        sorted_days = sorted(day_temps.keys(), reverse=True)

        consecutive_days = []
        prev_day = None
        for day in sorted_days:
            if prev_day is None or (prev_day - day).days == 1:
                consecutive_days.append(day)
                prev_day = day
            else:
                consecutive_days = [day]
                prev_day = day

            if len(consecutive_days) >= 7:
                break

        if len(consecutive_days) < 7:
            return False

        daily_means = []
        for day in consecutive_days[:7]:
            temps = day_temps[day]
            if temps:
                daily_means.append(mean(temps))

        if len(daily_means) < 7:
            return False

        return all(avg > 0 for avg in daily_means)

    def if_thaw(self) -> bool:
        if not self.records:
            return False

        now = self.records[-1]['datetime']
        today = now.date()

        time_24h_ago = now - timedelta(hours=24)
        temps_last_24h = [r['temperature'] for r in self.records if r['datetime'] >= time_24h_ago]

        if not temps_last_24h:
            return False

        t_max_last_24h = max(temps_last_24h)
        if t_max_last_24h < 0:
            return False

        day_temps = {}
        cutoff = now - timedelta(days=8)

        for r in self.records:
            if r['datetime'] < cutoff:
                continue
            day = r['datetime'].date()
            if day == today:
                continue
            day_temps.setdefault(day, []).append(r['temperature'])

        if len(day_temps) < 7:
            return False

        sorted_days = sorted(day_temps.keys(), reverse=True)

        consecutive_days = []
        prev_day = None
        for day in sorted_days:
            if prev_day is None or (prev_day - day).days == 1:
                consecutive_days.append(day)
                prev_day = day
            else:
                consecutive_days = [day]
                prev_day = day
            if len(consecutive_days) >= 7:
                break

        if len(consecutive_days) < 7:
            return False

        daily_means = []
        for day in consecutive_days[:7]:
            temps = day_temps[day]
            if temps:
                daily_means.append(mean(temps))

        if len(daily_means) < 7:
            return False

        return all(avg < 0 for avg in daily_means)

    def if_drought(self) -> bool:
        if not self.records:
            return False

        now = self.records[-1]['datetime']
        current_day = now.date()

        day_stats = {}

        for r in self.records:
            day = r['datetime'].date()
            if day >= current_day:
                continue
            if day not in day_stats:
                day_stats[day] = {'t_max': -999, 'h_min': 999}
            day_stats[day]['t_max'] = max(day_stats[day]['t_max'], r['temperature'])
            day_stats[day]['h_min'] = min(day_stats[day]['h_min'], r['humidity'])

        sorted_days = sorted(day_stats.keys(), reverse=True)

        if len(sorted_days) < 7:
            return False

        streak = 0
        prev_day = None

        for day in sorted_days:
            if prev_day is not None and (prev_day - day).days != 1:
                streak = 0

            stats = day_stats[day]
            drought_day = (stats['t_max'] > 25.0) and (stats['h_min'] < 40.0)

            if drought_day:
                streak += 1
                if streak >= 7:
                    return True
            else:
                streak = 0

            prev_day = day

        return False

    def if_fog(self) -> bool:
        if not self.records or len(self.records) < 1:
            return False

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']

        if H >= 100.0:
            Td = T
        else:
            Td = self.calculate_dew_point(T, H)

        delta = T - Td
        return H > 90.0 and delta <= 2.0

    def if_fire_danger(self) -> bool:
        if not self.records:
            return False

        now = self.records[-1]['datetime']

        day_noon_data = {}

        for r in self.records:
            dt = r['datetime']
            if dt > now:
                continue
            day = dt.date()
            hour = dt.hour

            if 12 <= hour <= 15:
                if day not in day_noon_data or abs(hour - 13.5) < abs(day_noon_data[day][4] - 13.5):
                    Td = self.calculate_dew_point(r['temperature'], r['humidity'])
                    day_noon_data[day] = (
                        r['temperature'],
                        Td,
                        r['humidity'],
                        r['pressure'],
                        hour
                    )

        if len(day_noon_data) < 3:
            return False

        sorted_days = sorted(day_noon_data.keys(), reverse=True)

        first_day = sorted_days[-1]
        last_day = sorted_days[0]
        days_span = (last_day - first_day).days

        if days_span > 14:
            return False

        kp_sum = 0.0
        n = 0

        for day in sorted_days:
            if day not in self.daily_precip_probs:
                continue

            prob = self.daily_precip_probs[day]
            if prob not in ("Низкая", "Очень низкая"):
                continue

            t, Td, H, P, _ = day_noon_data[day]
            delta = t - Td
            kp_sum += t * delta
            n += 1

            if n >= 14:
                break

        if n < 3:
            return False

        return kp_sum > 4000.0

    def if_pressure_decrease(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        now = self.records[-1]['datetime']
        current_P = self.records[-1]['pressure']

        time_6h_ago = now - timedelta(hours=6)
        time_24h_ago = now - timedelta(hours=24)

        past_6h_record = None
        past_24h_record = None
        has_6h_data = False
        has_24h_data = False

        for r in reversed(self.records):
            if not has_6h_data and r['datetime'] <= time_6h_ago:
                past_6h_record = r
                has_6h_data = True
            if not has_24h_data and r['datetime'] <= time_24h_ago:
                past_24h_record = r
                has_24h_data = True
            if has_6h_data and has_24h_data:
                break

        if has_6h_data and past_6h_record is not None:
            delta_6h = current_P - past_6h_record['pressure']
            if delta_6h < -9.0:
                return True

        if has_24h_data and past_24h_record is not None:
            delta_24h = current_P - past_24h_record['pressure']
            if delta_24h < -18.0:
                return True

        return False

    def if_pressure_increase(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        now = self.records[-1]['datetime']
        current_P = self.records[-1]['pressure']

        time_6h_ago = now - timedelta(hours=6)
        time_24h_ago = now - timedelta(hours=24)

        past_6h_record = None
        past_24h_record = None
        has_6h_data = False
        has_24h_data = False

        for r in reversed(self.records):
            if not has_6h_data and r['datetime'] <= time_6h_ago:
                past_6h_record = r
                has_6h_data = True
            if not has_24h_data and r['datetime'] <= time_24h_ago:
                past_24h_record = r
                has_24h_data = True
            if has_6h_data and has_24h_data:
                break

        if has_6h_data and past_6h_record is not None:
            delta_6h = current_P - past_6h_record['pressure']
            if delta_6h > 9.0:
                return True

        if has_24h_data and past_24h_record is not None:
            delta_24h = current_P - past_24h_record['pressure']
            if delta_24h > 18.0:
                return True

        return False

    def if_low_pressure(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False

        current_P = self.records[-1]['pressure']
        return current_P < 735.0

    def if_high_pressure(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False

        current_P = self.records[-1]['pressure']
        return current_P > 780.0

    def get_precipitation(self):
        if not self.records:
            return "—", "—"

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        Td = self.calculate_dew_point(T, H)

        delta = T - Td

        time_3h_ago = last['datetime'] - timedelta(hours=3)
        prev_3h = None
        for r in reversed(self.records[:-1]):
            if r['datetime'] <= time_3h_ago:
                prev_3h = r
                break

        if prev_3h:
            P_trend = P - prev_3h['pressure']
        else:
            P_trend = 0

        if P < 745:
            P_cat = "L"
        elif P > 765:
            P_cat = "H"
        else:
            P_cat = "M"

        if P_trend < -2:
            dP_cat = "F"
        elif P_trend > 2:
            dP_cat = "R"
        else:
            dP_cat = "S"

        if H >= 95 and delta <= 1 and P_cat == "L" and dP_cat == "F":
            prob = "Очень высокая"
        elif (H >= 95 and delta <= 1 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                (85 <= H < 95 and 1 < delta <= 3 and P_cat == "L" and dP_cat == "F"):
            prob = "Высокая"
        elif (85 <= H < 95 and 1 < delta <= 3 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                (70 <= H < 85 and 3 < delta <= 5 and P_cat == "L" and dP_cat == "F"):
            prob = "Средняя"
        elif (70 <= H < 85 and 3 < delta <= 5 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                (50 <= H < 70 and 5 < delta <= 8):
            prob = "Низкая"
        else:
            prob = "Очень низкая" if delta > 8 or H < 50 else "Низкая"

        if prob in ("Очень высокая", "Высокая", "Средняя"):
            if T > 2:
                p_type = "Дождь"
            elif T < -2:
                p_type = "Снег"
            else:
                p_type = "Мокрый снег"
        else:
            p_type = "—"

        return prob, p_type

    def if_rain(self) -> bool:
        prob, p_type = self.get_precipitation()

        if prob in ("Средняя", "Высокая", "Очень высокая"):
            return p_type == "Дождь"

        return False

    def if_snow(self) -> bool:
        prob, p_type = self.get_precipitation()

        if prob in ("Средняя", "Высокая", "Очень высокая"):
            return p_type == "Снег"

        return False

    def if_sleet(self) -> bool:
        prob, p_type = self.get_precipitation()

        if prob in ("Средняя", "Высокая", "Очень высокая"):
            return p_type == "Мокрый снег"

        return False

    def if_black_ice(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        Td = self.calculate_dew_point(T, H)
        delta_T_Td = T - Td

        if not (-7.0 <= T <= 0.0):
            return False

        if H < 85.0:
            return False

        if delta_T_Td > 3.0:
            return False

        if P >= 765.0:
            return False

        time_3h_ago = last['datetime'] - timedelta(hours=3)
        prev_record = None
        has_3h_data = False

        for r in reversed(self.records[:-1]):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                has_3h_data = True
                break

        if not has_3h_data or prev_record is None:
            return False

        delta_P_3h = P - prev_record['pressure']

        if delta_P_3h >= 0:
            return False

        return True

    def if_ice_slick(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        Td = self.calculate_dew_point(T, H)
        delta_T_Td = T - Td

        if T > 0.0:
            return False

        if H < 90.0:
            return False

        if delta_T_Td > 2.0:
            return False

        time_12h_ago = last['datetime'] - timedelta(hours=12)

        has_12h_data = any(r['datetime'] >= time_12h_ago for r in self.records)

        if not has_12h_data:
            return False

        temps_last_12h = [
            r['temperature']
            for r in self.records
            if r['datetime'] >= time_12h_ago
        ]

        t_max_12h = max(temps_last_12h)

        if t_max_12h < 1.0:
            return False

        return True

    def if_hoarfrost(self) -> bool:
        if not self.records or len(self.records) == 0:
            return False

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        Td = self.calculate_dew_point(T, H)
        delta_T_Td = T - Td

        if T > 0.0:
            return False

        if H < 80.0:
            return False

        if delta_T_Td > 3.0:
            return False

        return True

    def if_thunderstorm(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        Td = self.calculate_dew_point(T, H)
        delta_T_Td = T - Td

        if T <= 20.0:
            return False

        if H <= 70.0:
            return False

        if delta_T_Td > 5.0:
            return False

        time_3h_ago = last['datetime'] - timedelta(hours=3)
        prev_record = None
        has_3h_data = False

        for r in reversed(self.records[:-1]):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                has_3h_data = True
                break

        if not has_3h_data or prev_record is None:
            return False

        if H <= prev_record['humidity']:
            return False

        delta_P_3h = P - prev_record['pressure']
        if not (-3.0 <= delta_P_3h <= -2.0):
            return False

        return True

    def if_sharp_change(self) -> bool:
        if not self.records or len(self.records) < 2:
            return False

        now = self.records[-1]['datetime']
        current_T = self.records[-1]['temperature']
        current_P = self.records[-1]['pressure']
        current_H = self.records[-1]['humidity']

        conditions_met = 0

        time_6h = now - timedelta(hours=6)
        time_24h = now - timedelta(hours=24)

        past_6h_T = None
        past_24h_T = None
        has_6h_T = False
        has_24h_T = False

        for r in reversed(self.records):
            if not has_6h_T and r['datetime'] <= time_6h:
                past_6h_T = r['temperature']
                has_6h_T = True
            if not has_24h_T and r['datetime'] <= time_24h:
                past_24h_T = r['temperature']
                has_24h_T = True
            if has_6h_T and has_24h_T:
                break

        if has_6h_T and past_6h_T is not None:
            delta_T_6h = abs(current_T - past_6h_T)
            if delta_T_6h >= 5.0:
                conditions_met += 1
        elif has_24h_T and past_24h_T is not None:
            delta_T_24h = abs(current_T - past_24h_T)
            if delta_T_24h >= 10.0:
                conditions_met += 1

        past_6h_P = None
        past_24h_P = None
        has_6h_P = False
        has_24h_P = False

        for r in reversed(self.records):
            if not has_6h_P and r['datetime'] <= time_6h:
                past_6h_P = r['pressure']
                has_6h_P = True
            if not has_24h_P and r['datetime'] <= time_24h:
                past_24h_P = r['pressure']
                has_24h_P = True
            if has_6h_P and has_24h_P:
                break

        if has_6h_P and past_6h_P is not None:
            delta_P_6h = abs(current_P - past_6h_P)
            if delta_P_6h >= 9.0:
                conditions_met += 1
        elif has_24h_P and past_24h_P is not None:
            delta_P_24h = abs(current_P - past_24h_P)
            if delta_P_24h >= 18.0:
                conditions_met += 1

        past_6h_H = None
        past_24h_H = None
        has_6h_H = False
        has_24h_H = False

        for r in reversed(self.records):
            if not has_6h_H and r['datetime'] <= time_6h:
                past_6h_H = r['humidity']
                has_6h_H = True
            if not has_24h_H and r['datetime'] <= time_24h:
                past_24h_H = r['humidity']
                has_24h_H = True
            if has_6h_H and has_24h_H:
                break

        if has_6h_H and past_6h_H is not None:
            delta_H_6h = abs(current_H - past_6h_H)
            if delta_H_6h >= 20.0:
                conditions_met += 1
        elif has_24h_H and past_24h_H is not None:
            delta_H_24h = abs(current_H - past_24h_H)
            if delta_H_24h >= 40.0:
                conditions_met += 1

        return conditions_met >= 2

    def get_weather_character(self) -> str:
        if not self.records or len(self.records) < 2:
            return "Нет данных"

        last = self.records[-1]
        P = last['pressure']
        H = last['humidity']

        time_3h_ago = last['datetime'] - timedelta(hours=3)
        prev_record = None
        has_3h_data = False

        for r in reversed(self.records[:-1]):
            if r['datetime'] <= time_3h_ago:
                prev_record = r
                has_3h_data = True
                break

        if has_3h_data and prev_record is not None:
            delta_P = P - prev_record['pressure']
        else:
            delta_P = 0.0

        if P > 765:
            P_cat = "H"
        elif P < 745:
            P_cat = "L"
        else:
            P_cat = "M"

        if delta_P > 2:
            dP_cat = "R"
        elif delta_P < -2:
            dP_cat = "F"
        else:
            dP_cat = "S"

        if H < 60:
            H_cat = "L"
        elif H > 75:
            H_cat = "H"
        else:
            H_cat = "M"

        if P_cat == "H":
            if dP_cat == "R":
                if H_cat == "L":   return "Антициклонический"
                if H_cat == "M":   return "Антициклонический"
                if H_cat == "H":   return "Нейтральный"
            elif dP_cat == "S":
                if H_cat == "L":   return "Антициклонический"
                if H_cat == "M":   return "Антициклонический"
                if H_cat == "H":   return "Нейтральный"
            elif dP_cat == "F":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Нейтральный"
                if H_cat == "H":   return "Нейтральный"

        elif P_cat == "M":
            if dP_cat == "R":
                if H_cat == "L":   return "Антициклонический"
                if H_cat == "M":   return "Нейтральный"
                if H_cat == "H":   return "Нейтральный"
            elif dP_cat == "S":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Нейтральный"
                if H_cat == "H":   return "Нейтральный"
            elif dP_cat == "F":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Нейтральный"
                if H_cat == "H":   return "Нейтральный"

        elif P_cat == "L":
            if dP_cat == "R":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Нейтральный"
                if H_cat == "H":   return "Нейтральный"
            elif dP_cat == "S":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Циклонический"
                if H_cat == "H":   return "Циклонический"
            elif dP_cat == "F":
                if H_cat == "L":   return "Нейтральный"
                if H_cat == "M":   return "Циклонический"
                if H_cat == "H":   return "Циклонический"

        return "Нейтральный"

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

            self.weather_type.set("--")
            self.precip_type.set("--")
            self.precip_prob.set("--")

            self.trend_p.set("--")
            self.trend_t.set("--")
            self.trend_h.set("--")

            self.update_time_var.set("Нет достаточных данных для анализа")
            self.window.update_idletasks()
            return

        last = self.records[-1]
        T = last['temperature']
        H = last['humidity']
        P = last['pressure']
        dt = last['datetime']
        Td = self.calculate_dew_point(T, H)

        self.update_daily_precip_probs()

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

        self.weather_type.set(self.get_weather_character())

        prob, p_type = self.get_precipitation()
        self.precip_prob.set(prob)
        self.precip_type.set(p_type)

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

        events = []

        if self.if_heat():
            events.append("Сильная жара")
        if self.if_frost():
            events.append("Сильный мороз")
        if self.if_frosts():
            events.append("Заморозки")
        if self.if_thaw():
            events.append("Оттепель")
        if self.if_drought():
            events.append("Засуха")
        if self.if_fog():
            events.append("Возможен туман")
        if self.if_low_pressure():
            events.append("Экстремально низкое давление")
        if self.if_high_pressure():
            events.append("Экстремально высокое давление")
        if self.if_black_ice():
            events.append("Возможен гололёд")
        if self.if_ice_slick():
            events.append("Возможна гололедица")
        if self.if_hoarfrost():
            events.append("Возможна изморозь")
        if self.if_thunderstorm():
            events.append("Возможна гроза")
        if self.if_fire_danger():
            events.append("Высокая пожарная опасность")

        if self.if_rain():
            events.append("Возможен дождь")
        if self.if_snow():
            events.append("Возможен снег")
        if self.if_sleet():
            events.append("Возможен мокрый снег")

        if self.if_sharp_cold():
            events.append("Резкое похолодание")
        if self.if_sharp_warming():
            events.append("Резкое потепление")
        if self.if_pressure_decrease():
            events.append("Резкий спад давления")
        if self.if_pressure_increase():
            events.append("Резкий рост давления")
        if self.if_sharp_change():
            events.append("Резкая смена погоды")

        for widget in self.events_container.winfo_children():
            widget.destroy()

        # Масштабируем эмодзи и текст в событиях
        emoji_font = ("Segoe UI Emoji", scale_font_size(16))

        if events:
            for event in sorted(set(events)):
                frame = ttk.Frame(self.events_container)
                frame.pack(fill='x', pady=scale(4), padx=scale(5))

                icon = "•"
                for category in self.rec_data.values():
                    if event in category:
                        icon = category[event].get("icon", "•")
                        break

                ttk.Label(frame, text=icon, font=emoji_font).pack(side='left', padx=(0, scale(10)))
                ttk.Label(frame, text=event, wraplength=scale(580), justify='left').pack(side='left', expand=True,
                                                                                         fill='x')
        else:
            ttk.Label(self.events_container, text="Нет наблюдаемых явлений",
                      font=("Arial", scale_font_size(12), "italic")).pack(pady=scale(10))

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
                frame.pack(fill='x', pady=scale(6), padx=scale(5))

                icon = rec_line[:2].strip() if len(rec_line) > 2 else "•"
                text_part = rec_line[2:].strip() if len(rec_line) > 2 else rec_line

                ttk.Label(frame, text=icon, font=emoji_font).pack(side='left', padx=(0, scale(10)))
                ttk.Label(frame, text=text_part, wraplength=scale(580), justify='left').pack(side='left', expand=True,
                                                                                             fill='x')
        else:
            ttk.Label(self.rec_container, text="Рекомендаций нет", font=("Arial", scale_font_size(12), "italic")).pack(
                pady=scale(10))

        self.update_time_var.set(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
        self.window.update_idletasks()

    def update_daily_precip_probs(self):
        if not self.records:
            return

        self.daily_precip_probs.clear()

        day_records = {}
        for r in self.records:
            day = r['datetime'].date()
            day_records.setdefault(day, []).append(r)

        for day, records in day_records.items():
            if not records:
                continue

            avg_H = mean(r['humidity'] for r in records)
            avg_P = mean(r['pressure'] for r in records)
            avg_delta = mean(
                r['temperature'] - self.calculate_dew_point(r['temperature'], r['humidity']) for r in records)

            if len(records) >= 2:
                sorted_by_time = sorted(records, key=lambda r: r['datetime'])
                delta_P_day = sorted_by_time[-1]['pressure'] - sorted_by_time[0]['pressure']
            else:
                delta_P_day = 0.0

            P_cat = "L" if avg_P < 745 else "H" if avg_P > 765 else "M"
            dP_cat = "F" if delta_P_day < -2 else "R" if delta_P_day > 2 else "S"

            if avg_H >= 95 and avg_delta <= 1 and P_cat == "L" and dP_cat == "F":
                prob = "Очень высокая"
            elif (avg_H >= 95 and avg_delta <= 1 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                    (85 <= avg_H < 95 and 1 < avg_delta <= 3 and P_cat == "L" and dP_cat == "F"):
                prob = "Высокая"
            elif (85 <= avg_H < 95 and 1 < avg_delta <= 3 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                    (70 <= avg_H < 85 and 3 < avg_delta <= 5 and P_cat == "L" and dP_cat == "F"):
                prob = "Средняя"
            elif (70 <= avg_H < 85 and 3 < avg_delta <= 5 and P_cat in ("M", "H") and dP_cat in ("S", "R")) or \
                    (50 <= avg_H < 70 and 5 < avg_delta <= 8):
                prob = "Низкая"
            else:
                prob = "Очень низкая" if avg_delta > 8 or avg_H < 50 else "Низкая"

            self.daily_precip_probs[day] = prob
