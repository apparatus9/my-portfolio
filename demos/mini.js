/* ============================================================
   mini — five micro-scenes for the project index
   mode: css · slots: 0

   One module, five scenes chosen by data-scene on the tile root.
   Each is a single ~5 s CSS loop that only runs while the tile is
   on screen (the runtime toggles .is-live).
   ============================================================ */

export const meta = { id: 'mini', mode: 'css', duration: 5000, slots: 0 };

const CSS = `
.mini-in{position:absolute;inset:0;display:grid;place-items:center;font-family:var(--mono);color:var(--fg);overflow:hidden;
  background:repeating-linear-gradient(90deg,var(--rule) 0 1px,transparent 1px 34px)}
.mini-in *{box-sizing:border-box}
.mini .lab{position:absolute;left:10px;top:9px;font-size:7.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3)}

/* ttc — price tag flips to employee pricing */
.ttc-tag{position:relative;width:62%;aspect-ratio:2.6;perspective:600px}
.ttc-face{position:absolute;inset:0;border-radius:6px;border:1px solid var(--rule-2);background:var(--surface);padding:8% 10%;display:flex;flex-direction:column;justify-content:center;gap:4px;backface-visibility:hidden}
.ttc-face .k{font-size:7px;letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3)}
.ttc-face .v{font-family:var(--serif);font-size:clamp(16px,2.4vw,24px);letter-spacing:-.01em;color:var(--fg)}
.ttc-face.back{transform:rotateX(180deg);border-color:var(--ac);background:color-mix(in srgb,var(--ac) 14%,transparent)}
.ttc-face.back .v{color:var(--ac-2)}
.ttc-face.back .v s{color:var(--fg-3);font-size:.55em;margin-right:.4em}
.ttc-flip{position:absolute;inset:0;transform-style:preserve-3d}
.mini.is-live .ttc-flip{animation:ttc-flip 5s cubic-bezier(.3,1.3,.4,1) infinite}
@keyframes ttc-flip{0%,28%{transform:rotateX(0)}45%,82%{transform:rotateX(180deg)}100%{transform:rotateX(360deg)}}

/* ccaga — member card unlocks a gated panel */
.cc-wrap{position:relative;width:70%;aspect-ratio:2.1}
.cc-panel{position:absolute;inset:0;border-radius:6px;border:1px dashed var(--rule-2);display:grid;place-items:center;text-align:center;font-size:7.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--fg-3);overflow:hidden}
.cc-panel b{display:block;font-family:var(--serif);font-size:clamp(12px,1.8vw,18px);letter-spacing:0;text-transform:none;color:var(--fg);margin-top:4px;opacity:0;transform:translateY(6px)}
.cc-panel .lock{font-size:14px;transition:.3s}
.cc-card{position:absolute;left:-6%;bottom:-14%;width:42%;aspect-ratio:1.6;border-radius:5px;background:linear-gradient(135deg,#1f3a2b,#0e2b1e);border:1px solid var(--ac);padding:7%;font-size:6.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ac-2);
  transform:translateX(-120%) rotate(-8deg);box-shadow:0 16px 30px -14px rgba(0,0,0,.8)}
.cc-card i{display:block;font-style:normal;font-family:var(--serif);font-size:11px;letter-spacing:0;text-transform:none;color:#fff;margin-top:6px}
.mini.is-live .cc-card{animation:cc-card 5s var(--ease) infinite}
.mini.is-live .cc-panel .lock{animation:cc-lock 5s steps(1) infinite}
.mini.is-live .cc-panel b{animation:cc-reveal 5s var(--ease) infinite}
.mini.is-live .cc-panel{animation:cc-panel 5s var(--ease) infinite}
@keyframes cc-card{0%{transform:translateX(-120%) rotate(-8deg)}22%,85%{transform:translateX(0) rotate(-8deg)}100%{transform:translateX(-120%) rotate(-8deg)}}
@keyframes cc-lock{0%,30%{content:"🔒"}31%,100%{content:"🔓"}}
@keyframes cc-panel{0%,30%{border-style:dashed;border-color:var(--rule-2)}36%,85%{border-style:solid;border-color:var(--ac)}100%{border-style:dashed;border-color:var(--rule-2)}}
@keyframes cc-reveal{0%,32%{opacity:0;transform:translateY(6px)}42%,85%{opacity:1;transform:none}100%{opacity:0}}

/* service — coupon tears along the perforation */
.sv-coupon{position:relative;width:58%;aspect-ratio:1.7;font-size:7px}
.sv-top,.sv-bot{position:absolute;left:0;right:0;background:var(--surface);border:1px solid var(--rule-2);padding:8% 9%}
.sv-top{top:0;height:62%;border-radius:6px 6px 0 0;border-bottom:1px dashed var(--rule-2);display:flex;flex-direction:column;justify-content:center;gap:3px}
.sv-top .k{letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3)}
.sv-top .v{font-family:var(--serif);font-size:clamp(14px,2.2vw,22px);color:var(--fg)}
.sv-top .v b{color:var(--ac-2);font-weight:400}
.sv-bot{bottom:0;height:38%;border-radius:0 0 6px 6px;border-top:0;display:flex;align-items:center;justify-content:space-between;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-2);transform-origin:0 0}
.sv-bot i{font-style:normal;color:var(--ac-2)}
.mini.is-live .sv-bot{animation:sv-tear 5s cubic-bezier(.4,0,.2,1) infinite}
@keyframes sv-tear{0%,40%{transform:none;opacity:1}58%{transform:rotate(9deg) translateY(10%)}70%{transform:rotate(14deg) translate(6%,70%);opacity:0}71%,100%{transform:none;opacity:0}90%,100%{opacity:1}}

/* recon — a vehicle moves across the kanban */
.rc-board{position:relative;width:82%;display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:6.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-3)}
.rc-col{border:1px solid var(--rule);border-radius:5px;padding:7px 6px;min-height:64px;display:flex;flex-direction:column;gap:6px}
.rc-col.on{border-color:var(--ac)}
.rc-chip{height:16px;border-radius:3px;background:color-mix(in srgb,var(--fg) 10%,transparent);border:1px solid var(--rule)}
.rc-car{position:absolute;left:0;top:24px;width:calc(25% - 4.5px);height:16px;border-radius:3px;background:var(--ac);color:var(--bg);display:grid;place-items:center;font-size:6.5px;letter-spacing:.08em;font-weight:700;text-transform:none}
.mini.is-live .rc-car{animation:rc-move 5s cubic-bezier(.6,0,.2,1) infinite}
@keyframes rc-move{0%,18%{left:0}25%,43%{left:calc(25% + 1.5px)}50%,68%{left:calc(50% + 3px)}75%,93%{left:calc(75% + 4.5px)}100%{left:0}}

/* rewards — counter ticks, claim pulses */
.rw{display:flex;flex-direction:column;align-items:center;gap:10px}
.rw .n{font-family:var(--serif);font-size:clamp(22px,3.4vw,34px);letter-spacing:-.01em;color:var(--fg);display:flex;align-items:baseline;gap:6px}
.rw .n small{font-family:var(--mono);font-size:8px;letter-spacing:.2em;color:var(--ac-2)}
.rw .n b{font-weight:400;display:inline-block;min-width:3.2ch;text-align:right}
.rw .btn{font-size:7.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--bg);background:var(--ac-2);border-radius:100px;padding:6px 14px}
.mini.is-live .rw .btn{animation:rw-pulse 5s ease-in-out infinite}
.mini.is-live .rw .n b{animation:rw-count 5s steps(1) infinite}
@keyframes rw-pulse{0%,55%{box-shadow:0 0 0 0 color-mix(in srgb,var(--ac-2) 50%,transparent)}65%{box-shadow:0 0 0 10px transparent;transform:scale(1.06)}75%,100%{transform:none;box-shadow:0 0 0 0 transparent}}
@keyframes rw-count{0%{content:"0.000"}10%{content:"0.007"}20%{content:"0.015"}30%{content:"0.024"}40%{content:"0.033"}50%{content:"0.042"}60%,100%{content:"0.042"}}
.rw .n b::after{content:"0.042"}
.mini.is-live .rw .n b::after{animation:rw-count 5s steps(1) infinite}
`;

