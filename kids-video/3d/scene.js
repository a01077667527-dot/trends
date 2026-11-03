// 동물 친구들과 숫자 놀이 — 3D 장면 (three.js)
// render.js 가 헤드리스 크롬에서 이 페이지를 열고 window.renderFrame(i) 를 프레임마다 호출합니다.
import * as THREE from './vendor/three.module.min.js';
import { FontLoader } from './vendor/addons/FontLoader.js';
import { TextGeometry } from './vendor/addons/TextGeometry.js';

const CFG = await (await fetch('config.json')).json();
const SS = CFG.ss;
const OW = 1920, OH = 1080, RW = Math.round(OW * SS), RH = Math.round(OH * SS);
const TAU = Math.PI * 2;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = t => { t = clamp(t); return 1 - (1 - t) ** 3; };
const easeIO = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const backOut = (t, s = 2.2) => { t = clamp(t); return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2; };
const elastic = t => t <= 0 ? 0 : t >= 1 ? 1 : 2 ** (-9 * t) * Math.sin((t * 10 - 0.75) * TAU / 3) + 1;
const hash = (...a) => { const x = Math.sin(a.reduce((s, v, i) => s + (i + 1) * 12.9898 * v, 0) + 78.233) * 43758.5453; return x - Math.floor(x); };
const hex = s => parseInt(s.replace('#', ''), 16);

// ------------------------------------------------------------------ renderer
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(RW, RH, false);
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const outCanvas = document.createElement('canvas');
outCanvas.width = OW; outCanvas.height = OH;
const octx = outCanvas.getContext('2d');
octx.imageSmoothingEnabled = true;
octx.imageSmoothingQuality = 'high';

const scene = new THREE.Scene();
const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
window.GL_RENDERER = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'unknown';
if (CFG.hq) { // 그래픽카드 모드: 환경광 반사(IBL)
  const { RoomEnvironment } = await import('./vendor/addons/RoomEnvironment.js');
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
}
const camera = new THREE.PerspectiveCamera(30, OW / OH, 0.1, 400);

// ------------------------------------------------------------------ materials
const matCache = new Map();
function M(color, o = {}) {
  const key = color + JSON.stringify(o);
  if (matCache.has(key)) return matCache.get(key);
  const m = new THREE.MeshStandardMaterial({
    color, roughness: o.r ?? 0.6, metalness: 0,
    emissive: o.e ?? 0x000000, emissiveIntensity: o.ei ?? 1,
    flatShading: !!o.flat, transparent: o.op !== undefined, opacity: o.op ?? 1,
    depthWrite: o.op === undefined, side: o.side ?? THREE.FrontSide,
  });
  const rim = o.rim ?? 0.45;
  if (rim > 0) {
    // 부드러운 테두리광 (애니메이션 영화 같은 보송한 느낌)
    m.onBeforeCompile = sh => {
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `
        float fres = pow(1.0 - clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), 2.4);
        outgoingLight += (diffuseColor.rgb * 0.55 + vec3(0.45)) * fres * ${rim.toFixed(3)};
        #include <opaque_fragment>`);
    };
    m.customProgramCacheKey = () => 'rim' + rim;
  }
  matCache.set(key, m);
  return m;
}
function shade(c, k) { // k>0 밝게, k<0 어둡게
  const col = new THREE.Color(c);
  if (k > 0) col.lerp(new THREE.Color(0xffffff), k); else col.multiplyScalar(1 + k);
  return col.getHex();
}

// ------------------------------------------------------------------ geometry helpers
const SPH = new THREE.SphereGeometry(1, 40, 28);
const SPH_LO = new THREE.SphereGeometry(1, 18, 12);
const geoCache = new Map();
function cached(key, fn) { if (!geoCache.has(key)) geoCache.set(key, fn()); return geoCache.get(key); }
const capsule = (r, l) => cached(`cap${r},${l}`, () => new THREE.CapsuleGeometry(r, l, 8, 20));
const cone = (r, h) => cached(`cone${r},${h}`, () => new THREE.ConeGeometry(r, h, 28, 1));
const torus = (R, r, arc) => cached(`tor${R},${r},${arc}`, () => new THREE.TorusGeometry(R, r, 10, 32, arc));
const cyl = (rt, rb, h, s = 28) => cached(`cyl${rt},${rb},${h},${s}`, () => new THREE.CylinderGeometry(rt, rb, h, s));

function add(parent, geo, mat, pos = [0, 0, 0], scl = 1, rot = [0, 0, 0], shadow = true) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(...pos);
  if (typeof scl === 'number') m.scale.setScalar(scl); else m.scale.set(...scl);
  m.rotation.set(...rot);
  m.castShadow = shadow;
  parent.add(m);
  return m;
}
const ell = (p, mat, pos, rad, rot, shadow = true) => add(p, SPH, mat, pos, rad, rot, shadow);

// ------------------------------------------------------------------ font
const font = await new FontLoader().loadAsync('vendor/helvetiker_bold.typeface.json');
function textGeo(str, size, depth, bevel = true) {
  return cached(`txt${str},${size},${depth}`, () => {
    const g = new TextGeometry(str, {
      font, size, depth, curveSegments: 10, bevelEnabled: bevel,
      bevelThickness: size * 0.05, bevelSize: size * 0.035, bevelSegments: 4,
    });
    g.computeBoundingBox();
    const b = g.boundingBox;
    g.translate(-(b.max.x + b.min.x) / 2, -(b.max.y + b.min.y) / 2, -(b.max.z + b.min.z) / 2);
    return g;
  });
}

// 바닥 그림자(부드러운 원)
const blobTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(20,50,20,0.55)'); g.addColorStop(0.6, 'rgba(20,50,20,0.22)'); g.addColorStop(1, 'rgba(20,50,20,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();
const blobMat = new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false });
const blobGeo = new THREE.PlaneGeometry(1, 1);
function blob(parent, size) {
  const m = new THREE.Mesh(blobGeo, blobMat.clone());
  m.rotation.x = -Math.PI / 2; m.position.y = 0.012; m.scale.set(size, size * 0.8, 1);
  m.renderOrder = 1;
  parent.add(m);
  return m;
}

