#!/usr/bin/env python3
"""qq_bind.py 鈥?QQ 鏈哄櫒浜烘壂鐮佺粦瀹氾紙绾?Python 澶嶅埢 @tencent-connect/qqbot-connector 1.2.0 鍗忚路鍏?Node 杩愯鏃讹級锛歅OST https://q.qq.com/lite/create_bind_task {key:base64(32B)} 鈫?data.task_id锛涙壂鐮侀〉 https://q.qq.com/qqbot/openclaw/connect.html?task_id=..&source=..&_wv=2锛堟墜鏈?QQ 鎵爜鎴栨祻瑙堝櫒鎵撳紑锛夛紱POST /lite/poll_bind_result {task_id} 鈫?data{status 0NONE/1PENDING/2COMPLETED/3EXPIRED, bot_appid, bot_encrypt_secret, user_openid}锛沘ppSecret锛滱ES-256-GCM(key=base64decode(key), iv=鍓?2瀛楄妭, tag=鍚?6瀛楄妭, ct=涓棿) 瑙?bot_encrypt_secret锛涘叧閿孩鍒╋紳缁戝畾鍥炴墽鑷甫 user_openid锛屾晠鏃犻渶鐢ㄦ埛鍏堢粰鏈哄櫒浜哄彂娑堟伅鍗冲彲涓诲姩鎺ㄩ€併€傚嚟鎹惤 <SMS_HOME>/config/qq.json锛堟棫鍊煎浠?.bak锛夈€備簩缁寸爜锛濊浜?segno/qrcode 鎵撳嵃 ASCII锛屽惁鍒欐墦鍗伴摼鎺ャ€傜敤娉曪細python -B qq_bind.py [source] [--timeout 300] [--appid A --secret S --openid O 鎵嬪伐褰曞叆]"""
import os, sys, json, time, base64, secrets, urllib.request as U
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home
HOST = "https://q.qq.com"
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
            import importlib; fn(importlib.import_module(mod)); return "璇风敤鎵嬫満 QQ 鎵笂鏂逛簩缁寸爜"
        except Exception: pass
    return "鏈 segno/qrcode鈥斺€旇鐢ㄦ墜鏈?QQ 鎴栨祻瑙堝櫒鎵撳紑涓嬫柟閾炬帴瀹屾垚缁戝畾"
