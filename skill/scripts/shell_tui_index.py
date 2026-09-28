#!/usr/bin/env python3
"""shell_tui_index.py — sms-shell TUI 索引/链接 mixin（被 ShellApp 混入·与 shell_tui_menus.Menus/shell_tui_mode.Mode 组合）：F2/「/」＝SKILL.md 技能索引菜单（每项＝技能名＋其 SKILL.md frontmatter description 介绍·与文件索引分离·首项➕按路径输入加入 skill）；F5＝文件索引菜单（用户索引项 /名称→路径＋首项＋索引文件/文件夹→shell_tui_files 可浏览并选定文件夹中的文件）；选项以「/名称」插入输入行（user_index.fill·光标随插入跳末尾），提交时 core.handle 经 user_index.expand 就地展开；技能路由〔批16 参考句〕＝步骤名「路由参考：打分命中…」只提示不裁决（模型自主决定直答或派发），subconv_hint 仅提示参考命中与 :dispatch 重派入口（不再回填自引用语句——旧版连开 8 空对话死循环根因），open_subconv 保留为填 `:dispatch <id> ` 治理令牌（非路由话语·不再死循环）；F8＝action_editor 选文件开 shell_tui_editor 编辑器/查看器；_ev 收 msg_flow 信封：task 进度写 app.task_prog（顶栏）＋edit 写 app.touched（右栏）；配置写库后 on_config_change 即时刷新顶栏数据流（settings 本无缓存·每次读写即时读文件）。"""
import os, re
from textual.widgets import ProgressBar
import shell_core as core, user_index, msg_flow
from rich.text import Text
class Index:
    def _fdesc(self, s):
        try:
            t = open(os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md"))), encoding="utf-8", errors="ignore").read(4000)
            m = re.search(r"(?m)^description:\s*(.+)$", t.split("---", 2)[1] if t.startswith("---") else t)
            return re.sub(r"\s+", " ", (m.group(1) if m else str(s.get("description") or ""))).strip()[:56]
        except Exception: return str(s.get("description") or "")[:56]
    def action_menu_skill_index(self):
        import skill_route; rows = [("path:skill", "➕ 按路径输入加入 skill（登记扫描根＋重建注册表）")] + [("tok:" + str(s.get("id", "")), "%s｜%s" % (s.get("id"), self._fdesc(s))) for s in skill_route.skills()]
        self.menu("SKILL.md 索引·技能（名称＋介绍 · Enter 插入 /技能名 · F5＝文件索引）", rows)
    def action_menu_files(self):
        rows = [("#pick_file", "＋ 索引文件/文件夹：浏览选定即插 /名称（文件夹＝登记扫描根＋索引）")]
        rows += [("tok:" + x["name"], "/%s（%s）→ %s" % (x["name"], x["kind"], x["path"])) for x in user_index.load()]
        self.menu("文件索引（用户索引项 · Enter 插入 /名称 · F2＝技能索引）", rows)
    def action_pick_file(self):
        from shell_tui_files import Files; self.push_screen(Files(), self._file_picked)
    def _file_picked(self, path):
        if not path: return
        if getattr(self, "_ws_pick", False): self._ws_pick = False; self.ws_indexed(path); return
        os.path.isdir(path) and self.log_line(core.run_script("register.py", ["--add-root", path, "--write"])); self.log_line(user_index.add(path))
    def subconv_hint(self):
        for s in getattr(self, "steps", []):
            if not s.startswith("路由参考：打分命中"): continue
            sids = [x.strip() for x in s.split("命中", 1)[1].split("·")[0].split(",") if x.strip()]
            t = Text("⧉ 路由参考命中 " + "、".join(sids) + "：是否派发由模型自主决定（⧉技能▸ 行＝真对等派发对话输出·批23 各派发自开 conv）　可显式重派：", style="bold #f9e2af")
            t.append("[:dispatch " + (sids[0] if sids else "<技能id>") + " <诉求>]", style="bold #89b4fa underline"); self.log_line(t); break
    def open_subconv(self, sid, only_empty=False):
        try: import chains; chains.log("sub", sid)
        except Exception: pass
        ta = self.query_one("#input")
        if not (only_empty and ta.text.strip()): ta.text = ":dispatch " + sid + " "; ta.focus(); return sid
    def _ev(self, e):
        try:
            m = e.get("meta") or {}; k = e.get("kind")
            if k == "task": self.call_from_thread(setattr, self, "task_prog", "≡ %s ▸ %s/%s%s" % (str(m.get("id", ""))[-6:], m.get("done", 0), m.get("total", 0), (" ▸" + msg_flow.fmt(m["eta_s"])) if m.get("eta_s") else "")); self.call_from_thread(self._taskbar, m)
            elif k == "edit": self.call_from_thread(self.touched.append, str(e.get("text") or ""))
        except Exception: pass
    def _taskbar(self, m): t = int(m.get("total", 0) or 0); t > 0 and self.query_one("#prog", ProgressBar).update(total=t, progress=int(m.get("done", 0) or 0))
    def action_editor(self):
        from shell_tui_files import Files; self.push_screen(Files(), lambda p: p and self._open_editor(p))
    def _open_editor(self, p, ro=False):
        from shell_tui_editor import Editor; self.push_screen(Editor(p, ro))
    def on_config_change(self, path): self.sub_title = "数据流：" + (core.ag.current() or "未检出 agent")
