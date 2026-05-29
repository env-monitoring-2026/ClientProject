#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from statistics import mean

def calculate_stats(records):
    if not records:
        return None
    temps = [r["temperature"] for r in records]
    hums = [r["humidity"] for r in records]
    press = [r["pressure"] for r in records]
    return {
        "temp": {"min": min(temps), "max": max(temps), "avg": mean(temps)},
        "hum": {"min": min(hums), "max": max(hums), "avg": mean(hums)},
        "press": {"min": min(press), "max": max(press), "avg": mean(press)}
    }