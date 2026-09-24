#!/usr/bin/env python3
"""shell.py — sms-shell 交互壳：在命令行操作已安装的 agent 客户端来使用 SMS 与 skills——列 skills/agents、指令系统（cmds/intent/use/alias 个性化指令）、session/grant 授权、hud 顶面提示、deploy 部署到其他目录；一律转 SMS 脚本执行，SMS 本体不作答。"""
import os, sys, json, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import resolve_home
sms = resolve_home.ensure()
HELP = ("skills | agents | cmds [name] | intent <text> | use <name> [args] | alias <name> --desc= --args= --step= | unalias <name> | "
        "session \"<task>\" | grant <key|role> [min] | hud session|step|alert <text> | hud hide | deploy <dir|--clients a,b> [--skills all] [--write] | quit")
def run(name, args):
    p = subprocess.run([sys.executable, "-B", os.path.join(S, name)] + list(args), capture_output=True, text=True)
    out = (p.stdout or p.stderr).strip()
    try: return json.dumps(json.loads(out), ensure_ascii=False, indent=2)
    except Exception: return out or "(no output)"
def registry(key):
    try: return json.load(open(os.path.join(sms, "registry", key), encoding="utf-8"))
    except Exception: return {}
def main():
    print("sms-shell — SMS 指令壳（help 看命令，quit 退出）· SMS_HOME=" + sms)
    while True:
        try: line = input("sms> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not line: continue
        parts = line.split(); c, a = parts[0], parts[1:]
        if c in ("quit", "exit"): break
        elif c == "help": print(HELP)
        elif c == "skills": print("\n".join(s.get("id", "?") + " [" + s.get("kind", "?") + "] " + s.get("trust", "") for s in registry("register.json").get("skills", [])) or "无注册表：init_registry.py --write")
        elif c == "agents": print("\n".join(k + " -> " + v for k, v in sorted(__import__("sync_skills").clients().items())) or "未检出已安装 agent 客户端")
        elif c == "cmds": print(run("commands.py", ["help"] if not a else ["show"] + a))
        elif c == "intent": print(run("commands.py", ["intent"] + a))
        elif c == "use": print(run("commands.py", ["use"] + a))
        elif c == "alias": print(run("user_commands.py", ["add"] + a))
        elif c == "unalias": print(run("user_commands.py", ["rm"] + a))
        elif c == "session": print(run("session.py", a))
        elif c == "grant": print(run("permissions.py", ["grant"] + a + ["--write"]))
        elif c == "hud": print(run("hud.py", a))
        elif c == "deploy": print(run("deploy.py", a))
        else: print("未知命令：" + c + "（help）")
if __name__ == "__main__":
    main()
