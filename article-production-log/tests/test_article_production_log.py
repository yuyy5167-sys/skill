from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "article_production_log.py"
PROJECT = r"C:\AIフォルダ\ブログ\site"


class ArticleProductionLogCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "quality-log"
        self.article = self.base / "article.md"
        self.article.write_text("before\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, stdin: dict | None = None, expected: int = 0) -> dict:
        command = [sys.executable, "-X", "utf8", str(SCRIPT), *args]
        process = subprocess.run(
            command,
            input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, expected, process.stderr + process.stdout)
        return json.loads(process.stdout)

    def start(self, *extra: str) -> dict:
        return self.run_cli(
            "start-log",
            "--root",
            str(self.root),
            "--project-root",
            PROJECT,
            "--article-id",
            "sample-記事",
            "--article-path",
            str(self.article),
            "--request-type",
            "correction",
            "--request-text",
            "導入文を短くしてください。\nただし結論は残してください。",
            "--source-ref",
            "test:turn-1",
            "--entry-skill",
            "cloudflare-seo-article-creator",
            "--target-skill",
            "readable-article-style",
            "--stage",
            "writing",
            "--run-id",
            "run-1",
            "--quality-dimension",
            "readability",
            "--explicit-requirement",
            "導入文を短くする",
            "--exclusion",
            "結論を削除しない",
            *extra,
        )

    def test_init_creates_canonical_structure(self) -> None:
        result = self.run_cli("init", "--root", str(self.root))
        self.assertTrue(result["ok"])
        self.assertTrue((self.root / "meta.json").is_file())
        self.assertTrue((self.root / "events.jsonl").is_file())
        for name in ("品質傾向.md", "再発問題.md", "スキル別問題.md", "継続ルール候補.md"):
            self.assertTrue((self.root / "reports" / name).is_file())

    def test_start_preserves_verbatim_and_renders_sections(self) -> None:
        result = self.start()
        record = json.loads(Path(result["record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["request"]["verbatim"], "導入文を短くしてください。\nただし結論は残してください。")
        markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("## ユーザー原文", markdown)
        self.assertIn("## 変更前", markdown)
        self.assertIn("## 継続ルール候補", markdown)
        self.assertIn("結論を削除しない", markdown)

    def test_business_purpose_requires_user_confirmation_and_renders_funnel_alignment(self) -> None:
        rejected = self.run_cli(
            "start-log", "--root", str(self.root), "--project-root", PROJECT,
            "--article-id", "new-article", "--request-type", "initial_request",
            "--request-text", "成約用の記事を作って", "--source-ref", "test:purpose",
            "--entry-skill", "cloudflare-seo-article-creator", "--target-skill", "cloudflare-seo-article-creator",
            "--stage", "orchestration", "--run-id", "purpose-run",
            "--article-business-purpose", "conversion", expected=2,
        )
        self.assertIn("confirmed_by_user", rejected["error"])

        started = self.run_cli(
            "start-log", "--root", str(self.root), "--project-root", PROJECT,
            "--article-id", "new-article", "--request-type", "initial_request",
            "--request-text", "成約用の記事を作って", "--source-ref", "test:purpose",
            "--entry-skill", "cloudflare-seo-article-creator", "--target-skill", "cloudflare-seo-article-creator",
            "--stage", "orchestration", "--run-id", "purpose-run",
            "--article-business-purpose", "conversion",
            "--business-purpose-confirmation-text", "成約用の記事を作って",
            "--business-purpose-confirmation-source-ref", "test:purpose",
            "--business-purpose-confirmed-by-user",
        )
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        purpose = record["target"]["article_business_purpose"]
        self.assertEqual(purpose["type"], "conversion")
        self.assertEqual(purpose["primary_action"], "affiliate_conversion")

        finished = self.run_cli(
            "finish-log", "--root", str(self.root), "--log-id", started["log_id"],
            "--status", "implemented", "--result-text", "CTAを配置した",
            "--classification", "one_off", "--improvement-decision", "not_needed",
            "--improvement-reason", "目的別契約どおり",
            "--funnel-alignment", "pass", "--funnel-alignment-reason", "承認済みCTAを監査した",
        )
        markdown = Path(finished["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("## 記事の事業目的", markdown)
        self.assertIn("## 目的別導線の整合", markdown)
        self.assertIn("affiliate_conversion", markdown)

    def test_snapshot_hash_and_verify(self) -> None:
        result = self.start("--snapshot-before")
        record = json.loads(Path(result["record_path"]).read_text(encoding="utf-8"))
        item = record["evidence"]["before"][0]
        self.assertEqual(item["sha256"], hashlib.sha256(self.article.read_bytes()).hexdigest())
        self.assertTrue(Path(item["stored_path"]).is_file())
        verified = self.run_cli("verify-store", "--root", str(self.root))
        self.assertTrue(verified["ok"])

    def test_finish_adds_result_issue_candidate_and_reports(self) -> None:
        started = self.start("--snapshot-before")
        self.article.write_text("after\n", encoding="utf-8")
        issue = {
            "problem": "導入が長い",
            "cause": "結論の重複",
            "dimension": "readability",
            "stage": "writing",
            "priority": "high",
            "certainty": "observed",
            "status": "resolved",
        }
        finished = self.run_cli(
            "finish-log",
            "--root",
            str(self.root),
            "--log-id",
            started["log_id"],
            "--status",
            "verified",
            "--result-text",
            "導入を短縮した",
            "--observed-after",
            "結論を保ったまま短縮された",
            "--verification",
            "Markdown差分を確認",
            "--classification",
            "skill_gap",
            "--issue-json",
            json.dumps(issue, ensure_ascii=False),
            "--changed-file",
            str(self.article),
            "--unchanged-scope",
            "結論",
            "--candidate-key",
            "writing:lead-repetition",
            "--rule-candidate-text",
            "導入で結論を重複しない",
            "--rule-scope",
            "readable-article-style/writing",
            "--acceptance-criterion",
            "導入と結論の重複がない",
            "--snapshot-after",
        )
        self.assertEqual(finished["status"], "verified")
        markdown = Path(finished["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("導入が長い", markdown)
        self.assertIn("SHA-256", markdown)
        self.assertIn("候補は未承認", markdown)
        candidates = (self.root / "reports" / "継続ルール候補.md").read_text(encoding="utf-8")
        self.assertIn("導入で結論を重複しない", candidates)
        recurrence = (self.root / "reports" / "再発問題.md").read_text(encoding="utf-8")
        self.assertIn("writing:lead-repetition", recurrence)

    def test_article_history_contains_detail_link(self) -> None:
        started = self.start()
        history = self.root / "articles" / "sample-記事" / "制作履歴.md"
        self.assertTrue(history.is_file())
        history_text = history.read_text(encoding="utf-8")
        self.assertIn("[詳細]", history_text)
        self.assertIn(Path(started["markdown_path"]).name, history_text)

    def test_record_decision_keeps_exact_text(self) -> None:
        started = self.start()
        self.run_cli(
            "record-decision",
            "--root",
            str(self.root),
            "--log-id",
            started["log_id"],
            "--decision",
            "approve",
            "--decision-text",
            "このルールを今後も使ってください。",
            "--source-ref",
            "test:turn-2",
            "--approval-target",
            "F-999@1",
        )
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["user_decision"]["decision_text"], "このルールを今後も使ってください。")
        self.assertEqual(record["learning"]["rule_candidate"]["status"], "none")

    def test_rejects_noncanonical_project(self) -> None:
        result = self.run_cli(
            "start-log",
            "--root",
            str(self.root),
            "--project-root",
            str(self.base),
            "--article-id",
            "x",
            "--request-type",
            "review",
            "--request-text",
            "x",
            "--source-ref",
            "x",
            "--entry-skill",
            "x",
            "--target-skill",
            "x",
            "--stage",
            "x",
            "--run-id",
            "x",
            expected=2,
        )
        self.assertFalse(result["ok"])
        self.assertIn("対象外", result["error"])

    def test_rejects_unknown_quality_dimension(self) -> None:
        result = self.run_cli(
            "start-log",
            "--root",
            str(self.root),
            "--project-root",
            PROJECT,
            "--article-id",
            "x",
            "--request-type",
            "review",
            "--request-text",
            "x",
            "--source-ref",
            "x",
            "--entry-skill",
            "x",
            "--target-skill",
            "x",
            "--stage",
            "x",
            "--run-id",
            "x",
            "--quality-dimension",
            "video_camera",
            expected=2,
        )
        self.assertFalse(result["ok"])

    def test_hook_captures_prompt_and_is_idempotent(self) -> None:
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": PROJECT,
            "prompt": "原文です",
        }
        first = self.run_cli("hook-event", "--root", str(self.root), stdin=payload)
        second = self.run_cli("hook-event", "--root", str(self.root), stdin=payload)
        first_id = first["hookSpecificOutput"]["additionalContext"].split("source_hook_event_id=")[1].split()[0]
        second_id = second["hookSpecificOutput"]["additionalContext"].split("source_hook_event_id=")[1].split()[0]
        self.assertEqual(first_id, second_id)
        raw_files = list((self.root / "raw" / "hooks" / "session-1").glob("*.json"))
        self.assertEqual(len(raw_files), 1)
        self.assertEqual(json.loads(raw_files[0].read_text(encoding="utf-8"))["user_prompt"], "原文です")

    def test_start_event_key_is_idempotent(self) -> None:
        first = self.start("--event-key", "run-1:sample:turn-1")
        second = self.start("--event-key", "run-1:sample:turn-1")
        self.assertEqual(first["log_id"], second["log_id"])
        self.assertTrue(second["idempotent"])
        records = list((self.root / "records").glob("*.json"))
        self.assertEqual(len(records), 1)

    def test_stop_hook_returns_json_and_captures_assistant(self) -> None:
        output = self.run_cli(
            "hook-event",
            "--root",
            str(self.root),
            stdin={
                "hook_event_name": "Stop",
                "session_id": "session-2",
                "turn_id": "turn-2",
                "cwd": PROJECT,
                "last_assistant_message": "最終応答です",
                "stop_hook_active": False,
            },
        )
        self.assertEqual(output, {})
        raw_files = list((self.root / "raw" / "hooks" / "session-2").glob("*.json"))
        self.assertEqual(len(raw_files), 1)
        raw = json.loads(raw_files[0].read_text(encoding="utf-8"))
        self.assertEqual(raw["last_assistant_message"], "最終応答です")

    def test_verify_detects_tampered_markdown(self) -> None:
        started = self.start()
        Path(started["markdown_path"]).write_text("tampered", encoding="utf-8")
        result = self.run_cli("verify-store", "--root", str(self.root), expected=1)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Markdownが構造化正本と一致しません" in value for value in result["errors"]))

    def test_hook_verified_requires_exact_user_wording(self) -> None:
        original = "導入文を短くしてください。\nただし結論は残してください。"
        hook = self.run_cli("hook-event", "--root", str(self.root), stdin={"hook_event_name": "UserPromptSubmit", "session_id": "original-source", "prompt": original})
        hook_id = hook["hookSpecificOutput"]["additionalContext"].split("source_hook_event_id=")[1].split()[0]
        started = self.start("--source-hook-event-id", hook_id, "--source-provenance", "hook_verified", "--uttered-at", "2026-09-14T10:00:00Z")
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["source"]["provenance"], "hook_verified")
        self.assertTrue(self.run_cli("verify-store", "--root", str(self.root))["ok"])
        mismatch = self.run_cli("start-log", "--root", str(self.root), "--project-root", PROJECT, "--article-id", "other", "--request-type", "correction", "--request-text", "要約に置換", "--source-ref", "test:other", "--entry-skill", "cloudflare-seo-article-creator", "--target-skill", "readable-article-style", "--stage", "writing", "--run-id", "run-2", "--source-hook-event-id", hook_id, "--source-provenance", "hook_verified", expected=2)
        self.assertIn("一致しません", mismatch["error"])

    def test_audit_detects_missing_and_unassessed_requests(self) -> None:
        started = self.start()
        first = self.run_cli("audit-requests", "--root", str(self.root), "--article-id", "sample-記事", "--run-id", "run-1", "--expected-source-ref", "test:turn-1", "--expected-source-ref", "test:turn-2", expected=1)
        self.assertEqual(first["missing_source_refs"], ["test:turn-2"])
        self.assertEqual(first["unassessed_correction_log_ids"], [started["log_id"]])
        self.run_cli("finish-log", "--root", str(self.root), "--log-id", started["log_id"], "--status", "implemented", "--result-text", "導入を短くした", "--classification", "skill_gap", "--improvement-decision", "candidate", "--improvement-reason", "別記事での再発を確認する")
        final = self.run_cli("audit-requests", "--root", str(self.root), "--article-id", "sample-記事", "--run-id", "run-1", "--expected-source-ref", "test:turn-1")
        self.assertTrue(final["ok"])
        self.assertEqual(final["unfinished_log_ids"], [])
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["learning"]["improvement_decision"], "candidate")

    def test_legacy_audit_reports_gaps_without_rewriting_record(self) -> None:
        started = self.start()
        original = Path(started["record_path"]).read_bytes()
        audit = self.run_cli("audit-legacy", "--root", str(self.root), "--article-id", "sample-記事")
        self.assertEqual(audit["record_count"], 1)
        self.assertEqual(Path(started["record_path"]).read_bytes(), original)
        self.assertTrue(any("未判定" in flag for flag in audit["needs_review"][0]["確認事項"]))
        self.assertIn("旧記事ログの確認", audit["日本語一覧"])

    def test_legacy_amendment_keeps_saved_verbatim_and_is_idempotent(self) -> None:
        started = self.start()
        options = (
            "amend-legacy", "--root", str(self.root), "--log-id", started["log_id"],
            "--original-excerpt", "結論は残してください。",
            "--corrected-excerpt", "結論は必ず残してください。",
            "--source-ref", "visible:test:turn-1", "--source-provenance", "visible_user_message",
            "--reason", "保存済み抜粋と表示された発言の差異を記録", "--event-key", "test:legacy-amendment",
        )
        first = self.run_cli(*options)
        second = self.run_cli(*options)
        self.assertEqual(first["event_id"], second["event_id"])
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["request"]["verbatim"], "導入文を短くしてください。\nただし結論は残してください。")
        self.assertEqual(len(record["amendments"]), 1)
        markdown = Path(started["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("## 過去ログの訂正", markdown)
        self.assertIn("結論は必ず残してください。", markdown)
        self.assertTrue(self.run_cli("verify-store", "--root", str(self.root))["ok"])

    def test_legacy_amendment_rejects_missing_saved_excerpt(self) -> None:
        started = self.start()
        failure = self.run_cli(
            "amend-legacy", "--root", str(self.root), "--log-id", started["log_id"],
            "--original-excerpt", "保存されていない文", "--corrected-excerpt", "実際の文",
            "--source-ref", "test:turn-1", "--source-provenance", "visible_user_message",
            "--reason", "差異", "--event-key", "test:invalid-amendment", expected=2,
        )
        self.assertIn("保存済み原文", failure["error"])

    def test_raw_hook_amendment_requires_matching_hook_excerpt(self) -> None:
        started = self.start()
        hook = self.run_cli("hook-event", "--root", str(self.root), stdin={"hook_event_name": "UserPromptSubmit", "session_id": "legacy-source", "prompt": "結論は必ず残してください。"})
        hook_id = hook["hookSpecificOutput"]["additionalContext"].split("source_hook_event_id=")[1].split()[0]
        base = (
            "amend-legacy", "--root", str(self.root), "--log-id", started["log_id"],
            "--original-excerpt", "結論は残してください。", "--source-ref", hook_id,
            "--source-provenance", "raw_hook_verified", "--reason", "raw原文との差異",
            "--event-key", "test:raw-amendment",
        )
        rejected = self.run_cli(*base, "--corrected-excerpt", "根拠のない訂正文", expected=2)
        self.assertIn("rawフック原文", rejected["error"])
        self.assertTrue(self.run_cli(*base, "--corrected-excerpt", "結論は必ず残してください。")["ok"])

    def test_verify_detects_tampered_artifact(self) -> None:
        started = self.start("--snapshot-before")
        record = json.loads(Path(started["record_path"]).read_text(encoding="utf-8"))
        Path(record["evidence"]["before"][0]["stored_path"]).write_text("tampered", encoding="utf-8")
        result = self.run_cli("verify-store", "--root", str(self.root), expected=1)
        self.assertFalse(result["ok"])
        self.assertTrue(any("ハッシュ不一致" in value for value in result["errors"]))


if __name__ == "__main__":
    unittest.main()
