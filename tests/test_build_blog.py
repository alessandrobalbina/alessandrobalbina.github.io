import tempfile
import unittest
from pathlib import Path

from scripts.build_blog import (
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


if __name__ == "__main__":
    unittest.main()
