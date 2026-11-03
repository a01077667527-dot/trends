// 헤드리스 크롬으로 3D 프레임 렌더링
// 사용: node render.js <출력폴더> <워커수> [프레임번호,프레임번호,...]
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const outDir = process.argv[2];
const workers = parseInt(process.argv[3] || '4', 10);
const only = process.argv[4] ? process.argv[4].split(',').map(Number) : null;
fs.mkdirSync(outDir, { recursive: true });

const types = { '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html' };
const server = http.createServer((req, res) => {
  const f = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  });
});

(async () => {
  await new Promise(r => server.listen(0, r));
  const url = `http://127.0.0.1:${server.address().port}/scene.html`;
  const launch = async () => {
    const gpu = process.env.GPU === '1';
    const args = gpu
      ? ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', process.platform === 'win32' ? '--use-angle=d3d11' : '--use-angle=default']
      : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
    const b = await chromium.launch({ args, headless: true });
    const p = await b.newPage({ viewport: { width: 640, height: 360 } });
    p.on('pageerror', e => console.error('pageerror', e.message));
    p.on('console', m => { if (m.type() === 'error') console.error('console', m.text()); });
    await p.goto(url);
    await p.waitForFunction('window.ready === true', null, { timeout: 120000 });
    console.log('GPU renderer:', await p.evaluate('window.GL_RENDERER'));
    return { b, p };
  };
  const first = await launch();
  const total = await first.p.evaluate('window.TOTAL_FRAMES');
  const frames = only || Array.from({ length: total }, (_, i) => i).filter(i => !fs.existsSync(path.join(outDir, `f${String(i).padStart(5, '0')}.json`)));
  const CH = 15;
  const chunks = [];
  for (let i = 0; i < frames.length; i += CH) chunks.push(frames.slice(i, i + CH));
  let done = 0; const t0 = Date.now();
  const run = async (w) => {
    const { b, p } = w === 0 ? first : await launch();
    while (chunks.length) {
      const chunk = chunks.shift();
      for (const fi of chunk) {
        const r = await p.evaluate(fi => window.renderFrame(fi), fi);
        const name = path.join(outDir, `f${String(fi).padStart(5, '0')}`);
        fs.writeFileSync(name + '.jpg', Buffer.from(r.img, 'base64'));
        fs.writeFileSync(name + '.json', JSON.stringify(r.meta));
        done++;
        if (done % 100 === 0) {
          const el = (Date.now() - t0) / 1000;
          console.log(`  ${done}/${frames.length}  ${(el / done).toFixed(2)}s/frame  남은 시간 ~${Math.round(el / done * (frames.length - done) / 60)}분`);
        }
      }
    }
    await b.close();
  };
  await Promise.all(Array.from({ length: workers }, (_, w) => run(w)));
  server.close();
  console.log(`rendered ${done} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})();
