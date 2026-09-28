#!/usr/bin/env python3
"""shell_tui_paint.py — sms-shell 输出区着色渲染（批6·用户「代码高亮式区分 工具/skill/输出」）：把 on_line 文本按类型上色——⧉技能▸ 派发对话正文＝紫色技能徽章＋正文（路径暗青·`code` 橙）·〔技能:x〕/〔工具:x〕徽章着色·$ 命令行（工具）橙·✎ 编辑黄·✗ 错误红·▸ 步骤暗青（不进主输出·F9 收）·纯正文默认色＋路径/反引号/方括号高亮。与 shell_tui_detail.split 配合：split 决定该行进主输出还是 F9，paint 给进主输出的行上色。"""
import re
from rich.text import Text
PATH = re.compile(r"[A-Za-z]:[\\/][^\s，。！？；：]*|[\w\-\./\\]+\.(?:py|md|ps1|cmd|json|txt|html|csv|sh|js|ts)\b")
CODE = re.compile(r"`([^`\n]+)`")
SKPRE = re.compile(r"⧉([^\s▸]+)▸\s?(.*)", re.S)
TOOLN = re.compile(r"\b(exec|read|write|skill|ask|task|glob|grep|ls|webfetch|user_send|thinking_chain)\b")
def _seg(t, s, base="#cdd6f4"):
    ms = sorted(list(PATH.finditer(s)) + list(CODE.finditer(s)), key=lambda x: x.start()); pos = 0
    for m in ms:
        if m.start() < pos: continue
        t.append(s[pos:m.start()], base)
        if m.group(0).startswith("`"): t.append(m.group(1), "bold #fab387")
        else: t.append(m.group(0), "#89dceb")
        pos = m.end()
    t.append(s[pos:], base)
def paint(s):
    s = str(s)
    if s.startswith("⧉") and "▸" in s:
        m = SKPRE.match(s)
        if m:
            t = Text(); t.append("⧉" + m.group(1), "bold #cba6f7"); t.append("▸ ", "dim #cba6f7"); _seg(t, m.group(2)); return t
    if s.startswith("$ "):
        t = Text(); t.append("$ ", "bold #fab387"); _seg(t, s[2:], "#f9e2af"); return t
    if s.startswith("✗ "): return Text(s, style="bold red")
    if s.startswith("✎ "): return Text(s, style="yellow")
    if s.startswith("• "):
        t = Text(); t.append("• ", "bold green"); _seg(t, s[2:]); return t
    t = Text(); _seg(t, s); return t
