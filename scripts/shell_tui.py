#!/usr/bin/env python3
"""shell_tui.py — sms-shell TUI 前端：pwsh/bash/zsh 式终端交互壳，完全无需图形服务器（TTY/SSH 可跑），readline 历史 + Tab 命令补全 + ANSI 着色提示符；命令引擎见 shell_core。"""
import os, sys, subprocess, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core
try: import readline
except ImportError: readline = None
CMDS = ["help", "skills", "agents", "cmds", "intent", "use", "alias", "unalias", "session", "grant", "hud", "deploy", "tui", "gui", "quit"]
def _complete(text, state):
    hits = [m + " " for m in CMDS if m.startswith(text)]
    return hits[state] if state < len(hits) else None
def main():
    if readline:
        readline.set_completer(_complete); readline.parse_and_bind("tab: complete")
    print(core.BANNER + "\nhelp 看命令 · quit 退出 · gui 切换窗口版")
    while True:
        try: line = input("\x1b[38;5;39msms>\x1b[0m " if sys.stdout.isatty() else "sms> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not line: continue
        c = line.split()[0]
        if c in ("quit", "exit"): break
        if c == "help": print(core.HELP)
        elif c == "gui": subprocess.Popen([sys.executable, "-B", os.path.join(S, "shell_gui.py")]); print("GUI 已另起窗口")
        elif c == "tui": print("已在 TUI 模式")
        else:
            out = core.exec_line(line)
            print("\x1b[38;5;203m未知命令：" + c + "（help）\x1b[0m" if out is None else out)
if __name__ == "__main__":
    main()
