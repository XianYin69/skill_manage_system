#!/usr/bin/env python3
"""task_table.py — 任务表制表器（SMS 子技能 task_table·批12②·批14①复杂门控·批18 行数无上限＋主流程守卫·批22 模型裁量）：脚本标点粗分（task.decompose）只作「自动种子」——拆步≥2 且至少一步命中执行性技能时 attach() 先建种子表；批22：判简单时不再沉默，注入〔任务表·脚本未建〕一行把复杂判定权交还模型——模型判复杂即 task_plan op=plan（new_table·免用户写「制表」字样）自建表；〔任务表〕块命令模型据实改表（行数无上限·不得只跑一两行就停）按行推进·每步 task_plan status done·中途 add/remove/skill 改表；pending(conv)＝本对话未完成行清单供 gateway 主流程守卫续推（未完成不得收口·无依赖 task 工具并发·有依赖依序）；批29 子步骤并行真可用（task_res.py）：行资源声明 files=/dir=/reads=/port=/device=/skill= ＋冲突判定（写-写/写-读互斥·只读共享·端口设备互斥）＋ op=conflict 回传可并发/须串行分组 ＋ op=run 按互不冲突组并发批次执行（task.batch_parallel 上限·task.row_timeout 行级超时·失败隔离写 error 链）＋ eta 改批内最大值求和。落 <SMS_HOME>/tasks/<id>.json＋msg_flow task 信封（顶栏进度/剩余·eta＝未完成行×latency 均值）。用法：python -B task_table.py plan <诉求>|new <步骤逗号分隔>|show <tid>|next <tid>|eta <tid>|status <tid> <t#> <状态>|add <tid> <目标> [技能id]|remove <tid> <t#>|skill <tid> <t#> <技能id>|pending [conv]"""
import os, sys, json, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, task as tsk, skill_route, settings, atomic_io, latency, msg_flow, qq_report, task_res as tr
SMS = resolve_home.ensure(); GEN = ("general_answer", "constraint_arbiter"); TD = os.path.join(SMS, "tasks")
def _tf(tid): return os.path.join(TD, tid + ".json")
_SIG = {}
def _lc(tid):
    """批29 P1-01：按 (mtime_ns,size) 缓存解析——tasks\\ 已 115 张/186KB，旧版每次全量 rjson 把 UI 线程打到 950ms/s 空转。"""
    q = _tf(tid)
    try: st = os.stat(q); sg = (st.st_mtime_ns, st.st_size)
    except Exception: sg = None
    c = _SIG.get(tid)
    if sg is not None and c and c[0] == sg: return c[1]
    d = _load(tid)
    if len(_SIG) > 3000: _SIG.clear()
    _SIG[tid] = (sg, d); return d
def _save(doc):
    os.makedirs(TD, exist_ok=True); atomic_io.wjson(_tf(doc["id"]), doc)
    subs = doc.get("subtasks") or []
    if subs and all(x.get("status") == "done" for x in subs): _arch(doc["id"])
def _arch(tid):
    """批29 P3-12：全行 done 的表自动移入 tasks_archive\\，tasks\\ 只留在途表（P1-01 空转放大根因）。"""
    try:
        q = _tf(tid)
        if not os.path.exists(q): return ""
        os.makedirs(AD, exist_ok=True); os.replace(q, os.path.join(AD, tid + ".json"))
        _SIG.pop(tid, None); return tid
    except Exception: return 
AD = os.path.join(SMS, "tasks_archive")
def _load(tid):
    try:
        q = _tf(tid)
        if not os.path.exists(q): q = os.path.join(AD, tid + ".json")
        return atomic_io.rjson(q)
    except Exception: return None  # noqa
def _per_ms(llm):
    """单行预估毫秒：命中技能取该技能 latency 均值，否则取 llm 均值（旧口径不变）。"""
    def per(x): return (latency.avg("skill|" + str(x.get("skill"))) or llm) if x.get("skill") else llm
    return per
def eta(doc, parallel=None):
    """剩余时间预测（批29 修正）：默认按并发批次「批内最大值求和」（task.eta_parallel），
    旧版逐行累加在并行时高估耗时（实测 6 行表预测 240s·真实两批≈80s）；parallel=false 退回累加口径。"""
    llm = latency.avg("llm|" + str(settings.get("llm_gateway.model", "auto"))) or 45000
    rows = [x for x in (doc.get("subtasks") or []) if x.get("status") in ("pending", "running")]
    if not rows: return 0
    par = bool(settings.get("task.eta_parallel", True)) if parallel is None else bool(parallel)
    tot = tr.batch_eta(rows, _per_ms(llm)) if par else sum(_per_ms(llm)(x) for x in rows)
    return round(tot / 1000)
