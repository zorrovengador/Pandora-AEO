---
name: aeo-audit
description: Audit websites for AEO, Agent Readiness, LLM-friendly content, and SEO technical issues. 8-category scoring with impact/effort per check.
version: 0.4.0
author: Manuel Hernández (zorrovengador), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [AEO, SEO, Agent-Readiness, LLM-friendly, auditing, MCP, markdown-negotiation, robots-txt, hreflang, structured-data]
    related_skills: []
---

# AEO Audit Skill (v0.3)

Run the bundled deterministic engine before interpreting a website. This skill measures reproducible HTML facts, Agent Readiness signals, and LLM-friendly content signals; it does not claim universal AI visibility rankings, publish website changes, or replace human review.

## What the engine checks (v0.3)

### Per-page: 8 categories (matching the bizbrain AEO system)

| Category | Checks | Description |
|---|---|---|
| **technicalSeo** | TITLE_PRESENT, TITLE_LENGTH (30–65 chars), META_DESCRIPTION, H1_COUNT, CANONICAL, IMAGES_WITHOUT_ALT | Core SEO technical signals |
| **metadata** | OG_IMAGE, OG_TITLE, OG_DESCRIPTION | Open Graph tags for social sharing and ads |
| **htmlSemantics** | HEADING_HIERARCHY, HEADING_COUNT | Semantic HTML structure and accessibility |
| **structuredData** | JSON_LD | Valid JSON-LD structured data blocks |
| **llmContent** | CONTENT_DEPTH (min 300 words), QUESTION_HEADINGS | Content depth and question-format headings for LLM extraction |
| **i18n** | HREFLANG, LANG_ATTR | Internationalization tags (hreflang, lang) |
| **metaAdsReadiness** | META_ADS_READY | All Open Graph tags present for ad campaigns |
| **performance** | HTML_SIZE | HTML payload size for rendering speed |

### Cross-page checks
- DUPLICATE_TITLES — detects repeated `<title>` across pages
- THIN_CONTENT — aggregates pages with <300 words

### Agent Readiness (20 checks across 5 categories)
**Discoverability:** robots.txt, sitemap, Link headers (RFC 8288), DNS-AID (RFC 9460)
**Content Accessibility:** Markdown negotiation (Accept: text/markdown)
**Bot Access Control:** AI bot rules in robots.txt, Content Signals
**API/Auth/MCP:** API Catalog, OAuth, OIDC, OAuth Protected Resource, Auth.md, MCP Server Card, MCP metadata, Agent Skills Index
**Commerce (info):** ARD manifest, Web Bot Auth, UCP, ACP, OpenAPI.json

### Every check carries:
- `impact` (1–10): how much this issue affects AEO visibility
- `effort` (1–10): how much work it takes to fix
- `category`: which of the 8 categories it belongs to
- `evidence`: the measured fact

## How to Run

```bash
# Single page audit
python -m pandora_aeo.cli https://example.com --output artifacts/example.json

# Full site crawl audit
python -m pandora_aeo.cli https://example.com --crawl --max-pages 50 --output artifacts/site.json
```

## Output format

```json
{
  "run": {"engine_version": "0.3.0", "measured_at": "...", "timeout_seconds": 20, "max_pages": 50},
  "target": {"url": "https://example.com"},
  "global_score": 86,
  "category_scores": {"technicalSeo": 71, "metadata": 100, "htmlSemantics": 86, ...},
  "pages": [{"url": "...", "title": "...", "word_count": 1009, "score": 90}],
  "findings": [{"id": "CONTENT_DEPTH", "impact": 8, "effort": 6, "category": "llmContent", ...}],
  "findings_count": 42,
  "pages_analyzed": 7,
  "agent_readiness": {"checks": [...], "facts": {...}}
}
```

## When to Use

- Audit a public website for technical AEO, Agent Readiness, and LLM-friendly content.
- Produce structured facts comparable to isitagentready.com and the bizbrain AEO system.
- Generate a reproducible JSON run record with per-page and per-category scores.
- Prioritize fixes by impact/effort scoring.

