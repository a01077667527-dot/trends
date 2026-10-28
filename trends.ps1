# Local keyword dashboard server (Naver / Google / Daum)
# Usage: powershell -ExecutionPolicy Bypass -File trends.ps1 [-Port 8787] [-NoBrowser]
param([int]$Port = 8787, [switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $root 'keywords.ps1')

$cacheSeconds = 60
$script:cache = $null
$script:cacheTime = [datetime]::MinValue

function Get-Keywords {
    if ($script:cache -and ((Get-Date) - $script:cacheTime).TotalSeconds -lt $cacheSeconds) { return $script:cache }
    $script:cache = Get-KeywordJson
    $script:cacheTime = Get-Date
    $script:cache
}

function Send($ctx, [int]$status, [string]$type, [byte[]]$body) {
    $res = $ctx.Response
    $res.StatusCode = $status
    $res.ContentType = $type
    $res.Headers['Cache-Control'] = 'no-store'
    $res.ContentLength64 = $body.Length
    $res.OutputStream.Write($body, 0, $body.Length)
    $res.Close()
}

$listener = New-Object Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
$url = "http://localhost:$Port/"
Write-Host "Keyword dashboard running at $url  (close this window or press Ctrl+C to stop)"
if (-not $NoBrowser) { Start-Process $url }

$utf8 = New-Object Text.UTF8Encoding $false
try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        try {
            switch ($ctx.Request.Url.AbsolutePath) {
                '/' { Send $ctx 200 'text/html; charset=utf-8' ([IO.File]::ReadAllBytes((Join-Path $root 'index.html'))) }
                # Same path the hosted page reads, but fetched live
                '/data.json' { Send $ctx 200 'application/json; charset=utf-8' $utf8.GetBytes((Get-Keywords)) }
                default { Send $ctx 404 'text/plain' $utf8.GetBytes('Not found') }
            }
        } catch {
            Write-Warning $_.Exception.Message
            try { Send $ctx 500 'text/plain' $utf8.GetBytes($_.Exception.Message) } catch {}
        }
    }
} finally {
    $listener.Stop()
}
