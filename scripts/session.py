#!/usr/bin/env python3
"""session.py — 在 SMS/sessions/<日期>/ 建立五元组（对话/用户链/逻辑链/技能/权限）。"""
import os, sys, json, time

DATE = time.strftime("%Y-%m-%d")


def create(sms, intent, write=False):
    d = os.path.join(sms, "sessions", DATE)
    os.makedirs(d, exist_ok=True)
    files = {
        "dialogue.md": f"# 对话 · {DATE}\n\n## 意图\n{intent}\n\n## 记录\n",
        "user_chain.json": {"date": DATE, "intent": intent, "user": None, "context": []},
        "logic_chain.json": {"nodes": [{"id": "n1", "type": "intent", "label": intent}], "edges": []},
        "skills.json": {"used": []},
        "permissions.json": {"date": DATE, "grants": {
            "read": True, "write": write, "execute": False, "network": False}},
    }
    for name, data in files.items():
        p = os.path.join(d, name)
        if os.path.exists(p):
            continue
        if name.endswith(".json"):
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        else:
            open(p, "w", encoding="utf-8").write(data)
    return d


def touch(d, skill_id):
    p = os.path.join(d, "skills.json")
    data = json.load(open(p, encoding="utf-8"))
    if skill_id not in data["used"]:
        data["used"].append(skill_id)
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home
    sms = resolve_home.ensure()
    intent = sys.argv[1] if len(sys.argv) > 1 else "（未填写意图）"
    d = create(sms, intent, "--write" in sys.argv)
    if "--dry-run" in sys.argv:
        print("would create:", d)
    else:
        print("OK", d)