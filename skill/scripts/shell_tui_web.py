#!/usr/bin/env python3
"""shell_tui_web.py — sms-shell TUI「网页壳」菜单 mixin（t3·新建以零增行接入：F1 主菜单 → 配置·权限·工具 → 网页壳）：状态与开关逻辑全在 web_banner.py（enabled/host/port 取真实配置 settings、运行状态取 net_util.running("web_shell")、token 只给掩码前缀），本 mixin 只做浮层与即时反馈——Enter「开/关」＝settings.set("web_shell.enabled", bool) 落盘，开启且未运行时按 net_util.spawn 后台拉起，关闭时提示可 :web stop；其余项直接提交 :web start|stop|status|token（明文 token 走既有审计，绝不写进链/日志）。红线：banner 与菜单均不打印完整明文 token；不破坏既有 SECT/ALI 与 MAIN 分组顺序（本项追加在「配置·权限·工具」组内）。"""
import web_banner as wb
from rich.text import Text
class Web:
    def action_menu_web(self):
        s = wb.status()
        self.menu("网页壳 web_shell（%s·%s·token %s·Enter 执行）" % (s["url"], s["run"], s["mask"]),
                  [("#web_toggle", ("✓ 已启用 → 关（写 web_shell.enabled=false·在跑的壳可 :web stop）" if s["enabled"] else "✗ 未启用 → 开（落盘＋未运行则后台拉起）")),
                   (":web start", "▶ 后台拉起（net_util spawn·日志 shell/web_shell.log）"),
                   (":web stop", "■ 停止（taskkill 进程树＋清 pid/port）"),
                   (":web status", "状态（URL/端口/证书指纹·JSON）"),
                   (":web token", "token 明文（走审计·勿贴入链/日志）"),
                   ("#menu_perms", "← 返回权限与工具")])
    def action_web_toggle(self):
        self.log_line(Text(wb.toggle(), style="bold cyan")); self.action_menu_web()
