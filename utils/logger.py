#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import time
from datetime import datetime


LOG_DIR = "logs"

_logger = None


def cleanup_old_logs(log_file_path: str, retention_days: int):
    if not os.path.exists(log_file_path) or os.path.getsize(log_file_path) == 0:
        return 0

    cutoff_time = time.time() - retention_days * 86400

    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    filtered_lines = []
    for line in lines:
        try:
            date_str = line[:10]
            timestamp = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            if timestamp >= cutoff_time:
                filtered_lines.append(line)
        except (ValueError, IndexError):
            continue

    with open(log_file_path, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)

    return len(lines) - len(filtered_lines)


def setup_logger():
    global _logger

    if _logger is not None:
        return _logger

    os.makedirs(LOG_DIR, exist_ok=True)

    log_file = os.path.join(LOG_DIR, "client.log")

    _logger = logging.getLogger("MonitoringClient")
    _logger.setLevel(logging.INFO)

    _logger.handlers.clear()

    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    _logger.addHandler(handler)

    _logger.info("=== Клиент запущен ===")

    return _logger


def get_logger():
    global _logger
    if _logger is None:
        return setup_logger()
    return _logger


def log_info(message):
    get_logger().info(message)


def log_error(message):
    get_logger().error(message)


def log_warning(message):
    get_logger().warning(message)


def log_debug(message):
    get_logger().debug(message)