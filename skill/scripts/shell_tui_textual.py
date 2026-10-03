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
    from shell_tui_widgets import Input, StatusBar, TopBar, TaskBar; from shell_tui_side import Side
    from shell_tui_menus import Menus; from shell_tui_index import Index; from shell_tui_ws import Ws; from shell_tui_mode import Mode; from shell_tui_perms import Perms; from shell_tui_detail import Details; from shell_tui_flow import Flow; from shell_tui_web import Web
    from shell_tui_taskbar import Taskbar
except ImportError as ie:
    print("textual 未安装或前端模块缺失（回退旧 TUI）：%s；pip install textual 可启用" % ie); sys.exit(1)
class ShellApp(Menus, Index, Ws, Mode, Perms, Flow, Taskbar, Web, App):
    ENABLE_COMMAND_PALETTE = False  # 底栏去重：Textual 自带 Ctrl+P 命令面板与 F1 主菜单功能重复，关掉免得多一个不明按钮
    CSS = "Screen{background:#1e1e2e} #top{height:1;background:#11111b;color:#89b4fa;padding:0 1} #log{width:1fr;color:#cdd6f4;border:round #313244} #side{width:1fr;background:#11111b;color:#cdd6f4;border:round #313244;padding:0 1} #taskbar{height:1;display:none;} #taskhint{width:1fr;color:#a6adc8;padding:0 1;text-overflow:ellipsis;} #taskbar Button{height:1;padding:0 1;} #input{background:#181825;color:#89b4fa;border:none;height:5} #status{background:#11111b}"
    # 底部栏重排（2026-09-26 用户报障「选项溢出」）：Footer 只显高频 8 键，其余仍生效但从底栏隐藏（F5/F6/F8/F10/Shift+Tab/Ctrl+L 全收进 F1 主菜单）
    BINDINGS = [Binding(k, a, d, priority=k != "escape", show=s) for k, a, d, s in [("f1,alt+m", "menu_main", "菜单", True), ("f2,alt+k", "menu_skill_index", "SKILL索引", False), ("ctrl+k", "menu_skill", "技能", True), ("f3,alt+h", "help_cmd", "帮助", True), ("f4,alt+c", "config", "配置", True), ("f7", "menu_mode", "模式", True), ("f9", "detail_win", "详情", True), ("ctrl+q", "exit_app", "退出", True), ("f5", "menu_files", "文件索引", False), ("f6", "menu_ws", "工作区", False), ("f8", "editor", "编辑器", False), ("f10", "menu_perms", "权限工具", False), ("shift+tab", "agents_menu", "agent", False), ("ctrl+l", "clear_log", "清屏", False), ("escape", "mode_chat", "回对话", False), ("ctrl+shift+c", "copy_log", "复制全部输出", True), ("f11", "stop_task", "停止", False), ("f12", "continue_task", "继续", False), ("ctrl+c", "confirm_quit", "退出确认", False)]]
    def __init__(self): super().__init__(); self.hist = []; self.logbuf = []; self.hi = 0; self.steps = []; self.touched = []; self.details = []; self.busy = False; self.task_prog = ""; self.pend = []; self.awaiting = None
    def compose(self):
        prog = ProgressBar(total=None, id="prog"); prog.display = False  # 空转放大器：默认不显，busy 由 flow 打开
        yield TopBar(id="top"); yield prog; yield Horizontal(RichLog(id="log", wrap=True, max_lines=400), VerticalScroll(Side(id="side"))); yield TaskBar(id="taskbar"); yield Input(id="input"); yield StatusBar(id="status"); yield Footer()
    def on_mount(self):
        import ask_channel; ask_channel.arm()
        try:
            import net_util as nu
            if (core.settings.get("web_shell") or {}).get("enabled", True) and not nu.running("web_shell"): nu.spawn("web_shell")
        except Exception: pass
        self._logw = self.query_one("#log", RichLog); self.set_interval(0.4, self.ask_poll); self.set_interval(1.0, self.bus_poll); self.set_interval(2.0, self.taskbar_refresh); self.set_interval(30, self.plan_tick)
        self.set_interval(1.0, self.spin_tick)  # 空转哨兵 UI 侧心跳：只消费 hide_req 藏 #prog，自转不算进展
        try:
            import spin_guard; spin_guard.arm(self)
        except Exception: pass
        try:
            import planned_tasks as pt
            self.run_worker(lambda: pt.start(), thread=True)  # 壳一起即拉起分离调度进程（pid 文件防重复）
        except Exception: pass
        self.run_worker(self.warm, thread=True)
        self.title = "sms-shell"; self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
        try:
            import console_font
            _fm = console_font.ensure_cjk()
            if _fm: self.log_line(Text(_fm, style="yellow"))
        except Exception: pass
        blk = core.startup_block(); self.log_line(Text(core.banner() + (("\n\n" + blk) if blk else ""), style="bold cyan")); self.query_one("#input", Input).focus()
        try:
            import close_guard
            self.log_line(Text("关闭拦截：" + close_guard.arm(self), style="dim"))
        except Exception: pass
        try:
            import shell_lifecycle as lc
            hint, nxt = lc.resume()
            hint and self.log_line(Text(hint, style="bold magenta"))
            nxt and self.set_timer(1.5, lambda: self.submit(nxt))  # 重启后自动续跑未完成任务表
        except Exception: pass
    def spin_tick(self):
        """1s 一次：把「藏 #prog」请求交回 UI 线程消费（停 15fps 整屏重绘＝归还核子）。"""
        try:
            import spin_guard; return spin_guard.tick(self)
        except Exception: return "ok"
    def log_line(self, t):
        try:
            w = getattr(self, "_logw", None) or self.query_one("#log", RichLog); self._logw = w
            self.log_copy(t); w.write(t if isinstance(t, Text) else Text(str(t)))
            try:
                import spin_guard; spin_guard.beat("log")
            except Exception: pass
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
