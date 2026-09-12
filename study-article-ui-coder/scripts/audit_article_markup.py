#!/usr/bin/env python3
"""教育記事UIの決定的な静的監査。入力ファイルは変更しない。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


ASTRO_CLASS_PREFIXES = ("article-callout", "article-link-card", "scroll-table")
FORBIDDEN_TAGS = {"script", "iframe", "object", "embed"}
SVG_ALLOWED_TAGS = {
    "svg", "g", "path", "rect", "circle", "line", "polyline", "polygon",
    "text", "title", "desc",
}
SVG_ALLOWED_ATTRS = {
    "id", "class", "xmlns", "viewbox", "width", "height", "x", "y", "x1",
    "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "d", "points",
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "transform", "role", "focusable", "aria-hidden", "aria-label",
    "aria-labelledby",
}
URL_ATTRS = {"href", "src", "xlink:href", "formaction", "action"}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    line: int
    severity: str = "error"

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
        }


class MarkupAuditParser(HTMLParser):
    def __init__(self, target: str, allowed_classes: Iterable[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.target = target
        self.allowed_classes = tuple(allowed_classes)
        self.issues: list[Issue] = []
        self.stack: list[tuple[str, set[str], int]] = []
        self.ids: dict[str, int] = {}
        self.anchor_refs: list[tuple[str, int]] = []
        self.h1_count = 0
        self.main_count = 0
        self.style_count = 0
        self.has_doctype = False
        self.has_viewport = False
        self.html_lang = ""
        self.svg_depth = 0

    def add(self, code: str, message: str, line: int | None = None) -> None:
        self.issues.append(Issue(code, message, line or self.getpos()[0]))

    def handle_decl(self, decl: str) -> None:
        if decl.strip().lower() == "doctype html":
            self.has_doctype = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        line = self.getpos()[0]
        attr_map = {name.lower(): (value or "") for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        ancestors = [entry[0] for entry in self.stack]
        in_svg = self.svg_depth > 0 or tag == "svg"

        if tag == "html":
            self.html_lang = attr_map.get("lang", "")
        if tag == "meta" and attr_map.get("name", "").lower() == "viewport":
            self.has_viewport = True
        if tag == "h1":
            self.h1_count += 1
            if self.target == "astro-markdown":
                self.add("ASTRO_BODY_H1", "Astro本文へ<h1>を書かないでください。", line)
        if tag == "main":
            self.main_count += 1

        if tag in FORBIDDEN_TAGS:
            self.add("FORBIDDEN_TAG", f"禁止要素 <{tag}> が残っています。", line)
        if tag == "style":
            self.style_count += 1
            if self.target == "astro-markdown" or "head" not in ancestors:
                self.add("FORBIDDEN_STYLE", "許可されない<style>要素があります。", line)
        if self.target == "astro-markdown" and tag in {"html", "head", "body"}:
            self.add("ASTRO_LAYOUT_DUPLICATE", f"Astro本文へ<{tag}>を書かないでください。", line)

        if tag == "a" and "a" in ancestors:
            self.add("NESTED_LINK", "リンクの中に別のリンクがあります。", line)
        if tag == "img" and "alt" not in attr_map:
            self.add("MISSING_ALT", "img要素にalt属性がありません。", line)
        if tag == "table":
            wrapped = any("edu-table-scroll" in entry[1] or "scroll-table" in entry[1] for entry in self.stack)
            if not wrapped:
                self.add("TABLE_NOT_WRAPPED", "tableを登録済み横スクロールラッパーで囲んでください。", line)

        element_id = attr_map.get("id", "")
        if element_id:
            if element_id in self.ids:
                self.add("DUPLICATE_ID", f"id '{element_id}' が重複しています。", line)
            else:
                self.ids[element_id] = line

        for name, value in attr_map.items():
            if name.startswith("on"):
                self.add("EVENT_ATTRIBUTE", f"イベント属性 '{name}' は禁止です。", line)
            if name == "style":
                self.add("INLINE_STYLE", "style属性は使用できません。", line)
            if name in URL_ATTRS:
                normalized = value.strip().lower()
                if normalized == "#" or "todo" in normalized:
                    self.add("PLACEHOLDER_URL", f"仮URL '{value}' が残っています。", line)
                if normalized.startswith(("javascript:", "data:")):
                    self.add("DANGEROUS_URL", f"危険なURLスキーム '{value}' があります。", line)
                if name == "href" and normalized.startswith("#") and len(normalized) > 1:
                    self.anchor_refs.append((value[1:], line))

        if self.target == "standalone-html":
            for class_name in classes:
                if not class_name.startswith("edu-"):
                    self.add("UNSUPPORTED_CLASS", f"standaloneで未登録class '{class_name}' を使用しています。", line)
        else:
            prefixes = ASTRO_CLASS_PREFIXES + self.allowed_classes
            for class_name in classes:
                if not any(class_name == p or class_name.startswith(p + "__") or class_name.startswith(p + "--") for p in prefixes):
                    self.add("UNSUPPORTED_CLASS", f"Astroで許可されていないclass '{class_name}' です。", line)

        if in_svg:
            if tag not in SVG_ALLOWED_TAGS:
                self.add("SVG_FORBIDDEN_TAG", f"SVG内の<{tag}>は許可されていません。", line)
            for name, value in attr_map.items():
                if name.startswith("on") or name not in SVG_ALLOWED_ATTRS:
                    self.add("SVG_FORBIDDEN_ATTRIBUTE", f"SVG属性 '{name}' は許可されていません。", line)
                if "url(" in value.lower() or name in {"href", "xlink:href"}:
                    self.add("SVG_EXTERNAL_REFERENCE", "SVGの外部参照は許可されていません。", line)
            self.svg_depth += 1

        self.stack.append((tag, classes, line))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.svg_depth and tag == "svg":
            self.svg_depth = 0
        elif self.svg_depth:
            self.svg_depth = max(0, self.svg_depth - 1)

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def finalize(self) -> list[Issue]:
        for anchor, line in self.anchor_refs:
            if anchor not in self.ids:
                self.add("MISSING_ANCHOR", f"リンク先id '#{anchor}' が存在しません。", line)

        if self.target == "standalone-html":
            if not self.has_doctype:
                self.add("MISSING_DOCTYPE", "standalone HTMLに<!doctype html>がありません。", 1)
            if self.html_lang.lower() != "ja":
                self.add("MISSING_LANG", "standalone HTMLのlangをjaにしてください。", 1)
            if not self.has_viewport:
                self.add("MISSING_VIEWPORT", "viewport metaがありません。", 1)
            if self.h1_count != 1:
                self.add("H1_COUNT", f"standalone HTMLのH1は1つ必要です。現在{self.h1_count}個です。", 1)
            if self.main_count != 1:
                self.add("MAIN_COUNT", f"standalone HTMLのmainは1つ必要です。現在{self.main_count}個です。", 1)
            if self.style_count > 1:
                self.add("STYLE_COUNT", "standaloneのstyle要素はhead内の1つに統合してください。", 1)
        return self.issues


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    match = re.match(r"\A---\s*\n.*?\n---\s*\n", text, flags=re.DOTALL)
    return text[match.end():] if match else text


def audit_document(text: str, target: str, allowed_classes: Iterable[str] = ()) -> list[Issue]:
    body = strip_frontmatter(text) if target == "astro-markdown" else text
    parser = MarkupAuditParser(target, allowed_classes)
    parser.feed(body)
    parser.close()
    issues = parser.finalize()

    patterns = [
        (r"\bTODO\b", "TODO_TOKEN", "TODOが残っています。"),
        (r"\{\{[^{}]+\}\}", "TEMPLATE_TOKEN", "未解決のテンプレート記号があります。"),
    ]
    for pattern, code, message in patterns:
        for match in re.finditer(pattern, body, flags=re.IGNORECASE):
            issues.append(Issue(code, message, line_number(body, match.start())))

    if target == "astro-markdown":
        for match in re.finditer(r"(?m)^\s*#\s+\S", body):
            issues.append(Issue("ASTRO_BODY_H1", "Astro本文へMarkdown H1を書かないでください。", line_number(body, match.start())))
        for match in re.finditer(r"(?is)<svg\b", body):
            issues.append(Issue("ASTRO_INLINE_SVG", "Astro本文へ生のインラインSVGを書かないでください。", line_number(body, match.start())))

    unique = {(item.code, item.line, item.message): item for item in issues}
    return sorted(unique.values(), key=lambda item: (item.line, item.code, item.message))


class ReadabilityParser(HTMLParser):
    """補助的な生HTML警告。安全性・CSS・文章の意味の監査とは分離する。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.warnings: list[Issue] = []
        self.ignored: list[str] = []
        self.paragraph: tuple[int, bool] | None = None
        self.break_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.ignored:
            if tag in {"pre", "code", "script", "style", "textarea"}:
                self.ignored.append(tag)
            return
        if tag in {"pre", "code", "script", "style", "textarea"}:
            self.ignored.append(tag)
            self.break_count = 0
            if self.paragraph:
                self.paragraph = (self.paragraph[0], True)
            return
        if tag == "p":
            self.paragraph = (self.getpos()[0], False)
        if tag == "br":
            self.break_count += 1
            if self.break_count == 2:
                self.warnings.append(Issue("CONSECUTIVE_BREAKS", "連続改行が余白調整になっていないか確認してください。", self.getpos()[0], "warning"))
        elif tag not in {"span", "strong", "em", "b", "i", "a", "small"}:
            self.break_count = 0
        if tag in {"img", "svg", "input", "button", "video", "audio", "math"} and self.paragraph:
            self.paragraph = (self.paragraph[0], True)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == "p" and self.paragraph:
            line, meaningful = self.paragraph
            if not meaningful:
                self.warnings.append(Issue("EMPTY_PARAGRAPH", "空の段落が余白調整に使われていないか確認してください。", line, "warning"))
            self.paragraph = None
        if tag not in {"span", "strong", "em", "b", "i", "a", "small"}:
            self.break_count = 0

    def handle_data(self, data: str) -> None:
        if not self.ignored and data.strip():
            self.break_count = 0
            if self.paragraph:
                self.paragraph = (self.paragraph[0], True)


