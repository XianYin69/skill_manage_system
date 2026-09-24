#!/usr/bin/env python3
"""agent_stream.py — sms-shell 数据流引擎：检测电脑上已安装 agent 的非交互 CLI（claude/codex/kilocode/kilo/cursor/aider，可经用户配置 agent_cli 增改 {bin,args}），把用户话语（默认前置「使用 skill_manage_system 技能」指令）以参数送入 CLI、stdout 逐行流回回调；选中 agent 与技能前缀开关等状态只存 <SMS_HOME>/shell/；未检出 CLI 时明确拒绝（SMS 本体不作答）。"""
import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home
SMS = resolve_home.ensure()
STATE = os.path.join(SMS, "shell")
ADAPTERS = {"claude": {"bin": "claude", "args": ["-p"]}, "codex": {"bin": "codex", "args": ["exec"]},
            "cursor": {"bin": "cursor-agent", "args": []}, "kilocode": {"bin": "kilocode", "args": ["run"]},
            "kilo": {"bin": "kilo", "args": ["run"]}, "aider": {"bin": "aider", "args": ["--message"]}}
SKILL_DIRECTIVE = "使用 skill_manage_system 技能完成本请求（SMS 只调取·管理技能并整合结果，不得以模型知识代答）："
def adapters():
    extra = {k: v for k, v in (resolve_home.conf(SMS).get("agent_cli") or {}).items() if not k.startswith("_") and isinstance(v, dict)}
    return dict(ADAPTERS, **extra)
def detected():
    return {k: v for k, v in adapters().items() if shutil.which(v.get("bin", k))}
def _state(name, default=""):
    try: return open(os.path.join(STATE, name), encoding="utf-8").read().strip()
    except Exception: return default
def _put(name, val): os.makedirs(STATE, exist_ok=True); open(os.path.join(STATE, name), "w", encoding="utf-8").write(val)
def current():
    cur = _state("current_agent"); return cur if cur in detected() else next(iter(sorted(detected())), None)
def prefix_on(): return _state("skill_prefix", "on") != "off"
def use(name): _put("current_agent", name); return "切到 agent：" + name + ("" if name in detected() else "（未检出其 CLI——配置 agent_cli {bin,args} 并确保在 PATH）")
def skill(on): _put("skill_prefix", "on" if on else "off"); return "skill_manage_system 前缀：" + _state("skill_prefix", "on")
def ask(text, on_line):
    ag = current()
    if not ag:
        on_line("拒绝：未检出任何已安装 agent 的 CLI（候选：" + "、".join(adapters()) + "）。sms-shell 只经数据流操作已装 agent，本体不作答——请安装 agent 或在 <SMS_HOME>/config/config.json 配 agent_cli。")
        return None
    spec = adapters()[ag]; prompt = (SKILL_DIRECTIVE if prefix_on() else "") + text
    args, env = list(spec.get("args", [])), dict(os.environ, PYTHONIOENCODING="utf-8")
    use_stdin = bool(spec.get("prompt_stdin"))
    p = subprocess.Popen([spec.get("bin", ag)] + args + ([] if use_stdin else [prompt]), stdin=subprocess.PIPE if use_stdin else None,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
    if use_stdin: p.stdin.write(prompt); p.stdin.close()
    for ln in iter(p.stdout.readline, ""):
        if ln.strip(): on_line(ln.rstrip())
    p.wait()
    return {"agent": ag, "rc": p.returncode}
