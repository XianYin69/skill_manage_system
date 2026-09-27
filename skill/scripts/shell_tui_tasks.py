#!/usr/bin/env python3
"""shell_tui_tasks.py — 右栏「任务表」数据源（2026-09-26 批4 用户需求：触发 task 工具时右栏自动出现任务表·含已完成/未完成任务）：task 工具（agent_task.py）每拆/每完成一笔子任务都落 <SMS_HOME>/tasks/<id>.json，本模块即读该真源——rows(sms) 返回末 3 任务的 (文本行, 样式) 列表：任务头＝id 尾段＋完成数/总数＋意图截断＋〔已完成〕/〔进行中〕，子任务行＝✓ done／▶ running／✗ failed／○ pending＋目标截断；无任务文件＝返回空表由 Side 显示占位。纯函数零 UI 依赖，Side 5s 节流刷新即“自动创建”（task 信封本身已实时写 app.task_prog 上顶栏）。"""
import os, json
MARK = {"done": "✓ ", "running": "▶ ", "failed": "✗ ", "pending": "○ "}
def rows(sms, limit=3, sub=6):
    d = os.path.join(sms, "tasks"); out = []
    if not os.path.isdir(d): return out
    for fn in sorted(os.listdir(d), key=lambda x: x[:-5])[-limit:]:
        try: doc = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        except Exception: continue
        subs = doc.get("subtasks") or []; dn = sum(1 for x in subs if x.get("status") == "done")
        head = "%s｜%d/%d｜%s%s" % (str(doc.get("id", fn))[-14:], dn, len(subs), str(doc.get("intent", ""))[:22], "〔已完成〕" if subs and dn == len(subs) else "〔进行中〕" if subs else "〔无子任务〕")
        out.append((head, "bold #cba6f7"))
        for s in subs[:sub]:
            st = s.get("status", "pending")
            out.append((MARK.get(st, "○ ") + s.get("id", "?") + " " + str(s.get("goal", ""))[:26], "#a6e3a1" if st == "done" else "#f9e2af" if st == "running" else "#f38ba8" if st == "failed" else "dim"))
        if len(subs) > sub: out.append(("…其余 %d 项（task_detail %s）" % (len(subs) - sub, doc.get("id")), "dim"))
    return out
