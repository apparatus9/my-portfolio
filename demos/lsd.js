/* ============================================================
   lsd — Licence Scanner replay
   mode: loop · 9.2 s

   A scripted replay that reads as machine vision: a (fictional)
   licence tilts in, a scan sweeps it, the PDF417 barcode locks
   first — that is the real product's primary path — then six
   OCR field boxes snap on with confidences, values type into a
   data panel, barcode ⇄ OCR cross-check, VALIDATED stamp, reset.
   No real OCR runs. Nothing here is a real person or a real ID.
   ============================================================ */

export const meta = { id: 'lsd', mode: 'loop', duration: 9200, slots: 1 };

const CSS = `
.lsd-in{position:absolute;inset:0;display:grid;grid-template-columns:1.15fr 1fr;gap:4%;padding:6% 5%;
  font-family:var(--mono);color:var(--fg);
  background:
    repeating-linear-gradient(0deg,var(--rule) 0 1px,transparent 1px 42px),
    repeating-linear-gradient(90deg,var(--rule) 0 1px,transparent 1px 42px);
  background-color:transparent}
.lsd *{box-sizing:border-box}

/* ---- card ---- */
.lsd-cardwrap{position:relative;perspective:1200px;display:grid;place-items:center}
.lsd-card{
  position:relative;width:100%;aspect-ratio:1.586;border-radius:10px;overflow:hidden;
  background:linear-gradient(135deg,#f4efe4 0%,#e9e1d1 55%,#dfd5c2 100%);color:#1b1610;
  box-shadow:0 30px 60px -24px rgba(0,0,0,.7);
  transform:rotateY(var(--cy,-28deg)) rotateX(var(--cx,10deg)) translateX(var(--tx,-18%));opacity:var(--co,0);
  transition:transform .9s var(--ease),opacity .6s var(--ease);
}
.lsd-card::after{ /* hologram sheen */
  content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.55) 46%,rgba(180,140,255,.25) 52%,transparent 62%);
  transform:translateX(var(--sheen,-60%));transition:transform 1.4s var(--ease);
}
.lsd-card .hdr{position:absolute;left:5%;top:6%;right:5%;display:flex;justify-content:space-between;font-size:7.5px;letter-spacing:.18em;text-transform:uppercase;color:#4a3f2f}
.lsd-card .hdr b{color:#7e621f}
.lsd-card .photo{position:absolute;left:5%;top:20%;width:21%;aspect-ratio:3/4;border-radius:4px;background:#cfc4ad;overflow:hidden}
.lsd-card .photo::before{content:"";position:absolute;left:50%;top:22%;width:38%;aspect-ratio:1;border-radius:50%;background:#8e8270;transform:translateX(-50%)}
.lsd-card .photo::after{content:"";position:absolute;left:50%;bottom:-10%;width:78%;aspect-ratio:1;border-radius:50%;background:#8e8270;transform:translateX(-50%)}
.lsd-card .f{position:absolute;font-size:8.5px;line-height:1.15}
.lsd-card .f i{display:block;font-style:normal;font-size:6px;letter-spacing:.16em;text-transform:uppercase;color:#7e7563;margin-bottom:2px}
.lsd-card .f b{font-weight:500;color:#1b1610;white-space:nowrap}
.lsd-card .bar{position:absolute;left:5%;right:5%;bottom:7%;height:16%;display:grid;grid-template-columns:repeat(60,1fr);gap:1px;opacity:.85}
.lsd-card .bar i{background:#1b1610;display:block}
.lsd-card .sig{position:absolute;right:6%;top:20%;width:20%;height:8%;border-bottom:1px solid #7e7563;font-family:var(--serif);font-style:italic;font-size:9px;color:#4a3f2f;text-align:center}

/* scan line */
.lsd-scan{
  position:absolute;left:-2%;right:-2%;top:calc(var(--sy,0) * 100%);height:2px;z-index:3;
  background:var(--ac-2);box-shadow:0 0 14px var(--ac-2),0 0 2px #fff;opacity:var(--so,0);
}
.lsd-scan::after{content:"";position:absolute;left:0;right:0;top:2px;height:46px;background:linear-gradient(to bottom,color-mix(in srgb,var(--ac-2) 30%,transparent),transparent)}

/* detection boxes */
.lsd-box{
  position:absolute;left:calc(var(--x)*100%);top:calc(var(--y)*100%);width:calc(var(--w)*100%);height:calc(var(--h)*100%);
  z-index:4;opacity:var(--bo,0);transform:scale(calc(1.25 - var(--bo,0) * .25));transition:opacity .18s,transform .18s cubic-bezier(.2,1.4,.4,1);
}
.lsd-box::before,.lsd-box::after,.lsd-box i::before,.lsd-box i::after{
  content:"";position:absolute;width:9px;height:9px;border:1.5px solid var(--hot);
}
.lsd-box::before{left:-2px;top:-2px;border-right:0;border-bottom:0}
.lsd-box::after{right:-2px;top:-2px;border-left:0;border-bottom:0}
.lsd-box i::before{left:-2px;bottom:-2px;border-right:0;border-top:0}
.lsd-box i::after{right:-2px;bottom:-2px;border-left:0;border-top:0}
.lsd-box i{position:absolute;inset:0;display:block}
.lsd-box .c{position:absolute;right:-2px;top:-14px;font-size:7px;letter-spacing:.12em;color:var(--hot);background:color-mix(in srgb,var(--bg) 80%,transparent);padding:1px 4px;border-radius:2px}
.lsd-box.bar{--x:.05;--y:.77;--w:.9;--h:.16}
.lsd-box.bar::before,.lsd-box.bar::after,.lsd-box.bar i::before,.lsd-box.bar i::after{border-color:var(--ok-c)}
.lsd-box.bar .c{color:var(--ok-c)}
.lsd-box.ok::before,.lsd-box.ok::after,.lsd-box.ok i::before,.lsd-box.ok i::after{border-color:var(--ok-c)}

/* validated stamp */
.lsd-stamp{
  position:absolute;right:6%;top:26%;z-index:5;transform:rotate(-12deg) scale(var(--ss,3));opacity:var(--sto,0);
  transition:transform .35s cubic-bezier(.2,1.6,.4,1),opacity .2s;
  border:2px solid var(--ok-c);color:var(--ok-c);border-radius:6px;padding:6px 12px;
  font-family:var(--serif);font-style:italic;font-size:20px;letter-spacing:.02em;background:color-mix(in srgb,var(--bg) 55%,transparent);
}

/* ---- data panel ---- */
.lsd-panel{display:flex;flex-direction:column;justify-content:center;gap:10px;min-width:0}
.lsd-panel .ttl{font-size:9px;letter-spacing:.22em;text-transform:uppercase;color:var(--fg-3);display:flex;justify-content:space-between;align-items:center}
.lsd-panel .ttl em{font-style:normal;color:var(--ok-c);opacity:var(--lo,0)}
.lsd-panel .ttl em::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--ok-c);margin-right:6px;vertical-align:1px}
.lsd-row{display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:baseline;border-bottom:1px solid var(--rule);padding:7px 0;font-size:11px;opacity:var(--ro,.35);transition:opacity .3s}
.lsd-row i{font-style:normal;font-size:8px;letter-spacing:.18em;text-transform:uppercase;color:var(--fg-3)}
.lsd-row b{font-weight:500;color:var(--fg);min-height:1.2em;white-space:nowrap;overflow:hidden;text-overflow:clip;font-family:var(--serif);font-size:14px;letter-spacing:.01em}
.lsd-row b::after{content:"";display:inline-block;width:1px;height:1em;background:var(--ac-2);margin-left:2px;vertical-align:-2px;opacity:var(--caret,0)}
.lsd-xc{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-2);margin-top:6px;opacity:var(--xo,0);transform:translateY(calc((1 - var(--xo,0)) * 6px));transition:opacity .35s,transform .35s}
.lsd-xc b{color:var(--ok-c)}
.lsd-pill{
  align-self:flex-start;margin-top:8px;border:1px solid var(--ok-c);color:var(--ok-c);border-radius:100px;padding:6px 12px;
  font-size:9px;letter-spacing:.18em;text-transform:uppercase;opacity:var(--po,0);transform:translateY(calc((1 - var(--po,0)) * 8px));transition:opacity .3s,transform .3s;
}

@media (max-width:640px){
  .lsd-in{grid-template-columns:1fr;grid-template-rows:auto 1fr;gap:14px;padding:6% 6% 5%}
  .lsd-panel{gap:4px}
  .lsd-row{padding:4px 0;font-size:10px}
  .lsd-row b{font-size:12px}
  .lsd-stamp{font-size:15px}
}
`;

