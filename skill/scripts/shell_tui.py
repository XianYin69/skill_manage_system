#!/usr/bin/env python3
"""shell_tui.py — sms-shell TUI 前端（免图形服务器，pwsh/bash/zsh 式·系统终端原生中文）：带参数＝单发模式（把参数拼为一轮话语或 `:` 元指令，执行完即退——系统原生 shell 即界面）；默认直达系统网关即时流式回显；个性化指令自动展开；`:` 元指令治理；readline 历史 + Tab 补全（元指令与个性化指令名）。"""
import os, sys
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception: pass
try: sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core, shell_console, stop_channel
try: import readline
except ImportError: readline = None
META = [":" + m for m in ("agents", "use", "skill", "cmds", "intent", "alias", "unalias", "hud", "deploy", "session", "workspace", "restart", "shutdown", "repair", "debug", "detail", "mode", "grant", "api", "config", "web", "ext", "net", "tts", "learn", "file", "path", "dream", "image", "help", "stop", "quit")]
def _complete(text, state):
    try:
        import user_commands
        names = [c["name"] for c in user_commands.load(core.SMS)["commands"]]
    except Exception:
        names = []
    hits = [m + " " for m in META + names if m.startswith(text)]
    return hits[state] if state < len(hits) else None
def emit(x):
    t = str(x)
    sys.stdout.write(t + ("" if t.endswith("\n") else "\n")); sys.stdout.flush()
def main():
    os.environ["SMS_DEBUG"] = "1" if "--debug" in sys.argv else os.environ.get("SMS_DEBUG", ""); pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if pos:
        core.handle(" ".join(pos), shell_console.wrap(emit)); return
    if readline:
        readline.set_completer(_complete); readline.parse_and_bind("tab: complete")
    emit(core.banner())
    while True:
        try: line = input("\x1b[38;5;39msms>\x1b[0m " if sys.stdout.isatty() else "sms> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not line: continue
        try: r = core.handle(line, shell_console.wrap(emit))
        except KeyboardInterrupt: stop_channel.clear(); emit("⛔ Ctrl+C 已中断本轮任务（停止旗标复位·可继续输入下一句）"); continue
        if r == "exit": break
if __name__ == "__main__":
    main()
