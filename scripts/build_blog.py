"""Zero-dependency static blog generator for alessandrobalbina.github.io."""

from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any

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
