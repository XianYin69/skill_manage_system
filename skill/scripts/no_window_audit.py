#!/usr/bin/env python3
"""no_window_audit.py — 静态审计：禁止裸 subprocess/os.system 调用点（闪黑框·抢前台根因）。

口径：AST 解析（注释与文档字符串里的字样不算命中）——
· subprocess.run|Popen|call|check_output|check_call、os.system|os.popen 一律违规；
· `from subprocess import run…` / `from os import system` 同样违规（别名绕过）；
· 例外①白名单文件 no_window.py＝静默封装本体；
· 例外②调用行或其上两行含标记 `# sms-visible`＝有意可见控制台（GUI 起 TUI、入口交棒壳）。
一切子进程须经 no_window.run/Popen；需脱离父进程仍保 DETACHED 语义者传 sms_detach=True
（封装内 OR 合并 creationflags，绝不丢原标志）。
用法：python -B no_window_audit.py [扫描根]；有违规 exit 1（sms.py doctor 已接入）。
"""
import ast, json, os, sys

CALLS = ("run", "Popen", "call", "check_output", "check_call")
MARK = "# sms-visible"
WHITELIST = {"no_window.py": "静默子进程封装本体：唯一允许直接触碰 subprocess 的模块"}
PRUNE = {".git", ".kilo", "__pycache__", ".pytest_cache", "tmp", "SMS", "registry",
         "sessions", "workspaces", "node_modules", "vendor", "dependence", "deps"}


def _marked(lines, lineno):
    """调用行本身或其上两行带 # sms-visible 即视为有意可见控制台。"""
    return any(MARK in ln for ln in lines[max(0, lineno - 3):lineno])


def hits(src, name=""):
    """返回该源码的裸子进程调用点列表 [{line, why, file}]。"""
    lines = src.splitlines()
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"line": e.lineno or 0, "why": "无法解析（语法错误）：%s" % e.msg, "file": name}]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                mod, attr = f.value.id, f.attr
                if mod == "subprocess" and attr in CALLS and not _marked(lines, node.lineno):
                    out.append({"line": node.lineno, "why": "subprocess." + attr, "file": name})
                elif mod == "os" and attr in ("system", "popen") and not _marked(lines, node.lineno):
                    out.append({"line": node.lineno, "why": "os." + attr, "file": name})
        elif isinstance(node, (ast.ImportFrom,)):
            if node.module == "subprocess" and any(a.name in CALLS for a in node.names):
                if not _marked(lines, node.lineno):
                    out.append({"line": node.lineno, "why": "from subprocess import 别名绕过", "file": name})
            elif node.module == "os" and any(a.name in ("system", "popen") for a in node.names):
                if not _marked(lines, node.lineno):
                    out.append({"line": node.lineno, "why": "from os import system/popen", "file": name})
    return out


def _py_files(root):
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in PRUNE]
        for f in sorted(fs):
            if f.endswith(".py") and f not in WHITELIST:
                yield os.path.join(d, f)


def scan(root):
    """扫描根 → {"root","scanned","violations","whitelist"}。"""
    bad = []
    n = 0
    for p in _py_files(root):
        n += 1
        try:
            src = open(p, encoding="utf-8").read()
        except Exception as e:
            bad.append({"line": 0, "why": "读取失败：%s" % str(e)[:80], "file": p})
            continue
        bad += hits(src, os.path.relpath(p, root))
    return {"root": root, "scanned": n, "violations": bad,
            "whitelist": WHITELIST, "marker": MARK}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(here))
    r = scan(root)
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(1 if r["violations"] else 0)


if __name__ == "__main__":
    main()