// ------------------------------------------------------------------ characters
const ANIM = {
  dog: { body: 0xf5b56e, belly: 0xfff0db, acc: 0x8f5a3a, nose: 0x231815, iris: 0x5a3420 },
  cat: { body: 0xffa940, belly: 0xfff1da, acc: 0xd9741c, nose: 0xff8fa3, iris: 0x3d7a2a },
  rabbit: { body: 0xf6f2f8, belly: 0xffffff, acc: 0xffaec6, nose: 0xff8fa3, iris: 0x5a3420 },
  chick: { body: 0xffd52e, belly: 0xfff2a0, acc: 0xff9420, nose: 0xff9420, iris: 0x2a1a10 },
  bear: { body: 0xa8693d, belly: 0xe7c194, acc: 0x7a4a28, nose: 0x231815, iris: 0x3a2416 },
  penguin: { body: 0x2d3d63, belly: 0xffffff, acc: 0xffa22a, nose: 0xffa22a, iris: 0x1c2438 },
  pig: { body: 0xffb3c4, belly: 0xffd8e1, acc: 0xff8aa6, nose: 0xff8aa6, iris: 0x4a2a20 },
  frog: { body: 0x76d14f, belly: 0xdaf6b4, acc: 0x4fa936, nose: 0x2f5a22, iris: 0x2a1a10 },
  panda: { body: 0xf7f7f5, belly: 0xffffff, acc: 0x25252c, nose: 0x18181c, iris: 0x18181c },
  hamster: { body: 0xf7a55a, belly: 0xfff6ea, acc: 0xffb1a0, nose: 0xff8fa3, iris: 0x2a1a10 },
};

function makeEye(parent, x, y, z, rotY, irisHex, size = 1) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  g.rotation.y = rotY;
  g.scale.setScalar(size);
  const open = new THREE.Group(); g.add(open);
  ell(open, M(0xffffff, { r: 0.3, rim: 0.1 }), [0, 0, 0], [0.12, 0.14, 0.06], [0, 0, 0], false);
  ell(open, M(irisHex, { r: 0.25, rim: 0 }), [0, -0.012, 0.038], [0.098, 0.115, 0.035], [0, 0, 0], false);
  ell(open, M(0x07070a, { r: 0.15, rim: 0 }), [0, -0.012, 0.062], [0.058, 0.068, 0.02], [0, 0, 0], false);
  ell(open, M(0xffffff, { e: 0xffffff, ei: 1.2, rim: 0 }), [0.036, 0.042, 0.078], [0.032, 0.036, 0.012], [0, 0, 0], false);
  ell(open, M(0xffffff, { e: 0xffffff, ei: 1.2, rim: 0 }), [-0.032, -0.05, 0.074], [0.015, 0.015, 0.008], [0, 0, 0], false);
  const happy = add(g, torus(0.075, 0.018, Math.PI), M(0x2a1a14, { rim: 0 }), [0, -0.03, 0.045], 1, [0, 0, 0], false);
  happy.visible = false;
  parent.add(g);
  return { g, open, happy };
}

