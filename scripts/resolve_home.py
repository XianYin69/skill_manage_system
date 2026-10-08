#!/usr/bin/env python3
"""resolve_home.py — 解析 SMS 固定路径（env SMS_HOME -> 缓存目录 -> 根目录）。"""
import os, sys, platform

NAME = "SMS"


def _cache():
    s = platform.system()
    if s == "Windows":
        return os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    if s == "Darwin":
        return os.path.expanduser("~/Library/Caches")
    return os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")


def resolve():
    if os.environ.get("SMS_HOME"):
        return os.environ["SMS_HOME"]
    return os.path.join(_cache() or os.path.expanduser("~"), NAME)


def ensure():
    p = resolve()
    os.makedirs(os.path.join(p, "registry"), exist_ok=True)
    os.makedirs(os.path.join(p, "sessions"), exist_ok=True)
    return p


if __name__ == "__main__":
    p = resolve()
    if "--ensure" in sys.argv:
        ensure()
    print(p)