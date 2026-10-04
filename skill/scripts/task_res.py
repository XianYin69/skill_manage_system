#!/usr/bin/env python3
"""task_res.py — 任务表行级资源声明·冲突判定·并发批次·并行执行器（批29·用户诉求「子步骤并行真正可用」：多任务之间＋单一任务表内的子步骤并行，前提＝互不冲突）。旧版并行前提全靠模型口头判断（task 工具 parallel=true／task_plan lane），既没有互斥依据、也没有并行度上限/行级超时/失败隔离，eta 还按串行累加高估耗时。本模块补四件事：①资源声明——行 goal 内可写 files=a.py,b.md／dir=tmp／reads=x.json／port=8080／device=mouse／skill=xxx；未显式声明时按正则自动抽取 goal 中的路径与端口，写动词（修改/写入/生成/patch/apply…）决定读写属性；②冲突判定 conflicts(rows)——同一资源被两行「写」占用即冲突，写+读按 task.conflict_read_write（默认 true＝保守串行）判冲突，只读可共享，目录与其内文件按前缀判冲突，路径按归一化尾两段匹配（绝对/相对同形即撞），端口/设备/交互会话＝恒互斥，同技能默认不算冲突（task.conflict_skill，agent_task 已给同技能多实例各开独立 conv）；③批次编排 batches(rows, limit)——贪心首适：按行序把互不冲突的行塞进同一批，批内并发上限 task.batch_parallel（默认 3），批与批之间串行（跨批存在冲突），并把结论回传调度方（哪几行可并发、哪几行必须串行）；④并行执行 run_rows(rows, runner, limit, timeout)——逐批 ThreadPoolExecutor 并发，每行独立超时 task.row_timeout（秒·到点标 timeout 并 cancel 未起行的线程，不拖同批其他行）、独立失败隔离（异常标 error＋写 error 链，其余行照常跑完），返回 wall_s 供实测。task_table.eta 经 batch_eta 用「批内最大值求和」替代串行累加。用法：python -B task_res.py check <表id> | plan <表id> | selftest [tmp目录]"""
import os, sys, re, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import settings

# 资源 token 种类：w=路径写 r=路径读 d=目录写 p=端口 v=设备/会话/浏览器 s=技能
W_K = ("files", "file", "paths", "path", "outputs", "out", "dst", "targets", "target", "writes", "write", "outdir")
R_K = ("reads", "read", "src", "sources", "inputs", "input")
D_K = ("dir", "dirs", "folders")
P_K = ("port", "ports")
V_K = ("device", "devices", "session", "sessions", "browser", "instances", "instance")
S_K = ("skill", "skills")
_KVKEY = "|".join(sorted(set(W_K + R_K + D_K + P_K + V_K + S_K), key=len, reverse=True))
KV = re.compile(r"(?<![\w.\-])(%s)\s*[=:：]\s*([^\s;；]+)" % _KVKEY, re.I)
WRITE_VERB = re.compile(r"(修改|写入|新建|创建|删除|更新|实现|生成|改造|重构|修复|补丁|应用|提交|部署|落盘|回写|patch|write|create|delete|update|apply|commit|deploy|refactor|fix|implement|generate)", re.I)
PATH_RX = re.compile(r"(?:[A-Za-z]:[\\/][^\s,;、，）)（\"'”’]+|(?:[\w\-.]+[\\/])+[\w\-.]+|[\w\-.]+\.(?:py|md|json|ya?ml|toml|js|ts|tsx|txt|csv|log|ps1|sh|html|css|ini|cfg|jsonl))")
PORT_RX = re.compile(r"(?:port|端口)\s*[=:：]?\s*(\d{2,5})")


def _norm(p):
    """路径归一：去引号/尾标点、统一分隔符、去盘符与 ./ 前缀（绝对与相对同形即视为同一资源）。"""
    s = str(p or "").strip().strip("\"'“”‘’「」").rstrip(".,;:、。").replace("\\", "/")
    s = re.sub(r"(?i)^[a-z]:", "", s)
    while "//" in s: s = s.replace("//", "/")
    s = re.sub(r"^\.?/+|/+$", "", s)
    return s.lower()

def _tail(p, n=2):
    parts = [x for x in str(p or "").split("/") if x]
    return "/".join(parts[-n:]) if parts else ""

def _vals(v):
    return [x.strip().strip("\"'“”‘’") for x in re.split(r"[,，、]", str(v or "")) if x.strip().strip("\"'“”‘’")]

