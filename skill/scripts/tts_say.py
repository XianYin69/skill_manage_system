#!/usr/bin/env python3
"""tts_say.py — 阿林娜（alina）SAPI5 合成后端（被 tts.py 引用·文本不出本机）：voices 枚举系统语音；speak 逐段 PowerShell Add-Type System.Speech 播报（SSML rate/pitch/volume 由 settings 取值·属性双引号合法 XML〔旧版单引号致 SpeakSsml 抛错被 DEVNULL 吞＝无声根因〕·语音名按前缀容错匹配·无启用语音明确报错·here-string 定界独立成行防 '@ 文本崩溃·wait 模式供 CLI 且回传失败原因）；clean 去 markdown/控制前缀（** ` # 链接 URL $ ▸ ⧉ ≡ sms> 等）；chunks 按句切 ≤cap 段（修复旧版整段截 400 字朗读不完整与噪音符号）。"""
import os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import settings
_MD = re.compile(r"\$[^\s]*|▸|⧉|≡|sms>|●|◀|\*\*|__|`{1,3}|~~|#{1,6}\s+|\((?=[^\)]*https?://)|https?://\S+|!\[[^\]]*\]|\[[^\]]*\]\([^)]*\)|\[\d+\]")
def clean(s): return re.sub(r"\s+", " ", _MD.sub(" ", str(s))).strip()
def chunks(s, cap):
    out, buf = [], ""
    for sent in re.split(r"(?<=[。！？；!?;\n])", str(s)):
        buf += sent
        if len(buf) >= cap: out.append(buf.strip()); buf = ""
    return out + ([buf.strip()] if buf.strip() else [])
_PS_ENUM = "Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name}"
def voices():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", _PS_ENUM], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return "\n".join(x for x in (r.stdout or "").splitlines() if x.strip()) or ("ERR " + (r.stderr or "无语音").strip()[:200])
    except Exception as e: return "ERR 枚举语音失败：" + str(e)[:150]
def _ssml(text):
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN"><prosody rate="%s%%" pitch="%s" volume="%s%%">%s</prosody></speak>' % (int(float(settings.get("tts.rate", -1)) * 10), settings.get("tts.pitch", "+0st"), int(settings.get("tts.volume", 100)), t)
def _ps(text):
    v = str(settings.get("tts.voice", "") or "Microsoft Huihui").replace("'", "''")
    return "\n".join(["Add-Type -AssemblyName System.Speech", "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "$n=@(($s.GetInstalledVoices()|Where-Object{$_.Enabled}).VoiceInfo.Name)",
        "if($n.Count -eq 0){[Console]::Error.WriteLine('系统无已启用语音（安装中文语音包后再试）');exit 3}",
        "$w=$n|Where-Object{$_ -eq '%s' -or $_ -like '%s*'}|Select-Object -First 1; if(-not $w){$w=$n|Where-Object{$_ -match 'Huihui|Xiaoxiao|Kangkang|Yaoyao|Chinese|中文'}|Select-Object -First 1}; if($w){$s.SelectVoice($w)}" % (v, v),
        "$x=@'", _ssml(text[:600]), "'@",
        "try{$s.SpeakSsml($x)}catch{[Console]::Error.WriteLine($_.Exception.Message);exit 2}"])
def speak(text, wait=False):
    if not (text or "").strip(): return ""
    try:
        if wait:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", _ps(text)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            return "done" if r.returncode == 0 else "ERR 朗读失败：" + ((r.stderr or "").strip() or "rc=%d（无输出设备/语音异常）" % r.returncode)[:200]
        return subprocess.Popen(["powershell", "-NoProfile", "-Command", _ps(text)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
    except Exception as e: return "ERR 朗读失败：" + str(e)[:150]
