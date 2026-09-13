---
name: report-design
description: Generate professional AEO audit reports in Stripe style — self-contained HTML with embedded SVG charts plus DOCX with chart images, from a Pandora-AEO JSON run record.
version: 0.1.0
author: Manuel Hernández (zorrovengador), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [reports, charts, svg, docx, html, stripe-design, AEO, pandora-aeo]
    related_skills: [aeo-audit]
---

# Report Design Skill (v0.1)

Turn a Pandora-AEO JSON run record into a client-grade report: a self-contained
interactive HTML with embedded SVG charts, plus a DOCX with the same charts as
images. This skill bundles the visual conventions, chart patterns, QA steps,
and delivery rules so any new Hermes profile produces the same quality without
external design skills.

Pair with `aeo-audit` (the engine + report workflow). This skill covers
**Step 2–6** of the aeo-audit Report Workflow.

## Prerequisites

- Python 3.10+ (stdlib only for HTML generation)
- For the DOCX: `python-docx` (`pip install python-docx`) or the Hermes `docx`
  skill's `docx_create.py`
- Optional QA render: any headless Chromium via CDP (screenshot verification)

## Hard rules (non-negotiable)

1. **REGLA DURA:** NEVER include comparisons with AEO Bizbrain, isitagentready.com,
   or ANY external system in any deliverable (HTML, DOCX, JSON, PDF, PPTX).
   Only facts measured by Pandora-AEO: category scores, pages, impact/effort
   findings, Agent Readiness, action plan.
2. **Full crawl only.** `--crawl --max-pages 2000` — never present a sample
   (e.g. 30 pages) as if it were the site. State both counts when crawler
   discovery is smaller than the sitemap (dedupe http/https and URL variants).
3. **Escape all dynamic strings.** Engine evidence can contain `<`, quotes, and
   brackets. Unescaped injection breaks the HTML mid-document (real bug:
   the report truncated at the findings section). Use `html.escape(x, quote=False)`.
4. **QA the render before delivery.** Verify with a real browser parse or
   headless-Chrome screenshot; check every section rendered (count h2s, table
   rows, chart elements) before declaring done.
5. **Delivery:** upload to the client's Drive folder when available
   (Composio `GOOGLEDRIVE_UPLOAD_FILE`); otherwise attach the files and say
   explicitly that Drive delivery wasn't available.

## Stripe design tokens (use exactly)

| Token | Value |
|---|---|
| Accent / links / CTA | `#533afd` (hover `#4434d4`) |
| Headings | `#061b31` (deep navy — never `#000`) |
| Body text | `#64748d` |
| Labels | `#273951` |
| Borders | `#e5edf5`, row hover bg `#fafbff` |
| Dark section bg | `#1c1e54`, white text, card borders `rgba(255,255,255,.14)` |
| Success | `#15be53` (badge bg `rgba(21,190,83,.15)`, text `#108c3d`) |
| Warning | `#9b6829` |
| Danger | `#ea2261` |
| Signature shadow | `rgba(50,50,93,.25) 0 30px 45px -30px, rgba(0,0,0,.1) 0 18px 36px -18px` |
| Radius | 4–6px (buttons/badges/cards); never pills |
| Font | `Source Sans 3` (Google Fonts), weight **300** for headings/body, 600 for emphasis, `font-feature-settings:"ss01"`; numerals `"tnum"` |
| Mono | `Source Code Pro` 400/500 for URLs, check IDs, evidence |
| Headline scale | h1 48px /-.96px; h2 32px /-.64px; h3 22px /-.22px (all weight 300) |
| Layout | max-width 1080px centered; sections 48px vertical padding, 1px border between |

```html
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600&family=Source+Code+Pro:wght@400;500&display=swap" rel="stylesheet">
```

## Score color scale (charts + badges)

```python
def col(s):  # score 0-100
    return '#15be53' if s >= 80 else ('#9b6829' if s >= 60 else '#ea2261')
```

Badges: `background: {col}1f; color:{col}; border:1px solid {col}55`.

## Required report sections (in order)

1. **Header** — kicker `Pandora-AEO vX · Auditoría determinista`, domain h1,
   subtitle, meta-line (pages analyzed / URLs crawled / findings / AR pass
   count / date).
2. **Score global** — donut SVG (left, 220px col) + category bars (right).
3. **Distribución de scores por página** — histogram.
4. **Hallazgos principales** — 2-col card grid, sorted by impact desc then
   effort asc then count desc; left border color by severity
   (impact ≥7 danger, ≥5 warning, else purple-light).
5. **Páginas que requieren atención** — full table of pages with score < 75
   (score badge, words, URL mono, title).
6. **Agent Readiness** — dark `#1c1e54` section: 4 stat cards (pass/fail/AI
   bots/agent endpoints), approved pills, failed checks list with category +
   impact/effort + recommendation.
7. **Plan de acción priorizado** — numbered list ordered by impact/effort.
8. Footer methodology note (deterministic measurement disclaimer, date).

## Chart patterns (hand-built SVG/CSS — no chart libraries)

**Donut** (score g, radius 70, stroke 16):
```html
<svg viewBox="0 0 200 200" class="donut">
<circle cx="100" cy="100" r="70" fill="none" stroke="#e5edf5" stroke-width="16"/>
<circle cx="100" cy="100" r="70" fill="none" stroke="{col(g)}" stroke-width="16"
 stroke-linecap="round" stroke-dasharray="{2*pi*70*g/100:.1f} {2*pi*70:.1f}"
 transform="rotate(-90 100 100)"/>
<text x="100" y="95" text-anchor="middle" class="donut-num">{g}</text>
<text x="100" y="118" text-anchor="middle" class="donut-lab">de 100</text></svg>
```

**Category bars:** CSS grid rows `170px 1fr 40px`, track `#f0f4f8` height 10px
radius 4, fill width = score%.

**Histogram:** flex row of score buckets; bar height = `count / max_count * 120px`,
min 4px; label under each bar; `title` attr with exact count.

**Stat cards:** 4-col grid (2-col mobile), border + signature shadow,
number 32px weight 300, label 13px.

## DOCX generation

Same data, same section order. Convert the HTML's chart regions to PNGs by
screenshotting each section with headless Chrome CDP
(`Page.captureScreenshot` with `clip` at `scale: 2`) and embed with
`python-docx` `add_picture` / the `docx` skill's `image` block (`width_mm`
≈ 165–170). Tables are allowed ONLY for page-level detail and check lists —
never as the sole data presentation. Keep the Stripe colors in embedded charts
and heading styles.

## QA checklist (run before delivery)

- [ ] HTML parses with zero unclosed tags / unmatched elements
- [ ] All h2 sections present (count them: expect 6 sections + header)
- [ ] Table row count == number of worst pages
- [ ] Donut number == global score; bar lengths match values (visual check)
- [ ] No unescaped engine text (search the HTML for raw `<` inside .fev divs)
- [ ] 0 occurrences of "Bizbrain" / "isitagentready" / external system names
- [ ] DOCX validates (`docx_validate.py` or python-docx open+save round-trip)
- [ ] Both files handed off or uploaded, delivery method stated

## Reference

- `references/stripe-tokens.md` — full extracted Stripe design system
  (palette, typography scale, component specs, do/don'ts) for custom styling
  beyond the tokens above.
