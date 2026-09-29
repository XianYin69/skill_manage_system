#!/usr/bin/env python3
"""qq_push.py — QQ 主动推送（2026-09-29 用户「QQ 第三方 Agent 接入 SMS·只发送主要信息到我的 QQ」）：凭据 <SMS_HOME>/config/qq.json＝{appId,clientSecret,openid,enabled}（qq_bind.py 扫码写入）；发送＝POST https://api.bot.qq.com/v2/users/{openid}/messages {msg_type:0,content}＋Authorization: QQBot <token>（token 走 /app/getAppAccessToken，缓存 <SMS_HOME>/qq/token.json，提前 60s 重取）；口径＝只推 msg_flow CLASS∈{body,alert}（llm_out 模型正文/notice user_send/err 告警）＋模型提问＋做梦待批，思考 reasoning/工具 tool/代码 sh·edit/步骤 step·task/技能过程 skill 一律不推；护栏＝同文 60s 去重、最小间隔、日配额（官方 5qps·30qpm·单好友 1000/天），超限写 <SMS_HOME>/qq/outbox.json 不阻塞前台，对话收口 flush() 补发；异常一律静默并记 error 链，推送失败绝不影响数据流。函数：conf/ready/push/hook/flush/token/send；CLI 见 qq_cli.py。"""
import os, sys, json, time, urllib.request as U
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, msg_flow
API = "https://api.bot.qq.com"; DEF = {"enabled": True, "max_day": 400, "min_gap": 2.0, "max_len": 500, "dedup": 60}
def _f(sms, n): return os.path.join(sms, "qq", n)
_ld = lambda p, d=None: json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else d
def conf(sms=None):
    sms = sms or resolve_home.ensure(); c = _ld(os.path.join(sms, "config", "qq.json"), {}) or {}
    return dict(DEF, **{k: v for k, v in c.items() if not k.startswith("_")}, sms=sms)
def ready(c=None): c = c or conf(); return bool(c.get("appId") and c.get("clientSecret") and c.get("openid") and c.get("enabled"))
def _st(c): return _ld(_f(c["sms"], "state.json"), None) or {"day": "", "n": 0, "last": 0.0, "seen": {}}
def _wj(p, o): os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(o, open(p, "w", encoding="utf-8"))
def _ob(c, txt, why):
    rows = (_ld(_f(c["sms"], "outbox.json"), []) or []) + [{"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": txt, "why": why}]
    _wj(_f(c["sms"], "outbox.json"), rows[-80:])
def _post(url, body, tok=""):
    req = U.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **({"Authorization": "QQBot " + tok} if tok else {})})
    with U.urlopen(req, timeout=8) as r: return json.loads(r.read().decode("utf-8", "replace") or "{}")
def token(c):
    p, now = _f(c["sms"], "token.json"), time.time(); t = _ld(p, {}) or {}
    if t.get("token") and int(t.get("exp", 0)) - 60 > now: return t["token"]
    d = _post(API + "/app/getAppAccessToken", {"appId": c["appId"], "clientSecret": c["clientSecret"]})
    tk = d.get("access_token") or (d.get("data") or {}).get("access_token")
    if not tk: raise RuntimeError("token: " + json.dumps(d, ensure_ascii=False)[:160])
    _wj(p, {"token": tk, "exp": now + int(d.get("expires_in") or 3600)}); return tk
def send(c, text): return _post(API + "/v2/users/%s/messages" % c["openid"], {"msg_type": 0, "content": str(text)[:int(c["max_len"])]}, token(c))
def push(text, tag="SMS", c=None):
    try:
        c = c or conf(); text = " ".join(str(text or "").split())
        if not text or not ready(c): return None
        s, now, day = _st(c), time.time(), time.strftime("%Y%m%d")
        s = {"day": day, "n": 0, "last": 0.0, "seen": {}} if s.get("day") != day else s
        if now - float(s["seen"].get(text[:120]) or 0) < float(c["dedup"]): return "去重跳过"
        s["seen"] = {a: b for a, b in s["seen"].items() if now - float(b) < 600}; s["seen"][text[:120]] = now
        if int(s["n"]) >= int(c["max_day"]) or now - float(s.get("last") or 0) < float(c["min_gap"]): _ob(c, text, "配额/间隔"); return "已入outbox待补发"
        send(c, ("〔%s〕%s" % (tag, text))[:int(c["max_len"])]); s["last"], s["n"] = now, int(s["n"]) + 1; _wj(_f(c["sms"], "state.json"), s); return "已推送QQ"
    except Exception as e:
        try: import chain_error; chain_error.hook("gate", "qq_push", str(e)[:200])
        except Exception: pass
        return "推送失败（不影响数据流）：" + str(e)[:120]
def hook(e, c=None): return push(e.get("text"), "QQ·" + str(e.get("kind")), c) if msg_flow.cls(e.get("kind")) in ("body", "alert") else None
def flush(c=None):
    c = c or conf(); p = _f(c["sms"], "outbox.json"); rows = _ld(p, []) or []
    if not (ready(c) and rows): return None
    left = [r for r in rows[-10:] if push(r.get("text"), "QQ·补发", c) != "已推送QQ"]
    _wj(p, left) if left else os.remove(p); return "outbox 补发 %d/%d 条" % (len(rows) - len(left), len(rows))
