# sms_route.ps1 — 确定性路由引擎：剥离 sms-shell/sms 调用前缀重路由 · 裸内置词（help/config/cmds）· :元指令（治理类原生零依赖；托管引擎按外部程序调用）· 个性化指令展开 · 其余话语→数据流
$ENGINE = @{ cmds = 'commands.py'; intent = 'commands.py'; alias = 'user_commands.py'; unalias = 'user_commands.py'; grant = 'permissions.py'; perms = 'permissions.py'; tools = 'agent_dispatch.py'; dream = 'dream.py'; api = 'api.py'; deploy = 'deploy.py'; session = 'session.py'; hud = 'hud.py'; web = 'web_shell.py'; ext = 'external.py'; net = 'ff_lite.py'; tts = 'tts.py'; learn = 'learn.py'; file = 'sub_skills\file_ops\scripts\file_ops.py'; path = 'sub_skills\file_ops\scripts\path_ops.py'; index = 'register.py'; skills = 'skill_route.py'; workspace = 'workspace.py'; sh = 'sys_shells.py'; debug = 'debug.py'; mode = 'shell_mode.py' }
function SkillScripts {
  $c = @((Join-Path $PSScriptRoot '..\skill\scripts'), (Join-Path $PSScriptRoot '..\scripts'))
  if ($env:SMS_SKILL) { $c += @((Join-Path $env:SMS_SKILL 'skill\scripts'), (Join-Path $env:SMS_SKILL 'scripts')) }
  $s = CfgGet 'sms_skill' ''; if ($s) { $c += @((Join-Path $s 'skill\scripts'), (Join-Path $s 'scripts')) }
  foreach ($p in $c) { if ($p -and (Test-Path (Join-Path $p 'shell.py'))) { return $p } }
  $null }
