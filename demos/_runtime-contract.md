# Demo runtime contract

Every file in `demos/` is an ES module that the tile runtime in `demos/runtime.js`
lazy-imports when its root scrolls within one viewport. `work.html` loads the
runtime and mounts the demos inside its project cards.

## Markup (in work.html)

```html
<div class="tile" data-demo="lsd" data-mode="loop"
     role="img" aria-label="Animated demonstration of …"
     style="aspect-ratio:16/9.5"></div>
```

## Module shape

```js
export const meta = {
  id: 'lsd',
  mode: 'loop',      // 'loop' | 'scrub' | 'interactive' | 'css'
  duration: 9200,    // loop: ms per cycle — the runtime wraps t for you
  slots: 1           // cost against the active budget (2). CSS-kind tiles cost 0.
};

export default function create(root, ctx) {
  return {
    mount(),            // sync, < 10 ms. Build DOM into root; ctx.css(id, text) injects styles once.
    play(),             // add will-change on the few moving nodes; enter live state
    pause(),            // remove will-change; freeze where you are (do NOT reset)
    reset(state),       // 'start' | 'end'. 'end' = the resolved static state (reduced-motion / no loop)
    tick(now, dt, t),   // loop/interactive only. dt ≤ 50 ms; t = ms within the loop [0, duration)
    setProgress(p),     // scrub only. p ∈ [0,1]; called only when |Δp| ≥ .002
    resize(w, h),       // optional; one ResizeObserver on root
    destroy()           // optional
  };
}
// ctx = { reduced, fine, coarse, probe(url) => Promise<boolean>, css(id, text), dev }
```

## Rules

- **No** `requestAnimationFrame`, `setTimeout`, `setInterval`, or unconditional `@keyframes`
  inside a demo. The runtime owns time. CSS-kind tiles write keyframes as `.root.is-live …`.
- `tick` / `setProgress` write only transforms, opacity, CSS custom properties, and
  `textContent`. **Zero layout reads** in the hot path — measure in `mount` / `resize`.
- Consume only the semantic tokens: `--bg --bg-2 --fg --fg-2 --fg-3 --rule --rule-2 --ac --ac-2 --surface --ok-c --hot`.
  Never reference `--paper`/`--ink` directly; the tile must look right in both scopes.
- Scope every selector under the root class (`.lsd …`).
- Decorative: no focusable elements inside a `role="img"` root.
- Fictional data only — no real people, real IDs, real licence numbers.

## Testing

`demos/dev.html?demo=lsd` mounts one tile with the old site.js runtime (the
untracked redesign); `work.html?debug=tiles` exposes `window.__tiles.stats()`.
Add `&rm=1` to force reduced motion, `&light=1` to mount outside `.theatre`.
`?debug=tiles` on any page shows the HUD (active set, tick counts, frame dt p95).
