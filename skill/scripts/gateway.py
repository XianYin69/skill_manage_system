#!/usr/bin/env python3
"""gateway.py — SMS 原生大模型网关（OpenAI 兼容·TUI 默认直连）：config llm_gateway{enabled,base_url,api_key,api_key_env,model}；对话/工具/视觉不依赖 agent CLI——run() 工具循环经 agent_dispatch 执行 exec·read·write·skill·ask·task·task_detail·user_send·thinking_chain 并回填（子进程 UTF-8 中文·附图 base64（>800KB 经可选 Pillow 缩为 JPEG）），首条恒为 SYS 系统提示词（批16 起 LLM 主导治理：简单问答可直答、动手才用工具·执行类经 skill 子会话真跑＋查证红线·批18 加主流程守卫：话语带〔任务表〕且仍有未完成行时禁止收口，注入续推提示让模型继续派发/改表，depth==0 才生效避免子会话递归；批20 空口守卫 flow_guard：免表单步任务以「现在开始写/Let me check」类纯文本收口且本轮无 write/skill/task 调用时同样注入续推（共用 task.max_continue 熔断），finish=length 截断致工具参数不完整即不执行并回分段 append 指引；批21 token 预算：发送前经 fg.budget 估算消息 tokens、大于 max_tokens 即在首条用户消息追加〔Token 预算〕块——脚本只测量、超限拆分由模型自决，finish=length 截断正文亦注入续推让模型分段续写）；输出区治理（批7②）：只有末轮（无 tool_calls）正文经 on_line 上主输出，工具轮 content/reasoning 与非流式思考全走 ◌ reasoning 信封进 F9/detail.json——思考混进 content 的上游同样不漏进主屏；工具输出与进度经 msg_flow 信封（on_line 人读行＋ev 结构化回调供顶栏 task 进度）；每次调用记 tool_call 链（挂当前 conv/sess 边）。用法：python -B gateway.py ask|models|doctor "<文本>" [图片路径…]。"""
import os, sys, json, base64, urllib.request, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, settings, msg_flow, agent_dispatch as ad, agent_ctx as ac, task_table as tt, latency, stop_channel as stop, flow_guard as fg
def _b64img(p):
    if os.path.getsize(p) > 800_000:
        try: from PIL import Image; import io as _io; im = Image.open(p); im.thumbnail((1568, 1568)); buf = _io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=82); return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
        except Exception: pass
    return ({".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}).get(os.path.splitext(p)[1].lower(), "image/png"), base64.b64encode(open(p, "rb").read()).decode()
def image_message(text, paths): return {"role": "user", "content": [{"type": "text", "text": text}] + [{"type": "image_url", "image_url": {"url": "data:" + m + ";base64," + d}} for m, d in (_b64img(p) for p in paths)]}
def cfg():
    c = dict(resolve_home.conf(resolve_home.ensure()).get("llm_gateway") or {}); k = c.get("api_key_env"); c["api_key"] = os.environ.get(k, c.get("api_key", "")) if k else c.get("api_key", ""); return c
def enabled(): return bool(cfg().get("enabled"))
def _send(req):
    try: return json.loads(urllib.request.urlopen(req, timeout=int(cfg().get("timeout", 120))).read().decode("utf-8", "replace")), ""
    except Exception as e:
        try: d = e.read().decode("utf-8", "replace")[:300]
        except Exception: d = str(e)[:150]
        return None, str(e)[:150] + " " + d
def _req(path, body=None):
    c = cfg(); h = {"Authorization": "Bearer " + str(c.get("api_key", ""))}; d = None if body is None else json.dumps(body).encode("utf-8"); d is not None and h.update({"Content-Type": "application/json"}); return _send(urllib.request.Request(str(c.get("base_url", "")).rstrip("/") + path, data=d, headers=h))
def chat(msgs, on_line=None):
    if on_line is not None and settings.get("llm_gateway.stream", True): import gateway_sse as sse; return sse.stream(msgs, on_line)
    data, err = _req("/chat/completions", {"model": cfg().get("model") or "auto", "messages": msgs, "max_tokens": int(cfg().get("max_tokens", 1024)), "tools": ad.tools_schema(), **{k: cfg()[k] for k in ("temperature", "top_p", "reasoning_effort") if cfg().get(k) is not None}})
    if data: m = data["choices"][0]["message"]; m["content"] = (m.get("content") or "").replace("\x00", "").replace("\r", "\n"); m["reasoning_content"] = (m.get("reasoning_content") or "").replace("\x00", "")
    return (None, err) if not data else ((chains.log("tool", "gateway:" + str(data.get("model"))) and data)["choices"][0]["message"], "finish=" + str(data["choices"][0].get("finish_reason")))
SYS = "你是 skill_manage_system（SMS）数据流中的主导决策者：由你自主判断如何完成用户请求——纯知识问答/闲聊/解释可直接作答（简短·简体中文），不必先派子技能；需要本机事实（文件/配置/日志/网络）时用 read/grep/glob/ls/exec/webfetch 查证后再答，禁止编造；需要动手执行（写盘/派技能/调脚本）才用工具——执行类诉求经 skill 工具开子会话真执行（按注入的 SKILL.md 与脚本清单），禁止空口声称已执行、也不得越权直接写 skill 目录；宣告动手必须在同一轮直接调用 write/exec/skill 落地，禁止只说一句「现在开始写/Let me check」就结束回合；单次 write 内容较长时分多段 append=true（每段≤600字）防 max_tokens 截断；话语带〔Token 预算〕块＝脚本估算输入已超单轮 max_tokens，凡预计单轮输出会超限的自行分段/拆多轮（拆分方案由你定），预计不超则忽略该块。可用工具：exec/read/write/skill/ask/ask_user/task/task_detail/task_plan/user_send/thinking_chain/chain/debate/glob/grep/ls/webfetch（webfetch 需 :grant network）。链＝省 token 的记忆介质（批17·相信大模型）：涉既往经验/历史决定先用 chain recall 查证再答，禁止只凭猜测；得出值得留存的结论、偏好、修法即用 chain append 写入 memory/knowledge/logic 链（收口链收口时自动落盘）；决策岔路先用 debate 铺正反双链自辩修正路径——人多在回路旁、机制自动修正，只有高危节点（:grant danger/云端下载/对外端口）才回人在回路征求确认。[SMS 路由] 注入只是打分参考提示，命中与否由你结合话语与索引自行决定派发或直答；多技能约束冲突时先派 constraint_arbiter 仲裁。话语带〔任务表〕时按表推进（批18·行数无上限）：脚本给的是粗分种子，首轮据实改表（task_plan add/remove/skill）到真实步数，每步完成必调 task_plan status <表id> <行id> done；子任务无依赖可用 task 工具（parallel=true）并发派发，有依赖则 parallel=false 或依序逐 skill 派发；找文件用 glob/ls、查内容用 grep，禁止 dir/find 反复试探。skill 工具返回若带「已实时显示·禁止复述」包装头，正文用户已看过、你只见首尾片段，最终回复严禁复述/引用/改写/摘要原文；子会话收口即返回 SMS 主流程：主任务＝整张任务表全部行 done，未完成前不得结束对话——先查〔任务表〕未完成行并继续推进（续派 skill/task 或自办工具），全部完成后才以一句 ≤40 字收尾回报，禁止把单个子技能完成当作整段对话结束、禁止反复宣告完成而不推进；SMS 主流程守卫会在任务表仍有未完成行时阻止收口并注入续推提示；需要技能结果里的数据继续干活时用 read/exec 读其产物文件。用户话语含问题/故障/报错/检查/为什么＝诊断请求：用工具实际排查（日志、doctor、链）后给结论，禁止回「输入 help/查配置表」式敷衍，也禁止拿压缩记忆里的旧用法文本充当答案；仅问 sms-shell 用法/配置入口时可指路 :help/:config/:cmds。问到 SMS 设置时用 exec 跑一次 `python -B " + os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.py") + " show`（或 status/get <dot路径>）读真实配置再作答；配置存 <SMS_HOME>\\config\\config.json，命令汇总 `commands.py help`。生成文件一律入工作区 tmp\\（env SMS_TMP）；目标为工作区文件的产物经用户审核后用 ws_release.py diff 预览、release --yes 收编（用户当轮确认＋:grant danger）。向用户的重要结论用 user_send；缺关键信息必须用户拍板才能继续时用 ask_user（阻塞等待用户屏幕应答，一次一问、问题简短，超时按合理假设继续）。始终简体中文、简短。"
def run(text, on_line=lambda ln: None, images=None, ev=None, max_rounds=None):
    ad.bind(on_line=on_line, ev=ev if ev is not None else False); cap = int(settings.get("caps.gateway_rounds", 0) if max_rounds is None else max_rounds); n = 0; last = ""; idle = 0; acted = False; R = max(0, int(settings.get("llm_gateway.retries", 1))); left = R; msgs = [{"role": "system", "content": SYS}, image_message(text, images) if images else {"role": "user", "content": text}]; msgs[-1] = fg.add_note(msgs[-1], fg.budget(msgs, int(cfg().get("max_tokens", 4096))))
    while True:
        stop.check(); n += 1
        if cap and n > cap: on_line("⚠ 工具循环达 %d 轮上限——强制收口返回（caps.gateway_rounds＝0 即无限·F4 图形配置可调）" % cap); return last or "（达轮次上限·无正文输出）"
        m, err = latency.wrap("llm", cfg().get("model") or "auto", chat, msgs, on_line); m, err = ((None, "空响应（上游 200 无正文·多为并发过载）") if m and not (m.get("tool_calls") or []) and not ((m.get("content") or "") + (m.get("reasoning_content") or "")).strip() else (m, err))
        if not m and left > 0: left -= 1; time.sleep(1.2); on_line(msg_flow.brief(msg_flow.make("reasoning", "网关瞬时错误（" + str(err)[:80] + "）自动重试 " + str(R - left) + "/" + str(R) + "·stop 可中断"))); continue
        if not m: on_line("网关错误：" + str(err)[:150] + "（重试仍失败——本轮收口·未尽事项由接续注入下轮续跑）"); return last or None
        if not (tcs := m.get("tool_calls") or []):
            r = m.get("reasoning_content") or ""; p = not m.get("printed"); p and r and on_line(msg_flow.brief(msg_flow.make("reasoning", r))); txt = m.get("content") or (r if p else ""); go = ac.cur()["depth"] == 0 and settings.get("task.auto_continue", True); pend = go and tt.pending(chains.ACTIVE.get("conv") or ""); prom = go and not pend and not acted and fg.promises(txt); cut = go and not pend and not prom and bool(txt) and "finish=length" == str(err).strip(); kind = "pend" if pend else "prom" if prom else "cut" if cut else ""
            if kind:
                (p and txt) and on_line(msg_flow.brief(msg_flow.make("reasoning", "（续推·主任务未完成）" + txt[:200]))); msgs.append(m); idle += 1; mc = int(settings.get("task.max_continue", 5)); on_line(msg_flow.brief(msg_flow.make("notice", fg.notice(kind, idle))))
                if mc and idle > mc: on_line(msg_flow.brief(msg_flow.make("notice", "⚠ 主流程续推达上限 task.max_continue·任务未收口·请用户介入或用 :task status 收口"))); return last or txt or None
                msgs.append({"role": "user", "content": fg.inject(kind, pend)}); last = txt or last; continue
            txt and on_line(txt); return txt
        r = m.get("reasoning_content") or ""; c = "" if m.get("printed") else (m.get("content") or ""); (x := (r + (("过程·" + c) if c else ""))[:2000]) and on_line(msg_flow.brief(msg_flow.make("reasoning", x))); msgs.append(m); last = m.get("content") or last; idle = 0
        for tc in tcs:
            f = tc.get("function") or {}; nm = str(f.get("name") or ""); raw = str(f.get("arguments") or "{}"); acted = acted or nm in ("write", "skill", "task"); res = fg.TRUNC if "finish=length" == str(err).strip() and not fg.jargs(raw) else latency.wrap("tool", nm, ad.execute, nm, raw); stop.check(); msgs.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": str(res)[:4000] or "(无输出)"})
if __name__ == "__main__":
    a = sys.argv[1:] or ["doctor"]; cmd, arg, c = a[0], " ".join(a[1:]), cfg()
    if cmd == "doctor": print(json.dumps({"enabled": bool(c.get("enabled")), "base_url": c.get("base_url"), "model": c.get("model"), "key": "set" if c.get("api_key") else "missing"}, ensure_ascii=False))
    elif cmd == "models": data, err = _req("/models"); print("\n".join(x["id"] for x in (data or {}).get("data", [])) or "ERR " + err)
    else: run(arg or "你好", print, images=[p for p in a[1:] if os.path.isfile(p) and not p.startswith("-")] or None) if not cmd.startswith("-") else (print(__doc__.strip()), sys.exit(1))
