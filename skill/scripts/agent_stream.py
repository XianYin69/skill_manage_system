#!/usr/bin/env python3
"""agent_stream.py — sms-shell 数据流引擎：默认直达系统原生网关（config llm_gateway.enabled→gateway，OpenAI 兼容直连·SSE 流式、不经外部 agent CLI），网关未启用才回退已装 agent CLI（claude/codex 等，agent_cli 可增改，:use 手选）；每次输入＝新开一次对话（chains.conversation 压缩记忆＋双层规则，红线 17），话语先经 skill_route 与 registry 技能匹配（命中记 skill_call 链·注入先读 SKILL.md 真调指令），各阶段步骤名经 st 回调上报 TUI 状态栏，逐行流回、收口记链；尾行 [图:<路径>] 为网关视觉附图；状态存 <SMS_HOME>/shell/；皆无则拒绝（本体不作答）。"""
import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, dream, gateway, model_meta, tts, skill_route
SMS = resolve_home.ensure()
STATE = os.path.join(SMS, "shell")
ADAPTERS = {"claude": {"bin": "claude", "args": ["-p"]}, "codex": {"bin": "codex", "args": ["exec"]}, "cursor": {"bin": "cursor-agent", "args": []}, "kilocode": {"bin": "kilocode", "args": ["run"]}, "kilo": {"bin": "kilo", "args": ["run"]}, "aider": {"bin": "aider", "args": ["--message"]}}
SKILL_DIRECTIVE = "本请求经 skill_manage_system（SMS）治理：SMS 只调取与管理技能及其副产物，不得以模型自身常识代答（勿扯 Android/adb/其它无关软件）；问到 sms-shell 设置/命令/配置时，先经 exec 工具执行 settings.py show 或 commands.py help 查证，再据实作答。"
def adapters():
    extra = {k: v for k, v in (resolve_home.conf(SMS).get("agent_cli") or {}).items() if not k.startswith("_") and isinstance(v, dict)}
    out = dict(ADAPTERS, **extra)
    if gateway.enabled(): out["gateway"] = {"native": True}
    return out
def detected(): return {k: v for k, v in sorted(adapters().items()) if v.get("native") or shutil.which(v.get("bin", k))}
def _state(name, default=""):
    try: return open(os.path.join(STATE, name), encoding="utf-8").read().strip()
    except Exception: return default
def _put(name, val): os.makedirs(STATE, exist_ok=True); open(os.path.join(STATE, name), "w", encoding="utf-8").write(val)
def current():
    det = detected(); cur = _state("current_agent")
    return next((k for k, v in det.items() if v.get("native")), cur if cur in det else next(iter(det), None))
def prefix_on(): return _state("skill_prefix", "on") != "off"
def use(name): _put("current_agent", name); return "切到 agent：" + name + ("" if name in detected() else "（未检出其 CLI——配置 agent_cli {bin,args} 并确保在 PATH）")
def skill(on): _put("skill_prefix", "on" if on else "off"); return "skill_manage_system 前缀：" + _state("skill_prefix", "on")
def ask(text, on_line, st=lambda n: None):
    on_line = tts.hook(on_line); dream.maybe(SMS); model_meta.maybe(); ag = current(); st("检测执行器：" + (ag or "无"))
    if not ag: on_line("拒绝：未检出 agent CLI 且原生网关未启用（config llm_gateway.enabled=true）——sms-shell 只经数据流执行，本体不作答"); return None
    spec = adapters()[ag]; conv = chains.session_id(); chains.record("session", "open:" + conv); st("开新对话：" + conv)
    want = _state("current_agent")
    if want and want != ag and not spec.get("native"): on_line("注意：所选 agent " + want + " 未检出，本次经 " + ag + " 执行（:agents 查看）")
    sid2, inj = skill_route.route(text, SMS); st("技能路由：" + (sid2 and ("命中 " + sid2 + "·已记 skill_call 链") or "未命中·注入技能全表"))
    body = text if not prefix_on() else chains.conversation(text + "\n\n[" + SKILL_DIRECTIVE + "]\n" + inj); st("压缩记忆·提示词组装")
    chains.record("dialogue", "user@" + conv + " " + text[:200]); rc = 0; st("网关流式执行" if spec.get("native") else "agent CLI 执行：" + ag)
    if spec.get("native"):
        bl = body.split("\n"); imgs = None
        if bl[-1].startswith("[图:") and bl[-1].endswith("]"):
            p = bl[-1][3:-1].strip(); body = "\n".join(bl[:-1]); imgs = [p] if os.path.isfile(p) else None
        gateway.run(body, on_line, images=imgs)
    else:
        args, env = list(spec.get("args", [])), dict(os.environ, PYTHONIOENCODING="utf-8"); env.update(spec.get("env") or {}); stdin = subprocess.PIPE if spec.get("prompt_stdin") else subprocess.DEVNULL
        p = subprocess.Popen([spec.get("bin", ag)] + args + ([] if stdin else [body]), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
        if spec.get("prompt_stdin"): p.stdin.write(body); p.stdin.close()
        for ln in iter(p.stdout.readline, ""):
            if ln.strip(): on_line(ln.rstrip())
        rc = p.wait()
    chains.record("session", "close:" + conv); chains.record("time", "对话 " + conv + " 收口 rc=" + str(rc)); st("对话收口 rc=" + str(rc)); return {"agent": ag, "rc": rc, "conv": conv}
