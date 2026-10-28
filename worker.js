// Cloudflare Worker: live keywords (Naver / Google / Daum) + blog long-tail suggestions
// GET /api -> same shape as data.json plus "longtail"; cached 60s at the edge

const CACHE_SECONDS = 60;
const SEED_COUNT = 12; // 12 seeds x 3 autocomplete calls + 4 sources stays under the free plan's 50 subrequests
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const url = new URL(request.url);
    if (url.pathname !== '/api') return new Response('Not found', { status: 404, headers: CORS });

    const cache = caches.default;
    const key = new Request(url.origin + '/api');
    const hit = await cache.match(key);
    if (hit) return hit;

    const body = JSON.stringify(await collect());
    const res = new Response(body, {
      headers: {
        ...CORS,
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': `public, max-age=${CACHE_SECONDS}`,
      },
    });
    ctx.waitUntil(cache.put(key, res.clone()));
    return res;
  },
};

async function collect() {
  const [naver, naverNews, google, daum] = await Promise.all([
    source(getSignal), source(getNaverNews), source(getGoogle), source(getDaum),
  ]);
  const longtail = await source(() => getLongtail([naver.items, google.items, daum.items]));
  return { updated: new Date().toISOString(), live: true, naver, naverNews, google, daum, longtail };
}

async function source(fn) {
  try { return { items: await fn(), error: null }; }
  catch (e) { return { items: [], error: String(e.message || e) }; }
}

