const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({viewport:{width:800,height:800}});
 for (const n of ['logo_A','logo_B','logo_C']) { await p.goto('file://'+__dirname+'/'+n+'.svg'); await p.screenshot({path:n+'.png'}); }
 await p.setViewportSize({width:1060,height:520}); await p.goto('file://'+__dirname+'/preview.html'); await p.screenshot({path:'preview.png'});
 await b.close(); })();