def readability_warnings(text: str, target: str) -> list[Issue]:
    """コード例を除外して空段落・連続brを警告する。入力・既存監査を変更しない。"""
    body = text
    if target == "astro-markdown":
        stripped = strip_frontmatter(text)
        body = "\n" * (text.count("\n") - stripped.count("\n")) + stripped
        # Markdownの完全な構文解析ではない。警告対象は生HTMLに限定する。
        lines = []
        fence: tuple[str, int] | None = None
        for line in body.splitlines(keepends=True):
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
            masked = fence is not None
            if marker:
                run, tail = marker.groups()
                if fence is None:
                    fence = (run[0], len(run))
                    masked = True
                elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                    fence = None
            if masked or line.startswith(("    ", "\t")):
                lines.append(re.sub(r"[^\r\n]", " ", line))
            else:
                lines.append(line)
        body = "".join(lines)
        body = re.sub(r"(`+)(?!`)([\s\S]*?)(?<!`)\1(?!`)", lambda m: "x" + re.sub(r"[^\r\n]", " ", m.group())[1:], body)
    parser = ReadabilityParser()
    parser.feed(body)
    parser.close()
    return parser.warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="教育記事UIの静的監査")
    parser.add_argument("--target", choices=("standalone-html", "astro-markdown"), required=True)
    parser.add_argument("--input", type=Path, help="監査対象。省略時は標準入力")
    parser.add_argument("--readability-warnings", action="store_true", help="空段落・連続改行の補助警告を追加。passedと終了コードには影響しない")
    parser.add_argument(
        "--allowed-class",
        action="append",
        default=[],
        help="Astroで実装確認済みのclass接頭辞。複数指定可",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.input:
            text = args.input.read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        if not text.strip():
            raise ValueError("入力が空です。")
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"target": args.target, "passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    issues = audit_document(text, args.target, args.allowed_class)
    result = {
        "target": args.target,
        "passed": not issues,
        "issue_count": len(issues),
        "issues": [issue.as_dict() for issue in issues],
    }
    if args.readability_warnings:
        warnings = readability_warnings(text, args.target)
        result["warning_count"] = len(warnings)
        result["warnings"] = [warning.as_dict() for warning in warnings]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
