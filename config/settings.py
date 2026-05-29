#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# Базовая директория проекта
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Пути к данным
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RECOMMENDATIONS_DIR = os.path.join(DATA_DIR, "recommendations")
MODES_DIR = os.path.join(DATA_DIR, "modes")
ICON_DIR = os.path.join(PROJECT_ROOT, "icons")
DEVICE_DATA_DIR = os.path.join(DATA_DIR, "device_data")

# Интервал опроса FTP-сервера в секундах
POLL_INTERVAL = 30

# Таймаут FTP-соединения в секундах
TIMEOUT = 60

# Количество попыток подключения
MAX_RETRIES = 3

# Файл локальной конфигурации клиента
CLIENT_CONFIG_FILE = os.path.join(PROJECT_ROOT, "client_config.json")

# Срок хранения логов клиента (в днях)
CLIENT_LOG_RETENTION_DAYS = 30