#!/usr/bin/env python3
"""chains.py — 十一链记录 API（用户/记忆/逻辑/时间/事件/会话/调用skill/调用工具/subsession 派发对话/对话/钉选knowledge）＋对话规则（红线 17·批23 对等对话：每次用户输入与每次技能派发＝各开一个独立 conv 独立链归属，对话间无主次、互任监视者·指导者·训诫者；输出停止＝形式收口非实质完成，dream 审计）＋会话层 sess（session＝多对话容器·新建会话＝新 session 非 conv，防跨会话污染：session/skill_call/tool_call/subsession/dialogue 碎片打 member→sess 边，prompt_pack 检索只收当前 sess；多壳并行以 env SMS_SESSION 各绑其 session；先后顺序与跨会话未完成冲突经 sessions_view 供对话监视）；清单存 <SMS_HOME>/shell/sessions.json＋current_session；批17 读写时序分层——在谈链（user/logic/dialogue/session/skill_call/tool_call/subsession）会话中即写，收口链（memory/knowledge/time/event）对话中经 chain_timing 缓冲、收口统一落盘。用法：python -B chains.py <链> "<语句>" [--to <目标>] [--rel 关系] | session new [名]|list|use <id>|current|overview|conflicts | log <skill|tool|sub> "<名>" | list [链]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store, chain_timing
CHAINS = ("user", "memory", "logic", "time", "event", "session", "skill_call", "tool_call", "subsession", "dialogue", "knowledge")
ISO = ("session", "skill_call", "tool_call", "subsession", "dialogue")
RULE = "对话规则（批23·对等对话）：本对话是独立对话——每次用户输入与每次技能派发各成一个独立 conv 与独立链归属，对话间无主次之分，只互相扮演监视者·指导者·训诫者；输出停止＝形式收口而非实质完成，任务完成只认〔任务表〕全部行 done 与用户诉求落地；本对话收口只结束自己：〔任务表〕仍有未完成行时由调度你的对话（或任何监视到它的对话）继续推进，禁止把单个派发完成当作整段任务结束；凡使用 agent 的 skill 必须另开对等对话执行并即时收口（红线17·防跨对话污染）；压缩记忆仅供背景引用；[当前输入·唯一指令] 只约束本对话；session＝多对话容器（新建会话＝新 session·conv 每输入/派发自动开收），话语带〔会话拓扑〕＝他 session 有未完成/冲突线索——负监视训诫之责：提示用户接续或收口，未经确认不越会话代改他人表；处理协议（批24）＝内部处理一律英语·语句精简，用户可见输出先英语成稿再译回用户语言。"
ACTIVE = {"conv": "", "sess": ""}
def store(): return chain_store.Store(resolve_home.ensure())
def record(chain, text, edges=None): return chain_timing.buffer(chain, text, edges) if chain in CHAINS and chain_timing.deferred(chain) else store().add(chain, text, edges) if chain in CHAINS else "ERR 未知链：" + chain + "（候选：" + "、".join(CHAINS) + "）"
def session_id(): return "conv-" + time.strftime("%Y%m%d-%H%M%S")
def _st(n): p = os.path.join(resolve_home.ensure(), "shell"); os.makedirs(p, exist_ok=True); return os.path.join(p, n)
def _smap():
    import atomic_io
    try: return atomic_io.rjson(_st("sessions.json"))
    except Exception: return {}
def cur_sess():
    if not ACTIVE["sess"]:
        try: ACTIVE["sess"] = os.environ.get("SMS_SESSION") or open(_st("current_session"), encoding="utf-8").read().strip()
        except Exception: ACTIVE["sess"] = ""
    return ACTIVE["sess"] or new_sess("默认会话")
def new_sess(name=""):
    sid = "sess-" + time.strftime("%Y%m%d-%H%M%S"); m = _smap(); m[sid] = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "name": (name or "").strip()[:40] or sid[5:]}
    import atomic_io; atomic_io.wjson(_st("sessions.json"), m); open(_st("current_session"), "w", encoding="utf-8").write(sid)
    ACTIVE["sess"] = sid; record("session", "sess-new:" + sid + " " + m[sid]["name"]); return "已新建并切入会话（session）" + sid + "——新建会话＝新 session 非 conv·conv 每输入/派发自动开收（批23 对等对话）"
def use_sess(sid):
    if sid not in _smap(): return "无此会话：" + sid + "（session list 查看）"
    open(_st("current_session"), "w", encoding="utf-8").write(sid); ACTIVE["sess"] = sid; record("session", "sess-use:" + sid); return "已切换会话 " + sid
def list_sess():
    cur = cur_sess(); return "\n".join("%s %s｜%s%s" % (k, v.get("created", ""), v.get("name", ""), "（当前）" if k == cur else "") for k, v in sorted(_smap().items())) or "（暂无会话）"
def set_active(conv=None, sess=None): ACTIVE.update(({"conv": conv} if conv else {}) | ({"sess": sess} if sess else {}))
def conversation(text):
    import prompt_pack; h = __import__("sessions_view").hint(cur_sess())
    return "[压缩记忆]\n" + prompt_pack.pack(text, 1200, sess=cur_sess()) + "\n\n[" + RULE + "]" + ("\n\n〔会话拓扑〕" + h if h else "") + "\n\n[当前输入·唯一指令]\n" + text
def log(kind, name, conv=""):
    sid = conv or ACTIVE["conv"] or session_id()
    return record("skill_call" if kind == "skill" else "tool_call" if kind == "tool" else "subsession", name + "@" + sid, [[sid, "ref", 1], [cur_sess(), "member", 1]])
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__.strip().splitlines()[1]); sys.exit(1)
    if a[0] == "session":
        if len(a) > 1 and a[1] in ("overview", "conflicts"): import sessions_view as sv; print(sv.overview(cur_sess()) if a[1] == "overview" else sv.conflicts(cur_sess()) or "（无跨会话未完成·各会话任务表均已收口）"); sys.exit(0)
        print(new_sess(" ".join(a[2:])) if len(a) > 1 and a[1] == "new" else list_sess() if len(a) > 1 and a[1] == "list" else use_sess(a[2]) if len(a) > 2 and a[1] == "use" else "当前会话 " + cur_sess() + "（session＝多对话容器·conv 自动开收）"); sys.exit(0)
    if a[0] == "log" and len(a) >= 3: print(log(a[1], a[2])); sys.exit(0)
    if a[0] == "list": print("\n".join("%s %s %s" % (f["id"], f["chain"], f["text"][:60]) for f in store().all_frags(a[1] if len(a) > 1 else None))); sys.exit(0)
    edges = [[a[a.index("--to") + 1], a[a.index("--rel") + 1] if "--rel" in a else "semantic"]] if "--to" in a else None
    fid = record(a[0], a[1]) if len(a) > 1 else None
    if fid and edges and not str(fid).startswith("ERR"): store().link(fid, edges[0][0], edges[0][1])
    print(fid if fid else "用法：chains.py <链> \"<语句>\" [--to t --rel r] | session new|list|use|current | list [链] | log <skill|tool|sub> <名>")
