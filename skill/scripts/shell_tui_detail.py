#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（批6·用户「调用过程进 F9·输出区只放文字结果」＋批7·用户「模型思考过程和调用输出全放F9·输出区只放非思考非工具调用文本」）：msg_flow.visible 共享判定（与 readline/单发/GUI 门控同口径）——tool/edit/sh/step/task/reasoning（◌ 模型思考流）与「⧉ 开派发对话/收口」过程行→全文压进 app.details（末 60 条·每条 ≤3000 字·连续思考并入同一条免刷屏）供右栏＋F9，主输出不显示；批27（用户「其他会话任务的详细信息（推导·工具使用·命令行输出）也应该写在主 shell 的详细细节里」）＝app.details 由本会话 split ＋ detail_bus 跨会话增量合并（shell_tui_flow.bus_poll），来源以〔sess·kind〕前缀标注、条数上限 60→150；⧉技能▸ 派发对话行剥前缀再分类：其工具/步骤/思考同样只进 F9、仅正文可见。F9＝常规不透明 Screen 全屏（v3 弃 alpha 遮罩防真机合成崩屏·compose 全程 try/except 降级纯文本列表）。"""
import re, msg_flow
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from shell_tui_paint import paint
RML = re.compile(r"^(?:⧉[^\s▸]*▸\s*)*◌\s*")
def _push(app, t):
    d = getattr(app, "details", None)
    if d is None: d = app.details = []
    if (m := RML.match(t)) and d and RML.match(d[-1]) and len(d[-1]) < 3000 and "〔" not in d[-1][:16]: d[-1] = d[-1] + " " + t[m.end():]
    else: d.append(t[:3000])
    app.details = d[-int(getattr(app, "detail_cap", 150)):]
def split(app, s, tag=""):
    t = str(s)
    if not msg_flow.visible(t): (not msg_flow.blank(t)) and _push(app, (tag or "") + t); return None
    p = paint(t); return (Text(tag, style="dim cyan") + p) if tag and p is not None else p
class Details(Screen):
    CSS = "Details{background:#11111b} Details>VerticalScroll{width:100%;max-width:170;height:100%;background:#181825;border:heavy #89b4fa;padding:1 2} Details VerticalScroll>Static{width:100%;text-wrap:wrap}"
    BINDINGS = [("escape", "close", "关闭"), ("f9", "close", "关闭")]
    def _blocks(self):
        ds = list(getattr(self.app, "details", []))
        no = sum(1 for x in ds if x.startswith("〔"))
        out = [Text("■ 详细细节·调用过程＋模型思考（最近 %d 条 · tool/skill/edit/sh/step/task/◌思考 · 含其他会话 %d 条〔sess·kind〕· Esc/F9 关闭）" % (len(ds), no), style="bold #f9e2af")]
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
