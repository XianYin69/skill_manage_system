#!/usr/bin/env python3
"""shell_core.py — sms-shell 共享命令引擎（TUI/GUI 前端通用）：skills/agents 列表、指令系统（cmds/intent/use/alias 个性化指令）、session/grant 授权、hud 顶面提示、deploy 部署到其他目录；一律转调 SMS 脚本，SMS 本体不作答。"""
import os, sys, json, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import resolve_home
SMS = resolve_home.ensure()
HELP = ("skills | agents | cmds [name] | intent <text> | use <name> [args] | alias <name> --desc= --args= --step= | unalias <name> | "
        "session \"<task>\" | grant <key|role> [min] | hud session|step|alert <text> | hud hide | deploy <dir|--clients a,b> [--skills all] [--write] | tui | gui | quit")
BANNER = "sms-shell — SMS 指令壳（操作已装 agent 客户端·SMS 本体不作答）· SMS_HOME=" + SMS
def run(name, args):
    p = subprocess.run([sys.executable, "-B", os.path.join(S, name)] + list(args), capture_output=True, text=True)
    out = (p.stdout or p.stderr).strip()
    try: return json.dumps(json.loads(out), ensure_ascii=False, indent=2)
    except Exception: return out or "(no output)"
def registry(key):
    try: return json.load(open(os.path.join(SMS, "registry", key), encoding="utf-8"))
    except Exception: return {}
def exec_line(line):
    parts = line.split(); c, a = parts[0], parts[1:]
    if c == "skills": return "\n".join(s.get("id", "?") + " [" + s.get("kind", "?") + "] " + s.get("trust", "") for s in registry("register.json").get("skills", [])) or "无注册表：init_registry.py --write"
    if c == "agents":
        import sync_skills
        return "\n".join(k + " -> " + v for k, v in sorted(sync_skills.clients().items())) or "未检出已安装 agent 客户端"
    if c == "cmds": return run("commands.py", ["help"] if not a else ["show"] + a)
    if c == "session": return run("session.py", a)
    if c == "grant": return run("permissions.py", ["grant"] + a + ["--write"])
    if c in ("intent", "use"): return run("commands.py", [c] + a)
    if c in ("hud", "deploy"): return run(c + ".py", a)
    if c == "alias": return run("user_commands.py", ["add"] + a)
    if c == "unalias": return run("user_commands.py", ["rm"] + a)
    return None
if __name__ == "__main__":
    print(json.dumps({"engine": "use shell_tui.py / shell_gui.py", "help": HELP}, ensure_ascii=False, indent=2))
