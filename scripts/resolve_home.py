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
    for name in ("registry", "sessions", "tmp"):
        os.makedirs(os.path.join(p, name), exist_ok=True)
    return p


def temp(p, rel="", mkdir=False):
    base = os.path.realpath(os.path.join(p, "tmp"))
    d = os.path.realpath(os.path.join(base, *(rel or "").split(os.sep)))
    if d != base and not d.startswith(base + os.sep):
        raise SystemExit("拒绝：子 skill 新建目录必须位于 SMS/tmp 下")
    if mkdir:
        os.makedirs(d, exist_ok=True)
    return d


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "temp":
        print(temp(ensure(), sys.argv[2] if len(sys.argv) > 2 else "", "--mkdir" in sys.argv))
    else:
        p = ensure() if "--ensure" in sys.argv or cmd == "ensure" else resolve()
        print(p)