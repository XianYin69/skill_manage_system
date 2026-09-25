#!/usr/bin/env python3
"""sms-shell launcher: Textual TUI preferred (source skill located via adjacent→SMS_SKILL→sms_skill, NO hardcoded path); ps1 native DOS TUI next to this file as fallback; no PowerShell -> locate.py python engine; first arg api -> locate.py."""
import os, sys, shutil, subprocess, importlib.util
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
if sys.argv[1:2] == ["api"]:
    sys.exit(subprocess.call([sys.executable, "-B", os.path.join(D, "locate.py")] + sys.argv[1:]))
BASE = None
try:
    import locate
    BASE = locate.find_base()
except Exception:
    pass
args = sys.argv[1:]
TUI = os.path.join(BASE, "scripts", "shell_tui_textual.py") if BASE else None
if TUI and os.path.isfile(TUI) and "--gui" not in args and importlib.util.find_spec("textual"):
    os.execv(sys.executable, [sys.executable, "-B", TUI] + args)
ps1 = shutil.which("powershell.exe") or shutil.which("pwsh")
if os.path.isfile(os.path.join(D, "sms_shell.ps1")) and ps1:
    if not args:
        sys.exit(subprocess.call([ps1, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(D, "sms_shell.ps1")]))
    sys.exit(subprocess.call([ps1, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "& '%s' @args" % os.path.join(D, "sms_shell.ps1")] + args))
sys.exit(subprocess.call([sys.executable, "-B", os.path.join(D, "locate.py")] + args))
