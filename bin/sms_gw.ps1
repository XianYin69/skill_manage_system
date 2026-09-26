# sms_gw.ps1 — 原生数据流（零 python）：话语默认直达网关（SSE 解析见 sms_gw_http.ps1）＋压缩记忆前缀＋附图；网关未启用回退已装 agent CLI 流式；皆无则拒绝（本体不作答）
$ADAPTERS = @{ claude = @{ bin = 'claude'; args = @('-p') }; codex = @{ bin = 'codex'; args = @('exec') }; cursor = @{ bin = 'cursor-agent'; args = @() }; kilocode = @{ bin = 'kilocode'; args = @('run') }; kilo = @{ bin = 'kilo'; args = @('run') }; aider = @{ bin = 'aider'; args = @('--message') } }
$SYS = '你是 skill_manage_system（SMS）的数据流：SMS 只调取与管理技能及其副产物，禁止以模型自身常识代答用户任务（不要提及 Qwen 客户端、Android 等无关软件）。用户话语含问题/故障/报错/检查/为什么＝诊断请求，需据实排查（可运行诊断命令）后给结论，禁止回「输入 help 查看表」式敷衍，禁止把历史记忆碎片当现行行为。问到 sms-shell/SMS 自身的设置·命令·提示词时：据实介绍内置面（help=元指令表；config=网关设置；配置存 <SMS_HOME>/config/config.json；对话经原生网关直连），不得编造不存在的功能。生成文件一律写入当前工作区的 tmp 子目录（SMS_TMP 环境变量，壳已自动创建），不得散落工作区根；大模型与技能配置文件直接读取 <SMS_HOME>/config 下的 config.json/skills.json，禁止复制一份到工作区；目标为工作区文件的 tmp 产物经用户审核后可经 :workspace diff <tmp文件> --to <目标> 预览、:workspace release <tmp文件> --to <目标> --yes 收编回工作区（须 :grant danger·用户当轮确认）。无法执行就明确拒绝并说明。本壳为最后兜底（零 python·无技能派发通道）：一般知识问答可直答但须简短并首行标注〔兜底直答·等效 general_answer 子技能〕；需动手执行/读写/派技能的诉求请用户改用 Textual 壳或 <目标>/sms-shell(.cmd)。始终用简体中文，回答简短。'
function Detected {
  $d = @(); if (CfgGet 'llm_gateway.enabled' $false) { $d += 'gateway' }
  $cli = Cfg 'agent_cli'
  foreach ($k in (@($ADAPTERS.Keys) + @($cli.PSObject.Properties.Name | Where-Object { $_ -notlike '_*' }))) {
    $b = if ($ADAPTERS[$k]) { $ADAPTERS[$k].bin } elseif ($cli.$k) { $cli.$k.bin } else { $k }
    if ($b -and (Get-Command $b -ErrorAction SilentlyContinue)) { $d += $k } }
  $d
}
function Current {
  $det = @(Detected)
  if ($det -contains 'gateway') { return 'gateway' }
  $cur = StateGet 'current_agent' ''
  if ($cur -and ($det -contains $cur)) { return $cur }
  $det | Select-Object -First 1
}
function UserMsg($text) {
  $pre = StateGet 'skill_prefix' 'on'
  $body = if ($pre -ne 'off') { "[压缩记忆]`n" + (TailText) + "`n`n[对话规则] 本对话为新开对话，仅当前输入是指令，压缩记忆仅供背景引用；输出结束即收口本对话。`n`n[当前输入·唯一指令]`n" + $text + "`n`n[本请求经 SMS 治理：只调取与管理技能，本体不得以常识代答]" } else { $text }
  if (-not $script:IMG -or -not (Test-Path $script:IMG)) { return [pscustomobject]@{ role = 'user'; content = $body } }
  $mime = @{ '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.jpeg' = 'image/jpeg'; '.webp' = 'image/webp'; '.gif' = 'image/gif' }[[IO.Path]::GetExtension($script:IMG).ToLower()]
  if (-not $mime) { $mime = 'image/png' }
  $u = $mime + ';base64,' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($script:IMG)); $script:IMG = $null
  [pscustomobject]@{ role = 'user'; content = @([pscustomobject]@{ type = 'text'; text = $body }, [pscustomobject]@{ type = 'image_url'; image_url = [pscustomobject]@{ url = ('data:' + $u) } }) }
}
function Invoke-Ask($text, $sink) {
  $ag = Current; $conv = 'conv-' + (Get-Date -Format 'yyyyMMdd-HHmmss'); $null = SMS_WTmp
  if (-not $ag) { Write-Line '拒绝：网关未启用且未检出 agent CLI——SMS 本体不作答。启用：:config set llm_gateway.enabled true（并设 base_url/api_key/model）'; return }
  Record 'session' ('open:' + $conv); Record 'dialogue' ('user@' + $conv + ' ' + $text); $out = ''
  if ($ag -eq 'gateway') {
    $c = Cfg 'llm_gateway'
    $body = @{ model = [string]$c.model; messages = @(@{ role = 'system'; content = $SYS }, (UserMsg $text)); stream = $true; max_tokens = [int]$c.max_tokens }
    if ($null -ne $c.temperature) { $body.temperature = $c.temperature }; if ($null -ne $c.top_p) { $body.top_p = $c.top_p }
    try { $out = Stream-Gateway $body $sink } catch { $d = ''; try { $d = (New-Object IO.StreamReader -ArgumentList $_.Exception.Response.GetResponseStream()).ReadToEnd() } catch {}; Write-Line ('网关错误：' + $_.Exception.Message + ' ' + $d.Substring(0, [Math]::Min(200, $d.Length))) }
    Record 'tool' ('gateway:' + $c.model + '@' + $conv)
  } else {
    $sp = if ($ADAPTERS[$ag]) { $ADAPTERS[$ag] } else { (Cfg 'agent_cli').$ag }
    $lines = @(); try { Push-Location (SMS_WS); & $sp.bin @($sp.args + $text) | ForEach-Object { Write-Line $_; $lines += [string]$_ } } catch { Write-Line ('agent CLI 调用失败：' + $_.Exception.Message) } finally { Pop-Location }
    $out = $lines -join "`n"; Record 'tool' ('cli:' + $ag + '@' + $conv)
  }
  if ($out) { Record 'dialogue' ('agent@' + $conv + ' ' + $out); TailPush 'U' $text; TailPush 'A' $out }
  Record 'session' ('close:' + $conv); Record 'time' ('对话 ' + $conv + ' 收口（sms-shell 原生）')
}
