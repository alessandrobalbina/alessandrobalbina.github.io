# Bilingual Blog Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure-static, bilingual (EN/IT) Blog section at `/blog/` and `/it/blog/` with a zero-dependency Python 3 Markdown-to-HTML generator, image/chart support, category filtering, RSS feeds, sitemap sync, and Homepage preview.

**Architecture:** A local Python 3 static generator (`scripts/build_blog.py`) reads paired `content/blog/<slug>/en.md` and `it.md` files, renders semantic HTML5 articles and bilingual index pages matching the site's exact CSP, theme, and `hreflang` conventions, generates `feed.xml` / `it/feed.xml`, and updates marked regions in `index.html`, `it/index.html`, and `sitemap.xml`. The deployed site remains 100% pure static HTML/CSS/JS with zero client-side dependencies.

**Tech Stack:** Python 3.9+ (standard library only, `unittest` for tests), Pure Vanilla HTML5/CSS3/JS (`styles.css`, `theme.js`).

**Spec:** Interactive `/grill-me` design session (2026-11-26):
- Local minimal Python 3 static generator (`scripts/build_blog.py`) converting EN/IT Markdown to pure static HTML.
- URLs: `/blog/`, `/it/blog/`, `/blog/<slug>/`, `/it/blog/<slug>/`.
- Navigation: `Blog` link in topbar across all EN/IT pages + compact "Latest from the Blog" section on `index.html` and `it/index.html`.
- Visuals: Optimized static images in `<figure>`/`<figcaption>` + lightweight theme-adaptive SVG/CSS charts (zero external JS, CSP-compliant).
- Features: Category/tag filters, reading-time badge, optional cover image, direct EN/IT article switch (`hreflang`), RSS (`feed.xml`, `it/feed.xml`), automatic `sitemap.xml` update, plus 1 bilingual starter post with an SVG chart.

## Global Constraints

- **Zero Client Dependencies:** No frameworks, npm packages, or external CDN scripts/styles.
- **Strict CSP:** Preserve `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'none';` — zero inline `<script>` or `<style>` blocks in generated HTML.
- **Safe DOM Manipulation:** Never use `innerHTML` or `eval` in `theme.js`.
- **Bilingual Parity (EN/IT):** Every post must have both `en.md` and `it.md` with synchronized `canonical`, `hreflang="en"`, `hreflang="it"`, and `hreflang="x-default"` tags.
- **Accessibility & Performance:** Touch targets ≥ 44×44px, semantic landmarks, `loading="lazy"` on article images, `prefers-reduced-motion` respected.
- **Deploy Hygiene:** `scripts/`, `tests/`, and `content/` must be excluded from `_site/` in `.github/workflows/deploy.yml`.

## Review Focus

- **Missing EN or IT translation file:** `build_blog.py` must fail fast with a clear `ValueError` naming the slug and missing language file rather than publishing half-translated pages or broken `hreflang` links.
- **HTML/XSS injection or broken CSP in Markdown:** Raw `<script>` tags or `on*=` attributes in Markdown must be stripped/escaped, while safe `<figure>`, `<img>`, and `<svg>` chart blocks are preserved without inline styles.
- **Relative asset paths across directory depths:** Links to `styles.css`, `theme.js`, `assets/`, and language toggles must resolve correctly at depth 1 (`/blog/`), depth 2 (`/it/blog/`, `/blog/<slug>/`), and depth 3 (`/it/blog/<slug>/`).
- **Draft posts leaking into production:** Posts with `draft: true` in frontmatter must be skipped from HTML output, Homepage preview, RSS feeds, and `sitemap.xml`.
- **Empty category filter state:** Clicking a category filter in `/blog/` or `/it/blog/` with no matching posts (or switching back to `All`) must show an accessible empty-state message or restore all cards cleanly.

---

### Task 1: Python Static Blog Generator Core (`scripts/build_blog.py`) & Unit Tests

**Files:**
- Create: `scripts/build_blog.py`
- Create: `tests/test_build_blog.py`

**Interfaces:**
- Produces:
  - `parse_frontmatter(text: str) -> tuple[dict[str, str | list[str] | bool], str]`
  - `markdown_to_html(md_text: str) -> str`
  - `estimate_reading_time(text: str) -> int`
  - `load_posts(content_dir: Path) -> list[dict]`
  - `build_site(root_dir: Path) -> dict[str, int]`

