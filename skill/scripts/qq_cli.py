#!/usr/bin/env python3
"""qq_cli.py — QQ 推送的命令行入口与绑定编排（2026-09-29）：bind [source]＝qq_bindflow 发起扫码（task 约 2 分钟过期→默认 180s×3 轮自动换新码·弱网退避重试），成功后写 <SMS_HOME>/config/qq.json（旧值 .bak·chmod 600）；resume＝读 bind_pending.json 对上次扫码续握手（免重扫·手机页面卡「连接中」时用）；check＝只取 getAppAccessToken 的链路自检（不发消息·不占日配额·报耗时，用来分清「凭据错」还是「网卡」）；手工录入 --appid/--secret/--openid（开放平台管理端可见，绕过扫码）；status＝配置/凭据/今日已推/outbox 积压一览（密钥打码）；test "<文本>"＝真发一条；on/off＝开关；conf k=v＝改阈值（max_day/min_gap/max_len/dedup）；flush＝补发 outbox（对话收口自动调，也可手跑）；open [create]＝webbrowser 打开开放平台机器人列表/快捷创建登录页（零新依赖，登录后管理端可见 appId/clientSecret，配合手工录入）。bind/resume/check 的编排在 qq_bindflow.py（慢网加固：task 约 2 分钟即过期→默认 180s×3 轮自动换新码；resume 读 bind_pending.json 免重扫续握手；check 只取 token 自检·不占日配额）。用法：python -B qq_cli.py bind|resume|check|status|test|on|off|conf|flush|open|listen|unlisten|lstatus|linbox [参数]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, qq_push as qp, qq_bindflow as qf
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
    if a[0] in ("bind", "resume"): p, m = (qf.bind((a[1] if len(a) > 1 and not a[1].startswith("--") else "") or "SMS", int(opt("--timeout", 180)), int(opt("--rounds", 3))) if a[0] == "bind" else qf.resume(int(opt("--timeout", 180)))); print(m + ("·" + p if p else ""))
    elif a[0] == "check": print(json.dumps(qf.check(), ensure_ascii=False, indent=1))
    elif a[0] == "test": print(qp.push(" ".join(a[1:]) or "SMS 测试推送：链路可用", "测试"))
    elif a[0] == "flush": print(qp.flush() or "outbox 无积压或未绑定")
    elif a[0] == "listen": print(__import__("qq_listen").spawn())
    elif a[0] == "unlisten": print(__import__("qq_listen").stop())
    elif a[0] == "lstatus": print(json.dumps(__import__("qq_watch").status(), ensure_ascii=False, indent=1))
    elif a[0] == "linbox": print(json.dumps(__import__("qq_policy").inbox()[-8:], ensure_ascii=False, indent=1))
    elif a[0] == "conf" and len(a) > 1: print(json.dumps(conf_set(a[1]), ensure_ascii=False))
    elif a[0] in ("on", "off"): print(toggle(a[0] == "on"))
    elif a[0] == "open": import webbrowser; u = {"create": "https://q.qq.com/qqbot/openclaw/login.html"}.get(a[1] if len(a) > 1 else "", "https://q.qq.com/qqbot/openclaw/index.html"); webbrowser.open(u); print("已调用系统浏览器打开：" + u + ("（登录后到「机器人管理」复制 AppID/AppSecret 回填 :qq --appid/--secret/--openid）" if u.endswith("login.html") else ""))
    elif opt("--appid"): print("已手工录入：" + qf.save(opt("--appid"), opt("--secret"), opt("--openid")))
    else: print(json.dumps(status(), ensure_ascii=False, indent=1))
