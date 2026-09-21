#!/usr/bin/env python3
"""emit.py — 统一写盘门控：默认预览；仅当 --write 且会话已授予 write 才落盘。"""
import os, json


def write_json(path, doc, sms, dry):
    if dry:
        return json.dumps(doc, ensure_ascii=False, indent=2)
    import permissions
    if not permissions.allow(sms, "write"):
        return "DENIED: 会话未授予 write 权限（permissions.json），拒绝写盘"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "OK " + path