- [ ] **Step 1: Write failing unit tests for frontmatter, Markdown, reading time, and bilingual validation**

Write `tests/test_build_blog.py` using `unittest` and `tempfile.TemporaryDirectory`:
- `test_parse_frontmatter_extracts_fields_and_tags_list`: asserts `title`, `date`, `category`, `tags` (list), `draft` (bool), and body.
- `test_markdown_to_html_renders_headings_lists_code_figures_and_escapes_scripts`: asserts `<h2>`, `<ul>`, `<pre><code>`, `<figure><img ...><figcaption>...</figcaption></figure>`, preserves `<svg ...>` chart blocks, and escapes `<script>` tags.
- `test_estimate_reading_time_minimum_one_minute`: asserts short text returns `1` and 450 words returns `2` or `3`.
- `test_load_posts_raises_on_missing_translation`: creates `en.md` without `it.md` and asserts `ValueError` is raised.
- `test_load_posts_skips_drafts`: creates a pair with `draft: true` and asserts `load_posts` returns `[]`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.build_blog'` (or `ImportError`).

- [ ] **Step 3: Implement `parse_frontmatter`, `markdown_to_html`, `estimate_reading_time`, and `load_posts` in `scripts/build_blog.py`**

Implement using Python 3 standard library only (`re`, `html`, `pathlib`, `datetime`, `xml.etree.ElementTree` or `xml.sax.saxutils`). Ensure:
- Frontmatter parses `key: value`, `[tag1, tag2]` lists, and `true`/`false` booleans.
- Markdown supports `#`–`####` headings, paragraphs, bold/italic/inline code, links, unordered/ordered lists, blockquotes, fenced code blocks, `![alt](src "caption")` rendered as `<figure><img src="..." alt="..." loading="lazy" decoding="async"><figcaption>...</figcaption></figure>`, and pass-through `<figure>` / `<svg>` chart blocks while escaping `<script` and `on\w+=`.
- `load_posts` enforces matching `en.md` and `it.md` per `<slug>` directory, skips `draft: true`, and sorts newest-first by `date`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (5 tests OK).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_blog.py tests/test_build_blog.py
git commit -m "feat(blog): add zero-dependency markdown parser and post loader"
```

---

### Task 2: HTML Page, RSS Feed, Sitemap & Homepage Preview Generation

**Files:**
- Modify: `scripts/build_blog.py`
- Modify: `tests/test_build_blog.py`

**Interfaces:**
- Consumes: `load_posts(content_dir: Path) -> list[dict]`
- Produces:
  - `render_post_page(post: dict, lang: str, asset_prefix: str) -> str`
  - `render_index_page(posts: list[dict], lang: str, asset_prefix: str) -> str`
  - `render_rss_feed(posts: list[dict], lang: str) -> str`
  - `update_marker_block(file_path: Path, start_marker: str, end_marker: str, replacement: str) -> None`
  - `build_site(root_dir: Path) -> dict[str, int]`

- [ ] **Step 1: Write failing integration tests for generated HTML, relative paths, RSS, and marker replacement**

Add to `tests/test_build_blog.py`:
- `test_build_site_generates_bilingual_pages_rss_and_updates_markers`: sets up a temp repo with a sample `content/blog/sample-post/{en,it}.md`, minimal `index.html`, `it/index.html`, and `sitemap.xml` containing `<!-- BLOG_LATEST_START -->...<!-- BLOG_LATEST_END -->` and `<!-- BLOG_SITEMAP_START -->...<!-- BLOG_SITEMAP_END -->`. Runs `build_site(tmp_path)` and asserts:
  - `blog/index.html` uses `../styles.css` and `../theme.js`
  - `it/blog/index.html` uses `../../styles.css` and `../../theme.js`
  - `blog/sample-post/index.html` uses `../../styles.css` and links `hreflang="it"` to `https://alessandrobalbina.github.io/it/blog/sample-post/`
  - `it/blog/sample-post/index.html` uses `../../../styles.css`
  - `feed.xml` and `it/feed.xml` are valid XML containing the post `<item>`
  - `index.html`, `it/index.html`, and `sitemap.xml` contain the injected post card / `<url>` entry.

- [ ] **Step 2: Run tests to verify the new test fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `AttributeError` / `ImportError` for `build_site`.