def resources(goal, skill=""):
    """行资源集：显式 `k=v` 声明优先；无声明时按正则自动抽取 goal 中的路径/端口，写动词决定读写属性。
    回 (tokens, declared)——declared＝本行有显式声明（供模型核对自动抽取是否漏了）。"""
    g = str(goal or ""); toks, declared = set(), False
    for m in KV.finditer(g):
        key = m.group(1).lower(); vals = _vals(m.group(2))
        if not vals: continue
        declared = True
        for v in vals:
            if key in W_K: toks.add("w:" + _norm(v))
            elif key in R_K: toks.add("r:" + _norm(v))
            elif key in D_K: toks.add("d:" + _norm(v))
            elif key in P_K: toks.add("p:" + re.sub(r"\D", "", str(v)))
            elif key in V_K: toks.add("v:" + _norm(v))
            elif key in S_K: toks.add("s:" + _norm(v))
    if not declared:
        wr = bool(WRITE_VERB.search(g))
        for x in PATH_RX.findall(g):
            nx = _norm(x)
            if nx: toks.add(("w:" if wr else "r:") + nx)
        for x in PORT_RX.findall(g): toks.add("p:" + x)
    if skill: toks.add("s:" + _norm(skill))
    return {t for t in toks if t.split(":", 1)[-1]}, declared

def _same(a, b):
    """两 token 是否指向同一/重叠资源：端口/设备/技能＝全等；路径族（w/r/d）＝全等、尾两段同形（绝对 vs 相对）、或目录前缀包含。"""
    ka, va = a.split(":", 1); kb, vb = b.split(":", 1)
    if ka in ("p", "v", "s") or kb in ("p", "v", "s"): return a == b
    if va == vb: return True
    ta, tb = _tail(va), _tail(vb)
    if ta and ta == tb: return True
    return va.startswith(vb + "/") or vb.startswith(va + "/")

def _kind(t): return str(t).split(":", 1)[0]
def res_of(row):
    """行资源集（算一次缓存进 row["res"]）：row＝{"goal","skill"} 或已带 res 的 dict／直接给 token 集合。"""
    if isinstance(row, (set, list, tuple, frozenset)): return set(row)
    if row.get("res") is None:
        row["res"] = sorted(resources(row.get("goal") or "", row.get("skill") or "")[0])
    return set(row["res"])

def pair_conflict(a, b, rw=None, sk=None):
    """两行冲突判定，回 (是否冲突, 资源, 说明)：写-写必冲突；写+读按 task.conflict_read_write（默认 true＝保守串行）；
    只读可共享；端口/设备/交互会话恒互斥；同技能按 task.conflict_skill（默认 false＝agent_task 已给同技能多实例各开独立 conv）。"""
    rw = bool(settings.get("task.conflict_read_write", True)) if rw is None else rw
    sk = bool(settings.get("task.conflict_skill", False)) if sk is None else sk
    A, B = res_of(a), res_of(b)
    for x in A:
        for y in B:
            if not _same(x, y): continue
            kx, ky = _kind(x), _kind(y)
            if kx == "s" or ky == "s":
                if sk: return True, x, "同技能互斥（task.conflict_skill=true）"
                continue
            if kx in ("p", "v") and ky in ("p", "v"): return True, x, "端口/设备/会话互斥：" + x
            if kx == "r" and ky == "r": continue
            if kx == "r" or ky == "r":
                if rw: return True, x, "写读冲突（task.conflict_read_write=true）：" + x + " × " + y
                continue
            return True, x, "写写冲突：" + x + " × " + y
    return False, "", ""

def _rid(r, i=0):
    return str(r.get("id") or ("t%d" % (i + 1))) if isinstance(r, dict) else "row%d" % (i + 1)
def conflicts(rows):
    """全对冲突清单 [{"a","b","res","why"}]——行序保持表序，供调度方核对「哪几行必须串行」。"""
    rs = list(rows); out = []
    for i, a in enumerate(rs):
        for j in range(i + 1, len(rs)):
            b = rs[j]; hit, res, why = pair_conflict(a, b)
            if hit: out.append({"a": _rid(a, i), "b": _rid(b, j), "res": res, "why": why})
    return out

def batches(rows, limit=None):
    """贪心首适并发编排：按行序把互不冲突的行塞进同一批（批内并发≤limit），批与批之间串行（跨批存在冲突或超并发上限）。"""
    limit = int(limit or 0) or max(1, int(settings.get("task.batch_parallel", 3) or 3))
    out = []
    for r in rows:
        for bt in out:
            if len(bt) >= limit: continue
            if any(pair_conflict(r, o)[0] for o in bt): continue
            bt.append(r); break
        else: out.append([r])
    return out

def batch_eta(rows, per):
    """并行剩余估算：每批取「批内最大值」再求和（旧版＝逐行累加，并行时高估）。per(row)→该 row 预估毫秒。"""
    return sum(max([int(per(r)) for r in bt] or [0]) for bt in batches(rows))

