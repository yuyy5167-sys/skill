from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILLS = Path(r"C:\Users\yuyy2\.codex\skills")
PROJECT_HOOKS = Path(r"C:\AIフォルダ\.codex\hooks.json")
SCRIPT = SKILLS / "article-production-log" / "scripts" / "article_production_log.py"


class ArticleProductionLogIntegrationTests(unittest.TestCase):
    def test_parent_contract_workflow_and_gate_are_connected(self) -> None:
        parent = SKILLS / "cloudflare-seo-article-creator"
        skill = (parent / "SKILL.md").read_text(encoding="utf-8")
        workflow = (parent / "references" / "workflow.md").read_text(encoding="utf-8")
        contract = (parent / "references" / "input-output-contract.md").read_text(encoding="utf-8")
        gate = (parent / "references" / "quality-gate.md").read_text(encoding="utf-8")
        for text in (skill, workflow, contract, gate):
            self.assertIn("article-production-log", text)
        self.assertIn("start-log", skill)
        self.assertIn("finish-log", skill)
        self.assertIn("funnel_alignment", skill)
        self.assertIn("article_log_context", contract)
        self.assertIn("article_business_purpose", contract)
        self.assertIn("verify-store", gate)

    def test_all_seven_children_reuse_one_log_id(self) -> None:
        entries = {
            "seo-keyword-competitor-research": SKILLS / "seo-keyword-competitor-research" / "SKILL.md",
            "seo-heading-outline-creator": SKILLS / "seo-heading-outline-creator" / "SKILL.md",
            "readable-article-style": SKILLS / "readable-article-style-20260822T011609Z-1-001" / "readable-article-style" / "SKILL.md",
            "article-internal-linker": SKILLS / "article-internal-linker" / "SKILL.md",
            "official-site-evidence-capture": SKILLS / "official-site-evidence-capture" / "SKILL.md",
            "study-article-ui-coder": SKILLS / "study-article-ui-coder" / "SKILL.md",
            "education-blog-thumbnail-creator": SKILLS / "education-blog-thumbnail-creator" / "SKILL.md",
        }
        for name, path in entries.items():
            with self.subTest(skill=name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("$article-production-log", text)
                self.assertIn("article_log_context.log_id", text)
                self.assertIn("子で新規ログを作らない", text)
                self.assertIn("start-log", text)
                self.assertIn("finish-log", text)

    def test_feedback_ledger_remains_authoritative_for_rule_state(self) -> None:
        feedback = SKILLS / "article-skill-feedback"
        skill = (feedback / "SKILL.md").read_text(encoding="utf-8")
        contract = (feedback / "references" / "integration-contract.md").read_text(encoding="utf-8")
        self.assertIn("継続ルールの状態遷移の正本", skill)
        self.assertIn("相互参照", skill)
        self.assertIn("品質ログの`log_id`", contract)
        self.assertIn("自動生成しない", contract)

    def test_project_hook_shape_and_windows_commands(self) -> None:
        config = json.loads(PROJECT_HOOKS.read_text(encoding="utf-8"))
        self.assertEqual(set(config["hooks"]), {"UserPromptSubmit", "Stop", "Interrupt", "SessionEnd"})
        for event_name, groups in config["hooks"].items():
            handler = groups[0]["hooks"][0]
            self.assertEqual(handler["type"], "command")
            self.assertIn(str(SCRIPT), handler["commandWindows"])
            self.assertTrue(SCRIPT.is_file())
            if event_name in {"Interrupt", "SessionEnd"}:
                self.assertLessEqual(handler["timeout"], 3)


if __name__ == "__main__":
    unittest.main()
