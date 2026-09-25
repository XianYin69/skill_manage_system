#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时 shell.py 回退旧 TUI）：流式输出日志＋输入框 Tab 补全+上下键历史·`:` 元指令与个性化指令路由同 shell_core。"""
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
    from textual.reactive import reactive
    from textual.widgets import Footer, Header, Log, TextArea
except ImportError:
    print("textual 未安装，回退旧 TUI；pip install textual 可启用"); sys.exit(1)
META = [":" + m for m in ("agents","use","skill","cmds","intent","alias","unalias","hud","deploy","session","grant","api","config","web","ext","net","tts","learn","file","path","dream","image","help","quit")]
class ShellApp(App):
    CSS = "Screen{background:#1e1e2e} #log{color:#cdd6f4;border:none} #input{background:#181825;color:#89b4fa;border:none}"
    prompt = reactive("sms> ")
    def compose(self): yield Header(); yield Container(Log(id="log"), TextArea(id="input"), Footer())
    def on_mount(self):
        self.query_one("#log", Log).write(core.banner()); self.query_one("#log", Log).write(core.HELP)
        self.set_interval(0.1, self._check_input)
    def _check_input(self):
        ta = self.query_one("#input", TextArea); txt = ta.text.strip()
        if txt and txt != self._last: self._last = txt; self.run_action("submit", txt); ta.text = ""
    def on_key(self, event):
        if event.key == "tab":
            ta = self.query_one("#input", TextArea); t = ta.text
            hits = [m+" " for m in META if m.startswith(t)] + [c["name"]+" " for c in core.user_commands.load(core.SMS)["commands"]]
            if hits: ta.text = hits[0]; event.stop()
    def action_submit(self, text):
        if not text.strip(): return
        log = self.query_one("#log", Log); log.write(f"\x1b[38;5;39msms>\x1b[0m {text}")
        out = []; core.handle(text, lambda s: out.append(s))
        for ln in out: log.write(ln)
if __name__ == "__main__":
    args = sys.argv[1:]; pos = [a for a in args if not a.startswith("--")]
    if pos:
        try: core.handle(" ".join(pos), print)
        except Exception: pass
        sys.exit(0)
    app = ShellApp(); app.run()
