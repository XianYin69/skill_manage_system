# scripts（脚本库）

本目录存放 SMS 的可执行脚本：路径解析、写盘门控、注册、打包、连接、会话、任务、进程、权限、并发调度。

## 应存什么

- 独立运行的 Python 脚本；文件名小写、中横线分隔；每个 ≤ 50 行。
- 数据写盘统一经 emit.py 门控：默认预览；`--write` 且会话已授予 write 才落盘。

## 当前内容

- [`resolve_home.py`](resolve_home.py)：解析 SMS 固定路径（env SMS_HOME → 缓存目录 → 根目录）。
- [`emit.py`](emit.py)：统一写盘门控（默认预览；已授予 write 才落盘）。
- [`register.py`](register.py)：扫描技能安装位置与所用工具 → register.json。
- [`pack.py`](pack.py)：描述技能用途与接口 → interfaces.json。
- [`connect.py`](connect.py)：生成技能间上下文连接 → connections.json。
- [`session.py`](session.py)：建立 `sessions/<日期>/` 五元组。
- [`task.py`](task.py)：任务拆分·理解·整合 → task.json。
- [`process.py`](process.py)：进程式注册生命周期 spawn/run/suspend/resume/kill → processes.json。
- [`permissions.py`](permissions.py)：权限 grant/deny/check/audit → permissions.json。
- [`scheduler.py`](scheduler.py)：五 lane 并发调度 → scheduler.json。
- [`init_registry.py`](init_registry.py)：初始设置一次性跑通 register → pack → connect。

## 数据契约

见 [`../schemas/`](../schemas/register.schema.json)：register / interfaces / connections / session / task / process / scheduler。

## 运行约定

1. 使用项目默认 Python。
2. 数据写盘统一经 emit.py：默认预览；`--write` 且已授予 write 才落盘。
3. 先 `session.py --write` 建会话，再 `permissions.py grant write --write` 授权，之后写盘才生效。
4. 运行前先看 [`../resistance/resistance.md`](../resistance/resistance.md) 确认权限。