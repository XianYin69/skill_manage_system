#!/usr/bin/env python3
"""shell_tui_index.py — sms-shell TUI 索引/链接 mixin（被 ShellApp 混入·与 shell_tui_menus.Menus 组合）：F2/「/」＝SKILL.md 技能索引菜单（每项＝技能名＋其 SKILL.md frontmatter description 介绍·与文件索引分离）；F5＝文件索引菜单（用户索引项 /名称→路径＋首项＋索引文件/文件夹→shell_tui_files 可浏览并选定文件夹中的文件）；选项以「/名称」插入输入行（user_index.fill），提交时 core.handle 经 user_index.expand 就地展开；技能路由命中（红线17 须开子会话）→主输出区自动给出「链接子对话提示」并备好子会话调用语句（open_subconv 填入输入行＋聚焦＋记 subsession 链·不自动发送以免意外，回车确认即开）；配置写库后 on_config_change 即时刷新顶栏数据流（settings 本无缓存·每次读写即时读文件）。"""
import os, re
import shell_core as core, user_index
from rich.text import Text
class Index:
    def _fdesc(self, s):
        try:
            t = open(os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md"))), encoding="utf-8", errors="ignore").read(4000)
            m = re.search(r"(?m)^description:\s*(.+)$", t.split("---", 2)[1] if t.startswith("---") else t)
            return re.sub(r"\s+", " ", (m.group(1) if m else str(s.get("description") or ""))).strip()[:56]
        except Exception: return str(s.get("description") or "")[:56]
    def action_menu_skill_index(self):
        import skill_route
        rows = [("tok:" + str(s.get("id", "")), "%s｜%s" % (s.get("id"), self._fdesc(s))) for s in skill_route.skills()] or [(":cmds", "注册表为空：先跑 register.py")]
        self.menu("SKILL.md 索引·技能（名称＋介绍 · Enter 插入 /技能名 · F5＝文件索引）", rows)
    def action_menu_files(self):
        rows = [("#pick_file", "＋ 索引文件/文件夹：浏览选定即插 /名称（文件夹＝登记扫描根＋索引）")]
        rows += [("tok:" + x["name"], "/%s（%s）→ %s" % (x["name"], x["kind"], x["path"])) for x in user_index.load()]
        self.menu("文件索引（用户索引项 · Enter 插入 /名称 · F2＝技能索引）", rows)
    def action_pick_file(self):
        from shell_tui_files import Files
        self.push_screen(Files(), self._file_picked)
    def _file_picked(self, path):
        if not path: return
        if getattr(self, "_ws_pick", False): self._ws_pick = False; self.ws_indexed(path); return
        if os.path.isdir(path): self.log_line(core.run_script("register.py", ["--add-root", path, "--write"]))
        self.log_line(user_index.add(path))
    def subconv_hint(self):
        for s in getattr(self, "steps", []):
            if not s.startswith("技能路由：命中"): continue
            for sid in s.split("命中", 1)[1].split("·")[0].split(","):
                sid = sid.strip()
                if not sid: continue
                t = Text("⧉ 检测到目标技能 " + sid + " 须开子会话执行（红线17）→ 已备好链接子对话　", style="bold #f9e2af")
                t.append("[" + sid + " 子对话] 待回车确认 · 或输入 /" + sid, style="bold #89b4fa underline")
                self.log_line(t); self.open_subconv(sid, only_empty=True)
    def open_subconv(self, sid, only_empty=False):
        try:
            import chains; chains.log("sub", sid)
        except Exception: pass
        ta = self.query_one("#input")
        if only_empty and ta.text.strip(): return sid
        ta.text = "请为托管技能 " + sid + " 另开新子会话按其 SKILL.md 执行（子会话收口即停）："; ta.focus(); return sid
    def on_config_change(self, path):
        self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
