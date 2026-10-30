/* ============================================================
   video — a recorded walkthrough of a real page
   mode: css · slots: 0   (the <video> element does its own work)

   <div class="tile" data-demo="video" data-src="assets/video/name"
        data-mode="css" data-poster="assets/video/name.jpg"></div>
   Loads name.webm / name.mp4 lazily; plays only while on screen,
   muted, looping; pauses the moment it leaves. Reduced motion →
   poster only with a play control.
   ============================================================ */

export const meta = { id: 'video', mode: 'css', duration: 1, slots: 0 };

const CSS = `
.vid{position:absolute;inset:0;background:#000}
.vid video,.vid img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:top center}
.vid video{opacity:0;transition:opacity .5s}
.vid.playing video{opacity:1}
.vid .bar{position:absolute;left:0;right:0;bottom:0;height:2px;background:rgba(255,255,255,.12)}
.vid .bar i{display:block;height:100%;width:0;background:var(--ac-2);transform-origin:0 0}
.vid .tag{position:absolute;left:12px;bottom:12px;font-family:var(--mono);font-size:9px;letter-spacing:.2em;text-transform:uppercase;
  color:var(--fg);background:rgba(0,0,0,.55);backdrop-filter:blur(8px);border:1px solid var(--rule);padding:5px 9px;border-radius:3px;display:flex;align-items:center;gap:7px}
.vid .tag::before{content:"";width:6px;height:6px;border-radius:50%;background:#ff3b4a;box-shadow:0 0 8px #ff3b4a}
.vid.paused .tag::before{background:var(--fg-3);box-shadow:none}
.vid button{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:64px;height:64px;border-radius:50%;border:1px solid var(--rule-2);
  background:rgba(0,0,0,.55);backdrop-filter:blur(8px);color:var(--fg);font-size:20px;display:none;place-items:center;cursor:pointer}
.vid.rm button{display:grid}
.vid.rm.playing button{display:none}
`;

export default function create(root, ctx) {
  ctx.css('video', CSS);
  let wrap, video, bar, loaded = false, raf = null;
  const base = root.dataset.src;
  const poster = root.dataset.poster || base + '.jpg';

  function load() {
    if (loaded) return; loaded = true;
    video.innerHTML = `<source src="${base}.webm" type="video/webm"><source src="${base}.mp4" type="video/mp4">`;
    video.load();
  }
  function onTime() {           // progress bar driven by the media clock — no rAF needed
    if (video.duration) bar.style.transform = `scaleX(${video.currentTime / video.duration})`;
  }

  return {
    mount() {
      root.classList.add('video');
      root.innerHTML = `<div class="vid${ctx.reduced ? ' rm' : ''}">
        <img src="${poster}" alt="" loading="lazy" decoding="async">
        <video muted loop playsinline preload="none" poster="${poster}" aria-hidden="true"></video>
        <div class="bar"><i></i></div>
        <span class="tag">${root.dataset.label || 'recorded walkthrough'}</span>
        <button type="button" aria-label="Play walkthrough">▶</button>
      </div>`;
      wrap = root.querySelector('.vid'); video = wrap.querySelector('video'); bar = wrap.querySelector('.bar i');
      video.addEventListener('timeupdate', onTime);
      video.addEventListener('playing', () => wrap.classList.add('playing'));
      wrap.querySelector('button').addEventListener('click', () => { load(); video.play(); });
    },
    play() {
      if (ctx.reduced) return;
      load(); wrap.classList.remove('paused');
      const p = video.play(); if (p && p.catch) p.catch(() => {});
    },
    pause() { wrap.classList.add('paused'); video.pause(); },
    reset() {},
    tick() {},
    setProgress() {},
    resize() {},
  };
}
