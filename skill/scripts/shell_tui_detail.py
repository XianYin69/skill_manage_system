#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（用户 2026-09-26 需求：主输出只留简略，细节进右栏新分区）：shrink() 把工具/技能/步骤类超长或多行输出压成首行＋提示，全文收进 app.details（末 8 条·每条 ≤3000 字）供右栏渲染；Details＝F9 全屏查看（ModalScreen·Esc 关）。llm_out 正文不折叠（那是答案本体）。"""
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static
DETAIL_PREFIX = ("$ ", "▸ ", "⧉", "! ", "≡", "✎ ", "♪ ", "✗ ")
def shrink(app, s):
    t = str(s)
    if len(t) <= 240 and "\n" not in t[3:]: return t
    if not t.startswith(DETAIL_PREFIX): return t
    d = getattr(app, "details", None)
    if d is None: d = app.details = []
    d.append(t[:3000]); app.details = d[-8:]
    return (t.splitlines() or [""])[0][:160] + " …〔详情→右栏·F9〕"
class Details(ModalScreen):
    CSS = "Details{align:center middle} Details>VerticalScroll{width:92%;max-width:150;height:88%;background:#181825;border:round #89b4fa;padding:1 2}"
    BINDINGS = [("escape", "close", "关闭")]
    def compose(self):
        ds = list(getattr(self.app, "details", []))
        yield VerticalScroll(Static(Text(("■ 详细细节（最近 %d 条 · 工具/技能/步骤长输出）\n\n" % len(ds) + "\n———\n".join(ds)) if ds else "（暂无——超长工具/技能输出会自动收进这里）")))
    def action_close(self): self.dismiss(None)
