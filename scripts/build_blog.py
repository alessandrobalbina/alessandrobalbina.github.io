"""Zero-dependency static blog generator for alessandrobalbina.github.io."""

from __future__ import annotations

import html
import json
import math
import re
import shutil
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any

SITE_ORIGIN = "https://alessandrobalbina.github.io"
CSP_CONTENT = (
    "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-src 'none'; worker-src 'none'; "
    "object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests;"
)

SAFE_BLOCK_PREFIXES = ("<figure", "<svg")
INLINE_EVENT_RE = re.compile(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
SCRIPT_TAG_RE = re.compile(r"<\s*/?\s*script\b[^>]*>", re.IGNORECASE)
IMAGE_LINE_RE = re.compile(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\s*$')
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$")
UL_RE = re.compile(r"^[-*]\s+(.+)$")
OL_RE = re.compile(r"^\d+\.\s+(.+)$")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-like frontmatter delimited by '---' and return (metadata, body)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Markdown file must start with '---' frontmatter block")

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        raise ValueError("Unterminated frontmatter block (missing closing '---')")

    meta: dict[str, Any] = {}
    for line in lines[1:end_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw_val = stripped.split(":", 1)
        key = key.strip()
        val = raw_val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
        elif val.lower() in ("true", "false"):
            meta[key] = val.lower() == "true"
        else:
            meta[key] = val.strip("'\"")

    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return meta, body


def _sanitize_raw_html(block: str) -> str:
    """Strip <script> tags and inline event handlers from pass-through figure/svg blocks."""
    cleaned = SCRIPT_TAG_RE.sub(lambda m: html.escape(m.group(0)), block)
    return INLINE_EVENT_RE.sub("", cleaned)


def _render_inline(text: str) -> str:
    """Escape HTML and convert inline Markdown (code, links, bold, italic)."""
    code_tokens: list[str] = []

    def _hold_code(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    protected = re.sub(r"`([^`]+)`", _hold_code, text)
    escaped = html.escape(protected)

    def _replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2)
        if href.startswith(("http://", "https://")):
            return f'<a href="{href}" rel="noopener noreferrer">{label}</a>'
        return f'<a href="{href}">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _replace_link, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)

    for idx, token in enumerate(code_tokens):
        escaped = escaped.replace(f"\x00CODE{idx}\x00", token)
    return escaped


def markdown_to_html(md_text: str) -> str:
    """Convert a Markdown string into CSP-safe semantic HTML."""
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append(f"<pre><code>{chr(10).join(code_lines)}</code></pre>")
            continue

        # Pass-through safe <figure> / <svg> chart blocks
        if stripped.lower().startswith(SAFE_BLOCK_PREFIXES):
            closing_tag = "</figure>" if stripped.lower().startswith("<figure") else "</svg>"
            block_lines = [line]
            while closing_tag not in lines[i].lower() and i + 1 < len(lines):
                i += 1
                block_lines.append(lines[i])
            i += 1
            out.append(_sanitize_raw_html("\n".join(block_lines)))
            continue

        # Standalone image -> <figure>
        img_match = IMAGE_LINE_RE.match(stripped)
        if img_match:
            alt = html.escape(img_match.group(1))
            src = html.escape(img_match.group(2))
            caption = html.escape(img_match.group(3) or "")
            fig = f'<figure class="blog-figure"><img src="{src}" alt="{alt}" loading="lazy" decoding="async">'
            if caption:
                fig += f"<figcaption>{caption}</figcaption>"
            fig += "</figure>"
            out.append(fig)
            i += 1
            continue

        # Headings
        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            out.append(f"<h{level}>{_render_inline(heading_match.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(_render_inline(lines[i].strip()[1:].strip()))
                i += 1
            out.append(f"<blockquote><p>{' '.join(quote_lines)}</p></blockquote>")
            continue

        # Unordered list
        if UL_RE.match(stripped):
            items: list[str] = []
            while i < len(lines):
                m = UL_RE.match(lines[i].strip())
                if not m:
                    break
                items.append(f"<li>{_render_inline(m.group(1))}</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue

        # Ordered list
        if OL_RE.match(stripped):
            items = []
            while i < len(lines):
                m = OL_RE.match(lines[i].strip())
                if not m:
                    break
                items.append(f"<li>{_render_inline(m.group(1))}</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(items) + "\n</ol>")
            continue

        # Paragraph
        para_lines: list[str] = []
        while i < len(lines):
            cur = lines[i].strip()
            if (
                not cur
                or cur.startswith(("```", ">", "#"))
                or cur.lower().startswith(SAFE_BLOCK_PREFIXES)
                or IMAGE_LINE_RE.match(cur)
                or UL_RE.match(cur)
                or OL_RE.match(cur)
            ):
                break
            para_lines.append(_render_inline(cur))
            i += 1
        out.append(f"<p>{' '.join(para_lines)}</p>")

    return "\n".join(out)


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes (minimum 1 minute)."""
    plain = re.sub(r"<[^>]+>", " ", text)
    words = len(re.findall(r"\b\w+\b", plain))
    return max(1, math.ceil(words / words_per_minute))


def load_posts(content_dir: Path) -> list[dict[str, Any]]:
    """Load paired EN/IT posts from content_dir/<slug>/{en,it}.md, skipping drafts."""
    if not content_dir.exists():
        return []

    posts: list[dict[str, Any]] = []
    for post_dir in sorted(p for p in content_dir.iterdir() if p.is_dir()):
        slug = post_dir.name
        en_path = post_dir / "en.md"
        it_path = post_dir / "it.md"

        if not en_path.exists():
            raise ValueError(f"Post '{slug}' is missing en.md")
        if not it_path.exists():
            raise ValueError(f"Post '{slug}' is missing it.md")

        en_meta, en_body = parse_frontmatter(en_path.read_text(encoding="utf-8"))
        it_meta, it_body = parse_frontmatter(it_path.read_text(encoding="utf-8"))

        if en_meta.get("draft") is True or it_meta.get("draft") is True:
            continue

        posts.append(
            {
                "slug": slug,
                "date": str(en_meta.get("date", "")),
                "cover": str(en_meta.get("cover", "")),
                "en": {
                    "meta": en_meta,
                    "body_md": en_body,
                    "body_html": markdown_to_html(en_body),
                    "reading_time": estimate_reading_time(en_body),
                },
                "it": {
                    "meta": it_meta,
                    "body_md": it_body,
                    "body_html": markdown_to_html(it_body),
                    "reading_time": estimate_reading_time(it_body),
                },
            }
        )

    posts.sort(key=lambda item: item["date"], reverse=True)
    return posts


def _format_date(date_str: str, lang: str) -> str:
    """Format YYYY-MM-DD into a human-readable EN or IT date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return html.escape(date_str)
    months_en = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )
    months_it = (
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    )
    month = months_it[dt.month - 1] if lang == "it" else months_en[dt.month - 1]
    return f"{dt.day} {month} {dt.year}"


def _resolve_asset(path_val: str, asset_prefix: str) -> str:
    if not path_val or path_val.startswith(("http://", "https://", "/", "../", "data:")):
        return path_val
    return f"{asset_prefix}{path_val}"


def _render_topbar(lang: str, asset_prefix: str, lang_switch_href: str, active: str = "blog") -> str:
    home_href = f"{asset_prefix}it/" if lang == "it" else asset_prefix
    projects_href = f"{asset_prefix}it/other-projects/" if lang == "it" else f"{asset_prefix}other-projects/"
    blog_href = f"{asset_prefix}it/blog/" if lang == "it" else f"{asset_prefix}blog/"
    contact_href = f"{asset_prefix}it/contact/" if lang == "it" else f"{asset_prefix}contact/"
    nav_label = "Navigazione principale" if lang == "it" else "Main navigation"
    projects_desktop = "Altri progetti" if lang == "it" else "Other Projects"
    projects_mobile = "Progetti" if lang == "it" else "Projects"
    contact_desktop = "Contattami" if lang == "it" else "Contact me"
    contact_mobile = "Contatti" if lang == "it" else "Contact"
    lang_code = "EN" if lang == "it" else "IT"
    lang_aria = "EN - Switch language to English" if lang == "it" else "IT - Cambia lingua in Italiano"
    blog_current = ' aria-current="page"' if active == "blog" else ""

    return f"""    <header class="topbar card" role="banner">
      <nav aria-label="{nav_label}">
        <div class="topbar-links">
          <a href="{home_href}">Home</a>
          <a href="{projects_href}">
            <span class="nav-desktop">{projects_desktop}</span>
            <span class="nav-mobile">{projects_mobile}</span>
          </a>
          <a href="{blog_href}"{blog_current}>Blog</a>
          <div class="dropdown">
            <button class="dropdown-trigger" aria-haspopup="true" aria-expanded="false"
              aria-controls="cv-dropdown-menu">
              <svg class="cv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              <span class="nav-desktop">CV / Resume</span>
              <span class="nav-mobile">CV</span>
              <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>
            <div class="dropdown-menu" id="cv-dropdown-menu" aria-hidden="true">
              <a href="{asset_prefix}assets/CV%20Alessandro%20Balbina.pdf" target="_blank" rel="noopener noreferrer">
                <span>CV Standard (EN)</span>
              </a>
              <a href="{asset_prefix}assets/CV%20Alessandro%20Balbina%20Europeo.pdf" target="_blank" rel="noopener noreferrer">
                <span>CV Europeo (IT)</span>
              </a>
            </div>
          </div>
        </div>
        <div class="topbar-actions">
          <a href="{contact_href}" class="btn-contact">
            <span class="nav-desktop">{contact_desktop}</span>
            <span class="nav-mobile">{contact_mobile}</span>
          </a>
          <a href="{lang_switch_href}" class="lang-toggle" aria-label="{lang_aria}">{lang_code}</a>
          <button id="theme-toggle" class="theme-toggle" aria-label="Toggle dark/light mode">
            <svg class="moon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
            <svg class="sun-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
          </button>
        </div>
      </nav>
    </header>"""


def _render_shell_head(
    *,
    lang: str,
    title: str,
    description: str,
    canonical_url: str,
    en_url: str,
    it_url: str,
    asset_prefix: str,
    og_type: str,
    schema_objs: list[dict[str, Any]],
    keywords: list[str] | None = None,
    article_meta: dict[str, Any] | None = None,
    robots_meta: str = "index, follow, max-image-preview:large",
    og_image: str | None = None,
) -> str:
    og_locale = "it_IT" if lang == "it" else "en_US"
    og_alt = "en_US" if lang == "it" else "it_IT"
    rss_href = f"{asset_prefix}it/feed.xml" if lang == "it" else f"{asset_prefix}feed.xml"
    rss_title = "Blog di Alessandro Balbina (IT)" if lang == "it" else "Alessandro Balbina Blog (EN)"
    resolved_og_image = og_image or f"{SITE_ORIGIN}/assets/og-preview.png"
    keywords_tag = (
        f'\n  <meta name="keywords" content="{html.escape(", ".join(str(k) for k in keywords))}" />'
        if keywords
        else ""
    )
    article_tags = ""
    if article_meta:
        iso_dt = f'{article_meta["published"]}T09:00:00+01:00'
        parts = [
            f'  <meta property="article:published_time" content="{html.escape(iso_dt)}" />',
            f'  <meta property="article:modified_time" content="{html.escape(iso_dt)}" />',
            f'  <meta property="article:author" content="Alessandro Balbina" />',
            f'  <meta property="article:section" content="{html.escape(str(article_meta["section"]))}" />',
        ]
        for t in article_meta.get("tags", []):
            parts.append(f'  <meta property="article:tag" content="{html.escape(str(t))}" />')
        article_tags = "\n" + "\n".join(parts)

    ld_scripts = "\n  ".join(
        f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>'
        for obj in schema_objs
    )
    return f"""<!doctype html>
<html lang="{lang}" data-type="article" data-radius="soft" data-buttons="pill" data-motion>

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy" content="{CSP_CONTENT}" />
  <meta name="referrer" content="strict-origin-when-cross-origin" />
  <meta name="description" content="{html.escape(description)}" />{keywords_tag}
  <meta name="author" content="Alessandro Balbina" />
  <meta name="robots" content="{robots_meta}" />
  <meta name="theme-color" content="#11213f" />
  <meta property="og:type" content="{og_type}" />
  <meta property="og:site_name" content="Alessandro Balbina" />
  <meta property="og:title" content="{html.escape(title)}" />
  <meta property="og:description" content="{html.escape(description)}" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="{html.escape(resolved_og_image)}" />
  <meta property="og:image:alt" content="{html.escape(title)}" />
  <meta property="og:locale" content="{og_locale}" />
  <meta property="og:locale:alternate" content="{og_alt}" />{article_tags}
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{html.escape(title)}" />
  <meta name="twitter:description" content="{html.escape(description)}" />
  <meta name="twitter:image" content="{html.escape(resolved_og_image)}" />
  <meta name="twitter:image:alt" content="{html.escape(title)}" />
  <title>{html.escape(title)}</title>
  <link rel="canonical" href="{canonical_url}" />
  <link rel="alternate" hreflang="en" href="{en_url}" />
  <link rel="alternate" hreflang="it" href="{it_url}" />
  <link rel="alternate" hreflang="x-default" href="{en_url}" />
  <link rel="alternate" type="application/rss+xml" title="{rss_title}" href="{rss_href}" />
  <link rel="icon" href="{asset_prefix}assets/favicon.svg" type="image/svg+xml" />
  <link rel="icon" href="{asset_prefix}assets/favicon-48x48.png" sizes="48x48" type="image/png" />
  <link rel="apple-touch-icon" href="{asset_prefix}assets/apple-touch-icon.png" sizes="180x180" />
  <link rel="stylesheet" href="{asset_prefix}styles.css?v=3" />
  <script src="{asset_prefix}theme.js"></script>
  {ld_scripts}
</head>"""


def _render_shell_footer(lang: str) -> str:
    top_label = "Torna su" if lang == "it" else "Back to top"
    quote_text = (
        "Note di ricerca, progetti e riflessioni."
        if lang == "it"
        else "Research notes, projects &amp; reflections."
    )
    return f"""      <footer class="card site-footer" role="contentinfo">
        <div>© Alessandro Balbina (2026)</div>
        <span class="site-footer-quote">{quote_text}</span>
      </footer>
    </main>
  </div>
  <button class="back-to-top" aria-label="{top_label}" title="{top_label}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"
      stroke-linejoin="round" aria-hidden="true" focusable="false">
      <polyline points="18 15 12 9 6 15"></polyline>
    </svg>
  </button>
</body>

</html>"""


def render_post_page(post: dict[str, Any], lang: str, asset_prefix: str) -> str:
    """Render an individual bilingual blog article page."""
    slug = post["slug"]
    data = post[lang]
    meta = data["meta"]
    title = str(meta.get("title", slug))
    excerpt = str(meta.get("excerpt", ""))
    category = str(meta.get("category", "Notes"))
    tags = meta.get("tags", [])
    date_str = post["date"]
    formatted_date = _format_date(date_str, lang)
    min_label = f"{data['reading_time']} min di lettura" if lang == "it" else f"{data['reading_time']} min read"
    en_url = f"{SITE_ORIGIN}/blog/{slug}/"
    it_url = f"{SITE_ORIGIN}/it/blog/{slug}/"
    canonical_url = it_url if lang == "it" else en_url
    lang_switch_href = f"{asset_prefix}blog/{slug}/" if lang == "it" else f"{asset_prefix}it/blog/{slug}/"
    lang_switch_text = "Read in English" if lang == "it" else "Leggi in Italiano"
    back_href = f"{asset_prefix}it/blog/" if lang == "it" else f"{asset_prefix}blog/"
    back_text = "← Torna al Blog" if lang == "it" else "← Back to Blog"
    skip_text = "Vai al contenuto principale" if lang == "it" else "Skip to main content"

    cover_html = ""
    if post["cover"]:
        cover_src = _resolve_asset(post["cover"], asset_prefix)
        cover_html = (
            f'<figure class="blog-figure blog-cover">'
            f'<img src="{html.escape(cover_src)}" alt="{html.escape(title)}" loading="eager" decoding="async">'
            f"</figure>"
        )

    tags_html = "".join(f'<span class="blog-tag">{html.escape(str(t))}</span>' for t in tags)
    person_ref = {
        "@type": "Person",
        "@id": f"{SITE_ORIGIN}/#person",
        "name": "Alessandro Balbina",
        "url": SITE_ORIGIN,
    }
    cover_abs = f"{SITE_ORIGIN}/{post['cover'].lstrip('/')}" if post["cover"] else f"{SITE_ORIGIN}/assets/og-preview.png"
    word_count = len(re.findall(r"\b\w+\b", data["body_md"]))
    iso_published = f"{date_str}T09:00:00+01:00"
    post_schema = {
        "@context": "https://schema.org",
        "@type": ["NewsArticle", "BlogPosting"],
        "headline": title,
        "description": excerpt,
        "datePublished": iso_published,
        "dateModified": iso_published,
        "inLanguage": lang,
        "articleSection": category,
        "keywords": [str(t) for t in tags],
        "wordCount": word_count,
        "timeRequired": f"PT{data['reading_time']}M",
        "isAccessibleForFree": True,
        "image": [cover_abs],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
        "author": person_ref,
        "publisher": person_ref,
        "url": canonical_url,
    }
    home_abs = f"{SITE_ORIGIN}/it/" if lang == "it" else f"{SITE_ORIGIN}/"
    blog_abs = f"{SITE_ORIGIN}/it/blog/" if lang == "it" else f"{SITE_ORIGIN}/blog/"
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": home_abs},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": blog_abs},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical_url},
        ],
    }
    head = _render_shell_head(
        lang=lang,
        title=f"{title} | Alessandro Balbina",
        description=excerpt,
        canonical_url=canonical_url,
        en_url=en_url,
        it_url=it_url,
        asset_prefix=asset_prefix,
        og_type="article",
        schema_objs=[post_schema, breadcrumb_schema],
        keywords=[str(t) for t in tags],
        article_meta={"published": date_str, "section": category, "tags": tags},
        og_image=cover_abs,
    )
    topbar = _render_topbar(lang, asset_prefix, lang_switch_href, active="blog")
    footer = _render_shell_footer(lang)
    return f"""{head}
<body>
  <a href="#main-content" class="skip-link">{skip_text}</a>
  <div class="page">
{topbar}
    <main id="main-content">
      <article class="card blog-article">
        <nav class="blog-breadcrumb" aria-label="Breadcrumb">
          <a href="{back_href}">{back_text}</a>
          <a href="{lang_switch_href}" class="blog-lang-pill">{lang_switch_text}</a>
        </nav>
        <header class="blog-article-header">
          <div class="blog-meta">
            <span class="blog-category-pill">{html.escape(category)}</span>
            <time datetime="{html.escape(date_str)}">{formatted_date}</time>
            <span>· {min_label}</span>
          </div>
          <h1>{html.escape(title)}</h1>
          <p class="blog-lead">{html.escape(excerpt)}</p>
          <div class="blog-tags">{tags_html}</div>
        </header>
        {cover_html}
        <div class="blog-prose">
{data["body_html"]}
        </div>
        <footer class="blog-article-footer">
          <a href="{back_href}">{back_text}</a>
          <a href="{lang_switch_href}" class="blog-lang-pill">{lang_switch_text}</a>
        </footer>
      </article>
{footer}"""


def render_index_page(posts: list[dict[str, Any]], lang: str, asset_prefix: str) -> str:
    """Render /blog/index.html or /it/blog/index.html with category filter buttons."""
    is_it = lang == "it"
    title = "Blog & Note di Ricerca | Alessandro Balbina" if is_it else "Blog & Research Notes | Alessandro Balbina"
    desc = (
        "Articoli, aggiornamenti sui progetti in corso e riflessioni su AI, cloud ed edge computing."
        if is_it
        else "Articles, ongoing project updates, and reflections on AI, cloud, and edge computing."
    )
    en_url = f"{SITE_ORIGIN}/blog/"
    it_url = f"{SITE_ORIGIN}/it/blog/"
    canonical_url = it_url if is_it else en_url
    lang_switch_href = f"{asset_prefix}blog/" if is_it else f"{asset_prefix}it/blog/"
    skip_text = "Vai al contenuto principale" if is_it else "Skip to main content"
    all_label = "Tutti" if is_it else "All"
    empty_label = "Nessun articolo in questa categoria." if is_it else "No articles found in this category."

    categories = sorted({str(p[lang]["meta"].get("category", "Notes")) for p in posts})
    filter_buttons = [
        f'<button type="button" class="blog-filter-btn is-active" data-filter="all" aria-pressed="true">{all_label}</button>'
    ]
    for cat in categories:
        cat_esc = html.escape(cat)
        filter_buttons.append(
            f'<button type="button" class="blog-filter-btn" data-filter="{cat_esc.lower()}" aria-pressed="false">{cat_esc}</button>'
        )

    read_label = "Leggi" if is_it else "Read"
    cards_html: list[str] = []
    for p in posts:
        slug = p["slug"]
        data = p[lang]
        meta = data["meta"]
        cat = str(meta.get("category", "Notes"))
        post_href = f"{slug}/"
        min_label = f"{data['reading_time']} min"
        cover_block = ""
        if p["cover"]:
            cover_src = _resolve_asset(p["cover"], asset_prefix)
            cover_block = (
                f'<a href="{post_href}" class="blog-card-cover-link" tabindex="-1" aria-hidden="true">'
                f'<img class="blog-card-cover" src="{html.escape(cover_src)}" '
                f'alt="{html.escape(str(meta.get("title", slug)))}" loading="lazy" decoding="async">'
                f"</a>"
            )
        cards_html.append(
            f'<article class="blog-card" data-category="{html.escape(cat.lower())}">'
            f"{cover_block}"
            f'<div class="blog-card-body">'
            f'<div class="blog-meta">'
            f'<span class="blog-category-pill">{html.escape(cat)}</span>'
            f'<time datetime="{html.escape(p["date"])}">{_format_date(p["date"], lang)}</time>'
            f"<span>· {min_label}</span>"
            f"</div>"
            f'<h2><a href="{post_href}">{html.escape(str(meta.get("title", slug)))}</a></h2>'
            f'<p>{html.escape(str(meta.get("excerpt", "")))}</p>'
            f'<div class="blog-card-footer">'
            f'<a href="{post_href}" class="blog-read-btn">{read_label} <span aria-hidden="true">→</span></a>'
            f"</div>"
            f"</div></article>"
        )

    blog_posts_ld = [
        {
            "@type": "BlogPosting",
            "headline": str(p[lang]["meta"].get("title", p["slug"])),
            "description": str(p[lang]["meta"].get("excerpt", "")),
            "url": f"{SITE_ORIGIN}/it/blog/{p['slug']}/" if is_it else f"{SITE_ORIGIN}/blog/{p['slug']}/",
            "datePublished": f"{p['date']}T09:00:00+01:00",
            "image": (
                f"{SITE_ORIGIN}/{p['cover'].lstrip('/')}"
                if p["cover"]
                else f"{SITE_ORIGIN}/assets/og-preview.png"
            ),
            "author": {"@type": "Person", "name": "Alessandro Balbina", "url": SITE_ORIGIN},
        }
        for p in posts
    ]
    schema_obj = {
        "@context": "https://schema.org",
        "@type": ["CollectionPage", "Blog"],
        "name": title,
        "description": desc,
        "url": canonical_url,
        "inLanguage": lang,
        "blogPost": blog_posts_ld,
    }
    home_abs = f"{SITE_ORIGIN}/it/" if is_it else f"{SITE_ORIGIN}/"
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": home_abs},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": canonical_url},
        ],
    }
    head = _render_shell_head(
        lang=lang,
        title=title,
        description=desc,
        canonical_url=canonical_url,
        en_url=en_url,
        it_url=it_url,
        asset_prefix=asset_prefix,
        og_type="website",
        schema_objs=[schema_obj, breadcrumb_schema],
        robots_meta="index, follow, max-image-preview:large" if posts else "noindex, follow",
    )
    topbar = _render_topbar(lang, asset_prefix, lang_switch_href, active="blog")
    footer = _render_shell_footer(lang)
    heading = "Blog &amp; Note di Ricerca" if is_it else "Blog &amp; Research Notes"
    empty_attr = ' aria-live="polite" hidden' if posts else ' aria-live="polite"'
    unica_alt = "Logo Università degli Studi di Cagliari" if is_it else "University of Cagliari Logo"
    filter_aria = "Filtra articoli per categoria" if is_it else "Filter posts by category"
    articles_aria = "Articoli" if is_it else "Articles"

    return f"""{head}
<body>
  <a href="#main-content" class="skip-link">{skip_text}</a>
  <div class="page">
{topbar}
    <main id="main-content">
      <header class="hero card hero--full-width" aria-labelledby="blog-index-title">
        <div class="hero-copy hero-copy--wide">
          <img src="{asset_prefix}assets/unica-logo.svg" alt="{unica_alt}" class="unica-logo" width="320" height="51" loading="eager" />
          <h1 id="blog-index-title">{heading}</h1>
          <p class="lead">{html.escape(desc)}</p>
          <div class="blog-filter-bar" role="group" aria-label="{filter_aria}">
            {"".join(filter_buttons)}
          </div>
        </div>
      </header>
      <section class="blog-grid" aria-label="{articles_aria}">
        {"".join(cards_html)}
        <p class="card blog-empty-state"{empty_attr}>{empty_label}</p>
      </section>
{footer}"""