function makeAnimal(kind) {
  const P = ANIM[kind];
  const root = new THREE.Group();
  const hopG = new THREE.Group(); root.add(hopG);
  const sq = new THREE.Group(); hopG.add(sq);
  const shadowBlob = blob(root, 1.15);
  const mBody = M(P.body), mBelly = M(P.belly), mAcc = M(P.acc);
  const mDark = M(0x25252c);
  const parts = { root, hopG, sq, shadowBlob, arms: [], ears: [], eyes: [], kind };

  // 발
  const mFeet = (kind === 'chick' || kind === 'penguin') ? mAcc : kind === 'panda' ? mDark : M(shade(P.body, -0.12));
  for (const d of [-1, 1]) ell(sq, mFeet, [d * 0.19, 0.08, 0.1], [0.15, 0.09, 0.2]);

  // 몸통
  ell(sq, mBody, [0, 0.5, 0], [0.42, 0.44, 0.38]);
  ell(sq, mBelly, [0, 0.46, 0.15], [0.3, 0.32, 0.25]);
  if (kind === 'panda') { // 어깨 띠
    ell(sq, mDark, [0, 0.74, -0.02], [0.4, 0.16, 0.34]);
  }

  // 배 번호 스티커
  const badge = new THREE.Group();
  badge.position.set(0, 0.46, 0.41);
  badge.rotation.x = -0.12;
  add(badge, cyl(0.15, 0.15, 0.03, 40), M(0xffffff, { r: 0.4, rim: 0 }), [0, 0, 0], 1, [Math.PI / 2, 0, 0], false);
  const ring = add(badge, torus(0.15, 0.018, TAU), M(0xff5c8a, { r: 0.35, rim: 0 }), [0, 0, 0.012], 1, [0, 0, 0], false);
  sq.add(badge);
  badge.visible = false;
  parts.badge = badge; parts.badgeRing = ring; parts.badgeNum = null;

  // 팔
  const mArm = kind === 'panda' ? mDark : mBody;
  for (const d of [-1, 1]) {
    const pv = new THREE.Group();
    pv.position.set(d * 0.36, 0.72, 0.02);
    if (kind === 'chick' || kind === 'penguin') ell(pv, mArm, [d * 0.04, -0.18, 0], [0.09, 0.22, 0.13], [0, 0, d * 0.15]);
    else add(pv, capsule(0.085, 0.2), mArm, [0, -0.17, 0]);
    sq.add(pv);
    parts.arms.push(pv);
  }

  // 꼬리
  if (kind === 'dog' || kind === 'cat') {
    const curve = kind === 'cat'
      ? new THREE.CatmullRomCurve3([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0.12, 0.15, -0.1), new THREE.Vector3(0.18, 0.45, -0.12), new THREE.Vector3(0.08, 0.62, -0.1)])
      : new THREE.CatmullRomCurve3([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0.08, 0.15, -0.1), new THREE.Vector3(0.12, 0.3, -0.12)]);
    const tg = new THREE.Group(); tg.position.set(0.1, 0.35, -0.33);
    add(tg, cached('tail' + kind, () => new THREE.TubeGeometry(curve, 24, kind === 'cat' ? 0.055 : 0.07, 12)), kind === 'cat' ? mBody : mAcc);
    ell(tg, kind === 'cat' ? mBody : mAcc, curve.points.at(-1).toArray(), kind === 'cat' ? 0.055 : 0.07);
    sq.add(tg); parts.tail = tg;
  } else if (kind === 'rabbit' || kind === 'bear' || kind === 'panda' || kind === 'hamster') {
    ell(sq, kind === 'panda' ? mDark : (kind === 'rabbit' ? M(0xffffff) : mBody), [0, 0.32, -0.36], 0.12);
  } else if (kind === 'pig') {
    const tg = new THREE.Group(); tg.position.set(0, 0.42, -0.4);
    add(tg, torus(0.06, 0.022, TAU * 0.85), mAcc, [0, 0, 0], 1, [0, Math.PI / 2, 0]);
    sq.add(tg); parts.tail = tg;
  }

  // 머리
  const head = new THREE.Group();
  head.position.set(0, 1.22, 0);
  sq.add(head);
  parts.head = head;
  const HR = { frog: [0.6, 0.44, 0.5], hamster: [0.6, 0.52, 0.52], chick: [0.54, 0.5, 0.5] }[kind] || [0.56, 0.5, 0.5];
  const surf = (x, y) => HR[2] * Math.sqrt(Math.max(0, 1 - (x / HR[0]) ** 2 - (y / HR[1]) ** 2));
  ell(head, mBody, [0, 0, 0], HR);

  // 귀
  if (kind === 'dog') {
    for (const d of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(d * 0.44, 0.2, 0.02);
      ell(pv, mAcc, [d * 0.05, -0.22, 0], [0.13, 0.3, 0.08], [0, 0, d * 0.2]);
      head.add(pv); parts.ears.push(pv);
    }
    ell(head, M(shade(P.acc, 0.35)), [0.22, 0.14, surf(0.22, 0.14) - 0.04], [0.15, 0.14, 0.06], [0, 0.4, 0.3], false);
  } else if (kind === 'cat') {
    for (const d of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(d * 0.3, 0.36, 0); pv.rotation.z = -d * 0.38;
      add(pv, cone(0.17, 0.34), mBody, [0, 0.12, 0]);
      add(pv, cone(0.1, 0.22), M(0xffb3c1), [0, 0.09, 0.075], [1, 1, 0.4], [0, 0, 0], false);
      head.add(pv); parts.ears.push(pv);
    }
    for (const x of [-0.11, 0, 0.11]) ell(head, mAcc, [x, 0.34 - Math.abs(x) * 0.4, surf(x, 0.34) - 0.02], [0.028, 0.08, 0.03], [-0.6, 0, 0], false);
  } else if (kind === 'rabbit') {
    for (const d of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(d * 0.18, 0.4, 0); pv.rotation.z = -d * 0.12;
      add(pv, capsule(0.11, 0.48), mBody, [0, 0.33, 0], [1, 1, 0.6]);
      add(pv, capsule(0.06, 0.4), M(P.acc), [0, 0.33, 0.05], [1, 1, 0.3], [0, 0, 0], false);
      head.add(pv); parts.ears.push(pv);
    }
  } else if (kind === 'bear' || kind === 'panda' || kind === 'hamster') {
    const r = kind === 'hamster' ? 0.12 : 0.16;
    for (const d of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(d * 0.38, 0.36, -0.02);
      ell(pv, kind === 'panda' ? mDark : mBody, [0, 0, 0], [r, r, r * 0.6]);
      if (kind !== 'panda') ell(pv, kind === 'hamster' ? M(P.acc) : M(shade(P.body, 0.35)), [0, 0, r * 0.4], [r * 0.6, r * 0.6, r * 0.3], [0, 0, 0], false);
      head.add(pv); parts.ears.push(pv);
    }
  } else if (kind === 'pig') {
    for (const d of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(d * 0.32, 0.36, 0.05); pv.rotation.set(0.5, 0, -d * 0.5);
      add(pv, cone(0.14, 0.26), mBody, [0, 0.1, 0], [1, 1, 0.45]);
      head.add(pv); parts.ears.push(pv);
    }
  } else if (kind === 'chick') {
    for (const [i, a] of [-0.45, 0, 0.45].entries()) {
      const pv = new THREE.Group(); pv.position.set(0, 0.46, 0.02); pv.rotation.z = a;
      ell(pv, mBody, [0, 0.1, 0], [0.05, 0.13, 0.05]);
      head.add(pv); parts.ears.push(pv);
    }
  }

  // 얼굴
  let eyeY = 0.04, eyeX = 0.2, mouthY = -0.2, eyeSize = 1;
  if (kind === 'frog') {
    for (const d of [-1, 1]) ell(head, mBody, [d * 0.27, 0.32, 0.1], [0.19, 0.18, 0.18]);
    for (const d of [-1, 1]) parts.eyes.push(makeEye(head, d * 0.27, 0.34, 0.27, d * 0.2, P.iris, 1.05));
    mouthY = -0.12;
  } else {
    if (kind === 'panda') {
      for (const d of [-1, 1]) ell(head, mDark, [d * 0.2, 0.02, surf(0.2, 0.02) - 0.05], [0.15, 0.19, 0.07], [0, d * 0.35, -d * 0.55], false);
    }
    if (kind === 'penguin') {
      for (const d of [-1, 1]) ell(head, M(0xffffff), [d * 0.16, -0.02, 0.2], [0.27, 0.34, 0.32], [0, 0, 0], false);
    }
    for (const d of [-1, 1]) {
      const x = d * eyeX, z = surf(x, eyeY);
      parts.eyes.push(makeEye(head, x, eyeY, z - 0.025, Math.asin(clamp(x / HR[0])) * 0.85, P.iris, eyeSize));
    }
  }
  // 볼터치
  for (const d of [-1, 1]) {
    const x = d * 0.34, y = -0.15;
    ell(head, M(0xff8fa8, { rim: 0, op: 0.75 }), [x, y, surf(x, y) - 0.015], [0.085, 0.05, 0.03], [0, d * 0.6, 0], false);
  }
  // 주둥이·코
  const muzzle = { dog: [0.24, 0.16, 0.13], bear: [0.24, 0.17, 0.14], hamster: [0.2, 0.14, 0.12], cat: [0.17, 0.11, 0.1], rabbit: [0.17, 0.11, 0.1], panda: [0.2, 0.14, 0.11] }[kind];
  if (muzzle) {
    const mz = kind === 'bear' ? M(shade(P.body, 0.45)) : kind === 'panda' ? M(0xffffff) : mBelly;
    ell(head, mz, [0, -0.15, surf(0, -0.15) - muzzle[2] * 0.55], muzzle, [0, 0, 0], false);
    if (kind === 'hamster') for (const d of [-1, 1]) ell(head, mBelly, [d * 0.27, -0.16, surf(0.27, -0.16) - 0.12], [0.21, 0.17, 0.15], [0, 0, 0], false);
    const big = kind === 'dog' || kind === 'bear' || kind === 'panda';
    const nz = surf(0, -0.08) + (muzzle[2] * 0.45);
    ell(head, M(P.nose, { r: 0.22, rim: 0.1 }), [0, -0.075, nz], big ? [0.075, 0.055, 0.05] : [0.045, 0.035, 0.03], [0, 0, 0], false);
    ell(head, M(0xffffff, { e: 0xffffff, ei: 0.6, rim: 0 }), [-0.02, -0.06, nz + (big ? 0.045 : 0.027)], big ? 0.016 : 0.01, [0, 0, 0], false);
    mouthY = -0.2;
  }
  if (kind === 'pig') {
    add(head, cyl(0.15, 0.15, 0.12, 40), mAcc, [0, -0.1, surf(0, -0.1) + 0.02], [1, 1, 0.75], [Math.PI / 2, 0, 0], false);
    for (const d of [-1, 1]) ell(head, M(shade(P.acc, -0.45)), [d * 0.05, -0.1, surf(0, -0.1) + 0.08], [0.025, 0.04, 0.015], [0, 0, 0], false);
    mouthY = -0.27;
  }
  if (kind === 'chick' || kind === 'penguin') {
    const beak = new THREE.Group(); beak.position.set(0, -0.09, surf(0, -0.09) - 0.02);
    add(beak, cone(0.09, 0.18), mAcc, [0, 0.02, 0.07], [1, 1, 0.7], [Math.PI / 2, 0, 0], false);
    const low = new THREE.Group(); beak.add(low);
    add(low, cone(0.07, 0.13), M(shade(P.acc, -0.15)), [0, -0.04, 0.05], [1, 1, 0.6], [Math.PI / 2, 0, 0], false);
    head.add(beak); parts.beakLow = low;
  }
  if (kind === 'cat' || kind === 'rabbit' || kind === 'hamster') {
    const wm = M(shade(P.body, -0.45), { rim: 0 });
    for (const d of [-1, 1]) for (const k of [-1, 1]) {
      add(head, cyl(0.005, 0.005, 0.28, 6), wm, [d * 0.3, -0.13 + k * 0.03, surf(0.22, -0.13) + 0.02], 1, [0, 0, Math.PI / 2 + d * k * 0.15], false);
    }
  }
  // 입
  if (kind !== 'chick' && kind !== 'penguin') {
    const mg = new THREE.Group();
    mg.position.set(0, mouthY, surf(0, mouthY) - 0.005);
    const wide = kind === 'frog' ? 2.6 : 1;
    const smile = add(mg, torus(0.065 * wide, 0.016, Math.PI), M(0x4a1e1e, { rim: 0 }), [0, 0.02, 0.01], 1, [0, 0, Math.PI], false);
    const open = new THREE.Group(); mg.add(open);
    ell(open, M(0x8a2333, { r: 0.4, rim: 0 }), [0, -0.02, 0], [0.085 * (kind === 'frog' ? 2 : 1), 0.075, 0.045], [0, 0, 0], false);
    ell(open, M(0xff8a9a, { rim: 0 }), [0, -0.055, 0.02], [0.05 * (kind === 'frog' ? 1.8 : 1), 0.028, 0.03], [0, 0, 0], false);
    if (kind === 'rabbit' || kind === 'hamster') add(mg, new THREE.BoxGeometry(0.07, 0.06, 0.02), M(0xffffff, { rim: 0 }), [0, -0.035, 0.035], 1, [0, 0, 0], false);
    head.add(mg);
    parts.smile = smile; parts.mouthOpen = open;
  }
  return parts;
}

