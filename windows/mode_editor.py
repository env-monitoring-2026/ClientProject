#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox


class ModeEditor:


    def __init__(self, parent, mode_manager, mode_name=None):

        self.parent = parent
        self.mode_manager = mode_manager
        self.mode_name = mode_name

        self.window = tk.Toplevel(parent)
        self.window.title(
            "Создание режима"
            if not mode_name else f"Редактирование режима: {mode_name}"
        )
        self.window.geometry("600x700")
        self.window.resizable(False, False)


        self.mode_data = {}
        if mode_name:
            self.mode_data = mode_manager.load_mode(mode_name) or {}

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            main_frame,
            text="Настройки режима",
            font=("Arial", 16, "bold")
        )
        title.grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(
            main_frame,
            text="Название режима:",
            font=("Arial", 11)
        ).grid(row=1, column=0, sticky='w', pady=5)

        self.name_var = tk.StringVar(value=self.mode_data.get('name', ''))
        ttk.Entry(
            main_frame,
            textvariable=self.name_var,
            width=40,
            font=("Arial", 11)
        ).grid(row=1, column=1, pady=5)

        ttk.Separator(
            main_frame,
            orient='horizontal'
        ).grid(row=2, column=0, columnspan=2, sticky='ew', pady=15)

        ttk.Label(
            main_frame,
            text="ТЕМПЕРАТУРА",
            font=("Arial", 12, "bold")
        ).grid(row=3, column=0, columnspan=2, sticky='w', pady=5)

        self.t_min_var = self._add_param(
            main_frame, 4, "Минимум (°C):", 't_min'
        )
        self.t_max_var = self._add_param(
            main_frame, 5, "Максимум (°C):", 't_max'
        )
        self.t_crit_var = self._add_param(
            main_frame, 6, "Порог критичности (%):", 't_crit'
        )

        ttk.Separator(
            main_frame,
            orient='horizontal'
        ).grid(row=7, column=0, columnspan=2, sticky='ew', pady=10)

        ttk.Label(
            main_frame,
            text="ВЛАЖНОСТЬ",
            font=("Arial", 12, "bold")
        ).grid(row=8, column=0, columnspan=2, sticky='w', pady=5)

        self.h_min_var = self._add_param(
            main_frame, 9, "Минимум (%):", 'h_min'
        )
        self.h_max_var = self._add_param(
            main_frame, 10, "Максимум (%):", 'h_max'
        )
        self.h_crit_var = self._add_param(
            main_frame, 11, "Порог критичности (%):", 'h_crit'
        )

        ttk.Separator(
            main_frame,
            orient='horizontal'
        ).grid(row=12, column=0, columnspan=2, sticky='ew', pady=10)

        ttk.Label(
            main_frame,
            text="ДАВЛЕНИЕ",
            font=("Arial", 12, "bold")
        ).grid(row=13, column=0, columnspan=2, sticky='w', pady=5)

        self.p_min_var = self._add_param(
            main_frame, 14, "Минимум (мм рт.ст.):", 'p_min'
        )
        self.p_max_var = self._add_param(
            main_frame, 15, "Максимум (мм рт.ст.):", 'p_max'
        )
        self.p_crit_var = self._add_param(
            main_frame, 16, "Порог критичности (%):", 'p_crit'
        )

        ttk.Separator(
            main_frame,
            orient='horizontal'
        ).grid(row=17, column=0, columnspan=2, sticky='ew', pady=15)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=18, column=0, columnspan=2, pady=20)

        ttk.Button(
            button_frame,
            text="Сохранить",
            command=self.save_mode,
            width=15
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Отмена",
            command=self.window.destroy,
            width=15
        ).pack(side='left', padx=5)

        ttk.Label(
            main_frame,
            text="Оставьте поля пустыми, если параметр не контролируется",
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).grid(row=19, column=0, columnspan=2, pady=5)

    def _add_param(self, frame, row, label_text, key):
        ttk.Label(
            frame,
            text=label_text,
            font=("Arial", 11)
        ).grid(row=row, column=0, sticky='w', pady=2)

        var = tk.StringVar(value=self.mode_data.get(key, ''))
        ttk.Entry(
            frame,
            textvariable=var,
            width=20,
            font=("Arial", 11)
        ).grid(row=row, column=1, sticky='w', pady=2)
        return var

    def save_mode(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введите название режима")
            return

        # Преобразование значений
        t_min = self._float_or_none(self.t_min_var.get())
        t_max = self._float_or_none(self.t_max_var.get())
        t_crit = self._float_or_none(self.t_crit_var.get())
        h_min = self._float_or_none(self.h_min_var.get())
        h_max = self._float_or_none(self.h_max_var.get())
        h_crit = self._float_or_none(self.h_crit_var.get())
        p_min = self._float_or_none(self.p_min_var.get())
        p_max = self._float_or_none(self.p_max_var.get())
        p_crit = self._float_or_none(self.p_crit_var.get())

        errors = []

        if t_min is not None and t_max is not None and t_min > t_max:
            errors.append("Нижняя граница температуры не может превышать верхнюю")
        if t_crit is not None and (t_crit < 0 or t_crit > 100):
            errors.append("Порог критичности температуры должен быть от 0 до 100%")

        if h_min is not None and h_max is not None and h_min > h_max:
            errors.append("Нижняя граница влажности не может превышать верхнюю")
        if h_crit is not None and (h_crit < 0 or h_crit > 100):
            errors.append("Порог критичности влажности должен быть от 0 до 100%")

        if p_min is not None and p_max is not None and p_min > p_max:
            errors.append("Нижняя граница давления не может превышать верхнюю")
        if p_crit is not None and (p_crit < 0 or p_crit > 100):
            errors.append("Порог критичности давления должен быть от 0 до 100%")

        has_any = (t_min is not None or t_max is not None or
                   h_min is not None or h_max is not None or
                   p_min is not None or p_max is not None)

        if not has_any:
            errors.append(
                "Задайте хотя бы одну границу (минимум или максимум)\n"
                "хотя бы для одного параметра (температура, влажность или давление)"
            )

        if errors:
            messagebox.showerror("Ошибка ввода", "\n".join(errors))
            return

        mode = {
            'name': name,
            't_min': t_min,
            't_max': t_max,
            't_crit': t_crit,
            'h_min': h_min,
            'h_max': h_max,
            'h_crit': h_crit,
            'p_min': p_min,
            'p_max': p_max,
            'p_crit': p_crit
        }

        self.mode_manager.save_mode(name, mode)
        messagebox.showinfo("Успех", f"Режим '{name}' сохранён")
        self.window.destroy()
        
    def _float_or_none(self, value):
        value = value.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None