#!/usr/bin/env python3
"""chains.py — 十一链记录 API（用户/记忆/逻辑/时间/事件/会话/调用skill/调用工具/子会话/对话/钉选knowledge）＋双层对话规则（红线 17：每次输入＝开新对话、结束即收口；用 agent 的 skill 必开子会话并收口，dream 审计）＋会话层 sess（session＝多对话容器，防跨会话污染：session/skill_call/tool_call/subsession/dialogue 碎片打 member→sess 边，prompt_pack 检索只收当前 sess）；清单存 <SMS_HOME>/shell/sessions.json＋current_session。用法：python -B chains.py <链> "<语句>" [--to <目标>] [--rel 关系] | session new [名]|list|use <id>|current | log <skill|tool|sub> "<名>" | list [链]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store
CHAINS = ("user", "memory", "logic", "time", "event", "session", "skill_call", "tool_call", "subsession", "dialogue", "knowledge")
ISO = ("session", "skill_call", "tool_call", "subsession", "dialogue")
RULE = "对话规则：本对话为新开对话，仅当前输入有效；压缩记忆仅供背景引用；输出结束后结束本对话；凡使用 agent 的 skill 必须另开子会话执行、完成后立即关闭子会话（禁止续用旧对话）。"
ACTIVE = {"conv": "", "sess": ""}
def store(): return chain_store.Store(resolve_home.ensure())
def record(chain, text, edges=None): return store().add(chain, text, edges) if chain in CHAINS else "ERR 未知链：" + chain + "（候选：" + "、".join(CHAINS) + "）"
def session_id(): return "conv-" + time.strftime("%Y%m%d-%H%M%S")
def _st(n): p = os.path.join(resolve_home.ensure(), "shell"); os.makedirs(p, exist_ok=True); return os.path.join(p, n)
def _smap():
    try: return json.load(open(_st("sessions.json"), encoding="utf-8"))
    except Exception: return {}
def cur_sess():
    if not ACTIVE["sess"]:
        try: ACTIVE["sess"] = open(_st("current_session"), encoding="utf-8").read().strip()
        except Exception: ACTIVE["sess"] = ""
    return ACTIVE["sess"] or new_sess("默认会话")
def new_sess(name=""):
    sid = "sess-" + time.strftime("%Y%m%d-%H%M%S"); m = _smap(); m[sid] = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "name": (name or "").strip()[:40] or sid[5:]}
    json.dump(m, open(_st("sessions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(_st("current_session"), "w", encoding="utf-8").write(sid)
    ACTIVE["sess"] = sid; record("session", "sess-new:" + sid + " " + m[sid]["name"]); return "已新建并切入会话 " + sid + "（旧会话链与对话已隔离）"
def use_sess(sid):
    if sid not in _smap(): return "无此会话：" + sid + "（session list 查看）"
    open(_st("current_session"), "w", encoding="utf-8").write(sid); ACTIVE["sess"] = sid; record("session", "sess-use:" + sid); return "已切换会话 " + sid
def list_sess():
    cur = cur_sess(); return "\n".join("%s %s｜%s%s" % (k, v.get("created", ""), v.get("name", ""), "（当前）" if k == cur else "") for k, v in sorted(_smap().items())) or "（暂无会话）"
def set_active(conv=None, sess=None): ACTIVE.update(({"conv": conv} if conv else {}) | ({"sess": sess} if sess else {}))
def conversation(text):
    import prompt_pack
    return "[压缩记忆]\n" + prompt_pack.pack(text, 1200, sess=cur_sess()) + "\n\n[" + RULE + "]\n\n[当前输入·唯一指令]\n" + text
def log(kind, name):
    sid = ACTIVE["conv"] or session_id()
    return record("skill_call" if kind == "skill" else "tool_call" if kind == "tool" else "subsession", name + "@" + sid, [[sid, "ref", 1], [cur_sess(), "member", 1]])
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__.strip().splitlines()[1]); sys.exit(1)
    if a[0] == "session":
        print(new_sess(" ".join(a[2:])) if len(a) > 1 and a[1] == "new" else list_sess() if len(a) > 1 and a[1] == "list" else use_sess(a[2]) if len(a) > 2 and a[1] == "use" else "当前会话 " + cur_sess()); sys.exit(0)
    if a[0] == "log" and len(a) >= 3: print(log(a[1], a[2])); sys.exit(0)
    if a[0] == "list": print("\n".join("%s %s %s" % (f["id"], f["chain"], f["text"][:60]) for f in store().all_frags(a[1] if len(a) > 1 else None))); sys.exit(0)
    edges = [[a[a.index("--to") + 1], a[a.index("--rel") + 1] if "--rel" in a else "semantic"]] if "--to" in a else None
    fid = record(a[0], a[1]) if len(a) > 1 else None
    if fid and edges and not str(fid).startswith("ERR"): store().link(fid, edges[0][0], edges[0][1])
    print(fid if fid else "用法：chains.py <链> \"<语句>\" [--to t --rel r] | session new|list|use|current | list [链] | log <skill|tool|sub> <名>")
