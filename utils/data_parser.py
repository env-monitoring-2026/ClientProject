#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from utils.logger import log_error


def parse_data_file(filepath):
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) == 4:
                    try:
                        timestamp = float(parts[0])
                        temperature = float(parts[1])
                        humidity = float(parts[2])
                        pressure = float(parts[3])

                        if (temperature < -50.0 or temperature > 60.0 or
                                humidity < 0.0 or humidity > 100.0 or
                                pressure < 700.0 or pressure > 820.0):
                            continue

                        records.append({
                            'datetime': datetime.fromtimestamp(timestamp),
                            'temperature': temperature,
                            'humidity': humidity,
                            'pressure': pressure
                        })
                    except ValueError:
                        continue
        return records
    except Exception as e:
        log_error(f"Ошибка парсинга {filepath}: {e}")
        return []


def parse_diag_file(filepath):
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 9:
                    try:
                        timestamp = float(parts[0])
                        records.append({
                            'timestamp': datetime.fromtimestamp(timestamp),
                            'system_mode': parts[1],
                            'operation_mode': parts[2],
                            'mcc': parts[3],
                            'mnc': parts[4],
                            'rssi': parts[5],
                            'voltage': parts[6],
                            'temperature': parts[7],
                            'uart': parts[8],
                        })
                    except (ValueError, IndexError):
                        continue
        return records
    except Exception as e:
        print(f"Ошибка парсинга {filepath}: {e}")
        return []