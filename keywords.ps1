# Keyword fetchers shared by trends.ps1 (local server) and build.ps1 (GitHub Actions)
# Works on Windows PowerShell 5.1 and PowerShell 7 (pwsh)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if ($PSVersionTable.PSEdition -eq 'Core') {
    # .NET Core needs this for EUC-KR (Naver ranking page)
    [Text.Encoding]::RegisterProvider([Text.CodePagesEncodingProvider]::Instance)
}

function Get-Text([string]$url, [string]$encoding = 'utf-8') {
    $wc = New-Object Net.WebClient
    $wc.Headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
    $wc.Headers['Accept-Language'] = 'ko-KR,ko;q=0.9'
    try { $bytes = $wc.DownloadData($url) } finally { $wc.Dispose() }
    [Text.Encoding]::GetEncoding($encoding).GetString($bytes)
}

function Decode([string]$s) { [Net.WebUtility]::HtmlDecode($s).Trim() }

function Get-Google {
    $xml = [xml](Get-Text 'https://trends.google.com/trending/rss?geo=KR')
    $ns = New-Object Xml.XmlNamespaceManager $xml.NameTable
    $ns.AddNamespace('ht', 'https://trends.google.com/trending/rss')
    $rank = 0
    foreach ($item in $xml.SelectNodes('//item')) {
        $rank++
        $news = $item.SelectSingleNode('ht:news_item', $ns)
        [ordered]@{
            rank    = $rank
            keyword = $item.title
            traffic = $item.SelectSingleNode('ht:approx_traffic', $ns).InnerText
            news    = if ($news) { $news.SelectSingleNode('ht:news_item_title', $ns).InnerText } else { $null }
            url     = 'https://www.google.com/search?q=' + [uri]::EscapeDataString($item.title)
        }
    }
}

function Get-Signal {
    $json = Get-Text 'https://api.signal.bz/news/realtime' | ConvertFrom-Json
    foreach ($k in $json.top10) {
        [ordered]@{
            rank    = $k.rank
            keyword = $k.keyword
            state   = $k.state
            url     = 'https://search.naver.com/search.naver?query=' + [uri]::EscapeDataString($k.keyword)
        }
    }
}

function Get-NaverNews {
    # Ranking page lists top articles per press; take each press's #1 article
    $html = Get-Text 'https://news.naver.com/main/ranking/popularDay.naver' 'euc-kr'
    $re = '<em class="list_ranking_num">1<.*?<a href="([^"]+)" class="list_title[^"]*"[^>]*>([^<]+)</a>'
    $rank = 0
    foreach ($m in [regex]::Matches($html, $re, 'Singleline')) {
        $rank++
        if ($rank -gt 20) { break }
        [ordered]@{ rank = $rank; keyword = Decode $m.Groups[2].Value; url = Decode $m.Groups[1].Value }
    }
}

function Get-Daum {
    $html = Get-Text 'https://news.daum.net/'
    $start = $html.IndexOf('data-tiara-layer="realtime_trend"')
    if ($start -lt 0) { throw 'realtime_trend block not found' }
    $end = $html.IndexOf('</ol>', $start)
    $block = $html.Substring($start, $end - $start)
    $re = '<a href="([^"]+)" class="item_trendranking"[^>]*data-tiara-copy="([^"]*)" data-tiara-ordnum="(\d+)" data-tiara-custom="badge=(\w*)'
    foreach ($m in [regex]::Matches($block, $re)) {
        [ordered]@{
            rank    = [int]$m.Groups[3].Value
            keyword = Decode $m.Groups[2].Value
            state   = $m.Groups[4].Value
            url     = Decode $m.Groups[1].Value
        }
    }
}

function Invoke-Source([scriptblock]$fetch) {
    try { @{ items = @(& $fetch); error = $null } }
    catch { @{ items = @(); error = $_.Exception.Message } }
}

# Returns all sources as a compact JSON string; "updated" is ISO 8601 with offset so any timezone reads it right
function Get-KeywordJson {
    [ordered]@{
        updated   = [DateTimeOffset]::Now.ToString('yyyy-MM-ddTHH:mm:sszzz')
        naver     = Invoke-Source { Get-Signal }
        naverNews = Invoke-Source { Get-NaverNews }
        google    = Invoke-Source { Get-Google }
        daum      = Invoke-Source { Get-Daum }
    } | ConvertTo-Json -Depth 6 -Compress
}
