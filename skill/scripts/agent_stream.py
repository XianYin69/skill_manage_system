#!/usr/bin/env python3
"""agent_stream.py — sms-shell 数据流引擎：优先原生网关（config llm_gateway.enabled→gateway，OpenAI 兼容直连、不依赖 CLI），否则检测已装 agent CLI（claude/codex 等，agent_cli 可增改）；每次输入＝新开一次对话（chains.conversation 压缩记忆＋双层规则，红线 17），逐行流回、收口记链；尾行 [图:<路径>] 为网关视觉附图；状态存 <SMS_HOME>/shell/；皆无则拒绝（本体不作答）。"""
import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, dream, gateway
SMS = resolve_home.ensure()
STATE = os.path.join(SMS, "shell")
ADAPTERS = {"claude": {"bin": "claude", "args": ["-p"]}, "codex": {"bin": "codex", "args": ["exec"]}, "cursor": {"bin": "cursor-agent", "args": []}, "kilocode": {"bin": "kilocode", "args": ["run"]}, "kilo": {"bin": "kilo", "args": ["run"]}, "aider": {"bin": "aider", "args": ["--message"]}}
SKILL_DIRECTIVE = "使用 skill_manage_system 技能完成本请求（SMS 只调取·管理技能并整合结果、不得以模型知识代答）；以下已按规则开新对话并附压缩记忆。原始请求："
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
    return cur if cur in det else ("gateway" if "gateway" in det else next(iter(det), None))
def prefix_on(): return _state("skill_prefix", "on") != "off"
def use(name): _put("current_agent", name); return "切到 agent：" + name + ("" if name in detected() else "（未检出其 CLI——配置 agent_cli {bin,args} 并确保在 PATH）")
def skill(on): _put("skill_prefix", "on" if on else "off"); return "skill_manage_system 前缀：" + _state("skill_prefix", "on")
def ask(text, on_line):
    dream.maybe(SMS); ag = current()
    if not ag: on_line("拒绝：未检出 agent CLI 且原生网关未启用（config llm_gateway.enabled=true）——sms-shell 只经数据流执行，本体不作答"); return None
    spec = adapters()[ag]; conv = chains.session_id(); chains.record("session", "open:" + conv)
    body = text if not prefix_on() else SKILL_DIRECTIVE + "\n" + chains.conversation(text)
    chains.record("dialogue", "user@" + conv + " " + text[:200]); rc = 0
    if spec.get("native"):
        bl = body.split("\n"); imgs = None
        if bl[-1].startswith("[图:") and bl[-1].endswith("]"):
            p = bl[-1][3:-1].strip(); body = "\n".join(bl[:-1]); imgs = [p] if os.path.isfile(p) else None
        gateway.run(body, on_line, images=imgs)
    else:
        args, env = list(spec.get("args", [])), dict(os.environ, PYTHONIOENCODING="utf-8"); stdin = subprocess.PIPE if spec.get("prompt_stdin") else None
        p = subprocess.Popen([spec.get("bin", ag)] + args + ([] if stdin else [body]), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
        if stdin: p.stdin.write(body); p.stdin.close()
        for ln in iter(p.stdout.readline, ""):
            if ln.strip(): on_line(ln.rstrip())
        rc = p.wait()
    chains.record("session", "close:" + conv); chains.record("time", "对话 " + conv + " 收口 rc=" + str(rc)); return {"agent": ag, "rc": rc, "conv": conv}
