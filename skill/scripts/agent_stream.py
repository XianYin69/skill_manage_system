#!/usr/bin/env python3
"""agent_stream.py — sms-shell 数据流引擎：默认直达系统原生网关（config llm_gateway.enabled→gateway），网关未启用才回退已装 agent CLI；每次输入＝开新对话（红线 17），会话层 chains.set_active(conv/sess)＋session/dialogue 碎片打 member→sess 边；工作区＝gateway exec 与 agent CLI 的 cwd；技能路由命中→SMS 直接经 agent_tools.run_skill 开子会话真派发，未命中→chains.conversation 压缩记忆＋SKILL.md 索引＋治理注入送网关；话语/工具/技能/任务输出全程 msg_flow 信封（on_line 人读行＋ev 回调供 TUI 顶栏进度）；各阶段步骤名经 st 回调上报；尾行 [图:<路径>] 为网关视觉附图；状态存 <SMS_HOME>/shell/；皆无则拒绝（本体不作答）。"""
import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, dream, gateway, model_meta, tts, skill_route, prompt_builder, workspace as ws, agent_tools as at, shell_resume as sr
SMS = resolve_home.ensure(); STATE = os.path.join(SMS, "shell")
ADAPTERS = {"claude": {"bin": "claude", "args": ["-p"]}, "codex": {"bin": "codex", "args": ["exec"]}, "cursor": {"bin": "cursor-agent", "args": []}, "kilocode": {"bin": "kilocode", "args": ["run"]}, "kilo": {"bin": "kilo", "args": ["run"]}, "aider": {"bin": "aider", "args": ["--message"]}}
def adapters():
    extra = {k: v for k, v in (resolve_home.conf(SMS).get("agent_cli") or {}).items() if not k.startswith("_") and isinstance(v, dict)}
    return dict(ADAPTERS, **extra, **({"gateway": {"native": True}} if gateway.enabled() else {}))
def detected(): return {k: v for k, v in sorted(adapters().items()) if v.get("native") or shutil.which(v.get("bin", k))}
def _state(n, d=""):
    try: return open(os.path.join(STATE, n), encoding="utf-8").read().strip()
    except Exception: return d
def _put(n, v): os.makedirs(STATE, exist_ok=True); open(os.path.join(STATE, n), "w", encoding="utf-8").write(v)
def current():
    det = detected(); cur = _state("current_agent")
    return next((k for k, v in det.items() if v.get("native")), cur if cur in det else next(iter(det), None))
def prefix_on(): return _state("skill_prefix", "on") != "off"
def use(name): _put("current_agent", name); return "切到 agent：" + name + ("" if name in detected() else "（未检出其 CLI——配置 agent_cli {bin,args} 并确保在 PATH）")
def skill(on): _put("skill_prefix", "on" if on else "off"); return "skill_manage_system 前缀：" + _state("skill_prefix", "on")
def compose(text, sms=None): return prompt_builder.init(sms or SMS) + "\n\n" + prompt_builder.build(text, sms or SMS)
def _edge(conv): return [[conv, "ref", 1], [chains.cur_sess(), "member", 1]]
def ask(text, on_line, st=lambda n: None, ev=None):
    on_line = tts.hook(on_line); dream.maybe(SMS); model_meta.maybe(); ag = current(); st("检测执行器：" + (ag or "无"))
    if not ag: on_line("拒绝：未检出 agent CLI 且原生网关未启用（config llm_gateway.enabled=true）——sms-shell 只经数据流执行，本体不作答"); return None
    spec = adapters()[ag]; conv = chains.session_id(); chains.set_active(conv); chains.record("session", "open:" + conv, _edge(conv)); st("开新对话：" + conv)
    wsp, virt = ws.begin(conv); st("工作区：" + wsp + ("〔虚拟·收口即删〕" if virt else "")); at.bind(on_line=on_line, ev=ev if ev is not None else False)
    want = _state("current_agent"); want and want != ag and not spec.get("native") and on_line("注意：所选 agent " + want + " 未检出，本次经 " + ag + " 执行（:agents 查看）")
    sid2, inj = skill_route.route(text, SMS); st("技能路由：" + (sid2 and ("命中 " + sid2 + "·已记 skill_call 链") or "未命中·注入技能全表"))
    chains.record("dialogue", "user@" + conv + " " + text[:200], _edge(conv)); rc = 0; st("话语送数据流")
    if sid2 and spec.get("native"):
        names = sid2.split(","); st("派发子会话：" + sid2 + ("（%d 技能并行）" % len(names) if len(names) > 1 else ""))
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(3, max(1, len(names)))) as ex: list(ex.map(lambda n: at.run_skill(n, text), names))
        on_line("【SMS 整合】" + sid2 + " 子会话输出如上（⧉ 前缀）；不满意可 :dispatch " + names[0] + " <更具体诉求> 重派")
    elif spec.get("native"):
        body = sr.prefix() + (text if not prefix_on() else chains.conversation(compose(text, SMS) + "\n\n" + inj)); st("提示词构建·压缩记忆组装·网关流式执行")
        bl = body.split("\n"); imgs = None
        if bl[-1].startswith("[图:") and bl[-1].endswith("]"): p = bl[-1][3:-1].strip(); body = "\n".join(bl[:-1]); imgs = [p] if os.path.isfile(p) else None
        resp = gateway.run(body, on_line, images=imgs, ev=ev); resp and sr.flag() and sr.append(text, str(resp))
    else:
        st("agent CLI 执行：" + ag); args, env = list(spec.get("args", [])), dict(os.environ, PYTHONIOENCODING="utf-8", SMS_WORKSPACE=wsp, SMS_TMP=resolve_home.wtmp()); env.update(spec.get("env") or {})
        stdin = subprocess.PIPE if spec.get("prompt_stdin") else subprocess.DEVNULL
        p = subprocess.Popen([spec.get("bin", ag)] + args + ([] if stdin else [text if not prefix_on() else text + "\n\n" + inj]), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env, cwd=wsp)
        if spec.get("prompt_stdin"): p.stdin.write(text + "\n\n" + inj); p.stdin.close()
        for ln in iter(p.stdout.readline, ""):
            ln.strip() and on_line(ln.rstrip())
        rc = p.wait()
    chains.record("session", "close:" + conv, _edge(conv)); chains.record("time", "对话 " + conv + " 收口 rc=" + str(rc), _edge(conv)); st("对话收口 rc=" + str(rc)); m_ = ws.end(wsp, virt); m_ and on_line(m_); chains.ACTIVE["conv"] = ""; return {"agent": ag, "rc": rc, "conv": conv}