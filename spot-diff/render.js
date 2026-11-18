const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1080,height:1920}});
 for (const n of ['quiz','answer']) { await p.goto('file://'+__dirname+'/'+n+'.html'); await p.screenshot({path:n+'.png'}); }
 await b.close(); })();
