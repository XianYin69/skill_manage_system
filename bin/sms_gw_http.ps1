# sms_gw_http.ps1 — 原生网关 HTTP 层（零 python）：OpenAI 兼容 /chat/completions SSE 逐字流式解析（content/reasoning/usage/[DONE]/非 data 行兜底）；依赖 sms_state.ps1 的 Cfg/CfgGet，由 sms_shell.ps1 统一点源加载
function Stream-Gateway($body, $sink) {
  $c = Cfg 'llm_gateway'
  $key = [string]$c.api_key; if ($c.api_key_env -and (Get-Item ('env:' + $c.api_key_env) -ErrorAction SilentlyContinue)) { $key = (Get-Item ('env:' + $c.api_key_env)).Value }
  $req = [Net.HttpWebRequest]::Create(([string]$c.base_url).TrimEnd('/') + '/chat/completions')
  $tm = 120; try { $tm = [int](CfgGet 'llm_gateway.timeout' 120) } catch {}; if ($tm -le 0) { $tm = 120 }
  $req.Method = 'POST'; $req.ContentType = 'application/json'; $req.Timeout = 1000 * $tm; $req.ReadWriteTimeout = 1000 * $tm
  $req.ServicePoint.Expect100Continue = $false
  $req.Headers.Add('Authorization', 'Bearer ' + $key)
  $b = [Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Depth 10 -Compress)); $req.ContentLength = $b.Length
  $qs = $req.GetRequestStream(); $qs.Write($b, 0, $b.Length); $qs.Close()
  $resp = $req.GetResponse(); $rd = New-Object IO.StreamReader -ArgumentList $resp.GetResponseStream(), ([Text.Encoding]::UTF8)
  $full = ''; $reason = ''; $buf = ''
  while ($null -ne ($ln = $rd.ReadLine())) {
    if ($ln -notlike 'data: *') { if ($ln.Trim()) { $buf += $ln.Trim() }; continue }
    $d = $ln.Substring(6).Trim(); if ($d -eq '[DONE]') { break }
    $j = $null; try { $j = $d | ConvertFrom-Json } catch { continue }
    if ($j.usage) { break }
    $ch = $j.choices[0]
    if ($ch.delta.content) { $full += $ch.delta.content; & $sink $ch.delta.content }
    elseif ($ch.delta.reasoning_content) { $reason += $ch.delta.reasoning_content }
    if ($ch.finish_reason) { break }
  }
  $rd.Close(); $resp.Close()
  if (-not $full -and $reason) { $full = $reason; & $sink $reason }
  if (-not $full -and $buf) { try { $full = ($buf | ConvertFrom-Json).choices[0].message.content; if ($full) { & $sink $full } } catch {} }
  if ($full) { Write-Host '' }
  $full
}
