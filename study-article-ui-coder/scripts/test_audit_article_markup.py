#!/usr/bin/env python3
"""audit_article_markup.py の単体テスト。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("audit_article_markup.py")
SPEC = importlib.util.spec_from_file_location("audit_article_markup", SCRIPT_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def codes(text: str, target: str) -> set[str]:
    return {issue.code for issue in AUDIT.audit_document(text, target)}


class AuditArticleMarkupTests(unittest.TestCase):
    def test_readability_empty_and_repeated_breaks(self) -> None:
        found = AUDIT.readability_warnings('<p> &nbsp; </p><p>本文<br />\n<!--注--><br><br>続き</p>', 'astro-markdown')
        self.assertEqual([x.code for x in found], ['EMPTY_PARAGRAPH', 'CONSECUTIVE_BREAKS'])
        self.assertTrue(all(x.severity == 'warning' for x in found))

    def test_readability_single_break_and_media_are_valid(self) -> None:
        text = '<p>本文<br>続き</p><p><img src="x" alt="図"></p><p><code>例</code></p><p>`code`</p>'
        self.assertEqual(AUDIT.readability_warnings(text, 'astro-markdown'), [])

    def test_readability_ignores_html_code_and_escaped_examples(self) -> None:
        text = '<pre><code>&lt;p&gt;&lt;/p&gt;</code><br><br></pre><code><br><br></code><p>&lt;p&gt;&lt;/p&gt;</p>'
        self.assertEqual(AUDIT.readability_warnings(text, 'standalone-html'), [])

    def test_readability_ignores_markdown_code(self) -> None:
        text = '```html\n<p></p><br><br>\n```\n~~~html\n<p></p>\n~~~\n`<p></p>`\n    <p></p>\n'
        self.assertEqual(AUDIT.readability_warnings(text, 'astro-markdown'), [])

    def test_readability_keeps_source_line_numbers(self) -> None:
        text = '---\ntitle: 例\n---\n```html\n<p></p>\n```\n<p></p>\n'
        found = AUDIT.readability_warnings(text, 'astro-markdown')
        self.assertEqual([(x.code, x.line) for x in found], [('EMPTY_PARAGRAPH', 7)])

    def test_cli_warning_opt_in_preserves_contract(self) -> None:
        command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPT_PATH), '--target', 'astro-markdown']
        original = subprocess.run(command, input='<p></p>', text=True, encoding='utf-8', capture_output=True, check=False)
        extended = subprocess.run(command + ['--readability-warnings'], input='<p></p>', text=True, encoding='utf-8', capture_output=True, check=False)
        before, after = json.loads(original.stdout), json.loads(extended.stdout)
        self.assertEqual(original.returncode, 0)
        self.assertEqual(extended.returncode, 0)
        self.assertEqual(set(before), {'target', 'passed', 'issue_count', 'issues'})
        self.assertEqual(before, {k: after[k] for k in before})
        self.assertEqual(after['warning_count'], 1)

    def test_cli_errors_remain_errors_with_warnings(self) -> None:
        command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPT_PATH), '--target', 'astro-markdown', '--readability-warnings']
        result = subprocess.run(command, input='<p style="color:red"></p>', text=True, encoding='utf-8', capture_output=True, check=False)
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(data['passed'])
        self.assertEqual(data['warning_count'], 1)
        self.assertEqual([x['code'] for x in data['issues']], ['INLINE_STYLE'])

    def test_valid_standalone_template(self) -> None:
        template = SCRIPT_PATH.parent.parent.joinpath("assets", "standalone-article-template.html").read_text(encoding="utf-8")
        self.assertEqual(codes(template, "standalone-html"), set())

    def test_nested_link_and_missing_anchor(self) -> None:
        html = """<!doctype html><html lang='ja'><head><meta name='viewport' content='width=device-width'><style></style></head><body><main class='edu-article'><h1>題</h1><a class='edu-link' href='#none'><a class='edu-link' href='/x'>x</a></a></main></body></html>"""
        found = codes(html, "standalone-html")
        self.assertIn("NESTED_LINK", found)
        self.assertIn("MISSING_ANCHOR", found)

    def test_table_requires_wrapper(self) -> None:
        html = """<!doctype html><html lang='ja'><head><meta name='viewport' content='width=device-width'><style></style></head><body><main class='edu-article'><h1>題</h1><table class='edu-table'></table></main></body></html>"""
        self.assertIn("TABLE_NOT_WRAPPED", codes(html, "standalone-html"))

    def test_dangerous_markup_and_event(self) -> None:
        html = """<!doctype html><html lang='ja'><head><meta name='viewport' content='width=device-width'><style></style></head><body><main class='edu-article'><h1>題</h1><script>x</script><img class='edu-image' src='x' onerror='x'></main></body></html>"""
        found = codes(html, "standalone-html")
        self.assertIn("FORBIDDEN_TAG", found)
        self.assertIn("EVENT_ATTRIBUTE", found)
        self.assertIn("MISSING_ALT", found)

    def test_valid_astro_markdown(self) -> None:
        markdown = """---
title: 記事タイトル
draft: true
---

導入文。

## 見出し

【結論】
本文。
"""
        self.assertEqual(codes(markdown, "astro-markdown"), set())

    def test_astro_forbids_body_h1_and_style(self) -> None:
        markdown = """---
title: 記事タイトル
---
# 重複H1
<p style='color:red'>本文</p>
"""
        found = codes(markdown, "astro-markdown")
        self.assertIn("ASTRO_BODY_H1", found)
        self.assertIn("INLINE_STYLE", found)

    def test_astro_unknown_class(self) -> None:
        markdown = "<aside class='invented-card'>本文</aside>"
        self.assertIn("UNSUPPORTED_CLASS", codes(markdown, "astro-markdown"))

    def test_svg_rejects_external_features(self) -> None:
        html = """<!doctype html><html lang='ja'><head><meta name='viewport' content='width=device-width'><style></style></head><body><main class='edu-article'><h1>題</h1><svg class='edu-diagram' viewBox='0 0 10 10'><foreignObject onload='x'></foreignObject></svg></main></body></html>"""
        found = codes(html, "standalone-html")
        self.assertIn("SVG_FORBIDDEN_TAG", found)
        self.assertIn("SVG_FORBIDDEN_ATTRIBUTE", found)

    def test_placeholder_url(self) -> None:
        html = """<!doctype html><html lang='ja'><head><meta name='viewport' content='width=device-width'><style></style></head><body><main class='edu-article'><h1>題</h1><a class='edu-link' href='#'>仮</a></main></body></html>"""
        self.assertIn("PLACEHOLDER_URL", codes(html, "standalone-html"))


if __name__ == "__main__":
    unittest.main()