function setBadge(p, num, colorHex) {
  if (p.badgeNum !== num) {
    if (p.badgeNumMesh) p.badge.remove(p.badgeNumMesh);
    const g = textGeo(String(num), num >= 10 ? 0.12 : 0.16, 0.025, false);
    p.badgeNumMesh = add(p.badge, g, M(colorHex, { r: 0.35, rim: 0 }), [0, 0, 0.03], 1, [0, 0, 0], false);
    p.badgeRing.material = M(colorHex, { r: 0.35, rim: 0 });
    p.badgeNum = num;
  }
}

function pose(p, st) {
  const t = st.t || 0;
  p.hopG.position.y = st.hop || 0;
  const sx = st.sx || 1, sy = st.sy || 1;
  p.sq.scale.set(sx, sy, sx);
  p.sq.rotation.set(0, 0, st.tilt || 0);
  p.hopG.rotation.y = st.spin || 0;
  p.head.rotation.set(st.nod || 0, st.turn || 0, st.headTilt || 0);
  const blink = st.blink || 0, happy = (st.happy || 0) > 0.5;
  for (const e of p.eyes) {
    e.open.visible = !happy;
    e.happy.visible = happy;
    e.open.scale.y = 1 - 0.92 * blink;
  }
  const mouth = st.mouth || 0;
  if (p.smile) {
    p.smile.visible = mouth < 0.15;
    p.mouthOpen.visible = mouth >= 0.15;
    p.mouthOpen.scale.set(1, 0.35 + mouth * 0.9, 1);
  }
  if (p.beakLow) p.beakLow.rotation.x = mouth * 0.5;
  const arm = st.arm || 0;
  p.arms.forEach((a, i) => {
    const d = i === 0 ? -1 : 1;
    a.rotation.z = d * (0.28 + arm * 2.2 + Math.sin(t * 9 + i) * 0.15 * arm);
  });
  if (p.tail) p.tail.rotation.z = Math.sin(t * (p.kind === 'dog' ? 10 : 4)) * 0.35;
  p.ears.forEach((e, i) => {
    const d = i === 0 ? -1 : 1;
    if (p.kind === 'rabbit') e.rotation.z = -d * 0.12 + (d > 0 ? -0.5 * (0.5 + 0.5 * Math.sin(t * 1.5)) : 0) + Math.sin(t * 3 + d) * 0.05;
    else if (p.kind === 'dog') e.rotation.z = Math.sin(t * 4 + d) * 0.12 + (st.hop || 0) * 0.15 * d;
    else if (p.kind === 'cat') e.rotation.z = -d * 0.38 + Math.sin(t * 3.5 + i) * 0.05;
    else if (p.kind === 'chick') e.rotation.z = [-0.45, 0, 0.45][i] + Math.sin(t * 4 + i) * 0.12;
  });
  if (st.num) {
    p.badge.visible = st.num[1] > 0.01;
    p.badge.scale.setScalar(Math.max(0.001, st.num[1]));
    setBadge(p, st.num[0], st.num[2]);
  } else p.badge.visible = false;
  const h = st.hop || 0;
  const k = clamp(1 - h / 3);
  p.shadowBlob.scale.set(1.15 * (0.55 + 0.45 * k), 0.92 * (0.55 + 0.45 * k), 1);
  p.shadowBlob.material.opacity = k;
}

