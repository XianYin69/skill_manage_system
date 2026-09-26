#!/usr/bin/env python3
"""shell_tui_side.py — sms-shell TUI 右半侧栏（左右分屏各 1/2·0.5s 自刷新·重数据 5s 节流）：当前工作区（SMS_WORKSPACE·真实目录或虚拟〔每对话开建口删〕＋登记数·F6 可切换）·数据根 SMS_HOME·技能源·启动 cwd 路径·本次对话修改的文件（从网关 $ exec 回显抽取脚本/文件路径＋图形化配置改动·去重末 7）·所在链与会话（解析「开新对话」id·本对话写入链，技能命中含 skill_call）·当前步骤类型＋简略说明（关键词映射）·会话总览（shell_tui_sessions.overview：最近对话＝创建时间＋首条话语简略）。样式由主文件 CSS 控制。"""
import os, re, time
from rich.text import Text
from textual.widgets import Static
import shell_core as core, shell_tui_sessions, workspace
FILE = re.compile(r"(?:[\w\-\.:~][\w\-\./\\:~]{2,}\.(?:py|md|ps1|cmd|json|txt|html|csv|sh|js|ts))")
TYPE = [("确定性路由", "零模型·内置词直达"), ("元指令", "`:` 治理指令·转调 SMS 脚本"), ("内置词", "帮助/配置/命令表·零模型"), ("个性化指令", "user_commands 步骤展开"), ("SMS 壳自管理", "壳自身信息直答"), ("检测执行器", "选定网关/CLI 后端"), ("开新对话", "红线17·每输入一对话"), ("技能路由", "registry 匹配·记 skill_call"), ("压缩记忆", "prompt_pack＋治理指令组装"), ("网关流式执行", "大模型流式输出中"), ("agent CLI 执行", "外部 CLI 输出中"), ("对话收口", "链记录完成"), ("话语", "转入数据流引擎")]
def _files(app):
    out = []
    for s in getattr(app, "touched", []):
        if s.startswith("config:"): out.append("config.json ← " + s[7:]); continue
        out += FILE.findall(s)
    return out
class Side(Static):
    def on_mount(self): self._ov = []; self._nw = 0; self._ot = 0.0; self.set_interval(0.5, self._tick)
    def _heavy(self, force=False):
        if force or time.time() - self._ot > 5: self._ot = time.time(); self._ov = shell_tui_sessions.overview(); self._nw = len(workspace.list_ws())
    def _tick(self):
        self._heavy()
        a = self.app; steps = list(getattr(a, "steps", [])); cur = steps[-1] if steps else "就绪"
        conv = next((x.split("：", 1)[1] for x in reversed(steps) if "开新对话" in x), "—")
        chains = "session·dialogue·time" + ("·skill_call" if any("命中" in x for x in steps) else "")
        tag = next((v for k, v in TYPE if k in cur), "等待提交话语（回车/F1 菜单/Ctrl+K 技能）")
        files = _files(a)
        t = Text(no_wrap=False, overflow="fold")
        cw = workspace.current()
        t.append("■ 当前工作区 SMS_WORKSPACE\n", "bold yellow")
        t.append(cw + ("〔虚拟·对话收口即删〕" if workspace.is_virtual(cw) else "（F6 切换）") + "　登记 " + str(self._nw) + " 个\n", "#a6e3a1")
        t.append("数据根 SMS_HOME " + core.SMS + "\n", "dim")
        t.append("技能源 " + os.path.dirname(core.__file__) + "\n启动 cwd " + os.getcwd() + "\n\n", "dim")
        t.append("■ 本次修改的文件\n", "bold yellow")
        t.append(("\n".join(list(dict.fromkeys(files))[-7:]) + "\n") if files else "（无写文件记录）\n")
        t.append("\n■ 所在链与会话\n", "bold yellow")
        t.append(conv + "\n" + chains + "\n\n", "#89b4fa")
        t.append("■ 当前步骤·类型\n", "bold yellow")
        t.append(cur + "\n", "bold cyan"); t.append(tag, "italic #cdd6f4")
        t.append("\n\n■ 会话总览（创建时间＋简略）\n", "bold yellow")
        t.append(("\n".join("%s｜%s｜%s" % r for r in self._ov) + "\n") if self._ov else "（暂无会话）\n", "dim")
        self.update(t)
