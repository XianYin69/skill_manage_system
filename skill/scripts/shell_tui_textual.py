#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时启动器回退 ps1 原生 DOS TUI）：RichLog 富文本渲染（修复转义序列乱码）·工作线程流式执行不阻塞界面·状态栏实时显示步骤名/步序/本对话用时（shell_tui_widgets.StatusBar）·进度条·F1/Alt+M 主菜单·Ctrl+K 托管技能菜单（skill_route 路由·命中记 skill_call 链·真调技能）·Shift+Tab agent 菜单·Tab 补全·上下历史·Ctrl+Enter 提交·Ctrl+L 清屏·Ctrl+Q 退出（菜单/补全/历史见 shell_tui_menus.Menus）；路由与治理同 shell_core。"""
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
    from textual.widgets import Footer, Header, ProgressBar, RichLog
    from rich.text import Text
    from shell_tui_widgets import Input, StatusBar
    from shell_tui_menus import Menus
except ImportError:
    print("textual 未安装，回退旧 TUI；pip install textual 可启用"); sys.exit(1)
class ShellApp(Menus, App):
    CSS = "Screen{background:#1e1e2e} #log{color:#cdd6f4;border:none} #input{background:#181825;color:#89b4fa;border:none;height:5} #status{background:#11111b}"
    BINDINGS = [("f1,alt+m","menu_main","菜单"),("ctrl+k","menu_skill","技能"),("shift+tab","agents_menu","agent"),("alt+h","help_cmd","帮助"),("ctrl+l","clear_log","清屏"),("ctrl+q","exit_app","退出")]
    def __init__(self): super().__init__(); self.hist = []; self.hi = 0; self.steps = []; self.busy = False
    def compose(self): yield Header(); yield ProgressBar(total=None, id="prog"); yield Container(RichLog(id="log"), Input(id="input"), StatusBar(id="status"), Footer())
    def on_mount(self):
        self.title = "sms-shell"; self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
        self.log_line(Text(core.banner(), style="bold cyan")); self.log_line(core.HELP); self.query_one("#input", Input).focus()
    def log_line(self, t): self.query_one("#log", RichLog).write(t if isinstance(t, Text) else Text(str(t)))
    def submit(self, text):
        if not (text := (text or "").strip()): return
        if self.busy: self.log_line(Text("忙：上一条仍在处理（见状态栏计时）", style="yellow")); return
        self.log_line(Text("sms> ", style="bold blue") + Text(text)); self.query_one("#input", Input).text = ""
        self.hist.append(text); self.hi = len(self.hist); self.steps = []; self.busy = True
        self.query_one("#prog", ProgressBar).display = True; self.query_one("#status", StatusBar).begin(); self.run_worker(lambda: self._work(text), thread=True)
    def _work(self, text):
        done = None
        try: done = core.handle(text, lambda s: self.call_from_thread(self.log_line, s), self.steps.append)
        except Exception as e: self.call_from_thread(self.log_line, Text("处理异常：" + repr(e)[:200], style="red")); done = None
        self.call_from_thread(self._done, done)
    def _done(self, done):
        self.busy = False; self.query_one("#prog", ProgressBar).display = False; self.query_one("#status", StatusBar).end()
        if done == "exit": self.exit()
if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if pos:
        try: core.handle(" ".join(pos), print)
        except Exception: pass
        sys.exit(0)
    ShellApp().run()
