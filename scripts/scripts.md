# scripts（脚本库）

本目录存放 SMS 的可执行脚本：路径解析、注册、打包、连接、会话、初始设置。

## 应存什么

- 独立运行的 Python 脚本；文件名小写、中横线分隔；每个 ≤ 50 行。
- 写盘脚本必须带 `--dry-run` 默认模式（register / pack / connect / session / init_registry）。

## 当前内容

- [`resolve_home.py`](resolve_home.py)：解析 SMS 固定路径（env SMS_HOME → 缓存目录 → 根目录）。
- [`register.py`](register.py)：扫描技能安装位置与所用工具 → register.json。
- [`pack.py`](pack.py)：描述技能用途与接口 → interfaces.json。
- [`connect.py`](connect.py)：生成技能间上下文连接 → connections.json。
- [`session.py`](session.py)：建立 `sessions/<日期>/` 五元组。
- [`init_registry.py`](init_registry.py)：初始设置一次性跑通 register → pack → connect。

## 数据契约

见 [`../schemas/`](../schemas/register.schema.json)：register / interfaces / connections / session。

## 运行约定

1. 使用项目默认 Python。
2. 任何写盘脚本默认 `--dry-run`；确认后去除该旗标再执行。
3. 运行前先看 [`../resistance/resistance.md`](../resistance/resistance.md) 确认权限。