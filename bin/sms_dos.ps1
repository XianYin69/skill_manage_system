# sms_dos.ps1 — DOS 程序风格界面：蓝底灰字全屏配色 · 制表符边框题头 · 彩色状态栏/提示符 · 蜂鸣 · 退出恢复控制台
function Init-Dos {
  try { $r = $Host.UI.RawUI; $script:DosBack = $r.BackgroundColor; $script:DosFore = $r.ForegroundColor
    $r.BackgroundColor = 'DarkBlue'; $r.ForegroundColor = 'Gray'; $r.WindowTitle = 'SMS-SHELL v3 (DOS TUI) - ' + (Get-Location) } catch {}
  try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
}
function Exit-Dos { try { $r = $Host.UI.RawUI; if ($script:DosBack) { $r.BackgroundColor = $script:DosBack }; if ($script:DosFore) { $r.ForegroundColor = $script:DosFore }; $r.WindowTitle = 'sms-shell exit' } catch {} }
function Write-Line($t) { Write-Host $t }
function Write-Dim($t) { Write-Host -ForegroundColor DarkGray $t }
function Write-Warn($t) { Write-Host -ForegroundColor Yellow $t }
function Write-Key($t) { Write-Host -ForegroundColor Cyan $t }
function Write-Out($t) { Write-Host $t }
function Beep { try { [Console]::Beep(660, 60) } catch {} }
function Pad($w) { ('-' * $w) }
function Show-Banner {
  $w = 78
  Write-Key ('+' + (Pad $w) + '+')
  $rows = @('SMS-SHELL v3.0 · DOS TUI · 完全在系统 shell 中运行（本体零 python）',
    'SMS_HOME = ' + $SMS,
    'agent = ' + (Current) + ' · 技能前缀 = ' + (StateGet 'skill_prefix' 'on') + ' · 设置系统 = :config status|show|get|set',
    '直接输入话语＝交给数据流 · help/config/cmds＝内置词 · :help＝全表 · :quit＝退出')
  foreach ($t in $rows) { if ($t.Length -gt ($w - 3)) { $t = $t.Substring(0, $w - 3) }; Write-Key ('| ' + $t.PadRight($w - 2) + '|') }
  Write-Key ('+' + (Pad $w) + '+')
}
function Show-MetaHelp {
  Write-Key 'SMS-SHELL 元指令（:）'
  Write-Line ':help 帮助 · :config status|show|get <path>|set <path> <json> 配置 · :agents 看/选 agent · :use <name> · :skill on|off'
  Write-Line ':image <文件> 附下句话语图片 · :quit 退出（内置、零依赖）'
  Write-Dim '以下经托管引擎执行（外部程序·与系统 shell 调命令同理）：'
  Write-Line ':cmds [name] · :intent <话语> · :alias/:unalias 个性化指令 · :grant <键|角色> [分钟] · :deploy <dir|--Path P --FolderName F>'
  Write-Line ':session "<任务>" · :hud s|t|a|h · :dream status|run · :api formats|detect|show|validate|export · :web start|stop|token'
  Write-Line ':ext status|enable|enroll · :net search|fetch|download|status · :tts say|test|on|off|voices · :learn from-url|note|recall|distill|stats'
  Write-Line ':file read|write|list|copy|move|delete|stat · :path resolve|which|glob|tree|env'
}
function Show-Builtins {
  Write-Key '内置词（确定性路由·不经大模型）'
  Write-Line 'help / ? = 命令表 · config / 设置 / 配置 = :config status 摘要 · cmds / 命令 = :cmds'
}
