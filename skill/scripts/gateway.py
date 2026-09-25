#!/usr/bin/env python3
"""gateway.py — SMS 原生大模型网关（OpenAI 兼容）：config llm_gateway{enabled,base_url,api_key,api_key_env,model}；对话/工具/视觉不依赖 agent CLI——run() 工具循环（exec→回填）、附图 base64（>800KB 经可选 Pillow 缩为 JPEG）；每次调用记 tool_call 链。用法：python gateway.py ask|models|doctor "<文本>" [图片路径…]。"""
import os, sys, json, base64, subprocess, urllib.request; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains
def _b64img(p):
    if os.path.getsize(p) > 800_000:
        try:
            from PIL import Image; import io as _io; im = Image.open(p); im.thumbnail((1568, 1568)); buf = _io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=82)
            return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
        except Exception: pass
    return ({".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}).get(os.path.splitext(p)[1].lower(), "image/png"), base64.b64encode(open(p, "rb").read()).decode()
def image_message(text, paths):
    return {"role": "user", "content": [{"type": "text", "text": text}] + [{"type": "image_url", "image_url": {"url": "data:" + m + ";base64," + d}} for m, d in (_b64img(p) for p in paths)]}
def cfg():
    c = dict(resolve_home.conf(resolve_home.ensure()).get("llm_gateway") or {}); k = c.get("api_key_env")
    c["api_key"] = os.environ.get(k, c.get("api_key", "")) if k else c.get("api_key", ""); return c
def enabled(): return bool(cfg().get("enabled"))
def _send(req):
    try:
        with urllib.request.urlopen(req, timeout=int(cfg().get("timeout", 120))) as r: return json.loads(r.read().decode("utf-8", "replace")), ""
    except Exception as e:
        try: detail = e.read().decode("utf-8", "replace")[:300]
        except Exception: detail = str(e)[:150]
        return None, str(e)[:150] + " " + detail
def _req(path, body=None):
    c = cfg(); h = {"Authorization": "Bearer " + str(c.get("api_key", ""))}; d = None if body is None else json.dumps(body).encode("utf-8")
    if d is not None: h["Content-Type"] = "application/json"
    return _send(urllib.request.Request(str(c.get("base_url", "")).rstrip("/") + path, data=d, headers=h))
def chat(msgs):
    data, err = _req("/chat/completions", {"model": cfg().get("model") or "auto", "messages": msgs, "max_tokens": int(cfg().get("max_tokens", 1024)), "tools": TOOLS})
    if data: m = data["choices"][0]["message"]; m["content"] = (m.get("content") or "").replace("\x00", "").replace("\r", "\n"); m["reasoning_content"] = (m.get("reasoning_content") or "").replace("\x00", "")
    return (None, err) if not data else ((chains.log("tool", "gateway:" + str(data.get("model"))) and data)["choices"][0]["message"], "finish=" + str(data["choices"][0].get("finish_reason")))
TOOLS = [{"type": "function", "function": {"name": "exec", "description": "在用户电脑上执行一条 shell 命令", "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}}}]
def run(text, on_line=lambda ln: None, images=None, max_steps=5):
    msgs = [image_message(text, images) if images else {"role": "user", "content": text}]
    for _ in range(max_steps):
        m, err = chat(msgs)
        if not m: on_line("网关错误：" + err); return None
        if not (tcs := m.get("tool_calls") or []): txt = m.get("content") or m.get("reasoning_content") or ""; (txt and on_line(txt)); return txt
        msgs.append(m)
        for tc in tcs:
            cmd = (json.loads(tc["function"]["arguments"]) or {}).get("cmd", ""); on_line("$ " + cmd)
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": ((r.stdout or "") + (r.stderr or ""))[:4000] or "(无输出)"})
    on_line("达到 max_steps，中止"); return None
if __name__ == "__main__":
    a = sys.argv[1:] or ["doctor"]; cmd, arg, c = a[0], " ".join(a[1:]), cfg()
    if cmd == "doctor": print(json.dumps({"enabled": bool(c.get("enabled")), "base_url": c.get("base_url"), "model": c.get("model"), "key": "set" if c.get("api_key") else "missing"}, ensure_ascii=False))
    elif cmd == "models": data, err = _req("/models"); print("\n".join(x["id"] for x in (data or {}).get("data", [])) or "ERR " + err)
    else: run(arg or "你好", print, images=[p for p in a[1:] if os.path.isfile(p)] or None)
