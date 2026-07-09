---
name: spendly-ui-designer
description: Generates modern, production-ready UI pages and components for Spendly, a Flask/Jinja2 personal expense tracker (github.com/campusx-official/spendly). Use this skill whenever the user asks to design, create, build, redesign, or improve a page or component for Spendly, or for an expense-tracker app that shares its stack — even if they just say "design the ___ page," "create UI for ___," "build a component for ___," or "redesign/improve ___" without naming Spendly explicitly. Always trigger for any frontend/HTML/CSS work inside a Spendly-style Flask project. Covers matching an existing design system, writing clean Jinja2 templates and vanilla CSS, and choosing appropriate icons — do not treat this as generic web design; the project has hard tech constraints (no React, no npm, no CSS frameworks) that must be respected.
---

# Spendly UI Designer

Generates modern, clean, production-ready UI for Spendly — a personal expense
tracker built with **Flask + Jinja2 + vanilla CSS + vanilla JS**. No React,
no npm, no Tailwind/Bootstrap. The project intentionally keeps the frontend
plain, so "modern" here means good typography, spacing, and layout — not a
JS framework.

## Step 0: Figure out if the real repo is present

Before doing anything else, check whether you're actually working inside a
Spendly (or Spendly-derived) checkout:

- Look for `CLAUDE.md`, `app.py`, `templates/base.html`, and `static/css/style.css`
  in the working directory or a nearby repo root.
- If found → **repo mode**: read the real files (Step 1) and generate code
  that slots directly into the project.
- If not found → **standalone mode**: no project to inspect. Use the fallback
  design tokens in this file (they mirror the real Spendly system) and say so
  briefly, e.g. "I don't see the Spendly repo here, so I'm using its known
  design system from memory — let me know if yours has diverged." Still
  produce full Jinja2 + CSS output, not a generic mockup.

## Step 1: Read before you design (repo mode)

Never invent styles when the real ones are one `view` call away. Before
writing any code:

1. Read `templates/base.html` — layout shell, nav, footer, block structure.
2. Read `static/css/style.css` — the `:root` design tokens (colors, fonts,
   radii, spacing).
3. Find the **closest existing template + CSS pair** to what you're building
   (e.g. building a new "budgets" page? `profile.html` + `profile.css` is the
   closest analog — dashboard-style with cards and a stats row). Read both.
4. If the user references a page/component that doesn't clearly map to
   anything existing and no screenshots/description were given, ask for a
   screenshot or short description of the current look before generating —
   per the consistency rule below. Don't guess at a fundamentally different
   visual style.

Skipping this step is the single biggest way to produce output that looks
"off-brand" — inconsistent radius, wrong font, wrong spacing scale.

## Design tokens (fallback — verify against real `style.css` in repo mode)

```css
--ink: #0f0f0f;            --paper: #f7f6f3;
--ink-soft: #2d2d2d;       --paper-warm: #f0ede6;
--ink-muted: #6b6b6b;      --paper-card: #ffffff;
--ink-faint: #a0a0a0;      --border: #e4e1da;
--accent: #1a472a;         --border-soft: #eeebe4;
--accent-light: #e8f0eb;   --danger: #c0392b;
--accent-2: #c17f24;       --danger-light: #fdecea;
--accent-2-light: #fdf3e3;

--font-display: 'DM Serif Display', Georgia, serif;  /* headings only */
--font-body: 'DM Sans', system-ui, sans-serif;       /* everything else */

--radius-sm: 6px;   --radius-md: 12px;   --radius-lg: 20px;
--max-width: 1200px;
```

Character: warm "paper" fintech look — off-white paper background, near-black
ink text, deep green accent, mustard secondary accent. Serif display font for
titles only, sans for body/UI. Not a cold blue/gray SaaS look, not dark mode.

Category color tokens (extend as needed, following the same pattern):
`--cat-food` (green/accent), `--cat-transport` (mustard/accent-2),
`--cat-bills` (`#5b7fa6`), `--cat-health` (`#b94040`),
`--cat-entertainment` (`#8b5e83`), `--cat-other` (`--ink-faint`) — each paired
with a `-bg` tint for badges.

## Design rules

- **Spacing**: work on an 8px grid (0.5rem increments). No arbitrary values.
- **Cards**: `--paper-card` background, `1px solid var(--border)`,
  `var(--radius-md)`, subtle shadow (`0 2px 8px rgba(0,0,0,0.04)` for
  content cards, `0 8px 40px rgba(0,0,0,0.06)` for hero/feature elements).
