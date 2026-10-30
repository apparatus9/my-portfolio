/* ============================================================
   dw-offline — Dream Wheels: offline-resilient entries
   mode: loop · 10.4 s

   The booth form on a phone. Venue wifi drops. Three entries are
   submitted anyway and stack into device storage. Wifi returns and
   the queue drains into Firestore one by one. This is the claim
   from the project copy, shown rather than stated.
   ============================================================ */

export const meta = { id: 'dw-offline', mode: 'loop', duration: 10400, slots: 1 };

const CSS = `
.dwo-in{position:absolute;inset:0;display:grid;grid-template-columns:auto minmax(0,560px);justify-content:center;gap:6%;align-items:center;padding:5% 7%;
  font-family:var(--mono);color:var(--fg);
  background:repeating-linear-gradient(90deg,var(--rule) 0 1px,transparent 1px 42px)}
.dwo *{box-sizing:border-box}

/* phone */
.dwo-phone{
  position:relative;height:88%;max-height:420px;aspect-ratio:9/18.5;border-radius:26px;
  background:#0a0a0a;border:1px solid var(--rule-2);box-shadow:0 40px 80px -30px rgba(0,0,0,.8),inset 0 0 0 3px #1a1a1a;
  overflow:hidden;
}
.dwo-screen{position:absolute;inset:8px;border-radius:20px;overflow:hidden;
  background:radial-gradient(120% 60% at 50% 0%,#1e2a12 0%,#0a0d06 55%,#050604 100%);color:#fff;padding:20px 14px 14px;
  display:flex;flex-direction:column;gap:8px;font-size:8px}
.dwo-status{display:flex;justify-content:space-between;align-items:center;font-size:7.5px;letter-spacing:.1em;color:rgba(255,255,255,.7)}
.dwo-wifi{position:relative;width:12px;height:10px}
.dwo-wifi::before{content:"";position:absolute;left:50%;bottom:0;width:12px;height:12px;border-radius:50%;border:2px solid currentColor;border-color:currentColor transparent transparent transparent;transform:translateX(-50%) scale(1)}
.dwo-wifi::after{content:"";position:absolute;left:50%;bottom:0;width:3px;height:3px;border-radius:50%;background:currentColor;transform:translateX(-50%)}
.dwo-wifi.off{color:#ff5c6c}
.dwo-wifi.off::before{border-color:#ff5c6c transparent transparent transparent}
.dwo-wifi i{position:absolute;left:-2px;top:4px;width:16px;height:1.5px;background:#ff5c6c;transform:rotate(-45deg);opacity:0}
.dwo-wifi.off i{opacity:1}
.dwo-brand{font-family:var(--serif);font-style:italic;font-size:15px;color:#fff;text-align:center;margin-top:8px;line-height:1}
.dwo-brand small{display:block;font-family:var(--mono);font-style:normal;font-size:6.5px;letter-spacing:.2em;text-transform:uppercase;color:#c9e35a;margin-top:5px}
.dwo-field{height:22px;border:1px solid rgba(255,255,255,.18);border-radius:6px;background:rgba(255,255,255,.05);padding:0 8px;display:flex;align-items:center;color:rgba(255,255,255,.85);font-size:8px;white-space:nowrap;overflow:hidden}
.dwo-field.empty{color:rgba(255,255,255,.3)}
.dwo-btn{margin-top:auto;height:26px;border-radius:6px;background:#c9e35a;color:#111;display:grid;place-items:center;font-weight:700;font-size:8px;letter-spacing:.14em;text-transform:uppercase;transform:scale(var(--bs,1));transition:transform .12s}
.dwo-toast{position:absolute;left:12px;right:12px;bottom:44px;border-radius:6px;padding:7px 9px;font-size:7.5px;letter-spacing:.04em;
  background:rgba(255,255,255,.1);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.15);
  opacity:var(--to,0);transform:translateY(calc((1 - var(--to,0)) * 8px));transition:opacity .25s,transform .25s}
.dwo-toast b{color:#c9e35a}

/* right: storage drawer → cloud */
.dwo-right{display:flex;flex-direction:column;gap:16px;min-width:0}
.dwo-title{font-size:9px;letter-spacing:.22em;text-transform:uppercase;color:var(--fg-3)}
.dwo-net{display:flex;align-items:center;gap:10px;font-size:10px;letter-spacing:.14em;text-transform:uppercase}
.dwo-net .led{width:8px;height:8px;border-radius:50%;background:var(--ok-c);box-shadow:0 0 10px var(--ok-c)}
.dwo-net.off .led{background:#ff5c6c;box-shadow:0 0 10px #ff5c6c}
.dwo-net .txt{color:var(--fg-2)}
.dwo-net.off .txt{color:#ff8a96}

.dwo-flow{display:grid;grid-template-columns:1fr 40px 1fr;gap:8px;align-items:stretch}
.dwo-box{border:1px solid var(--rule);border-radius:8px;background:var(--surface);padding:12px;min-height:120px;position:relative}
.dwo-box .k{font-size:8px;letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3);display:flex;justify-content:space-between}
.dwo-box .k b{color:var(--ac-2);font-weight:500}
.dwo-box .k b.ok{color:var(--ok-c)}
.dwo-list{margin-top:10px;display:flex;flex-direction:column;gap:6px}
.dwo-item{
  height:22px;border-radius:4px;background:color-mix(in srgb,var(--fg) 8%,transparent);border:1px solid var(--rule);
  padding:0 8px;display:flex;align-items:center;justify-content:space-between;font-size:8px;color:var(--fg-2);
  opacity:var(--io,0);transform:translateX(calc(var(--ix,0) * 1px));transition:opacity .3s,transform .45s var(--ease);
}
.dwo-item i{font-style:normal;color:var(--ok-c);opacity:var(--tk,0);transition:opacity .2s}
.dwo-arrow{display:grid;place-items:center;color:var(--fg-3);font-size:16px;position:relative}
.dwo-arrow::before{content:"";position:absolute;left:0;right:0;top:50%;height:1px;background:var(--rule-2)}
.dwo-arrow span{position:relative;background:var(--bg);padding:0 4px}
.dwo-arrow b{position:absolute;left:0;top:50%;width:6px;height:6px;border-radius:50%;background:var(--ac-2);box-shadow:0 0 8px var(--ac-2);transform:translate(calc(var(--px,0) * 34px),-50%);opacity:var(--po,0)}
.dwo-cloud{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:8px;color:var(--fg-3)}
.dwo-cloud svg{width:18px;height:14px;stroke:var(--fg-3);fill:none;stroke-width:1.6}
.dwo-sum{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-2)}
.dwo-sum b{color:var(--ok-c);font-weight:500}

@media (max-width:640px){
  .dwo-in{grid-template-columns:1fr;grid-template-rows:auto;padding:5% 6%;gap:10px;align-content:center}
  .dwo-phone{display:none}
  .dwo-right{gap:10px}
  .dwo-flow{grid-template-columns:1fr 1fr;gap:8px}
  .dwo-arrow{display:none}
  .dwo-box{min-height:96px;padding:10px}
  .dwo-box .k{flex-direction:column;gap:2px}
  .dwo-item{font-size:7px;padding:0 6px}
  .dwo-item span:nth-child(2){display:none}
}
`;

