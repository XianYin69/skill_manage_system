#!/usr/bin/env python3
"""commands.py — 命令系统：汇总内置命令、各 skill 暴露接口与个性化指令（user_commands）→ registry/commands.json；help/intent/show/use 查看调用，alias/unalias 定义个性化指令格式（如 skill-update→迭代 skill），hud/deploy/shell/temp/sandbox/privacy 入口路由；SMS 本体不作答。"""
import os, sys, json, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = {"help": "列出所有命令（内置/skill 接口/个性化）", "intent": "按一句话意图匹配候选命令 <utterance>",
  "show": "查看某命令详情 <name>", "use": "调用命令 <name> [args...]（个性化=展开步骤并执行；其余转 dispatch/skill_executor，SMS 不作答）",
  "alias": "定义个性化指令 <name> --desc= --args=a,b --step='script:|delegate:|say:..' [--write]", "unalias": "删除个性化指令 <name> [--write]",
  "temp": "子 skill 未指定路径的新建目录 → <SMS_HOME>/tmp", "sandbox": "SMS 沙盒 create/list/deliver/clean",
  "privacy": "背景隐私采集 notice/collect/open（须 grant privacy，每笔告知）", "hud": "界面顶面 HUD session/step/alert/hide（置顶·穿透·不抢焦点，任务进行时提示）",
  "shell": "sms-shell 交互壳（操作已安装 agent 用 SMS 与 skills、按指令部署到其他目录）", "deploy": "部署 SMS/托管 skills 到其他目录或客户端（默认预览，--write 执行）"}
ROUTE = {"alias": "user_commands.py", "unalias": "user_commands.py", "temp": "resolve_home.py", "sandbox": "sandbox.py", "privacy": "privacy.py", "hud": "hud.py", "deploy": "deploy.py", "shell": "shell.py"}
def _load(sms, rel): return json.load(open(os.path.join(sms, rel), encoding="utf-8")) if os.path.exists(os.path.join(sms, rel)) else {}
def collect(sms):
    import user_commands
    cmds = [{"name": k, "description": v, "args": "", "source": "sms"} for k, v in BUILTIN.items()]
    for s in _load(sms, "registry/interfaces.json").get("skills", []):
        for it in s.get("interfaces", []):
            nm = it.get("name")
            if nm and all(c["name"] != nm for c in cmds): cmds.append({"name": nm, "description": it.get("description", ""), "args": "", "skill_id": s["skill_id"], "source": "skill"})
    for c in user_commands.load(sms)["commands"]:
        if all(x["name"] != c["name"] for x in cmds): cmds.append({"name": c["name"], "description": c.get("description", ""), "args": " ".join(c.get("arg_names", [])), "source": "user"})
    return {"schema": "skill_commands", "version": "1.1.0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "commands": cmds}
def match(doc, utter):
    u = (utter or "").lower()
    hits = [c["name"] for c in doc["commands"] if c["name"].lower() in u or any(t and t in u for t in c["name"].lower().replace("-", "_").split("_"))]
    return {"utterance": utter, "candidates": hits or [c["name"] for c in doc["commands"][:3]]}
def route(cmd, raw):
    name = ROUTE[cmd]; pre = {"alias": ["add"], "unalias": ["rm"]}.get(cmd, [])
    argvx = [sys.executable, "-B", os.path.join(HERE, name)] + pre + (raw if cmd == "temp" else raw[1:])
    if cmd == "shell": os.execv(sys.executable, argvx)
    p = subprocess.run(argvx, capture_output=True, text=True)
    return {"route": name, "out": (p.stdout or p.stderr).strip()[:2000]}
if __name__ == "__main__":
    sys.path.insert(0, HERE)
    import resolve_home, emit, user_commands
    sms = resolve_home.ensure()
    raw = sys.argv[1:]; argv = [x for x in raw if x != "--write"]; w = "--write" in raw
    cmd = argv[0] if argv else "help"; arg = argv[1] if len(argv) > 1 else ""
    if cmd in ROUTE: print(json.dumps(route(cmd, raw), ensure_ascii=False, indent=2)); sys.exit(0)
    doc = collect(sms)
    if w: print(emit.write_json(os.path.join(sms, "registry", "commands.json"), doc, sms, False))
    names = [c["name"] for c in doc["commands"]]
    if cmd == "help": r = {"commands": names, "detail": doc["commands"]}
    elif cmd == "intent": r = match(doc, arg)
    elif cmd == "show": r = next((c for c in doc["commands"] if c["name"] == arg), {"error": "用法: show <name>"})
    elif cmd == "use":
        uc = user_commands.load(sms)
        r = user_commands.run(sms, arg, argv[2:]) if user_commands.find(uc, arg) else {"invoked": arg or None, "args": argv[2:], "next": "转 dispatch.py / skill_executor 执行并回到 SMS"}
    else: r = {"error": "用法: help | intent <utterance> | show <name> | use <name> [args] | alias|unalias <name> [opts] | temp|sandbox|privacy|hud|deploy|shell [args]"}
    print(json.dumps(r, ensure_ascii=False, indent=2))
