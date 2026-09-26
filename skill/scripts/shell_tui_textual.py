#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时启动器回退 ps1 原生 DOS TUI）：TopBar 顶栏（左＝壳身份·数据流 中＝当前步骤/任务进度滚动 右＝时钟·shell_tui_widgets）＋左右分屏——左＝RichLog 流式输出（只留简略：工具/技能/步骤长输出自动折叠·全文进右栏「详细细节」＋F9 全屏·shell_tui_detail；llm 正文不折叠）、右＝可滚动 Side 侧栏（工作区/修改文件/链与会话/步骤/详细细节/会话总览·shell_tui_side）·底部 Input＋StatusBar 计时步进·进度条。键位全部 priority=True——修复 F6/F7 被 TextArea 内置 f6/f7 选词键绑吞掉（焦点在输入行时 App 收不到＝用户「F6 F7 不起作用」根因）。F1 菜单·Ctrl+K 技能·F2/「/」SKILL 索引·F5 文件·F6 工作区·F7 模式(查看/对话/直通·Esc 回)·F8 编辑·F9 详情全屏·F10 权限与工具(系统权限＋大模型工具开关＋HUD·shell_tui_perms)·F3 帮助(短表·全量 :cmds)·F4 图形配置·Shift+Tab agent·Tab 补全·↑↓ 历史·Ctrl+L 清屏·Ctrl+Q 退出。启动/收口按 settings hud.enabled 刷新 HUD。路由与治理同 shell_core。"""
import os, sys, contextlib
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_core as core
try:
    from textual.app import App, ComposeResult, Binding
    from textual.containers import Horizontal, VerticalScroll
    from textual.widgets import Footer, ProgressBar, RichLog; from rich.text import Text
    from shell_tui_widgets import Input, StatusBar, TopBar; from shell_tui_side import Side
    from shell_tui_menus import Menus; from shell_tui_index import Index; from shell_tui_ws import Ws; from shell_tui_mode import Mode; from shell_tui_perms import Perms; from shell_tui_detail import shrink, Details
except ImportError:
    print("textual 未安装，回退旧 TUI；pip install textual 可启用"); sys.exit(1)
class ShellApp(Menus, Index, Ws, Mode, Perms, App):
    CSS = "Screen{background:#1e1e2e} #top{height:1;background:#11111b;color:#89b4fa;padding:0 1} #log{width:1fr;color:#cdd6f4;border:round #313244} #side{width:1fr;background:#11111b;color:#cdd6f4;border:round #313244;padding:0 1} #input{background:#181825;color:#89b4fa;border:none;height:5} #status{background:#11111b}"
    BINDINGS = [Binding(k, a, d, priority=k != "escape") for k, a, d in [("f1,alt+m", "menu_main", "菜单"), ("f7", "menu_mode", "模式"), ("f8", "editor", "编辑器"), ("escape", "mode_chat", "回对话"), ("ctrl+k", "menu_skill", "技能"), ("f4,alt+c", "config", "配置"), ("f2,alt+k", "menu_skill_index", "SKILL索引"), ("f5", "menu_files", "文件索引"), ("f6", "menu_ws", "工作区"), ("f3,alt+h", "help_cmd", "帮助"), ("f9", "detail_win", "详情"), ("f10", "menu_perms", "权限工具"), ("shift+tab", "agents_menu", "agent"), ("ctrl+l", "clear_log", "清屏"), ("ctrl+q", "exit_app", "退出")]]
    def __init__(self): super().__init__(); self.hist = []; self.hi = 0; self.steps = []; self.touched = []; self.details = []; self.busy = False; self.task_prog = ""
    def compose(self): yield TopBar(id="top"); yield ProgressBar(total=None, id="prog"); yield Horizontal(RichLog(id="log", wrap=True), VerticalScroll(Side(id="side"))); yield Input(id="input"); yield StatusBar(id="status"); yield Footer()
    def on_mount(self):
        self.title = "sms-shell"; self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
        self.log_line(Text(core.banner(), style="bold cyan")); self.query_one("#input", Input).focus()
    def log_line(self, t): self.query_one("#log", RichLog).write(t if isinstance(t, Text) else Text(str(t)))
    def _hud(self, cmd, *a): core.settings.get("hud.enabled") and core.run_script("hud.py", [cmd] + list(a))
    def submit(self, text):
        if not (text := (text or "").strip()): return
        if self.busy: self.log_line(Text("忙：上一条仍在处理（见状态栏计时）", style="yellow")); return
        self.log_line(Text("sms> ", style="bold blue") + Text(text)); self.query_one("#input", Input).text = ""
        self.hist.append(text); self.hi = len(self.hist); self.steps = []; self.touched = []; self.busy = True
        self._hud("session", text[:40]); self.query_one("#prog", ProgressBar).display = True; self.query_one("#status", StatusBar).begin(); self.run_worker(lambda: self._work(text), thread=True)
    def _oline(self, s): s2 = shrink(self, str(s)); ("$ " in s2 or "config:" in s2 or ".py" in s2 or ".md" in s2) and self.touched.append(s2[:200]); self.call_from_thread(self.log_line, s2)
    def _work(self, text, done=None):
        try: done = core.handle(text, self._oline, self.steps.append, self._ev)
        except Exception as e: core.debug.enabled() and core.debug.log("EXC " + core.debug.tb()); self.call_from_thread(self.log_line, Text("处理异常：" + (core.debug.tb()[-900:] if core.debug.enabled() else repr(e)[:200]), style="red"))
        self.call_from_thread(self._done, done)
    def _done(self, done):
        self.busy = False; self.task_prog = ""; self.query_one("#prog", ProgressBar).display = False; self.query_one("#status", StatusBar).end(); self.subconv_hint(); self._hud("step", "收口就绪", "120")
        if done == "exit": self.exit()
        elif done == "config": self.action_config()
        elif isinstance(done, str) and done.startswith(("edit:", "view:")): self._open_editor(done.split(":", 1)[1], done.startswith("view:"))
    def action_detail_win(self): self.push_screen(Details())
if __name__ == "__main__":
    os.environ["SMS_DEBUG"] = "1" if "--debug" in sys.argv else os.environ.get("SMS_DEBUG", ""); pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if pos:
        with contextlib.suppress(Exception): core.handle(" ".join(pos), print)
        sys.exit(0)
    ShellApp().run()
