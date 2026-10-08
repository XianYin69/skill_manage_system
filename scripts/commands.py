#!/usr/bin/env python3
"""commands.py — 命令系统：汇总 SMS 内置命令与各 skill 暴露接口，支持 help/intent/show/use 查看与调用。"""
import os, sys, json, time

BUILTIN = {"help": "列出所有可用命令", "intent": "按一句话意图匹配候选命令 <utterance>",
           "show": "查看某命令详情 <name>", "use": "使用/调用命令 <name> [args...]（转 dispatch/skill_executor）"}


def _load(sms, rel):
    p = os.path.join(sms, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def collect(sms):
    cmds = [{"name": k, "description": v, "args": "", "source": "sms"} for k, v in BUILTIN.items()]
    for s in _load(sms, "registry/interfaces.json").get("skills", []):
        for it in s.get("interfaces", []):
            nm = it.get("name")
            if nm and all(c["name"] != nm for c in cmds):
                cmds.append({"name": nm, "description": it.get("description", ""), "args": "",
                             "skill_id": s["skill_id"], "source": "skill"})
    return {"schema": "skill_commands", "version": "1.0.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "commands": cmds}


def match(doc, utter):
    u = (utter or "").lower()
    hits = [c["name"] for c in doc["commands"] if c["name"].lower() in u
            or any(t and t in u for t in c["name"].lower().split("_"))]
    return {"utterance": utter, "candidates": hits or [c["name"] for c in doc["commands"][:3]]}


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home, emit
    sms = resolve_home.ensure()
    argv = [x for x in sys.argv[1:] if x != "--write"]; w = "--write" in sys.argv
    doc = collect(sms)
    if w: print(emit.write_json(os.path.join(sms, "registry", "commands.json"), doc, sms, False))
    cmd = argv[0] if argv else "help"; arg = argv[1] if len(argv) > 1 else ""
    names = [c["name"] for c in doc["commands"]]
    if cmd == "help": r = {"commands": names, "detail": doc["commands"]}
    elif cmd == "intent": r = match(doc, arg)
    elif cmd == "show": r = next((c for c in doc["commands"] if c["name"] == arg), {"error": "用法: show <name>"})
    elif cmd == "use": r = {"invoked": arg or None, "args": argv[2:], "next": "转 dispatch.py / skill_executor 执行并回到 SMS"}
    else: r = {"error": "用法: help | intent <utterance> | show <name> | use <name> [args] [--write]"}
    print(json.dumps(r, ensure_ascii=False, indent=2))
