#!/usr/bin/env python3
"""chains.py — 十一链记录 API（用户/记忆/逻辑/时间/事件/会话/调用skill/调用工具/子会话/代理对话/钉选knowledge）＋双层对话规则（红线 17）：每次用户输入＝开新对话（压缩记忆＋当前输入）、输出结束即收口；使用 agent 的 skill 必须自开新子会话并在完成后关闭（规则随对话注入，由 dream 审计）。用法：python chains.py <链> "<语句>" [--to <目标>] [--rel 关系]；子代理调用 log <skill|tool|sub> "<名>"。"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store
CHAINS = ("user", "memory", "logic", "time", "event", "session", "skill_call", "tool_call", "subsession", "dialogue", "knowledge")
RULE = "对话规则：本对话为新开对话，仅当前输入有效；压缩记忆仅供背景引用；输出结束后结束本对话；凡使用 agent 的 skill 必须另开子会话执行、完成后立即关闭子会话（禁止续用旧对话）。"

def store():
    return chain_store.Store(resolve_home.ensure())

def record(chain, text, edges=None):
    if chain not in CHAINS:
        return "ERR 未知链：" + chain + "（候选：" + "、".join(CHAINS) + "）"
    return store().add(chain, text, edges)

def session_id():
    return "conv-" + time.strftime("%Y%m%d-%H%M%S")

def conversation(text):
    import prompt_pack
    return "[压缩记忆]\n" + prompt_pack.pack(text, 1200) + "\n\n[" + RULE + "]\n\n[当前输入·唯一指令]\n" + text

def log(kind, name):
    sid = session_id()
    return record("skill_call" if kind == "skill" else "tool_call" if kind == "tool" else "subsession", name + "@" + sid, [[sid, "ref", 1]])

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__.strip().splitlines()[1]); sys.exit(1)
    if a[0] == "log" and len(a) >= 3:
        print(log(a[1], a[2])); sys.exit(0)
    if a[0] == "list":
        print("\n".join("%s %s %s" % (f["id"], f["chain"], f["text"][:60]) for f in store().all_frags(a[1] if len(a) > 1 else None))); sys.exit(0)
    if len(a) < 2:
        print("用法：chains.py <链> \"<语句>\" [--to t --rel r] | list [链] | log <skill|tool|sub> <名>"); sys.exit(1)
    edges = [[a[a.index("--to") + 1], a[a.index("--rel") + 1] if "--rel" in a else "semantic"]] if "--to" in a else None
    fid = record(a[0], a[1])
    if edges and fid and not str(fid).startswith("ERR"):
        store().link(fid, edges[0][0], edges[0][1])
    print(fid)