def _other_rows(tid="", conv=""):
    """跨表并行判定依据：同对话其他在途表的未完成行（多任务之间的子步骤并行也要有互斥证据）。"""
    c = conv or chains.ACTIVE.get("conv") or ""; out = []
    if not os.path.isdir(TD): return out
    for fn in sorted(os.listdir(TD)):
        t = fn[:-5]
        if not fn.endswith(".json") or t == tid: continue
        d = _lc(t)
        if not d or (c and d.get("conv") != c): continue
        out += [x for x in (d.get("subtasks") or []) if x.get("status") in ("pending", "running")]
    return out
def emit(doc, note="任务表"):
    import agent_tools as at; subs = doc.get("subtasks") or []; dn = sum(1 for x in subs if x.get("status") == "done"); at.emit("task", note + " " + str(doc["id"])[-14:] + "：" + str(dn) + "/" + str(len(subs)) + " " + msg_flow.fmt(eta(doc)), tool="task", meta={"id": doc["id"], "done": dn, "total": len(subs), "eta_s": eta(doc)}); qq_report.progress(doc, note)  # emit
def _rows(subs): return [{"id": "t%d" % (i + 1), "goal": (g := x["goal"] if isinstance(x, dict) else str(x)), "skill": (h := (skill_route.route(g)[0] or "").split(",")[0] or None), "inst": h or ("t%d" % (i + 1)), "status": "pending", "lane": "fg", "res": sorted(tr.resources(g, h or "")[0])} for i, x in enumerate(subs)]
def _mkdoc(intent, subs): tid = "task-" + time.strftime("%Y%m%d-%H%M%S") + "-" + "%03d" % (time.time() * 1000 % 1000); doc = {"id": tid, "intent": str(intent), "conv": chains.ACTIVE["conv"], "sess": chains.cur_sess(), "created": time.strftime("%Y-%m-%d %H:%M:%S"), "table": "task_table", "src": __import__("qq_stall").src(chains.ACTIVE["conv"]), "subtasks": subs}; _save(doc); emit(doc, "任务表（粗分种子·首轮据实改表）"); return doc
CUT = "，,。;；、 \n\"'“”‘’「」[]()（）"
def _steps(value): return [x.strip(CUT) for x in re.split(r"[\n,，;；、]", str(value)) if x.strip(CUT)]
def plan(intent, steps=None):
    subs = _rows(steps) if steps is not None else _rows(tsk.decompose(str(intent)))
    if steps is None and (len(subs) < 2 or not any(x["skill"] and x["skill"] not in GEN for x in subs)): return None
    return _mkdoc(intent, subs) if subs else None
def _res_hint(x):
    """行占用提示（只列互斥资源：写路径/目录/端口/设备——只读不互斥，不占版面）。"""
    w = [t[2:] for t in (x.get("res") or []) if t.startswith(("w:", "d:", "p:", "v:"))]
    return ("〔占:" + "、".join(w[:3]) + ("…" if len(w) > 3 else "") + "〕") if w else ""