const ENTRIES = [['Priya R.', '416-···-2210'], ['Marcus D.', '647-···-8831'], ['Jen & Tom K.', '905-···-0417']];

/* timeline (ms) */
const T = {
  wifiOff: 1300,
  submit: [1900, 3000, 4100],          // each: fill 0-600, press at 650, toast 700-1600, item lands 750
  wifiOn: 5600,
  sync: [6300, 7100, 7900],            // each: dot travels 0-500, tick at 520
  done: 8600, exit: 9700,
};

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const snap = (t, a, b) => clamp((t - a) / Math.max(b - a, 1), 0, 1);

export default function create(root, ctx) {
  ctx.css('dw-offline', CSS);
  let wifi, net, fields, btn, toast, qCount, cCount, qItems, cItems, dot, sum, screenWifi;

  function mount() {
    root.classList.add('dwo');
    root.innerHTML = `<div class="dwo-in">
      <div class="dwo-phone" aria-hidden="true">
        <div class="dwo-screen">
          <div class="dwo-status"><span>1:50</span><span class="dwo-wifi"><i></i></span></div>
          <div class="dwo-brand">Dream Wheels<small>Enter to win · free oil for life</small></div>
          <div class="dwo-field empty" data-ph="Full name"></div>
          <div class="dwo-field empty" data-ph="Phone"></div>
          <div class="dwo-field empty" data-ph="Email"></div>
          <div class="dwo-btn">Enter to win →</div>
          <div class="dwo-toast"><b>Saved on this device.</b> Will send when the wifi's back.</div>
        </div>
      </div>
      <div class="dwo-right">
        <div class="dwo-title">Booth · venue wifi</div>
        <div class="dwo-net"><span class="led"></span><span class="txt">Online</span></div>
        <div class="dwo-flow">
          <div class="dwo-box">
            <div class="k"><span>Device storage</span><b class="q">queued · 0</b></div>
            <div class="dwo-list">${ENTRIES.map(e => `<div class="dwo-item"><span>${e[0]}</span><span>${e[1]}</span><i>✓</i></div>`).join('')}</div>
          </div>
          <div class="dwo-arrow"><span>→</span><b></b></div>
          <div class="dwo-box">
            <div class="k"><span>Firestore</span><b class="c">entries · 0</b></div>
            <div class="dwo-list">${ENTRIES.map(e => `<div class="dwo-item"><span>${e[0]}</span><i>✓</i></div>`).join('')}</div>
            <div class="dwo-cloud"><svg viewBox="0 0 24 18"><path d="M6 15h12a4 4 0 0 0 0-8 6 6 0 0 0-11.5-1A4.5 4.5 0 0 0 6 15z"/></svg>REST · no SDK</div>
          </div>
        </div>
        <div class="dwo-sum">0 entries lost · <b>3/3 synced</b></div>
      </div>
    </div>`;
    screenWifi = root.querySelector('.dwo-wifi');
    net    = root.querySelector('.dwo-net');
    fields = [...root.querySelectorAll('.dwo-field')];
    btn    = root.querySelector('.dwo-btn');
    toast  = root.querySelector('.dwo-toast');
    qCount = root.querySelector('.q');
    cCount = root.querySelector('.c');
    qItems = [...root.querySelectorAll('.dwo-box:first-child .dwo-item')];
    cItems = [...root.querySelectorAll('.dwo-box:last-child .dwo-item')];
    dot    = root.querySelector('.dwo-arrow b');
    sum    = root.querySelector('.dwo-sum');
  }

  function frame(t) {
    const off = t >= T.wifiOff && t < T.wifiOn;
    screenWifi.classList.toggle('off', off);
    net.classList.toggle('off', off);
    net.querySelector('.txt').textContent = off ? 'Offline' : 'Online';

    /* which submission is in flight */
    let queued = 0, filling = -1, fp = 0, pressed = false, toastOn = false;
    T.submit.forEach((t0, i) => {
      if (t >= t0 + 750) queued++;
      if (t >= t0 && t < t0 + 1700) { filling = i; fp = snap(t, t0, t0 + 600); pressed = t >= t0 + 650 && t < t0 + 800; toastOn = t >= t0 + 700 && t < t0 + 1600; }
    });
    if (t >= T.exit) queued = 0;
    const e = ENTRIES[Math.max(filling, 0)];
    const vals = [e[0], e[1], e[0].split(' ')[0].toLowerCase() + '@example.com'];
    fields.forEach((f, i) => {
      const p = clamp(fp * 3 - i, 0, 1);
      const txt = filling >= 0 ? vals[i].slice(0, Math.round(vals[i].length * p)) : '';
      const show = txt || f.dataset.ph;
      if (f.textContent !== show) f.textContent = show;
      f.classList.toggle('empty', !txt);
    });
    btn.style.setProperty('--bs', pressed ? .96 : 1);
    toast.style.setProperty('--to', toastOn ? 1 : 0);

    /* queue list */
    qItems.forEach((it, i) => {
      const landed = t >= T.submit[i] + 750 && t < T.exit;
      const synced = t >= T.sync[i] + 520 && t < T.exit;
      it.style.setProperty('--io', landed && !synced ? 1 : 0);
      it.style.setProperty('--ix', synced ? 24 : 0);
    });
    let synced = 0;
    cItems.forEach((it, i) => {
      const on = t >= T.sync[i] + 520 && t < T.exit;
      if (on) synced++;
      it.style.setProperty('--io', on ? 1 : 0);
      it.style.setProperty('--tk', on ? 1 : 0);
    });
    qCount.textContent = `queued · ${Math.max(queued - synced, 0)}`;
    cCount.textContent = `entries · ${synced}`;
    cCount.classList.toggle('ok', synced === 3);

    /* dot travelling across the arrow during each sync */
    let px = 0, po = 0;
    T.sync.forEach(t0 => { if (t >= t0 && t < t0 + 500) { px = snap(t, t0, t0 + 500); po = 1; } });
    dot.style.setProperty('--px', px.toFixed(3));
    dot.style.setProperty('--po', po);

    sum.style.opacity = t >= T.done && t < T.exit ? 1 : .35;
  }

  return {
    mount,
    play() {},
    pause() {},
    reset(state) { frame(state === 'end' ? T.done + 100 : 0); },
    tick(now, dt, t) { frame(t); },
    setProgress() {},
    resize() {},
  };
}
