# Writes data.json next to index.html (run by GitHub Actions on a schedule)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $root 'keywords.ps1')

$json = Get-KeywordJson
[IO.File]::WriteAllText((Join-Path $root 'data.json'), $json, (New-Object Text.UTF8Encoding $false))

$data = $json | ConvertFrom-Json
foreach ($s in 'naver', 'naverNews', 'google', 'daum') {
    Write-Host ("{0}: {1} items {2}" -f $s, @($data.$s.items).Count, $data.$s.error)
}
