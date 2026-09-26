#!/usr/bin/env python3
"""shell_tui_widgets.py — sms-shell Textual TUI 组件（配 shell_tui_textual）：Input（回车/ctrl+enter 提交·Tab 补全·Shift+Tab agent 菜单·「/」空行时打开 SKILL.md 技能索引（F5 为文件索引）·上下历史）、StatusBar（步进器＋每步名称轮询＋本对话用时计时，RichLog 之外的实时状态行）、TopBar（顶栏：左＝壳身份·数据流·界面模式徽标（对话/直通/查看）·中＝task_detail 任务进度优先，否则当前步骤滚动简述·右＝用户地区实时日期＋星期＋时间（本机时区），0.5s 自刷新）、Menu（ModalScreen 快捷菜单：F1/Alt+M/Ctrl+K 打开，Enter 选择→命令串回 app.pick）。"""
import time, debug, shell_mode
from rich.text import Text
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListView, ListItem, Static, TextArea
SP = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
class Input(TextArea):
    async def _on_key(self, event):
        k = event.key; a = self.app
        if k in ("enter", "ctrl+enter"): a.submit(self.text); event.stop(); event.prevent_default(); return
        if k == "tab": a.complete(self); event.stop(); event.prevent_default(); return
        if k == "shift+tab": a.agents_menu(); event.stop(); event.prevent_default(); return
        if k == "slash" and not self.text.strip(): a.action_menu_skill_index(); event.stop(); event.prevent_default(); return
        if k in ("up", "down") and a.history(self, k): event.stop(); event.prevent_default(); return
        await super()._on_key(event)
class StatusBar(Static):
    def on_mount(self): self.t0 = 0.0; self.last = 0.0; self.busy = False; self.seen = 0; self.set_interval(0.15, self._tick)
    def begin(self): self.t0 = time.time(); self.busy = True; self.seen = 0
    def end(self):
        self.last = time.time() - self.t0 if self.t0 else self.last; secs = self.last; self.busy = False
        self.update(Text(" ● 就绪 · 上一条对话用时 %.1fs · 共 %d 步（F1 菜单 · F7 模式 · Ctrl+K 技能 · Shift+Tab agent · Ctrl+Q 退出）" % (secs, len(self.app.steps)), style="dim green"))
    def _tick(self):
        steps = self.app.steps
        sp = SP[int(time.time() * 8) % 10] if self.busy else "●"
        el = "%.1fs" % (time.time() - self.t0) if self.busy else "%.1fs" % self.last
        self.update(Text("%s %s ｜ 对话用时 %s ｜ 步序 %d" % (sp, steps[-1] if steps else "就绪", el, len(steps)), style="bold yellow" if self.busy else "dim"))
class TopBar(Static):
    def on_mount(self): self.off = 0; self.set_interval(0.5, self._tick)
    def _tick(self):
        a = self.app; steps = list(getattr(a, "steps", [])); cur = getattr(a, "task_prog", "") or (steps[-1] if steps else "") or "sms 托管技能数据流 · 就绪"
        left = (getattr(a, "title", "") or "sms-shell") + ("·DEB" if debug.enabled() else "") + "·" + shell_mode.badge() + " ▸ " + (getattr(a, "sub_title", "") or "")
        right = time.strftime("%Y-%m-%d") + " 周" + "一二三四五六日"[time.localtime().tm_wday] + time.strftime(" %H:%M:%S"); mid = max((self.size.width or 80) - len(left) - len(right) - 6, 8)
        if len(cur) <= mid: core = cur
        else:
            pad = cur + " · "; self.off = (self.off + 1) % len(pad); core = (pad * (mid // len(pad) + 2))[self.off:self.off + mid]
        self.update(Text("%s │ %s │ %s" % (left, core.ljust(mid), right), style="bold #89b4fa"))
class Menu(ModalScreen[str]):
    CSS = "Menu{align:center middle} Menu>Vertical{width:76;height:24;padding:1 2;background:#181825;border:round #89b4fa} #mt{color:#f9e2af} ListView{background:#181825}"
    BINDINGS = [("escape", "close", "关闭")]
    def __init__(self, title, items): self._t = title; self._i = items; super().__init__()
    def compose(self): yield Vertical(Static(Text(self._t), id="mt"), ListView(*[ListItem(Label(Text(l)), id="mi%d" % n) for n, (c, l) in enumerate(self._i)]))
    def action_close(self): self.dismiss(None)
    def on_list_view_selected(self, m):
        self.dismiss(self._i[m.index][0])
