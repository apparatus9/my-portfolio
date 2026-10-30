/* ============================================================
   gmd-pwa — Golden Mile Deals: phone admin → showroom display
   mode: loop · 10 s

   A staff member edits an offer on the PWA admin (phone, left);
   the showroom display (TV, right) updates live. Then the phone
   goes offline, the next edit queues under the service worker,
   and lands the moment the connection returns.
   ============================================================ */

export const meta = { id: 'gmd-pwa', mode: 'loop', duration: 10000, slots: 1 };

const CSS = `
.gmp-in{position:absolute;inset:0;display:grid;grid-template-columns:auto minmax(0,1fr);justify-content:center;gap:6%;align-items:center;padding:5% 7%;
  font-family:var(--mono);color:var(--fg);background:repeating-linear-gradient(90deg,var(--rule) 0 1px,transparent 1px 42px)}
.gmp-in *{box-sizing:border-box}

/* phone: the PWA admin */
.gmp-phone{position:relative;height:88%;max-height:420px;aspect-ratio:9/18.5;border-radius:26px;background:#0a0a0a;border:1px solid var(--rule-2);
  box-shadow:0 40px 80px -30px rgba(0,0,0,.8),inset 0 0 0 3px #1a1a1a;overflow:hidden}
.gmp-screen{position:absolute;inset:8px;border-radius:20px;overflow:hidden;background:#f5f3ee;color:#15130f;padding:18px 12px 12px;display:flex;flex-direction:column;gap:8px;font-size:8px}
.gmp-status{display:flex;justify-content:space-between;font-size:7px;letter-spacing:.1em;color:#6a645a}
.gmp-status .net{color:#1b7f4d}.gmp-status .net.off{color:#c23b4b}
.gmp-appbar{display:flex;align-items:center;justify-content:space-between;font-weight:700;font-size:8.5px;letter-spacing:.06em;padding-bottom:8px;border-bottom:1px solid #e1ddd2}
.gmp-appbar i{font-style:normal;font-size:6.5px;letter-spacing:.16em;color:#9c7a28;border:1px solid #9c7a28;border-radius:100px;padding:2px 6px}
.gmp-offer{border:1px solid #e1ddd2;border-radius:8px;padding:10px;background:#fff;display:flex;flex-direction:column;gap:6px}
.gmp-offer .k{font-size:6.5px;letter-spacing:.16em;text-transform:uppercase;color:#9a9184}
.gmp-offer .t{font-family:var(--serif);font-size:11px;color:#15130f}
.gmp-input{height:22px;border:1px solid #d6d0c4;border-radius:5px;padding:0 8px;display:flex;align-items:center;justify-content:space-between;background:#fbfaf7;font-size:9px;transition:border-color .2s,box-shadow .2s}
.gmp-input.focus{border-color:#9c7a28;box-shadow:0 0 0 2px rgba(156,122,40,.18)}
.gmp-input b{font-weight:500}
.gmp-input b::after{content:"";display:inline-block;width:1px;height:10px;background:#15130f;margin-left:1px;vertical-align:-1px;opacity:var(--caret,0)}
.gmp-save{margin-top:auto;height:26px;border-radius:6px;background:#0e2b1e;color:#f7f2e9;display:grid;place-items:center;font-size:7.5px;letter-spacing:.16em;text-transform:uppercase;transform:scale(var(--bs,1));transition:transform .12s}
.gmp-queue{position:absolute;left:12px;right:12px;bottom:46px;border-radius:6px;padding:6px 8px;font-size:7px;background:#15130f;color:#f7f2e9;display:flex;justify-content:space-between;align-items:center;
  opacity:var(--qo,0);transform:translateY(calc((1 - var(--qo,0)) * 8px));transition:opacity .25s,transform .25s}
.gmp-queue b{color:#c9a856;font-weight:500}
.gmp-thumb{position:absolute;width:22px;height:22px;border-radius:50%;background:rgba(21,19,15,.18);border:1.5px solid rgba(21,19,15,.5);
  left:calc(var(--tx,.5) * 100%);top:calc(var(--ty,.5) * 100%);transform:translate(-50%,-50%) scale(var(--ts,1));opacity:var(--to,0);transition:left .5s var(--ease),top .5s var(--ease),transform .15s,opacity .2s;pointer-events:none;z-index:3}

/* showroom display */
.gmp-tv{position:relative;width:100%;aspect-ratio:16/9;border-radius:8px;background:#050505;border:1px solid var(--rule-2);padding:2.2%;box-shadow:0 40px 80px -30px rgba(0,0,0,.8)}
.gmp-tv::after{content:"";position:absolute;left:50%;bottom:-14px;width:22%;height:14px;background:linear-gradient(#1a1a1a,#0a0a0a);transform:translateX(-50%);border-radius:0 0 4px 4px}
.gmp-flyer{position:relative;width:100%;height:100%;border-radius:3px;overflow:hidden;
  background:radial-gradient(120% 80% at 20% 0%,#1a2a10 0%,#0b0f06 55%,#060704 100%);color:#fff;padding:7% 8%;display:flex;flex-direction:column;justify-content:space-between}
.gmp-flyer .brand{font-family:var(--serif);font-style:italic;font-size:clamp(10px,1.6vw,14px);color:#fff}
.gmp-flyer .brand small{display:block;font-family:var(--mono);font-style:normal;font-size:6.5px;letter-spacing:.22em;text-transform:uppercase;color:#c9e35a;margin-top:3px}
.gmp-flyer .who{font-size:7.5px;letter-spacing:.24em;text-transform:uppercase;color:rgba(255,255,255,.6)}
.gmp-flyer .amt{font-family:var(--serif);font-weight:700;font-size:clamp(26px,4.6vw,48px);line-height:.95;letter-spacing:-.02em;color:#fff;display:flex;align-items:baseline;gap:.15em}
.gmp-flyer .amt .num{display:inline-block;perspective:400px}
.gmp-flyer .amt .num i{display:inline-block;font-style:normal;transform:rotateX(calc(var(--flip,0) * -90deg));opacity:calc(1 - var(--flip,0));transition:transform .22s,opacity .15s;transform-origin:50% 100%}
.gmp-flyer .amt .num u{display:inline-block;text-decoration:none;position:absolute;left:0;top:0;transform:rotateX(calc((1 - var(--flip,0)) * 90deg));opacity:var(--flip,0);transition:transform .22s,opacity .15s;transform-origin:50% 0%}
.gmp-flyer .amt small{font-family:var(--mono);font-weight:400;font-size:7.5px;letter-spacing:.18em;color:#c9e35a}
.gmp-flyer .foot{display:flex;justify-content:space-between;font-size:6.5px;letter-spacing:.18em;text-transform:uppercase;color:rgba(255,255,255,.45)}
.gmp-sw{position:absolute;right:10px;top:10px;display:flex;align-items:center;gap:6px;font-size:7px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-3);z-index:2}
.gmp-sw i{width:7px;height:7px;border-radius:50%;background:var(--ok-c);box-shadow:0 0 0 0 var(--ok-c);transform:scale(var(--pulse,1));transition:transform .2s}
.gmp-sw.off i{background:#ff5c6c}
.gmp-cap{margin-top:14px;font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3);display:flex;justify-content:space-between}
.gmp-cap b{color:var(--fg-2);font-weight:500}

@media (max-width:640px){
  .gmp-in{grid-template-columns:1fr;gap:12px;padding:5% 6%}
  .gmp-phone{display:none}
}
`;

