# smsystem-suit

SMS 系统套件伞仓（umbrella）。本仓不含实现代码，只承载套件清单与各成员仓指路；
原 `skill_manage_system` 单体仓内容已拆分至下列四个成员仓，本仓转为伞仓。

## 成员

| 成员 | 角色 | 本地路径 | 远端 |
|---|---|---|---|
| sms-core | 内核：数据流引擎 / 网关 / 十二链 / 权限 / SOLO | `Developin\SMS-core`（伞内链接 `sms-core/`） | https://github.com/XianYin69/sms-core |
| sms-shell | 命令行与图形壳（批36 PyQt6 GUI `shell_qt.py`） | `Developin\SMS-Shell`（伞内链接 `sms-shell/`） | https://github.com/XianYin69/sms-shell |
| smsc | 浏览器 / 控制台侧 | `Developin\smsc`（伞内链接 `smsc/`） | https://github.com/XianYin69/smsc |
| smsocket | 本地模型路由 socket | `Developin\smsocket`（伞内链接 `smsocket/`） | https://github.com/XianYin69/smsocket |

## 用法

机器可读清单见 [`suite.json`](suite.json)。成员目录在本仓工作树内以 Junction 挂载（链接名＝成员 id）：
`sms-core → ..\SMS-core`、`sms-shell → ..\SMS-Shell`、`smsc → ..\smsc`、`smsocket → ..\smsocket`；
建法 `New-Item -ItemType Junction -Name sms-core -Target ..\SMS-core`。`.gitignore` 已忽略这四个成员目录名，
成员内容不被伞仓跟踪（伞仓只跟踪 README.md / suite.json / .gitignore）。
GUI 起法：`sms-shell --qt` 或 `python -B bin/sms-shell.py --qt`（＝`sms-shell:skill/scripts/shell_qt.py`）。
技能入口：`<SMS_HOME>\skills\smsystem-suit → Developin\SMS-core`（伞目录不放 SKILL.md，避免同 id 双注册）。

## 历史

2026-10-09：`skill_manage_system` 单体内容清空并更名为 `smsystem-suit`；
`llm-router` 更名为 `smsocket`；`SMS-core` 的 origin 改接 `sms-core`；本地身份更名与伞目录挂载同日完成（旧名在进程回收/防误删处保留兼容匹配）。
