#!/usr/bin/env python3
"""shell_tui_widgets.py — sms-shell Textual TUI 组件（配 shell_tui_textual）：Input（回车/ctrl+enter 提交·Tab 补全·Shift+Tab agent 菜单·「/」空行时打开 SKILL.md 技能索引（F5 为文件索引）·上下历史）、StatusBar（步进器＋每步名称轮询＋本对话用时计时，RichLog 之外的实时状态行）、TopBar（顶栏：左＝壳身份·数据流·界面模式徽标（对话/直通/查看）·中＝task_detail 任务进度优先，否则当前步骤滚动简述·右＝用户地区实时日期＋星期＋实时时间 HH:MM:SS（本机时区），0.5s 自刷新永不静止）；快捷菜单浮层（F1/Ctrl+K·分组嵌套·返回上一级）见 shell_tui_menu。"""
import time, debug, shell_mode, dream_watch, dream_pending, qq_watch
from rich.text import Text
from textual.widgets import Static, TextArea, Button
from textual.containers import Horizontal
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
        b = " · ".join(x for x in (dream_watch.badge(), dream_pending.badge(), qq_watch.badge()) if x)
        left = (getattr(a, "title", "") or "sms-shell") + ("·DEB" if debug.enabled() else "") + "·" + shell_mode.badge() + ((" " + b) if b else "") + " ▸ " + (getattr(a, "sub_title", "") or "")
        right = time.strftime("%Y-%m-%d") + " 周" + "一二三四五六日"[time.localtime().tm_wday] + time.strftime(" %H:%M:%S"); mid = max((self.size.width or 80) - len(left) - len(right) - 6, 8)
        if len(cur) <= mid: core = cur
        else:
            pad = cur + " · "; self.off = (self.off + 1) % len(pad); core = (pad * (mid // len(pad) + 2))[self.off:self.off + mid]
        self.update(Text("%s │ %s │ %s" % (left, core.ljust(mid), right), style="bold #89b4fa"))

class TaskBar(Horizontal):
    """底栏「停止 / 继续」按钮条（2026-09-29 用户诉求）：仅当存在未完成计划表（仍有 pending/running 行＝尚未生成最终输出）时显示；按下转交 ShellApp.action_stop_task / action_continue_task，功能与名字一致；2026-09-30 迭代＝按钮 tooltip＋#taskhint 常驻说明。"""
    def compose(self):
        yield Button("⏸ 停止", id="btn_stop", variant="warning", tooltip="⏸ 停止（F11）：置停止旗标，在途输出于下一个检查点收口；计划表未完成行保留，可按「▶ 继续」续推")
        yield Button("▶ 继续", id="btn_go", variant="success", tooltip="▶ 继续（F12）：清除停止旗标，把最后一张未完成计划表交回数据流续推")
        yield Static("⏸停止＝在途输出下一检查点收口·未完成行保留(F11) ｜ ▶继续＝清旗标续推最后一张未完成表(F12) ｜ 悬停按钮看说明", id="taskhint")
    def on_button_pressed(self, event):
        (self.app.action_stop_task if event.button.id == "btn_stop" else self.app.action_continue_task)()
