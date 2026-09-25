#!/usr/bin/env python3
"""shell_tui.py — sms-shell TUI 前端（免图形服务器，pwsh/bash/zsh 式）：输入话语即时流式回显当前 agent 的输出；个性化指令自动展开；`:` 元指令治理；readline 历史 + Tab 补全（元指令与个性化指令名）。"""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core
try: import readline
except ImportError: readline = None
META = [":" + m for m in ("agents", "use", "skill", "cmds", "intent", "alias", "unalias", "hud", "deploy", "session", "grant", "help", "quit")]
def _complete(text, state):
    try:
        import user_commands
        names = [c["name"] for c in user_commands.load(core.SMS)["commands"]]
    except Exception:
        names = []
    hits = [m + " " for m in META + names if m.startswith(text)]
    return hits[state] if state < len(hits) else None
def main():
    if readline:
        readline.set_completer(_complete); readline.parse_and_bind("tab: complete")
    print(core.banner())
    while True:
        try: line = input("\x1b[38;5;39msms>\x1b[0m " if sys.stdout.isatty() else "sms> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not line: continue
        if core.handle(line, print) == "exit": break
if __name__ == "__main__":
    main()
