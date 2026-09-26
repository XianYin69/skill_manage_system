#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（批6·用户「调用过程进 F9·输出区只放文字结果」）：主输出只留文字结果——行按 kind 分类：tool/edit/sh/skill过程/step/task进度＝调用过程→全文压进 app.details（末 60 条·每条 ≤3000 字）供右栏＋F9，主输出不显示；⧉技能▸ 子会话正文/• notice/✗ err/纯正文→主输出（shell_tui_paint 上色区分）。F9＝常规不透明 Screen 全屏（v3 弃 alpha 遮罩防真机合成崩屏·compose 全程 try/except 降级纯文本列表）。"""
import msg_flow
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from shell_tui_paint import paint
PREFIX = (("$ ", "tool"), ("▸ ", "step"), ("⧉", "skill"), ("! ", "sh"), ("≡", "task"), ("✎ ", "edit"), ("♪ ", "tts"), ("✗ ", "err"), ("• ", "notice"))
HIDE = {"tool", "edit", "sh", "step", "task"}
def _kind(t):
    if (e := msg_flow.parse(t)): return e.get("kind")
    return next((k for p, k in PREFIX if t.startswith(p)), "llm_out")
def _push(app, t):
    d = getattr(app, "details", None)
    if d is None: d = app.details = []
    d.append(t[:3000]); app.details = d[-60:]
def split(app, s):
    t = str(s); k = _kind(t)
    if k in HIDE or (k == "skill" and "▸" not in t): _push(app, t); return None
    return paint(t)
class Details(Screen):
    CSS = "Details{background:#11111b} Details>VerticalScroll{width:100%;max-width:170;height:100%;background:#181825;border:heavy #89b4fa;padding:1 2} Details VerticalScroll>Static{width:100%;text-wrap:wrap}"
    BINDINGS = [("escape", "close", "关闭"), ("f9", "close", "关闭")]
    def _blocks(self):
        ds = list(getattr(self.app, "details", []))
        out = [Text("■ 详细细节·调用过程（最近 %d 条 · tool/skill/edit/sh/step/task · Esc/F9 关闭）" % len(ds), style="bold #f9e2af")]
        if not ds: out.append(Text("（暂无——调用过程自动收进这里·主输出只留文字结果）"))
        for n, x in enumerate(ds, 1):
            out.append(Text("── %d/%d ──" % (n, len(ds)), style="bold #89b4fa")); out.append(Text(x or "（空）", overflow="fold"))
        return out
    def compose(self):
        try: blocks = self._blocks()
        except Exception as e:
            blocks = [Text("■ 详细细节（渲染降级：%s）" % (str(e)[:80], ), style="red"), Text("\n".join(str(x)[:200] for x in list(getattr(self.app, "details", []))[-8:]), overflow="fold")]
        yield VerticalScroll(*[Static(b) for b in blocks])
    def action_close(self): self.app.pop_screen()
