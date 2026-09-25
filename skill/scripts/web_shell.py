#!/usr/bin/env python3
"""web_shell.py — 本地加密网页壳：HTTPS 绑 web_shell.host:port（默认 127.0.0.1:8737），自签指纹证书＋配对 token（常时比较·Host 防重绑定）；页面＝对话（等同 sms-shell 含 : 元指令）、配置系统（llm_gateway/chains/dream/模型参数，api_key 掩码只写不读）、上游模型元数据刷新、链设置与对外端口状态（对外开关属高危面须 confirm=yes，服务本体在 external.py＋PQ 验签）。用法：python -B web_shell.py start|serve|stop|status|token [--rotate]|fingerprint。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net_util, settings, model_meta, web_certs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
NAME = "web_shell"
class H(BaseHTTPRequestHandler):
    server_version = "sms-web"; protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _auth(self): return net_util.check_token(self.headers.get("X-SMS-Token") or self.headers.get("Authorization", "").removeprefix("Bearer ").strip()) and net_util.host_ok(self.headers.get("Host"))
    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"): return net_util.send(self, 200, net_util.page(), "text/html; charset=utf-8")
        if not self._auth(): return net_util.send(self, 401, {"err": "需要配对 token（python -B web_shell.py token / :web token）"})
        if p == "/api/info":
            st = settings.status(); st["fingerprint"] = web_certs.fpr(); st["token_prefix"] = net_util.token()[:6] + "…"
            st["model_meta"]["models"] = model_meta.load().get("models") or {}; return net_util.send(self, 200, st)
        return net_util.send(self, 404, {"err": "404"})
    def do_POST(self):
        p = self.path.split("?")[0]; b = net_util.body(self)
        if not self._auth(): return net_util.send(self, 401, {"err": "需要配对 token"})
        if p == "/api/chat": return net_util.send(self, 200, net_util.chat(b.get("text")))
        if p == "/api/config":
            path = str(b.get("path", ""))
            if not path or path.split(".")[0] in ("comment", ""): return net_util.send(self, 400, {"err": "无效路径"})
            if path.startswith("external") and b.get("confirm") != "yes": return net_util.send(self, 428, {"err": "对外端口属高危面：须 confirm=yes（resistance #16/#18）"})
            return net_util.send(self, 200, {"ok": settings.set(path, b.get("value"))})
        if p == "/api/models/refresh": return net_util.send(self, 200, model_meta.refresh())
        if p == "/api/token/rotate": return net_util.send(self, 200, {"token": net_util.token(True), "hint": "新 token 已写 shell/web.token 并输出到本地终端；旧 token 即刻失效"})
        return net_util.send(self, 404, {"err": "404"})
def serve(host=None, port=None):
    c = settings.eff()[NAME]
    if not c.get("enabled", True): return "web_shell.enabled=false——拒绝启动（:config set web_shell.enabled true）"
    host = host or c.get("host", "127.0.0.1"); port = int(port or c.get("port", 8737))
    srv = ThreadingHTTPServer((host, port), H); srv.socket = net_util.ctx().wrap_socket(srv.socket, server_side=True)
    net_util.write_run(NAME, port); model_meta.maybe()
    print("网页壳 https://%s:%d · 证书指纹 %s · token %s" % (host, port, web_certs.fpr()[:16], net_util.token()))
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: net_util.clear(NAME)
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; cmd = a[0]
    if cmd == "status":
        pid = net_util.running(NAME); port = net_util.port_of(NAME) or settings.get(NAME + ".port", 8737)
        print(json.dumps({"running": pid, "port": port, "url": "https://127.0.0.1:%s/" % port, "fingerprint": web_certs.fpr()[:16]}, ensure_ascii=False))
    elif cmd == "start": print("已在运行 pid=" + str(net_util.running(NAME)) if net_util.running(NAME) else net_util.spawn(NAME))
    elif cmd == "serve": print(serve())
    elif cmd in ("stop", "token", "fingerprint"): print(net_util.stop(NAME) if cmd == "stop" else net_util.token("--rotate" in a) if cmd == "token" else web_certs.fpr())
    else: print(__doc__.strip().splitlines()[-1])