function Run-Engine($script, $argv) {
  if (-not ($d = SkillScripts)) { Write-Warn '未定位托管 skill：deploy 登记 sms_skill 或设 SMS_SKILL=<skill_manage_system 绝对路径>'; return }
  $env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:SMS_WORKSPACE = SMS_WS; $env:SMS_TMP = SMS_WTmp; Write-Dim ('[' + $script + ']')
  & python -B (Join-Path $d $script) @argv 2>&1 | ForEach-Object { Write-Out ([string]$_) }
}
function Show-Cfg($sub, $argv) {
  $argv = @($argv); $c = Cfg 'llm_gateway'; $key = [string]$c.api_key; if ($c.api_key_env) { $e = (Get-Item ('env:' + $c.api_key_env) -ErrorAction SilentlyContinue); if ($e) { $key = $e.Value } }
  if (-not $sub -or $sub -eq 'status') { Write-Line ('gateway: enabled=' + $c.enabled + ' base_url=' + $c.base_url + ' model=' + $c.model + ' api_key=' + $(if ($key) { 'set' } else { 'missing' }) + ' max_tokens=' + $c.max_tokens + ' · 文件=' + (Join-Path $SMS 'config\config.json')) ; return }
  if ($sub -eq 'show') { Write-Out (MaskJson (Read-CfgDoc)); return }
  if ($sub -eq 'get' -and $argv.Count -ge 1) { Write-Out ((CfgGet $argv[0] $null | ConvertTo-Json -Depth 10 -Compress)); return }
  if ($sub -eq 'set' -and $argv.Count -ge 2) { CfgSet $argv[0] (($argv[1..($argv.Count - 1)]) -join ' '); Write-Line ('已写入 ' + $argv[0] + '（api_key 显示恒掩码）'); return }
  Write-Line ':config status|show|get <dot.path>|set <path> <json>（配置存 <SMS_HOME>/config\config.json·api_key 恒掩码）'
}
function Show-Help { Show-Builtins; Show-MetaHelp; Write-Dim '系统原生用法：sms-shell <话语|:元指令> 单发执行即退' }
function Handle-Line($line, $sink) {
  $t = ([string]$line).Trim(); if (-not $t) { return }
  if ($t -match '^(?i)(quit|exit|:quit|:q|:exit)$') { return 'exit' }
  if ($t -match '^(?i)(sms[\s\-_\.]*shell(\.cmd)?|sms)(?=[\s,，:：]|$)[\s,，]*(.*)$') { if ($Matches[3].Trim()) { return (Handle-Line $Matches[3] $sink) }; Show-Help; return }
  if ($t.StartsWith(':') -or $t.StartsWith([string][char]0xFF1A)) {
    $p = $t.TrimStart(':', [char]0xFF1A).Trim() -split '\s+'; $m = $p[0].ToLower(); $a = @($p | Select-Object -Skip 1)
    if ($m -eq 'help') { Show-Help }
    elseif ($m -eq 'config') { Show-Cfg $(if ($a.Count) { $a[0] } else { 'status' }) $(if ($a.Count -gt 1) { $a[1..($a.Count - 1)] } else { , @() }) }
    elseif ($m -eq 'agents') { Write-Line ('检出：' + ((@(Detected)) -join '、') + ' · 当前：' + (Current) + ' · 技能前缀：' + (StateGet 'skill_prefix' 'on') + ' · 切换：:use <name>（gateway＝原生直连）') }
    elseif ($m -eq 'use') { if (-not $a.Count) { Write-Line '用法 :use <name>' } else { StatePut 'current_agent' $a[0]; Write-Line ('切到 agent：' + $a[0] + $(if ($a[0] -ne 'gateway' -and (CfgGet 'llm_gateway.enabled' $false)) { '（已记住——网关开启期间话语仍恒走 gateway，:config set llm_gateway.enabled false 后生效）' } elseif (@(Detected) -notcontains $a[0]) { '（未检出——配 agent_cli {bin,args} 并确保在 PATH）' } else { '' })) } }
    elseif ($m -eq 'skill') { StatePut 'skill_prefix' $(if ($a.Count -and $a[0] -eq 'off') { 'off' } else { 'on' }); Write-Line ('skill_manage_system 前缀：' + (StateGet 'skill_prefix' 'on')) }
    elseif ($m -eq 'image') { $script:IMG = $(if ($a.Count -and (Test-Path (($a -join ' ')))) { ($a -join ' ') } else { $null }); Write-Line $(if ($script:IMG) { '已附图（下一句生效）：' + $script:IMG } else { '图片不存在：' + ($a -join ' ') }) }
    elseif ($m -in @('dispatch', 'session', 'edit', 'view', 'mode')) { if ($m -eq 'dispatch') { if ($a.Count -ge 2) { Run-Engine 'agent_dispatch.py' (@('skill') + $a) } else { Write-Line '用法 :dispatch <技能id> <诉求>（技能子会话真派发）' } } elseif ($m -eq 'session') { Run-Engine 'chains.py' (@('session') + $(if ($a.Count) { $a } else { , @('current') })) } else { Write-Line '内置编辑器/界面模式仅 Textual TUI 提供（python 入口 sms-shell·F7/F8）·原生壳话语恒＝对话·文件操作用 :sh' } }
    elseif ($ENGINE[$m]) { $x = $a; if ($m -eq 'cmds') { $x = $(if ($a.Count) { @('show') + $a } else { @('help') }) } elseif ($m -eq 'intent') { $x = @('intent') + $a } elseif ($m -eq 'alias') { $x = @('add') + $a + @('--write') } elseif ($m -eq 'unalias') { $x = @('rm') + $a + @('--write') } elseif ($m -eq 'grant') { $x = $a + @('--write') } elseif ($m -eq 'skills') { $x = @('list') } elseif ($m -eq 'index') { if (-not $a.Count) { Run-Engine 'skills_config.py' @('roots'); return }; $x = @('--add-root') + $a + @('--write') }; Run-Engine $ENGINE[$m] $x }
    else { Write-Warn ('未知元指令 :' + $m + '（:help）'); Beep }
    return
  }
  if (($w = $t.ToLower()) -in @('help', '?', 'h', '帮助', '用法')) { Show-Help; return }
  if ($w -in @('config', '设置', '配置', '状态', 'status', '修改配置', '打开设置', '打开配置', '进入配置', '配置编辑器', '图形化配置')) { Show-Cfg 'status' @(); Write-Line '改配置：:config set <path> <json> · 技能扫描根：:index <路径> · 全量：:config show'; return }
  if ($w -in @('cmds', '命令', '指令', '命令表')) { Run-Engine 'commands.py' @('help'); return }
  if ($t -match '^(?i)(?:config|设置|配置)[\s,，]+(\S.*)$') { $ca = $Matches[1] -split '\s+'; Show-Cfg $ca[0] $(if ($ca.Count -gt 1) { @($ca | Select-Object -Skip 1) } else { , @() }); return }
  if (($t -match '(哪些|那些|什么)[^。！!？?]{0,8}(技能|skills?\b)') -or ($t -match '^(?i)skills?\s*list$' -or $w -in @('技能列表', '可用技能', '可调用技能'))) { Run-Engine 'skill_route.py' @('list'); return }
  if (($t -match '(?i)sms|shell|壳' -and $t -match '设置|配置|命令|指令|config' -and $t -notmatch '问题|故障|报错|错误|异常|失败|无法|检查|诊断|为什么') -or ($w -in @('显示提示词', '提示词', '你的提示词'))) { Write-Line 'sms-shell：话语即数据流 · !命令＝系统 shell · :config 配置 · :cmds 全表 · :help 速查（确定性路由·未经大模型）'; return }
  if (AliasFind (($t -split '\s+')[0])) { Run-Engine 'user_commands.py' (@('run') + ($t -split '\s+')); return }
  Invoke-Ask $t $sink
}