- [ ] **Step 3: Implement HTML templates, RSS builder, marker updater, and `build_site` CLI in `scripts/build_blog.py`**

Implement `render_post_page`, `render_index_page`, `render_rss_feed`, `update_marker_block`, and `build_site(root_dir)` + `if __name__ == "__main__":` CLI entrypoint.
- Match the exact `<head>` CSP, favicon links, `<header class="topbar card">`, `<footer class="site-footer">`, and `<script src="...theme.js">` structure of `other-projects/index.html` and `it/other-projects/index.html`.
- Compute `asset_prefix` cleanly by depth (`../` for `/blog/`, `../../` for `/it/blog/` and `/blog/<slug>/`, `../../../` for `/it/blog/<slug>/`).
- Include JSON-LD `BlogPosting` schema on article pages and `Blog` schema on index pages.

- [ ] **Step 4: Run tests to verify all pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (all tests OK).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_blog.py tests/test_build_blog.py
git commit -m "feat(blog): add HTML, RSS, sitemap, and homepage preview generation"
```

---

### Task 3: Blog Styling (`styles.css`) & Category Filter Engine (`theme.js`)

**Files:**
- Modify: `styles.css` (append after line 2957)
- Modify: `theme.js` (lines 253-320)

**Interfaces:**
- Consumes: CSS custom properties in `styles.css:438-490` (`--surface`, `--text`, `--muted`, `--accent`, `--border`, `--radius`, `--font-serif`, `--font-sans`)
- Produces: `.blog-grid`, `.blog-card`, `.blog-prose`, `.blog-figure`, `.blog-chart`, `.blog-filter-btn`, `.blog-empty-state` in `styles.css`; generic filter handler in `theme.js`.

- [ ] **Step 1: Add Blog layout, prose, figure, and theme-adaptive chart styles to `styles.css`**

Append a clearly commented `/* === Blog Section === */` block at the end of `styles.css`:
- `.blog-grid` (responsive 2-column grid on desktop, 1-column on mobile), `.blog-card` with hover lift matching `.card` and `prefers-reduced-motion` guard.
- `.blog-meta` (date + reading time + category pill), `.blog-card-cover` (`aspect-ratio: 16 / 9`, `object-fit: cover`).
- `.blog-prose` (comfortable `68ch` measure, `line-height: 1.75`, styled `h2`/`h3`, `blockquote`, `pre`/`code`, `ul`/`ol`).
- `.blog-figure` & `figcaption` (`border-radius: var(--radius-sm)`, subtle border, centered caption in `--muted`).
- `.blog-chart` wrapper for SVG/CSS charts using `currentColor` and CSS variables (`--accent`, `--accent-warm`, `--border`) so charts automatically adapt to Light and Dark mode.
- `.blog-filter-bar` and `.blog-filter-btn` (min `44px` height for mobile WCAG touch target) + `.blog-empty-state`.

- [ ] **Step 2: Extend `theme.js` filter logic to support `.blog-filter-btn` and `.blog-card`**

Inspect `theme.js:253-320` and generalize or add a safe DOM listener for `.blog-filter-btn`:
- Toggles `aria-pressed` / `is-active` on filter buttons.
- Filters `.blog-card[data-category]` elements by `data-filter` (`all` shows every card).
- Toggles `.blog-empty-state` visibility using `hidden` attribute when 0 cards match (zero `innerHTML`).

- [ ] **Step 3: Verify JS syntax and CSS brace balance**

Run: `node --check theme.js 2>/dev/null || python3 -c "s=open('styles.css').read(); assert s.count('{')==s.count('}'), 'Unbalanced CSS braces'; print('CSS OK')"`
Expected: `CSS OK` (and `node --check` exits 0 if Node is installed).

- [ ] **Step 4: Commit**

```bash
git add styles.css theme.js
git commit -m "feat(blog): add responsive blog styles, dark-mode chart tokens, and category filter"
```

---

### Task 4: Navigation, Homepage Preview Markers & Deploy Hygiene

**Files:**
- Modify: `index.html`, `it/index.html`
- Modify: `contact/index.html`, `it/contact/index.html`
- Modify: `other-projects/index.html`, `it/other-projects/index.html`
- Modify: `sitemap.xml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `<!-- BLOG_LATEST_START -->...<!-- BLOG_LATEST_END -->` in `index.html` and `it/index.html`; `<!-- BLOG_SITEMAP_START -->...<!-- BLOG_SITEMAP_END -->` in `sitemap.xml`.

