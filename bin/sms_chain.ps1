# sms_chain.ps1 — 原生链碎片层（零 python）：十一链碎片写入（chain_store 兼容 schema·64 维哈希向量·频次/边）·压缩记忆尾 tail.log·chains git 收口；依赖 sms_state.ps1 的 SMS/CfgGet，由 sms_shell.ps1 统一点源加载
function FragVec($t) {
  $s = $t.ToLower(); $toks = @([regex]::Matches($s, '[a-z0-9]+') | ForEach-Object { $_.Value })
  foreach ($run in [regex]::Matches($s, '[\u4e00-\u9fff][\u4e00-\u9fff]+') | ForEach-Object { $_.Value }) { for ($i = 0; $i -lt $run.Length - 1; $i++) { $toks += [string]$run[$i] + [string]$run[$i + 1] } }
  $v = New-Object 'double[]' 64; $md5 = [Security.Cryptography.MD5]::Create()
  foreach ($x in ($toks | Select-Object -Unique)) { $hx = [BitConverter]::ToString($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($x)), 0, 4) -replace '-'; $v[[int]([Convert]::ToUInt32($hx, 16) % 64)] += 1 }
  $sq = 0.0; foreach ($x in $v) { $sq += $x * $x }; $n = [Math]::Sqrt($sq); if ($n -gt 0) { $v = @($v | ForEach-Object { [Math]::Round($_ / $n, 4) }) }
  $v
}
function Record($chain, $text) {
  try {
    if ((CfgGet ('chains.' + $chain + '.enabled') $true) -eq $false) { return }
    $md5 = [Security.Cryptography.MD5]::Create()
    $id = ((-join ($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($chain + $text + (Get-Date -UFormat %s))) | ForEach-Object { $_.ToString('x2') }))).Substring(0, 10)
    $dir = Join-Path (Join-Path $SMS 'chains') $chain; New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $frag = [ordered]@{ id = $id; chain = $chain; ts = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'); text = $text.Trim(); vec = (FragVec $text); freq = 1; edges = @() }
    [IO.File]::WriteAllText((Join-Path $dir ($id + '.json')), ($frag | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
  } catch {}
}
function TailPush($role, $text) {
  $p = StateFile 'tail.log'; $lines = @(); if (Test-Path $p) { $lines = @(Get-Content $p -Encoding UTF8) }
  $x = ($text -replace '\s+', ' '); $lines = $lines + ($role + ': ' + $x.Substring(0, [Math]::Min(160, $x.Length)))
  if ($lines.Count -gt 30) { $lines = $lines[($lines.Count - 30)..($lines.Count - 1)] }
  [IO.File]::WriteAllLines($p, $lines, (New-Object Text.UTF8Encoding $false))
}
function TailText { $p = StateFile 'tail.log'; if (-not (Test-Path $p)) { return '' }; $t = (Get-Content $p -Raw -Encoding UTF8).Trim(); if ($t.Length -gt 1200) { $t.Substring($t.Length - 1200) } else { $t } }
function ChainsGit {
  $r = Join-Path $SMS 'chains'; if (-not (Test-Path (Join-Path $r '.git'))) { try { & git -C $r init --quiet 2>$null } catch { return } }
  try { & git -C $r add -A 2>&1 | Out-Null; & git -C $r -c user.name=sms -c user.email=sms@local commit -qm ('sms-shell ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) 2>&1 | Out-Null } catch {}
}
