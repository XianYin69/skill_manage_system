#!/usr/bin/env python3
"""gateway_sse.py — 原生网关 SSE 流式（2026-09-26 治「运行慢」观感·ps1 壳已流式而 python 壳整轮等待）：stream(msgs, on_line) 以 stream:true 请求 /chat/completions，逐 chunk 累积 delta.content（遇换行/句末读标点或≥88 字即分段吐给 on_line——首段尽快可见），delta.reasoning_content（模型思考）单独缓冲并以 msg_flow reasoning 信封「◌ 」吐给 on_line→只进 F9 详细细节不入主输出（批7·用户「思考过程全放F9·输出区只放正文」），按 index 合并 delta.tool_calls 分片（id/name/arguments 拼接），返回与 gateway.chat 同构的 (message, note)。「残缺」根治（用户 2026-09-26 批4报障「对话输出部分消息残缺」）：旧版最终 message.content 只回传尚未吐出的 buf 尾巴——接续记录（shell_resume last_conv）、多轮工具循环历史、整合返回值全剩末尾几句；v2 全程另存 acc 完整正文，返回 content=acc 全文＋printed=True 防重复吐显；纯思考模型兜底（同 ps1 壳口径）：acc 恒空时思考即正文送主输出；上游不支持 event-stream 时读整包按非流式同构返回·思考仍走 ◌ 信封；异常回 (None, err)。llm_gateway.stream=false 即回退整轮 chat()。用法：经 gateway.chat 调用；python -B gateway_sse.py "<文本>" 直连验证流式。"""
import os, sys, json, time, urllib.request, msg_flow
SENT = "。！？；!?…"
def _req(msgs):
    import agent_dispatch as ad, settings
    c = settings.eff()["llm_gateway"]; body = {"model": c.get("model") or "auto", "messages": msgs, "max_tokens": int(c.get("max_tokens", 1024)), "tools": ad.tools_schema(), "stream": True, **{k: c[k] for k in ("temperature", "top_p") if c.get(k) is not None}}
    key = os.environ.get(c.get("api_key_env") or "", "") or c.get("api_key", "")
    return urllib.request.Request(str(c.get("base_url", "")).rstrip("/") + "/chat/completions", data=json.dumps(body).encode("utf-8"), headers={"Authorization": "Bearer " + str(key), "Content-Type": "application/json", "Accept": "text/event-stream"}), int(c.get("timeout", 120))
def _emit(buf, on_line):
    while buf:
        i = next((j for j, ch in enumerate(buf) if ch == "\n" or (ch in SENT and j > 24)), -1)
        if i < 0 and len(buf) < 88: break
        seg = buf[:i + 1] if i >= 0 else buf[:88]
        on_line(seg.rstrip("\n")); buf = buf[i + 1:] if i >= 0 else buf[88:]
    return buf
def _msg(d):
    m = (d.get("choices") or [{}])[0].get("message") or {}; m["content"] = (m.get("content") or "").replace("\x00", "").replace("\r", "\n"); return m, str((d.get("choices") or [{}])[0].get("finish_reason"))
def _rline(s): return msg_flow.brief(msg_flow.make("reasoning", s))
def stream(msgs, on_line):
    req, tout = _req(msgs); buf = ""; rbuf = ""; acc = ""; racc = ""; tcs = {}; fr = ""
    try:
        with urllib.request.urlopen(req, timeout=tout) as r:
            if "text/event-stream" not in str(r.headers.get("content-type") or ""):
                m, note = _msg(json.loads(r.read().decode("utf-8", "replace"))); rc = m.pop("reasoning_content", "") or ""; rc and on_line(_rline(rc)); return m, note
            for raw in r:
                ln = raw.decode("utf-8", "replace").strip()
                if not ln.startswith("data:"): continue
                p = ln[5:].strip()
                if p == "[DONE]": break
                try: d = json.loads(p)
                except Exception: continue
                ch = (d.get("choices") or [{}])[0]; de = ch.get("delta") or {}; fr = ch.get("finish_reason") or fr
                dt = de.get("content") or ""; rt = de.get("reasoning_content") or ""
                acc += dt; racc += rt; buf = _emit(buf + dt, on_line); rbuf = _emit(rbuf + rt, lambda s, _o=on_line: s.strip() and _o(_rline(s)))
                for t in de.get("tool_calls") or []:
                    e = tcs.setdefault(t.get("index", 0), {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    f = t.get("function") or {}; e["id"] = e["id"] or (t.get("id") or ""); e["function"]["name"] += f.get("name") or ""; e["function"]["arguments"] += f.get("arguments") or ""
    except Exception as e:
        detail = ""
        try: detail = e.read().decode("utf-8", "replace")[:200]
        except Exception: pass
        return None, str(e)[:150] + " " + detail
    buf.strip() and on_line(buf.rstrip("\n")); rbuf.strip() and on_line(_rline(rbuf.rstrip("\n")))
    if not acc.strip() and racc.strip(): acc = racc.strip(); on_line(acc)
    return {"role": "assistant", "content": acc.replace("\x00", "").replace("\r", "\n"), "tool_calls": list(tcs.values()) if tcs else None, "reasoning_content": "", "printed": True}, "finish=" + (fr or "stop")
if __name__ == "__main__":
    t = " ".join(sys.argv[1:]) or "你好，用一句话介绍 SMS"; m, err = stream([{"role": "user", "content": t}], lambda s: print(s, flush=True))
    print(json.dumps({"ok": bool(m), "err": err, "chars": len((m or {}).get("content") or ""), "tool_calls": bool((m or {}).get("tool_calls"))}, ensure_ascii=False) if m else "ERR " + err)