- [ ] **Step 1: Add `Blog` link to `.topbar-links` in all 6 existing HTML pages**

Insert `<a href="blog/">Blog</a>` (or `../blog/`, `../it/blog/`, `blog/` relative to each page's depth) in:
- `index.html` (after `Other Projects`)
- `it/index.html` (after `Altri Progetti`)
- `other-projects/index.html` and `it/other-projects/index.html`
- `contact/index.html` and `it/contact/index.html`

- [ ] **Step 2: Add "Latest from the Blog" section markers to `index.html` and `it/index.html`, and sitemap markers to `sitemap.xml`**

- In `index.html` (right after the About section or before Footer) and `it/index.html` (mirrored), add `<section aria-labelledby="latest-blog-title" class="card">` wrapping `<!-- BLOG_LATEST_START --><!-- BLOG_LATEST_END -->`.
- In `sitemap.xml` (before `</urlset>`), add `<!-- BLOG_SITEMAP_START -->` and `<!-- BLOG_SITEMAP_END -->`.

- [ ] **Step 3: Exclude generator sources from GitHub Pages deploy & ignore Python cache**

- In `.github/workflows/deploy.yml`, add `--exclude='scripts'` `--exclude='tests'` `--exclude='content'` to the `rsync` command (lines 39-48).
- In `.gitignore`, add `__pycache__/` and `*.pyc`.

- [ ] **Step 4: Verify no broken relative links or missing markers**

Run: `grep -rn "BLOG_LATEST_START\|BLOG_SITEMAP_START" index.html it/index.html sitemap.xml && grep -rn "/blog/\|blog/" index.html it/index.html contact/index.html it/contact/index.html other-projects/index.html it/other-projects/index.html`
Expected: All 3 marker files and all 6 navbars report matches.

- [ ] **Step 5: Commit**

```bash
git add index.html it/index.html contact/index.html it/contact/index.html other-projects/index.html it/other-projects/index.html sitemap.xml .github/workflows/deploy.yml .gitignore
git commit -m "feat(blog): wire blog navigation, homepage preview markers, and deploy exclusions"
```

---

### Task 5: Bilingual Starter Post with Theme-Adaptive SVG Chart & End-to-End Build

**Files:**
- Create: `content/blog/welcome-research-notes/en.md`
- Create: `content/blog/welcome-research-notes/it.md`
- Create: `assets/blog/welcome-research-notes/research-overview.svg`
- Generated by script: `blog/index.html`, `it/blog/index.html`, `blog/welcome-research-notes/index.html`, `it/blog/welcome-research-notes/index.html`, `feed.xml`, `it/feed.xml`, updated `index.html`, `it/index.html`, `sitemap.xml`

**Interfaces:**
- Consumes: `scripts/build_blog.py`

- [ ] **Step 1: Create starter bilingual post (`en.md` and `it.md`) and a theme-adaptive SVG diagram/chart**

- Create `content/blog/welcome-research-notes/en.md` and `it.md` with frontmatter (`title`, `date: 2026-11-26`, `category: Research`, `tags: [Research, AI, Sustainability]`, `excerpt`, `cover: assets/blog/welcome-research-notes/research-overview.svg`, `draft: false`), an inline `<figure class="blog-figure"><div class="blog-chart">...<svg>...</svg></div><figcaption>...</figcaption></figure>` demonstrating a clean data/conceptual chart using CSS variables, and a standard image `<figure>`.

- [ ] **Step 2: Run the blog generator and full test suite**

Run: `python3 scripts/build_blog.py && python3 -m unittest discover -s tests -v`
Expected: Generator prints processed post count (`1` post, `2` pages + `2` indexes + `2` feeds) and all unit/integration tests PASS.

- [ ] **Step 3: Verify generated HTML, CSP compliance, and local preview**

Run: `grep -rn "<script>" blog/ it/blog/ || echo "No inline scripts (CSP OK)"`
Expected: `No inline scripts (CSP OK)`. Start local static server briefly or inspect generated files to verify links and Dark/Light mode classes.

- [ ] **Step 4: Commit**

```bash
git add content/ assets/blog/ blog/ it/blog/ feed.xml it/feed.xml index.html it/index.html sitemap.xml
git commit -m "feat(blog): publish bilingual starter post with research chart and run initial build"
```
