#!/usr/bin/env python3
"""qq_bind.py — QQ 机器人扫码绑定（纯 Python 复刻 @tencent-connect/qqbot-connector 1.2.0 协议·无 Node 运行时）：POST https://q.qq.com/lite/create_bind_task {key:base64(32B)} → data.task_id；扫码页 https://q.qq.com/qqbot/openclaw/connect.html?task_id=..&source=..&_wv=2（手机 QQ 扫码或浏览器打开）；POST /lite/poll_bind_result {task_id} → data{status 0NONE/1PENDING/2COMPLETED/3EXPIRED, bot_appid, bot_encrypt_secret, user_openid}；appSecret＝AES-256-GCM(key=base64decode(key), iv=前12字节, tag=后16字节, ct=中间) 解 bot_encrypt_secret；关键红利＝绑定回执自带 user_openid，故无需用户先给机器人发消息即可主动推送。凭据落 <SMS_HOME>/config/qq.json（旧值备份 .bak）。二维码＝装 segno/qrcode 打印 ASCII，否则打印链接。用法：python -B qq_bind.py [source] [--timeout 300] [--appid A --secret S --openid O 手工录入]"""
import os, sys, json, time, base64, secrets, urllib.request as U
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home
HOST = "https://q.qq.com"
def _post(path, body):
    req = U.Request(HOST + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Accept": "application/json"})
    with U.urlopen(req, timeout=10) as r: return json.loads(r.read().decode("utf-8", "replace") or "{}")
def genkey(): return base64.b64encode(secrets.token_bytes(32)).decode()
def create(key):
    d = _post("/lite/create_bind_task", {"key": key})
    if d.get("retcode") != 0 or not (d.get("data") or {}).get("task_id"): raise RuntimeError(d.get("msg") or json.dumps(d, ensure_ascii=False)[:160])
    return d["data"]["task_id"]
def poll(tid):
    d = _post("/lite/poll_bind_result", {"task_id": tid})
    if d.get("retcode") != 0: raise RuntimeError(d.get("msg") or "poll_bind_result failed")
    x = d.get("data") or {}
    return int(x.get("status") or 0), str(x.get("bot_appid") or ""), x.get("bot_encrypt_secret") or "", x.get("user_openid") or ""
def decrypt(sec_b64, key_b64):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    n, k = base64.b64decode(sec_b64), base64.b64decode(key_b64)
    return AESGCM(k).decrypt(n[:12], n[12:-16], n[-16:]).decode("utf-8")
def qurl(tid, source=""): return "%s/qqbot/openclaw/connect.html?task_id=%s&source=%s&_wv=2" % (HOST, tid, source)
def show(u):
    for mod, fn in (("segno", lambda m: print(m.make(u, error="M").terminal())), ("qrcode", lambda m: m.make(u).print_ascii())):
        try:
            import importlib; fn(importlib.import_module(mod)); return "请用手机 QQ 扫上方二维码"
        except Exception: pass
    return "未装 segno/qrcode——请用手机 QQ 或浏览器打开下方链接完成绑定"
