#!/usr/bin/env python3
"""agent_dispatch.py — agent 工具 schema 与派发（gateway 工具循环与 CLI 共用·单一真源）：SCHEMA＝OpenAI function 清单 exec·read·write·skill·ask·task·task_detail·user_send·thinking_chain·glob·grep·ls·webfetch（read 一族与联网取文 2026-09-26 集成，实现见 agent_tools2.py）；execute(name, raw_args)→agent_tools/agent_task 对应实现，参数按形参名过滤、异常回错误文本给模型（不中断工具循环）。工具权限——settings agent_tools.<name>（默认 true）门控：tools_schema() 供 gateway 只暴露启用工具、execute() 拒调禁用工具，菜单 F1→大模型工具权限 或 `:tools`/`:config set agent_tools.read false` 增删。用法：python -B agent_dispatch.py call <工具> '<json>' | skill <id> <诉求> | task <诉求> | detail [task-id] | tools [enable|disable <name>]"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import agent_tools as at, agent_tools2 as a2, agent_task as atk, task_table as tt, settings
P = lambda t, d: {"type": t, "description": d}; F = lambda n, d, p, r: {"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": r}}}
SCHEMA = [F("exec", "执行 shell 命令（cwd＝工作区·生成文件入 tmp）", {"cmd": P("string", "命令")}, ["cmd"]),
 F("read", "读文本文件", {"path": P("string", "路径"), "max_lines": P("integer", "最多行数")}, ["path"]),
 F("write", "写文本文件（工作区/SMS 默认可写，越界需授权）", {"path": P("string", "路径"), "content": P("string", "内容"), "append": P("boolean", "是否追加")}, ["path", "content"]),
 F("skill", "把诉求派发给托管技能在其子会话按其 SKILL.md 全文执行（命中技能必须用它，禁止自行代答）", {"name": P("string", "技能id"), "input": P("string", "用户诉求")}, ["name", "input"]),
 F("ask", "子问答：需要独立小答案时用（≤300字·不面向用户复述）", {"question": P("string", "问题")}, ["question"]),
 F("task", "把复合诉求拆分为子任务并行执行并整合（进度实时上顶栏）", {"intent": P("string", "诉求")}, ["intent"]),
 F("task_detail", "查询任务进度（id 空＝最近清单）", {"id": P("string", "任务id")}, []),
 F("task_plan", "任务表制表器 task_table 的改表口：按〔任务表〕行推进——status 置行 done/running、add 补漏步（自动路由技能）、remove 删不合理行、skill 改指定技能、show/next/eta 查询；每次改表顶栏进度与剩余时间同步刷新", {"op": P("string", "show|next|eta|add|remove|status|skill"), "tid": P("string", "任务表id"), "row": P("string", "行id（t1/t2…）"), "value": P("string", "add＝新步骤目标；status＝状态；skill＝技能id")}, ["op", "tid"]),
 F("user_send", "向用户客户端发送一条提示/结果文本", {"text": P("string", "文本")}, ["text"]),
 F("thinking_chain", "把一步决策记入逻辑链（frm→to：why）", {"frm": P("string", "从"), "to": P("string", "到"), "why": P("string", "理由")}, ["frm", "to", "why"]),
 F("glob", "按文件名模式找文件（支持 ** 递归·默认工作区）", {"pattern": P("string", "glob 模式"), "path": P("string", "基目录，默认工作区")}, ["pattern"]),
 F("grep", "文件内容正则检索（跳过 .git/__pycache__/node_modules）", {"pattern": P("string", "正则"), "path": P("string", "基目录"), "include": P("string", "文件名过滤如 *.py"), "max": P("integer", "最多命中")}, ["pattern"]),
 F("ls", "目录清单（默认工作区）", {"path": P("string", "目录")}, []),
 F("webfetch", "网页取文（仅 http(s)·须先 :grant network）", {"url": P("string", "http(s) URL"), "chars": P("integer", "最多字符")}, ["url"]),
 F("ask_user", "任务进行中向用户提问并阻塞等待其屏幕应答（一次一问·简短；无交互壳会立即返回说明）", {"question": P("string", "要问用户的问题")}, ["question"])]
REG = {"read": at.read, "write": at.write, "command": at.command, "skill": at.run_skill, "ask": at.ask, "task": atk.task, "task_detail": atk.task_detail, "task_plan": tt.revise, "user_send": at.user_send, "thinking_chain": at.thinking_chain, "glob": a2.glob, "grep": a2.grep, "ls": a2.ls, "webfetch": a2.webfetch, "ask_user": lambda question: __import__("ask_channel").ask(question)}
NAMES = [f["function"]["name"] for f in SCHEMA]
def tool_on(n): return bool(settings.get("agent_tools." + n, True))
def tools_schema(): return [f for f in SCHEMA if tool_on(f["function"]["name"])]
def tools_status(): return {n: tool_on(n) for n in NAMES}
def tools_toggle(n, v): settings.set("agent_tools." + n, bool(v)); return "工具 " + n + " → " + ("启用" if v else "禁用（对大模型隐藏并拒绝调用；F1→工具权限 或 :config set agent_tools." + n + " true 恢复）")
def bind(on_line=None, ev=False): return at.bind(on_line, ev)
def execute(name, raw):
    tname = {"command": "exec"}.get(name, name)
    if tname in NAMES and not tool_on(tname): return "工具已禁用：" + tname + "（菜单 F1→大模型工具权限 或 :tools enable " + tname + "）"
    try: a = json.loads(raw or "{}")
    except Exception: a = {"cmd": str(raw)}
    if name in ("exec", "command"): return at.command(a.get("cmd", ""))
    if name == "skill": return at.run_skill(a.get("name", ""), a.get("input") or a.get("inp") or "")
    fn = REG.get(name)
    if not fn: return "未知工具：" + name
    kw = {k: v for k, v in a.items() if k in fn.__code__.co_varnames[:fn.__code__.co_argcount]}
    try: return fn(**kw)
    except Exception as e: return "工具失败：" + str(e)[:200]
if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    if a[0] == "call" and len(a) > 1: print(execute(a[1], a[2] if len(a) > 2 else "{}"))
    elif a[0] == "skill" and len(a) > 2: r = at.run_skill(a[1], " ".join(a[2:])); print(("子会话 " + a[1] + " 已收口·返回 SMS 主流程（正文如上·⧉ 前缀·可继续话语或重派）") if r.startswith(at.WRAP) else r)
    elif a[0] == "task" and len(a) > 1: print(atk.task(" ".join(a[1:])))
    elif a[0] == "detail": print(atk.task_detail(a[1] if len(a) > 1 else ""))
    else: print(__doc__.strip().splitlines()[1][:400])
