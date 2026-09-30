#!/usr/bin/env python3
"""shell_tui_menu.py — sms-shell TUI 通用菜单浮层（ModalScreen·自 shell_tui_widgets 拆出保 ≤50 行）：items 元素＝(cmd,label)——cmd 为 str＝叶子（Enter→dismiss(cmd) 回 app.pick 派发）；cmd 为 list＝子分组（行首自动加 ▸ 与项数·Enter 进入下一级·标题尾拼「 ▸ 分组名」面包屑）；进入子级后行首自动追加「← 返回上一级」（cmd None·Enter 回退一层不关窗·Esc 仍整体关闭）。Path＝路径输入浮层（「按路径加入 skill」用·Enter 提交原文 dismiss）。MAIN＝F1 主菜单分组表（技能与派发／文件·索引·工作区／配置·权限·工具／会话与数据流／系统／QQ 推送（六组·QQ 自系统组摘出独立成组）·供 shell_tui_menus 引用·命令串与旧平铺一致）。"""
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static
class Menu(ModalScreen[str]):
    CSS = "Menu{align:center middle} Menu>Vertical{width:80;height:24;padding:1 2;background:#181825;border:round #89b4fa} #mt{color:#f9e2af} ListView{background:#181825}"
    BINDINGS = [("escape", "close", "关闭")]
    def __init__(self, title, items): self._t = title; self._lv = [(title, list(items))]; self._i = []; super().__init__()
    def compose(self): yield Vertical(Static(id="mt"), ListView(id="ml"))
    def on_mount(self): self.fill()
    def fill(self):
        self._i = ([(None, "← 返回上一级")] if len(self._lv) > 1 else []) + self._lv[-1][1]
        self._t = " ▸ ".join(t for t, _ in self._lv); self.query_one("#mt", Static).update(Text(self._t))
        lv = self.query_one("#ml", ListView); lv.clear()
        lv.extend(ListItem(Label(Text("▸ %s（%d 项）" % (l, len(c)) if isinstance(c, list) else l))) for n, (c, l) in enumerate(self._i)); lv.index = 0
    def action_close(self): self.dismiss(None)
    def on_list_view_selected(self, m):
        c, l = self._i[m.index]
        if c is None: self._lv.pop(); self.fill()
        elif isinstance(c, list): self._lv.append((l, c)); self.fill()
        else: self.dismiss(c)
class Path(ModalScreen[str]):
    CSS = "Path{align:center middle} Path>Vertical{width:92%;max-width:104;padding:1 2;background:#181825;border:round #89b4fa} #pt{color:#f9e2af}"
    BINDINGS = [("escape", "cx", "取消")]
    def __init__(self, ask): self.a = ask; super().__init__()
    def compose(self): yield Vertical(Static(Text(self.a), id="pt"), Input(placeholder="输入路径 · Enter 提交 · Esc 取消", id="pi"))
    def on_mount(self): self.query_one("#pi", Input).focus()
    def on_input_submitted(self, m): self.dismiss(m.value)
    def action_cx(self): self.dismiss(None)
MAIN = [
    ([("#menu_skill", "托管技能：列表＋按路径加入（Ctrl+K）"), ("#menu_skill_index", "SKILL.md 技能索引：名称＋介绍·插 /技能名（F2）"), (":dispatch ", "技能真派发 <技能id> <诉求>"), ("path:skill", "➕ 按路径加入 skill：输入目录→登记扫描根＋重建注册表")], "技能与派发"),
    ([("#copy_log", "⧉ 复制全部输出（Ctrl+Shift+C·所选片段用 Ctrl+C）"), ("#stop_task", "⏸ 停止当前任务（有计划表未出最终输出时底栏按钮）"), ("#continue_task", "▶ 继续未完成计划表"), (":plan ls", "计划任务清单（到点自动执行·:plan add 登记）"), ("#menu_files", "文件索引：用户索引项·插 /名称·＋索引文件/文件夹（F5）"), ("#menu_ws", "工作区切换：切换/添加/更改路径·即时生效（F6）"), ("#editor", "编辑器/查看器（F8）：选文件·Ctrl+S 存"), ("#detail_win", "详细细节（长输出·F9）")], "文件·索引·工作区"),
    ([("#config", "图形化配置：分组·返回上一级·过滤·空格/Enter 改值·T/F 选择器（F4）"), ("#menu_perms", "权限与工具：系统权限总览＋大模型工具开关＋HUD（F10）"), (":grant ", "权限授予 <键|角色>"), (":config status", "配置状态（文本）"), (":perms", "权限总览（文本）"), ("#menu_remote", "远程会话权限授予（按 id 分配）")], "配置·权限·工具"),
    ([(":agents", "查看/选择数据流 agent"), ("#menu_mode", "界面模式：查看（只读）/对话（默认）/直通（＝系统 shell·!同义）（F7）"), (":session new ", "新建会话＝新建 session（多对话容器·批23·conv 每输入自动开）"), (":session list", "session 清单"), (":session overview", "会话拓扑：先后顺序＋跨会话未完成（对等监视）"), (":session conflicts", "仅看冲突：他会话未完成/同技能并行")], "会话与数据流"),
    ([(":sh list", "系统 shell 联动（powershell/bash/zsh·!命令）"), (":cmds", "命令总表"), (":deploy ", "部署＝仅复制 bin 到目录"), (":api formats", "格式 API"), (":dream run", "做梦整理链（后台真执行）"), (":dream status", "做梦状态：后台是否真在跑"), (":repair list", "修复待批：做梦受阻转前台"), (":tts status", "TTS 朗读状态"), (":restart", "重启SMS：拉起新实例并收口本壳"), (":shutdown", "关闭SMS：收后台进程并退出"), (":help", "速查（全量 :cmds）")], "系统"),
    ([(":qq status", "QQ 推送：状态/凭据/今日已推/outbox 积压"), (":qq bind", "QQ 推送：扫码绑定（task 约2分钟过期·自动3轮换码·弱网退避）"), (":qq resume", "QQ 推送：续绑上次扫码（免重扫·页面卡「连接中」时用）"), (":qq check", "QQ 推送：链路自检（取 token 不发消息·不占配额·报耗时）"), (":qq test", "QQ 推送：真发一条测试（验链路）"), (":qq on", "QQ 推送：开关＝开"), (":qq off", "QQ 推送：开关＝关"), (":qq conf max_day=200", "QQ 推送：改阈值 max_day/min_gap/max_len/dedup"), (":qq flush", "QQ 推送：补发 outbox 积压"), (":qq open", "QQ 推送：开放平台机器人列表（浏览器打开 q.qq.com/qqbot/openclaw/index.html）"), (":qq open create", "QQ 推送：快捷创建/登录（浏览器打开 q.qq.com/qqbot/openclaw/login.html）"), ("fill::qq --appid  --secret  --openid ", "QQ 推送：手工录入凭据（填入输入行·补值后回车）"), (":qq listen", "QQ 入站：启动常驻监听（灵魂接上·收你发来的消息）"), (":qq unlisten", "QQ 入站：停止监听"), (":qq lstatus", "QQ 入站：监听判活（真 pid＋心跳·僵尸告警）"), (":qq linbox", "QQ 入站：最近入站消息审计（含陌生人拒绝记录）")], "QQ 推送"),
]
