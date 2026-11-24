# SEO Audit & Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all technical, structured data, OpenGraph/Twitter, and sitemap SEO gaps across the bilingual (`en`/`it`) static site.

**Architecture:** Pure static HTML/XML updates across the 6 HTML pages (`index.html`, `it/index.html`, `contact/index.html`, `it/contact/index.html`, `other-projects/index.html`, `it/other-projects/index.html`) and `sitemap.xml`, preserving strict CSP, bilingual parity, and zero-dependency architecture.

**Tech Stack:** Static HTML5, Schema.org JSON-LD, OpenGraph, Twitter Cards, XML Sitemap.

## Global Constraints

- Maintain strict EN/IT bilingual parity across all pages.
- Preserve existing Content-Security-Policy (`default-src 'self'`), canonical URLs, and `hreflang` tags.
- Zero inline scripts or external dependencies.

## Review Focus

- Duplicate meta tags (`og:type` in `other-projects/index.html`) must be removed without dropping valid tags.
- JSON-LD blocks must remain valid JSON (no trailing commas, proper escaping).
- All `og:image:alt` and `twitter:image:alt` must match the page language (`en` vs `it`).
- `BreadcrumbList` on secondary pages must use exact canonical URLs and localized names.
- `sitemap.xml` `<lastmod>` must be valid ISO 8601 (`2026-11-24`) for all 8 URLs.

---

### Task 1: Fix Duplicate Meta Tags & Add Image Alt Metadata Across All 6 HTML Pages

**Files:**
- Modify: `index.html:25-42`
- Modify: `it/index.html:25-42`
- Modify: `contact/index.html:16-31`
- Modify: `it/contact/index.html:15-30`
- Modify: `other-projects/index.html:16-33`
- Modify: `it/other-projects/index.html:15-30`

- [x] Remove duplicate `<meta property="og:type" content="website" />` in `other-projects/index.html` (line 17).
- [x] Add `<meta property="og:image:alt" ... />` and `<meta name="twitter:image:alt" ... />` in all 6 HTML pages (localized EN/IT).
- [x] Verify with `grep -n "og:type" other-projects/index.html` (count = 1) and `grep -c "og:image:alt" *.html */*.html */*/*.html`.

---

### Task 2: Enrich Schema.org JSON-LD (Freshness, Languages, Breadcrumbs)

**Files:**
- Modify: `index.html:55-153`
- Modify: `it/index.html:55-153`
- Modify: `contact/index.html:42-72`
- Modify: `it/contact/index.html:41-71`
- Modify: `other-projects/index.html:44-74`
- Modify: `it/other-projects/index.html:41-71`

- [x] Add `"dateModified": "2026-11-24"` to `ProfilePage` / `ContactPage` in all 6 HTML pages.
- [x] Add `"Sardinian"` / `"Sardo"` to `Person.knowsLanguage` in `index.html` and `it/index.html`.
- [x] Verify `BreadcrumbList` (`Home -> Contact` / `Home -> Other Projects`, and Italian equivalents) in `contact/index.html`, `it/contact/index.html`, `other-projects/index.html`, and `it/other-projects/index.html` (already present).
- [x] Validate all JSON-LD blocks using `python3 -c` JSON parser across all 6 HTML files.

---

### Task 3: Update `sitemap.xml` Freshness & Add `llms.txt` Discovery Link

**Files:**
- Modify: `sitemap.xml:1-79`
- Modify: `index.html:21-24`
- Modify: `it/index.html:21-24`

- [x] Update all `<lastmod>` entries in `sitemap.xml` from `2026-10-30` to `2026-11-24`.
- [x] Add `<link rel="alternate" type="text/plain" title="LLMs.txt" href="https://alessandrobalbina.github.io/llms.txt" />` in `index.html` and `it/index.html`.
- [x] Validate `sitemap.xml` well-formedness with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('sitemap.xml')"`.
