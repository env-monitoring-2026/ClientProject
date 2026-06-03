#!/usr/bin/env python3
# -*- coding: utf-8 -*-

_SCALE_X = 1.0
_SCALE_Y = 1.0
_SCREEN_WIDTH = 1920
_SCREEN_HEIGHT = 1080
_REFERENCE_WIDTH = 1920
_REFERENCE_HEIGHT = 1080
_INITIALIZED = False


def init_scaling(root):
    global _SCALE_X, _SCALE_Y, _SCREEN_WIDTH, _SCREEN_HEIGHT, _INITIALIZED

    if _INITIALIZED:
        return

    _SCREEN_WIDTH = root.winfo_screenwidth()
    _SCREEN_HEIGHT = root.winfo_screenheight()

    _SCALE_X = _SCREEN_WIDTH / _REFERENCE_WIDTH
    _SCALE_Y = _SCREEN_HEIGHT / _REFERENCE_HEIGHT

    _SCALE_X = max(0.5, min(1.5, _SCALE_X))
    _SCALE_Y = max(0.5, min(1.5, _SCALE_Y))

    _INITIALIZED = True


def get_scale_x():
    return _SCALE_X


def get_scale_y():
    return _SCALE_Y


def get_scale_min():
    return min(_SCALE_X, _SCALE_Y)


def scale_x(value):
    return int(value * _SCALE_X)


def scale_y(value):
    return int(value * _SCALE_Y)


def scale(value):
    return int(value * ((_SCALE_X + _SCALE_Y) / 2))


def scale_font_size(size):
    return max(8, int(size * get_scale_min()))


def center_window(window, width=None, height=None):
    window.update_idletasks()
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    x = (_SCREEN_WIDTH - width) // 2
    y = (_SCREEN_HEIGHT - height) // 2
    window.geometry(f"+{x}+{y}")