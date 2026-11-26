import tempfile
import unittest
from pathlib import Path

from scripts.build_blog import (
    build_site,
    estimate_reading_time,
    load_posts,
    markdown_to_html,
    parse_frontmatter,
)


class TestBlogParser(unittest.TestCase):
    def test_parse_frontmatter_extracts_fields_and_tags_list(self) -> None:
        raw = (
            "---\n"
            "title: Research Notes on AI\n"
            "date: 2026-11-26\n"
            "category: Research\n"
            "tags: [AI, Sustainability, Cloud]\n"
            "excerpt: Exploring energy-aware architectures.\n"
            "cover: assets/blog/sample/cover.svg\n"
            "draft: false\n"
            "---\n\n"
            "# Heading\n\nBody text.\n"
        )
        meta, body = parse_frontmatter(raw)
        self.assertEqual(meta["title"], "Research Notes on AI")
        self.assertEqual(meta["date"], "2026-11-26")
        self.assertEqual(meta["category"], "Research")
        self.assertEqual(meta["tags"], ["AI", "Sustainability", "Cloud"])
        self.assertEqual(meta["excerpt"], "Exploring energy-aware architectures.")
        self.assertEqual(meta["cover"], "assets/blog/sample/cover.svg")
        self.assertFalse(meta["draft"])
        self.assertTrue(body.startswith("# Heading"))

    def test_markdown_to_html_renders_elements_and_escapes_scripts(self) -> None:
        md = (
            "## Overview\n\n"
            "A **bold** and *italic* note with `code` and [link](https://example.com).\n\n"
            "- First item\n"
            "- Second item\n\n"
            "> A thoughtful quote.\n\n"
            "```python\nprint('hello')\n```\n\n"
            '![System chart](../../assets/blog/test/chart.svg "Architecture overview")\n\n'
            '<figure class="blog-figure"><div class="blog-chart">'
            '<svg viewBox="0 0 100 40" role="img" aria-label="Chart">'
            '<rect x="0" y="0" width="50" height="40" fill="currentColor"></rect>'
            "</svg></div><figcaption>Live SVG chart</figcaption></figure>\n\n"
            "<script>alert('xss')</script>\n"
        )
        html_out = markdown_to_html(md)
        self.assertIn("<h2>Overview</h2>", html_out)
        self.assertIn("<strong>bold</strong>", html_out)
        self.assertIn("<em>italic</em>", html_out)
        self.assertIn("<code>code</code>", html_out)
        self.assertIn('<a href="https://example.com" rel="noopener noreferrer">link</a>', html_out)
        self.assertIn("<ul>\n<li>First item</li>\n<li>Second item</li>\n</ul>", html_out)
        self.assertIn("<blockquote><p>A thoughtful quote.</p></blockquote>", html_out)
        self.assertIn("<pre><code>print(&#x27;hello&#x27;)</code></pre>", html_out)
        self.assertIn('<figure class="blog-figure">', html_out)
        self.assertIn('loading="lazy" decoding="async"', html_out)
        self.assertIn("<figcaption>Architecture overview</figcaption>", html_out)
        self.assertIn('<svg viewBox="0 0 100 40"', html_out)
        self.assertNotIn("<script>", html_out)
        self.assertIn("&lt;script&gt;", html_out)

    def test_estimate_reading_time_minimum_one_minute(self) -> None:
        self.assertEqual(estimate_reading_time("Just a few words."), 1)
        long_text = " ".join(["word"] * 450)
        self.assertEqual(estimate_reading_time(long_text), 3)

    def test_load_posts_raises_on_missing_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            post_dir = Path(tmp) / "missing-it"
            post_dir.mkdir(parents=True)
            (post_dir / "en.md").write_text(
                "---\ntitle: Only EN\ndate: 2026-11-26\ncategory: Research\n"
                "tags: [AI]\nexcerpt: Test\ndraft: false\n---\n\nHello.\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                load_posts(Path(tmp))
            self.assertIn("missing-it", str(ctx.exception))
            self.assertIn("it.md", str(ctx.exception))

    def test_load_posts_skips_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            post_dir = Path(tmp) / "draft-post"
            post_dir.mkdir(parents=True)
            content = (
                "---\ntitle: Draft\ndate: 2026-11-26\ncategory: Research\n"
                "tags: [AI]\nexcerpt: Test\ndraft: true\n---\n\nBody.\n"
            )
            (post_dir / "en.md").write_text(content, encoding="utf-8")
            (post_dir / "it.md").write_text(content, encoding="utf-8")
            self.assertEqual(load_posts(Path(tmp)), [])

    def test_build_site_generates_bilingual_pages_rss_and_updates_markers(self) -> None:
        import xml.etree.ElementTree as ET

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post_dir = root / "content" / "blog" / "sample-post"
            post_dir.mkdir(parents=True)
            (post_dir / "en.md").write_text(
                "---\ntitle: Sample Post\ndate: 2026-11-26\ncategory: Research\n"
                "tags: [AI, Cloud]\nexcerpt: English excerpt.\n"
                "cover: assets/blog/sample-post/cover.svg\ndraft: false\n---\n\n"
                "## Section\n\nEnglish body.\n",
                encoding="utf-8",
            )
            (post_dir / "it.md").write_text(
                "---\ntitle: Articolo di Prova\ndate: 2026-11-26\ncategory: Ricerca\n"
                "tags: [AI, Cloud]\nexcerpt: Estratto italiano.\n"
                "cover: assets/blog/sample-post/cover.svg\ndraft: false\n---\n\n"
                "## Sezione\n\nTesto italiano.\n",
                encoding="utf-8",
            )
            (root / "index.html").write_text(
                "<html><body><!-- BLOG_LATEST_START --><!-- BLOG_LATEST_END --></body></html>",
                encoding="utf-8",
            )
            (root / "it").mkdir()
            (root / "it" / "index.html").write_text(
                "<html><body><!-- BLOG_LATEST_START --><!-- BLOG_LATEST_END --></body></html>",
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                "<!-- BLOG_SITEMAP_START --><!-- BLOG_SITEMAP_END -->\n"
                "</urlset>\n",
                encoding="utf-8",
            )

            stats = build_site(root)
            self.assertEqual(stats["posts"], 1)

            en_idx = (root / "blog" / "index.html").read_text(encoding="utf-8")
            it_idx = (root / "it" / "blog" / "index.html").read_text(encoding="utf-8")
            en_post = (root / "blog" / "sample-post" / "index.html").read_text(encoding="utf-8")
            it_post = (root / "it" / "blog" / "sample-post" / "index.html").read_text(encoding="utf-8")

            self.assertIn("../styles.css", en_idx)
            self.assertIn("../theme.js", en_idx)
            self.assertIn("../../styles.css", it_idx)
            self.assertIn("../../theme.js", it_idx)
            self.assertIn("../../styles.css", en_post)
            self.assertIn('hreflang="it" href="https://alessandrobalbina.github.io/it/blog/sample-post/"', en_post)
            self.assertIn("../../../styles.css", it_post)
            self.assertNotIn("<script>", en_post.split("</head>")[1])
            self.assertIn('class="blog-read-btn"', en_idx)
            self.assertIn('class="blog-card-cover-link"', en_idx)
            self.assertIn(">Read <span", en_idx)
            self.assertIn(">Leggi <span", it_idx)
            self.assertIn('class="blog-article-footer"', en_post)
            self.assertIn('name="twitter:card"', en_post)
            self.assertIn('property="article:published_time"', en_post)
            self.assertIn('"@type": "BreadcrumbList"', en_post)
            self.assertIn('"@type": "BlogPosting"', en_idx)

            en_rss = ET.fromstring((root / "feed.xml").read_text(encoding="utf-8"))
            it_rss = ET.fromstring((root / "it" / "feed.xml").read_text(encoding="utf-8"))
            self.assertEqual(en_rss.find(".//item/title").text, "Sample Post")
            self.assertEqual(it_rss.find(".//item/title").text, "Articolo di Prova")

            home_en = (root / "index.html").read_text(encoding="utf-8")
            home_it = (root / "it" / "index.html").read_text(encoding="utf-8")
            sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("Sample Post", home_en)
            self.assertIn("Articolo di Prova", home_it)
            self.assertIn('class="blog-read-btn"', home_en)
            self.assertIn('class="blog-read-btn"', home_it)
            self.assertIn("https://alessandrobalbina.github.io/blog/sample-post/", sitemap)


if __name__ == "__main__":
    unittest.main()
