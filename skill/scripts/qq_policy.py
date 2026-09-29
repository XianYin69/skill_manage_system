#!/usr/bin/env python3
"""qq_policy.py — QQ 入站事件的解析与准入治理（2026-09-29 用户「我要发消息给你」；红线＝远程入口默认不得驱动本机）：parse(m) 把网关 op=0 事件规一为 {kind,msg_id,openid,text,user,att,t}——只认 C2C_MESSAGE_CREATE（d.author.user_openid·单聊）与 GROUP_AT_MESSAGE_CREATE（d.group_openid＋d.author.member_openid·群@），其余（READY/RESUMED/互动/审核/群管理）回 None 忽略；attachments 本版只计数不外传。
准入＝qq.json.allow 白名单（缺省＝绑定机主 openid 一人，陌生人静默丢弃并记 inbox 审计）；gate()＝默认只放行数据流话语与安全元指令（:qq/:dream/:repair/:status/:config/:help…），:sh、!、:restart、:shutdown、:grant、:dispatch 须 qq.json remote_admin=true 才放行，否则回「需授权」——避免 QQ 变成远程 shell。去重＝msg_id 落 <SMS_HOME>/qq/inbox.json（留 200 条），重连 RESUME 补发的旧消息不二次执行。用法：python -B qq_policy.py parse '<事件JSON>'|gate '<文本>'|inbox。"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qq_push as qp
EV = {"C2C_MESSAGE_CREATE": "user", "GROUP_AT_MESSAGE_CREATE": "group"}
SAFE = ("qq", "dream", "repair", "status", "help", "cmds", "config", "session", "task", "index", "skills", "chains", "resume", "debug", "space")
BLOCK = ("sh", "restart", "shutdown", "quit", "exit", "q", "edit", "view", "dispatch", "grant", "ws", "workspace")
def parse(m):
    t = str((m or {}).get("t") or ""); kind = EV.get(t)
    if not kind: return None
    d = (m or {}).get("d") or {}; a = d.get("author") or {}
    oid = str(a.get("user_openid") or a.get("member_openid") or "") or str(d.get("group_openid") or "")
    return {"kind": kind, "msg_id": str(d.get("id") or ""), "openid": oid, "text": str(d.get("content") or "").strip(),
            "user": str(a.get("username") or ""), "att": len(d.get("attachments") or []), "t": t}
def _ip(c=None): return os.path.join((c or qp.conf())["sms"], "qq", "inbox.json")
def inbox(c=None):
    try: return qp._ld(_ip(c), []) or []
    except Exception: return []
def seen(mid, c=None): return any(r.get("id") == mid for r in inbox(c))
def mark(mid, e, c=None):
    c = c or qp.conf(); rows = inbox(c) + [{"id": mid, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": e.get("kind"),
            "openid": e.get("openid"), "text": str(e.get("text"))[:160], "t": e.get("t")}]
    qp._wj(_ip(c), rows[-200:]); return len(rows)
def allowed(e, c=None):
    c = c or qp.conf(); al = [x for x in (c.get("allow") or [c.get("openid")]) if x]
    return (not al) or e.get("openid") in al
def gate(text, c=None):
    c = c or qp.conf(); t = str(text or "").strip()
    if not t: return False, "空消息"
    if t[:1] in (":", "：", "!"):
        k = (t.lstrip(":：!").split() or [""])[0].lower()
        if c.get("remote_admin"): return True, ""
        if k in BLOCK: return False, "远程默认禁止 :" + k + "（qq.json 设 remote_admin=true 开启）"
        if k not in SAFE: return False, "远程仅放行安全元指令（:" + "、:".join(SAFE[:6]) + "…），:" + k + " 需 remote_admin"
    return True, ""
if __name__ == "__main__":
    a = sys.argv[1:] or ["inbox"]
    print(json.dumps(inbox()[-6:], ensure_ascii=False, indent=1) if a[0] == "inbox"
          else json.dumps(parse(json.loads(a[1])), ensure_ascii=False) if a[0] == "parse" and len(a) > 1
          else json.dumps(gate(" ".join(a[1:])), ensure_ascii=False) if a[0] == "gate" else __doc__.strip()[:300])
