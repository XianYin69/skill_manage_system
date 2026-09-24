#!/usr/bin/env python3
"""sms_formats.py — 多格式 skill 适配层（bin 纯标准库，被 sms_api.py 调用）：claude＝Agent Skills 标准 SKILL.md（YAML frontmatter，Claude Code 与 Anthropic API 同一格式）；claude-code＝项目级 CLAUDE.md＋.claude/commands 斜杠指令；openai 全系＝Chat Completions tools 函数 schema、Responses API、Assistants API instructions、realtime 与 Codex 的 SKILL.md＋SKILL.json（目录族 openai/*）。"""
import os, re, json

def load(path):
    rows = open(path, encoding="utf-8").read().splitlines()
    meta, body = {}, "\n".join(rows)
    if rows and rows[0].strip() == "---":
        i = next((j for j in range(1, len(rows)) if rows[j].strip() == "---"), -1)
        for ln in rows[1:i]:
            if ":" in ln and not ln.startswith(("-", " ", "\t")):
                k, v = ln.split(":", 1); meta[k.strip()] = v.strip().strip("\"'")
        body = "\n".join(rows[i + 1:]).strip()
    return meta, body

def openai_name(meta, path):
    n = (meta.get("name") or os.path.basename(os.path.dirname(os.path.abspath(path)))).lower().replace("-", "_")
    n = re.sub(r"[^a-z0-9_]", "", n)[:64]
    return n or "sms_skill"

def tool(meta, path):
    return {"type": "function", "function": {"name": openai_name(meta, path), "description": (meta.get("description") or "")[:1024],
            "strict": False, "parameters": {"type": "object", "properties": {"request": {"type": "string", "description": "用户的完整需求"}}, "required": ["request"]}}}

FORMATS = {"claude": "Agent Skills SKILL.md——Claude Code 与 Anthropic API skills 同格式",
           "claude-code": "CLAUDE.md＋.claude/commands/<id>.md 斜杠指令",
           "openai": "全系：chat/Responses tools JSON、Assistants instructions、realtime/Codex 技能目录（openai/*）"}

def convert(skill_md, out_dir):
    meta, text = load(skill_md); out = os.path.abspath(out_dir)
    tj = json.dumps(tool(meta, skill_md), ensure_ascii=False, indent=2)
    files = [(os.path.join(out, "SKILL.md"), open(skill_md, encoding="utf-8").read()),
             (os.path.join(out, "CLAUDE.md"), "# %s\n\n%s\n" % (meta.get("name", ""), text)),
             (os.path.join(out, ".claude", "commands", openai_name(meta, skill_md) + ".md"), (meta.get("description") or "") + "\n\n$ARGUMENTS\n"),
             (os.path.join(out, "openai", "chat_tool.json"), tj), (os.path.join(out, "openai", "responses_tool.json"), tj),
             (os.path.join(out, "openai", "assistant_instructions.md"), (meta.get("description") or text) + "\n"),
             (os.path.join(out, "openai", "realtime", "SKILL.md"), text),
             (os.path.join(out, "openai", "realtime", "SKILL.json"), tj)]
    return {"id": openai_name(meta, skill_md), "description": meta.get("description", ""),
            "frontmatter_ok": bool(meta.get("name") and meta.get("description")), "files": files}
