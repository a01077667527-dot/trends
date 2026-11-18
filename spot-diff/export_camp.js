// make.py의 캠핑 장면을 A/B 단일 이미지(1024x768)로 내보내기
const { chromium } = require('playwright'); const fs = require('fs');
(async () => { const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1024,height:768}});
 for (const n of ['base','b']) { await p.setContent(`<body style="margin:0">${fs.readFileSync(process.argv[2]+'/'+n+'.svg','utf8')}</body>`); await p.screenshot({path:process.argv[2]+'/'+n+'.png'}); }
 await b.close(); })();
