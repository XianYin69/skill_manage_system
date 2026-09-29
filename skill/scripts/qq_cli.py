#!/usr/bin/env python3
"""qq_cli.py — QQ 推送的命令行入口与绑定编排（2026-09-29）：bind [source]＝调 qq_bind 协议发起扫码（回执自带 user_openid），成功后写 <SMS_HOME>/config/qq.json（旧值 .bak·chmod 600）；手工录入 --appid/--secret/--openid（开放平台管理端可见，绕过扫码）；status＝配置/凭据/今日已推/outbox 积压一览（密钥打码）；test "<文本>"＝真发一条；on/off＝开关；conf k=v＝改阈值（max_day/min_gap/max_len/dedup）；flush＝补发 outbox（对话收口自动调，也可手跑）；open [create]＝webbrowser 打开开放平台机器人列表/快捷创建登录页（零新依赖，登录后管理端可见 appId/clientSecret，配合手工录入）。用法：python -B qq_cli.py bind|status|test|on|off|conf|flush|open [参数]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, qq_bind as qb, qq_push as qp
def save(appid, secret, openid, sms=None):
    sms = sms or resolve_home.ensure(); p = os.path.join(sms, "config", "qq.json")
    if os.path.isfile(p):
        try: open(p + ".bak", "w", encoding="utf-8").write(open(p, encoding="utf-8").read())
        except Exception: pass
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"appId": appid, "clientSecret": secret, "openid": openid, "enabled": True,
               "bound": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try: os.chmod(p, 0o600)
    except Exception: pass
    return p
def bind(source="", timeout=300):
    key = qb.genkey(); tid = qb.create(key); u = qb.qurl(tid, source)
    print(qb.show(u)); print("扫码链接：" + u); t0 = time.time()
    while time.time() - t0 < timeout:
        try: st, appid, sec, oid = qb.poll(tid)
        except Exception as e: print("轮询异常（重试）：" + str(e)[:80]); time.sleep(2); continue
        if st == 2 and appid and sec: return save(appid, qb.decrypt(sec, key), oid), "绑定成功 openid=" + (oid or "-")
        if st == 3: return None, "二维码已过期——重跑 bind 即可（换新任务号）"
        time.sleep(2)
    return None, "超时未完成绑定（可重跑，或用 --appid/--secret/--openid 手工录入）"
def mask(v): return (str(v)[:4] + "****" + str(v)[-3:]) if v and len(str(v)) > 8 else ("未设置" if not v else "****")
def status():
    c = qp.conf(); s = qp._st(c); ob = qp._ld(qp._f(c["sms"], "outbox.json"), []) or []
    return {"已绑定": bool(c.get("appId") and c.get("openid")), "开关": "on" if c.get("enabled") else "off",
            "appId": c.get("appId") or "-", "clientSecret": mask(c.get("clientSecret")), "openid": c.get("openid") or "-",
            "今日已推": s.get("n", 0), "日上限": c["max_day"], "outbox积压": len(ob), "阈值": {k: c[k] for k in ("min_gap", "max_len", "dedup")}}
def toggle(on):
    p = os.path.join(resolve_home.ensure(), "config", "qq.json"); d = qp._ld(p, {}) or {}
    d["enabled"] = bool(on); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); return "QQ 推送：" + ("开" if on else "关")
def conf_set(kv):
    p = os.path.join(resolve_home.ensure(), "config", "qq.json"); d = qp._ld(p, {}) or {}
    k, _, v = str(kv).partition("="); v = v.strip().strip('"')
    d[k] = {"true": True, "false": False}.get(v.lower(), int(v) if v.isdigit() else (float(v) if v.replace(".", "").isdigit() else v))
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); return {k: d[k]}
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; opt = lambda k, d="": sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    if a[0] == "bind": p, m = bind((a[1] if len(a) > 1 and not a[1].startswith("--") else "") or "SMS", int(opt("--timeout", 300))); print(m + ("·" + p if p else ""))
    elif a[0] == "test": print(qp.push(" ".join(a[1:]) or "SMS 测试推送：链路可用", "测试"))
    elif a[0] == "flush": print(qp.flush() or "outbox 无积压或未绑定")
    elif a[0] == "conf" and len(a) > 1: print(json.dumps(conf_set(a[1]), ensure_ascii=False))
    elif a[0] in ("on", "off"): print(toggle(a[0] == "on"))
    elif a[0] == "open": import webbrowser; u = {"create": "https://q.qq.com/qqbot/openclaw/login.html"}.get(a[1] if len(a) > 1 else "", "https://q.qq.com/qqbot/openclaw/index.html"); webbrowser.open(u); print("已调用系统浏览器打开：" + u + ("（登录后到「机器人管理」复制 AppID/AppSecret 回填 :qq --appid/--secret/--openid）" if u.endswith("login.html") else ""))
    elif opt("--appid"): print("已手工录入：" + save(opt("--appid"), opt("--secret"), opt("--openid")))
    else: print(json.dumps(status(), ensure_ascii=False, indent=1))
