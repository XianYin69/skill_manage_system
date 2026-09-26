#!/usr/bin/env python3
"""shell_tui_detail.py — sms-shell TUI「详细细节」分流（2026-09-26 v3·F9 崩屏二次根治）：主输出只留简略——行若是 JSON 信封按 kind 分类（parse→msg_flow.CLASS），否则按 brief() 人读行前缀反推类型（$ tool·⧉ skill·✎ edit·! sh·• notice 属 detail，▸/≡ status、✗ alert、裸行 body 一律不折叠）；detail 且超长/多行→压成首行＋提示，全文收进 app.details（末 8 条·每条 ≤3000 字）供右栏与 F9 查看。F9 崩溃修复 v3（用户 2026-09-26 报障「F9 崩屏导致整个程序界面崩坏」）：批3 的 ModalScreen＋alpha 遮罩在真机部分终端合成仍崩且异常拖垮整壳——v3 弃模态遮罩，改常规不透明 Screen 全屏（零 alpha 合成路径·pop_screen 关闭）＋compose 全程 try/except 降级为纯文本列表，任何内容异常只坏详情面板不坏主界面（textual 8.2.8 无 Fullscreen 类，实测以 ImportError 静默吞为「未安装」——except 同步收紧）。每条独立 Static＋rich Text(overflow="fold")＋CSS text-wrap:wrap 纵向折行、VerticalScroll 滚动、条间序号分隔。"""
import msg_flow
from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import Screen
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
class Details(Screen):
    CSS = "Details{background:#11111b} Details>VerticalScroll{width:100%;max-width:170;height:100%;background:#181825;border:heavy #89b4fa;padding:1 2} Details VerticalScroll>Static{width:100%;text-wrap:wrap}"
    BINDINGS = [("escape", "close", "关闭"), ("f9", "close", "关闭")]
    def _blocks(self):
        ds = list(getattr(self.app, "details", []))
        out = [Text("■ 详细细节（最近 %d 条 · tool/skill/edit/sh/notice 长输出·正文不折叠 · Esc/F9 关闭）" % len(ds), style="bold #f9e2af")]
        if not ds: out.append(Text("（暂无——超长工具/技能输出会自动收进这里）"))
        for n, x in enumerate(ds, 1):
            out.append(Text("── %d/%d ──" % (n, len(ds)), style="bold #89b4fa")); out.append(Text(x or "（空）", overflow="fold"))
        return out
    def compose(self):
        try: blocks = self._blocks()
        except Exception as e:
            blocks = [Text("■ 详细细节（渲染降级：%s）" % (str(e)[:80], ), style="red"),
                      Text("\n".join(str(x)[:200] for x in list(getattr(self.app, "details", []))[-8:]), overflow="fold")]
        yield VerticalScroll(*[Static(b) for b in blocks])
    def action_close(self): self.app.pop_screen()
