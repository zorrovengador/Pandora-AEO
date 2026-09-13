---
name: aeo-audit
description: Audit websites for AEO, Agent Readiness, LLM-friendly content, and SEO technical issues. 8-category scoring with impact/effort per check.
version: 0.3.0
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

- Python 3.10+, no external dependencies.
- The repository directory available in the active workspace.

## Report Workflow (MANDATORY — execute ALL steps in order)

When generating an audit report from a JSON run record, this workflow is non-negotiable. Do NOT stop at the first deliverable; do NOT substitute plain tables for charts; do NOT skip skill loading. Every step lists the exact skills to load and the reason.

### Step 0 — Before any work
- Load this skill (`aeo-audit`) and follow it. This section is the checklist.
- Check `session_search` for prior conventions on this task type if unsure what the user expects.

### Step 1 — Run the audit engine
- `python -m pandora_aeo.cli <url> --crawl --max-pages 2000 --output artifacts/<site>.json` (full crawl, not a sample — the user rejected a 30-page sample; always exhaust link discovery or cover the full sitemap).

### Step 2 — Define the visual system BEFORE writing anything
- Load `popular-web-designs` (template: `templates/stripe.md` — Stripe tokens: purple `#533afd`, navy `#061b31`, weight 300, blue-tinted shadows) and `claude-design` for design process/QA discipline.
- Optionally consult `pandora-professional-presentations` workflow: visual system first, QA render before delivery.

### Step 3 — Build the HTML report (self-contained, interactive)
- Load `claude-design` for authoring guidance; apply Stripe tokens from Step 2.
- Embed hand-built SVG/CSS charts: global-score donut, category-score bars, page-score heatmap/table, findings cards sorted by impact/effort, Agent Readiness status grid.
- All CSS/SVG inline; Google Fonts via `<link>`; opens offline in any browser.
- QA: render and visually verify before delivery (screenshot or browser check).

### Step 4 — Build the DOCX report (same data, same conventions)
- Load `docx` skill. Charts go in as embedded SVG-rendered images (convert the Step 3 SVGs to PNG if python-docx can't take SVG); tables are allowed ONLY for page-level detail, never as the sole data presentation.
- Match the Stripe color palette in charts and heading styles.

### Step 5 — REGLA DURA (hard rule)
- NEVER include comparisons with AEO Bizbrain, isitagentready.com, or ANY external system in any deliverable (HTML, DOCX, JSON, PDF, PPTX). Only facts measured by Pandora-AEO: category scores, pages, impact/effort findings, Agent Readiness, action plan.

### Step 6 — Deliver
- If the client's Google Drive folder is accessible (via Composio GOOGLEDRIVE_UPLOAD_FILE), upload both files there and report the links.
- If not, hand off files directly (MEDIA: attachment) and explicitly say that Drive delivery wasn't available — never silently skip it.

### Step 7 — Post-report
- Record any new convention or pitfall learned into this skill so it loads next time.

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