def render_rss_feed(posts: list[dict[str, Any]], lang: str) -> str:
    """Render RSS 2.0 XML feed for EN or IT."""
    is_it = lang == "it"
    feed_title = "Alessandro Balbina — Blog (IT)" if is_it else "Alessandro Balbina — Blog (EN)"
    feed_link = f"{SITE_ORIGIN}/it/blog/" if is_it else f"{SITE_ORIGIN}/blog/"
    feed_desc = (
        "Note di ricerca, progetti e riflessioni di Alessandro Balbina."
        if is_it
        else "Research notes, projects, and reflections by Alessandro Balbina."
    )
    items: list[str] = []
    for p in posts:
        slug = p["slug"]
        data = p[lang]
        meta = data["meta"]
        link = f"{SITE_ORIGIN}/it/blog/{slug}/" if is_it else f"{SITE_ORIGIN}/blog/{slug}/"
        try:
            pub_dt = datetime.strptime(p["date"], "%Y-%m-%d")
            pub_date = format_datetime(pub_dt)
        except ValueError:
            pub_date = p["date"]
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(str(meta.get('title', slug)))}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid>{link}</guid>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <description>{html.escape(str(meta.get('excerpt', '')))}</description>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{html.escape(feed_title)}</title>\n"
        f"    <link>{feed_link}</link>\n"
        f"    <description>{html.escape(feed_desc)}</description>\n"
        f"    <language>{lang}</language>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )


