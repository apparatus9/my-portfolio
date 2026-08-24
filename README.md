# Portfolio

A single-page portfolio for showing client work. No build step, no
dependencies — `index.html` is the whole site.

Branded as **Omada**, speaking in a solo "I" voice. To swap in a full name,
search `index.html` for `Omada` (page title, JSON-LD, nav, footer) and change
the `O` logo mark in the nav and favicon.

## Quick facts

- **Email:** omada008@gmail.com (contact section + footer)
- **Phone:** commented out in the Contact section — uncomment to show it
- **Location:** `Toronto, Canada` appears in the hero badge, About facts, and footer
- The hero badge says *"Available for new projects"* — change or delete it when booked.

## Preview it locally

```bash
npx serve@latest -l 5180 .
```

Then open <http://localhost:5180>.

You can also just double-click `index.html` — everything works offline except the
Google Fonts request, which falls back to a system font.

## Deploy it

Easiest is Vercel:

```bash
npm i -g vercel
vercel          # preview URL
vercel --prod   # live
```

Any static host works too — Netlify, Cloudflare Pages, or GitHub Pages. Upload the
folder as-is.

> After deploying, set the `og:image` meta tag in `index.html` to an absolute
> URL (e.g. `https://your-domain.com/assets/dream-wheels.jpg`) so link previews
> work on social platforms and in messengers.

## What's in here

```
index.html                 the entire site
assets/dream-wheels.jpg    screenshot — Dream Wheels Fest 2026
assets/empire-fitness.jpg  screenshot — Empire Fitness redesign
assets/golden-mile-team.jpg screenshot — Golden Mile team page
```

The three screenshots are real captures of the live projects. The other project
cards use a styled gradient panel instead, since those repos are private and had
no public URL to capture.

## Adding a screenshot to a project

Drop the image in `assets/`, then find that project's card in `index.html` and
replace this:

```html
<div class="thumb thumb-gen">
  <div>
    <div class="gen-mark">Project Name</div>
    <div class="gen-sub">Subtitle</div>
  </div>
</div>
```

with this:

```html
<div class="thumb">
  <img src="assets/your-screenshot.jpg" alt="Description of the page">
</div>
```

## Notes

- Private client repos are shown as case studies with no links, which is normal
  for client work. Each is labelled so it's clear why there's no link.
- The team page screenshot was cropped to remove staff emails and phone
  extensions before it went in `assets/`.
- Layout is responsive: two-column work grid on desktop, single column below
  760px, with a full-screen burger menu replacing the nav links on small screens.
- SEO extras baked in: Open Graph / Twitter card tags, an inline SVG favicon,
  and JSON-LD `ProfessionalService` structured data.
- All animations (particles, tilt, cursor, marquee, reveals) are vanilla JS/CSS,
  disabled automatically for `prefers-reduced-motion` and touch devices where
  appropriate.

## 3D hero experiment (`specimen-drift.html`)

A drag-to-slide carousel of five "orb worlds", built after studying how
[dirtverse.co](https://dirtverse.co) does its header. It is a **separate page**,
not yet wired into `index.html`.

The geometry is a cylinder: ten slots, 36° apart, each pushed out along a
**negative** `translateZ`. That sign is the whole trick — it puts the *centred*
orb furthest away, so it sits small and calm while orbs swell as they swing
outward. Pushing the ring forward instead crowds everything into a jammed band.

```css
.ring { transform: rotateY(var(--spin)) }
.slot { transform: rotateY(calc(var(--i) * 36deg)) translateZ(-1150px) }
```

Drag spins it, a flick coasts on friction, then it snaps to the nearest slot.

### Regenerating the orbs

The orbs are rendered in-browser with three.js — no Blender, no stock assets.
Serve the repo and open the rig; it renders each world and POSTs the PNGs back
to `assets/3d/`, so it needs a server that accepts writes (see git history for
the throwaway one used).

```
tools/render-worlds.html      the five shipped orbs
tools/render-organisms.html   translucent creature set (unused)
tools/render-organic.html     fur / iridescence experiments (unused)
tools/render-shapes.html      smooth primitives (unused)
tools/drag-physics-demo.html  minimal spring-drag reference
```

Each world is a painted background plus 3D content, rendered square, then cut to
a circle in 2D canvas with sphere shading and a specular highlight composited on
top. A domain-warped noise displacement is baked into the pixels — **alpha
included**, which is what melts the circular edge into a bead of liquid.

Then convert to WebP and rebuild the page:

```bash
cd assets/3d && for f in world-*.png; do
  ffmpeg -y -i "$f" -c:v libwebp -q:v 84 -compression_level 6 "${f%.png}.webp"
done
cd ../.. && node tools/build-hero.mjs
```

### Two gotchas worth remembering

**Don't use `<img>` for the orbs.** A host stylesheet's `img { max-width: 100% }`
resolves against the zero-width `.ring` and collapses every orb to 0×0. They are
`background-image` divs for that reason.

**Don't inline the same asset twice.** Ten slots share five images; emitting the
base64 per-slot doubled the page to 524 KB. The build script emits each payload
once as a CSS class — 269 KB.

The filename `specimen-drift.html` is historical and kept deliberately: a
published artifact is bound to it, and renaming the file would break that link.
