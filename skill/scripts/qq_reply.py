#!/usr/bin/env python3
"""qq_reply.py — 入站消息「回到原聊天线程」的被动回复（2026-09-29 用户「我要发消息给你」）：官方文档实测——同一 messages 接口多带 msg_id 即**被动回复**（msg_id 取自 C2C_MESSAGE_CREATE/GROUP_AT_MESSAGE_CREATE 的 d.id、**5 分钟内有效**、不占主动消息 1000 条/天配额），故入站对话的答案走被动、显示在原会话；本模块只存一次性上下文 CTX＝{msg_id,openid,kind,exp}，端点按 kind 选：user→/v2/users/{openid}/messages、group→/v2/groups/{group_openid}/messages；ttl 默认 280s 留 20s 余量防边界过期。qq_push.send 先问 try_send：命中就发被动，失败（过期/频控/无权限）自动清上下文回 None，qq_push 随即回落主动推送——两条都失败才由 qq_push 吞异常记 error 链，绝不影响数据流。与 qq_push 互为延迟 import（qq_push.send 内 import 本模块·本模块函数内 import qq_push）避免循环依赖。用法：python -B qq_reply.py state|set <msg_id> [openid] [user|group]|send "<文本>"|clear。"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
API = "https://api.bot.qq.com"
CTX = {}
def set_reply(msg_id="", openid="", kind="user", ttl=280):
    CTX.clear(); CTX.update({"msg_id": str(msg_id or ""), "openid": str(openid or ""), "kind": kind or "user", "exp": time.time() + float(ttl)}); return dict(CTX)
def clear(): CTX.clear()
def live(): return bool(CTX.get("msg_id")) and time.time() < float(CTX.get("exp") or 0)
def _ep(kind, oid): return API + "/v2/%s/%s/messages" % ("groups" if str(kind) == "group" else "users", oid)
def try_send(c, text):
    """有未过期 msg_id 就被动回复；失败清上下文回 None（qq_push 回落主动推送）。"""
    if not live(): return None
    mid, kind = CTX["msg_id"], CTX.get("kind") or "user"
    import qq_push as qp
    for oid in [x for x in (CTX.get("openid"), c.get("openid")) if x]:
        try:
            d = qp._post(_ep(kind, oid), {"msg_type": 0, "content": str(text)[:int(c["max_len"])], "msg_id": mid}, qp.token(c))
            if int(d.get("code") or 0): continue
            return d
        except Exception: continue
    clear(); return None
if __name__ == "__main__":
    import qq_push as qp
    a = sys.argv[1:] or ["state"]; c = qp.conf()
    print(json.dumps({"ctx": dict(CTX), "live": live(), "ready": qp.ready(c)}, ensure_ascii=False) if a[0] == "state"
          else str(set_reply(a[1], a[2] if len(a) > 2 else "", a[3] if len(a) > 3 else "user")) if a[0] == "set"
          else str(try_send(c, " ".join(a[1:]) or "SMS 被动回复自测") or "无上下文或被动失效（回落主动）") if a[0] == "send"
          else str(clear()) if a[0] == "clear" else __doc__.strip()[:300])
