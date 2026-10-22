import json
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILLS = Path(__file__).resolve().parents[2]
SITE_BLOG = Path(r"/Users/yudaikato/Documents/AIフォルダ/ブログ/公開サイト・教材/勉強ブログ/src/content/blog")


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
                self.assertIn(r"/Users/yudaikato/Documents/AIフォルダ/ブログ/公開サイト・教材/勉強ブログ", text)
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


    def parent_fixture(self, **kwargs):
        test_path=SKILLS/"cloudflare-seo-article-creator/scripts/test_validate_cloudflare_article.py"
        spec=importlib.util.spec_from_file_location("parent_cta_fixture",test_path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        os.environ.setdefault("ARTICLE_TEST_PROJECT_ROOT",str(SITE_BLOG.parents[2]))
        os.environ.setdefault("ARTICLE_TEST_WORK_ROOT",str(Path(__file__).resolve().parents[3]))
        return module.ParentValidation().run_fixture(**kwargs)

    def test_parent_traffic_validation_requires_two_placements_and_primary_card(self):
        report,code=self.parent_fixture(traffic=True,new_design=True)
        self.assertEqual((code,report["status"],report["parent_contract_pass"]),(0,"PASS",True),report)
        self.assertEqual(report["affiliate_markup_count"],2,report)
        self.assertEqual(report["internal_link_card_count"],1,report)

    def test_parent_completion_rejects_one_cta_and_rendered_loss(self):
        for mutation in ("one_cta","rendered_missing_cta","rendered_duplicate_id","context_mismatch"):
            with self.subTest(mutation=mutation):
                report,code=self.parent_fixture(traffic=True,mutation=mutation)
                self.assertNotEqual(code,0,report)
                self.assertFalse(report["parent_contract_pass"],report)


if __name__ == "__main__":
    unittest.main()
