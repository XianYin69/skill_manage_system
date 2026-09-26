#!/usr/bin/env python3
"""tts_say.py — 阿林娜（alina）SAPI5 合成后端（被 tts.py 引用·文本不出本机）：常驻 PowerShell worker 单进程串行播报——旧版每句 spawn 一个 powershell 并行抢说＝叠音＋每次延迟不一样的根因修复。worker 源＝同目录 tts_worker.ps1（ASCII·阻塞式逐行读 stdin·SpeakSsmlAsync＋90s 看门狗；PS5.1 下后台线程跑 scriptblock 会崩进程，故主循环串行），复制缓存到 <SMS_HOME>/shell/ 按 hash 复用（缓存不落 skill 目录·-File 启动免超长 -Command 解析风险）。stdin 行协议 JSON：{op:"s",t,v,r,p,o,a} 朗读（严格串行·说完才取下句，a=1 回 OK 供 wait 同步·看门狗最长 90s）·{op:"q"} 退出；stop()＝终止 worker（正在说的立刻掐断·防关不掉与关后仍排队）。语音按前缀容错切换·空闲随 python 退出由 atexit 收掉。clean 去 markdown/控制前缀；chunks 按句切 ≤cap 段。"""
import os, sys, re, json, threading, subprocess, atexit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import settings
_MD = re.compile(r"\$[^\s]*|▸|⧉|≡|sms>|●|◀|\*\*|__|`{1,3}|~~|#{1,6}\s+|\((?=[^\)]*https?://)|https?://\S+|!\[[^\]]*\]|\[[^\]]*\]\([^)]*\)|\[\d+\]")
def clean(s): return re.sub(r"\s+", " ", _MD.sub(" ", str(s))).strip()
def chunks(s, cap):
    out, buf = [], ""
    for sent in re.split(r"(?<=[。！？；!?;\n])", str(s)): buf += sent; out += [buf.strip()] if len(buf) >= cap else []; buf = "" if len(buf) >= cap else buf
    return out + ([buf.strip()] if buf.strip() else [])
def _esc(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
def voices():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name}"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return "\n".join(x for x in (r.stdout or "").splitlines() if x.strip()) or ("ERR " + (r.stderr or "无语音").strip()[:200])
    except Exception as e: return "ERR 枚举语音失败：" + str(e)[:150]
TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_worker.ps1")
def _wp():  # 模板 → 数据根缓存副本（hash 一致不重写）
    import hashlib, resolve_home; src = open(TPL, encoding="utf-8").read(); p = os.path.join(resolve_home.ensure(), "shell", "tts_worker.ps1"); h = "//" + hashlib.md5(src.encode()).hexdigest()
    if (open(p, encoding="utf-8").read()[-len(h):] if os.path.exists(p) else "") != h: os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(src + "\n" + h)
    return p
W = {"p": None}; L = threading.Lock()
def _params(): return {"v": str(settings.get("tts.voice", "") or "Microsoft Huihui"), "r": int(float(settings.get("tts.rate", -1)) * 10), "p": str(settings.get("tts.pitch", "+0st")), "o": int(settings.get("tts.volume", 100))}
def _bye():
    with __import__("contextlib").suppress(Exception): W["p"] and (W["p"].stdin.write('{"op":"q"}\n'), W["p"].stdin.close())
def _send(op):
    with L:
        if not (p := W["p"]) or p.poll() is not None:
            try: W["p"] = p = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _wp()], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="ascii", errors="replace"); atexit.register(_bye)
            except Exception: W["p"] = None; return None
        try: p.stdin.write(json.dumps(op) + "\n"); p.stdin.flush(); return p
        except Exception: W["p"] = None; return None
def speak(text, wait=False):
    if not (text or "").strip(): return ""
    p = _send(dict(_params(), op="s", t=_esc(text), **({"a": 1} if wait else {})))
    if not wait: return "queued" if p else "ERR 朗读失败：worker 启动失败"
    box = []; th = threading.Thread(target=lambda: box.append((p.stdout.readline() if p else "") or "")); th.daemon = True; th.start(); th.join(90)
    return "done" if box and box[0].strip() == "OK" else "ERR 朗读失败：worker 无回包（无输出设备/语音异常/超时）"
def stop():
    with L:
        p = W["p"]; W["p"] = None
    try: p and p.poll() is None and (p.stdin.write('{"op":"q"}\n'), p.wait(timeout=3))
    except Exception:
        try: p and p.kill()
        except Exception: pass
    return "worker 已停（含掐断当前朗读）"