def _one(runner, row, tmo):
    """单行执行＋独立超时：runner 在守护线程里跑，join(tmo) 到点即弃线程（不 kill·不阻同批其他行）。
    回 (状态, 值/异常)——状态∈done|error|timeout。"""
    box = {}
    def work():
        try: box["v"] = runner(row); box["ok"] = True
        except Exception as e: box["err"] = e; box["ok"] = False
    th = threading.Thread(target=work, daemon=True); th.start(); th.join(tmo or None)
    if th.is_alive(): return "timeout", RuntimeError("行超时 %ss（线程弃置·不阻同批其他行）" % tmo)
    return ("done", box["v"]) if box.get("ok") else ("error", box.get("err", RuntimeError("行无返回")))

def run_rows(rows, runner, limit=None, timeout=None, on_row=None, error_chain=True, src="task"):
    """逐批并发执行（批内并发≤limit·批间串行）：每行独立超时（秒·默认 task.row_timeout，0＝不限）与独立失败隔离——
    异常/超时只标该行，同批其余行照常跑完；失败原因写回 row["status"]/row["result"] 并记 error 链。
    runner(row)→结果（回写 row["result"]）；on_row(row, status)＝每行收口回调（落盘/发进度信封）。
    回 {"wall_s","batches":[[row_id]],"done","error","timeout","stopped","results":[row]}。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    tmo = float(timeout if timeout is not None else (settings.get("task.row_timeout", 0) or 0))
    bs = batches(rows, limit); out = []; t0 = time.time(); stat = {"done": 0, "error": 0, "timeout": 0, "stopped": 0}
    for bt in bs:
        with ThreadPoolExecutor(max_workers=max(1, len(bt))) as ex:
            fut = {ex.submit(_one, runner, r, tmo): r for r in bt}
            for f in as_completed(fut):
                r = fut[f]
                try: st, v = f.result()
                except Exception as e: st, v = "error", e
                own = r.get("status")
                if st == "done" and own in ("error", "stopped"): st = own      # runner 自判终态优先（agent_task.one 内部已写 result）
                r["status"] = st
                if st == "done": r["result"] = str(v)[:600] if v is not None else ""; stat["done"] += 1
                elif st == "stopped": stat["stopped"] += 1
                else:
                    if own != "error": r["result"] = "执行失败：" + str(v)[:180]
                    stat["error" if st == "error" else "timeout"] += 1
                    if error_chain:
                        try:
                            import chain_error
                            chain_error.record("task", str(src) + ":" + str(r.get("id") or "?"), "%s %s" % (st, str(v if own != "error" else r.get("result"))[:200]))
                        except Exception: pass
                out.append(r)
                if on_row:
                    try: on_row(r, st)
                    except Exception: pass
    return {"wall_s": round(time.time() - t0, 2), "batches": [[str(r.get("id")) for r in b] for b in bs],
            "done": stat["done"], "error": stat["error"], "timeout": stat["timeout"], "stopped": stat["stopped"], "results": out}

def report(rows, limit=None):
    """给调度方的并发结论（一行一批＝必须串行）：〔可并发〕批＝同批行可一次并行派发，〔须串行〕＝跨批原因（冲突资源）。"""
    bs = batches(rows, limit); ls = []
    for i, bt in enumerate(bs, 1):
        ls.append("批%d〔可并发 %d 行〕%s" % (i, len(bt), "、".join(str(r.get("id")) + "(" + str(r.get("skill") or "工具自办") + ")" for r in bt)))
    cf = conflicts(rows)
    for c in cf: ls.append("串行依据：%s × %s %s" % (c["a"], c["b"], c["why"]))
    ls.append("并行度上限 %d·批间串行（跨批冲突）" % (int(limit or 0) or int(settings.get("task.batch_parallel", 3) or 3)))
    return "\n".join(ls)

def _doc_rows(tid):
    import task_table as tt; d = tt._load(tt._find(tid)) or {}; return d, [r for r in (d.get("subtasks") or [])]

def selftest(tmp=""):
    """回归：6 行含 2 组资源冲突的表——断言分组正确、并行实测墙钟≈批内最大值（非累加）、失败隔离与行级超时生效；产物清单写 SMS_TMP。"""
    tmp = tmp or os.environ.get("SMS_TMP") or os.getcwd(); os.makedirs(tmp, exist_ok=True)
    ok = []; art = []
    def mk(i, goal, skill=""): return {"id": "t%d" % i, "goal": goal, "skill": skill, "status": "pending"}
    rows = [mk(1, "改造冲突检测模块 files=src/a.py"), mk(2, "改造并行执行器 files=src/a.py"), mk(3, "写报告 files=out/b.md"),
            mk(4, "校对报告 reads=out/b.md"), mk(5, "起服务 port=8080"), mk(6, "起服务 port=8081")]
    cf = conflicts(rows)
    ok.append(("冲突对＝2 组（t1×t2 写写、t3×t4 写读）", len(cf) == 2 and {(cf[0]["a"], cf[0]["b"]), (cf[1]["a"], cf[1]["b"])} == {("t1", "t2"), ("t3", "t4")}, str(cf)))
    bs = batches(rows, 3)
    ids = [[r["id"] for r in b] for b in bs]
    sep = lambda x, y: any(x in b and y in b for b in ids) == False
    ok.append(("并发批次不拆对（t1/t2 分批·t3/t4 分批）", sep("t1", "t2") and sep("t3", "t4"), str(ids)))
    ok.append(("批内并发≤上限 3", all(len(b) <= 3 for b in bs), str([len(b) for b in bs])))
    ok.append(("只读可共享（同文件双读不冲突）", not conflicts([mk(1, "分析 reads=x.json"), mk(2, "统计 reads=x.json")]), ""))
    ok.append(("端口互斥", bool(conflicts([mk(1, "起服务 port=8080"), mk(2, "压测 port=8080")])), ""))
    ok.append(("同技能默认不冲突（task.conflict_skill=false）", not conflicts([mk(1, "步骤甲", "sk_a"), mk(2, "步骤乙", "sk_a")]), ""))
    SLEEP = 0.4
    res = run_rows([dict(r) for r in rows], lambda r: (time.sleep(SLEEP), r["id"])[1], limit=3, timeout=0, error_chain=False)
    serial = SLEEP * len(rows); par = SLEEP * len(bs)
    ok.append(("并行墙钟≈批内最大值（%.1fs＜串行 %.1fs）" % (res["wall_s"], serial), res["wall_s"] < serial * 0.75 and res["wall_s"] >= par * 0.8, "wall=%.2f batches=%d" % (res["wall_s"], len(bs))))
    be = batch_eta(rows, lambda r: 40000)
    ok.append(("eta 修正＝批内最大值求和（%ds ＜ 串行累加 %ds）" % (be // 1000, 40000 * len(rows) // 1000), be == 40000 * len(bs) and be < 40000 * len(rows), str(be)))
    bad = [mk(1, "好行 files=p1.txt"), mk(2, "炸行 files=p2.txt"), mk(3, "好行 files=p3.txt")]
    def boom(r):
        if "炸" in r["goal"]: raise RuntimeError("模拟行内异常")
        return "ok"
    r2 = run_rows(bad, boom, limit=3, timeout=0, error_chain=False)
    ok.append(("失败隔离（炸 1 行不影响同批其余）", r2["error"] == 1 and r2["done"] == 2 and [x["status"] for x in r2["results"]].count("done") == 2, str([(x["id"], x["status"]) for x in r2["results"]])))
    slow = [mk(1, "慢行 files=s1.txt"), mk(2, "快行 files=s2.txt")]
    r3 = run_rows(slow, lambda r: (time.sleep(1.2 if "慢" in r["goal"] else 0.1), "ok")[1], limit=2, timeout=0.3, error_chain=False)
    ok.append(("行级独立超时（慢行 timeout·快行 done）", r3["timeout"] == 1 and r3["done"] == 1, str([(x["id"], x["status"]) for x in r3["results"]])))
    p = os.path.join(tmp, "parallel_selftest.json")
    import json; open(p, "w", encoding="utf-8").write(json.dumps({"pass": all(x[1] for x in ok), "checks": [{"name": n, "ok": b, "detail": d} for n, b, d in ok], "wall_s": res["wall_s"], "serial_s": serial, "batches": ids}, ensure_ascii=False, indent=1))
    art.append(p)
    for n, b, d in ok: print(("  ✓ " if b else "  ✗ ") + n + (("｜" + d) if d and not b else ""))
    print("task_res selftest: " + ("OK" if all(x[1] for x in ok) else "FAIL") + "｜产物 " + p)
    return all(x[1] for x in ok)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "selftest": raise SystemExit(0 if selftest(a[1] if len(a) > 1 else "") else 1)
    if a and a[0] in ("check", "plan") and len(a) > 1:
        d, rs = _doc_rows(a[1])
        if not rs: print("无此表或表无行：" + a[1])
        elif a[0] == "check":
            cf = conflicts(rs); print(("无冲突——全部行可并发" if not cf else "冲突 %d 对：" % len(cf)) + "\n" + "\n".join("%s × %s %s" % (c["a"], c["b"], c["why"]) for c in cf) + "\n" + report(rs))
        else: print(report(rs))
    else: print(__doc__.strip().splitlines()[-1])
