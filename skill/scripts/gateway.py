#!/usr/bin/env python3
"""gateway.py — SMS 原生大模型网关（OpenAI 兼容·TUI 默认直连）：config llm_gateway{enabled,base_url,api_key,api_key_env,model}；对话/工具/视觉不依赖 agent CLI——run() 工具循环经 agent_dispatch 执行 exec/read/write/skill/ask/task/task_detail/user_send/thinking_chain 并回填（子进程 UTF-8 中文·附图 base64（>800KB 经可选 Pillow 缩为 JPEG）），首条恒为 SYS 系统提示词（SMS 治理红线＋涉及 SMS 设置/命令必先工具查证）；输出区治理（批7②）：只有末轮（无 tool_calls）正文经 on_line 上主输出，工具轮 content/reasoning 与非流式思考全走 ◌ reasoning 信封进 F9/detail.json——思考混进 content 的上游同样不漏进主屏；工具输出与进度经 msg_flow 信封（on_line 人读行＋ev 结构化回调供顶栏 task 进度）；每次调用记 tool_call 链（挂当前 conv/sess 边）。用法：python -B gateway.py ask|models|doctor "<文本>" [图片路径…]。"""
import os, sys, json, base64, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, settings, msg_flow, agent_dispatch as ad, latency
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
def chat(msgs, on_line=None):
    if on_line is not None and settings.get("llm_gateway.stream", True): import gateway_sse as sse; return sse.stream(msgs, on_line)
    data, err = _req("/chat/completions", {"model": cfg().get("model") or "auto", "messages": msgs, "max_tokens": int(cfg().get("max_tokens", 1024)), "tools": ad.tools_schema(), **{k: cfg()[k] for k in ("temperature", "top_p") if cfg().get(k) is not None}})
    if data: m = data["choices"][0]["message"]; m["content"] = (m.get("content") or "").replace("\x00", "").replace("\r", "\n"); m["reasoning_content"] = (m.get("reasoning_content") or "").replace("\x00", "")
    return (None, err) if not data else ((chains.log("tool", "gateway:" + str(data.get("model"))) and data)["choices"][0]["message"], "finish=" + str(data["choices"][0].get("finish_reason")))
SYS = "你是 skill_manage_system（SMS）的数据流：SMS 只调取与管理技能及其副产物，不得以模型自身知识代答（尤其不得扯无关软件）。可用工具：exec/read/write/skill/ask/ask_user/task/task_detail/user_send/thinking_chain/glob/grep/ls/webfetch（webfetch 需 :grant network）——需要动手就用工具，禁止空口声称已执行；找文件用 glob/ls、查内容用 grep，禁止 dir/find 反复试探。命中托管技能（话语带【SMS 路由】或你判断该用）必须调 skill 工具开子会话按其 SKILL.md 真执行，绝不自答也不得反复回填自引用；一般知识问答而无执行性技能可派时调 skill 工具派 general_answer 作答，多技能约束冲突时先派 constraint_arbiter 仲裁。用户话语含问题/故障/报错/检查/为什么＝诊断请求：用工具实际排查（日志、doctor、链）后给结论，禁止回「输入 help/查配置表」式敷衍，也禁止拿压缩记忆里的旧用法文本充当答案。问到 sms-shell/SMS 设置·命令时用 exec 跑一次 `python -B " + os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.py") + " show`（或 status/get <dot路径>）读真实配置再作答；配置存 <SMS_HOME>\\config\\config.json，命令汇总 `commands.py help`。生成文件一律入工作区 tmp\\（env SMS_TMP）；目标为工作区文件的产物经用户审核后用 ws_release.py diff 预览、release --yes 收编（用户当轮确认＋:grant danger）；禁止反复 where/dir/type 试探。向用户的重要结论用 user_send；缺关键信息必须用户拍板才能继续时用 ask_user（阻塞等待用户屏幕应答，一次一问、问题简短，超时按合理假设继续）。始终简体中文、简短。"
def run(text, on_line=lambda ln: None, images=None, ev=None, max_rounds=None):
    ad.bind(on_line=on_line, ev=ev if ev is not None else False); cap = max_rounds or int(settings.get("gateway.max_rounds", 24)); n = 0; last = ""  # 轮次上限熔断：修复子技能已输出结束信息仍收不了口＝整壳卡死根因之一
    msgs = [image_message(text, images) if images else {"role": "user", "content": text}]
    while True:
        if (n := n + 1) > cap: on_line("⚠ 工具循环达 %d 轮上限——强制收口返回（可调 settings gateway.max_rounds）" % cap); return last or "（达轮次上限·无正文输出）"
        m, err = latency.wrap("llm", cfg().get("model") or "auto", chat, msgs, on_line)
        if not m: on_line("网关错误：" + err); return last or None
        if not (tcs := m.get("tool_calls") or []): r = m.get("reasoning_content") or ""; txt = m.get("content") or ""; p = not m.get("printed"); p and r and on_line(msg_flow.brief(msg_flow.make("reasoning", r))); txt = txt or (r if p else ""); txt and on_line(txt); return txt
        r = m.get("reasoning_content") or ""; c = "" if m.get("printed") else (m.get("content") or ""); (x := (r + (("过程·" + c) if c else ""))[:2000]) and on_line(msg_flow.brief(msg_flow.make("reasoning", x))); msgs.append(m); last = m.get("content") or last
        for tc in tcs: f = tc.get("function") or {}; res = latency.wrap("tool", str(f.get("name", "")), ad.execute, str(f.get("name", "")), str(f.get("arguments") or "{}")); msgs.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": str(res)[:4000] or "(无输出)"})
if __name__ == "__main__":
    a = sys.argv[1:] or ["doctor"]; cmd, arg, c = a[0], " ".join(a[1:]), cfg()
    if cmd == "doctor": print(json.dumps({"enabled": bool(c.get("enabled")), "base_url": c.get("base_url"), "model": c.get("model"), "key": "set" if c.get("api_key") else "missing"}, ensure_ascii=False))
    elif cmd == "models": data, err = _req("/models"); print("\n".join(x["id"] for x in (data or {}).get("data", [])) or "ERR " + err)
    else: run(arg or "你好", print, images=[p for p in a[1:] if os.path.isfile(p) and not p.startswith("-")] or None) if not cmd.startswith("-") else (print(__doc__.strip()), sys.exit(1))