const T = {
  focus: 900, type1: 1200, save1: 2400, tvFlip1: 2700,
  offline: 4300, focus2: 4900, type2: 5200, save2: 6300, queued: 6400,
  online: 7800, tvFlip2: 8200, done: 8900, exit: 9600,
};
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const snap = (t, a, b) => clamp((t - a) / Math.max(b - a, 1), 0, 1);

export default function create(root, ctx) {
  ctx.css('gmd-pwa', CSS);
  let net, input, inputVal, save, queue, thumb, num, sw, cap, cap2, flyerAmtNow = '1,500';

  function mount() {
    root.classList.add('gmp');
    root.innerHTML = `<div class="gmp-in">
      <div class="gmp-phone" aria-hidden="true">
        <div class="gmp-screen">
          <div class="gmp-status"><span>1:50</span><span class="net">● online</span></div>
          <div class="gmp-appbar"><span>Golden Mile · Offers</span><i>PWA</i></div>
          <div class="gmp-offer">
            <div class="k">Offer</div>
            <div class="t">First Responders</div>
            <div class="k" style="margin-top:4px">Amount off</div>
            <div class="gmp-input"><b>$1,500</b><span style="color:#9a9184">CAD</span></div>
            <div class="k" style="margin-top:4px">Audience</div>
            <div class="gmp-input"><b>Police · Fire · EMS</b></div>
          </div>
          <div class="gmp-save">Save &amp; publish</div>
          <div class="gmp-queue"><span>Offline — saved locally</span><b>queued · 1</b></div>
          <div class="gmp-thumb"></div>
        </div>
      </div>
      <div>
        <div class="gmp-tv" aria-hidden="true">
          <div class="gmp-sw"><i></i>service worker</div>
          <div class="gmp-flyer">
            <div class="brand">Golden Mile Chrysler<small>Showroom · Offer board</small></div>
            <div>
              <div class="who">First responders · Police · Fire · EMS</div>
              <div class="amt">$<span class="num" style="position:relative"><i>1,500</i><u>2,000</u></span><small>off MSRP</small></div>
            </div>
            <div class="foot"><span>Valid this month</span><span>See dealer for details</span></div>
          </div>
        </div>
        <div class="gmp-cap"><span>Phone → showroom display</span><b class="c2">live</b></div>
      </div>
    </div>`;
    net   = root.querySelector('.gmp-status .net');
    input = root.querySelector('.gmp-input');
    inputVal = input.querySelector('b');
    save  = root.querySelector('.gmp-save');
    queue = root.querySelector('.gmp-queue');
    thumb = root.querySelector('.gmp-thumb');
    num   = root.querySelector('.amt .num');
    sw    = root.querySelector('.gmp-sw');
    cap2  = root.querySelector('.c2');
  }

  function typeVal(t, t0, from, to) {
    const p = snap(t, t0, t0 + 700);
    if (p <= 0) return from;
    const n = Math.round(to.length * p);
    return to.slice(0, n);
  }

  function frame(t) {
    const off = t >= T.offline && t < T.online;
    net.textContent = off ? '○ offline' : '● online';
    net.classList.toggle('off', off);
    sw.classList.toggle('off', off);

    /* thumb path: (.5,.5) → price input (.5,.42) → save (.5,.88) */
    let tx = .5, ty = .5, to = 0, ts = 1;
    if (t >= T.focus - 400 && t < T.exit) { to = 1; }
    if (t >= T.focus - 400) { tx = .5; ty = .41; }
    if (t >= T.save1 - 400) { ty = .88; }
    if (t >= T.focus2 - 400) { ty = .41; }
    if (t >= T.save2 - 400) { ty = .88; }
    if (t >= T.queued + 800) { to = 0; }
    const tap = (t >= T.focus && t < T.focus + 150) || (t >= T.save1 && t < T.save1 + 150) || (t >= T.focus2 && t < T.focus2 + 150) || (t >= T.save2 && t < T.save2 + 150);
    ts = tap ? .78 : 1;
    thumb.style.setProperty('--tx', tx); thumb.style.setProperty('--ty', ty);
    thumb.style.setProperty('--to', to); thumb.style.setProperty('--ts', ts);

    /* input */
    const focused = (t >= T.focus && t < T.save1) || (t >= T.focus2 && t < T.save2);
    input.classList.toggle('focus', focused);
    let v = '$1,500';
    if (t >= T.type1) v = '$' + typeVal(t, T.type1, '1,500', '2,000');
    if (t >= T.type2) v = '$' + typeVal(t, T.type2, '2,000', '2,500');
    if (t >= T.exit) v = '$1,500';
    if (inputVal.textContent !== v) inputVal.textContent = v;
    inputVal.style.setProperty('--caret', focused && ((t >= T.type1 && t < T.type1 + 700) || (t >= T.type2 && t < T.type2 + 700)) ? 1 : 0);
    save.style.setProperty('--bs', (t >= T.save1 && t < T.save1 + 160) || (t >= T.save2 && t < T.save2 + 160) ? .95 : 1);
    queue.style.setProperty('--qo', t >= T.queued && t < T.online ? 1 : 0);

    /* TV amount flips */
    let cur = '1,500', next = '2,000', flip = 0;
    if (t >= T.tvFlip1) { cur = '1,500'; next = '2,000'; flip = 1; }
    if (t >= T.tvFlip1 + 400) { cur = '2,000'; next = '2,500'; flip = 0; }
    if (t >= T.tvFlip2) { flip = 1; }
    if (t >= T.tvFlip2 + 400) { cur = '2,500'; next = '1,500'; flip = 0; }
    if (t >= T.exit) { cur = '1,500'; next = '2,000'; flip = 0; }
    const i = num.querySelector('i'), u = num.querySelector('u');
    if (i.textContent !== cur) i.textContent = cur;
    if (u.textContent !== next) u.textContent = next;
    num.style.setProperty('--flip', flip);

    /* SW pulse when a publish lands */
    const pulse = (t >= T.tvFlip1 - 150 && t < T.tvFlip1 + 250) || (t >= T.tvFlip2 - 150 && t < T.tvFlip2 + 250);
    sw.querySelector('i').style.setProperty('--pulse', pulse ? 1.8 : 1);

    cap2.textContent = off ? (t >= T.queued ? 'queued · will publish on reconnect' : 'offline') : (t >= T.tvFlip2 ? 'published from the queue' : 'live');
  }

  return {
    mount,
    play() {},
    pause() {},
    reset(state) { frame(state === 'end' ? T.done : 0); },
    tick(now, dt, t) { frame(t); },
    setProgress() {},
    resize() {},
  };
}