/* fictional card data */
const FIELDS = [
  { k: 'Name',    v: 'AVERY T. MARCHBANK', x: .31, y: .20, w: .40, h: .13, conf: .98 },
  { k: 'DOB',     v: '1991-04-17',         x: .31, y: .36, w: .20, h: .11, conf: .97 },
  { k: 'Lic. no', v: 'CR-4471-20893-K',    x: .31, y: .50, w: .30, h: .11, conf: .99 },
  { k: 'Class',   v: 'G',                  x: .74, y: .36, w: .10, h: .11, conf: .96 },
  { k: 'Expiry',  v: '2029-08-30',         x: .74, y: .50, w: .20, h: .11, conf: .98 },
  { k: 'Address', v: '12 HARROW LN · ASHFORD VALE', x: .05, y: .665, w: .52, h: .10, conf: .94 },
];

/* timeline (ms) */
const T = {
  cardIn: 0, scanStart: 900, scanEnd: 2100, barLock: 2050,
  fieldsStart: 2500, fieldGap: 330,           // six boxes 2500 → 4150
  typeStart: 2900, typeGap: 330, typeDur: 650, // rows 2900 → 5500
  xcheck: 6300, stamp: 7000, exit: 8400,
};

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = p => 1 - Math.pow(1 - p, 3);
const snap = (t, a, b) => clamp((t - a) / Math.max(b - a, 1), 0, 1);