def block(doc): return "\n〔任务表 " + doc["id"] + "（预测" + msg_flow.fmt(eta(doc)) + "）〕\n" + "\n".join("%s %s%s%s%s" % (x["id"], str(x["goal"])[:70], ("〔技能:" + str(x["skill"]) + "〕" if x.get("skill") else "〔工具自办〕"), "〔后台·不阻前台收口〕" if str(x.get("lane", "fg")) == "bg" else "", _res_hint(x)) for x in doc["subtasks"]) + "\n〔执行规则〕这是脚本粗分种子或你自建的表——复杂与否由你判、按真实步骤推进（task_plan add/remove/skill 随时改表），行数无上限、不得只跑一两行就停；按行推进：〔技能:x〕调 skill 派发、〔工具自办〕用 exec/read/write/glob/grep 自办；并行按资源互斥判定（task_res.py·不再凭口头判断）：建行/改行时在目标里声明资源 files=… |dir=… |reads=… |port=… |device=… |skill=…（逗号分隔多个；未声明则脚本按 goal 自动抽路径与端口判冲突）；task_plan op=conflict 取「哪几行可并发、哪几行必须串行」（写-写/写-读/同端口/同设备＝冲突·只读可共享·value=all 连其他在途表一起判），op=run 一次把互不冲突的行组成并发批次执行（批内≤task.batch_parallel·每行独立超时 task.row_timeout·失败行只标自己并写 error 链），或继续用 task 工具 parallel=true 并发派发；顶栏剩余时间已按批内最大值估算；每步完成立刻 task_plan status <表id> <行id> done（顶栏进度据此刷新）；全部行 done 才输出整合结果收口——派发对话收口＝形式停止·调度方继续未完成行（批23 对等对话），禁止把单个派发完成当作整段任务结束。\n"
def attach(intent): return "" if not settings.get("task.auto_table", True) else (block(d) if (d := plan(intent)) else "\n〔任务表·脚本未建〕标点粗分判非复杂或无执行技能命中——复杂与否由你定：判定需≥2步动手执行时，先 task_plan op=plan value=你拆的各步骤（逗号分隔）自建表并按表推进；单步/问答直接办，勿为表而表。\n")
def pending(conv=""):
    c = conv or chains.ACTIVE.get("conv") or ""; out = []
    for tid in ([fn[:-5] for fn in sorted(os.listdir(TD)) if fn.endswith(".json")] if os.path.isdir(TD) else []):
        doc = _load(tid); rest = [x for x in (doc.get("subtasks") or []) if x.get("status") != "done" and str(x.get("lane", "fg")) != "bg"] if doc and doc.get("conv") == c else []
        rest and out.append("〔任务表 " + tid[-14:] + "〕未完成 " + str(len(rest)) + "/" + str(len(doc.get("subtasks") or [])) + "：" + "；".join(str(x.get("id")) + "｜" + str(x.get("skill") or "工具自办") + "｜" + str(x.get("goal"))[:40] + "〔" + str(x.get("status", "pending")) + "〕" for x in rest)[:600])
    return "\n".join(out)
def unfinished():
    """未完成计划表 [(tid, done, total)]＝仍有非 done 行的表（＝尚未生成最终输出）·底栏停止/继续按钮可见性判据。"""
    out = []
    if not os.path.isdir(TD): return out
    for fn in sorted(os.listdir(TD)):
        if not fn.endswith(".json"): continue
        doc = _lc(fn[:-5]); subs = (doc or {}).get("subtasks") or []
        if not subs: continue
        dn = sum(1 for x in subs if x.get("status") == "done")
        if dn < len(subs): out.append((fn[:-5], dn, len(subs)))
    return out

def new_table(intent, sv): rows = _steps(sv); d = plan(intent, steps=rows) if rows else None; return ("已建任务表 " + d["id"] + "（" + str(len(d["subtasks"])) + " 行·据实推进）\n" + block(d)) if d else "建表失败：步骤为空——value/参数＝你拆的步骤（逗号/顿号分隔）"
def _all(): return sorted([f[:-5] for f in (os.listdir(TD) if os.path.isdir(TD) else []) if f.endswith(".json")])
def _find(t): k = [i for i in _all() if (t := str(t or "").strip()) and (i == t or i.endswith(t) or t in i)]; return k[-1] if k else ""
def _latest():
    sc = lambda d: 0 if (c := chains.ACTIVE.get("conv") or "") and d.get("conv") == c else 1 if d.get("sess") == chains.cur_sess() else 2
    op_ = [(d, t) for t in _all() if (d := _lc(t)) and any(x.get("status") != "done" for x in (d.get("subtasks") or []))]
    return sorted(op_, key=lambda z: (sc(z[0]), z[1]))[-1][1] if op_ else ""
