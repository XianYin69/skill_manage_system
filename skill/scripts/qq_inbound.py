#!/usr/bin/env python3
"""qq_inbound.py — QQ 入站消息的派发（2026-09-29 用户「我要发消息给你」；解析与准入在 qq_policy，回复通道在 qq_reply，长连接在 qq_session，本模块只做「一条消息 → 一次 SMS 对话 → 回到原会话」）：handle(m) 顺序＝parse → allowed（非白名单只记审计不外泄本机状态）→ seen（RESUME 补发去重）→ gate（安全元指令白名单）→ mark → deliver；deliver 先 qq_reply.set_reply(msg_id, openid, kind) 置被动回复上下文，再分两路——① 以 : ／ ! 开头＝元指令：经 shell_core.handle 执行并把可见行合并成一条回发（tag QQ·指令）；② 普通话语＝交 agent_stream.ask 走完整数据流（开新 conv、压缩记忆注入、工具循环、收口时 qq_flow.close 自动把正文经被动回复发出），本模块不重复发以免双份。被动窗口 5 分钟，过期由 qq_push.send 自动回落主动推送。任何异常吞掉→记 error 链并回一句错误摘要，监听器绝不因单条消息崩。用法：python -B qq_inbound.py handle '<事件JSON>'|test '<文本>'。"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qq_push as qp, qq_reply, qq_policy as Q, chain_error
def _col(L):
    def on_line(x):
        x = str(x).rstrip()
        if x: L.append(x)
    return on_line
def deliver(e, c=None):
    c = c or qp.conf(); txt = e.get("text") or ""; L = []
    qq_reply.set_reply(e.get("msg_id"), e.get("openid"), e.get("kind"))
    try:
        if txt[:1] in (":", "：", "!"):
            import shell_core; shell_core.handle(txt, _col(L))
            return qp.push("\n".join(L)[-1400:] or "（无输出）", "QQ·指令", c)
        import agent_stream; agent_stream.ask(txt, _col(L))
        return "数据流已跑·正文经 qq_flow 被动回复（行 %d）" % len(L)
    finally:
        qq_reply.clear()
def handle(m, c=None):
    try:
        c = c or qp.conf(); e = Q.parse(m)
        if not e or not e.get("text"): return None
        if not Q.allowed(e, c): Q.mark(e["msg_id"], e, c); return "拒·非白名单 " + e["openid"][:14]
        if Q.seen(e["msg_id"], c): return "重复忽略 " + e["msg_id"][:16]
        ok, why = Q.gate(e["text"], c); Q.mark(e["msg_id"], e, c)
        if not ok: return qp.push("⚠" + why, "QQ·准入", c)
        return deliver(e, c)
    except Exception as ex:
        try: chain_error.hook("gate", "qq_inbound.handle", str(ex)[:200])
        except Exception: pass
        return qp.push("⚠入站处理异常：" + str(ex)[:120], "QQ·错误", c or qp.conf())
if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    print(json.dumps(handle(json.loads(a[1])), ensure_ascii=False) if a[0] == "handle" and len(a) > 1
         else str(deliver({"kind": "user", "msg_id": "", "openid": (qp.conf().get("openid") or ""), "text": " ".join(a[1:])})) if a[0] == "test"
         else __doc__.strip()[:300])