export default function create(root, ctx) {
  ctx.css('lsd', CSS);

  let card, scan, boxes, barBox, stamp, rows, xc, pill, live;
  let lastPhase = '';

  /* deterministic PDF417-looking pattern */
  function barcode() {
    let s = 7, out = '';
    for (let i = 0; i < 60 * 4; i++) { s = (s * 1103515245 + 12345) & 0x7fffffff; out += `<i style="opacity:${(s >> 8) % 3 ? 1 : .15}"></i>`; }
    return out;
  }

  function mount() {
    root.classList.add('lsd');
    root.innerHTML = `<div class="lsd-in">
      <div class="lsd-cardwrap">
        <div class="lsd-card">
          <div class="hdr"><span><b>Province of Caledon Reach</b> · Driver's Licence</span><span>Class G</span></div>
          <div class="photo"></div>
          ${FIELDS.map(f => `<div class="f" style="left:${f.x * 100 + 1}%;top:${f.y * 100 + 1.5}%"><i>${f.k}</i><b>${f.v}</b></div>`).join('')}
          <div class="sig">A. Marchbank</div>
          <div class="bar">${barcode()}</div>
          <div class="lsd-scan"></div>
          <div class="lsd-box bar"><i></i><span class="c">PDF417 · 0.99</span></div>
          ${FIELDS.map(f => `<div class="lsd-box" style="--x:${f.x};--y:${f.y};--w:${f.w};--h:${f.h}"><i></i><span class="c">0.00</span></div>`).join('')}
          <div class="lsd-stamp">✓ Validated</div>
        </div>
      </div>
      <div class="lsd-panel">
        <div class="ttl"><span>Extracted record</span><em>live</em></div>
        ${FIELDS.map(f => `<div class="lsd-row"><i>${f.k}</i><b></b></div>`).join('')}
        <div class="lsd-xc">barcode ⇄ ocr · <b>6/6 match</b></div>
        <div class="lsd-pill">Export PDF · Save to CRM</div>
      </div>
    </div>`;
    card   = root.querySelector('.lsd-card');
    scan   = root.querySelector('.lsd-scan');
    barBox = root.querySelector('.lsd-box.bar');
    boxes  = [...root.querySelectorAll('.lsd-box:not(.bar)')];
    stamp  = root.querySelector('.lsd-stamp');
    rows   = [...root.querySelectorAll('.lsd-row')];
    xc     = root.querySelector('.lsd-xc');
    pill   = root.querySelector('.lsd-pill');
    live   = root.querySelector('.lsd-panel .ttl');
  }

  function frame(t) {
    /* card in / out */
    const inP = ease(snap(t, T.cardIn, T.cardIn + 900));
    const outP = ease(snap(t, T.exit, T.exit + 600));
    card.style.setProperty('--cy', (-28 + 28 * inP + 22 * outP).toFixed(1) + 'deg');
    card.style.setProperty('--cx', (10 - 10 * inP).toFixed(1) + 'deg');
    card.style.setProperty('--tx', (-18 + 18 * inP + 14 * outP).toFixed(1) + '%');
    card.style.setProperty('--co', (inP * (1 - outP)).toFixed(2));
    card.style.setProperty('--sheen', t > 300 && t < T.exit ? '160%' : '-60%');

    /* scan */
    const sp = snap(t, T.scanStart, T.scanEnd);
    scan.style.setProperty('--sy', sp.toFixed(3));
    scan.style.setProperty('--so', sp > 0 && sp < 1 ? 1 : 0);

    /* barcode lock */
    barBox.style.setProperty('--bo', t >= T.barLock && t < T.exit ? 1 : 0);

    /* field boxes + confidences */
    boxes.forEach((b, i) => {
      const t0 = T.fieldsStart + i * T.fieldGap;
      const on = t >= t0 && t < T.exit;
      b.style.setProperty('--bo', on ? 1 : 0);
      const c = FIELDS[i].conf * ease(snap(t, t0, t0 + 500));
      b.querySelector('.c').textContent = c.toFixed(2);
      b.classList.toggle('ok', t >= t0 + 520);
    });

    /* typing into the panel */
    rows.forEach((r, i) => {
      const t0 = T.typeStart + i * T.typeGap;
      const p = snap(t, t0, t0 + T.typeDur);
      const v = FIELDS[i].v, n = Math.round(v.length * p);
      const b = r.querySelector('b');
      const txt = t >= T.exit ? '' : v.slice(0, n);
      if (b.textContent !== txt) b.textContent = txt;
      r.style.setProperty('--ro', t >= t0 && t < T.exit ? 1 : .35);
      b.style.setProperty('--caret', p > 0 && p < 1 ? 1 : 0);
    });
    live.style.setProperty('--lo', t > T.scanStart && t < T.exit ? 1 : 0);

    /* cross-check, stamp, pill */
    xc.style.setProperty('--xo', t >= T.xcheck && t < T.exit ? 1 : 0);
    const st = t >= T.stamp && t < T.exit;
    stamp.style.setProperty('--sto', st ? 1 : 0);
    stamp.style.setProperty('--ss', st ? 1 : 3);
    pill.style.setProperty('--po', t >= T.stamp + 250 && t < T.exit ? 1 : 0);
  }

  return {
    mount,
    play() { card.style.willChange = 'transform, opacity'; },
    pause() { card.style.willChange = 'auto'; },
    reset(state) {
      if (state === 'end') { root.classList.add('instant'); frame(T.stamp + 600); }
      else frame(0);
    },
    tick(now, dt, t) { frame(t); },
    setProgress() {},
    resize() {},
  };
}