function idleState(t, seed) {
  const br = Math.sin(t * 3 + seed) * 0.02;
  const bl = (t + hash(seed) * 3) % (2.6 + hash(seed, 1) * 1.6);
  return {
    t, sx: 1 + br, sy: 1 - br, blink: bl < 0.1 ? 1 : bl < 0.15 ? 0.5 : 0,
    arm: 0.05 * Math.sin(t * 2 + seed), headTilt: 0.07 * Math.sin(t * 1.3 + seed),
    turn: 0.12 * Math.sin(t * 0.7 + seed * 2), hop: Math.abs(Math.sin(t * 2.2 + seed)) * 0.03,
  };
}
function jumpState(tj, dur = 0.55, height = 1.0) {
  if (tj < 0) return {};
  if (tj < 0.08) { const k = tj / 0.08; return { sx: 1 + 0.15 * k, sy: 1 - 0.18 * k }; }
  tj -= 0.08;
  if (tj < dur) {
    const p = tj / dur, s = 0.12 * (1 - Math.abs(2 * p - 1));
    return { hop: 4 * p * (1 - p) * height, sx: 1 - s, sy: 1 + s, arm: 0.9, happy: 1, mouth: 0.8 };
  }
  tj -= dur;
  if (tj < 0.22) { const k = Math.sin(tj / 0.22 * Math.PI) * (1 - tj / 0.22); return { sx: 1 + 0.2 * k, sy: 1 - 0.2 * k, happy: 1, mouth: 0.5 }; }
  return {};
}

// ------------------------------------------------------------------ world
const skyUniforms = { top: { value: new THREE.Color(0x6fc3ff) }, hor: { value: new THREE.Color(0xe8f7ff) }, sunDir: { value: new THREE.Vector3(0.5, 0.45, -0.75).normalize() } };
const sky = new THREE.Mesh(new THREE.SphereGeometry(250, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false, uniforms: skyUniforms,
  vertexShader: `varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `uniform vec3 top; uniform vec3 hor; uniform vec3 sunDir; varying vec3 vP;
    void main(){ float h = clamp(vP.y, 0.0, 1.0);
      vec3 c = mix(hor, top, smoothstep(0.0, 0.55, h));
      float s = max(dot(normalize(vP), sunDir), 0.0);
      c += vec3(1.0,0.92,0.7) * (pow(s, 400.0) * 1.5 + pow(s, 12.0) * 0.25);
      gl_FragColor = vec4(c, 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
}));
scene.add(sky);
scene.fog = new THREE.Fog(0xe8f7ff, 32, 130);

const hemi = new THREE.HemisphereLight(0xd2ebff, 0x6fae4c, 1.25); scene.add(hemi);
const key = new THREE.DirectionalLight(0xfff0dc, 2.7);
key.position.set(7, 12, 9); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -11, right: 11, top: 9, bottom: -9, near: 1, far: 45 });
key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02;
scene.add(key); scene.add(key.target);
const fill = new THREE.DirectionalLight(0xc4dcff, 0.75); fill.position.set(-9, 5, 7); scene.add(fill);
const rimL = new THREE.DirectionalLight(0xffffff, 1.6); rimL.position.set(-4, 7, -10); scene.add(rimL);

// 지형
function groundH(x, z) {
  let h = 0.04 * Math.sin(x * 1.1) * Math.cos(z * 0.9);
  const back = clamp((-z - 5) / 10);
  h += back * back * (1.3 + 0.9 * Math.sin(x * 0.22 + 1.2) + 0.6 * Math.sin(x * 0.47 + 0.3));
  return h;
}
{
  const g = new THREE.PlaneGeometry(160, 120, 220, 160);
  g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position, cols = [];
  const c1 = new THREE.Color(0x7fcf5c), c2 = new THREE.Color(0x5db146), c3 = new THREE.Color(0x9fdc72);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    pos.setY(i, groundH(x, z));
    const n = 0.5 + 0.5 * Math.sin(x * 0.7 + Math.sin(z * 0.5) * 2) * Math.cos(z * 0.6 - x * 0.2);
    const c = c1.clone().lerp(c2, n * 0.6).lerp(c3, clamp(groundH(x, z) / 3) * 0.6);
    cols.push(c.r, c.g, c.b);
  }
  g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
  g.computeVertexNormals();
  const gm = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  gm.receiveShadow = true;
  scene.add(gm);
}
// 먼 언덕
for (let i = 0; i < 9; i++) {
  const r = 14 + hash(i, 3) * 12;
  const m = ell(scene, M([0x9ad97a, 0x86cf6a, 0xb2e391][i % 3], { r: 0.95, rim: 0.15 }), [-70 + i * 18 + hash(i) * 8, -r * 0.62, -48 - hash(i, 2) * 25], [r * 1.6, r, r]);
  m.castShadow = false;
}

// 나무
const trees = [];
{
  const spots = [[-9.5, -6.5], [-6.5, -9], [-3, -11.5], [1.5, -10], [5.5, -12], [9.5, -7.5], [12, -11], [-12, -10],
    [7.5, -5.8], [-8, -4.6], [3.8, -15], [-5.5, -16], [14.5, -6.5], [-14.5, -6]];
  spots.forEach(([x, z], i) => {
    const g = new THREE.Group();
    const s = 0.9 + hash(i, 7) * 0.5;
    g.position.set(x, groundH(x, z), z); g.scale.setScalar(s);
    add(g, cyl(0.16, 0.22, 1.6, 12), M(0x9a6a43, { r: 0.9, rim: 0.1 }), [0, 0.8, 0]);
    const leaf = M([0x5cbf4a, 0x6fcb55, 0x4fb244][i % 3], { r: 0.75, rim: 0.3 });
    const geo = cached('ico', () => new THREE.IcosahedronGeometry(1, 3));
    add(g, geo, leaf, [0, 2.15, 0], 1.0);
    add(g, geo, leaf, [-0.62, 1.75, 0.15], 0.72);
    add(g, geo, leaf, [0.6, 1.8, -0.1], 0.75);
    add(g, geo, leaf, [0.1, 2.75, 0.05], 0.6);
    scene.add(g); trees.push(g);
  });
}

