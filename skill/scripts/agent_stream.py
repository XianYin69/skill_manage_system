#!/usr/bin/env python3
"""agent_stream.py — sms-shell 数据流引擎：默认直达系统原生网关（config llm_gateway.enabled→gateway，OpenAI 兼容·不经外部 agent CLI），网关未启用才回退已装 agent CLI（claude/codex 等，agent_cli 可增改，:use 手选）；每次输入＝开新对话（红线 17）＋chains.set_active(conv)＋session/dialogue/time 碎片 member→sess 边（会话隔离防污染）；工作区（SMS_WORKSPACE·真实或 <SMS_HOME>/workspaces/_virtual/<conv> 虚拟·begin 建 end 删·自动建 tmp）＝gateway exec 与 agent CLI 的 cwd；技能路由命中→SMS 直接经 agent_tools.run_skill 开子会话真派发（多技能 ThreadPool 并行·整合提示；修复旧版「注入 1400 字截断 SKILL.md 让网关空转＋subconv 提示回填自引用死循环」），未命中→chains.conversation 压缩记忆＋prompt_builder 组装＋治理注入送网关工具循环；全程 msg_flow 信封（on_line 人读行＋ev 回调供 TUI 顶栏 task 进度）；st 上报步骤名；尾行 [图:<路径>] 视觉附图；状态存 <SMS_HOME>/shell/；皆无则拒绝（本体不作答）。"""
import os, sys, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, dream, gateway, model_meta, tts, skill_route, prompt_builder, workspace as ws, agent_tools as at
SMS = resolve_home.ensure(); STATE = os.path.join(SMS, "shell")
ADAPTERS = {"claude": {"bin": "claude", "args": ["-p"]}, "codex": {"bin": "codex", "args": ["exec"]}, "cursor": {"bin": "cursor-agent", "args": []}, "kilocode": {"bin": "kilocode", "args": ["run"]}, "kilo": {"bin": "kilo", "args": ["run"]}, "aider": {"bin": "aider", "args": ["--message"]}}
def adapters():
    extra = {k: v for k, v in (resolve_home.conf(SMS).get("agent_cli") or {}).items() if not k.startswith("_") and isinstance(v, dict)}
    return dict(ADAPTERS, **extra, **({"gateway": {"native": True}} if gateway.enabled() else {}))
def detected(): return {k: v for k, v in sorted(adapters().items()) if v.get("native") or shutil.which(v.get("bin", k))}
def _state(name, default=""): return open(os.path.join(STATE, name), encoding="utf-8").read().strip() if os.path.isfile(os.path.join(STATE, name)) else default
def _put(name, val): os.makedirs(STATE, exist_ok=True); open(os.path.join(STATE, name), "w", encoding="utf-8").write(val)
def current(): det = detected(); cur = _state("current_agent"); return next((k for k, v in det.items() if v.get("native")), cur if cur in det else next(iter(det), None))
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
        with ThreadPoolExecutor(max_workers=min(3, max(1, len(names)))) as ex: list(ex.map(lambda n: at.run_skill(n, text), names))
        on_line("【SMS 整合】" + sid2 + " 子会话输出如上（⧉ 前缀）；需重派：:dispatch " + names[0] + " <更具体诉求>")
    elif spec.get("native"):
        body = text if not prefix_on() else chains.conversation(compose(text, SMS) + "\n\n" + inj); st("提示词构建·压缩记忆组装·网关流式执行")
        bl = body.split("\n"); img = bl[-1] if bl[-1].startswith("[图:") and bl[-1].endswith("]") else ""
        if img: body = "\n".join(bl[:-1])
        gateway.run(body, on_line, images=[img[3:-1].strip()] if img and os.path.isfile(img[3:-1].strip()) else None, ev=ev)
    else:
        st("agent CLI 执行：" + ag); body = text if not prefix_on() else chains.conversation(compose(text, SMS) + "\n\n" + inj)
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SMS_WORKSPACE=wsp, SMS_TMP=resolve_home.wtmp()); env.update(spec.get("env") or {})
        stdin = subprocess.PIPE if spec.get("prompt_stdin") else subprocess.DEVNULL
        p = subprocess.Popen([spec.get("bin", ag)] + list(spec.get("args", [])) + ([] if stdin else [body]), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env, cwd=wsp)
        if stdin: p.stdin.write(body); p.stdin.close()
        for ln in iter(p.stdout.readline, ""):
            if ln.strip(): on_line(ln.rstrip())
        rc = p.wait()
    chains.record("session", "close:" + conv, _edge(conv)); chains.record("time", "对话 " + conv + " 收口 rc=" + str(rc), _edge(conv)); st("对话收口 rc=" + str(rc)); m_ = ws.end(wsp, virt); m_ and on_line(m_); chains.ACTIVE["conv"] = ""; return {"agent": ag, "rc": rc, "conv": conv}
