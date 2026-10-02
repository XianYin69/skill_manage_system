#!/usr/bin/env python3
"""solo.py — SOLO 模式唯一真源（权限免用户确认·缺权限时由大模型自审决定是否授予）：cfg/enabled/auto_pending/never/set/banner_lines/status/review/allow/gate/granted_today/notice；auto_pending＝SOLO 开且 solo.auto_pending（默认 true）时对「做梦修复待批」视同用户已同意，空闲自动续跑（dream_pending.auto_solo）；自审 danger 授予范围＝用户明确要求的 skill 目录改动，或用户明确要求的 git 写操作（commit/merge/push/branch 删除等·非强推非改写已推送历史）；review 经 gateway._req 非流式、不带 tools 的单次判定（prompt 含〔键/工具/目标/意图/本轮用户话语摘要/风险摘要〕，只回一行 JSON {"grant","ttl_min","reason"}），网关未启用/调用失败/不可解析/异常一律保守拒绝（绝不因审核失败放行）；allow 顺序＝已授予即真→SOLO 关即假→solo.never 键永不自审→danger 未开 solo.allow_danger 不自审→自审通过才 permissions.apply(grant, ttl 钳 max_ttl_min) 并落 audit（solo 标记）＋event 链；gate 回 (bool, note) 供工具层拼拒绝文案。红线：SOLO 只改「权限准入」，不绕 stop_channel/任务表/审计，自审授予可 :grant revoke <键> 即时收回（注意 :grant <键> 0＝永久授予、非收回）；后台与非交互路径（auto_compress/cache_cleanup/dep_fetch/dream_*/deploy 等）不经本模块，防做梦链路阻塞与成本失控；SOLO 关闭＝行为与今天逐字一致。批28：err_sig＝分类前缀＋全串归一哈希签名（不截断头部，同错必同签、异错必不同签），err_count＝模块级跨调用同错计数（solo.retry_ttl_sec 默认 300s 过期自动清、成功一轮 reset 清零），修「同错熔断形同虚设＋跨轮计数清零」；自检 python -B solo.py check。用法：python -B solo.py status|on|off|banner|review <key> [ctx]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings, permissions, chains
SMS = resolve_home.ensure()
NEVER = ("remote",)
RISK = ("无人确认：缺权限时不再询问用户，由大模型自审判定即执行",
        "自审可放行 skill 目录写入——仅 solo.allow_danger=true 时（红线16·默认 false 仍须当轮 :grant danger）",
        "solo.never 列内键（默认 remote）永不自审",
        "误判不可逆：授予即生效并可能被后续工具立即使用",
        "全部自审授予落 permissions.json audit（solo 标记）＋event 链，可追溯可收回",
        "随时关闭：:solo off 或 F4 改 solo.enabled=false；单项收回：:grant revoke <键>（:grant <键> 0＝永久授予非收回）")
def cfg(): return settings.get("solo") or {}
def enabled(): return bool(cfg().get("enabled"))
def auto_pending():
    """SOLO 下「自动同意修复待批」（配置 solo.auto_pending·默认 true）：开关开且 SOLO 开才为真。
    供 dream_repair.blocked 视同用户已同意、dream_pending.auto_solo 空闲时逐条续跑；SOLO 关＝恒假零回归。"""
    try: return bool(cfg().get("auto_pending", True) and enabled())
    except Exception: return False
def never(): return tuple(cfg().get("never") or NEVER)
def banner_lines(): return "\n".join("· " + x for x in RISK)
def set(on):
    """开关（写 config solo.enabled）：开启即回风险提示文案（供主输出窗口/菜单打印）。"""
    on = bool(on); settings.set("solo.enabled", on)
    return ("── SOLO 模式已开启 ──\n权限不再向用户确认，缺权限时由大模型自审决定是否授予。风险须知：\n" + banner_lines()) if on \
        else "SOLO 模式已关闭——权限准入回到用户确认（:grant），与未启用 SOLO 时逐字一致"
def _utter():
    """本轮用户话语摘要（user 链最新碎片·取不到＝空串，绝不因缺上下文阻断审核）。"""
    try:
        fs = [f for f in chains.store().all_frags("user") if (f or {}).get("text")]
        return sorted(fs, key=lambda f: f.get("ts", ""))[-1].get("text", "")[:300] if fs else ""
    except Exception: return ""
def _jsonline(txt):
    """从回复里取第一个 JSON 对象（模型多话也容得下·解不出＝None→上层保守拒绝）。"""
    s = str(txt or ""); i = s.find("{")
    if i < 0: return None
    try: return json.loads(s[i:s.rfind("}") + 1])
    except Exception: return None
def review(key, ctx=None):
    """LLM 自审：回 (grant, reason, ttl_min)。网关未启用/调用失败/不可解析/异常一律 (False, 原因, 0)——审核失败绝不放行。"""
    c = cfg(); ctx = ctx or {}
    try:
        import gateway
        if not gateway.enabled(): return False, "网关未启用（llm_gateway.enabled=false），无法自审", 0
        gc = gateway.cfg()
        sysp = ('你是 SMS SOLO 权限自审器：判断本次工具调用是否应授予权限键。只回一行 JSON：'
                '{"grant":true|false,"ttl_min":整数,"reason":"≤40字中文理由"}。原则：与本轮用户诉求直接相关且最小必要才授予；'
                '破坏性/不可逆/越权/与诉求无关/意图不明＝拒绝；danger 仅限用户明确要求的 skill 目录改动，'
                '〔工具〕为 dream_repair 且 SOLO 开（auto_pending）时，修复待批续跑＝用户已预先同意该 skill/脚本修复性改动，属可授予范围（给最小 TTL）；'
                '或用户明确要求的 git 写操作（commit/merge/push/branch 删除等·非强推、非改写已推送历史）；never 列内键不得授予。'
                'never 列内是 SMS 权限键名（remote＝远程会话越权执行元指令的键），'
                '与 git remote、网络推送、GitHub 无关；用户明确要求的 git commit/merge/push '
                '不得以 remote 键为由拒绝。')
        usr = "\n".join(["〔键〕" + str(key), "〔工具〕" + str(ctx.get("tool") or "-"),
                         "〔目标〕" + str(ctx.get("path") or ctx.get("url") or ctx.get("target") or "-"),
                         "〔意图〕" + str(ctx.get("intent") or "-"),
                         "〔本轮用户话语摘要〕" + (_utter() or "-"),
                         "〔风险摘要〕" + banner_lines().replace("\n", "；"),
                         "〔永不自审权限键（非 git remote）〕" + "、".join(never()),
                         "〔allow_danger〕" + str(bool(c.get("allow_danger"))), "〔已授予键〕" + "、".join(sorted(k for k in permissions.KEYS if permissions.allow_base(SMS, k)))])
        data, err = gateway._req("/chat/completions", {"model": gc.get("model") or "auto",
            "messages": [{"role": "system", "content": sysp}, {"role": "user", "content": usr}],
            "max_tokens": int(c.get("review_max_tokens", 200)), "temperature": 0})
        if not data: return False, "自审网关调用失败：" + str(err)[:80], 0
        txt = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        j = _jsonline(txt)
        if not isinstance(j, dict) or not isinstance(j.get("grant"), bool):
            return False, "自审回复不可解析（须 JSON·grant 为布尔）：" + str(txt)[:60], 0
        return bool(j["grant"]), str(j.get("reason") or "（未给理由）")[:120], int(j.get("ttl_min") or 0)
    except Exception as e: return False, "自审异常：" + str(e)[:100], 0
def _mark(sms, key, reason):
    """给本次自审授予的 audit 末条打 solo 标记与理由（审计可追溯·失败不影响授予结果）。"""
    try:
        import atomic_io
        p = permissions._path(sms); d = permissions._doc(p, sms)
        for a in reversed(d.get("audit") or []):
            if a.get("action") == "grant" and a.get("key") == key: a["solo"] = True; a["reason"] = reason; break
        atomic_io.wjson(p, d); return True
    except Exception: return False
def notice(text):
    """主输出窗口通报一行（SOLO 自审放行/拒绝上屏）：solo.notify=false 即静默；惰性 import agent_ctx/msg_flow
    防循环依赖，信封机制同 agent_tools.emit（kind=notice＝msg_flow CLASS body，主输出可见）；全程 try/except，
    异常只回 False——绝不影响权限判定与工具执行。"""
    if not cfg().get("notify", True): return False
    try:
        import agent_ctx, msg_flow
        c = agent_ctx.cur()
        e = msg_flow.make("notice", str(text), conv=c.get("conv") or chains.ACTIVE["conv"],
                          sess=chains.cur_sess(), tool="solo", ok=True)
        if callable(c.get("ev")): c["ev"](e)
        ln = c.get("on_line")
        if ln: ln(msg_flow.brief(e))
        return True
    except Exception: return False
def _decide(sms, key, ctx=None):
    """自审决策核心（allow/gate 共用·一次判定一次落账）：回 (grant, reason)。never 键与未开 allow_danger 的 danger 不送审；
    审核通过即 permissions.apply(grant, ttl 钳 max_ttl_min)＋audit 打 solo 标记＋event 链，可 :grant revoke <键> 收回。"""
    if str(key) in never(): return False, "键 %s 在 solo.never 列内永不自审" % key
    if str(key) == "danger" and not cfg().get("allow_danger"): return False, "danger 不随自审（须 solo.allow_danger=true 或当轮 :grant danger）"
    g, why, ttl = review(key, ctx)
    if not g:
        chains.record("event", "SOLO自审拒绝 key=%s 理由=%s" % (key, why)); notice("SOLO 自审拒绝 %s：%s" % (key, why)); return False, why
    c = cfg(); t2 = min(ttl or int(c.get("ttl_min", 30)), int(c.get("max_ttl_min", 120)))
    permissions.apply(sms, "grant", str(key), False, t2); _mark(sms, str(key), why)
    chains.record("event", "SOLO自审授予 key=%s ttl=%d分钟 理由=%s" % (key, t2, why)); notice("SOLO 自审放行 %s（ttl=%d分钟）：%s" % (key, t2, why)); return True, why
def allow(sms, key, id=None, ctx=None):
    """准入判定（布尔版）：已授予即真；SOLO 关即假；否则走自审（通过即落授予）。"""
    if permissions.allow_base(sms, key, id): return True
    if not enabled(): return False
    return _decide(sms, key, ctx)[0]
def gate(sms, key, ctx=None):
    """(是否放行, 说明)：SOLO 关＝(False,「需 :grant <key>」) 与今天逐字一致；SOLO 开＝拒绝原因给到用户可见。"""
    if permissions.allow_base(sms, key, (ctx or {}).get("id")): return True, ""
    if not enabled(): return False, "需 :grant " + str(key)
    g, why = _decide(sms, key, ctx); return (True, "") if g else (False, "SOLO 自审判定不予授予：" + why)
def tail(note):
    """拒绝文案尾部拼接：SOLO 关（note＝原文案「需 :grant ..」）＝空串保零回归；SOLO 开＝拼「（SOLO 自审：..）」，
    理由自带全角括号时改用〔〕包裹，避免括号套括号影响可读性。"""
    if not note or note.startswith("需 :grant"): return ""
    o, c = ("〔", "〕") if "（" in note else ("（", "）")
    return o + note + c
def granted_today(sms=None):
    """今日 SOLO 自审授予条数（permissions.json audit 中带 solo 标记者）。"""
    try:
        d = permissions._doc(permissions._path(sms or SMS), sms or SMS)
        return sum(1 for a in (d.get("audit") or []) if a.get("action") == "grant" and a.get("solo"))
    except Exception: return 0

def _gw_ok():
    try:
        import gateway; return bool(gateway.enabled())
    except Exception: return False
# ---- 批27 SOLO 故障分析（用户：SOLO 下重试无限但有条件——阻塞/错误后大模型必须先分析，分析后才决定修复还是重试）
import re as _re, hashlib as _hashlib
def analyze_on():
    """分析闸：SOLO 开＋solo.analyze_retry＋非后台非交互（做梦/压缩等无人应答链路不入此路）。"""
    try: return bool(enabled() and cfg().get("analyze_retry", True) and not permissions._NONINTERACTIVE[0])
    except Exception: return False
def retry_cfg():
    c = cfg(); return {"max_same": int(c.get("max_same_error", 5)), "cap": float(c.get("retry_backoff_cap", 30.0))}
_VOL_UUID = _re.compile(r"\b[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
_VOL_HEX = _re.compile(r"\b[0-9a-fA-F]{8,}\b")
_VOL_Q = _re.compile(r'(["\'])(.{40,}?)\1', _re.S)
_CLS = _re.compile(r"\b([A-Za-z0-9_]*(?:Error|Exception|Timeout|Failure))\b")
_CODE = (_re.compile(r"HTTP Error (\d{3})"), _re.compile(r"Error code:?\s*(\d{3})"),
         _re.compile(r'"(?:code|status)"\s*:\s*"?(\d{3})'))
_ETYPE = _re.compile(r'"(?:type|error_code)"\s*:\s*"?([A-Za-z][A-Za-z0-9_.\-]{2,})')


def _norm_err(s):
    """全串易变归一（不截断头部）：uuid/长十六进制→H、引号内长文本只留前 40 字、数字→N、空白折叠。"""
    s = _VOL_UUID.sub("H", s)
    s = _VOL_HEX.sub("H", s)
    s = _VOL_Q.sub(lambda m: m.group(1) + m.group(2)[:40] + m.group(1), s)
    s = _re.sub(r"\d+", "N", s)
    return _re.sub(r"\s+", " ", s).strip()


def _classify(s):
    """分类前缀＝异常类名 + 状态码（HTTP Error NNN / Error code: NNN / JSON "code"），
    抽不到码退 JSON error.type 字符串；前缀只增辨识度，判同仍靠全串哈希。"""
    m = _CLS.search(s)
    cls = m.group(1) if m else ""
    code = ""
    for rx in _CODE:
        mm = rx.search(s)
        if mm:
            code = mm.group(1)
            break
    if not code:
        mm = _ETYPE.search(s)
        code = mm.group(1) if mm else ""
    return cls, code


def err_sig(err):
    """批28 签名＝分类前缀 + 完整串归一哈希（sha1[:12]）。旧实现先归一数字再截断 160 字符：长错误
    （gateway._send 回 str(e)[:150]+" "+body[:300]）尾部差异被截掉致异错塌缩同签，易变量落在保留区
    又致同错签名漂移——same 恒为 1 令 solo.max_same_error 熔断形同虚设。现不截断，同错必同签。"""
    s = str(err or "")
    cls, code = _classify(s)
    h = _hashlib.sha1(_norm_err(s).encode("utf-8", "replace")).hexdigest()[:12]
    return ":".join([x for x in (cls, code) if x] + [h])


_SIG_COUNT = {}


def _ttl():
    """同错计数存活秒数（solo.retry_ttl_sec·默认 300）：超时自动过期，防陈旧计数误熔断。"""
    try:
        return float(cfg().get("retry_ttl_sec", 300) or 300)
    except Exception:
        return 300.0


def err_count(err=None, reset=False):
    """跨调用同错计数（批28·模块级存活）：gateway.run 旧版局部 same 每次调用即清零，400 投毒每轮
    只计到 1＝无限烧 token。reset=True（拿到有效响应/成功一轮）＝全清；err=None 且非 reset＝回快照；
    否则按 err_sig 累计并回本次次数（超 TTL 则从 1 重计）。solo.on_error 入参语义不变。"""
    now = time.time()
    if reset:
        _SIG_COUNT.clear()
        return 0
    if err is None:
        return dict((k, v[0]) for k, v in _SIG_COUNT.items())
    sg = err_sig(err)
    prev = _SIG_COUNT.get(sg)
    n = (prev[0] if prev and now - prev[1] <= _ttl() else 0) + 1
    _SIG_COUNT[sg] = (n, now)
    return n


def reset_sig():
    """清空同错计数（成功一轮的显式入口·等价 err_count(reset=True)）。"""
    return err_count(reset=True)
def _ajson(txt):
    s = str(txt or ""); i = s.find("{")
    if i < 0: return None
    try: return json.loads(s[i:s.rfind("}") + 1])
    except Exception: return None

def analyze(kind, detail, ctx=None):
    """故障分析器（非流式单次·不带 tools）：回 {"decision":"retry|fix|abort","reason","action"}；
    网关未启用/调用失败/不可解析/异常＝None——上层据此回退旧的有限重试，绝不因分析失败而盲目放行或死循环。"""
    c = cfg(); ctx = ctx or {}
    try:
        import gateway
        if not gateway.enabled(): return None
        gc = gateway.cfg()
        sysp = ("你是 SMS SOLO 故障分析器：对刚发生的阻塞/错误先做根因分析，再决定下一步。只回一行 JSON："
                '{"decision":"retry|fix|abort","reason":"≤40字根因","action":"≤80字给主模型的修复指令（retry 时可空）"}。'
                "原则：必须先分析后决定，禁止未分析就原样重试。瞬时性（网络抖动/超时/429/5xx/空响应）且首次出现＝retry；"
                "同类错误重复出现＝不得原样重试，必须 fix（换参数/换路径/换技能/拆步/降级）；权限缺失＝fix（先申请或改走不需该权限的路）；"
                "不可恢复（认证失败/内容安全/目标不存在且无法创建/诉求本身矛盾）＝abort。")
        usr = "\n".join(["〔类别〕" + str(kind), "〔错误/阻塞详情〕" + str(detail)[:600],
                         "〔同签名连续次数〕" + str(ctx.get("same", 1)), "〔连续续推次数〕" + str(ctx.get("idle", 0)),
                         "〔任务表未完成〕" + str(ctx.get("pend") or "-")[:600],
                         "〔本轮用户话语摘要〕" + (_utter() or "-")])
        data, err = gateway._req("/chat/completions", {"model": gc.get("model") or "auto",
            "messages": [{"role": "system", "content": sysp}, {"role": "user", "content": usr}],
            "max_tokens": int(c.get("analyze_max_tokens", 300)), "temperature": 0})
        if not data: chains.record("event", "SOLO故障分析不可用：" + str(err)[:80]); return None
        j = _ajson(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        if not isinstance(j, dict) or str(j.get("decision")) not in ("retry", "fix", "abort"):
            chains.record("event", "SOLO故障分析回复不可解析：" + str(j)[:60]); return None
        out = {"decision": str(j["decision"]), "reason": str(j.get("reason") or "")[:160],
               "action": str(j.get("action") or "")[:300]}
        chains.record("event", "SOLO故障分析 %s→%s：%s" % (kind, out["decision"], out["reason"]))
        notice("SOLO 分析（%s）→ %s：%s" % (kind, out["decision"], out["reason"]))
        return out
    except Exception as e:
        chains.record("event", "SOLO故障分析异常：" + str(e)[:100]); return None

def on_error(err, same, kind="llm"):
    """run() 错误口决策（批27）：分析闸未开＝("legacy", None) 与旧行为逐字一致；开＝先分析后决定
    ("retry",d)/("fix",d)/("abort",d)。硬条件：同签名连续超 solo.max_same_error 直接 abort——
    「无限重试」的边界是「有进展」，无进展即停，防死循环烧钱。"""
    try:
        if not analyze_on(): return "legacy", None
        if same > retry_cfg()["max_same"]:
            return "abort", {"decision": "abort", "reason": "同类错误已连续第 %d 次（solo.max_same_error=%d）·分析后仍无进展" % (same, retry_cfg()["max_same"]), "action": ""}
        d = analyze(kind, err, {"same": same})
        if not d: return "legacy", None
        return (d["decision"], d)
    except Exception: return "legacy", None
def continue_gate(kind, idle, pend=""):
    """主流程守卫熔断的 SOLO 分支：闸未开＝(False,None) 上层按旧 task.max_continue 收口；
    开＝分析后决定继续（retry/fix 带修复指令注入）或中止。回 (是否继续, d)。"""
    try:
        if not analyze_on(): return False, None
        d = analyze("stall", "主流程守卫连续续推第 %d 次（kind=%s）仍未收口" % (idle, kind), {"idle": idle, "same": idle, "pend": pend})
        if not d or d["decision"] == "abort": return False, d
        return True, d
    except Exception: return False, None
def status(sms=None):
    sms = sms or SMS; c = cfg()
    return {"enabled": bool(c.get("enabled")), "allow_danger": bool(c.get("allow_danger")),
            "auto_pending": auto_pending(), "never": list(never()),
            "ttl_min": int(c.get("ttl_min", 30)), "max_ttl_min": int(c.get("max_ttl_min", 120)),
            "notify": bool(c.get("notify", True)), "gateway_ok": _gw_ok(), "granted_today": granted_today(sms)}
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; k = a[0]
    if k == "on": print(set(True))
    elif k == "off": print(set(False))
    elif k == "banner": print(banner_lines())
    elif k == "review":
        g, why, ttl = review(a[1] if len(a) > 1 else "write", {"tool": "cli", "target": " ".join(a[2:]) or "-"})
        print(json.dumps({"grant": g, "reason": why, "ttl_min": ttl}, ensure_ascii=False))
    elif k == "check":
        e4 = ('HTTP Error 400: Bad Request {"error": {"message": "This model maximum context length '
              'is 8192 tokens, however you requested 9000 tokens (index=17, offset=4201)", "type": '
              '"invalid_request_error"}, "id": "chatcmpl-1a2b3c4d5e6f7a8b9c0d"}')
        mx = retry_cfg()["max_same"]; reps = max(6, mx + 1)
        sigs = [err_sig(e4) for _ in range(reps)]
        uniq = list(dict.fromkeys(sigs))
        assert len(uniq) == 1, "同错签名漂移：%s" % uniq
        ns = [err_count(e4) for _ in range(reps)]
        assert ns == list(range(1, reps + 1)), "计数未递增：%s" % ns
        assert ns[-1] > mx, "未达熔断阈值：%s>%s" % (ns[-1], mx)
        s401 = err_sig(e4.replace("400", "401"))
        soth = err_sig(e4.replace("maximum context", "content policy"))
        assert s401 != sigs[0], "400/401 塌缩同签"
        assert soth != sigs[0], "同码异文塌缩同签"
        assert err_count(reset=True) == 0 and err_count(e4) == 1, "reset 未清零"
        _SIG_COUNT[sigs[0]] = (9, time.time() - _ttl() - 1)
        assert err_count(e4) == 1, "TTL 未过期"
        err_count(reset=True)
        print(json.dumps({"check": "pass", "sig": sigs[0], "counts": ns, "max_same": mx,
                          "ttl_sec": _ttl(), "sig_401": s401, "sig_other": soth},
                         ensure_ascii=False, indent=2))
    elif k == "allow":
        print(json.dumps({"allow": allow(SMS, a[1] if len(a) > 1 else "write", ctx={"tool": "cli", "target": " ".join(a[2:]) or "-"}), "status": status()}, ensure_ascii=False))
    else: print(json.dumps(status(), ensure_ascii=False, indent=2))