- **Hierarchy**: serif display font for page/section titles only; everything
  interactive or tabular (buttons, table cells, form labels) stays in
  DM Sans. Don't mix this up.
- **Buttons**: reuse `.btn-primary` (solid ink, hover→accent), `.btn-ghost`
  (outlined), `.btn-delete` (danger outline) conventions rather than
  inventing new button classes unless the design genuinely needs a new
  variant.
- **Currency**: ₹ symbol, not $.
- **Avoid clutter**: prefer whitespace and a clear stat row / card grid over
  dense panels. No random one-off colors outside the token system.

## Icons

Icon library: **Lucide**. The repo currently only has a single unicode glyph
(◈) as the brand mark and no icon system otherwise, so pick one of two
Lucide integration paths depending on how many icons the page needs — both
are npm-free and fine under "vanilla JS only":

**CDN script (preferred when a page uses several icons, e.g. a dashboard
with per-category icons, nav icons, empty-state icons):**
```html
<!-- in {% block scripts %} of the page, or once in base.html if most pages need icons -->
<script src="https://unpkg.com/lucide@latest"></script>
<script>lucide.createIcons();</script>
```
Use icons in markup as:
```html
<i data-lucide="utensils" class="cat-icon"></i>
```
Size and color via CSS (`.cat-icon { width: 18px; height: 18px; color: var(--ink-muted); }`) —
Lucide's rendered SVGs inherit `currentColor` by default.

**Inline SVG (preferred for one or two static icons, e.g. a single button
icon, so the page doesn't pull in the whole script for one glyph):**
Paste Lucide's raw `<svg>` markup directly (viewBox + path data,
`stroke="currentColor"`, `fill="none"`), sized 18–20px for inline UI icons.

Do not add a `lucide-react` or other npm/bundler dependency — that violates
the project's "vanilla JS only, no npm packages" rule; both approaches above
avoid that. Use icons purposefully (category markers, empty states, nav
items, button accents) — not decoratively on every element. If `base.html`
already loads the CDN script (check on read), reuse it instead of re-adding
a second `<script>` tag on the new page.

## Tech constraints (hard rules, not preferences)

- Flask + Jinja2 templates only. No blueprints — routes stay in `app.py` if
  you're also asked to wire one up.
- Vanilla CSS only — no Tailwind, Bootstrap, or CSS-in-JS. New page → new
  `static/css/<page>.css` file, linked via a `{% block head %}` in that
  template, never inline `<style>`.
- Vanilla JS only — no React/Vue/jQuery, no npm packages. If interactivity is
  needed, write plain JS, ideally appended to `static/js/main.js` or a
  page-specific script block.
- Every internal link uses `{{ url_for(...) }}` — never a hardcoded path.
- New template extends `base.html` and fills `{% block content %}`.

## Output format

Structure every response as:

1. **UI structure (brief)** — the page's layout in a few lines: key sections
   top to bottom, and 1-3 sentences on the important UX decisions (why a
   stat row, why a table vs. cards, etc.). Not a full spec — just enough to
   orient before the code.
2. **Code** — the actual files:
   - `templates/<name>.html` (or the component snippet if editing an
     existing page)
   - `static/css/<name>.css`
   - Any JS needed, clearly marked with where it goes
   Write real, complete, ready-to-drop-in code — not pseudocode or partial
   snippets with "... rest of the page here."
3. Nothing else. Don't restate the design rules back at the user or pad the
   response with a summary of what you just did.

## Consistency rule

Match the existing project design over generic "modern SaaS" defaults. If a
request is ambiguous or seems to call for a visual direction that doesn't
match what's in `style.css` / the closest existing page, say so and ask for
a screenshot or short description of the current look rather than guessing.

## Avoid

- Generic, dated-looking UI (heavy gradients, drop shadows everywhere,
  default browser form styling, Bootstrap-esque defaults).
- Unstructured code dumps — no inline styles, no giant single CSS file with
  no sectioning, no skipping the design tokens.
- Introducing a JS framework, CSS framework, or npm dependency to hit a
  visual effect — solve it in vanilla CSS/JS instead.
- Reproducing copyrighted icon libraries' full package — inline only the
  specific SVGs needed.