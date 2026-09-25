#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时启动器回退 ps1 原生 DOS TUI）：TopBar 顶栏（左＝壳身份·数据流 中＝当前任务步骤滚动简述 右＝时钟·shell_tui_widgets）＋左右分屏——左＝RichLog 流式输出（wrap 换行·无转义乱码）右＝Side 侧栏（工作区/路径/修改文件/链与会话/当前步骤类型简释·shell_tui_side）·底部 Input＋StatusBar 计时步进·进度条·F1/Alt+M 主菜单·Ctrl+K 托管技能菜单·「/」或 F2/Alt+K 打开 SKILL.md 索引（id→SKILL.md 路径·首项索引本地文件→文件选择菜单·shell_tui_files→:index 登记 scan_roots）·F3/Alt+H 帮助·F4/Alt+C 图形化配置编辑（shell_tui_config·方向键/字母过滤/空格布尔与多选/Shift+Tab 编辑值）——注：VS Code/部分 Windows 终端把 Alt+字母截获为窗口菜单，故 F1 菜单/F2 索引/F3 帮助/F4 配置/Ctrl+K 为恒可达主键，Alt 组为兼容终端保留·Shift+Tab agent 菜单·Tab 补全·上下历史·Ctrl+Enter 提交·Ctrl+L 清屏·Ctrl+Q 退出（菜单/补全/历史见 shell_tui_menus.Menus）；路由与治理同 shell_core。"""
import os, sys
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_core as core
try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal
    from textual.widgets import Footer, ProgressBar, RichLog
    from rich.text import Text
    from shell_tui_widgets import Input, StatusBar, TopBar
    from shell_tui_side import Side
    from shell_tui_menus import Menus
except ImportError:
    print("textual 未安装，回退旧 TUI；pip install textual 可启用"); sys.exit(1)
class ShellApp(Menus, App):
    CSS = "Screen{background:#1e1e2e} #top{height:1;background:#11111b;color:#89b4fa;padding:0 1} #log{width:1fr;color:#cdd6f4;border:round #313244} #side{width:1fr;background:#11111b;color:#cdd6f4;border:round #313244;padding:0 1} #input{background:#181825;color:#89b4fa;border:none;height:5} #status{background:#11111b}"
    BINDINGS = [("f1,alt+m","menu_main","菜单"),("ctrl+k","menu_skill","技能"),("f4,alt+c","config","配置"),("f2,alt+k","menu_skill_index","SKILL索引"),("f3,alt+h","help_cmd","帮助"),("shift+tab","agents_menu","agent"),("ctrl+l","clear_log","清屏"),("ctrl+q","exit_app","退出")]
    def __init__(self): super().__init__(); self.hist = []; self.hi = 0; self.steps = []; self.touched = []; self.busy = False
    def compose(self): yield TopBar(id="top"); yield ProgressBar(total=None, id="prog"); yield Horizontal(RichLog(id="log", wrap=True), Side(id="side")); yield Input(id="input"); yield StatusBar(id="status"); yield Footer()
    def on_mount(self):
        self.title = "sms-shell"; self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
        self.log_line(Text(core.banner(), style="bold cyan")); self.log_line(core.HELP); self.query_one("#input", Input).focus()
    def log_line(self, t): self.query_one("#log", RichLog).write(t if isinstance(t, Text) else Text(str(t)))
    def submit(self, text):
        if not (text := (text or "").strip()): return
        if self.busy: self.log_line(Text("忙：上一条仍在处理（见状态栏计时）", style="yellow")); return
        self.log_line(Text("sms> ", style="bold blue") + Text(text)); self.query_one("#input", Input).text = ""
        self.hist.append(text); self.hi = len(self.hist); self.steps = []; self.touched = []; self.busy = True
        self.query_one("#prog", ProgressBar).display = True; self.query_one("#status", StatusBar).begin(); self.run_worker(lambda: self._work(text), thread=True)
    def _oline(self, s): ("$ " in s or "config:" in s or ".py" in s or ".md" in s) and self.touched.append(s[:200]); self.call_from_thread(self.log_line, s)
    def _work(self, text, done=None):
        try: done = core.handle(text, self._oline, self.steps.append)
        except Exception as e: self.call_from_thread(self.log_line, Text("处理异常：" + repr(e)[:200], style="red"))
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
