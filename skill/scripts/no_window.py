#!/usr/bin/env python3
"""no_window.py — 静默子进程统一封装：前台运行任务时不再弹出命令行窗口。

成因：GUI/无控制台宿主（pythonw、壳内工作线程）下，Windows 会为每个 console 子进程
新建一个控制台，用户看到的就是「每执行一条命令闪一个黑窗」。
CREATE_NO_WINDOW(0x08000000) 让子进程不分配新控制台；
STARTF_USESHOWWINDOW + SW_HIDE 兜住仍会自建窗口的宿主（conhost/包装器脚本）。

边界：需要真正脱离父进程的后台调用点（hud/dream_bg/qq_listen/shell 自举）自行保留
DETACHED_PROCESS 语义，不经本模块改写；本模块只保证「不弹窗」，不改变进程归属与超时。
"""
import os
import sys
import subprocess

NT = (os.name == "nt")
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
SW_HIDE = 0


def _si():
    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = SW_HIDE
    except Exception:
        pass
    return si


def flags(kw, detach=False):
    """合并调用点已有 creationflags（绝不丢失），并补 STARTUPINFO 隐藏窗口。"""
    if not NT:
        kw.pop("sms_detach", None)
        return kw
    f = int(kw.get("creationflags") or 0)
    f |= (DETACHED_PROCESS | CREATE_NO_WINDOW) if detach else CREATE_NO_WINDOW
    kw["creationflags"] = f
    kw.setdefault("startupinfo", _si())
    kw.pop("sms_detach", None)
    return kw


def run(*a, **kw):
    detach = bool(kw.pop("sms_detach", False))
    return subprocess.run(*a, **flags(kw, detach))


def Popen(*a, **kw):
    detach = bool(kw.pop("sms_detach", False))
    return subprocess.Popen(*a, **flags(kw, detach))


def selftest():
    """只读自检：子进程应拿不到新控制台（GetConsoleWindow()==0）。"""
    code = ("import ctypes;print('CONSOLE=%s' % (ctypes.windll.kernel32.GetConsoleWindow()))")
    p = run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    out = (p.stdout or p.stderr or "").strip()
    return {"rc": p.returncode, "child": out[:60], "silent": "CONSOLE=0" in out}


if __name__ == "__main__":
    import json
    print(json.dumps(selftest(), ensure_ascii=False))
