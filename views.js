/*
 * Views: one switcher for every skin of the landing page.
 *
 *   classic  the card grid in index.html (always underneath, never registered)
 *   world    overworld.js, the walkable pixel map
 *   glass    glass.js, the sleek scrolling page with 3D glass
 *
 * A skin calls HofView.register(name, { label, show(), hide() }). Only one
 * skin is ever showing; picking "classic" hides them all. The choice is
 * remembered in localStorage ("hof:view"), and ?view=<name> overrides it.
 * A floating pill in the top-right switches between them and restyles itself
 * to match whichever skin is active (html[data-view]).
 */
(() => {
  'use strict';
  if (window.HofView) return;

  const ORDER = ['world', 'glass', 'classic'];
  const LABELS = { world: 'Walk', glass: 'Glass', classic: 'Classic' };
  const skins = {};
  let current = null;
  let bar = null;

  const CSS = `
  #hv-bar{position:fixed;top:max(12px,env(safe-area-inset-top));right:max(12px,env(safe-area-inset-right));z-index:1001;display:flex;gap:2px;padding:4px;border-radius:999px;
    font:600 12px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:rgba(18,18,26,.82);border:1px solid #2a2a3c;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:0 8px 24px rgba(0,0,0,.35)}
  #hv-bar button{position:relative;z-index:1;appearance:none;border:0;background:none;color:#8888a0;font:inherit;padding:8px 12px;border-radius:999px;cursor:pointer;transition:color .25s}
  #hv-bar button[aria-pressed="true"]{color:#0a0a0f}
  #hv-bar button:focus-visible{outline:2px solid #3b82f6;outline-offset:1px}
  #hv-pill{position:absolute;z-index:0;top:4px;bottom:4px;border-radius:999px;background:#e0e0e8;transition:left .35s cubic-bezier(.2,.8,.2,1),width .35s cubic-bezier(.2,.8,.2,1)}
  html[data-view="world"] #hv-bar{font-family:'Press Start 2P',ui-monospace,monospace;font-size:8px;font-weight:400;border-radius:0;border:2px solid #3a3a52;background:#12121a;box-shadow:3px 3px 0 #000;backdrop-filter:none;-webkit-backdrop-filter:none}
  html[data-view="world"] #hv-bar button,html[data-view="world"] #hv-pill{border-radius:0}
  html[data-view="world"] #hv-bar button{padding:8px 9px}
  html[data-view="glass"] #hv-bar{font-family:'Geist',-apple-system,sans-serif;font-weight:500;font-size:13px;background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.8);box-shadow:0 10px 30px rgba(32,0,168,.12)}
  html[data-view="glass"] #hv-bar button{color:#606171}
  html[data-view="glass"] #hv-bar button[aria-pressed="true"]{color:#fff}
  html[data-view="glass"] #hv-pill{background:linear-gradient(100deg,#0040ff,#5e00ff);box-shadow:0 6px 18px rgba(64,0,255,.35)}
  @media (prefers-reduced-motion: reduce){#hv-pill{transition:none}}
  `;

  function saved() {
    const q = new URLSearchParams(location.search).get('view');
    if (q && (q === 'classic' || skins[q])) return q;
    let pref = null;
    try { pref = localStorage.getItem('hof:view'); } catch (e) { /* ignore */ }
    if (pref && (pref === 'classic' || skins[pref])) return pref;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return reduced || !skins.world ? 'classic' : 'world';
  }

  function set(name, save) {
    if (name !== 'classic' && !skins[name]) name = 'classic';
    if (save) { try { localStorage.setItem('hof:view', name); } catch (e) { /* ignore */ } }
    if (name === current) return;
    const prev = current;
    current = name;
    if (prev && skins[prev]) skins[prev].hide();
    document.documentElement.dataset.view = name;
    if (skins[name]) skins[name].show();
    window.scrollTo(0, 0);
    paint();
  }

  function paint() {
    if (!bar) return;
    let on = null;
    bar.querySelectorAll('button').forEach((b) => {
      const yes = b.dataset.view === current;
      b.setAttribute('aria-pressed', yes ? 'true' : 'false');
      if (yes) on = b;
    });
    const pill = bar.querySelector('#hv-pill');
    if (on) { pill.style.left = on.offsetLeft + 'px'; pill.style.width = on.offsetWidth + 'px'; }
  }

  function build() {
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    bar = document.createElement('nav');
    bar.id = 'hv-bar';
    bar.setAttribute('aria-label', 'Choose a view');
    bar.innerHTML = '<span id="hv-pill"></span>' + ORDER
      .filter((v) => v === 'classic' || skins[v])
      .map((v) => `<button type="button" data-view="${v}">${(skins[v] && skins[v].label) || LABELS[v]}</button>`)
      .join('');
    bar.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-view]');
      if (b) set(b.dataset.view, true);
    });
    document.body.appendChild(bar);
    window.addEventListener('resize', paint);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(paint).catch(() => {});
  }

  window.HofView = {
    register(name, skin) { skins[name] = skin; },
    set,
    get current() { return current; },
  };

  // Skins register in their own DOMContentLoaded handlers, which run after
  // this one, so wait a tick before picking the first view.
  function boot() {
    setTimeout(() => {
      build();
      set(saved(), false);
      // The first paint happens before layout settles in some browsers.
      requestAnimationFrame(paint);
    }, 0);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
