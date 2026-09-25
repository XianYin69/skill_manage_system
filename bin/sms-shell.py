#!/usr/bin/env python3
"""sms-shell launcher: python Textual TUI preferred; fallback ps1 native DOS TUI; api -> locate.py."""
import os, sys, shutil, subprocess
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "C:\\Users\\User\\.kilocode\\skills\\skill_manage_system\\skill\\scripts")
if sys.argv[1:2] and sys.argv[1] == "api":
    sys.exit(subprocess.call([sys.executable, "-B", os.path.join(D, "locate.py")] + sys.argv[2:]))
try:
    import shell_tui_textual
    has_textual = True
except ImportError:
    has_textual = False
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
if pos:
    if has_textual:
        os.execv(sys.executable, [sys.executable, "-B", os.path.join("C:\\Users\\User\\.kilocode\\skills\\skill_manage_system\\skill\\scripts", "shell_tui_textual.py")] + pos)
    else:
        os.execv(sys.executable, [sys.executable, "-B", os.path.join("C:\\Users\\User\\.kilocode\\skills\\skill_manage_system\\skill\\scripts", "shell_tui.py")] + pos)
if has_textual and sys.stdin.isatty() and sys.stdout.isatty():
    os.execv(sys.executable, [sys.executable, "-B", os.path.join("C:\\Users\\User\\.kilocode\\skills\\skill_manage_system\\skill\\scripts", "shell_tui_textual.py")])
if has_textual:
    os.execv(sys.executable, [sys.executable, "-B", os.path.join("C:\\Users\\User\\.kilocode\\skills\\skill_manage_system\\skill\\scripts", "shell_tui_textual.py")])
ps1 = os.path.join(D, "sms_shell.ps1")
if os.path.isfile(ps1) and (shutil.which("powershell.exe") or shutil.which("pwsh")):
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
sys.exit(subprocess.call([sys.executable, "-B", os.path.join(D, "locate.py")] + sys.argv[1:]))
