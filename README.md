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
