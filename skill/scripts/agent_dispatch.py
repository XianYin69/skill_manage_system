#!/usr/bin/env python3
"""agent_dispatch.py — agent 工具 schema 与派发（gateway 工具循环与 CLI 共用·单一真源）：SCHEMA＝OpenAI function 清单 exec·read·write·skill·ask·task·task_detail·user_send·thinking_chain；execute(name, raw_args)→agent_tools/agent_task 对应实现，参数按形参名过滤、异常回错误文本给模型（不中断工具循环）。用法：python -B agent_dispatch.py call <工具> '<json参数>' | skill <技能id> <诉求> | task <诉求> | detail [task-id]"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import agent_tools as at, agent_task as atk
P = lambda t, d: {"type": t, "description": d}; F = lambda n, d, p, r: {"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": r}}}
SCHEMA = [F("exec", "执行 shell 命令（cwd＝工作区·生成文件入 tmp）", {"cmd": P("string", "命令")}, ["cmd"]),
 F("read", "读文本文件", {"path": P("string", "路径"), "max_lines": P("integer", "最多行数")}, ["path"]),
 F("write", "写文本文件（工作区/SMS 默认可写，越界需授权）", {"path": P("string", "路径"), "content": P("string", "内容"), "append": P("boolean", "是否追加")}, ["path", "content"]),
 F("skill", "把诉求派发给托管技能在其子会话按其 SKILL.md 全文执行（命中技能必须用它，禁止自行代答）", {"name": P("string", "技能id"), "input": P("string", "用户诉求")}, ["name", "input"]),
 F("ask", "子问答：需要独立小答案时用（≤300字·不面向用户复述）", {"question": P("string", "问题")}, ["question"]),
 F("task", "把复合诉求拆分为子任务并行执行并整合（进度实时上顶栏）", {"intent": P("string", "诉求")}, ["intent"]),
 F("task_detail", "查询任务进度（id 空＝最近清单）", {"id": P("string", "任务id")}, []),
 F("user_send", "向用户客户端发送一条提示/结果文本", {"text": P("string", "文本")}, ["text"]),
 F("thinking_chain", "把一步决策记入逻辑链（frm→to：why）", {"frm": P("string", "从"), "to": P("string", "到"), "why": P("string", "理由")}, ["frm", "to", "why"])]
REG = {"read": at.read, "write": at.write, "command": at.command, "skill": at.run_skill, "ask": at.ask, "task": atk.task, "task_detail": atk.task_detail, "user_send": at.user_send, "thinking_chain": at.thinking_chain}
def bind(on_line=None, ev=False): return at.bind(on_line, ev)
def execute(name, raw):
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
    elif a[0] == "skill" and len(a) > 2: print(at.run_skill(a[1], " ".join(a[2:])))
    elif a[0] == "task" and len(a) > 1: print(atk.task(" ".join(a[1:])))
    elif a[0] == "detail": print(atk.task_detail(a[1] if len(a) > 1 else ""))
    else: print(__doc__.strip().splitlines()[1][:400])
