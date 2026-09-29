#!/usr/bin/env python3
"""shell_help.py — sms-shell 帮助单一真源（shell_core/TUI 由此导出；ps1 原生壳 Show-MetaHelp 同口径）：HELP＝速查短表（全量明细＝:cmds，不再整屏铺细节）；SHORT＝一行指路（自管理/近帮助话语时的最小提示）。改壳行为必同步此文件与 bin/sms_dos.ps1。"""
HELP = ("sms-shell 速查（全量命令表＝:cmds · 本帮助不展开细节）\n"
         "话语＝直接交数据流（批16 LLM 主导）：纯问答/闲聊大模型直答不再强制派子技能；执行类诉求由模型自主经 skill 工具派发对等对话真执行（批23：每次派发＝独立 conv 独立链·对话无主次·互任监视者/指导者/训诫者·输出停止只是形式停止非实质完成）（路由打分行仅供参考）·复杂任务自动经 task_table 建种子表·脚本判简单时仍注入〔任务表·脚本未建〕由模型裁量（批22·task_plan new/plan 自建表·勿为表而表）·派发对话收口返回调度方按表续推·!命令＝系统 shell（ls/grep 等 unix 命令自动走 bash）· 裸词 help/配置/cmds 零模型直达（批22 收窄＝仅整行显式命令）\n"
         "session 与 conv 分开（批23）：新建会话＝:session new（session＝多对话容器·防跨会话污染）；conv＝每次用户输入/每次技能派发自开的独立对话；:session overview 看先后顺序与他会话未完成、:session conflicts 看同技能跨会话冲突；多壳并行 env SMS_SESSION 各绑其 session\n"
        "顶栏进度条与剩余时间＝按任务表完成度＋各技能/模型实测反应时间预测（latency 均值·:task eta <表id> 手查）\n"
        "任务进行中仍可输入：普通话语自动排队·完成即依序发送；大模型弹「❓提问」时下一条输入即答复（ask_user 应答通道·超时按假设继续）；输 stop/停止/:stop（中英词表·仅任务中当指令）＝请求停止当前任务——流式吐字/工具轮/子进程输出行下一检查点收口·会话照常归档，readline 兜底壳用 Ctrl+C 中断〔stop_channel.py〕\n"
        "新启动自动接续上次关闭前的对话（末轮上下文注入＋界面回显 · :resume on|off）；网关瞬时错误自动重试（llm_gateway.retries）·异常/中断轮仍记接续与任务表，未完成步骤下轮续跑\n"
        "键位：F1 分组主菜单（五组·进组「← 返回上一级」） F2 技能索引（➕按路径加入 skill） F3 帮助 F4 图形化配置（按段分组·组内返回上一级） F5 文件索引 F6 工作区 F7 界面模式（查看/对话/直通·Esc 回） F8 编辑器（Ctrl+S 存） F9 详情（折行查看） · Ctrl+K 技能 Shift+Tab agent Ctrl+L 清屏 Ctrl+Q 退出 Tab 补全 ↑↓ 历史 · F1 系统组＝重启SMS/关闭SMS/修复待批\n"
         "元指令：:agents :use <名> :skill on|off :image <文件> :dispatch <技能id> <诉求> :sh [list|<命令>] :task [new|show|status|add|remove|skill|eta] 任务表手改（new＝模型判复杂自建） :manual [kind|all] 三平台命令手册 :edit/:view <路径> :mode :session [new|list|use|current|overview|conflicts]（新建会话＝新 session·批23） :resume :workspace :index :skills :cmds :intent :alias/:unalias\n"
        "治理：:config status|show|get|set <dot.path> <json> · 推理等级 :config set llm_gateway.reasoning_effort \"high\"（low|medium|high·F4 同处）· :perms 权限总览 :grant <键|角色> [分钟] :tools 工具权限 :hud start|session|step|alert|hide|stop :dream status|run :debug on|off|tail :detail [n] 过程行·思考查看 :tts on|off|test :net :learn :file :path :api :web :ext :deploy <dir> :quit\n"
        "配置＝<SMS_HOME>/config/config.json（api_key 恒掩码·F4 图形化·做梦间隔用户设置 dream.interval_min·触发时间戳按间隔计算·task.auto_table 自动建表开关）· 思考◌/工具$/技能⧉/步骤▸等过程行不入主输出——Textual 收右栏「详细细节」＋F9 全文，readline/单发/GUI 存 <SMS_HOME>/shell/detail.json（:detail 可读）· 网关流式逐段吐字（llm_gateway.stream）")
SHORT = "sms-shell：话语即数据流 · !命令＝系统 shell · F1 菜单/F4 配置/F7 模式/F8 编辑 · 速查 :help · 全表 :cmds"