def revise(op, tid="", row="", value=""):
    if op in ("new", "plan"): st = _steps(value or tid); return new_table(str(tid or value)[:200] if (value or tid) else "未命名任务表", st) if st else "建表失败：value＝你拆的步骤（逗号/顿号分隔）"
    _tid = str(tid or "").strip()
    if _tid:
        _hit = _find(_tid)
        if not _hit: return "无此表：" + _tid + "（tid 未命中即拒绝·不回落他人表·task_plan show 看全部）"
        doc = _load(_hit)
    else:
        doc = _load(_latest())
    if not doc: return "无任务表：" + str(tid) + "（task_plan op=plan value=<步骤逗号分隔> 先建表；op=show 看全部）"
    if not row and re.search(r"pending|running|error|stopped", str(value or "")): row, value = str(value), "done"
    subs = doc.get("subtasks") or []; x = next((s for s in subs if s.get("id") == row), None)
    if op == "show":
        for x in subs: tr.res_of(x)
        return json.dumps({"id": doc["id"], "sess": doc.get("sess"), "conv": doc.get("conv"), "subtasks": subs}, ensure_ascii=False)[:2400]
    if op == "next": p = next((s for s in subs if s.get("status") == "pending"), None); return (p and (str(p["id"]) + "｜" + str(p.get("skill") or "工具自办") + "｜" + str(p["goal"])[:80])) or "全部完成"
    if op == "eta": return "剩余预测 " + msg_flow.fmt(eta(doc))
    if op == "lane":
        if not x: return "无此行：" + str(row)
        x["lane"] = "bg" if str(value or "").strip().lower() in ("bg", "后台", "back", "background") else "fg"
        _save(doc); emit(doc, "任务表（行转%s）" % ("后台" if x["lane"] == "bg" else "前台"))
        return "行 %s 车道＝%s（后台行不阻前台收口·表内地位相同）" % (row, x["lane"])
    if op == "add": n = 1 + max([int(str(s["id"])[1:]) for s in subs if str(s["id"]).startswith("t") and str(s["id"])[1:].isdigit()] or [0]); sid, _ = skill_route.route(str(value)); h = (sid or "").split(",")[0] or None; subs.append({"id": "t%d" % n, "goal": str(value), "skill": h, "inst": h or "t%d" % n, "status": "pending", "res": sorted(tr.resources(str(value), h or "")[0])}); _save(doc); emit(doc, "任务表加行"); return "已加 t%d｜%s%s" % (n, str(value)[:60], ("·指定技能 " + h) if h else "")
    if op == "remove" and x: subs.remove(x); _save(doc); emit(doc, "任务表删行"); return "已删 " + str(row)
    if op == "status" and x: x["status"] = value if value in ("pending", "running", "done", "error", "stopped") else "done"; _save(doc); emit(doc, "任务表步进"); return str(row) + " → " + x["status"] + "（" + str(sum(1 for s in subs if s.get("status") == "done")) + "/" + str(len(subs)) + "·" + msg_flow.fmt(eta(doc)) + "）"
    if op == "skill" and x: x["skill"] = str(value); x["inst"] = str(value); _save(doc); emit(doc, "任务表改派"); return str(row) + " 指定技能：" + str(value)
    if op == "conflict":
        rows = [x for x in subs if x.get("status") != "done"]
        if str(value or "").strip().lower() in ("all", "cross", "跨表"): rows = rows + _other_rows(doc["id"])
        if not rows: return "无未完成行——本表已清空"
        cf = tr.conflicts(rows)
        return tr.report(rows) + ("\n结论：%d 行分 %d 批执行·%d 对资源冲突需串行（同批内行可一次并发·批间依序）" % (len(rows), len(tr.batches(rows)), len(cf)) if cf else "\n结论：无冲突——%d 行可一次全并发（op=run 或 task 工具 parallel=true）" % len(rows))
    if op == "run":
        rows = [x for x in subs if x.get("status") in ("pending", "running")]
        if not rows: return "无未完成行——本表已清空"
        import agent_task as atk; return atk.run_table(doc, rows)
    if op == "res" and x:
        toks = sorted(tr.resources(str(value), x.get("skill") or "")[0]) if value else sorted(tr.res_of(x))
        x["res"] = toks; x["res_decl"] = str(value or ""); _save(doc); emit(doc, "任务表声明资源")
        return "行 %s 资源＝%s（写占用即与他行互斥·只读可共享）" % (row, "、".join(toks) or "（未识别到资源——目标里写明 files=/dir=/reads=/port=）")
    return "用法 task_plan new|show|next|eta|conflict|run|res|add|remove|status|skill|lane <表id/步骤> [行id] [值]"


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__.strip().splitlines()[-1])
    elif a[0] == "plan" and len(a) > 1: d = plan(" ".join(a[1:])); print(block(d) if d else "判非复杂或无执行技能命中——免表直送（模型判多步即 task_plan op=plan value=步骤逗号分隔）")
    elif a[0] == "new" and len(a) > 1: print(new_table("模型自建表", _steps(a[1])))
    elif a[0] == "pending": print(pending(a[1] if len(a) > 1 else "") or "无未完成行")
    elif a[0] in ("show", "next", "eta", "conflict", "run") and len(a) > 1: print(revise(a[0], a[1], "", a[2] if len(a) > 2 else ""))
    elif a[0] == "add" and len(a) > 2: print(revise("add", a[1], "", a[2]))
    elif a[0] in ("status", "remove", "skill", "lane", "res") and len(a) > 2: print(revise(a[0], a[1], a[2], a[3] if len(a) > 3 else ""))
    else: print(__doc__.strip().splitlines()[-1])
