#!/usr/bin/env python3
"""shell_tui_side.py — sms-shell TUI 右半侧栏（左右分屏各 1/2·0.5s 自刷新）：当前工作区/技能源·启动 cwd 路径·本次对话修改的文件（从网关 $ exec 回显抽取脚本/文件路径＋图形化配置改动·去重末 7）·所在链与会话（解析「开新对话」id·本对话写入链，技能命中含 skill_call）·当前步骤类型＋简略说明（关键词映射）。样式由主文件 CSS 控制。"""
import os, re
from rich.text import Text
from textual.widgets import Static
import shell_core as core
FILE = re.compile(r"(?:[\w\-\.:~][\w\-\./\\:~]{2,}\.(?:py|md|ps1|cmd|json|txt|html|csv|sh|js|ts))")
TYPE = [("确定性路由", "零模型·内置词直达"), ("元指令", "`:` 治理指令·转调 SMS 脚本"), ("内置词", "帮助/配置/命令表·零模型"), ("个性化指令", "user_commands 步骤展开"), ("SMS 壳自管理", "壳自身信息直答"), ("检测执行器", "选定网关/CLI 后端"), ("开新对话", "红线17·每输入一对话"), ("技能路由", "registry 匹配·记 skill_call"), ("压缩记忆", "prompt_pack＋治理指令组装"), ("网关流式执行", "大模型流式输出中"), ("agent CLI 执行", "外部 CLI 输出中"), ("对话收口", "链记录完成"), ("话语", "转入数据流引擎")]
def _files(app):
    out = []
    for s in getattr(app, "touched", []):
        if s.startswith("config:"): out.append("config.json ← " + s[7:]); continue
        out += FILE.findall(s)
    return out
class Side(Static):
    def on_mount(self): self.set_interval(0.5, self._tick)
    def _tick(self):
        a = self.app; steps = list(getattr(a, "steps", [])); cur = steps[-1] if steps else "就绪"
        conv = next((x.split("：", 1)[1] for x in reversed(steps) if "开新对话" in x), "—")
        chains = "session·dialogue·time" + ("·skill_call" if any("命中" in x for x in steps) else "")
        tag = next((v for k, v in TYPE if k in cur), "等待提交话语（回车/F1 菜单/Ctrl+K 技能）")
        files = _files(a)
        t = Text(no_wrap=False, overflow="fold")
        t.append("■ 当前工作区\n", "bold yellow")
        t.append(core.SMS + "\n", "#a6e3a1")
        t.append("技能源 " + os.path.dirname(core.__file__) + "\n启动 cwd " + os.getcwd() + "\n\n", "dim")
        t.append("■ 本次修改的文件\n", "bold yellow")
        t.append(("\n".join(list(dict.fromkeys(files))[-7:]) + "\n") if files else "（无写文件记录）\n")
        t.append("\n■ 所在链与会话\n", "bold yellow")
        t.append(conv + "\n" + chains + "\n\n", "#89b4fa")
        t.append("■ 当前步骤·类型\n", "bold yellow")
        t.append(cur + "\n", "bold cyan"); t.append(tag, "italic #cdd6f4")
        self.update(t)
