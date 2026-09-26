#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（2026-09-26 v2·按 msg_flow 类型分类折叠）：主输出只留简略——行若是 JSON 信封按 kind 分类（parse→msg_flow.CLASS），否则按 brief() 人读行前缀反推类型（$ tool·⧉ skill·✎ edit·! sh·• notice 属 detail，▸/≡ status、✗ alert、裸行 body 一律不折叠）；detail 且超长/多行→压成首行＋提示，全文收进 app.details（末 8 条·每条 ≤3000 字）供右栏与 F9 查看。Details 显示异常修复（旧版单块 Static 长行横向裁切）：每条独立 Static＋rich Text(overflow="fold")＋CSS text-wrap:fold 纵向折行、VerticalScroll 滚动、遮罩层、条间序号分隔。"""
import msg_flow
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static
PREFIX = (("$ ", "tool"), ("▸ ", "step"), ("⧉", "skill"), ("! ", "sh"), ("≡", "task"), ("✎ ", "edit"), ("♪ ", "tts"), ("✗ ", "err"), ("• ", "notice"))
def _kind(t):
    if (e := msg_flow.parse(t)): return e.get("kind")
    return next((k for p, k in PREFIX if t.startswith(p)), "llm_out")
def shrink(app, s):
    t = str(s)
    if len(t) <= 240 and "\n" not in t[3:]: return t
    if not msg_flow.foldable(_kind(t)): return t
    d = getattr(app, "details", None)
    if d is None: d = app.details = []
    d.append(t[:3000]); app.details = d[-8:]
    head = (msg_flow.brief(e) if (e := msg_flow.parse(t)) else t).splitlines()[0]
    return head[:160] + " …〔详情→右栏·F9〕"
class Details(ModalScreen):
    CSS = "Details{align:center middle;overlay:#11111b 70%} Details>VerticalScroll{width:90%;max-width:160;height:86%;background:#181825;border:round #89b4fa;padding:1 2} Details VerticalScroll>Static{width:100%;text-wrap:fold}"
    BINDINGS = [("escape", "close", "关闭")]
    def compose(self):
        ds = list(getattr(self.app, "details", []))
        blocks = [Static(Text("■ 详细细节（最近 %d 条 · tool/skill/edit/sh/notice 长输出·正文不折叠）" % len(ds), style="bold #f9e2af"))]
        blocks += [Static(Text("（暂无——超长工具/技能输出会自动收进这里）"))] if not ds else [w for n, x in enumerate(ds, 1) for w in (Static(Text("── %d/%d ──" % (n, len(ds)), style="bold #89b4fa")), Static(Text(x or "（空）", overflow="fold")))]
        yield VerticalScroll(*blocks)
    def action_close(self): self.dismiss(None)
