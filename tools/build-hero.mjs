// Builds the hero page by inlining the rendered orbs into the template.
//
//   node tools/build-hero.mjs
//
// Reads  tools/hero.template.html  +  assets/3d/world-*.webp
// Writes specimen-drift.html       (self-contained, no external requests)
//
// Each orb's base64 is emitted ONCE as a CSS class (.w0 - .w4) rather than
// per-slot in markup. Ten slots share five images, so inlining per <img> would
// double the page size. The orbs are background-image divs, not <img>, because
// a host stylesheet's `img { max-width: 100% }` resolves against the
// zero-width .ring and collapses every orb to 0x0.

import { readFileSync, writeFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

// order matters: this is the slot order Dirt uses around the ring
// A world is [name, label] plus an optional 'video' flag. Video-backed worlds
// are NOT inlined: a base64 webm would add most of a megabyte to the page for
// one orb, so they are referenced as files and the page stops being
// self-contained.
// The ring is the Blender-rendered set now. Two rounds of pruning got here:
// first the five painted stills (acid, bloom, liquid, plant, chrome-cluster),
// which sat dead among orbs that turn, then the three celestial ones (earth,
// sun, blackhole) left over from the space version of this page. Every asset
// is still in assets/3d/ -- any of them comes back by re-adding its line.
const WORLDS = [
  ['world-phones',         'Chrome phones', 'video'],
  ['world-smoke',          'Smoke handshake', 'video'],
  ['world-brain',          'Neural brain', 'video'],
  ['world-marks',          'Question and answer', 'video'],
];

// One slot per world, and the step follows. This used to be a hardcoded 10 with
// 36deg written into both the CSS and the JS of the template; adding an
// eleventh world silently dropped it off the ring, because slot i took
// WORLDS[i % length] and i never reached 10.
// At least ten slots, whatever the world count. The step is 360/SLOTS, and a
// slot turned much past ~40deg is nearly edge-on to the lens -- with four
// worlds in four slots the step is 90deg and the neighbours collapse to zero
// width, leaving one orb alone on the page. Repeating a short list around a
// fuller ring is what keeps every slot facing the viewer.
const SLOTS = Math.max(WORLDS.length, 10);
const STEP = +(360 / SLOTS).toFixed(4);

let html = readFileSync(join(root, 'tools/hero.template.html'), 'utf8');

const css = WORLDS.map(([name, , kind], i) => {
  if (kind === 'video') return null;               // nothing to inline
  const b64 = readFileSync(join(root, `assets/3d/${name}.webp`)).toString('base64');
  return `  .w${i}{ background-image:url(data:image/webp;base64,${b64}) }`;
}).filter(Boolean).join('\n');

// The bob's duration and delay are set at runtime, not here: they follow
// the entry delay, so the page owns them.
const slots = Array.from({ length: SLOTS }, (_, i) => {
  const k = i % WORLDS.length;
  const [name, label, kind] = WORLDS[k];
  const face = kind === 'video'
    ? `<video class="orbimg orbvid" src="assets/3d/${name}.webm" ` +
      `poster="assets/3d/${name}.webp" autoplay loop muted playsinline preload="auto" ` +
      `disablepictureinpicture aria-label="${label}"></video>`
    : `<div class="orbimg w${k}" role="img" aria-label="${label}"></div>`;
  return `    <div class="slot" style="--i:${i}">` +
         `<div class="slot__f">` + face + `</div></div>`;
}).join('\n');

html = html.replace('{{IMGCSS}}', css)
           .replace('{{SLOTS}}', slots)
           .replaceAll('{{STEP}}', String(STEP));

if (html.includes('{{')) throw new Error('template still has unreplaced placeholders');

const out = join(root, 'specimen-drift.html');
writeFileSync(out, html);
console.log(`built ${out} - ${(statSync(out).size / 1024).toFixed(0)} KB, ${SLOTS} slots, ${WORLDS.length} orbs`);