def update_marker_block(file_path: Path, start_marker: str, end_marker: str, replacement: str) -> None:
    """Replace content between start_marker and end_marker in file_path."""
    if not file_path.exists():
        return
    content = file_path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(content):
        return
    new_block = f"{start_marker}\n{replacement}\n{end_marker}"
    file_path.write_text(pattern.sub(new_block, content, count=1), encoding="utf-8")


def _render_homepage_latest(posts: list[dict[str, Any]], lang: str) -> str:
    if not posts:
        return ""
    is_it = lang == "it"
    heading = "Dal Blog" if is_it else "Latest from the Blog"
    all_label = "Tutti gli articoli →" if is_it else "All articles →"
    blog_root = "blog/"
    read_label = "Leggi" if is_it else "Read"
    cards: list[str] = []
    for p in posts[:3]:
        slug = p["slug"]
        data = p[lang]
        meta = data["meta"]
        href = f"{blog_root}{slug}/"
        cards.append(
            f'<article class="blog-preview-item">'
            f'<div class="blog-meta"><span class="blog-category-pill">{html.escape(str(meta.get("category", "")))}</span>'
            f'<time datetime="{html.escape(p["date"])}">{_format_date(p["date"], lang)}</time></div>'
            f'<h3><a href="{href}">{html.escape(str(meta.get("title", slug)))}</a></h3>'
            f'<p>{html.escape(str(meta.get("excerpt", "")))}</p>'
            f'<div class="blog-card-footer">'
            f'<a href="{href}" class="blog-read-btn">{read_label} <span aria-hidden="true">→</span></a>'
            f"</div>"
            f"</article>"
        )
    return (
        f'<section aria-labelledby="latest-blog-title" class="card">\n'
        f'  <div class="blog-preview-header"><h2 id="latest-blog-title">{heading}</h2>'
        f'<a href="{blog_root}" class="blog-preview-all">{all_label}</a></div>\n'
        f'  <div class="blog-preview-grid">{"".join(cards)}</div>\n'
        f"</section>"
    )