// 잔디 (인스턴스 + 바람)
const grassUniform = { value: 0 };
{
  const N = 9000;
  const bg = new THREE.ConeGeometry(0.03, 0.28, 3, 1); bg.translate(0, 0.14, 0);
  const gmat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 });
  gmat.onBeforeCompile = sh => {
    sh.uniforms.uTime = grassUniform;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec3 ip = instanceMatrix[3].xyz;
        float w = sin(uTime * 2.0 + ip.x * 0.6 + ip.z * 0.4) * 0.06 + sin(uTime * 3.3 + ip.x * 1.7) * 0.02;
        transformed.x += w * position.y * 4.0; transformed.z += w * position.y * 1.5;`);
  };
  const im = new THREE.InstancedMesh(bg, gmat, N);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), s = new THREE.Vector3();
  const c = new THREE.Color();
  for (let i = 0; i < N; i++) {
    const x = (hash(i, 1) - 0.5) * 26, z = -7 + hash(i, 2) * 14;
    e.set((hash(i, 3) - 0.5) * 0.5, hash(i, 4) * TAU, (hash(i, 5) - 0.5) * 0.5);
    q.setFromEuler(e);
    const sc = 0.7 + hash(i, 6) * 0.8;
    m4.compose(v.set(x, groundH(x, z), z), q, s.set(sc, sc * (0.8 + hash(i, 8) * 0.6), sc));
    im.setMatrixAt(i, m4);
    im.setColorAt(i, c.setHSL(0.27 + hash(i, 7) * 0.06, 0.6, 0.38 + hash(i, 9) * 0.15));
  }
  im.receiveShadow = true;
  scene.add(im);
}

// 꽃 (인스턴스)
const flowers = [];
const FLOWER_N = 70;
const petalIM = new THREE.InstancedMesh(SPH_LO, M(0xffffff, { r: 0.6, rim: 0.2 }), FLOWER_N * 5);
const centerIM = new THREE.InstancedMesh(SPH_LO, M(0xffc531, { r: 0.6, rim: 0.1 }), FLOWER_N);
const stemIM = new THREE.InstancedMesh(cyl(0.015, 0.02, 1, 6), M(0x3f9a35, { rim: 0 }), FLOWER_N);
{
  const pal = [0xffffff, 0xffb8d0, 0xfff07a, 0xc8d8ff, 0xff9a8a];
  const c = new THREE.Color();
  for (let i = 0; i < FLOWER_N; i++) {
    let x = (hash(i, 11) - 0.5) * 24, z = -6 + hash(i, 12) * 12;
    if (Math.abs(x - 0.8) < 4.8 && z > -2.6 && z < 2.2) x += x > 0.8 ? 5 : -5; // 무대 비우기
    flowers.push({ x, z, h: 0.25 + hash(i, 13) * 0.15, s: 0.8 + hash(i, 14) * 0.5, ph: hash(i, 15) * 6 });
    for (let k = 0; k < 5; k++) petalIM.setColorAt(i * 5 + k, c.setHex(pal[i % pal.length]));
  }
  [petalIM, centerIM, stemIM].forEach(m => { m.castShadow = true; scene.add(m); });
}
function updateFlowers(t) {
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), s = new THREE.Vector3();
  flowers.forEach((f, i) => {
    const sw = Math.sin(t * 2 + f.ph) * 0.12;
    const by = groundH(f.x, f.z);
    const top = new THREE.Vector3(f.x + Math.sin(sw) * f.h, by + f.h * Math.cos(sw), f.z);
    q.setFromEuler(e.set(0, 0, -sw));
    m4.compose(v.set(f.x + Math.sin(sw) * f.h / 2, by + f.h / 2, f.z), q, s.set(1, f.h, 1));
    stemIM.setMatrixAt(i, m4);
    const r = 0.05 * f.s;
    m4.compose(top, q, s.set(r * 0.8, r * 0.8, r * 0.8)); centerIM.setMatrixAt(i, m4);
    for (let k = 0; k < 5; k++) {
      const a = k * TAU / 5 + t * 0.2;
      q.setFromEuler(e.set(-0.3, 0, a - sw));
      m4.compose(v.set(top.x + Math.cos(a) * r * 1.3, top.y + Math.sin(a) * r * 1.3, top.z + 0.01), q, s.set(r * 1.1, r * 0.75, r * 0.35));
      petalIM.setMatrixAt(i * 5 + k, m4);
    }
  });
  [petalIM, centerIM, stemIM].forEach(m => { m.instanceMatrix.needsUpdate = true; });
}

// 버섯
for (const [x, z, s] of [[-6.2, 1.8, 1], [-5.4, 2.5, 0.7], [7.2, 1.5, 0.9], [6.3, 2.6, 0.6], [-7.8, -1.5, 1.2]]) {
  const g = new THREE.Group(); g.position.set(x, groundH(x, z), z); g.scale.setScalar(s * 0.8);
  add(g, cyl(0.12, 0.16, 0.4, 20), M(0xfff6e8), [0, 0.2, 0]);
  const capG = cached('cap', () => new THREE.SphereGeometry(0.34, 32, 16, 0, TAU, 0, Math.PI / 2));
  add(g, capG, M(0xff5a4a, { r: 0.45 }), [0, 0.36, 0], [1, 0.8, 1]);
  for (let k = 0; k < 6; k++) {
    const a = k * TAU / 6, el = 0.6 + (k % 2) * 0.3;
    ell(g, M(0xffffff, { rim: 0 }), [Math.cos(a) * 0.34 * Math.cos(el), 0.36 + 0.27 * Math.sin(el), Math.sin(a) * 0.34 * Math.cos(el)], [0.06, 0.04, 0.06], [0, 0, 0], false);
  }
  scene.add(g);
}

// 구름 (인스턴스)
const CLOUD_N = 8, PUFFS = 6;
const cloudIM = new THREE.InstancedMesh(SPH, M(0xffffff, { e: 0xffffff, ei: 0.55, r: 1, rim: 0.2 }), CLOUD_N * PUFFS);
cloudIM.material.fog = false;
scene.add(cloudIM);
function updateClouds(t) {
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), s = new THREE.Vector3();
  for (let c = 0; c < CLOUD_N; c++) {
    const span = 120;
    const cx = ((hash(c, 1) * span + t * (0.5 + hash(c, 2) * 0.4)) % span) - span / 2;
    const cy = 12 + hash(c, 3) * 9, cz = -55 - hash(c, 4) * 20, sc = 2.2 + hash(c, 5) * 1.6;
    for (let k = 0; k < PUFFS; k++) {
      const ox = (k - 2.5) * 1.1 * sc, oy = Math.sin(k * 1.7) * 0.5 * sc + (k === 2 || k === 3 ? 0.6 * sc : 0);
      const r = (1.1 + 0.5 * Math.sin(k * 2.3 + c)) * sc * (k === 0 || k === 5 ? 0.7 : 1);
      m4.compose(v.set(cx + ox, cy + oy, cz), q, s.set(r, r * 0.85, r));
      cloudIM.setMatrixAt(c * PUFFS + k, m4);
    }
  }
  cloudIM.instanceMatrix.needsUpdate = true;
}

// 나비
const butterflies = [];
for (let i = 0; i < 3; i++) {
  const g = new THREE.Group();
  const col = [0xffd23a, 0xff8ad0, 0x8ad0ff][i];
  const wings = [];
  for (const d of [-1, 1]) {
    const w = new THREE.Group();
    ell(w, M(col, { rim: 0.3, side: THREE.DoubleSide }), [d * 0.09, 0.02, 0], [0.09, 0.07, 0.008], [0, 0, d * 0.3], false);
    ell(w, M(shade(col, 0.3), { rim: 0.3, side: THREE.DoubleSide }), [d * 0.07, -0.06, 0], [0.06, 0.045, 0.008], [0, 0, -d * 0.4], false);
    g.add(w); wings.push(w);
  }
  ell(g, M(0x3a2a20), [0, 0, 0], [0.015, 0.06, 0.015], [0, 0, 0], false);
  scene.add(g); butterflies.push({ g, wings, i });
}
function updateButterflies(t) {
  for (const b of butterflies) {
    const k = b.i;
    const a = t * (0.35 + 0.1 * k) + k * 2.1;
    b.g.position.set(Math.cos(a) * (5 + k) + (k - 1) * 2, 2.6 + Math.sin(t * 1.3 + k) * 0.6 + k * 0.5, -2.5 + Math.sin(a) * 2.2);
    b.g.rotation.y = -a + Math.PI;
    const f = Math.sin(t * 18 + k) * 0.9;
    b.wings[0].rotation.y = f; b.wings[1].rotation.y = -f;
  }
}

// ------------------------------------------------------------------ number
const bigNumGroup = new THREE.Group(); scene.add(bigNumGroup);
let bigNumMesh = null, bigNumKey = null;
const bigNumBlob = blob(scene, 2.4);
function setBigNumber(n, colorHex) {
  const k = n + ':' + colorHex;
  if (k === bigNumKey) return;
  if (bigNumMesh) bigNumGroup.remove(bigNumMesh);
  bigNumMesh = add(bigNumGroup, textGeo(String(n), n >= 10 ? 1.25 : 1.6, 0.42), M(colorHex, { r: 0.28, rim: 0.35 }));
  bigNumKey = k;
}

// ------------------------------------------------------------------ timeline
const SC = CFG.scenes;
const SKY3D = [['#3fa6ff', '#c9ecff'], ['#5ab8ff', '#ffe3c4'], ['#3d9cf5', '#d3f1ff'], ['#4fb4ff', '#e2fbd6'], ['#4aa3f0', '#ffe0c0'],
  ['#2f8fef', '#cfe7ff'], ['#58aefc', '#ffdbe8'], ['#45b0ff', '#e0f8cf'], ['#6c8cff', '#eadfff'], ['#4aa8ff', '#ffe8c8']];
const NUMC = CFG.numColors.map(hex);
const SEGS = [['intro', null, CFG.intro], ...SC.map((s, i) => ['num', i, CFG.head + s[0] * CFG.step + 0.6 + CFG.tail]), ['outro', null, CFG.outro]];
const STARTS = []; { let a = 0; for (const s of SEGS) { STARTS.push(a); a += s[2]; } }

const pool = new Map();
function getChar(kind, i) {
  const k = kind + i;
  if (!pool.has(k)) { const p = makeAnimal(kind); scene.add(p.root); pool.set(k, p); }
  return pool.get(k);
}
let activeSeg = -1, active = [];
function useChars(list) {
  for (const p of pool.values()) p.root.visible = false;
  active = list.map(([kind, i]) => { const p = getChar(kind, i); p.root.visible = true; return p; });
}

function slots(n) {
  if (n <= 5) return Array.from({ length: n }, (_, i) => [1.25 + (i - (n - 1) / 2) * 1.4, 0]);
  // 두 줄: 앞줄이 화면에서 뒷줄 사이사이에 보이도록 원근 보정
  const b = Math.ceil(n / 2), f = n - b, zB = -1.6, zF = 1.0, camX = 1.4, camZ = 13.5, sp = 1.75;
  const back = Array.from({ length: b }, (_, i) => [1.1 + (i - (b - 1) / 2) * sp, zB]);
  const mids = Array.from({ length: f }, (_, i) => 1.1 + (f === b ? sp / 2 : 0) + (i - (f - 1) / 2) * sp);
  const k = (camZ - zF) / (camZ - zB);
  return [...back, ...mids.map(x => [camX + (x - camX) * k, zF])];
}

const v3 = new THREE.Vector3();
function project(x, y, z) {
  v3.set(x, y, z).project(camera);
  return [(v3.x * 0.5 + 0.5) * OW, (-v3.y * 0.5 + 0.5) * OH, v3.z < 1 ? 1 : 0];
}

function setSky(top, hor) {
  skyUniforms.top.value.setHex(hex(top));
  skyUniforms.hor.value.setHex(hex(hor));
  scene.fog.color.setHex(hex(hor));
}

function poseSeg(si, t) {
  const [kind, idx, dur] = SEGS[si];
  const meta = { si, t, anchors: [] };
  if (si !== activeSeg) {
    activeSeg = si;
    if (kind === 'intro') useChars(SC.map((s, i) => [s[6], 0]));
    else if (kind === 'num') useChars(Array.from({ length: SC[idx][0] }, (_, i) => [SC[idx][6], i]));
    else useChars(SC.map((s, i) => [s[6], 0]));
  }
  bigNumGroup.visible = false; bigNumBlob.visible = false;

  if (kind === 'intro') {
    setSky('#3fa6ff', '#d8f1ff');
    const k = t / dur;
    camera.position.set(lerp(-1.5, 1.2, easeIO(k)), lerp(2.6, 2.1, easeIO(k)), lerp(15.5, 13.2, easeIO(k)));
    camera.lookAt(0, 2.8, 0);
    active.forEach((p, i) => {
      const tx = -5.2 + i * 1.155, tz = (i % 2) * 0.7 - 0.2;
      const ti = t - 0.25 * i;
      const st = idleState(t, i);
      let x = tx;
      if (ti < 0) { p.root.visible = false; return; }
      p.root.visible = true;
      if (ti < 1.2) {
        const q = easeOut(ti / 1.2);
        x = lerp(i < 5 ? -13 : 13, tx, q);
        Object.assign(st, { hop: Math.abs(Math.sin(ti * 9)) * 0.5 * (1 - q), arm: 0.6, mouth: 0.6, spin: (i < 5 ? 1 : -1) * 0.9 * (1 - q) });
      } else if (t > 4.2) Object.assign(st, jumpState((t - 4.2 - i * 0.12) % 2.4, 0.5, 0.8));
      st.tilt = 0.05 * Math.sin(t * 3 + i);
      p.root.position.set(x, 0, tz);
      pose(p, st);
      meta.anchors.push(project(x, 2.0 + (st.hop || 0), tz));
    });
  } else if (kind === 'num') {
    const [n, , , , , , ak] = SC[idx];
    const col = NUMC[idx];
    setSky(SKY3D[idx][0], SKY3D[idx][1]);
    const k = t / dur;
    const two = n > 5;
    camera.position.set(0.9 + 0.7 * Math.sin(t * 0.22 + idx), (two ? 4.3 : 2.45) + 0.15 * Math.sin(t * 0.3), lerp(two ? 14.4 : 13.2, two ? 13.0 : 11.8, easeIO(k)));
    camera.lookAt(0.55, two ? 1.55 : 1.75, 0);
    // 3D 숫자
    const bs = elastic(clamp((t - 0.15) / 0.9));
    setBigNumber(n, col);
    bigNumGroup.visible = bs > 0.01;
    bigNumBlob.visible = bigNumGroup.visible;
    const ny = 2.35 + 0.12 * Math.sin(t * 2);
    bigNumGroup.position.set(-3.7, ny, 0.4);
    bigNumGroup.scale.setScalar(Math.max(0.001, bs));
    bigNumGroup.rotation.set(0.05 * Math.sin(t * 1.5), 0.32 + (1 - easeOut((t - 0.15) / 1.1)) * -TAU + 0.18 * Math.sin(t * 1.1), 0.04 * Math.sin(t * 1.7));
    bigNumBlob.position.set(-3.7, 0.015, 0.4);
    bigNumBlob.scale.set(2.4 * bs, 1.6 * bs, 1);
    bigNumBlob.material.opacity = 0.7;
    meta.num = project(-3.7, 0.75, 0.4);
    meta.numTop = project(-3.7, ny, 0.4);

    const sl = slots(n);
    const cheer0 = CFG.head + n * CFG.step + 0.6;
    active.forEach((p, i) => {
      const [x, z] = sl[i];
      const ti = t - (CFG.head + i * CFG.step);
      if (ti < 0) { p.root.visible = false; meta.anchors.push([0, 0, 0]); return; }
      p.root.visible = true;
      const st = idleState(t, i * 3 + idx);
      let px = x, pz = z;
      if (ti < CFG.fly) {
        const q = ti / CFG.fly;
        px = lerp(9.5, x, easeIO(q)); pz = lerp(z + 1.5, z, q);
        Object.assign(st, { hop: 4 * q * (1 - q) * 2.6 + (1 - q) * 0.6, sx: 0.92, sy: 1.1, arm: 1, mouth: 0.7, tilt: 0.35 * (1 - q), spin: -(1 - q) * TAU });
      } else {
        const tl = ti - CFG.fly;
        if (tl < 0.25) { const q = Math.sin(tl / 0.25 * Math.PI) * (1 - tl / 0.25 * 0.5); Object.assign(st, { sx: 1 + 0.22 * q, sy: 1 - 0.22 * q, hop: 0 }); }
        if (tl < 0.9) Object.assign(st, { mouth: 0.7 * (1 - tl / 0.9) + 0.1, happy: tl < 0.5 ? 1 : 0, arm: 0.8 * (1 - tl / 0.9) });
        const tc = t - cheer0 - i * 0.09;
        if (tc > 0) { Object.assign(st, jumpState(tc % 1.35, 0.5, 1.0)); st.mouth = Math.max(st.mouth || 0, 0.5); }
        st.num = [i + 1, backOut(clamp((tl - 0.1) / 0.35)), col];
        // 숫자 쪽을 살짝 바라보기
        st.turn = (st.turn || 0) - 0.15;
      }
      p.root.position.set(px, groundH(px, pz), pz);
      pose(p, st);
      meta.anchors.push(project(px, 2.05 + (st.hop || 0), pz));
    });
  } else {
    setSky('#5aa8ff', '#ffe0ec');
    const k = t / dur;
    camera.position.set(lerp(0.8, -0.6, easeIO(k)), 2.5, lerp(15.5, 14.5, easeIO(k)));
    camera.lookAt(0, 2.3, 0);
    active.forEach((p, i) => {
      const x = -5.4 + i * 1.2, z = i % 2 === 0 ? -0.7 : 0.7;
      const ti = t - 0.15 * i;
      if (ti < 0) { p.root.visible = false; meta.anchors.push([0, 0, 0]); return; }
      p.root.visible = true;
      const st = idleState(t, i + 50);
      st.hop += (1 - easeOut(clamp(ti / 0.6))) * 6;
      const hl = 2.2 + i * 0.55;
      if (t > hl) Object.assign(st, jumpState(t - hl, 0.45, 0.9));
      if (t > 8.0) { Object.assign(st, jumpState((t - 8.0 - i * 0.07) % 1.2, 0.45, 0.8)); st.arm = 0.6 + 0.4 * Math.sin(t * 10 + i); }
      st.num = [i + 1, t > hl ? backOut(clamp((t - hl) / 0.35)) : 0, NUMC[i]];
      p.root.position.set(x, 0, z);
      pose(p, st);
      meta.anchors.push(project(x, 2.0 + (st.hop || 0), z));
    });
  }
  return meta;
}

async function renderFrame(fi) {
  const T = fi / CFG.fps;
  let si = 0;
  for (let i = 0; i < STARTS.length; i++) if (STARTS[i] <= T + 1e-9) si = i;
  si = Math.min(si, SEGS.length - 1);
  const t = T - STARTS[si];
  grassUniform.value = T;
  updateFlowers(T); updateClouds(T); updateButterflies(T);
  trees.forEach((g, i) => { g.rotation.z = Math.sin(T * 1.2 + i) * 0.015; });
  camera.updateMatrixWorld();
  const meta = poseSeg(si, t);
  camera.updateMatrixWorld();
  // 투영 좌표를 카메라 갱신 후 다시 계산하기 위해 한 번 더
  const meta2 = poseSeg(si, t);
  renderer.render(scene, camera);
  octx.drawImage(renderer.domElement, 0, 0, OW, OH);
  const blobOut = await new Promise(r => outCanvas.toBlob(r, 'image/jpeg', 0.95));
  const b64 = await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result.split(',')[1]); fr.readAsDataURL(blobOut); });
  return { img: b64, meta: meta2 };
}
window.renderFrame = renderFrame;
window.TOTAL_FRAMES = Math.floor((STARTS.at(-1) + SEGS.at(-1)[2]) * CFG.fps);
window.ready = true;
