#!/usr/bin/env python3
"""shell_tui_textual.py — sms-shell Textual TUI 前端（依赖 textual；缺失时启动器回退 ps1 原生 DOS TUI）：TopBar 顶栏＋左右分屏——左＝RichLog 流式输出（只留简略：长输出自动折叠·全文进右栏「详细细节」＋F9 全屏·shell_tui_detail；SSE 逐段吐字不再整轮空等·gateway_sse）、右＝可滚动 Side 侧栏·底部 Input＋StatusBar 计时步进·进度条。交互流 shell_tui_flow.Flow＝任务进行中可输入（排队自动续发）＋大模型 ask_user 提问即时应答＋启动接续上次对话＋链缓存预热。键位全 priority=True——F1 菜单·Ctrl+K 技能·F2/「/」SKILL 索引·F5 文件·F6 工作区·F7 模式(查看/对话/直通·Esc 回)·F8 编辑·F9 详情全屏＝不透明 Fullscreen（v3 弃 alpha 遮罩防真机合成崩屏·异常降级只坏面板不坏主壳）·F10 权限与工具·F3 帮助·F4 图形配置·Shift+Tab agent·Tab 补全·↑↓ 历史·Ctrl+L 清屏·Ctrl+Q 退出。路由与治理同 shell_core。"""
import os, sys, contextlib
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ["PYTHONUTF8"] = "1"; os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_core as core
import session_reg as _sreg; SELF_SESS = _sreg.bind("client", os.getpid(), "Textual壳")
try:
    from textual.app import App, ComposeResult, Binding
    from textual.containers import Horizontal, VerticalScroll
    from textual.widgets import Footer, ProgressBar, RichLog; from rich.text import Text
    from shell_tui_widgets import Input, StatusBar, TopBar; from shell_tui_side import Side
    from shell_tui_menus import Menus; from shell_tui_index import Index; from shell_tui_ws import Ws; from shell_tui_mode import Mode; from shell_tui_perms import Perms; from shell_tui_detail import Details; from shell_tui_flow import Flow
except ImportError as ie:
    print("textual 未安装或前端模块缺失（回退旧 TUI）：%s；pip install textual 可启用" % ie); sys.exit(1)
class ShellApp(Menus, Index, Ws, Mode, Perms, Flow, App):
    CSS = "Screen{background:#1e1e2e} #top{height:1;background:#11111b;color:#89b4fa;padding:0 1} #log{width:1fr;color:#cdd6f4;border:round #313244} #side{width:1fr;background:#11111b;color:#cdd6f4;border:round #313244;padding:0 1} #input{background:#181825;color:#89b4fa;border:none;height:5} #status{background:#11111b}"
    # 底部栏重排（2026-09-26 用户报障「选项溢出」）：Footer 只显高频 8 键，其余仍生效但从底栏隐藏（F5/F6/F8/F10/Shift+Tab/Ctrl+L 全收进 F1 主菜单）
    BINDINGS = [Binding(k, a, d, priority=k != "escape", show=s) for k, a, d, s in [("f1,alt+m", "menu_main", "菜单", True), ("f2,alt+k", "menu_skill_index", "SKILL索引", True), ("ctrl+k", "menu_skill", "技能", True), ("f3,alt+h", "help_cmd", "帮助", True), ("f4,alt+c", "config", "配置", True), ("f7", "menu_mode", "模式", True), ("f9", "detail_win", "详情", True), ("ctrl+q", "exit_app", "退出", True), ("f5", "menu_files", "文件索引", False), ("f6", "menu_ws", "工作区", False), ("f8", "editor", "编辑器", False), ("f10", "menu_perms", "权限工具", False), ("shift+tab", "agents_menu", "agent", False), ("ctrl+l", "clear_log", "清屏", False), ("escape", "mode_chat", "回对话", False)]]
    def __init__(self): super().__init__(); self.hist = []; self.hi = 0; self.steps = []; self.touched = []; self.details = []; self.busy = False; self.task_prog = ""; self.pend = []; self.awaiting = None
    def compose(self): yield TopBar(id="top"); yield ProgressBar(total=None, id="prog"); yield Horizontal(RichLog(id="log", wrap=True), VerticalScroll(Side(id="side"))); yield Input(id="input"); yield StatusBar(id="status"); yield Footer()
    def on_mount(self):
        import ask_channel; ask_channel.arm(); self._logw = self.query_one("#log", RichLog); self.set_interval(0.4, self.ask_poll); self.run_worker(self.warm, thread=True)
        self.title = "sms-shell"; self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
        blk = core.startup_block(); self.log_line(Text(core.banner() + (("\n\n" + blk) if blk else ""), style="bold cyan")); self.query_one("#input", Input).focus()
    def log_line(self, t):
        try:
            w = getattr(self, "_logw", None) or self.query_one("#log", RichLog); self._logw = w
            w.write(t if isinstance(t, Text) else Text(str(t)))
        except Exception: pass
    def action_detail_win(self):
        if isinstance(self.screen, Details): self.screen.action_close(); return
        try: self.push_screen(Details())
        except Exception as e: self.log_line(Text("F9 详情面板打开失败（主界面不受影响）：" + str(e)[:200], style="red"))
if __name__ == "__main__":
    os.environ["SMS_DEBUG"] = "1" if "--debug" in sys.argv else os.environ.get("SMS_DEBUG", ""); pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if pos:
        with contextlib.suppress(Exception): core.handle(" ".join(pos), __import__("shell_console").wrap(print))
        sys.exit(0)
    ShellApp().run()