def _render_sitemap_entries(posts: list[dict[str, Any]]) -> str:
    if not posts:
        return ""
    latest_date = posts[0]["date"]
    entries = [
        f"""  <url>
    <loc>{SITE_ORIGIN}/blog/</loc>
    <lastmod>{html.escape(latest_date)}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE_ORIGIN}/blog/" />
    <xhtml:link rel="alternate" hreflang="it" href="{SITE_ORIGIN}/it/blog/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_ORIGIN}/blog/" />
  </url>
  <url>
    <loc>{SITE_ORIGIN}/it/blog/</loc>
    <lastmod>{html.escape(latest_date)}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE_ORIGIN}/blog/" />
    <xhtml:link rel="alternate" hreflang="it" href="{SITE_ORIGIN}/it/blog/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_ORIGIN}/blog/" />
  </url>"""
    ]
    for p in posts:
        slug = p["slug"]
        en_u = f"{SITE_ORIGIN}/blog/{slug}/"
        it_u = f"{SITE_ORIGIN}/it/blog/{slug}/"
        for lang_key, loc in (("en", en_u), ("it", it_u)):
            img_block = ""
            if p["cover"] and not p["cover"].startswith(("http://", "https://")):
                img_loc = f"{SITE_ORIGIN}/{p['cover'].lstrip('/')}"
                img_title = html.escape(str(p[lang_key]["meta"].get("title", slug)))
                img_block = (
                    f"\n    <image:image>\n"
                    f"      <image:loc>{html.escape(img_loc)}</image:loc>\n"
                    f"      <image:title>{img_title}</image:title>\n"
                    f"    </image:image>"
                )
            entries.append(
                f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{html.escape(p["date"])}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <xhtml:link rel="alternate" hreflang="en" href="{en_u}" />
    <xhtml:link rel="alternate" hreflang="it" href="{it_u}" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{en_u}" />{img_block}
  </url>"""
            )
    return "\n".join(entries)


def build_site(root_dir: Path) -> dict[str, int]:
    """Build bilingual blog HTML pages, RSS feeds, homepage previews, and sitemap."""
    posts = load_posts(root_dir / "content" / "blog")

    en_blog_dir = root_dir / "blog"
    it_blog_dir = root_dir / "it" / "blog"
    en_blog_dir.mkdir(parents=True, exist_ok=True)
    it_blog_dir.mkdir(parents=True, exist_ok=True)

    (en_blog_dir / "index.html").write_text(render_index_page(posts, "en", "../"), encoding="utf-8")
    (it_blog_dir / "index.html").write_text(render_index_page(posts, "it", "../../"), encoding="utf-8")

    active_slugs = {post["slug"] for post in posts}
    for base_dir in (en_blog_dir, it_blog_dir):
        for child in base_dir.iterdir():
            if child.is_dir() and child.name not in active_slugs:
                shutil.rmtree(child)

    for post in posts:
        slug = post["slug"]
        en_post_dir = en_blog_dir / slug
        it_post_dir = it_blog_dir / slug
        en_post_dir.mkdir(parents=True, exist_ok=True)
        it_post_dir.mkdir(parents=True, exist_ok=True)
        (en_post_dir / "index.html").write_text(render_post_page(post, "en", "../../"), encoding="utf-8")
        (it_post_dir / "index.html").write_text(render_post_page(post, "it", "../../../"), encoding="utf-8")

    (root_dir / "feed.xml").write_text(render_rss_feed(posts, "en"), encoding="utf-8")
    (root_dir / "it" / "feed.xml").write_text(render_rss_feed(posts, "it"), encoding="utf-8")

    nav_targets = (
        (root_dir / "index.html", '<a href="blog/">Blog</a>'),
        (root_dir / "it" / "index.html", '<a href="blog/">Blog</a>'),
        (root_dir / "contact" / "index.html", '<a href="../blog/">Blog</a>'),
        (root_dir / "it" / "contact" / "index.html", '<a href="../blog/">Blog</a>'),
        (root_dir / "other-projects" / "index.html", '<a href="../blog/">Blog</a>'),
        (root_dir / "it" / "other-projects" / "index.html", '<a href="../blog/">Blog</a>'),
    )
    for nav_file, nav_link in nav_targets:
        update_marker_block(
            nav_file,
            "<!-- BLOG_NAV_START -->",
            "<!-- BLOG_NAV_END -->",
            nav_link if posts else "",
        )

    update_marker_block(
        root_dir / "index.html",
        "<!-- BLOG_LATEST_START -->",
        "<!-- BLOG_LATEST_END -->",
        _render_homepage_latest(posts, "en"),
    )
    update_marker_block(
        root_dir / "it" / "index.html",
        "<!-- BLOG_LATEST_START -->",
        "<!-- BLOG_LATEST_END -->",
        _render_homepage_latest(posts, "it"),
    )
    update_marker_block(
        root_dir / "sitemap.xml",
        "<!-- BLOG_SITEMAP_START -->",
        "<!-- BLOG_SITEMAP_END -->",
        _render_sitemap_entries(posts),
    )

    return {"posts": len(posts), "pages": len(posts) * 2 + 2, "feeds": 2}


if __name__ == "__main__":
    summary = build_site(Path(__file__).resolve().parent.parent)
    print(f"Built {summary['posts']} posts ({summary['pages']} HTML pages, {summary['feeds']} RSS feeds).")
