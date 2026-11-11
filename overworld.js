/*
 * Overworld: a walkable pixel-art version of the landing page.
 *
 * The landing page's .card elements stay the single source of truth: every
 * card becomes an object somewhere on a little night-time East Village map,
 * and its name, blurb, stats and links fill the dialog when you walk up to it.
 *
 * Controls
 *   Desktop: arrows / WASD to walk, Space or Enter to open, 1-3 for a
 *            specific link, Esc for the classic scroll view.
 *            Switching skins (Walk / Glass / Classic) lives in views.js.
 *   Touch:   drag the stick to walk, A to open, or tap anywhere to walk there.
 *
 * views.js remembers which skin was chosen; this file remembers your spot on
 * the map in sessionStorage, so the back button drops you where you were.
 */
(() => {
  'use strict';
  if (window.__hofOverworld) return;
  window.__hofOverworld = true;

  // ---------------------------------------------------------------- map ----
  const T = 16, W = 46, H = 34;
  const ROAD = 0, WALK = 1, BLD = 2, GRASS = 3, PATH = 4, PROM = 5, WATER = 6;
  const AVES = [[4, '2ND AVE'], [18, '1ST AVE'], [32, 'AVE A']];
  const STS = [[4, 'E 10TH ST'], [15, 'ST MARKS PL'], [26, 'E 7TH ST']];
  const PARK = { x0: 21, x1: 29, y0: 18, y1: 23 };
  const PROM_X0 = 35, WATER_X0 = 39;
  const SPAWN = { x: 13, y: 17 };

  function classify(x, y) {
    if (x >= WATER_X0) return WATER;
    if (x >= PROM_X0) return PROM;
    if (x >= PARK.x0 && x <= PARK.x1 && y >= PARK.y0 && y <= PARK.y1) {
      if (x === PARK.x0 || x === PARK.x1 || y === PARK.y0 || y === PARK.y1 || x === 25 || y === 20) return PATH;
      return GRASS;
    }
    for (const [ax] of AVES) if (Math.abs(x - ax) <= 1) return ROAD;
    for (const [sy] of STS) if (Math.abs(y - sy) <= 1) return ROAD;
    for (const [ax] of AVES) if (Math.abs(x - ax) === 2) return WALK;
    for (const [sy] of STS) if (Math.abs(y - sy) === 2) return WALK;
    return BLD;
  }

  const tiles = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) tiles[y * W + x] = classify(x, y);
  const tileAt = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLD : tiles[y * W + x];
  const solid = new Uint8Array(W * H);
  for (let i = 0; i < tiles.length; i++) solid[i] = tiles[i] === BLD || tiles[i] === WATER ? 1 : 0;
  const setSolid = (x, y) => { if (x >= 0 && y >= 0 && x < W && y < H) solid[y * W + x] = 1; };
  const isSolid = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? true : solid[y * W + x] === 1;

  function hash(x, y, s = 0) {
    let h = (x * 374761393 + y * 668265263 + s * 982451653) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  // Each card class maps to a spot and a sprite. Cards without an entry
  // (a future page) get dropped on one of the spare spots below.
  const PLACES = {
    burrow:  { x: 25, y: 15, sprite: 'manhole', solid: false, label: 30 },
    lapse:   { x: 22, y: 18, sprite: 'camera',  solid: true,  label: 22 },
    bikes:   { x: 11, y: 13, sprite: 'bike',    solid: true,  label: 18 },
    runs:    { x: 36, y: 8,  sprite: 'shoe',    solid: true,  label: 18 },
    rides:   { x: 17, y: 9,  sprite: 'car',     solid: true,  label: 28, extra: [[17, 8]] },
    subways: { x: 16, y: 17, sprite: 'subway',  solid: true,  label: 28 },
    walks:   { x: 26, y: 22, sprite: 'steps',   solid: false, label: 14 },
    beats:   { x: 28, y: 19, sprite: 'heart',   solid: true,  label: 24 },
    reads:   { x: 8,  y: 6,  sprite: 'library', solid: true,  label: 20 },
    camp:    { x: 23, y: 22, sprite: 'tent',    solid: true,  label: 14 },
    dose:    { x: 30, y: 13, sprite: 'wheel',   solid: true,  label: 28 },
    nyc:     { x: 2,  y: 20, sprite: 'kiosk',   solid: true,  label: 28 },
    sub:     { x: 20, y: 28, sprite: 'arcade',  solid: true,  label: 32 },
    mara:    { x: 37, y: 20, sprite: 'arch',    solid: false, label: 42 },
  };
  const SPARE = [[9, 28], [13, 2], [27, 28], [36, 30], [2, 9], [24, 6]];

  const TREES = [[24, 19], [26, 19], [22, 21], [28, 22], [24, 22], [37, 12], [36, 16], [37, 26], [36, 31], [35, 3]];
  const LAMPS = [];
  for (const [ax] of AVES) for (const [sy] of STS) {
    const lx = ax + 2, ly = sy + 2;
    if (lx < PROM_X0) LAMPS.push([lx, ly]);
  }
  LAMPS.push([36, 11], [37, 23], [36, 29]);
  for (const [x, y] of TREES) setSolid(x, y);

  // ------------------------------------------------------- read the cards --
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  const ACCENT = {
    burrow: '--emerald', lapse: '--orange', bikes: '--accent', runs: '--orange', rides: '--purple',
    subways: '--amber', walks: '--green', beats: '--red', reads: '--amber', camp: '--camp',
    dose: '--dose', nyc: '--nyc', sub: '--sub', mara: '--mara',
  };

  function readCards() {
    const items = [];
    let spare = 0;
    document.querySelectorAll('.cards > .card').forEach((card) => {
      const key = [...card.classList].find((c) => c !== 'card') || 'card';
      const onclick = card.getAttribute('onclick') || '';
      const m = onclick.match(/['"]([^'"]+)['"]/);
      const primary = m ? m[1] : (card.getAttribute('href') || '');
      const links = [];
      const seen = new Set();
      if (primary) { links.push({ href: primary, text: 'Open' }); seen.add(primary); }
      card.querySelectorAll('.card-links a').forEach((a) => {
        const href = a.getAttribute('href');
        if (!href || seen.has(href)) return;
        seen.add(href);
        links.push({ href, text: a.textContent.trim() });
      });
      if (!links.length) return;
      let place = PLACES[key];
      if (!place) {
        const s = SPARE[spare++ % SPARE.length];
        place = { x: s[0], y: s[1], sprite: 'sign', solid: true, label: 22 };
      }
      const stats = [...card.querySelectorAll('.card-stat')].map((s) => ({
        val: (s.querySelector('.val') || {}).textContent || '',
        lbl: (s.querySelector('.lbl') || {}).textContent || '',
      }));
      items.push({
        key,
        name: (card.querySelector('h2') || {}).textContent || key,
        brand: (card.querySelector('.brand') || {}).textContent || '',
        desc: (card.querySelector('p') || {}).textContent || '',
        stats, links,
        color: cssVar(ACCENT[key] || '--accent') || '#3b82f6',
        ...place,
        cx: place.x * T + 8,
        by: place.y * T + 16,
      });
      if (place.solid) setSolid(place.x, place.y);
      (place.extra || []).forEach(([x, y]) => setSolid(x, y));
    });
    return items;
  }

  // ---------------------------------------------------------- base layer --
  const BRICKS = ['#5a2e2a', '#4d3328', '#6b3a2e', '#433d45', '#5c4a3a', '#3f3a33', '#62352f'];
  const ROOFS = ['#2a2a31', '#2e2c33', '#26262d', '#2c2f33'];
  const AWNINGS = ['#8f2a2a', '#1f5a3a', '#25386b', '#6b2346', '#7a5a1a', '#2a2a2a'];

  function buildBase() {
    const base = document.createElement('canvas');
    base.width = W * T; base.height = H * T;
    const b = base.getContext('2d');
    const R = (c, x, y, w, h) => { b.fillStyle = c; b.fillRect(x, y, w, h); };

    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const px = x * T, py = y * T, t = tileAt(x, y);
      if (t === ROAD) {
        R('#24242d', px, py, T, T);
        for (let i = 0; i < 5; i++) if (hash(x, y, i) < 0.5) R('#2b2b35', px + ((hash(x, y, i + 9) * 16) | 0), py + ((hash(x, y, i + 19) * 16) | 0), 1, 1);
        const ave = AVES.find((a) => Math.abs(x - a[0]) <= 1);
        const st = STS.find((s) => Math.abs(y - s[0]) <= 1);
        if (ave && !st) {
          if (STS.some((s) => Math.abs(y - s[0]) === 2)) { for (let i = 1; i < T; i += 4) R('#55555f', px + i, py + 3, 2, 10); }
          else if (x === ave[0] && y % 2 === 0) { R('#5f5f69', px, py + 4, 1, 8); R('#5f5f69', px + 15, py + 4, 1, 8); }
        }
        if (st && !ave) {
          if (AVES.some((a) => Math.abs(x - a[0]) === 2)) { for (let i = 1; i < T; i += 4) R('#55555f', px + 3, py + i, 10, 2); }
          else if (y === st[0] && x % 2 === 0) { R('#5f5f69', px + 4, py, 8, 1); R('#5f5f69', px + 4, py + 15, 8, 1); }
        }
      } else if (t === WALK) {
        R('#3a3a45', px, py, T, T);
        R('#33333d', px, py, T, 1); R('#33333d', px, py, 1, T);
        if (hash(x, y, 3) < 0.25) R('#30303a', px + 3 + ((hash(x, y, 4) * 9) | 0), py + 4 + ((hash(x, y, 5) * 8) | 0), 2, 1);
        if (tileAt(x, y - 1) === ROAD) R('#4f4f5c', px, py, T, 1);
        if (tileAt(x, y + 1) === ROAD) R('#4f4f5c', px, py + 15, T, 1);
        if (tileAt(x - 1, y) === ROAD) R('#4f4f5c', px, py, 1, T);
        if (tileAt(x + 1, y) === ROAD) R('#4f4f5c', px + 15, py, 1, T);
      } else if (t === GRASS) {
        R('#1c3324', px, py, T, T);
        for (let i = 0; i < 10; i++) R(hash(x, y, i) < 0.5 ? '#25432f' : '#2c4f37', px + ((hash(x, y, i + 30) * 15) | 0), py + ((hash(x, y, i + 50) * 15) | 0), 1, 2);
      } else if (t === PATH) {
        R('#3d362f', px, py, T, T);
        for (let i = 0; i < 6; i++) R('#4a4239', px + ((hash(x, y, i + 70) * 15) | 0), py + ((hash(x, y, i + 90) * 15) | 0), 1, 1);
      } else if (t === PROM) {
        R('#3b3129', px, py, T, T);
        for (let i = 0; i < T; i += 4) R('#30271f', px, py + i, T, 1);
        if (x === WATER_X0 - 1) { R('#6f7480', px + 14, py, 1, T); R('#8d93a0', px + 13, py + 2, 3, 2); R('#8d93a0', px + 13, py + 10, 3, 2); }
      } else if (t === WATER) {
        R('#0d1d31', px, py, T, T);
        for (let i = 0; i < 3; i++) R('#142a45', px + ((hash(x, y, i + 110) * 13) | 0), py + ((hash(x, y, i + 130) * 15) | 0), 3, 1);
      } else {
        drawBuildingTile(R, x, y, px, py);
      }
    }
    // Water towers, one on roughly a third of the lots.
    for (let y = 1; y < H; y++) for (let x = 0; x < W; x++) {
      if (tileAt(x, y) !== BLD || tileAt(x, y - 1) === BLD) continue;
      // (x, y) is a block's top row; walk its lots.
      if (tileAt(x - 1, y) === BLD) continue;
      let x1 = x; while (x1 + 1 < W && tileAt(x1 + 1, y) === BLD) x1++;
      let y1 = y; while (y1 + 1 < H && tileAt(x, y1 + 1) === BLD) y1++;
      if (y1 - y < 4) continue;
      for (let lx = x; lx + 2 <= x1; lx += 3) {
        if (hash(lx, y, 41) > 0.38) continue;
        const cx = lx * T + 16 + ((hash(lx, y, 42) * 8) | 0) - 4, cy = (y + 1) * T + 10;
        R('rgba(0,0,0,.35)', cx - 5, cy + 4, 13, 3);
        R('#2a2018', cx - 4, cy - 2, 1, 7); R('#2a2018', cx + 4, cy - 2, 1, 7); R('#2a2018', cx, cy - 2, 1, 7);
        R('#6b4a32', cx - 5, cy - 12, 11, 11);
        R('#4c3424', cx - 5, cy - 9, 11, 1); R('#4c3424', cx - 5, cy - 5, 11, 1);
        R('#7d5a3e', cx - 4, cy - 12, 2, 11);
        R('#3a2a20', cx - 5, cy - 13, 11, 1); R('#3a2a20', cx - 4, cy - 14, 9, 1); R('#3a2a20', cx - 2, cy - 15, 5, 1); R('#3a2a20', cx, cy - 16, 1, 1);
      }
    }
    return base;
  }

  function drawBuildingTile(R, x, y, px, py) {
    let x0 = x; while (tileAt(x0 - 1, y) === BLD && x0 > 0) x0--;
    let y0 = y; while (tileAt(x, y0 - 1) === BLD && y0 > 0) y0--;
    const lot = ((x - x0) / 3) | 0;
    const lotX = x0 + lot * 3;
    const brick = BRICKS[(hash(lotX, y0, 7) * BRICKS.length) | 0];
    const k = tileAt(x, y + 1) !== BLD ? 0 : (tileAt(x, y + 2) !== BLD ? 1 : 2);
    const lotEdge = x === lotX && x !== x0;

    if (k === 2) {
      R(ROOFS[(hash(lotX, y0, 8) * ROOFS.length) | 0], px, py, T, T);
      if (tileAt(x, y - 1) !== BLD) R('#3c3c46', px, py, T, 2);
      if (tileAt(x - 1, y) !== BLD) R('#3c3c46', px, py, 2, T);
      if (tileAt(x + 1, y) !== BLD) R('#3c3c46', px + 14, py, 2, T);
      if (lotEdge) R('#1c1c22', px, py, 1, T);
      const f = hash(x, y, 9);
      if (f < 0.1) { R('#666a74', px + 4, py + 5, 6, 5); R('#4b4f57', px + 5, py + 6, 4, 1); R('#4b4f57', px + 5, py + 8, 4, 1); }
      else if (f < 0.16) { R('#34445a', px + 3, py + 3, 8, 6); R('#4f6684', px + 4, py + 4, 3, 2); }
      return;
    }
    R(brick, px, py, T, T);
    for (let r = 1; r < T; r += 3) for (let i = 0; i < 3; i++) {
      if (hash(x, y, r * 7 + i) < 0.6) R('rgba(0,0,0,.18)', px + ((hash(x, y, r * 11 + i) * 14) | 0), py + r, 3, 1);
    }
    if (lotEdge) R('rgba(0,0,0,.35)', px, py, 1, T);
    if (k === 1) {
      R('#1d1d23', px, py, T, 2); R('rgba(255,255,255,.08)', px, py + 2, T, 1);
      for (const wx of [2, 10]) {
        const lit = hash(x * 3 + wx, y, 12) < 0.42;
        R('#121218', px + wx - 1, py + 4, 6, 8);
        R(lit ? (hash(x, wx, 13) < 0.5 ? '#f2c46b' : '#e8a95a') : '#1b1b25', px + wx, py + 5, 4, 6);
        if (lit) R('rgba(255,255,255,.25)', px + wx, py + 5, 1, 2);
        R('rgba(255,255,255,.12)', px + wx - 1, py + 12, 6, 1);
      }
      if (hash(lotX, y0, 14) < 0.45) {
        R('#18181c', px, py + 13, T, 1); R('#18181c', px, py + 3, T, 1);
        for (let i = 1; i < T; i += 3) R('#18181c', px + i, py + 13, 1, 3);
      }
    } else {
      const awn = AWNINGS[(hash(lotX, y0, 15) * AWNINGS.length) | 0];
      const door = (x - lotX) === 1 && hash(lotX, y0, 16) < 0.6;
      R(awn, px, py + 1, T, 4);
      for (let i = 0; i < T; i += 4) R('rgba(255,255,255,.12)', px + i, py + 1, 2, 4);
      R('rgba(0,0,0,.35)', px, py + 5, T, 1);
      if (door) {
        R('#140f0c', px + 5, py + 6, 6, 10);
        R('#f2c46b', px + 6, py + 7, 4, 1);
        R('#2a1f18', px + 6, py + 9, 4, 7);
      } else {
        const lit = hash(x, y, 17) < 0.7;
        R('#121218', px + 2, py + 6, 12, 9);
        R(lit ? '#d9a35a' : '#1b1b25', px + 3, py + 7, 10, 7);
        if (lit) { R('rgba(255,255,255,.2)', px + 3, py + 7, 2, 3); R('rgba(0,0,0,.25)', px + 3, py + 12, 10, 2); }
      }
    }
  }

  // ------------------------------------------------------------- styles ----
  const CSS = `
  #ow-root{position:fixed;inset:0;z-index:1000;background:#0a0a0f;touch-action:none;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;overflow:hidden}
  #ow-root[hidden]{display:none}
  #ow-canvas{position:absolute;inset:0;display:block;image-rendering:pixelated;cursor:pointer}
  .ow-px{font-family:'Press Start 2P',ui-monospace,Menlo,monospace}
  .ow-hud{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:max(14px,env(safe-area-inset-top)) 16px 0;pointer-events:none}
  .ow-title{font-size:11px;color:#e0e0e8;text-shadow:2px 2px 0 #000;letter-spacing:1px}
  .ow-title small{display:block;font-size:7px;color:#8888a0;margin-top:6px;letter-spacing:.5px}
  .ow-btn{pointer-events:auto;font-family:'Press Start 2P',ui-monospace,monospace;font-size:9px;color:#e0e0e8;background:#12121a;border:2px solid #3a3a52;box-shadow:3px 3px 0 #000;padding:9px 11px;cursor:pointer;line-height:1}
  .ow-btn:hover,.ow-btn:focus-visible{border-color:#e0e0e8;outline:none}
  .ow-dialog{position:absolute;left:50%;bottom:22px;transform:translate(-50%,12px);width:min(520px,calc(100% - 32px));background:#0f0f17;border:2px solid var(--c,#3b82f6);box-shadow:4px 4px 0 #000,0 0 32px color-mix(in srgb,var(--c,#3b82f6) 25%,transparent);padding:14px 16px 14px;color:#e0e0e8;opacity:0;pointer-events:none;transition:opacity .15s,transform .15s;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
  .ow-dialog.on{opacity:1;transform:translate(-50%,0);pointer-events:auto}
  .ow-d-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .ow-d-name{font-family:'Press Start 2P',ui-monospace,monospace;font-size:13px;color:var(--c)}
  .ow-d-brand{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#8888a0}
  .ow-d-desc{font-size:13px;line-height:1.45;color:#b8b8c8;margin:8px 0 0}
  .ow-d-stats{display:flex;gap:16px;margin-top:10px;font-size:10px;color:#8888a0;text-transform:uppercase;letter-spacing:.5px;flex-wrap:wrap}
  .ow-d-stats b{color:var(--c);font-size:13px;margin-right:4px;letter-spacing:0;text-transform:none}
  .ow-d-links{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
  .ow-d-links a{font-family:'Press Start 2P',ui-monospace,monospace;font-size:9px;text-decoration:none;color:#e0e0e8;border:2px solid #3a3a52;background:#16161f;padding:8px 10px;box-shadow:2px 2px 0 #000}
  .ow-d-links a.primary{border-color:var(--c);color:#0a0a0f;background:var(--c)}
  .ow-d-links a kbd{font:inherit;opacity:.65;margin-left:6px}
  .ow-hint{position:absolute;left:0;right:0;bottom:8px;text-align:center;font-size:8px;color:#5c5c74;pointer-events:none;transition:opacity .2s}
  .ow-intro{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;background:radial-gradient(ellipse at center,rgba(10,10,15,.55),rgba(10,10,15,.92));pointer-events:none;transition:opacity .6s;text-align:center;padding:24px}
  .ow-intro h1{font-family:'Press Start 2P',ui-monospace,monospace;font-size:clamp(16px,4.2vw,30px);color:#e0e0e8;text-shadow:4px 4px 0 #000,0 0 24px rgba(59,130,246,.45);letter-spacing:2px;font-weight:400}
  .ow-intro p{font-family:'Press Start 2P',ui-monospace,monospace;font-size:9px;color:#8888a0;line-height:2}
  .ow-intro .blink{animation:owblink 1.1s steps(2) infinite;color:#e0e0e8}
  @keyframes owblink{50%{opacity:0}}
  .ow-intro.gone{opacity:0}
  .ow-stick{position:absolute;left:max(22px,env(safe-area-inset-left));bottom:max(26px,env(safe-area-inset-bottom));width:116px;height:116px;border-radius:50%;background:rgba(18,18,26,.55);border:2px solid rgba(224,224,232,.25);box-shadow:3px 3px 0 rgba(0,0,0,.6);touch-action:none}
  .ow-knob{position:absolute;left:50%;top:50%;width:48px;height:48px;margin:-24px 0 0 -24px;border-radius:50%;background:#e0e0e8;box-shadow:3px 3px 0 #000;opacity:.85}
  .ow-a{position:absolute;right:max(26px,env(safe-area-inset-right));bottom:max(46px,env(safe-area-inset-bottom));width:72px;height:72px;border-radius:50%;background:#ef4444;border:2px solid #000;box-shadow:3px 3px 0 #000;font-family:'Press Start 2P',ui-monospace,monospace;font-size:18px;color:#fff;text-shadow:2px 2px 0 #7a1515;touch-action:none}
  .ow-a.dim{background:#3a3a52;text-shadow:none;color:#8888a0}
  .ow-fade{position:absolute;inset:0;background:#0a0a0f;opacity:0;pointer-events:none;transition:opacity .25s}
  .ow-fade.on{opacity:1}
  .ow-touch .ow-hint{display:none}
  .ow-touch .ow-dialog{bottom:auto;top:calc(max(14px,env(safe-area-inset-top)) + 60px)}
  @media (prefers-reduced-motion: reduce){.ow-intro .blink{animation:none}.ow-dialog{transition:none}}
  `;

  // --------------------------------------------------------------- setup ---
  function init() {
    const items = readCards();
    if (!items.length) return;

    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    const touch = window.matchMedia('(pointer: coarse)').matches;
    const root = document.createElement('div');
    root.id = 'ow-root';
    root.className = touch ? 'ow-touch' : '';
    root.setAttribute('role', 'application');
    root.setAttribute('aria-label', 'Walkable map of the site. Use arrow keys to walk and Space to open a page, or press Escape for the classic list.');
    root.innerHTML = `
      <canvas id="ow-canvas"></canvas>
      <div class="ow-hud">
        <div class="ow-title ow-px">WILL HOFNER<small>walk up to anything</small></div>
      </div>
      <div class="ow-dialog" id="ow-dialog" aria-live="polite"></div>
      <div class="ow-hint ow-px" id="ow-hint">ARROWS / WASD walk &middot; SPACE open &middot; CLICK to walk there &middot; ESC classic</div>
      ${touch ? '<div class="ow-stick" id="ow-stick"><div class="ow-knob" id="ow-knob"></div></div><button class="ow-a dim" id="ow-a" type="button" aria-label="Open">A</button>' : ''}
      <div class="ow-intro" id="ow-intro">
        <h1>WILLHOFNER.COM</h1>
        <p>${touch ? 'drag the stick to walk<br>tap A to open' : 'arrow keys to walk<br>space to open'}</p>
        <p class="blink">${touch ? 'TAP TO START' : 'PRESS ANY KEY'}</p>
      </div>
      <div class="ow-fade" id="ow-fade"></div>`;
    document.body.appendChild(root);


    const canvas = root.querySelector('#ow-canvas');
    const ctx = canvas.getContext('2d');
    const dialog = root.querySelector('#ow-dialog');
    const intro = root.querySelector('#ow-intro');
    const fade = root.querySelector('#ow-fade');
    const hint = root.querySelector('#ow-hint');
    const aBtn = root.querySelector('#ow-a');
    const base = buildBase();

    // ------------------------------------------------------------ state ---
    const player = { x: SPAWN.x * T + 8, y: SPAWN.y * T + 12, dir: 'down', walkT: 0, moving: false };
    try {
      const saved = JSON.parse(sessionStorage.getItem('hof:pos') || 'null');
      if (saved && !isSolid(Math.floor(saved.x / T), Math.floor((saved.y - 2) / T))) Object.assign(player, saved);
    } catch (e) { /* storage off */ }

    const keys = new Set();
    const stick = { x: 0, y: 0, id: null };
    let path = null, pathGoal = null;
    let near = null, shownNear = undefined;
    let active = false, started = false, leaving = false;
    let dpr = 1, S = 3, camX = 0, camY = 0, last = 0, time = 0, raf = 0;

    const pigeons = [[9, 17], [14, 13], [23, 24], [33, 28], [36, 18], [6, 7]].map(([x, y], i) => ({
      hx: x * T + 4 + (i * 5) % 8, hy: y * T + 10, x: 0, y: 0, state: 'idle', t: 0, vx: 0, flip: i % 2,
    }));
    pigeons.forEach((p) => { p.x = p.hx; p.y = p.hy; });

    const cars = [
      { axis: 'v', lane: 3 * T + 8, pos: 4 * T, dir: 1, speed: 46, kind: 'cab' },
      { axis: 'v', lane: 33 * T + 8, pos: 25 * T, dir: -1, speed: 40, kind: 'cab' },
      { axis: 'h', lane: 27 * T + 8, pos: 8 * T, dir: 1, speed: 42, kind: 'sedan', color: '#2e4a7a' },
      { axis: 'h', lane: 3 * T + 8, pos: 28 * T, dir: -1, speed: 38, kind: 'sedan', color: '#5a5f6b' },
    ];
    const steam = [];
    let steamT = 0;

    // ---------------------------------------------------------- sizing ----
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 3);
      const vw = window.innerWidth, vh = window.innerHeight;
      canvas.width = Math.round(vw * dpr);
      canvas.height = Math.round(vh * dpr);
      canvas.style.width = vw + 'px';
      canvas.style.height = vh + 'px';
      const across = vw < 700 ? 12 : vw < 1200 ? 18 : 22;
      S = Math.max(1, Math.round(canvas.width / (across * T)));
      ctx.imageSmoothingEnabled = false;
    }

    // ------------------------------------------------------ draw helpers --
    const P = (c, x, y, w, h) => { ctx.fillStyle = c; ctx.fillRect(Math.round(x), Math.round(y), w, h); };
    function disc(cx, cy, r, c) {
      ctx.fillStyle = c;
      for (let dy = -r; dy <= r; dy++) {
        const half = Math.floor(Math.sqrt(r * r - dy * dy) + 0.35);
        ctx.fillRect(Math.round(cx) - half, Math.round(cy) + dy, half * 2 + 1, 1);
      }
    }
    function ring(cx, cy, r, c) {
      ctx.fillStyle = c;
      const seen = new Set();
      for (let a = 0; a < Math.PI * 2; a += 0.12) {
        const x = Math.round(cx + Math.cos(a) * r), y = Math.round(cy + Math.sin(a) * r);
        const k = x + ',' + y;
        if (!seen.has(k)) { seen.add(k); ctx.fillRect(x, y, 1, 1); }
      }
    }
    function line(x0, y0, x1, y1, c) {
      ctx.fillStyle = c;
      x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
      const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
      let err = dx + dy;
      for (;;) {
        ctx.fillRect(x0, y0, 1, 1);
        if (x0 === x1 && y0 === y1) break;
        const e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
      }
    }
    function pixmap(rows, pal, x, y) {
      x = Math.round(x); y = Math.round(y);
      for (let r = 0; r < rows.length; r++) for (let c = 0; c < rows[r].length; c++) {
        const ch = rows[r][c];
        if (ch === '.') continue;
        ctx.fillStyle = pal[ch];
        ctx.fillRect(x + c, y + r, 1, 1);
      }
    }
    function glow(x, y, r, color, alpha) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, hexA(color, alpha));
      g.addColorStop(1, hexA(color, 0));
      ctx.fillStyle = g;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
      ctx.restore();
    }
    function hexA(hex, a) {
      const h = hex.replace('#', '');
      const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
      return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
    }
    const shadow = (cx, by, w) => P('rgba(0,0,0,.35)', cx - w / 2, by - 2, w, 2);

    // ---------------------------------------------------------- sprites ---
    const SHOE = [
      '.......kkkk.....',
      '......kooook....',
      '.....koowwook...',
      '..kkkoowlwlook..',
      '.koooooowwwwook.',
      'kooooooooooooook',
      'kwwwwwwwwwwwwwwk',
      '.kkkkkkkkkkkkkk.',
    ];
    const HEART = [
      '.kkk...kkk.',
      'krrrk.krrrk',
      'krwrrkrrrrk',
      'krwrrrrrrrk',
      'krrrrrrrrrk',
      '.krrrrrrrk.',
      '..krrrrrk..',
      '...krrrk...',
      '....krk....',
      '.....k.....',
    ];
    const TENT = [
      '.......kk.......',
      '......kyyk......',
      '.....kyyyyk.....',
      '....kyyyyyyk....',
      '...kyyyykyyyk...',
      '..kyyyykdkyyyk..',
      '.kyyyykdddkyyyk.',
      'kyyyyykdddkyyyyk',
      'kkkkkkkkkkkkkkkk',
    ];
    const LIB = [
      '..kkkkkkkk..',
      '.kRRRRRRRRk.',
      'kRRRRRRRRRRk',
      'kwwwwwwwwwwk',
      'kwbgybrgbywk',
      'kwbgybrgbywk',
      'kwwwwwwwwwwk',
      'kwrbbgyrgbwk',
      'kwrbbgyrgbwk',
      'kwwwwwwwwwwk',
      'kkkkkkkkkkkk',
      '....kppk....',
      '....kppk....',
      '....kppk....',
      '...kkkkkk...',
    ];

    const SPRITES = {
      manhole(it) {
        const { cx, by } = it;
        P('#141418', cx - 7, by - 7, 14, 5); P('#2a2a31', cx - 6, by - 7, 12, 1);
        for (let i = -5; i <= 5; i += 3) P('#22222a', cx + i, by - 6, 1, 3);
        for (let i = 0; i < 6; i++) P(i % 2 ? '#f2f2f2' : '#ff7a1a', cx + 2, by - 9 - i * 3, 5, 3);
        P('#d9640f', cx + 1, by - 27, 7, 2);
      },
      camera(it) {
        const { cx, by } = it;
        shadow(cx, by, 12);
        line(cx, by - 10, cx - 5, by - 1, '#8a8f99'); line(cx, by - 10, cx + 5, by - 1, '#8a8f99'); line(cx, by - 10, cx, by - 1, '#6a6f79');
        P('#1b1b22', cx - 6, by - 17, 12, 7); P('#2c2c36', cx - 6, by - 17, 12, 1);
        P('#1b1b22', cx - 2, by - 19, 5, 2);
        disc(cx, by - 13, 2, '#3a3a48'); P('#9fc0ff', cx - 1, by - 14, 1, 1);
        if (Math.sin(time * 4) > 0) P('#ff3b3b', cx + 4, by - 16, 1, 1);
      },
      bike(it) {
        const { cx, by } = it;
        shadow(cx, by, 18);
        P('#3a3d46', cx - 12, by - 3, 22, 2);
        P('#55606e', cx - 12, by - 16, 3, 13); P('#7cc4ff', cx - 12, by - 15, 3, 2);
        const blue = '#3b82f6';
        ring(cx - 4, by - 6, 3.4, '#cfd3da'); ring(cx + 6, by - 6, 3.4, '#cfd3da');
        line(cx - 4, by - 6, cx, by - 10, blue); line(cx, by - 10, cx + 5, by - 10, blue);
        line(cx + 5, by - 10, cx + 6, by - 6, blue); line(cx, by - 10, cx + 1, by - 6, blue); line(cx - 4, by - 6, cx + 1, by - 6, blue);
        P('#111', cx - 2, by - 12, 4, 1); P('#cfd3da', cx + 4, by - 12, 3, 1);
        P('#2a2a30', cx + 5, by - 14, 4, 3);
      },
      shoe(it) {
        const { cx, by } = it;
        const f = Math.round(Math.sin(time * 2.5) * 1.5);
        P('rgba(0,0,0,.35)', cx - 6, by - 3, 12, 2);
        pixmap(SHOE, { k: '#1a1a1a', o: '#f97316', w: '#f3f3f3', l: '#9aa' }, cx - 8, by - 15 + f);
      },
      car(it) {
        const { cx, by } = it;
        P('rgba(0,0,0,.35)', cx - 6, by - 21, 14, 21);
        P('#18181f', cx - 6, by - 23, 12, 21); P('#18181f', cx - 5, by - 24, 10, 1); P('#18181f', cx - 5, by - 2, 10, 1);
        P('#2a2a35', cx - 4, by - 18, 8, 10);
        P('#47587a', cx - 4, by - 19, 8, 2); P('#3a4a68', cx - 4, by - 9, 8, 2);
        P('#fff2c0', cx - 5, by - 3, 2, 1); P('#fff2c0', cx + 3, by - 3, 2, 1);
        P('#ff3b3b', cx - 5, by - 23, 2, 1); P('#ff3b3b', cx + 3, by - 23, 2, 1);
        P('#0a0a0e', cx - 7, by - 20, 1, 4); P('#0a0a0e', cx + 6, by - 20, 1, 4); P('#0a0a0e', cx - 7, by - 8, 1, 4); P('#0a0a0e', cx + 6, by - 8, 1, 4);
        const on = 0.6 + 0.4 * Math.sin(time * 3);
        P(hexA('#a855f7', on), cx - 1, by - 14, 3, 2);
      },
      subway(it) {
        const { cx, by } = it;
        P('#1d1d24', cx - 7, by - 15, 14, 14);
        for (let i = 0; i < 6; i++) P(['#4a4a55', '#3e3e48', '#33333c', '#29292f', '#1f1f25', '#16161a'][i], cx - 6, by - 14 + i * 2, 12, 2);
        P('#7a7f8a', cx - 8, by - 17, 1, 16); P('#7a7f8a', cx + 7, by - 17, 1, 16); P('#7a7f8a', cx - 8, by - 17, 16, 1);
        P('#4b4b55', cx - 8, by - 22, 1, 5); P('#4b4b55', cx + 7, by - 22, 1, 5);
        disc(cx - 8, by - 24, 2, '#2ecc71'); disc(cx + 7, by - 24, 2, '#2ecc71');
        P('#bff5d4', cx - 9, by - 25, 1, 1); P('#bff5d4', cx + 6, by - 25, 1, 1);
      },
      steps(it) {
        const { cx, by } = it;
        const n = 7, phase = (time * 2.2) % (n + 3);
        for (let i = 0; i < n; i++) {
          const x = cx - 18 + i * 6, y = by - 4 - Math.round(Math.sin(i * 0.7) * 3) + (i % 2 ? -3 : 0);
          const a = i < phase ? Math.max(0.15, 1 - (phase - i) / 6) : 0.12;
          const c = hexA('#22c55e', a);
          P(c, x, y, 2, 3); P(c, x + (i % 2 ? 0 : 1), y - 2, 1, 1);
        }
      },
      heart(it) {
        const { cx, by } = it;
        const beat = time % 1.1, pulse = beat < 0.12 ? 1.25 : beat < 0.24 ? 1.05 : beat < 0.36 ? 1.18 : 1;
        const f = Math.sin(time * 2) * 1.5;
        P('rgba(0,0,0,.35)', cx - 4, by - 3, 9, 2);
        ctx.save();
        ctx.translate(cx, by - 12 + f);
        ctx.scale(pulse, pulse);
        pixmap(HEART, { k: '#3a0d0d', r: '#ef4444', w: '#ffd0d0' }, -5.5, -5);
        ctx.restore();
      },
      library(it) {
        const { cx, by } = it;
        shadow(cx, by, 10);
        pixmap(LIB, { k: '#16110d', R: '#8a4b22', w: '#e9dcc0', b: '#3b6fd8', g: '#2e9e5b', y: '#eab308', r: '#c0392b', p: '#6b4a2a' }, cx - 6, by - 15);
      },
      tent(it) {
        const { cx, by } = it;
        P('rgba(0,0,0,.35)', cx - 8, by - 2, 16, 2);
        pixmap(TENT, { k: '#24180a', y: '#e2a62b', d: '#2a1a0a' }, cx - 8, by - 10);
        const fx = cx + 11;
        P('#5a3a22', fx - 3, by - 2, 6, 1); P('#4a2e1a', fx - 2, by - 3, 4, 1);
        for (let i = 0; i < 6; i++) {
          const h = hash(i, Math.floor(time * 10), 3);
          P(i < 2 ? '#ffe08a' : i < 4 ? '#ffb347' : '#ff6a1a', fx - 2 + ((h * 4) | 0), by - 4 - ((hash(i, Math.floor(time * 10), 4) * 5) | 0), 1, 1);
        }
      },
      wheel(it) {
        const { cx, by } = it;
        shadow(cx, by, 10);
        line(cx, by - 12, cx - 4, by - 1, '#6a6f79'); line(cx, by - 12, cx + 4, by - 1, '#6a6f79');
        const cols = ['#ffbf1a', '#ef4444', '#3b82f6', '#22c55e', '#a855f7', '#f97316'];
        const a0 = time * 0.9;
        ctx.save();
        for (let i = 0; i < 6; i++) {
          ctx.beginPath(); ctx.moveTo(cx, by - 14);
          ctx.arc(cx, by - 14, 8, a0 + i * Math.PI / 3, a0 + (i + 1) * Math.PI / 3);
          ctx.closePath(); ctx.fillStyle = cols[i]; ctx.fill();
        }
        ctx.restore();
        ring(cx, by - 14, 8.5, '#111');
        disc(cx, by - 14, 1, '#fff');
        P('#ffffff', cx - 1, by - 24, 3, 1); P('#ffffff', cx, by - 23, 1, 1);
      },
      kiosk(it) {
        const { cx, by } = it;
        shadow(cx, by, 16);
        P('#4b4b55', cx - 6, by - 7, 2, 7); P('#4b4b55', cx + 4, by - 7, 2, 7);
        P('#0d1320', cx - 8, by - 24, 16, 17);
        P('#1d3a5f', cx - 7, by - 23, 14, 15);
        P('#c9c1a4', cx - 4, by - 22, 3, 13); P('#c9c1a4', cx - 3, by - 23, 2, 1);
        P('#b8b096', cx, by - 20, 6, 11); P('#b8b096', cx - 6, by - 13, 2, 4);
        P('#ee352e', cx - 3, by - 20, 1, 9); P('#00933c', cx - 2, by - 21, 1, 10); P('#fccc0a', cx, by - 15, 5, 1); P('#0039a6', cx + 2, by - 19, 1, 8);
        if (Math.sin(time * 5) > 0) P('#ff3b3b', cx - 3, by - 16, 2, 2);
      },
      arcade(it) {
        const { cx, by } = it;
        P('rgba(0,0,0,.35)', cx - 7, by - 2, 15, 2);
        P('#2a1e3a', cx - 6, by - 26, 12, 25); P('#1e1530', cx + 4, by - 26, 2, 25);
        P('#ffbf1a', cx - 6, by - 26, 12, 3); P('#b3860f', cx - 6, by - 23, 12, 1);
        P('#0c0c12', cx - 5, by - 21, 10, 8); P('#0b2a1a', cx - 4, by - 20, 8, 6);
        const tx = cx - 7 + Math.floor((time * 6) % 14);
        ctx.save(); ctx.beginPath(); ctx.rect(cx - 4, by - 20, 8, 6); ctx.clip();
        P('#3a5a48', cx - 4, by - 16, 8, 1);
        P('#ffbf1a', tx, by - 18, 4, 2); P('#fff', tx + 3, by - 18, 1, 1);
        ctx.restore();
        P('#3a2a50', cx - 6, by - 12, 12, 3);
        P('#ef4444', cx - 1, by - 11, 1, 1); P('#22c55e', cx + 2, by - 11, 1, 1); P('#ddd', cx - 4, by - 12, 1, 2);
        P('#1e1530', cx - 6, by - 4, 12, 1);
      },
      arch(it) {
        const { cx, by } = it;
        P('rgba(0,0,0,.3)', cx - 24, by - 2, 4, 2); P('rgba(0,0,0,.3)', cx + 20, by - 2, 4, 2);
        P('#2a2a32', cx - 24, by - 34, 4, 33); P('#2a2a32', cx + 20, by - 34, 4, 33);
        P('#3e3e48', cx - 24, by - 34, 1, 33); P('#3e3e48', cx + 20, by - 34, 1, 33);
        P('#ff8436', cx - 24, by - 40, 48, 9);
        for (let i = 0; i < 24; i++) { P(i % 2 ? '#111' : '#f5f5f5', cx - 24 + i * 2, by - 31, 2, 1); P(i % 2 ? '#f5f5f5' : '#111', cx - 24 + i * 2, by - 30, 2, 1); }
        P('#c9601f', cx - 24, by - 40, 48, 1);
        // Finish line on the ground.
        for (let i = 0; i < 20; i++) P(i % 2 ? '#e8e8e8' : '#222', cx - 20 + i * 2, by - 3, 2, 2);
      },
      sign(it) {
        const { cx, by } = it;
        shadow(cx, by, 8);
        P('#4b4b55', cx, by - 14, 1, 14);
        P(it.color, cx - 6, by - 20, 13, 7); P('#0a0a0f', cx - 5, by - 18, 11, 1); P('#0a0a0f', cx - 5, by - 16, 8, 1);
      },
    };

    function drawTree(x, y) {
      const cx = x * T + 8, by = y * T + 15;
      P('rgba(0,0,0,.35)', cx - 6, by - 2, 13, 3);
      P('#4a3424', cx - 1, by - 7, 3, 7);
      disc(cx, by - 13, 7, '#1d4429'); disc(cx - 1, by - 15, 5, '#285a35'); disc(cx - 3, by - 16, 2, '#357044');
    }
    function drawLamp(x, y) {
      const cx = x * T + 13, by = y * T + 13;
      P('#3b3b44', cx - 1, by, 3, 1);
      P('#55555f', cx, by - 20, 1, 20);
      P('#55555f', cx - 3, by - 21, 4, 1);
      P('#ffe9b0', cx - 4, by - 20, 3, 2);
    }
    function drawPlayer() {
      const fx = Math.round(player.x), fy = Math.round(player.y);
      const x = fx - 6, y = fy - 17;
      const step = player.moving ? (Math.floor(player.walkT * 8) % 2 ? 1 : -1) : 0;
      const SK = '#f0c39b', HR = '#4a2f1f', SH = '#3b82f6', SD = '#2c63c0', PN = '#2a3550', SO = '#ececec', EY = '#1b1b1b';
      P('rgba(0,0,0,.4)', x + 2, y + 16, 8, 2);
      // Legs and shoes.
      const lL = step < 0 ? 1 : 0, rL = step > 0 ? 1 : 0;
      P(PN, x + 3, y + 12, 3, 4 - lL); P(SO, x + 3, y + 16 - lL, 3, 1);
      P(PN, x + 6, y + 12, 3, 4 - rL); P(SO, x + 6, y + 16 - rL, 3, 1);
      // Torso and arms.
      P(SH, x + 2, y + 7, 8, 5); P(SD, x + 2, y + 11, 8, 1);
      const aL = step > 0 ? -1 : 0, aR = step < 0 ? -1 : 0;
      P(SD, x + 1, y + 7 + aL, 1, 4); P(SK, x + 1, y + 11 + aL, 1, 1);
      P(SD, x + 10, y + 7 + aR, 1, 4); P(SK, x + 10, y + 11 + aR, 1, 1);
      // Head.
      P(SK, x + 2, y, 8, 7);
      if (player.dir === 'up') {
        P(HR, x + 2, y, 8, 6); P(HR, x + 1, y + 1, 1, 4); P(HR, x + 10, y + 1, 1, 4);
      } else {
        P(HR, x + 2, y, 8, 2); P(HR, x + 1, y + 1, 10, 1);
        if (player.dir === 'down') {
          P(HR, x + 2, y + 2, 1, 2); P(HR, x + 9, y + 2, 1, 2); P(HR, x + 3, y + 2, 2, 1);
          P(EY, x + 4, y + 4, 1, 1); P(EY, x + 7, y + 4, 1, 1);
          P('#d99a7a', x + 5, y + 6, 2, 1);
        } else {
          const left = player.dir === 'left';
          P(HR, left ? x + 6 : x + 2, y + 2, 4, 3);
          P(EY, left ? x + 3 : x + 8, y + 4, 1, 1);
          P(SK, left ? x + 1 : x + 10, y + 4, 1, 1);
        }
      }
    }
    function drawPigeon(p) {
      const x = Math.round(p.x), y = Math.round(p.y);
      const flying = p.state === 'fly';
      const f = p.flip ? -1 : 1;
      if (!flying) P('rgba(0,0,0,.3)', x - 2, y, 5, 1);
      const peck = !flying && Math.sin(time * 3 + p.hx) > 0.85 ? 1 : 0;
      P('#8a8f9e', x - 2, y - 3, 5, 3);
      P('#6b7080', x + (f > 0 ? 2 : -3), y - 4 + peck, 2, 2);
      P('#e0a030', x + (f > 0 ? 4 : -4), y - 3 + peck, 1, 1);
      P('#2f8a7a', x + (f > 0 ? 1 : -2), y - 2, 1, 1);
      if (flying) {
        const up = Math.floor(time * 18) % 2;
        P('#a3a8b6', x - 3, y - (up ? 6 : 3), 3, 2); P('#a3a8b6', x + 1, y - (up ? 6 : 3), 3, 2);
      } else P('#c48a3a', x - 1, y, 1, 1);
    }
    function drawCar(c) {
      const x = Math.round(c.axis === 'v' ? c.lane : c.pos), y = Math.round(c.axis === 'v' ? c.pos : c.lane);
      if (c.axis === 'v') {
        const body = '#f2c230';
        P('rgba(0,0,0,.35)', x - 5, y - 8, 12, 19);
        P(body, x - 6, y - 10, 12, 20); P(body, x - 5, y - 11, 10, 1); P(body, x - 5, y + 10, 10, 1);
        P('#d9a91c', x - 4, y - 5, 8, 10);
        P('#3a4a68', x - 4, y + (c.dir > 0 ? 4 : -7), 8, 2); P('#2e3a52', x - 4, y + (c.dir > 0 ? -7 : 4), 8, 2);
        P('#fff6c0', x - 2, y - 1, 4, 2);
        const fy = c.dir > 0 ? y + 10 : y - 11, ry = c.dir > 0 ? y - 11 : y + 10;
        P('#fff2c0', x - 5, fy, 2, 1); P('#fff2c0', x + 3, fy, 2, 1);
        P('#ff3b3b', x - 5, ry, 2, 1); P('#ff3b3b', x + 3, ry, 2, 1);
        glow(x, c.dir > 0 ? y + 18 : y - 19, 12, '#fff2c0', 0.18);
      } else {
        P('rgba(0,0,0,.35)', x - 9, y - 4, 20, 11);
        P(c.color, x - 10, y - 6, 20, 12); P(c.color, x - 11, y - 5, 1, 10); P(c.color, x + 10, y - 5, 1, 10);
        P('rgba(0,0,0,.25)', x - 5, y - 4, 10, 8);
        P('#3a4a68', x + (c.dir > 0 ? 4 : -6), y - 4, 2, 8); P('#2e3a52', x + (c.dir > 0 ? -6 : 4), y - 4, 2, 8);
        const fx = c.dir > 0 ? x + 10 : x - 11, rx = c.dir > 0 ? x - 11 : x + 10;
        P('#fff2c0', fx, y - 5, 1, 2); P('#fff2c0', fx, y + 3, 1, 2);
        P('#ff3b3b', rx, y - 5, 1, 2); P('#ff3b3b', rx, y + 3, 1, 2);
        glow(c.dir > 0 ? x + 18 : x - 18, y, 12, '#fff2c0', 0.18);
      }
    }

    // ---------------------------------------------------------- update ----
    const SPEED = 74; // art px per second
    function blockedBox(x, y) {
      const pts = [[x - 4, y - 4], [x + 3.9, y - 4], [x - 4, y - 0.1], [x + 3.9, y - 0.1]];
      return pts.some(([px, py]) => isSolid(Math.floor(px / T), Math.floor(py / T)));
    }

    function update(dt) {
      let mx = 0, my = 0;
      if (keys.has('left')) mx -= 1;
      if (keys.has('right')) mx += 1;
      if (keys.has('up')) my -= 1;
      if (keys.has('down')) my += 1;
      if (mx || my) { path = null; pathGoal = null; }
      else if (stick.x || stick.y) { mx = stick.x; my = stick.y; path = null; pathGoal = null; }
      else if (path && path.length) {
        const [tx, ty] = path[0];
        const dx = tx - player.x, dy = ty - player.y, d = Math.hypot(dx, dy);
        if (d < 2) { path.shift(); if (!path.length) path = null; }
        else { mx = dx / d; my = dy / d; }
      }
      const len = Math.hypot(mx, my);
      if (len > 1) { mx /= len; my /= len; }
      player.moving = len > 0.15;
      if (player.moving) {
        if (Math.abs(mx) > Math.abs(my)) player.dir = mx < 0 ? 'left' : 'right';
        else player.dir = my < 0 ? 'up' : 'down';
        player.walkT += dt * Math.min(1, len);
        const nx = player.x + mx * SPEED * dt;
        if (!blockedBox(nx, player.y)) player.x = nx;
        const ny = player.y + my * SPEED * dt;
        if (!blockedBox(player.x, ny)) player.y = ny;
      }

      // Which item are we standing next to?
      let best = null, bestD = 26;
      for (const it of items) {
        const iy = it.sprite === 'arch' ? it.by - 4 : it.y * T + 10;
        const d = Math.hypot(player.x - it.cx, player.y - iy);
        if (d < bestD) { best = it; bestD = d; }
      }
      near = best;
      if (near !== shownNear) { renderDialog(); shownNear = near; }

      // Pigeons scatter when you get close.
      for (const p of pigeons) {
        if (p.state === 'idle') {
          if (Math.hypot(player.x - p.x, player.y - p.y) < 26) {
            p.state = 'fly'; p.t = 0; p.vx = (p.x >= player.x ? 1 : -1) * (50 + Math.random() * 30); p.flip = p.vx < 0 ? 1 : 0;
          }
        } else if (p.state === 'fly') {
          p.t += dt; p.x += p.vx * dt; p.y -= (70 - p.t * 10) * dt;
          if (p.t > 2.2) { p.state = 'gone'; p.t = 0; }
        } else {
          p.t += dt;
          if (p.t > 7 && Math.hypot(player.x - p.hx, player.y - p.hy) > 90) { p.state = 'idle'; p.x = p.hx; p.y = p.hy; }
        }
      }

      // Traffic; cars wait if you're standing in front of them.
      for (const c of cars) {
        const ahead = c.axis === 'v'
          ? Math.abs(player.x - c.lane) < 10 && (player.y - c.pos) * c.dir > 4 && (player.y - c.pos) * c.dir < 30
          : Math.abs(player.y - 2 - c.lane) < 9 && (player.x - c.pos) * c.dir > 6 && (player.x - c.pos) * c.dir < 32;
        if (!ahead) c.pos += c.dir * c.speed * dt;
        const max = c.axis === 'v' ? H * T + 24 : (PROM_X0) * T + 20;
        if (c.dir > 0 && c.pos > max) c.pos = -24;
        if (c.dir < 0 && c.pos < -24) c.pos = max;
      }

      // Steam from the manhole.
      const mh = items.find((i) => i.sprite === 'manhole');
      if (mh) {
        steamT += dt;
        while (steamT > 0.09) {
          steamT -= 0.09;
          steam.push({ x: mh.cx + 4.5 + (Math.random() - 0.5) * 3, y: mh.by - 28, vx: (Math.random() - 0.3) * 6, vy: -14 - Math.random() * 8, life: 0, max: 1.6 + Math.random() * 0.8 });
        }
        for (const s of steam) { s.life += dt; s.x += s.vx * dt; s.y += s.vy * dt; s.vy *= 0.985; }
        while (steam.length && steam[0].life > steam[0].max) steam.shift();
      }
    }

    // ------------------------------------------------------------ render --
    function render() {
      const viewW = canvas.width / S, viewH = canvas.height / S;
      const mapW = W * T, mapH = H * T;
      let tx = player.x - viewW / 2, ty = player.y - 8 - viewH / 2;
      tx = viewW >= mapW ? (mapW - viewW) / 2 : Math.max(0, Math.min(mapW - viewW, tx));
      ty = viewH >= mapH ? (mapH - viewH) / 2 : Math.max(0, Math.min(mapH - viewH, ty));
      camX = tx; camY = ty;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = '#0a0a0f';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(S, 0, 0, S, -Math.round(camX * S), -Math.round(camY * S));
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(base, 0, 0);

      // Water shimmer.
      const x0 = Math.max(WATER_X0, Math.floor(camX / T)), x1 = Math.min(W - 1, Math.ceil((camX + viewW) / T));
      const y0 = Math.max(0, Math.floor(camY / T)), y1 = Math.min(H - 1, Math.ceil((camY + viewH) / T));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
        const h = hash(x, y, 200), a = 0.12 + 0.12 * Math.sin(time * 1.5 + h * 10);
        P(`rgba(120,170,230,${a.toFixed(3)})`, x * T + ((h * 16 + time * 5) % 14), y * T + ((hash(x, y, 201) * 14) | 0), 3, 1);
      }

      // Ground glow under every item.
      for (const it of items) {
        const pulse = 0.18 + 0.08 * Math.sin(time * 2 + it.x);
        glow(it.cx, it.by - 5, it === near ? 30 : 22, it.color, it === near ? 0.42 : pulse);
      }

      // Everything that stands up gets drawn back to front.
      const list = [];
      for (const [x, y] of TREES) list.push({ y: y * T + 15, draw: () => drawTree(x, y) });
      for (const [x, y] of LAMPS) list.push({ y: y * T + 13, draw: () => drawLamp(x, y) });
      for (const it of items) list.push({ y: it.by - 1, draw: () => SPRITES[it.sprite](it) });
      for (const p of pigeons) if (p.state !== 'gone') list.push({ y: p.state === 'fly' ? 9999 : p.y, draw: () => drawPigeon(p) });
      for (const c of cars) list.push({ y: (c.axis === 'v' ? c.pos + 10 : c.lane + 6), draw: () => drawCar(c) });
      list.push({ y: player.y, draw: drawPlayer });
      list.sort((a, b) => a.y - b.y);
      for (const e of list) e.draw();

      for (const s of steam) {
        const k = s.life / s.max;
        disc(s.x, s.y, 1 + Math.floor(k * 4), `rgba(225,232,236,${(0.35 * (1 - k)).toFixed(3)})`);
      }
      for (const [x, y] of LAMPS) glow(x * T + 11.5, y * T - 6, 34, '#ffd27a', 0.16);

      // Tap-to-walk target marker.
      if (pathGoal && path) {
        const b = Math.sin(time * 8) > 0 ? 1 : 0;
        P('rgba(255,255,255,.7)', pathGoal[0] - 3, pathGoal[1] - 1 - b, 7, 1);
        P('rgba(255,255,255,.7)', pathGoal[0] - 1, pathGoal[1] - 3 - b, 3, 5);
      }

      // Screen-space text: street names and item labels.
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const sx = (wx) => (wx - camX) * S, sy = (wy) => (wy - camY) * S;
      const small = Math.round(8 * dpr);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = `${small}px "Press Start 2P", ui-monospace, monospace`;
      ctx.fillStyle = 'rgba(160,160,185,.28)';
      for (const [ax, name] of AVES) for (const wy of [10 * T, 21 * T, 31 * T]) {
        ctx.save(); ctx.translate(sx(ax * T + 8), sy(wy)); ctx.rotate(-Math.PI / 2); ctx.fillText(name, 0, 0); ctx.restore();
      }
      for (const [syy, name] of STS) for (const wx of [11 * T, 25 * T]) ctx.fillText(name, sx(wx), sy(syy * T + 8));
      ctx.fillText('TOMPKINS SQ', sx(25 * T + 8), sy(PARK.y0 * T - 1));
      ctx.save(); ctx.translate(sx(42.5 * T), sy(17 * T)); ctx.rotate(-Math.PI / 2); ctx.fillStyle = 'rgba(120,160,210,.3)'; ctx.fillText('EAST RIVER', 0, 0); ctx.restore();

      const big = Math.round(10 * dpr);
      for (const it of items) {
        const lx = sx(it.cx), ly = sy(it.by - it.label - 4 + Math.sin(time * 2 + it.x) * 1.2);
        if (lx < -200 || lx > canvas.width + 200 || ly < -50 || ly > canvas.height + 50) continue;
        const isNear = it === near;
        ctx.font = `${isNear ? big : small}px "Press Start 2P", ui-monospace, monospace`;
        const label = it.name.toUpperCase();
        const w = ctx.measureText(label).width + small * 1.2, h = (isNear ? big : small) * 1.9;
        ctx.fillStyle = isNear ? 'rgba(10,10,15,.92)' : 'rgba(10,10,15,.6)';
        ctx.fillRect(Math.round(lx - w / 2), Math.round(ly - h / 2), Math.round(w), Math.round(h));
        if (isNear) { ctx.strokeStyle = it.color; ctx.lineWidth = Math.max(2, dpr * 1.5); ctx.strokeRect(Math.round(lx - w / 2), Math.round(ly - h / 2), Math.round(w), Math.round(h)); }
        ctx.fillStyle = isNear ? it.color : 'rgba(224,224,232,.85)';
        ctx.fillText(label, Math.round(lx), Math.round(ly + 1));
      }
      if (items.find((i) => i.sprite === 'arch')) {
        const a = items.find((i) => i.sprite === 'arch');
        ctx.font = `${Math.max(6, Math.round(S * 1.6))}px "Press Start 2P", ui-monospace, monospace`;
        ctx.fillStyle = '#1a0d05';
        ctx.fillText('FINISH', sx(a.cx), sy(a.by - 35.5));
      }

      // Soft vignette for the night-time feel.
      const g = ctx.createRadialGradient(canvas.width / 2, canvas.height / 2, Math.min(canvas.width, canvas.height) * 0.35, canvas.width / 2, canvas.height / 2, Math.max(canvas.width, canvas.height) * 0.75);
      g.addColorStop(0, 'rgba(5,5,10,0)'); g.addColorStop(1, 'rgba(5,5,10,.55)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    function frame(now) {
      raf = 0;
      if (!active) return;
      const dt = Math.min(0.05, (now - (last || now)) / 1000);
      last = now; time += dt;
      if (started) update(dt);
      else { near = null; }
      render();
      raf = requestAnimationFrame(frame);
    }

    // ----------------------------------------------------------- dialog ---
    function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
    function renderDialog() {
      if (aBtn) aBtn.classList.toggle('dim', !near);
      if (hint) hint.style.opacity = near ? 0 : 1;
      if (!near) { dialog.classList.remove('on'); return; }
      const it = near;
      dialog.style.setProperty('--c', it.color);
      dialog.innerHTML = `
        <div class="ow-d-top"><span class="ow-d-name">${esc(it.name)}</span><span class="ow-d-brand">${esc(it.brand)}</span></div>
        <p class="ow-d-desc">${esc(it.desc)}</p>
        ${it.stats.length ? `<div class="ow-d-stats">${it.stats.map((s) => `<span><b>${esc(s.val)}</b>${esc(s.lbl)}</span>`).join('')}</div>` : ''}
        <div class="ow-d-links">${it.links.map((l, i) => `<a href="${esc(l.href)}" data-i="${i}" class="${i === 0 ? 'primary' : ''}">${esc(l.text)}${touch ? '' : `<kbd>${i === 0 ? 'SPACE' : i + 1}</kbd>`}</a>`).join('')}</div>`;
      dialog.classList.add('on');
    }
    dialog.addEventListener('click', (e) => {
      const a = e.target.closest('a');
      if (!a) return;
      e.preventDefault();
      go(a.getAttribute('href'));
    });

    function go(href) {
      if (leaving || !href) return;
      leaving = true;
      savePos();
      fade.classList.add('on');
      setTimeout(() => { window.location.href = href; }, 230);
    }
    function savePos() {
      try { sessionStorage.setItem('hof:pos', JSON.stringify({ x: player.x, y: player.y, dir: player.dir })); } catch (e) { /* ignore */ }
    }
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) { leaving = false; fade.classList.remove('on'); keys.clear(); }
    });
    window.addEventListener('pagehide', savePos);

    function interact(index = 0) {
      if (!started) { start(); return; }
      if (!near) return;
      const link = near.links[index];
      if (link) go(link.href);
    }

    // ---------------------------------------------------- tap to walk -----
    function findPath(goals) {
      const sx0 = Math.floor(player.x / T), sy0 = Math.floor((player.y - 2) / T);
      const goal = new Set(goals.map(([x, y]) => y * W + x));
      if (goal.has(sy0 * W + sx0)) return [];
      const prev = new Int32Array(W * H).fill(-1);
      const q = [sy0 * W + sx0]; prev[q[0]] = q[0];
      let found = -1;
      for (let qi = 0; qi < q.length && found < 0; qi++) {
        const cur = q[qi], cx = cur % W, cy = (cur / W) | 0;
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = cx + dx, ny = cy + dy;
          if (isSolid(nx, ny)) continue;
          const n = ny * W + nx;
          if (prev[n] !== -1) continue;
          prev[n] = cur; q.push(n);
          if (goal.has(n)) { found = n; break; }
        }
      }
      if (found < 0) return null;
      const out = [];
      for (let n = found; n !== prev[n]; n = prev[n]) out.push([(n % W) * T + 8, ((n / W) | 0) * T + 12]);
      return out.reverse();
    }
    function tapAt(clientX, clientY) {
      if (!started) { start(); return; }
      const wx = clientX * dpr / S + camX, wy = clientY * dpr / S + camY;
      // Did they tap an item (sprite or label)?
      let hit = null, hd = 22;
      for (const it of items) {
        const d = Math.min(Math.hypot(wx - it.cx, wy - (it.by - 8)), Math.hypot(wx - it.cx, wy - (it.by - it.label - 4)) * 1.4);
        if (d < hd) { hit = it; hd = d; }
      }
      if (hit && hit === near) { renderDialog(); return; }
      let goals;
      if (hit) {
        goals = [];
        if (!hit.solid) goals.push([hit.x, hit.y]);
        for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0], [1, 1], [-1, 1]]) {
          const gx = hit.x + dx, gy = hit.y + dy;
          if (!isSolid(gx, gy)) goals.push([gx, gy]);
        }
      } else {
        const gx = Math.floor(wx / T), gy = Math.floor(wy / T);
        if (isSolid(gx, gy)) return;
        goals = [[gx, gy]];
      }
      const p = findPath(goals);
      if (p) {
        path = p.length ? p : null;
        const g = p.length ? p[p.length - 1] : null;
        pathGoal = g ? [g[0], g[1]] : null;
      }
    }

    // ------------------------------------------------------------ input ---
    const KEYMAP = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down', KeyA: 'left', KeyD: 'right', KeyW: 'up', KeyS: 'down' };
    window.addEventListener('keydown', (e) => {
      if (!active || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.code === 'Escape') { e.preventDefault(); toClassic(); return; }
      if (!started) {
        if (e.code === 'Tab') return;
        e.preventDefault(); start(); return;
      }
      const dir = KEYMAP[e.code];
      if (dir) { e.preventDefault(); keys.add(dir); return; }
      if (e.code === 'Space' || e.code === 'Enter') {
        if (document.activeElement && document.activeElement.closest && document.activeElement.closest('#ow-dialog, .ow-hud') && e.code === 'Enter') return;
        e.preventDefault(); interact(0); return;
      }
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= 9) { e.preventDefault(); interact(n === 1 ? 0 : n - 1); }
    });
    window.addEventListener('keyup', (e) => { const dir = KEYMAP[e.code]; if (dir) keys.delete(dir); });
    window.addEventListener('blur', () => keys.clear());

    let down = null;
    canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
    canvas.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      down = null;
      if (moved < 12) tapAt(e.clientX, e.clientY);
    });
    intro.style.pointerEvents = 'auto';
    intro.addEventListener('pointerup', () => start());

    const stickEl = root.querySelector('#ow-stick'), knob = root.querySelector('#ow-knob');
    if (stickEl) {
      const move = (e) => {
        const r = stickEl.getBoundingClientRect();
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2, rad = r.width / 2 - 8;
        let dx = (e.clientX - cx) / rad, dy = (e.clientY - cy) / rad;
        const l = Math.hypot(dx, dy);
        if (l > 1) { dx /= l; dy /= l; }
        knob.style.transform = `translate(${dx * rad}px, ${dy * rad}px)`;
        const dead = 0.22;
        if (Math.hypot(dx, dy) < dead) { stick.x = 0; stick.y = 0; }
        else { stick.x = dx; stick.y = dy; }
      };
      const end = (e) => {
        if (e.pointerId !== stick.id) return;
        stick.id = null; stick.x = 0; stick.y = 0; knob.style.transform = '';
      };
      stickEl.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        if (!started) start();
        stick.id = e.pointerId; stickEl.setPointerCapture(e.pointerId); move(e);
      });
      stickEl.addEventListener('pointermove', (e) => { if (e.pointerId === stick.id) move(e); });
      stickEl.addEventListener('pointerup', end);
      stickEl.addEventListener('pointercancel', end);
    }
    if (aBtn) aBtn.addEventListener('pointerdown', (e) => { e.preventDefault(); interact(0); });


    // ------------------------------------------------------------- modes --
    function start() {
      if (started) return;
      started = true;
      intro.classList.add('gone');
      intro.style.pointerEvents = 'none';
      try { sessionStorage.setItem('hof:intro', '1'); } catch (e) { /* ignore */ }
      setTimeout(() => intro.remove(), 700);
    }
    // views.js owns which skin is showing; these are its show/hide hooks.
    function toClassic() {
      if (window.HofView) window.HofView.set('classic', true); else showClassic();
    }
    function showWorld() {
      active = true;
      root.hidden = false;
      document.documentElement.style.overflow = 'hidden';
      resize();
      last = 0;
      if (!raf) raf = requestAnimationFrame(frame);
      canvas.focus && canvas.focus();
    }
    function showClassic() {
      active = false; keys.clear();
      root.hidden = true;
      document.documentElement.style.overflow = '';
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
    }

    window.addEventListener('resize', () => { if (active) resize(); });

    let seenIntro = false;
    try { seenIntro = sessionStorage.getItem('hof:intro') === '1'; } catch (e) { /* ignore */ }
    if (seenIntro) { started = true; intro.remove(); }

    root.hidden = true;
    if (window.HofView) window.HofView.register('world', { label: 'Walk', show: showWorld, hide: showClassic });
    else showWorld();

    // Redraw labels once the pixel font arrives.
    if (document.fonts && document.fonts.load) document.fonts.load('10px "Press Start 2P"').catch(() => {});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
