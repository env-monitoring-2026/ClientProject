#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ftplib
import time
import os
import tempfile
from config.auth import FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS
from config.settings import MAX_RETRIES, TIMEOUT
from utils.logger import log_error

TEMP_DIR = tempfile.mkdtemp(prefix="ftp_sensor_")


def connect_ftp():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, FTP_PORT, timeout=TIMEOUT)
            ftp.login(FTP_USER, FTP_PASS)
            return ftp
        except Exception as e:
            log_error(f"Ошибка FTP-подключения (попытка {attempt}): {e}")
            time.sleep(5)
    return None


def download_data_file(device_name, ftp=None, since_timestamp=None):

    from utils.data_parser import parse_data_file

    close_ftp = False
    if ftp is None:
        ftp = connect_ftp()
        close_ftp = True

    if not ftp:
        return []

    local_path = os.path.join(TEMP_DIR, f"data_{device_name}.txt")
    try:
        ftp.cwd("devices")
        ftp.cwd(device_name)
        with open(local_path, "wb") as f:
            ftp.retrbinary("RETR data.txt", f.write)
        all_records = parse_data_file(local_path)

        if since_timestamp is not None:
            filtered = [r for r in all_records if r['datetime'].timestamp() >= since_timestamp]
            return filtered
        return all_records
    except Exception as e:
        log_error(f"Ошибка загрузки data.txt: {e}")
        return []
    finally:
        if close_ftp and ftp:
            try:
                ftp.quit()
            except:
                pass


def download_latest_diag(device_name, ftp=None):

    from utils.data_parser import parse_diag_file

    close_ftp = False
    if ftp is None:
        ftp = connect_ftp()
        close_ftp = True

    if not ftp:
        return None

    local_path = os.path.join(TEMP_DIR, f"diag_{device_name}.txt")
    try:
        ftp.cwd("devices")
        ftp.cwd(device_name)
        with open(local_path, "wb") as f:
            ftp.retrbinary("RETR diag.txt", f.write)
        records = parse_diag_file(local_path)
        return records[-1] if records else None
    except Exception as e:
        log_error(f"Ошибка загрузки diag.txt: {e}")
        return None
    finally:
        if close_ftp and ftp:
            try:
                ftp.quit()
            except:
                pass


def download_daily_file(username, device_name, date_str, local_path):
    ftp = connect_ftp()
    if not ftp:
        return False

    try:
        year, month, day = date_str.split('-')
        month_name = get_month_name(int(month))
        remote_path = f"/FTP/{username}/devices/{device_name}/{year}/{month_name}/{date_str}.txt"
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_path}", f.write)
        return True
    except Exception as e:
        log_error(f"Ошибка скачивания суточного файла: {e}")
        return False
    finally:
        try:
            ftp.quit()
        except:
            pass


def get_month_name(month_num):
    months = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
    return months[month_num - 1]