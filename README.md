# smsystem-suit

SMS 系统套件伞仓（umbrella）。本仓不含实现代码，只承载套件清单与各成员仓指路；
原 `skill_manage_system` 单体仓内容已拆分至下列四个成员仓，本仓转为伞仓。

## 成员

| 成员 | 角色 | 本地路径 | 远端 |
|---|---|---|---|
| sms-core | 内核：数据流引擎 / 网关 / 十二链 / 权限 / SOLO | `C:\UserSpace\EthanYan\Developin\SMS-core` | https://github.com/XianYin69/sms-core |
| sms-shell | 命令行与图形壳（批36 PyQt6 GUI `shell_qt.py`，起法 `sms-shell --qt`） | `C:\UserSpace\EthanYan\Developin\SMS-Shell` | https://github.com/XianYin69/sms-shell |
| smsc | 浏览器 / 控制台侧 | `C:\UserSpace\EthanYan\Developin\smsc` | https://github.com/XianYin69/smsc |
| smsocket | 本地模型路由 socket | `C:\UserSpace\EthanYan\Developin\smsocket` | https://github.com/XianYin69/smsocket |

## 用法

机器可读清单见 [`suite.json`](suite.json)。成员目录可在本仓工作树内以 junction 挂载
（由其它会话负责创建），`.gitignore` 已忽略这四个成员目录名，避免成员内容被伞仓跟踪。

## 历史

2026-10-09：`skill_manage_system` 单体内容清空并更名为 `smsystem-suit`；
`llm-router` 更名为 `smsocket`；`SMS-core` 的 origin 改接 `sms-core`。
