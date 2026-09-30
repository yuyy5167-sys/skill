import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILLS = Path(r"C:\Users\yuyy2\.codex\skills")
SITE_BLOG = Path(r"C:\AIフォルダ\ブログ\site\src\content\blog")


class SkillIntegrationTests(unittest.TestCase):
    def read(self, relative):
        return (SKILLS / relative).read_text(encoding="utf-8")

    def test_parent_entry_workflow_contract_and_gate_are_connected(self):
        parent = self.read("cloudflare-seo-article-creator/SKILL.md")
        workflow = self.read("cloudflare-seo-article-creator/references/workflow.md")
        contract = self.read("cloudflare-seo-article-creator/references/input-output-contract.md")
        gate = self.read("cloudflare-seo-article-creator/references/quality-gate.md")
        self.assertIn("$article-skill-feedback", parent)
        self.assertIn("article_business_purpose", parent)
        self.assertIn("依頼文に記事目的が明記されていれば、その原文を確認回答として扱い再質問しない", parent)
        self.assertIn("調査、タイトル案、見出し、本文、リンク計画、画像、記事ファイル、プレビュー", parent)
        self.assertIn("## 0.5 修正履歴と有効ルールの接続", workflow)
        self.assertIn("## G0 事業目的の確認", gate)
        self.assertIn("article_feedback_context:", contract)
        self.assertIn("article_business_purpose:", contract)
        self.assertIn("rule_applications:", contract)
        self.assertIn("## G0.5 修正履歴と承認済みルール", gate)

    def test_all_seven_child_entry_points_have_exact_stage_mapping(self):
        expected = {
            "seo-keyword-competitor-research/SKILL.md": ("seo-keyword-competitor-research", "research"),
            "seo-heading-outline-creator/SKILL.md": ("seo-heading-outline-creator", "outline"),
            "readable-article-style-20260822T011609Z-1-001/readable-article-style/SKILL.md": ("readable-article-style", "writing"),
            "article-internal-linker/SKILL.md": ("article-internal-linker", "links"),
            "official-site-evidence-capture/SKILL.md": ("official-site-evidence-capture", "evidence"),
            "study-article-ui-coder/SKILL.md": ("study-article-ui-coder", "ui"),
            "education-blog-thumbnail-creator/SKILL.md": ("education-blog-thumbnail-creator", "images"),
        }
        for relative, (skill, stage) in expected.items():
            with self.subTest(skill=skill):
                text = self.read(relative)
                self.assertIn("$article-skill-feedback", text)
                self.assertIn(r"C:\AIフォルダ\ブログ\site", text)
                self.assertIn(f"target_skill: {skill}", text)
                self.assertIn(f"stage: {stage}", text)
                self.assertIn("別プロジェクトには適用しない", text)

    def test_child_permissions_limit_standing_approval_to_ledger(self):
        paths = [
            "seo-keyword-competitor-research/SKILL.md",
            "seo-heading-outline-creator/SKILL.md",
            "readable-article-style-20260822T011609Z-1-001/readable-article-style/SKILL.md",
            "article-internal-linker/SKILL.md",
            "official-site-evidence-capture/SKILL.md",
            "study-article-ui-coder/SKILL.md",
            "education-blog-thumbnail-creator/SKILL.md",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                text = self.read(relative)
                self.assertIn("記事フィードバック台帳への定型追記", text)
                self.assertIn("この許可を", text)
                self.assertIn("広げない", text)

    def test_parent_affiliate_validation_uses_explicit_six_placement_manifest(self):
        validator = SKILLS / "cloudflare-seo-article-creator/scripts/validate-cloudflare-article.ps1"
        placements = [
            ("チャレンジタッチに合う子", "touch-fit", "shinken_zemi"),
            ("チャレンジタッチに合う子", "touch-compare", "shinken_zemi"),
            ("チャレンジタッチに合う子", "touch-final", "shinken_zemi"),
            ("スマイルゼミに合う子", "smile-fit", "smile_zemi"),
            ("スマイルゼミに合う子", "smile-compare", "smile_zemi"),
            ("スマイルゼミに合う子", "smile-final", "smile_zemi"),
        ]
        manifest = []
        sections = {}
        for heading, placement_id, provider in placements:
            root_class = "smile-zemi-cta" if provider == "smile_zemi" else "shinken-zemi-cta"
            component = "smile_zemi_cta_v1" if provider == "smile_zemi" else "shinken_zemi_cta_v1"
            href = f"https://testing.invalid/{provider}/elementary"
            pixel = f"https://testing.invalid/{provider}/pixel"
            block = f'<div class="{root_class}" data-course="elementary" data-placement-id="{placement_id}"><a class="{root_class}__button" href="{href}" rel="nofollow"><img src="{pixel}" height="1" width="1" border="0" alt="">資料を見る</a></div>'
            sections.setdefault(heading, []).append(block)
            manifest.append({"provider": provider, "placement_id": placement_id, "section_heading": heading, "section_id": "h2-1", "target_course": "elementary", "presentation": "cta_button", "component_id": component, "href": href, "tracking_image_src": pixel, "rel": "nofollow"})
        body = "\n".join(f"## {heading}\n説明文\n" + "\n".join(blocks) for heading, blocks in sections.items())
        with tempfile.TemporaryDirectory(prefix="codex-cta-validator-", dir=SITE_BLOG) as tmp:
            article = Path(tmp) / "index.md"
            images = Path(tmp) / "images"
            images.mkdir()
            (images / "cover.webp").write_bytes(b"test")
            frontmatter = '---\ntitle: "CTA配置の検証"\ndate: 2026-09-16\ncategories: [education]\ncoverImage: "images/cover.webp"\ndraft: true\n---\n'
            article.write_text(frontmatter + body, encoding="utf-8")
            args = ["pwsh", "-NoProfile", "-File", str(validator), "-ArticlePath", str(article), "-ValidationMode", "parent", "-ExpectedArticleBusinessPurpose", "conversion", "-ExpectedTitle", "CTA配置の検証", "-ExpectedAffiliateDisposition", "eligible", "-ExternalLinkPolicy", "allow_task_required_only", "-ExpectedEmphasisPlanJson", json.dumps([{"section_id": "H2-01", "exact_text": "説明文", "role": "conclusion"}], ensure_ascii=False), "-ExpectedInternalLinkManifestJson", '{"new_links":[]}', "-ExpectedAffiliateLinkManifestJson", json.dumps({"links": manifest}, ensure_ascii=False)]
            complete = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False)
            result = json.loads(complete.stdout)
            self.assertEqual(result["affiliate_manifest_link_count"], 6)
            self.assertEqual(result["affiliate_markup_count"], 6, result["errors"])
            self.assertEqual(result["checks"]["affiliate"], "pass", result["errors"])
            single_body = f"## {placements[0][0]}\n説明文\n{sections[placements[0][0]][0]}"
            article.write_text(frontmatter + single_body, encoding="utf-8")
            single_args = args[:-2] + ["-ExpectedAffiliateLinkManifestJson", json.dumps({"links": manifest[:1]}, ensure_ascii=False), "-ExpectedAffiliateProvider", "shinken_zemi", "-ExpectedAffiliateCourse", "elementary"]
            single = json.loads(subprocess.run(single_args, capture_output=True, text=True, encoding="utf-8", check=False).stdout)
            self.assertEqual(single["affiliate_markup_count"], 1)
            self.assertEqual(single["checks"]["affiliate"], "pass", single["errors"])
            article.write_text(frontmatter + body.replace('data-placement-id="smile-final"', 'data-placement-id="wrong-final"'), encoding="utf-8")
            mismatch = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False)
            invalid = json.loads(mismatch.stdout)
            self.assertEqual(invalid["checks"]["affiliate"], "fail")
            self.assertTrue(any("smile-final" in message for message in invalid["errors"]))

    def test_parent_traffic_validation_requires_primary_conversion_card_and_zero_affiliate(self):
        validator = SKILLS / "cloudflare-seo-article-creator/scripts/validate-cloudflare-article.ps1"
        with tempfile.TemporaryDirectory(prefix="codex-traffic-validator-", dir=SITE_BLOG) as tmp:
            article = Path(tmp) / "index.md"
            images = Path(tmp) / "images"
            images.mkdir()
            (images / "cover.webp").write_bytes(b"test")
            frontmatter = '---\ntitle: "集客記事の検証"\ndate: 2026-09-17\ncategories: [education]\ncoverImage: "images/cover.webp"\ndraft: true\n---\n'
            body = "## 選び方\n**判断基準**を説明します。\n\n【内部リンクカード】\nURL: /conversion-article/\n紹介文: 成約用記事で料金と申込み条件を確認できます。\n"
            article.write_text(frontmatter + body, encoding="utf-8")
            internal = {"new_links": [{"href": "/conversion-article/", "destination_role": "conversion_direct", "presentation": "image_card", "card_description": "成約用記事で料金と申込み条件を確認できます。", "required": True, "primary_destination": True}]}
            args = ["pwsh", "-NoProfile", "-File", str(validator), "-ArticlePath", str(article), "-ValidationMode", "parent", "-ExpectedArticleBusinessPurpose", "traffic", "-ExpectedTitle", "集客記事の検証", "-ExpectedAffiliateDisposition", "not_applicable", "-ExternalLinkPolicy", "allow_task_required_only", "-ExpectedEmphasisPlanJson", json.dumps([{"section_id": "H2-01", "exact_text": "判断基準", "role": "conclusion"}], ensure_ascii=False), "-ExpectedInternalLinkManifestJson", json.dumps(internal, ensure_ascii=False), "-ExpectedAffiliateLinkManifestJson", '{"links":[]}']
            passed = json.loads(subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False).stdout)
            self.assertEqual(passed["article_business_purpose"], "traffic")
            self.assertEqual(passed["checks"]["affiliate"], "pass", passed["errors"])
            self.assertEqual(passed["checks"]["internal_links"], "pass", passed["errors"])

            contaminated = body + '\n<div class="smile-zemi-cta"><a href="https://px.a8.net/svt/ejp?x=1">資料請求</a></div>\n'
            article.write_text(frontmatter + contaminated, encoding="utf-8")
            failed = json.loads(subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False).stdout)
            self.assertEqual(failed["checks"]["affiliate"], "fail")
            self.assertTrue(any("集客用記事" in message or "not_applicable" in message for message in failed["errors"]))

            missing_primary_args = args.copy()
            manifest_index = missing_primary_args.index("-ExpectedInternalLinkManifestJson") + 1
            missing_primary_args[manifest_index] = '{"new_links":[]}'
            article.write_text(frontmatter + "## 選び方\n**判断基準**を説明します。\n", encoding="utf-8")
            missing = json.loads(subprocess.run(missing_primary_args, capture_output=True, text=True, encoding="utf-8", check=False).stdout)
            self.assertTrue(any("主成約記事画像カード" in message for message in missing["errors"]))


if __name__ == "__main__":
    unittest.main()
