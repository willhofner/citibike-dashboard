/*
 * Glass: a sleek, light, motion-heavy skin for the landing page, modeled on
 * lead.bank. Frosted 3D glass slabs float behind the page (three.js) and
 * re-stack themselves as you scroll; type is huge and gradient; everything
 * reveals on scroll.
 *
 * Like overworld.js, the landing page's .card elements are the source of
 * truth: names, blurbs, stats and links are read from them at load, so
 * editing a card updates this view too. GROUPS decides which section a card
 * lands in (unknown cards go to "Everything else"), STATS picks the big
 * numbers, and the build log reads the same cards.
 *
 * views.js decides when this skin is showing (Walk / Glass / Classic).
 * three.js and Lenis load from jsDelivr the first time the skin is shown;
 * without WebGL the background falls back to drifting CSS gradients.
 */
(() => {
  'use strict';
  if (window.__hofGlass) return;
  window.__hofGlass = true;

  const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
  const LENIS_URL = 'https://cdn.jsdelivr.net/npm/lenis@1.3.24/dist/lenis.min.js';
  const FONT_URL = 'https://fonts.googleapis.com/css2?family=Geist:wght@300..700&family=Geist+Mono:wght@400;500&display=swap';

  const GROUPS = [
    { id: 'maps', name: 'Maps', line: 'Everywhere I’ve been, drawn from the raw data.', keys: ['burrow', 'lapse', 'bikes', 'runs', 'rides', 'subways'], wide: ['burrow', 'lapse'] },
    { id: 'body', name: 'Body', line: 'Half a million heartbeats, thirty million steps and one marathon.', keys: ['walks', 'beats', 'mara'], wide: ['mara'] },
    { id: 'games', name: 'Games', line: 'Just how well do you know New York?', keys: ['nyc', 'sub', 'dose'], wide: ['dose'] },
    { id: 'life', name: 'Everything else', line: 'Books on the shelf and gear on the floor.', keys: ['reads', 'camp'], wide: [] },
  ];
  // [card class, stat index, label]
  const STATS = [
    ['lapse', 0, 'Trips on one map'],
    ['bikes', 0, 'CitiBike rides'],
    ['runs', 1, 'Run, in miles'],
    ['walks', 0, 'Steps counted'],
    ['rides', 2, 'Cities by Uber'],
    ['reads', 0, 'Books finished'],
  ];
  const LOG = [
    ['bikes', 0, 'CitiBike rides'], ['runs', 0, 'Strava runs'], ['rides', 0, 'Uber rides'],
    ['subways', 0, 'subway trips'], ['beats', 0, 'heart-rate readings'], ['reads', 0, 'books'],
  ];
  const ACCENT = {
    burrow: '--emerald', lapse: '--orange', bikes: '--accent', runs: '--orange', rides: '--purple',
    subways: '--amber', walks: '--green', beats: '--red', reads: '--amber', camp: '--camp',
    dose: '--dose', nyc: '--nyc', sub: '--sub', mara: '--mara',
  };

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  const lerp = (a, b, t) => a + (b - a) * t;

  // ------------------------------------------------------------- cards ----
  function readCards() {
    const items = [];
    document.querySelectorAll('.cards > .card').forEach((card) => {
      const key = [...card.classList].find((c) => c !== 'card') || 'card';
      const m = (card.getAttribute('onclick') || '').match(/['"]([^'"]+)['"]/);
      const primary = m ? m[1] : '';
      const links = [];
      const seen = new Set();
      card.querySelectorAll('.card-links a').forEach((a) => {
        const href = a.getAttribute('href');
        if (!href || seen.has(href)) return;
        seen.add(href);
        links.push({ href, text: a.textContent.trim() });
      });
      if (!primary && !links.length) return;
      const badge = card.querySelector('.badge');
      items.push({
        key,
        href: primary || links[0].href,
        icon: (card.querySelector('.icon') || {}).textContent || '',
        badge: badge ? badge.textContent.trim() : '',
        name: (card.querySelector('h2') || {}).textContent || key,
        brand: (card.querySelector('.brand') || {}).textContent || '',
        desc: (card.querySelector('p') || {}).textContent || '',
        stats: [...card.querySelectorAll('.card-stat')].map((s) => ({
          val: ((s.querySelector('.val') || {}).textContent || '').trim(),
          lbl: ((s.querySelector('.lbl') || {}).textContent || '').trim(),
        })),
        links,
        color: cssVar(ACCENT[key] || '--accent') || '#3b82f6',
      });
    });
    return items;
  }

  // "663 mi" -> {pre:'', num:663, dec:0, post:' mi'}; "$7.7K" -> {pre:'$', num:7.7, dec:1, post:'K'}
  function parseVal(v) {
    const m = String(v).match(/^([^\d]*)([\d,]*\.?\d+)(.*)$/);
    if (!m) return null;
    const raw = m[2].replace(/,/g, '');
    const dec = raw.includes('.') ? raw.split('.')[1].length : 0;
    return { pre: m[1], num: parseFloat(raw), dec, post: m[3], comma: m[2].includes(',') };
  }
  const fmtVal = (p, n) => {
    let s = n.toFixed(p.dec);
    if (p.comma) s = Number(s).toLocaleString('en-US', { minimumFractionDigits: p.dec, maximumFractionDigits: p.dec });
    return p.pre + s + p.post;
  };

  // --------------------------------------------------------------- css ----
  const CSS = `
  html.gl-on{background:#eaeaee}
  html.gl-on body{display:block;min-height:0;background:#eaeaee;color:#2b2c39;padding:0;overflow-x:hidden}
  html.gl-on body > .container{display:none}
  html.gl-on.lenis,html.gl-on.lenis body{height:auto}
  html.gl-on.lenis.lenis-smooth{scroll-behavior:auto!important}
  #gl-root[hidden]{display:none}
  #gl-root{--ink:#2b2c39;--mid:#606171;--soft:#9a9bab;--line:rgba(43,44,57,.12);--b1:#0040ff;--b2:#5e00ff;--lead:#2000a8;
    position:relative;font-family:'Geist',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased;font-feature-settings:'ss01'}
  #gl-root *{box-sizing:border-box}
  #gl-root a{color:inherit;text-decoration:none}
  .gl-bg{position:fixed;inset:0;z-index:0;pointer-events:none;background:linear-gradient(105deg,#f4f4f8 0%,#dfe2f1 38%,#aab3dc 72%,#8a96cf 100%)}
  .gl-bg canvas{position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity 1.2s ease}
  .gl-bg canvas.on{opacity:1}
  .gl-blob{position:absolute;border-radius:50%;filter:blur(60px);opacity:.75;animation:glDrift 18s ease-in-out infinite alternate}
  .gl-blob.a{width:46vmax;height:46vmax;right:-10vmax;top:-8vmax;background:radial-gradient(circle,#ffffff 0%,#c3c9ef 45%,transparent 70%)}
  .gl-blob.b{width:38vmax;height:38vmax;right:12vmax;bottom:-12vmax;background:radial-gradient(circle,#7f6bff 0%,rgba(64,0,255,.25) 45%,transparent 70%);animation-duration:23s}
  .gl-bg.webgl .gl-blob{display:none}
  @keyframes glDrift{to{transform:translate(-6vmax,5vmax) scale(1.12)}}
  .gl-main{position:relative;z-index:1}
  .gl-wrap{width:min(1200px,100% - 48px);margin:0 auto}
  .gl-grad{background:linear-gradient(95deg,var(--b1) 0%,var(--b2) 100%);-webkit-background-clip:text;background-clip:text;color:transparent}

  /* nav */
  .gl-nav{position:fixed;z-index:20;top:max(10px,env(safe-area-inset-top));left:max(10px,env(safe-area-inset-left));right:max(10px,env(safe-area-inset-right));height:58px;display:flex;align-items:center;gap:40px;padding:0 260px 0 22px;border-radius:999px;border:1px solid transparent;transition:background .5s,border-color .5s,box-shadow .5s,backdrop-filter .5s,transform .5s cubic-bezier(.2,.8,.2,1)}
  .gl-nav.solid{background:rgba(255,255,255,.55);border-color:rgba(255,255,255,.75);box-shadow:0 12px 40px rgba(32,0,168,.08);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4)}
  .gl-nav.tuck{transform:translateY(-120%)}
  .gl-logo{display:flex;align-items:center;gap:10px;font-weight:500;font-size:20px;letter-spacing:-.02em;color:var(--lead)!important;white-space:nowrap}
  .gl-logo svg{width:26px;height:26px}
  .gl-links{position:relative;display:flex;gap:6px}
  .gl-links a{position:relative;font-size:15px;color:var(--ink);padding:8px 12px;border-radius:999px;transition:color .3s}
  .gl-links a:hover{color:var(--b1)}
  .gl-links a.on{color:var(--b1)}
  .gl-ul{position:absolute;bottom:2px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--b1),var(--b2));transition:left .45s cubic-bezier(.2,.8,.2,1),width .45s cubic-bezier(.2,.8,.2,1),opacity .3s;opacity:0}

  /* hero */
  .gl-hero{min-height:100vh;min-height:100svh;display:flex;flex-direction:column;justify-content:center;padding:120px 0 80px}
  .gl-eyebrow{font-size:15px;color:var(--mid);margin-bottom:22px;display:flex;align-items:center;gap:10px}
  .gl-eyebrow i{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 0 rgba(34,197,94,.6);animation:glPing 2.2s infinite}
  @keyframes glPing{70%{box-shadow:0 0 0 10px rgba(34,197,94,0)}100%{box-shadow:0 0 0 0 rgba(34,197,94,0)}}
  .gl-h1{font-size:clamp(3.2rem,9.2vw,7.25rem);line-height:.98;letter-spacing:-.05em;font-weight:400;margin:0}
  .gl-h1 .ln{display:block;overflow:hidden;padding-bottom:.12em;margin-bottom:-.12em}
  .gl-h1 .w{display:inline-block;transform:translateY(105%);opacity:0;filter:blur(8px)}
  #gl-root.play .gl-h1 .w{animation:glRise 1.1s cubic-bezier(.16,1,.3,1) forwards;animation-delay:calc(var(--i) * 90ms + 150ms)}
  @keyframes glRise{to{transform:none;opacity:1;filter:none}}
  .gl-sub{max-width:620px;font-size:clamp(1.1rem,1.6vw,1.5rem);line-height:1.35;color:var(--ink);margin:34px 0 0;font-weight:300;opacity:0;transform:translateY(20px)}
  .gl-ctas{display:flex;gap:12px;flex-wrap:wrap;margin-top:36px;opacity:0;transform:translateY(20px)}
  #gl-root.play .gl-sub{animation:glUp 1s cubic-bezier(.16,1,.3,1) .7s forwards}
  #gl-root.play .gl-ctas{animation:glUp 1s cubic-bezier(.16,1,.3,1) .85s forwards}
  @keyframes glUp{to{opacity:1;transform:none}}
  .gl-btn{display:inline-flex;align-items:center;gap:10px;height:52px;padding:0 26px;border-radius:999px;font-size:16px;font-weight:500;transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s,background .35s}
  .gl-btn.pri{color:#fff!important;background:linear-gradient(100deg,var(--b1),var(--b2));box-shadow:0 10px 30px rgba(64,0,255,.35),inset 0 1px 0 rgba(255,255,255,.35)}
  .gl-btn.pri:hover{transform:translateY(-2px);box-shadow:0 16px 40px rgba(64,0,255,.45),inset 0 1px 0 rgba(255,255,255,.35)}
  .gl-btn.sec{background:rgba(255,255,255,.6);border:1px solid rgba(255,255,255,.85);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
  .gl-btn.sec:hover{background:#fff;transform:translateY(-2px)}
  .gl-btn span{transition:transform .35s cubic-bezier(.2,.8,.2,1)}
  .gl-btn:hover span{transform:translateX(4px)}
  .gl-scroll{margin-top:70px;display:flex;align-items:center;gap:12px;font-size:13px;color:var(--mid);opacity:0}
  #gl-root.play .gl-scroll{animation:glUp 1s ease 1.3s forwards}
  .gl-scroll b{position:relative;width:1px;height:44px;background:rgba(43,44,57,.15);overflow:hidden}
  .gl-scroll b:after{content:'';position:absolute;left:0;top:-50%;width:1px;height:50%;background:var(--b1);animation:glDrop 1.8s cubic-bezier(.6,0,.2,1) infinite}
  @keyframes glDrop{to{top:110%}}

  /* marquee */
  .gl-marq{position:relative;overflow:hidden;padding:22px 0;border-top:1px solid rgba(255,255,255,.7);border-bottom:1px solid rgba(255,255,255,.7);background:rgba(255,255,255,.28);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);mask-image:linear-gradient(90deg,transparent,#000 10%,#000 90%,transparent);-webkit-mask-image:linear-gradient(90deg,transparent,#000 10%,#000 90%,transparent)}
  .gl-marq-t{display:flex;width:max-content;animation:glMarq 48s linear infinite}
  .gl-marq:hover .gl-marq-t{animation-play-state:paused}
  .gl-marq-t a{display:flex;align-items:center;gap:12px;font-size:clamp(1.3rem,2.4vw,2rem);letter-spacing:-.03em;padding:0 34px;white-space:nowrap;color:var(--ink);transition:color .3s}
  .gl-marq-t a:hover{color:var(--b1)}
  .gl-marq-t a i{width:10px;height:10px;border-radius:50%;background:var(--c);box-shadow:0 0 14px var(--c)}
  @keyframes glMarq{to{transform:translateX(-50%)}}

  /* scroll-lit paragraph */
  .gl-story{height:220vh;position:relative}
  .gl-story-in{position:sticky;top:0;height:100vh;display:flex;align-items:center}
  .gl-story p{font-size:clamp(1.9rem,4.4vw,3.6rem);line-height:1.12;letter-spacing:-.035em;margin:0;max-width:1050px}
  .gl-story .sw{color:rgba(43,44,57,.16);transition:color .25s}
  .gl-story .sw.lit{color:var(--ink)}
  .gl-story .sw.lit.g{color:var(--b1)}
  .gl-story .sw.lit.g2{color:var(--b2)}

  /* sections */
  .gl-sec{padding:clamp(5rem,12vh,9rem) 0}
  .gl-kicker{font-family:'Geist Mono',ui-monospace,monospace;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--mid);display:flex;align-items:center;gap:12px}
  .gl-kicker:after{content:'';flex:0 0 60px;height:1px;background:var(--line)}
  .gl-h2{font-size:clamp(2.6rem,6vw,4.5rem);line-height:1;letter-spacing:-.045em;font-weight:400;margin:18px 0 14px}
  .gl-lede{font-size:clamp(1.05rem,1.4vw,1.25rem);color:var(--mid);max-width:560px;margin:0;line-height:1.45;font-weight:300}

  /* numbers */
  .gl-nums{display:grid;grid-template-columns:repeat(3,1fr);margin-top:56px;border-top:1px solid var(--line)}
  .gl-num{padding:34px 28px 38px 0;border-bottom:1px solid var(--line);position:relative}
  .gl-num:not(:nth-child(3n+1)){padding-left:28px;border-left:1px solid var(--line)}
  .gl-num .v{font-size:clamp(3rem,6.4vw,5.5rem);letter-spacing:-.05em;line-height:1;font-variant-numeric:tabular-nums;font-weight:400}
  .gl-num .l{margin-top:12px;font-size:15px;color:var(--mid);display:flex;align-items:center;gap:8px}
  .gl-num .l i{width:7px;height:7px;border-radius:50%;background:var(--c)}

  /* project cards */
  .gl-group{padding:clamp(4rem,10vh,7rem) 0 0}
  .gl-group-h{display:flex;justify-content:space-between;align-items:flex-end;gap:30px;flex-wrap:wrap;margin-bottom:40px}
  .gl-count{font-family:'Geist Mono',ui-monospace,monospace;font-size:13px;color:var(--mid)}
  .gl-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
  .gl-card{--c:#3b82f6;--mx:50%;--my:50%;position:relative;display:block;padding:7px;border-radius:44px;background:rgba(255,255,255,.28);border:1px solid rgba(255,255,255,.75);box-shadow:0 20px 40px rgba(64,72,140,.10);transition:transform .6s cubic-bezier(.2,.8,.2,1),box-shadow .6s;transform-style:preserve-3d;cursor:pointer}
  .gl-card.wide{grid-column:span 2}
  .gl-card:hover{box-shadow:0 30px 70px rgba(64,72,140,.20)}
  .gl-card-in{position:relative;height:100%;overflow:hidden;border-radius:37px;padding:34px 34px 30px;background:rgba(255,255,255,.62);backdrop-filter:blur(22px) saturate(1.3);-webkit-backdrop-filter:blur(22px) saturate(1.3);display:flex;flex-direction:column}
  .gl-card-in:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .5s;background:radial-gradient(420px circle at var(--mx) var(--my),color-mix(in srgb,var(--c) 22%,transparent),transparent 60%)}
  .gl-card:hover .gl-card-in:before{opacity:1}
  .gl-card-top{position:relative;display:flex;min-height:46px;padding-right:0;align-items:center;gap:10px;font-size:14px;color:var(--mid)}
  .gl-card-top i{width:9px;height:9px;border-radius:50%;background:var(--c);box-shadow:0 0 12px color-mix(in srgb,var(--c) 70%,transparent)}
  .gl-badge{margin-left:auto;margin-right:54px;font-family:'Geist Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:5px 10px;border-radius:999px;background:rgba(43,44,57,.06);color:var(--ink)}
  .gl-badge.live{background:rgba(34,197,94,.14);color:#15803d}
  .gl-arrow{position:absolute;top:26px;right:26px;width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:#fff;box-shadow:0 6px 16px rgba(43,44,57,.08);transition:transform .5s cubic-bezier(.2,.8,.2,1),background .4s,color .4s;z-index:2}
  .gl-arrow svg{width:16px;height:16px;transition:transform .5s cubic-bezier(.2,.8,.2,1)}
  .gl-card:hover .gl-arrow{background:linear-gradient(135deg,var(--b1),var(--b2));color:#fff}
  .gl-card:hover .gl-arrow svg{transform:rotate(-45deg)}
  .gl-card h3{position:relative;font-size:clamp(1.9rem,3vw,2.6rem);letter-spacing:-.04em;line-height:1.02;font-weight:400;margin:22px 0 10px}
  .gl-card.wide h3{font-size:clamp(2.2rem,4.4vw,3.6rem)}
  .gl-card p{position:relative;margin:0;color:var(--mid);font-size:16px;line-height:1.45;max-width:640px;font-weight:300}
  .gl-stats{position:relative;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:auto;padding-top:30px}
  .gl-stats div{border-top:1px solid var(--line);padding-top:14px}
  .gl-stats b{display:block;font-weight:400;font-size:clamp(1.3rem,2vw,1.75rem);letter-spacing:-.03em;font-variant-numeric:tabular-nums}
  .gl-stats span{font-size:12.5px;color:var(--mid)}
  .gl-pills{position:relative;display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}
  .gl-pills a{font-size:14px;padding:9px 15px;border-radius:999px;background:rgba(255,255,255,.75);border:1px solid rgba(43,44,57,.08);transition:background .3s,color .3s,border-color .3s}
  .gl-pills a:hover{background:var(--ink);color:#fff;border-color:var(--ink)}

  /* build log */
  .gl-build{display:grid;grid-template-columns:1fr 1.15fr;gap:40px;align-items:center}
  .gl-jobs{margin-top:28px;display:flex;flex-direction:column;gap:10px}
  .gl-job{display:flex;align-items:center;gap:12px;font-size:15px;padding:14px 18px;border-radius:18px;background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.8)}
  .gl-job i{width:8px;height:8px;border-radius:50%;background:#22c55e;animation:glPing 2.2s infinite}
  .gl-job small{margin-left:auto;color:var(--mid);font-size:13px;text-align:right}
  .gl-term{position:relative;border-radius:44px;padding:7px;background:rgba(23,23,31,.35);border:1px solid rgba(255,255,255,.35);box-shadow:0 40px 80px rgba(23,23,31,.25)}
  .gl-term-in{border-radius:37px;background:#17171f;color:#d6d7e4;padding:26px 30px 34px;font-family:'Geist Mono',ui-monospace,monospace;font-size:14px;line-height:1.75;min-height:360px;overflow:hidden}
  .gl-term-dots{display:flex;gap:7px;margin-bottom:20px}
  .gl-term-dots i{width:11px;height:11px;border-radius:50%;background:#2b2c39}
  .gl-term .p{color:#6e8bff}.gl-term .ok{color:#4ade80}.gl-term .dim{color:#606171}.gl-term .n{color:#fff}
  .gl-term .cur{display:inline-block;width:8px;height:1.1em;vertical-align:-3px;background:#6e8bff;animation:glBlink 1s steps(2) infinite}
  @keyframes glBlink{50%{opacity:0}}
  .gl-term-line{white-space:pre-wrap;word-break:break-word}

  /* footer */
  .gl-foot{padding:clamp(5rem,14vh,10rem) 0 40px;overflow:hidden}
  .gl-mark{font-size:clamp(3.4rem,13.5vw,12.5rem);letter-spacing:-.06em;line-height:.9;font-weight:400;white-space:nowrap;margin:0}
  .gl-foot-cols{display:grid;grid-template-columns:repeat(4,1fr);gap:30px;margin-top:70px;padding-top:34px;border-top:1px solid var(--line)}
  .gl-foot-cols h4{margin:0 0 14px;font-size:13px;font-weight:500;color:var(--mid);font-family:'Geist Mono',ui-monospace,monospace;text-transform:uppercase;letter-spacing:.04em}
  .gl-foot-cols a{display:block;font-size:15px;padding:5px 0;color:var(--ink);transition:color .25s,transform .35s cubic-bezier(.2,.8,.2,1)}
  .gl-foot-cols a:hover{color:var(--b1);transform:translateX(4px)}
  .gl-fine{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-top:60px;font-size:13px;color:var(--mid)}

  /* reveal */
  .gl-rv{opacity:0;transform:translateY(42px);filter:blur(6px);transition:opacity 1.1s cubic-bezier(.16,1,.3,1),transform 1.1s cubic-bezier(.16,1,.3,1),filter 1.1s cubic-bezier(.16,1,.3,1);transition-delay:var(--d,0ms)}
  .gl-rv.in{opacity:1;transform:none;filter:none}
  .gl-card.gl-rv.in{transition:opacity 1.1s cubic-bezier(.16,1,.3,1) var(--d,0ms),filter 1.1s cubic-bezier(.16,1,.3,1) var(--d,0ms),transform .6s cubic-bezier(.2,.8,.2,1),box-shadow .6s}

  @media (max-width:900px){
    .gl-nav{gap:0;padding:0 230px 0 18px}
    .gl-links{display:none}
    .gl-nums{grid-template-columns:repeat(2,1fr)}
    .gl-num:not(:nth-child(3n+1)){padding-left:0;border-left:0}
    .gl-num:nth-child(2n){padding-left:20px;border-left:1px solid var(--line)}
    .gl-grid{grid-template-columns:1fr}
    .gl-card.wide{grid-column:auto}
    .gl-build{grid-template-columns:1fr}
    .gl-foot-cols{grid-template-columns:repeat(2,1fr)}
  }
  @media (max-width:560px){
    .gl-wrap{width:calc(100% - 32px)}
    .gl-nav{height:52px;padding:0 0 0 16px;right:auto;border-color:transparent!important;background:none!important;box-shadow:none!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
    .gl-logo span{display:none}
    .gl-logo{width:44px;height:44px;justify-content:center;border-radius:50%;background:rgba(255,255,255,.6);border:1px solid rgba(255,255,255,.85);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:0 8px 24px rgba(32,0,168,.1)}
    .gl-logo svg{width:24px;height:24px}
    .gl-hero{padding-top:110px}
    .gl-card{border-radius:34px;padding:5px}
    .gl-card-in{border-radius:29px;padding:26px 22px 22px}
    .gl-arrow{top:18px;right:18px;width:40px;height:40px}
    .gl-num{padding:26px 14px 28px 0}
    .gl-num:nth-child(2n){padding-left:14px}
    .gl-term-in{font-size:12px;padding:22px 20px 26px;border-radius:29px}
    .gl-term{border-radius:34px;padding:5px}
    .gl-story{height:180vh}
  }
  @media (prefers-reduced-motion: reduce){
    #gl-root .gl-h1 .w,#gl-root .gl-sub,#gl-root .gl-ctas,#gl-root .gl-scroll{animation:none!important;opacity:1;transform:none;filter:none}
    .gl-rv{opacity:1;transform:none;filter:none;transition:none}
    .gl-marq-t,.gl-blob,.gl-scroll b:after,.gl-eyebrow i,.gl-job i{animation:none}
    .gl-story{height:auto}.gl-story-in{position:static;height:auto;padding:6rem 0}
    .gl-story .sw{color:var(--ink)}
  }
  `;

  const ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8h12M9 3l5 5-5 5"/></svg>';
  const LOGO = '<svg viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="glg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#47baff"/><stop offset=".55" stop-color="#0040ff"/><stop offset="1" stop-color="#2000a8"/></linearGradient></defs><path d="M3 9.5 13.5 4l2 6.2L7 15z" fill="#47baff"/><path d="M15.5 4H29l-4.6 10H20l-4 14-3-11.5z" fill="url(#glg)"/></svg>';

  // ----------------------------------------------------------- markup ----
  function cardHTML(it, wide) {
    const stats = it.stats.slice(0, 3).map((s) => `<div><b>${esc(s.val)}</b><span>${esc(s.lbl)}</span></div>`).join('');
    const pills = it.links.map((l) => `<a href="${esc(l.href)}">${esc(l.text)}</a>`).join('');
    const badge = it.badge ? `<span class="gl-badge${/live/i.test(it.badge) ? ' live' : ''}">${esc(it.badge)}</span>` : '';
    return `<article class="gl-card gl-rv${wide ? ' wide' : ''}" style="--c:${esc(it.color)}" data-href="${esc(it.href)}">
      <div class="gl-card-in">
        <span class="gl-arrow">${ARROW}</span>
        <div class="gl-card-top"><i></i>${esc(it.brand)}${badge}</div>
        <h3>${esc(it.name)}</h3>
        <p>${esc(it.desc)}</p>
        <div class="gl-stats">${stats}</div>
        <div class="gl-pills">${pills}</div>
      </div>
    </article>`;
  }

  function words(text, cls) {
    return text.split(/\s+/).map((w) => `<span class="sw${cls ? ' ' + cls : ''}">${esc(w)}</span>`).join(' ');
  }

  function build(items) {
    const by = Object.fromEntries(items.map((i) => [i.key, i]));
    const used = new Set();
    const groups = GROUPS.map((g) => ({ ...g, items: g.keys.filter((k) => by[k]).map((k) => { used.add(k); return by[k]; }) }));
    const extra = items.filter((i) => !used.has(i.key));
    groups[groups.length - 1].items.push(...extra);
    const live = groups.filter((g) => g.items.length);

    const marq = items.map((i) => `<a href="${esc(i.href)}" style="--c:${esc(i.color)}"><i></i>${esc(i.name)}</a>`).join('');
    const nums = STATS.filter(([k, idx]) => by[k] && by[k].stats[idx]).map(([k, idx, label], n) => {
      const v = by[k].stats[idx].val;
      return `<div class="gl-num gl-rv" style="--d:${(n % 3) * 90}ms;--c:${esc(by[k].color)}"><div class="v" data-count="${esc(v)}">${esc(v)}</div><div class="l"><i></i>${esc(label)}</div></div>`;
    }).join('');

    let card = 0;
    const sections = live.map((g, gi) => `
      <section class="gl-group" id="gl-${g.id}">
        <div class="gl-wrap">
          <div class="gl-group-h gl-rv">
            <div>
              <div class="gl-kicker">0${gi + 1} &mdash; ${esc(g.name)}</div>
              <h2 class="gl-h2"><span class="gl-grad">${esc(g.name)}</span></h2>
              <p class="gl-lede">${esc(g.line)}</p>
            </div>
            <div class="gl-count">${g.items.length} ${g.items.length === 1 ? 'page' : 'pages'}</div>
          </div>
          <div class="gl-grid">${g.items.map((it) => { const h = cardHTML(it, g.wide.includes(it.key)); card++; return h; }).join('')}</div>
        </div>
      </section>`).join('');

    const jobs = [...document.querySelectorAll('.jobs .job-row')].map((r) => {
      const name = (r.querySelector('.job-name') || {}).textContent || '';
      const det = (r.querySelector('.job-detail') || {}).textContent || '';
      return `<div class="gl-job"><i></i>${esc(name)}<small>${esc(det)}</small></div>`;
    }).join('');

    const nav = live.map((g) => `<a href="#gl-${g.id}" data-sec="gl-${g.id}">${esc(g.name === 'Everything else' ? 'More' : g.name)}</a>`).join('')
      + '<a href="#gl-numbers" data-sec="gl-numbers">Numbers</a>';

    const foot = live.map((g) => `<div><h4>${esc(g.name)}</h4>${g.items.map((i) => `<a href="${esc(i.href)}">${esc(i.name)}</a>`).join('')}</div>`).join('');

    let wi = 0;
    const hw = (t, g) => t.split(' ').map((w) => `<span class="w${g ? ' gl-grad' : ''}" style="--i:${wi++}">${esc(w)}</span>`).join(' ');

    return `
      <div class="gl-bg" id="gl-bg"><div class="gl-blob a"></div><div class="gl-blob b"></div></div>
      <header class="gl-nav" id="gl-nav">
        <a class="gl-logo" href="#gl-top">${LOGO}<span>Will Hofner</span></a>
        <nav class="gl-links" id="gl-links">${nav}<span class="gl-ul" id="gl-ul"></span></nav>
      </header>
      <main class="gl-main" id="gl-top">
        <section class="gl-hero">
          <div class="gl-wrap">
            <div class="gl-eyebrow"><i></i>Welcome to willhofner.com</div>
            <h1 class="gl-h1"><span class="ln">${hw('My New York,', true)}</span><span class="ln">${hw('in motion.')}</span></h1>
            <p class="gl-sub">Every CitiBike ride, run, Uber, subway trip, heartbeat and book I could get my hands on, pulled out of the apps and turned into maps you can play with.</p>
            <div class="gl-ctas">
              <a class="gl-btn pri" href="#gl-maps">Explore the maps <span>&rarr;</span></a>
              <a class="gl-btn sec" href="#gl-games">Play a game <span>&rarr;</span></a>
            </div>
            <div class="gl-scroll"><b></b>Scroll</div>
          </div>
        </section>
        <div class="gl-marq" aria-hidden="true"><div class="gl-marq-t">${marq}${marq}</div></div>
        <section class="gl-story" id="gl-story">
          <div class="gl-story-in"><div class="gl-wrap">
            <p>${words('The bike rides come from the CitiBike app, the runs from Strava, the Ubers from a privacy export and the heartbeats from my watch.')} ${words('Every one of them lands', 'g')} ${words('on the same map of the city.', 'g2')}</p>
          </div></div>
        </section>
        <section class="gl-sec" id="gl-numbers">
          <div class="gl-wrap">
            <div class="gl-rv"><div class="gl-kicker">By the numbers</div>
            <h2 class="gl-h2">Ten years of getting around, <span class="gl-grad">counted.</span></h2></div>
            <div class="gl-nums">${nums}</div>
          </div>
        </section>
        ${sections}
        <section class="gl-sec">
          <div class="gl-wrap gl-build">
            <div class="gl-rv">
              <div class="gl-kicker">Under the hood</div>
              <h2 class="gl-h2">Built from <span class="gl-grad">raw exports.</span></h2>
              <p class="gl-lede">No backend and no build step. Python scripts turn each app's export into JSON, OSRM fills in the routes, and the rest is hand-written HTML. Some of it even updates itself.</p>
              <div class="gl-jobs">${jobs}</div>
            </div>
            <div class="gl-term gl-rv" style="--d:120ms"><div class="gl-term-in" id="gl-term"><div class="gl-term-dots"><i></i><i></i><i></i></div><div id="gl-term-body"></div></div></div>
          </div>
        </section>
        <footer class="gl-foot">
          <div class="gl-wrap">
            <h2 class="gl-mark gl-rv"><span class="gl-grad">willhofner</span>.com</h2>
            <div class="gl-foot-cols gl-rv">${foot}</div>
            <div class="gl-fine"><span>&copy; ${new Date().getFullYear()} Will Hofner</span><span>Made in the East Village</span></div>
          </div>
        </footer>
      </main>`;
  }

  // ------------------------------------------------------- the glass ----
  // Five frosted slabs and a ring, refracting a soft blue glow. The scroll
  // position drives a few poses (stacked hero, fanned out, drifting behind
  // the cards, collapsed into one puck at the footer); the frame loop eases
  // toward whichever pose the page is in.
  async function startGlass(host, getScroll) {
    const T = await import(THREE_URL);
    const canvas = document.createElement('canvas');
    let renderer;
    try {
      renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    } catch (e) { return null; }
    const mobile = window.matchMedia('(max-width: 700px)').matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 1.75));
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.22;
    renderer.outputColorSpace = T.SRGBColorSpace;
    host.appendChild(canvas);
    host.classList.add('webgl');

    const scene = new T.Scene();
    // Page gradient as the background, so the glass refracts what's behind it.
    const bgc = document.createElement('canvas');
    bgc.width = 512; bgc.height = 512;
    const g = bgc.getContext('2d');
    const lin = g.createLinearGradient(0, 0, 512, 380);
    lin.addColorStop(0, '#f5f5f9'); lin.addColorStop(0.4, '#dde1f1'); lin.addColorStop(0.75, '#a9b2dc'); lin.addColorStop(1, '#8592cd');
    g.fillStyle = lin; g.fillRect(0, 0, 512, 512);
    const bgTex = new T.CanvasTexture(bgc);
    bgTex.colorSpace = T.SRGBColorSpace;
    scene.background = bgTex;

    // A soft studio for reflections: grey room, bright strip lights, one blue panel.
    const pmrem = new T.PMREMGenerator(renderer);
    const room = new T.Scene();
    room.add(new T.Mesh(new T.BoxGeometry(30, 30, 30), new T.MeshBasicMaterial({ color: 0xc4c8e2, side: T.BackSide })));
    const panel = (w, h, col, x, y, z, ry, rx) => {
      const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: col, side: T.DoubleSide }));
      m.position.set(x, y, z); m.rotation.set(rx || 0, ry || 0, 0); room.add(m);
    };
    panel(20, 3, new T.Color(4, 4, 4.2), 0, 14, 0, 0, Math.PI / 2);
    panel(3, 16, new T.Color(3, 3, 3.3), -14, 2, 0, Math.PI / 2);
    panel(3, 12, new T.Color(2.2, 2.3, 3), 14, 4, -4, -Math.PI / 2);
    panel(10, 6, new T.Color(0.4, 0.6, 3.2), 4, -2, -14);
    panel(8, 2, new T.Color(3.5, 3.5, 3.5), -3, 5, 14, Math.PI);
    scene.environment = pmrem.fromScene(room, 0.035).texture;

    const camera = new T.PerspectiveCamera(30, 1, 0.1, 100);
    camera.position.set(0, 0, 16);

    const world = new T.Group();
    scene.add(world);

    // Glow behind the glass: transmission picks it up and tints the slabs.
    const gc = document.createElement('canvas');
    gc.width = gc.height = 256;
    const gg = gc.getContext('2d');
    const rad = gg.createRadialGradient(128, 128, 0, 128, 128, 128);
    rad.addColorStop(0, 'rgba(90,70,255,1)'); rad.addColorStop(0.35, 'rgba(0,64,255,.55)'); rad.addColorStop(1, 'rgba(0,64,255,0)');
    gg.fillStyle = rad; gg.fillRect(0, 0, 256, 256);
    const glowTex = new T.CanvasTexture(gc);
    glowTex.colorSpace = T.SRGBColorSpace;
    const glow = new T.Mesh(new T.PlaneGeometry(9, 9), new T.MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false, opacity: 0.9 }));
    glow.position.z = -3.5;
    world.add(glow);

    const shape = new T.Shape();
    const S = 1.35, R = 0.78;
    shape.moveTo(-S + R, -S);
    shape.lineTo(S - R, -S); shape.quadraticCurveTo(S, -S, S, -S + R);
    shape.lineTo(S, S - R); shape.quadraticCurveTo(S, S, S - R, S);
    shape.lineTo(-S + R, S); shape.quadraticCurveTo(-S, S, -S, S - R);
    shape.lineTo(-S, -S + R); shape.quadraticCurveTo(-S, -S, -S + R, -S);
    const slabGeo = new T.ExtrudeGeometry(shape, { depth: 0.16, bevelEnabled: true, bevelThickness: 0.11, bevelSize: 0.11, bevelSegments: 10, curveSegments: 36 });
    slabGeo.center();
    slabGeo.rotateX(-Math.PI / 2);

    const glass = new T.MeshPhysicalMaterial({
      color: 0xffffff, metalness: 0, roughness: 0.22, transmission: 1, thickness: 0.9, ior: 1.42,
      clearcoat: 1, clearcoatRoughness: 0.06, envMapIntensity: 1.25, specularIntensity: 1,
      attenuationColor: new T.Color('#dfe2ff'), attenuationDistance: 3.5, iridescence: 0.25, iridescenceIOR: 1.3,
    });

    const stack = new T.Group();
    world.add(stack);
    const slabs = [];
    for (let i = 0; i < 5; i++) {
      const m = new T.Mesh(slabGeo, glass);
      stack.add(m);
      slabs.push(m);
    }
    const ringGeo = new T.TorusGeometry(2.7, 0.2, 32, 160);
    const ring = new T.Mesh(ringGeo, glass);
    ring.scale.set(1, 1, 0.55);
    world.add(ring);

    // Poses: [x, y, scale, gap, tiltX, spinY, ring]
    // x and y are fractions of the visible half-width / half-height.
    const POSES = mobile ? [
      [0.42, 0.74, 0.46, 0.3, 0.62, 0.6, 1],
      [0.35, 0.05, 0.7, 0.85, 0.35, 1.6, 0.4],
      [0.0, 0.0, 0.85, 0.5, 0.95, 2.6, 0.8],
      [0.0, -0.2, 0.8, 0.02, 1.15, 3.6, 1],
    ] : [
      [0.5, 0.0, 1.0, 0.36, 0.62, 0.6, 1],
      [0.6, 0.02, 1.0, 0.9, 0.32, 1.7, 0.35],
      [0.62, -0.05, 1.12, 0.55, 0.92, 2.7, 0.75],
      [0.0, 0.05, 0.95, 0.02, 1.2, 3.8, 1],
    ];
    const cur = POSES[0].slice();

    let vw = 1, vh = 1, halfW = 1, halfH = 1;
    function resize() {
      vw = window.innerWidth; vh = window.innerHeight;
      renderer.setSize(vw, vh, false);
      camera.aspect = vw / vh;
      camera.updateProjectionMatrix();
      halfH = Math.tan((camera.fov * Math.PI) / 360) * camera.position.z;
      halfW = halfH * camera.aspect;
    }
    resize();

    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    const onMove = (e) => { mouse.tx = (e.clientX / vw - 0.5) * 2; mouse.ty = (e.clientY / vh - 0.5) * 2; };
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('resize', resize);

    function target() {
      const p = getScroll();
      const t = [];
      // p: 0 hero, ~.15 story, ~.55 cards, 1 footer
      const a = smooth(0.02, 0.16, p), b = smooth(0.22, 0.4, p), c = smooth(0.86, 0.99, p);
      for (let i = 0; i < 7; i++) t[i] = lerp(lerp(lerp(POSES[0][i], POSES[1][i], a), POSES[2][i], b), POSES[3][i], c);
      t[5] += p * 2.2;
      return t;
    }

    let running = false, raf = 0, last = 0, time = 0, first = true;
    function frame(now) {
      raf = running ? requestAnimationFrame(frame) : 0;
      const dt = Math.min(0.05, last ? (now - last) / 1000 : 0.016);
      last = now;
      if (!reduced) time += dt;
      const tg = target();
      const k = reduced ? 1 : 1 - Math.pow(0.0025, dt);
      for (let i = 0; i < 7; i++) cur[i] = lerp(cur[i], tg[i], k);
      mouse.x = lerp(mouse.x, mouse.tx, reduced ? 1 : 1 - Math.pow(0.02, dt));
      mouse.y = lerp(mouse.y, mouse.ty, reduced ? 1 : 1 - Math.pow(0.02, dt));

      const [x, y, sc, gap, tilt, spin, ringOn] = cur;
      world.position.set(x * halfW, y * halfH + Math.sin(time * 0.6) * 0.12, 0);
      world.scale.setScalar(sc * Math.min(1, halfW / 4.2));
      stack.rotation.set(tilt + mouse.y * 0.12, spin + time * 0.12 + mouse.x * 0.25, -0.12);
      slabs.forEach((m, i) => {
        const off = i - (slabs.length - 1) / 2;
        m.position.y = off * gap + Math.sin(time * 1.1 + i * 0.7) * 0.05 * (gap + 0.1) * 3;
        m.rotation.y = Math.sin(time * 0.5 + i) * 0.05 * gap;
      });
      ring.rotation.set(1.2 + Math.sin(time * 0.3) * 0.2 + mouse.y * 0.1, time * 0.25 + spin * 0.6, 0.4);
      ring.scale.setScalar(0.4 + 0.6 * ringOn);
      ring.scale.z *= 0.55;
      ring.visible = ringOn > 0.05;
      glow.position.x = mouse.x * 0.4;
      glow.material.opacity = 0.75 + Math.sin(time * 0.8) * 0.15;

      renderer.render(scene, camera);
      if (first) { first = false; canvas.classList.add('on'); }
    }

    return {
      start() { if (!running) { running = true; last = 0; raf = requestAnimationFrame(frame); } },
      stop() { running = false; if (raf) cancelAnimationFrame(raf); raf = 0; },
      resize,
    };
  }

  // --------------------------------------------------------------- run ----
  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src; s.async = true; s.onload = res; s.onerror = rej;
      document.head.appendChild(s);
    });
  }

  function init() {
    const items = readCards();
    if (!items.length || !window.HofView) return;

    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    const root = document.createElement('div');
    root.id = 'gl-root';
    root.hidden = true;
    root.innerHTML = build(items);
    document.body.appendChild(root);

    const nav = root.querySelector('#gl-nav');
    const ul = root.querySelector('#gl-ul');
    const navLinks = [...root.querySelectorAll('#gl-links a')];
    const storyWords = [...root.querySelectorAll('#gl-story .sw')];
    const story = root.querySelector('#gl-story');
    const bgHost = root.querySelector('#gl-bg');

    let active = false, glassApi = null, glassLoading = false, lenis = null, loop = 0, lastY = 0;
    const scrollP = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      return max > 0 ? clamp(window.scrollY / max, 0, 1) : 0;
    };

    // Cards: whole card clicks through, the glow follows the cursor, slight tilt.
    root.querySelectorAll('.gl-card').forEach((c) => {
      c.addEventListener('click', (e) => { if (!e.target.closest('a')) location.href = c.dataset.href; });
      c.addEventListener('pointermove', (e) => {
        const r = c.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
        c.style.setProperty('--mx', px * 100 + '%');
        c.style.setProperty('--my', py * 100 + '%');
        if (!reduced && e.pointerType === 'mouse') c.style.transform = `perspective(1200px) rotateX(${(0.5 - py) * 3}deg) rotateY(${(px - 0.5) * 4}deg) translateY(-6px)`;
      });
      c.addEventListener('pointerleave', () => { c.style.transform = ''; });
    });

    // In-page anchors go through Lenis when it's running.
    root.addEventListener('click', (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const el = document.getElementById(a.getAttribute('href').slice(1));
      if (!el) return;
      e.preventDefault();
      if (lenis) lenis.scrollTo(el, { offset: -70, duration: 1.4 });
      else window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 70, behavior: reduced ? 'auto' : 'smooth' });
    });

    // Reveal on scroll, count numbers up, type the build log.
    const counted = new WeakSet();
    function countUp(el) {
      if (counted.has(el)) return;
      counted.add(el);
      const p = parseVal(el.dataset.count);
      if (!p || reduced) return;
      const t0 = performance.now(), dur = 1800;
      const step = (now) => {
        const t = clamp((now - t0) / dur, 0, 1);
        const e = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
        el.textContent = fmtVal(p, p.num * e);
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }
    const termBody = root.querySelector('#gl-term-body');
    let typed = false;
    function typeLog() {
      if (typed) return;
      typed = true;
      const by = Object.fromEntries(items.map((i) => [i.key, i]));
      const lines = [
        ['<span class="p">~/homepage</span> <span class="n">$</span> python3 timelapse/build_events.py', 22],
        ...LOG.filter(([k, i]) => by[k] && by[k].stats[i]).map(([k, i, what]) =>
          [`<span class="dim">&rarr;</span> reading <span class="n">${esc(by[k].stats[i].val)}</span> ${esc(what)}`, 0]),
      ];
      if (by.lapse && by.lapse.stats[0]) lines.push([`<span class="ok">&check;</span> <span class="n">${esc(by.lapse.stats[0].val)}</span> trips painted on one map`, 0]);
      lines.push(['<span class="p">~/homepage</span> <span class="n">$</span> git push', 22]);
      lines.push(['<span class="dim">Railway deploying main&hellip;</span> <span class="ok">live</span>', 0]);
      lines.push(['<span class="p">~/homepage</span> <span class="n">$</span> <span class="cur"></span>', 0]);
      if (reduced) { termBody.innerHTML = lines.map(([h]) => `<div class="gl-term-line">${h}</div>`).join(''); return; }
      let i = 0;
      const next = () => {
        if (i >= lines.length || !active) { if (i < lines.length) termBody.innerHTML += lines.slice(i).map(([h]) => `<div class="gl-term-line">${h}</div>`).join(''); return; }
        const [html, typeMs] = lines[i++];
        const div = document.createElement('div');
        div.className = 'gl-term-line';
        termBody.appendChild(div);
        if (!typeMs) { div.innerHTML = html; setTimeout(next, 260); return; }
        // Type the command text, keep the prompt markup.
        const cut = html.lastIndexOf('</span>') + 7;
        const head = html.slice(0, cut), cmd = html.slice(cut);
        let n = 0;
        const tick = () => {
          div.innerHTML = head + esc(cmd.slice(0, n)) + '<span class="cur"></span>';
          if (n++ < cmd.length) setTimeout(tick, typeMs);
          else { div.innerHTML = head + esc(cmd); setTimeout(next, 420); }
        };
        tick();
      };
      next();
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        en.target.classList.add('in');
        en.target.querySelectorAll('[data-count]').forEach(countUp);
        if (en.target.classList.contains('gl-term')) typeLog();
        io.unobserve(en.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    root.querySelectorAll('.gl-rv').forEach((el, i) => {
      if (el.classList.contains('gl-card') && !el.style.getPropertyValue('--d')) {
        const sib = [...el.parentNode.children].indexOf(el);
        el.style.setProperty('--d', (sib % 2) * 110 + 'ms');
      }
      io.observe(el);
    });

    // Per-frame page work: story words, nav state, section underline.
    const sections = navLinks.map((a) => document.getElementById(a.dataset.sec));
    function moveUl(a) {
      if (!a) { ul.style.opacity = 0; return; }
      ul.style.opacity = 1;
      ul.style.left = a.offsetLeft + 12 + 'px';
      ul.style.width = a.offsetWidth - 24 + 'px';
    }
    let lastOn = null;
    function pageFrame() {
      loop = active ? requestAnimationFrame(pageFrame) : 0;
      const y = window.scrollY;
      nav.classList.toggle('solid', y > 30);
      nav.classList.toggle('tuck', y > 600 && y > lastY + 2);
      if (y < lastY - 2 || y < 600) nav.classList.remove('tuck');
      lastY = y;

      if (!reduced) {
        const r = story.getBoundingClientRect();
        const prog = clamp((-r.top + window.innerHeight * 0.15) / (r.height - window.innerHeight * 0.85), 0, 1);
        const lit = Math.round(prog * storyWords.length);
        for (let i = 0; i < storyWords.length; i++) storyWords[i].classList.toggle('lit', i < lit);
      }

      let on = null;
      const mid = window.innerHeight * 0.4;
      sections.forEach((s, i) => { if (s) { const r = s.getBoundingClientRect(); if (r.top < mid && r.bottom > mid) on = navLinks[i]; } });
      if (on !== lastOn) {
        navLinks.forEach((a) => a.classList.toggle('on', a === on));
        moveUl(on);
        lastOn = on;
      }
    }

    function lenisRaf(t) { if (lenis) { lenis.raf(t); requestAnimationFrame(lenisRaf); } }

    function show() {
      active = true;
      if (!document.querySelector('link[data-gl-font]')) {
        const l = document.createElement('link');
        l.rel = 'stylesheet'; l.href = FONT_URL; l.dataset.glFont = '1';
        document.head.appendChild(l);
      }
      document.documentElement.classList.add('gl-on');
      root.hidden = false;
      root.classList.remove('play');
      void root.offsetWidth;
      root.classList.add('play');
      lastOn = null;
      if (!loop) loop = requestAnimationFrame(pageFrame);

      if (glassApi) glassApi.start();
      else if (!glassLoading) {
        glassLoading = true;
        startGlass(bgHost, scrollP).then((api) => {
          glassApi = api;
          if (api && active) api.start();
        }).catch(() => { /* CSS blobs stay as the background */ });
      }

      if (!reduced && !window.matchMedia('(pointer: coarse)').matches) {
        const go = () => {
          if (!active || lenis || !window.Lenis) return;
          lenis = new window.Lenis({ duration: 1.15, smoothWheel: true });
          requestAnimationFrame(lenisRaf);
        };
        if (window.Lenis) go(); else loadScript(LENIS_URL).then(go).catch(() => {});
      }
      document.title = 'Will Hofner';
    }
    function hide() {
      active = false;
      root.hidden = true;
      document.documentElement.classList.remove('gl-on');
      if (glassApi) glassApi.stop();
      if (loop) cancelAnimationFrame(loop);
      loop = 0;
      if (lenis) { lenis.destroy(); lenis = null; }
      document.title = 'Activity Dashboard';
    }

    document.addEventListener('visibilitychange', () => {
      if (!glassApi || !active) return;
      if (document.hidden) glassApi.stop(); else glassApi.start();
    });

    window.HofView.register('glass', { label: 'Glass', show, hide });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
