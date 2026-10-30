/* ============================================================
   runtime.js — the tile runtime (ES module, zero dependencies)

   Finds every [data-demo] root on the page, lazy-imports
   demos/<id>.js one viewport ahead, and drives every playing demo
   from ONE requestAnimationFrame loop that stops entirely when
   nothing is on screen. At most BUDGET slots animate at once; the
   rest hold still until they're the most visible.

   Markup:   <div class="tile" data-demo="lsd" data-mode="loop" role="img" aria-label="…"></div>
   Module:   demos/<id>.js exporting { meta, default: create(root, ctx) }
   Contract: demos/_runtime-contract.md
   Used by:  work.html
   ============================================================ */

export const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const fine    = matchMedia('(pointer: fine)').matches;
export const coarse  = matchMedia('(pointer: coarse)').matches;

/* the shared frame loop: runs only while a job is registered */
const Loop = (() => {
  const jobs = new Set();
  let raf = 0, last = 0;
  const stats = { frames: 0, dts: [] };
  function frame(now) {
    raf = 0;
    const dt = last ? Math.min(now - last, 50) : 16;   // clamp: a tab switch never produces a 2s step
    last = now;
    stats.frames++;
    if (stats.dts.push(dt) > 120) stats.dts.shift();
    for (const job of jobs) job(now, dt);
    if (jobs.size) raf = requestAnimationFrame(frame);
    else last = 0;
  }
  return {
    add(job)    { jobs.add(job); if (!raf) raf = requestAnimationFrame(frame); },
    remove(job) { jobs.delete(job); },
    running()   { return !!raf; },
    stats,
  };
})();

const BUDGET = 2;                       // slots that may animate at once
const probeCache = new Map();
function probe(url) {                   // does an optional asset exist? (cached)
  if (!probeCache.has(url)) {
    probeCache.set(url, new Promise(res => {
      const im = new Image();
      im.onload = () => res(true);
      im.onerror = () => res(false);
      im.src = url;
    }));
  }
  return probeCache.get(url);
}
const styleOnce = new Set();
function css(id, text) {                // inject a demo's stylesheet exactly once
  if (styleOnce.has(id)) return;
  styleOnce.add(id);
  const s = document.createElement('style');
  s.dataset.demoCss = id;           // not data-demo: that attribute is how tiles are discovered
  s.textContent = text;
  document.head.appendChild(s);
}
const ctx = { reduced, fine, coarse, probe, css, dev: new URLSearchParams(location.search).has('debug') };

const tiles = new Map();                // root -> record
// mount in idle time, but never later than 300ms: a busy page must not stall a demo indefinitely
const idle = window.requestIdleCallback ? (fn => requestIdleCallback(fn, { timeout: 300 })) : (fn => setTimeout(fn, 0));

function record(root) {
  return {
    root, id: root.dataset.demo, mode: root.dataset.mode || 'loop',
    meta: null, inst: null, ready: false, playing: false, candidate: false,
    ratio: 0, t: 0, ticks: 0, lastP: -1,
  };
}

async function load(rec) {
  if (rec.ready || rec.loading) return;
  rec.loading = true;
  try {
    const mod = await import(`./${rec.id}.js`);
    rec.meta = Object.assign({ mode: rec.mode, duration: 8000, slots: 1 }, mod.meta || {});
    rec.mode = rec.meta.mode;
    idle(() => {
      rec.inst = mod.default(rec.root, ctx);
      rec.inst.mount();
      rec.inst.reset(reduced ? 'end' : 'start');
      const ro = new ResizeObserver(([e]) => rec.inst.resize && rec.inst.resize(e.contentRect.width, e.contentRect.height));
      ro.observe(rec.root);
      rec.ready = true;
      if (rec.mode === 'scrub') scrubOnce(rec);
      rank();
    });
  } catch (err) {
    rec.root.dataset.error = String(err && err.message || err);
    console.error(`[tiles] ${rec.id} failed to load`, err);
  }
}

function scrubOnce(rec) {
  if (!rec.ready) return;
  const p = parseFloat(rec.root.style.getPropertyValue('--p')) || 0;
  if (Math.abs(p - rec.lastP) >= .002) { rec.lastP = p; rec.inst.setProgress(p); rec.ticks++; }
}

function play(rec) {
  if (rec.playing || !rec.ready || reduced) return;
  rec.playing = true;
  if (rec.mode === 'loop') { rec.t = 0; rec.inst.reset('start'); }
  rec.inst.play();
}
function pause(rec) {
  if (!rec.playing) return;
  rec.playing = false;
  rec.inst.pause();
}

/* the one job that drives all playing tiles (css-kind tiles animate themselves) */
function tileJob(now, dt) {
  let any = false;
  for (const rec of tiles.values()) {
    if (!rec.playing || rec.mode === 'css') continue;
    any = true;
    if (rec.mode === 'scrub') { scrubOnce(rec); continue; }
    rec.t = (rec.t + dt) % rec.meta.duration;
    rec.inst.tick(now, dt, rec.t);
    rec.ticks++;
  }
  if (!any) Loop.remove(tileJob);
}

/* choose which candidates get to animate */
function rank() {
  const cands = [...tiles.values()].filter(r => r.candidate && r.ready);
  cands.sort((a, b) =>
    (b.ratio - a.ratio) ||
    ((b.playing ? 1 : 0) - (a.playing ? 1 : 0)) ||                          // hysteresis
    (a.root.compareDocumentPosition(b.root) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
  let used = 0;
  for (const rec of cands) {
    const cost = rec.meta.slots ?? 1;
    if (used + cost <= BUDGET) { used += cost; play(rec); } else pause(rec);
  }
  for (const rec of tiles.values()) if (!rec.candidate) pause(rec);
  if ([...tiles.values()].some(r => r.playing && r.mode !== 'css')) Loop.add(tileJob);
}

const loadIO = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { load(tiles.get(e.target)); loadIO.unobserve(e.target); } });
}, { rootMargin: '100% 0px 100% 0px', threshold: 0 });

const playIO = new IntersectionObserver(entries => {
  entries.forEach(e => {
    const rec = tiles.get(e.target);
    rec.candidate = e.isIntersecting;
    rec.ratio = e.intersectionRatio;
  });
  rank();
}, { rootMargin: '-15% 0px -15% 0px', threshold: [0, .25, .5, .75, 1] });

document.querySelectorAll('[data-demo]').forEach(root => {
  const rec = record(root);
  tiles.set(root, rec);
  loadIO.observe(root);
  playIO.observe(root);
});

/* tab hidden → everything stops; visible → re-rank */
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { for (const rec of tiles.values()) pause(rec); Loop.remove(tileJob); }
  else rank();
});

/* for the console and the screenshot harness */
window.__tiles = {
  active: () => [...tiles.values()].filter(r => r.playing).map(r => r.id),
  stats:  () => [...tiles.values()].map(r => ({ id: r.id, ticks: r.ticks, playing: r.playing, ready: r.ready, error: r.root.dataset.error || null })),
  loop:   Loop,
};
