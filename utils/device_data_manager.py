#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import DEVICE_DATA_DIR
from utils.logger import log_error



class DeviceDataManager:

    def __init__(self):

        self._data: Dict[str, Dict] = {}
        self._load_all()

    def _get_device_file(self, device_name: str) -> str:
        os.makedirs(DEVICE_DATA_DIR, exist_ok=True)
        return os.path.join(DEVICE_DATA_DIR, f"{device_name}.json")

    def _load_all(self):
        if not os.path.exists(DEVICE_DATA_DIR):
            return

        for filename in os.listdir(DEVICE_DATA_DIR):
            if filename.endswith('.json'):
                device_name = filename[:-5]
                filepath = os.path.join(DEVICE_DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._data[device_name] = data
                except Exception as e:
                    log_error(f"Ошибка загрузки данных устройства {device_name}: {e}")

    def _save_device(self, device_name: str):
        if device_name not in self._data:
            return

        filepath = self._get_device_file(device_name)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._data[device_name], f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            log_error(f"Ошибка сохранения данных устройства {device_name}: {e}")

    def get_records(self, device_name: str) -> List[Dict]:
        if device_name not in self._data:
            return []

        records = self._data[device_name].get('records', [])
        # Преобразование строк времени обратно в объекты datetime
        for r in records:
            if isinstance(r.get('datetime'), str):
                r['datetime'] = datetime.fromisoformat(r['datetime'])
        return records

    def set_records(self, device_name: str, records: List[Dict]):
        records_copy = []
        for r in records:
            r_copy = r.copy()
            if isinstance(r_copy.get('datetime'), datetime):
                r_copy['datetime'] = r_copy['datetime'].isoformat()
            records_copy.append(r_copy)

        if device_name not in self._data:
            self._data[device_name] = {}

        self._data[device_name]['records'] = records_copy
        self._save_device(device_name)

    def get_latest_diag(self, device_name: str) -> Optional[Dict]:
        if device_name not in self._data:
            return None
        return self._data[device_name].get('latest_diag')

    def set_latest_diag(self, device_name: str, diag_data: Optional[Dict]):
        if device_name not in self._data:
            self._data[device_name] = {}

        self._data[device_name]['latest_diag'] = diag_data
        self._save_device(device_name)

    def get_config(self, device_name: str) -> Dict:
        if device_name not in self._data:
            return {"work_dir": "", "reset_interval": 3600, "last_reset": None}
        return self._data[device_name].get('config', {"work_dir": "", "reset_interval": 3600, "last_reset": None})

    def set_config(self, device_name: str, config: Dict):
        if device_name not in self._data:
            self._data[device_name] = {}

        self._data[device_name]['config'] = config
        self._save_device(device_name)

    def get_reset_time(self, device_name: str) -> Optional[datetime]:
        records = self.get_records(device_name)
        if not records:
            return None
        first_record = records[0]
        if isinstance(first_record.get('datetime'), datetime):
            return first_record['datetime']
        elif isinstance(first_record.get('datetime'), str):
            return datetime.fromisoformat(first_record['datetime'])
        return None

    def clear_device(self, device_name: str):
        if device_name in self._data:
            del self._data[device_name]
            filepath = self._get_device_file(device_name)
            if os.path.exists(filepath):
                os.remove(filepath)

    def device_exists(self, device_name: str) -> bool:

        return device_name in self._data


device_data_manager = DeviceDataManager()