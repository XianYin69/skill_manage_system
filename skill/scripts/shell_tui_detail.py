#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（批6·用户「调用过程进 F9·输出区只放文字结果」＋批7·用户「模型思考过程和调用输出全放F9·输出区只放非思考非工具调用文本」）：行按 kind 分类——tool/edit/sh/step/task/reasoning（◌ 模型思考流）＝过程→全文压进 app.details（末 60 条·每条 ≤3000 字·连续思考并入同一条免刷屏）供右栏＋F9，主输出不显示；⧉技能▸ 子会话行剥前缀再分类：其工具/步骤/思考同样只进 F9、仅正文可见；顶层「⧉ 开子会话/收口」过程行、• notice/✗ err/纯正文→按原样处理。F9＝常规不透明 Screen 全屏（v3 弃 alpha 遮罩防真机合成崩屏·compose 全程 try/except 降级纯文本列表）。"""
import re, msg_flow
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from shell_tui_paint import paint
PREFIX = (("$ ", "tool"), ("▸ ", "step"), ("⧉", "skill"), ("! ", "sh"), ("≡", "task"), ("✎ ", "edit"), ("♪ ", "tts"), ("✗ ", "err"), ("• ", "notice"), ("◌ ", "reasoning"))
HIDE = {"tool", "edit", "sh", "step", "task", "reasoning"}
SUB = re.compile(r"^⧉[^\s▸]*▸\s*")
RML = re.compile(r"^(?:⧉[^\s▸]*▸\s*)?◌\s*")
def _kind(t):
    if (e := msg_flow.parse(t)): return e.get("kind")
    return next((k for p, k in PREFIX if t.startswith(p)), "llm_out")
def _push(app, t):
    d = getattr(app, "details", None)
    if d is None: d = app.details = []
    if (m := RML.match(t)) and d and RML.match(d[-1]) and len(d[-1]) < 3000: d[-1] = d[-1] + " " + t[m.end():]
    else: d.append(t[:3000])
    app.details = d[-60:]
def split(app, s):
    t = str(s); p = SUB.match(t); k = _kind(t[p.end():] if p else t)
    if k in HIDE or (not p and k == "skill"): _push(app, t); return None
    return paint(t)
class Details(Screen):
    CSS = "Details{background:#11111b} Details>VerticalScroll{width:100%;max-width:170;height:100%;background:#181825;border:heavy #89b4fa;padding:1 2} Details VerticalScroll>Static{width:100%;text-wrap:wrap}"
    BINDINGS = [("escape", "close", "关闭"), ("f9", "close", "关闭")]
    def _blocks(self):
        ds = list(getattr(self.app, "details", []))
        out = [Text("■ 详细细节·调用过程＋模型思考（最近 %d 条 · tool/skill/edit/sh/step/task/◌思考 · Esc/F9 关闭）" % len(ds), style="bold #f9e2af")]
        if not ds: out.append(Text("（暂无——调用过程与思考自动收进这里·主输出只留正文文字）"))
        for n, x in enumerate(ds, 1):
            out.append(Text("── %d/%d ──" % (n, len(ds)), style="bold #89b4fa")); out.append(Text(x or "（空）", overflow="fold"))
        return out
    def compose(self):
        try: blocks = self._blocks()
        except Exception as e:
            blocks = [Text("■ 详细细节（渲染降级：%s）" % (str(e)[:80], ), style="red"), Text("\n".join(str(x)[:200] for x in list(getattr(self.app, "details", []))[-8:]), overflow="fold")]
        yield VerticalScroll(*[Static(b) for b in blocks])
    def action_close(self): self.app.pop_screen()
