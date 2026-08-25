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
const WORLDS = [
  ['world-acid',           'Acid grid world'],
  ['world-bloom',          'Glowing bloom world'],
  ['world-liquid',         'Marbled liquid world'],
  ['world-plant',          'Chrome plant world'],
  ['world-chrome-cluster', 'Chrome cluster world'],
  ['world-earth',          'Rotating Earth', 'video'],
];

const SLOTS = 10;   // 36 degrees apart; with six worlds, Earth lands once and the rest twice

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

html = html.replace('{{IMGCSS}}', css).replace('{{SLOTS}}', slots);

if (html.includes('{{')) throw new Error('template still has unreplaced placeholders');

const out = join(root, 'specimen-drift.html');
writeFileSync(out, html);
console.log(`built ${out} - ${(statSync(out).size / 1024).toFixed(0)} KB, ${SLOTS} slots, ${WORLDS.length} orbs`);