Don't use for private-network targets, production changes, or unsupported claims about AI rankings.

## Prerequisites

- Python 3.10+; stdlib only for auditing and HTML report generation.
- For the DOCX deliverable: `python-docx` (or the Hermes `docx` skill).
- The repository directory available in the active workspace.
- This skill is self-contained: the report design system ships inside it
  (`references/`), no other design skills required.

## Report Workflow (MANDATORY — execute ALL steps in order)

When generating an audit report from a JSON run record, this workflow is non-negotiable. Do NOT stop at the first deliverable; do NOT substitute plain tables for charts; do NOT skip skill loading. Every step lists the exact skills to load and the reason.

### Step 0 — Before any work
- Load this skill (`aeo-audit`) and follow it. This section is the checklist.
- Check `session_search` for prior conventions on this task type if unsure what the user expects.

### Step 1 — Run the audit engine
- `python -m pandora_aeo.cli <url> --crawl --max-pages 2000 --output artifacts/<site>.json` (full crawl, not a sample — the user rejected a 30-page sample; always exhaust link discovery or cover the full sitemap).

### Step 2 — Define the visual system BEFORE writing anything
- Read `references/report-design.md` (bundled with this skill) — Stripe design tokens, chart patterns, and report structure are all in there. No external design skills required.
- For deeper styling, consult `references/stripe-tokens.md`; for the target quality bar, open `references/example-report.html`.

### Step 3 — Build the HTML report (self-contained, interactive)
- Follow `references/report-design.md` §"Required report sections" and §"Chart patterns": global-score donut, category bars, histogram, findings cards sorted by impact/effort, Agent Readiness dark grid.
- All CSS/SVG inline; Google Fonts via `<link>`; opens offline in any browser.
- QA: render and visually verify before delivery (screenshot or browser check) — checklist in `references/report-design.md` §QA.

### Step 4 — Build the DOCX report (same data, same conventions)
- Use the Hermes `docx` skill (or python-docx directly) for the container; charts as PNG screenshots of the HTML's chart regions (CDP clip capture, scale 2).
- Tables allowed ONLY for page-level detail, never as the sole data presentation. Match the Stripe palette. Details: `references/report-design.md` §DOCX.

### Step 5 — REGLA DURA (hard rule)
- NEVER include comparisons with AEO Bizbrain, isitagentready.com, or ANY external system in any deliverable (HTML, DOCX, JSON, PDF, PPTX). Only facts measured by Pandora-AEO: category scores, pages, impact/effort findings, Agent Readiness, action plan.

### Step 6 — Deliver
- If the client's Google Drive folder is accessible (via Composio GOOGLEDRIVE_UPLOAD_FILE), upload both files there and report the links.
- If not, hand off files directly (MEDIA: attachment) and explicitly say that Drive delivery wasn't available — never silently skip it.

### Step 7 — Post-report
- Record any new convention or pitfall learned into this skill so it loads next time.

## Report design system (bundled — no external skills needed)

The workflow steps above already carry the hard rules (REGLA DURA, full crawl,
string escaping, QA render, delivery). This section is the technical reference
those steps point into.

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

## Reference files (bundled)

- `references/stripe-tokens.md` — full extracted Stripe design system
  (palette, typography scale, component specs, do/don'ts) for styling beyond
  the tokens above.
- `references/example-report.html` — rendered reference report
  (executrain.com.mx audit) that defines the target quality bar.

## Common failure modes (do NOT repeat)
- Generating a plain-table DOCX with no charts and no Stripe styling (happened 2026-09-13; user flagged it).
- Crawling only 30 pages when the site has 1,000+ URLs (happened 2026-09-13; user flagged it).
- Loading only the `docx` skill and never checking `popular-web-designs`/`claude-design`/`pandora-professional-presentations`.
- Publishing to Drive without being asked; or comparing against AEO Bizbrain (REGLA DURA violation).

## Verification

```bash
python -m unittest discover -s tests -v
```

A valid run has 16 passing tests, a parseable JSON result, and no writes to the audited website.
