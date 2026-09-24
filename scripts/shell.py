#!/usr/bin/env python3
"""shell.py — sms-shell 入口：有图形服务器→GUI 窗口版（shell_gui），无→TUI 终端版（shell_tui，pwsh/bash/zsh 式、免图形服务器）；`--tui`/`--gui` 强制选择，GUI 探测失败自动回退 TUI。部署后其他路径可直接执行本 skill 的 bin/sms-shell(.cmd) 或 deploy.py --launcher 生成的启动器。"""
import os, sys, subprocess
S = os.path.dirname(os.path.abspath(__file__))
def has_display():
    if os.name == "nt" or sys.platform == "darwin": return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
def gui_ok():
    if not has_display(): return False
    try:
        import tkinter
        r = tkinter.Tk(); r.withdraw(); r.destroy(); return True
    except Exception: return False
def launch(mode):
    if mode == "gui" and not gui_ok():
        print("无可用图形服务器（X11/Wayland/RDP），回退 TUI"); mode = "tui"
    sp = [sys.executable, "-B", os.path.join(S, "shell_" + mode + ".py")]
    if mode == "gui" and os.name == "nt":
        dn = open(os.devnull, "r+b")
        subprocess.Popen(sp, stdin=dn, stdout=dn, stderr=dn, creationflags=0x8 | 0x08000000, close_fds=True); return
    os.execv(sp[0], sp)
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--tui" in args: launch("tui")
    elif "--gui" in args: launch("gui")
    else: launch("gui" if sys.stdin.isatty() and sys.stdout.isatty() and gui_ok() else "tui")
