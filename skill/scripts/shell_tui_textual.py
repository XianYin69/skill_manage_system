#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时启动器回退 ps1 原生 DOS TUI）：流式输出日志＋输入框——回车提交·Tab 补全元指令与个性化指令·上下键翻历史·:quit/exit 退出；路由与 `:` 元指令治理同 shell_core（与 bin 原生 ps1 同套确定性路由）。"""
import os, sys
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_core as core
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container
    from textual.widgets import Footer, Header, Log, TextArea
except ImportError:
    print("textual 未安装，回退旧 TUI；pip install textual 可启用"); sys.exit(1)
META = [":" + m for m in ("agents","use","skill","cmds","intent","alias","unalias","hud","deploy","session","grant","api","config","web","ext","net","tts","learn","file","path","dream","image","help","quit")]
class Input(TextArea):
    async def _on_key(self, event):
        if event.key == "enter": self.app.submit(self.text); event.stop(); event.prevent_default(); return
        if event.key == "tab": self.app.complete(self); event.stop(); event.prevent_default(); return
        if event.key in ("up", "down") and self.app.history(self, event.key): event.stop(); event.prevent_default(); return
        await super()._on_key(event)
class ShellApp(App):
    CSS = "Screen{background:#1e1e2e} #log{color:#cdd6f4;border:none} #input{background:#181825;color:#89b4fa;border:none}"
    def compose(self): yield Header(); yield Container(Log(id="log"), Input(id="input"), Footer())
    def on_mount(self):
        self.hist = []; self.hi = 0; log = self.query_one("#log", Log); log.write(core.banner()); log.write(core.HELP); self.query_one("#input", Input).focus()
    def submit(self, text):
        if not (text := (text or "").strip()): return
        log = self.query_one("#log", Log); log.write("\x1b[38;5;39msms>\x1b[0m " + text)
        out = []; done = core.handle(text, lambda s: out.append(s)); [log.write(ln) for ln in out]
        self.query_one("#input", Input).text = ""
        if done == "exit": self.exit(); return
        self.hist.append(text); self.hi = len(self.hist)
    def complete(self, ta):
        try: names = [c["name"] for c in core.user_commands.load(core.SMS)["commands"]]
        except Exception: names = []
        hits = [m + " " for m in META + names if m.startswith(ta.text)]
        if hits: ta.text = hits[0]
    def history(self, ta, key):
        if not self.hist: return False
        self.hi = min(len(self.hist), max(0, self.hi + (-1 if key == "up" else 1))); ta.text = self.hist[self.hi] if self.hi < len(self.hist) else ""; return True
if __name__ == "__main__":
    args = sys.argv[1:]; pos = [a for a in args if not a.startswith("--")]
    if pos:
        try: core.handle(" ".join(pos), print)
        except Exception: pass
        sys.exit(0)
    app = ShellApp(); app.run()