async function getText(url, encoding = 'utf-8') {
  const res = await fetch(url, { headers: { 'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return new TextDecoder(encoding).decode(await res.arrayBuffer());
}

function decode(s) {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCharCode(parseInt(n, 16)))
    .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
    .trim();
}

const naverSearch = q => 'https://search.naver.com/search.naver?query=' + encodeURIComponent(q);

async function getSignal() {
  const json = JSON.parse(await getText('https://api.signal.bz/news/realtime'));
  return json.top10.map(k => ({ rank: k.rank, keyword: k.keyword, state: k.state, url: naverSearch(k.keyword) }));
}

async function getNaverNews() {
  // Ranking page lists top articles per press; take each press's #1 article
  const html = await getText('https://news.naver.com/main/ranking/popularDay.naver', 'euc-kr');
  const re = /<em class="list_ranking_num">1<[\s\S]*?<a href="([^"]+)" class="list_title[^"]*"[^>]*>([^<]+)<\/a>/g;
  const items = [];
  for (const m of html.matchAll(re)) {
    items.push({ rank: items.length + 1, keyword: decode(m[2]), url: decode(m[1]) });
    if (items.length >= 20) break;
  }
  return items;
}

async function getGoogle() {
  const xml = await getText('https://trends.google.com/trending/rss?geo=KR');
  const items = [];
  for (const [, item] of xml.matchAll(/<item>([\s\S]*?)<\/item>/g)) {
    const tag = name => { const m = item.match(new RegExp(`<${name}>([\\s\\S]*?)</${name}>`)); return m ? decode(m[1]) : null; };
    const keyword = tag('title');
    items.push({
      rank: items.length + 1,
      keyword,
      traffic: tag('ht:approx_traffic'),
      news: tag('ht:news_item_title'),
      url: 'https://www.google.com/search?q=' + encodeURIComponent(keyword),
    });
  }
  return items;
}

async function getDaum() {
  const html = await getText('https://news.daum.net/');
  const start = html.indexOf('data-tiara-layer="realtime_trend"');
  if (start < 0) throw new Error('realtime_trend block not found');
  const block = html.slice(start, html.indexOf('</ol>', start));
  const re = /<a href="([^"]+)" class="item_trendranking"[^>]*data-tiara-copy="([^"]*)" data-tiara-ordnum="(\d+)" data-tiara-custom="badge=(\w*)/g;
  return [...block.matchAll(re)].map(m => ({ rank: +m[3], keyword: decode(m[2]), state: m[4], url: decode(m[1]) }));
}

// ---- Long-tail ----

async function suggestNaver(q) {
  const t = await getText(`https://ac.search.naver.com/nx/ac?q=${encodeURIComponent(q)}&st=100&r_format=json&q_enc=UTF-8&r_enc=UTF-8&frm=nv`);
  return (JSON.parse(t).items?.[0] || []).map(a => a[0]);
}
async function suggestGoogle(q) {
  const t = await getText(`https://suggestqueries.google.com/complete/search?client=firefox&hl=ko&q=${encodeURIComponent(q)}`);
  return JSON.parse(t)[1] || [];
}
async function suggestDaum(q) {
  const t = await getText(`https://suggest.search.daum.net/sushi/opensearch/pc?q=${encodeURIComponent(q)}`);
  return JSON.parse(t)[1] || [];
}

// Estimated advertiser value by topic; not real CPC data
const CATEGORIES = [
  { tier: 'high', label: '고단가', weight: 5, re: /보험|대출|금리|신용카드|카드발급|보상|배상|소송|변호사|위자료|합의금|이혼|상속|세금|환급|연말정산|부동산|청약|분양|전세|월세|아파트|매매|주식|코인|투자|코스피|코스닥|증시|주가|ETF|환율|배당|공모주|적금|예금|연금|펀드|수술|치료|병원|임플란트|교정|성형|렌트|리스|중고차|신차|할부|창업|부업|사업자|자격증|학원|인강|유학/ },
  { tier: 'commerce', label: '수익형', weight: 3, re: /가격|비용|요금|견적|할인|쿠폰|최저가|구매|구입|판매|예약|추천|비교|순위|후기|리뷰|가성비|신청|가입|지원금|보조금|혜택|이벤트|무료|결제|맛집|숙소|항공권|패키지/ },
  { tier: 'info', label: '정보형', weight: 2, re: /방법|원인|이유|뜻|정리|일정|시간|날짜|결과|조회|확인|조건|자격|기간|대상|증상|부작용|효과|나이|프로필|학력|재산|근황|위치|주차|메뉴|영업시간|사망|피해|현황|전망|발표/ },
];

const squash = s => s.replace(/\s+/g, '').toLowerCase();

function shortenSeed(k) {
  // Signal.bz keywords read like headlines; autocomplete works best on the first couple of words
  const words = k.trim().split(/\s+/);
  return words.length > 3 ? words.slice(0, 2).join(' ') : words.join(' ');
}

async function getLongtail(lists) {
  const seeds = [];
  const seen = new Set();
  for (let i = 0; seeds.length < SEED_COUNT && i < 10; i++) {
    for (const list of lists) {
      const k = list[i]?.keyword;
      if (!k) continue;
      const seed = shortenSeed(k);
      if (seen.has(squash(seed))) continue;
      seen.add(squash(seed));
      seeds.push(seed);
      if (seeds.length >= SEED_COUNT) break;
    }
  }

  const found = new Map(); // squashed phrase -> entry
  await Promise.all(seeds.map(async seed => {
    const results = await Promise.allSettled([suggestNaver(seed), suggestGoogle(seed), suggestDaum(seed)]);
    ['naver', 'google', 'daum'].forEach((src, i) => {
      if (results[i].status !== 'fulfilled') return;
      for (const raw of results[i].value) {
        const phrase = raw.replace(/\s+/g, ' ').trim();
        const key = squash(phrase);
        if (!key || key === squash(seed) || key.length < squash(seed).length + 2) continue;
        const entry = found.get(key) || { keyword: phrase, seed, sources: new Set() };
        entry.sources.add(src);
        found.set(key, entry);
      }
    });
  }));

  const items = [];
  for (const e of found.values()) {
    const tags = CATEGORIES.filter(c => c.re.test(e.keyword));
    const words = e.keyword.split(' ').length;
    const score = tags.reduce((s, c) => s + c.weight, 0) + (e.sources.size - 1) * 2 + (words >= 4 ? 1 : 0);
    if (score === 0) continue;
    items.push({
      keyword: e.keyword,
      seed: e.seed,
      sources: [...e.sources],
      tier: tags[0]?.tier || 'other',
      tags: tags.map(c => c.label),
      score,
      url: naverSearch(e.keyword),
    });
  }
  items.sort((a, b) => b.score - a.score || a.keyword.length - b.keyword.length);
  return items.slice(0, 60).map((it, i) => ({ rank: i + 1, ...it }));
}