const SCENES = {
  ttc: `<span class="lab">Employee pricing</span><div class="ttc-tag"><div class="ttc-flip">
          <div class="ttc-face"><span class="k">2026 Grand Cherokee · MSRP</span><span class="v">$54,995</span></div>
          <div class="ttc-face back"><span class="k">TTC employee price</span><span class="v"><s>$54,995</s>$49,450</span></div>
        </div></div>`,
  ccaga: `<span class="lab">Members only</span><div class="cc-wrap">
          <div class="cc-panel"><div><span class="lock">🔒</span><b>Exclusive member pricing unlocked</b></div></div>
          <div class="cc-card">CCAGA member<i>Card № 4471</i></div>
        </div>`,
  service: `<span class="lab">Service specials</span><div class="sv-coupon">
          <div class="sv-top"><span class="k">Synthetic oil change</span><span class="v"><b>$49.95</b> · was $89</span></div>
          <div class="sv-bot"><span>Code <i>SPRING-49</i></span><span>✂ tear</span></div>
        </div>`,
  recon: `<span class="lab">Reconditioning</span><div class="rc-board">
          <div class="rc-col">Intake<span class="rc-chip"></span></div>
          <div class="rc-col">Detail<span class="rc-chip"></span><span class="rc-chip"></span></div>
          <div class="rc-col">Photo</div>
          <div class="rc-col">Live<span class="rc-chip"></span></div>
          <div class="rc-car">STK 8813</div>
        </div>`,
  rewards: `<span class="lab">Reward apps</span><div class="rw">
          <div class="n"><b></b><small>SOL</small></div>
          <div class="btn">Claim</div>
        </div>`,
};

export default function create(root, ctx) {
  ctx.css('mini', CSS);
  return {
    mount() {
      root.classList.add('mini');
      root.innerHTML = `<div class="mini-in" aria-hidden="true">${SCENES[root.dataset.scene] || ''}</div>`;
    },
    play() { if (!ctx.reduced) root.classList.add('is-live'); },
    pause() { root.classList.remove('is-live'); },
    reset() {},
    tick() {},
    setProgress() {},
    resize() {},
  };
}
