#!/usr/bin/env python3
"""sms-shell 入口：Textual TUI 优先，textual 缺失回退旧 readline TUI，--gui 走 PySide6；单发模式直传位置参数。部署后其他路径可直接执行 bin/sms-shell 启动器定位起本脚本。"""
import os, sys, importlib
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
S = os.path.dirname(os.path.abspath(__file__))
def has_display():
    if os.name == "nt" or sys.platform == "darwin": return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
def gui_ok():
    if not has_display(): return False
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv); app.quit(); return True
    except Exception: return False
def launch(mode, extra=()):
    sp = [sys.executable, "-B", os.path.join(S, "shell_" + mode + ".py")] + list(extra)
    if mode == "gui" and os.name == "nt":
        import no_window; dn = open(os.devnull, "r+b")
        no_window.Popen(sp, stdin=dn, stdout=dn, stderr=dn, close_fds=True, sms_detach=True); return
    os.execv(sp[0], sp)
if __name__ == "__main__":
    args = sys.argv[1:]; pos = [a for a in args if not a.startswith("--")]
    if pos:
        try: launch("tui_textual", pos)
        except Exception: launch("tui", pos)
        sys.exit(0)
    if "--tui" in args:
        try: launch("tui_textual")
        except Exception: launch("tui")
    elif "--gui" in args:
        if not gui_ok(): print("GUI 探测失败，回退 TUI"); launch("tui")
        else: launch("gui")
    else:
        if sys.stdin.isatty() and sys.stdout.isatty():
            try: launch("tui_textual")
            except Exception: launch("tui" if has_display() else "tui")
        else: launch("tui")
