import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from article_feedback import FeedbackStore, LedgerError, sha256_file  # noqa: E402


BLOG_ROOT = r"C:\AIフォルダ\ブログ\site"


class FeedbackAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "ledger"
        self.store = FeedbackStore(self.root)
        self.store.init()

    def tearDown(self):
        self.temp.cleanup()

    def request(self, key="req-1", candidate_key="candidate-a", article_id="article-1", intent_scope="unclear"):
        return self.store.record_request(
            project_root=BLOG_ROOT,
            article_id=article_id,
            article_path="src/content/blog/article-1/index.md",
            entry_skill="cloudflare-seo-article-creator",
            target_skill="study-article-ui-coder",
            stage="ui",
            run_id="run-1",
            parent_run_id="run-1",
            request_text="冒頭の同じ画像を1枚にしてください",
            source_ref="thread:test#message-1",
            observed_before="同じ画像が2件",
            interpretation="重複表示の可能性",
            candidate_key=candidate_key,
            intent_scope=intent_scope,
            event_key=key,
        )

    def revised_rule(self, request_event_id, article_types=None):
        return self.store.propose_rule(
            rule_id="F-001", revision="2", rule_text="新しい明確な希望を反映する。",
            scope={"project_roots": [BLOG_ROOT], "entry_skills": ["cloudflare-seo-article-creator", "study-article-ui-coder"], "target_skills": ["study-article-ui-coder"], "stages": ["ui"], "business_purposes": ["*"], "article_types": article_types or ["*"], "grades": ["*"]},
            source_event_ids=[request_event_id], not_applicable_to=[], acceptance_criteria=["最新版だけを使う"],
            supersedes=["F-001@1"], event_key="proposal-F-001-2",
        )["proposal"]

    def proposal(self, request_event_id, rule_id="F-001", revision="1", project=BLOG_ROOT, business_purposes=None):
        return self.store.propose_rule(
            rule_id=rule_id,
            revision=revision,
            rule_text="レイアウトがcoverImageを冒頭表示する場合、本文先頭へ同一画像を重ねない。",
            status="proposed",
            scope={
                "project_roots": [project],
                "entry_skills": ["cloudflare-seo-article-creator", "study-article-ui-coder"],
                "target_skills": ["study-article-ui-coder"],
                "stages": ["ui"],
                "business_purposes": business_purposes or ["*"],
                "article_types": ["*"],
                "grades": ["*"],
            },
            not_applicable_to=["H2画像", "内部リンクカード"],
            source_event_ids=[request_event_id],
            acceptance_criteria=["記事冒頭の同一画像が1件"],
            event_key=f"proposal-{rule_id}-{revision}",
        )["proposal"]

    def approve_release_activate(self, rule, target_files=None):
        self.store.decide_rule(
            rule_id=rule["rule_id"],
            revision=rule["revision"],
            proposal_sha256=rule["proposal_sha256"],
            decision="approve",
            approval_kind="persistent_rule",
            approval_target=f"{rule['rule_id']}@{rule['revision']}",
            approval_text=f"{rule['rule_id']}@{rule['revision']}を今後のルールとして採用します",
            approval_source="thread:test#approval-1",
            event_key=f"decision-{rule['rule_id']}-{rule['revision']}",
        )
        release = self.store.record_release(
            rule_id=rule["rule_id"],
            revision=rule["revision"],
            proposal_sha256=rule["proposal_sha256"],
            release_id=f"release-{rule['rule_id']}-{rule['revision']}",
            validation_report="形式、抽出、代表シナリオが合格",
            meaning_review_result="pass",
            meaning_review_note="原文の対象・否定・条件を保持",
            target_files=target_files or [],
            event_key=f"release-{rule['rule_id']}-{rule['revision']}",
        )["release"]
        self.store.activate_rule(
            rule_id=rule["rule_id"],
            revision=rule["revision"],
            proposal_sha256=rule["proposal_sha256"],
            release_id=release["release_id"],
            event_key=f"activation-{rule['rule_id']}-{rule['revision']}",
        )

    def resolve(self, project=BLOG_ROOT, entry="cloudflare-seo-article-creator"):
        return self.store.resolve(project_root=project, entry_skill=entry, target_skill="study-article-ui-coder", stage="ui", business_purpose="conversion", article_type="how_to", grade="elementary")

    def test_t01_correction_stays_narrow(self):
        request = self.request()
        self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="本文先頭の重複参照だけを削除", observed_after="冒頭画像は1件", verification="DOMで1件", changed_files=["article/index.md"], classification="skill_gap", event_key="result-1")
        result = [e for e in self.store.read_events() if e["event_type"] == "correction_result"][0]
        self.assertEqual(result["payload"]["changed_files"], ["article/index.md"])
        self.assertEqual(self.resolve()["rules"], [])

    def test_t02_article_fix_yes_is_not_rule_approval(self):
        request = self.request()
        self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="はい、と確認された記事修正", observed_after="fixed", verification="checked", changed_files=[], classification="preference_candidate", event_key="result-1")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t03_ambiguous_approval_is_rejected(self):
        rule = self.proposal(self.request()["event_id"])
        with self.assertRaises(LedgerError):
            self.store.decide_rule(rule_id=rule["rule_id"], revision=rule["revision"], proposal_sha256=rule["proposal_sha256"], decision="approve", approval_kind="article_fix", approval_target="article-1", approval_text="はい", approval_source="thread:test", event_key="bad-decision")

    def test_t04_repetition_only_changes_priority(self):
        for number in range(3):
            self.request(key=f"req-{number}")
        summary = self.store.candidate_summary()
        self.assertEqual(summary["candidates"][0]["occurrences"], 3)
        self.assertFalse(summary["candidates"][0]["auto_approved"])
        self.assertEqual(self.resolve()["rules"], [])

    def test_t05_existing_rule_gap_does_not_create_rule(self):
        request = self.request()
        self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="既存CTA工程の接続を修復", observed_after="CTA1件", verification="audit pass", changed_files=[], classification="existing_rule_execution_gap", event_key="result-cta")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t06_one_off_does_not_change_active_rules(self):
        request = self.request()
        self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="今回だけ変更", observed_after="fixed", verification="checked", changed_files=[], classification="one_off", event_key="result-once")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t07_changed_proposal_or_file_blocks_activation(self):
        rule = self.proposal(self.request()["event_id"])
        with self.assertRaises(LedgerError):
            self.store.decide_rule(rule_id=rule["rule_id"], revision=rule["revision"], proposal_sha256="0" * 64, decision="approve", approval_kind="persistent_rule", approval_target="F-001@1", approval_text="今後のルールとして採用", approval_source="thread:test", event_key="wrong-hash")
        target = Path(self.temp.name) / "target.txt"
        target.write_text("before", encoding="utf-8")
        expected = sha256_file(target)
        self.store.decide_rule(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], decision="approve", approval_kind="persistent_rule", approval_target="F-001@1", approval_text="F-001@1を今後のルールとして採用", approval_source="thread:test", event_key="good-decision")
        release = self.store.record_release(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], release_id="release-1", validation_report="pass", meaning_review_result="pass", meaning_review_note="meaning retained", target_files=[f"{target}={expected}"], event_key="release-1")["release"]
        target.write_text("after", encoding="utf-8")
        with self.assertRaises(LedgerError):
            self.store.activate_rule(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], release_id=release["release_id"], event_key="activation-1")

    def test_t08_unapproved_and_rejected_are_excluded(self):
        request = self.request()
        proposed = self.proposal(request["event_id"], "F-001")
        rejected = self.proposal(request["event_id"], "F-002")
        self.store.decide_rule(rule_id="F-002", revision="1", proposal_sha256=rejected["proposal_sha256"], decision="reject", approval_kind="persistent_rule", approval_target="F-002@1", approval_text="F-002は採用しない", approval_source="thread:test", event_key="reject-2")
        self.assertTrue(proposed)
        self.assertEqual(self.resolve()["rules"], [])

    def test_t09_child_standalone_same_blog_only(self):
        rule = self.proposal(self.request()["event_id"])
        self.approve_release_activate(rule)
        self.assertEqual(len(self.resolve(entry="study-article-ui-coder")["rules"]), 1)
        self.assertEqual(self.resolve(project=str(Path(self.temp.name) / "other"), entry="study-article-ui-coder")["rules"], [])

    def test_t10_duplicate_and_corruption_are_not_silent(self):
        first = self.request()
        second = self.request()
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertTrue(second["deduplicated"])
        with self.assertRaises(LedgerError):
            self.request(key="req-1", candidate_key="different")
        with self.store.events_path.open("a", encoding="utf-8") as handle:
            handle.write("{broken\n")
        with self.assertRaises(LedgerError):
            self.store.verify()

    def test_retried_proposal_is_idempotent(self):
        request = self.request()
        first = self.proposal(request["event_id"])
        second = self.proposal(request["event_id"])
        self.assertEqual(first, second)

    def test_t11_partial_multi_skill_release_does_not_activate(self):
        rule = self.proposal(self.request()["event_id"])
        self.store.decide_rule(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], decision="approve", approval_kind="persistent_rule", approval_target="F-001@1", approval_text="F-001@1を今後のルールとして採用", approval_source="thread:test", event_key="decision-1")
        with self.assertRaises(LedgerError):
            self.store.record_release(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], release_id="release-1", validation_report="partial", meaning_review_result="pass", meaning_review_note="retained", target_files=[str(Path(self.temp.name) / "missing.txt") + "=" + "0" * 64], event_key="release-1")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t12_saved_ids_work_in_new_store_instance(self):
        rule = self.proposal(self.request()["event_id"])
        self.approve_release_activate(rule)
        reopened = FeedbackStore(self.root)
        self.assertEqual(len(reopened.resolve(project_root=BLOG_ROOT, entry_skill="cloudflare-seo-article-creator", target_skill="study-article-ui-coder", stage="ui", business_purpose="conversion", article_type="how_to", grade="elementary")["rules"]), 1)

    def test_t13_factual_update_is_not_preference(self):
        request = self.request()
        self.store.record_result(request_event_id=request["event_id"], status="needs_source_refresh", result_text="料金を公式根拠へ戻す", observed_after="unconfirmed", verification="source required", changed_files=[], classification="factual_update", event_key="result-fact")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t14_log_content_cannot_become_approval_automatically(self):
        request = self.request()
        self.proposal(request["event_id"])
        self.assertFalse(any(e["event_type"] == "rule_decision" for e in self.store.read_events()))

    def test_t15_withdrawn_rule_disappears(self):
        rule = self.proposal(self.request()["event_id"])
        self.approve_release_activate(rule)
        self.assertEqual(len(self.resolve()["rules"]), 1)
        self.store.withdraw_rule(rule_id="F-001", revision="1", reason="ユーザーが継続ルールを取り消した", source_ref="thread:test#withdraw", event_key="withdraw-1")
        self.assertEqual(self.resolve()["rules"], [])

    def test_t16_meaning_review_is_required_beyond_hash(self):
        rule = self.proposal(self.request()["event_id"])
        self.store.decide_rule(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], decision="approve", approval_kind="persistent_rule", approval_target="F-001@1", approval_text="F-001@1を今後のルールとして採用", approval_source="thread:test", event_key="decision-1")
        with self.assertRaises(LedgerError):
            self.store.record_release(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], release_id="release-1", validation_report="hash pass", meaning_review_result="fail", meaning_review_note="否定条件の意味が変わった", target_files=[], event_key="release-1")

    def test_manual_active_index_injection_is_rejected(self):
        request = self.request()
        rule = self.proposal(request["event_id"])
        fake = json.loads(self.store.index_path.read_text(encoding="utf-8"))
        fake["rules"] = [{"rule_id": rule["rule_id"], "revision": rule["revision"]}]
        from article_feedback import sha256_value
        fake["active_rule_set_id"] = sha256_value(fake["rules"])
        self.store.index_path.write_text(json.dumps(fake), encoding="utf-8")
        with self.assertRaises(LedgerError):
            self.store.verify()

    def test_release_id_path_traversal_is_rejected(self):
        rule = self.proposal(self.request()["event_id"])
        self.store.decide_rule(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], decision="approve", approval_kind="persistent_rule", approval_target="F-001@1", approval_text="F-001@1を今後のルールとして採用", approval_source="thread:test", event_key="decision-1")
        with self.assertRaises(LedgerError):
            self.store.record_release(rule_id="F-001", revision="1", proposal_sha256=rule["proposal_sha256"], release_id="../outside", validation_report="pass", meaning_review_result="pass", meaning_review_note="retained", target_files=[], event_key="release-1")

    def test_same_article_revisions_do_not_count_as_cross_article_recurrence(self):
        for number in range(3):
            request = self.request(key=f"revision-{number}")
            self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="見出しを修正", classification="skill_gap", improvement_decision="candidate", improvement_reason="見出し設計を確認する", event_key=f"result-{number}")
        one_article = self.store.candidate_summary()["candidates"][0]
        self.assertEqual(one_article["occurrences"], 3)
        self.assertEqual(one_article["eligible_article_count"], 1)
        self.assertFalse(one_article["review_ready"])
        request = self.request(key="another-article", article_id="article-2")
        self.store.record_result(request_event_id=request["event_id"], status="fixed", result_text="別記事の見出しを修正", classification="skill_gap", improvement_decision="candidate", improvement_reason="同じ原因を確認", event_key="result-another")
        self.assertTrue(self.store.candidate_summary()["candidates"][0]["review_ready"])

    def test_explicit_standing_instruction_is_reviewable_but_not_auto_active(self):
        request = self.request(intent_scope="standing_explicit")
        item = self.store.candidate_summary()["candidates"][0]
        self.assertTrue(item["review_ready"])
        self.assertFalse(item["auto_approved"])
        self.assertEqual(self.resolve()["rules"], [])

    def test_new_confirmed_preference_suppresses_old_until_implementation(self):
        old = self.proposal(self.request()["event_id"])
        self.approve_release_activate(old)
        newer = self.revised_rule(self.request(key="new-request")["event_id"])
        self.store.decide_rule(rule_id="F-001", revision="2", proposal_sha256=newer["proposal_sha256"], decision="approve", approval_kind="persistent_rule", approval_target="F-001@2", approval_text="今後は新方針に変更します", approval_source="thread:test#newer", event_key="decision-newer")
        pending = self.resolve()
        self.assertEqual(pending["rules"], [])
        self.assertEqual([item["revision"] for item in pending["pending_wishes"]], ["2"])
        self.approve_release_activate(newer)
        active = self.resolve()
        self.assertEqual([item["revision"] for item in active["rules"]], ["2"])
        self.assertEqual(active["pending_wishes"], [])
        self.store.withdraw_rule(rule_id="F-001", revision="2", reason="実装の一時的な復旧", source_ref="thread:test#technical", withdrawal_kind="technical_rollback", event_key="technical-rollback")
        rolled_back = self.resolve()
        self.assertEqual(rolled_back["rules"], [])
        self.assertEqual([item["revision"] for item in rolled_back["pending_wishes"]], ["2"])

    def test_narrow_new_preference_keeps_old_outside_its_scope(self):
        old = self.proposal(self.request()["event_id"])
        self.approve_release_activate(old)
        new = self.revised_rule(self.request(key="narrow-request")["event_id"], ["comparison"])
        self.approve_release_activate(new)
        self.assertEqual([item["revision"] for item in self.resolve()["rules"]], ["1"])
        comparison = self.store.resolve(project_root=BLOG_ROOT, entry_skill="cloudflare-seo-article-creator", target_skill="study-article-ui-coder", stage="ui", business_purpose="conversion", article_type="comparison", grade="elementary")
        self.assertEqual([item["revision"] for item in comparison["rules"]], ["2"])

    def test_business_purpose_scopes_do_not_leak(self):
        rule = self.proposal(self.request()["event_id"], rule_id="F-PURPOSE", business_purposes=["traffic"])
        self.approve_release_activate(rule)
        traffic = self.store.resolve(project_root=BLOG_ROOT, entry_skill="cloudflare-seo-article-creator", target_skill="study-article-ui-coder", stage="ui", business_purpose="traffic", article_type="how_to", grade="elementary")
        conversion = self.store.resolve(project_root=BLOG_ROOT, entry_skill="cloudflare-seo-article-creator", target_skill="study-article-ui-coder", stage="ui", business_purpose="conversion", article_type="how_to", grade="elementary")
        self.assertEqual([item["rule_id"] for item in traffic["rules"]], ["F-PURPOSE"])
        self.assertEqual(conversion["rules"], [])

    def test_skill_change_and_next_article_result_remain_separate(self):
        target = Path(self.temp.name) / "skill.md"
        target.write_text("article-specific decisions", encoding="utf-8")
        change = self.store.record_skill_change(source_ref="thread:test#skill-request", request_text="スキルを直して", problem="同じ見出し修正が再発", cause="担当への条件が渡されない", change_summary="受け渡しを改善", decision_basis="explicit_skill_change_request", status="verified", validation_report="実行例で検証", changed_files=[str(target)], business_purposes=["conversion"], article_types=["comparison"], target_skills=["seo-heading-outline-creator"], event_key="skill-change-1")
        before = self.store.skill_change_summary()["skill_changes"][0]
        self.assertEqual(before["eligible_article_count"], 0)
        self.assertEqual(before["effect_status"], "not_observed_yet")
        self.store.record_impact(change_event_id=change["change_event_id"], article_id="comparison-next", business_purpose="conversion", article_type="comparison", first_draft="unreviewed", evidence_ref="preview:next", verification="読者評価は未実施", event_key="impact-unreviewed")
        unreviewed = self.store.skill_change_summary()["skill_changes"][0]
        self.assertEqual(unreviewed["first_draft_pass_count"], 0)
        self.assertEqual(unreviewed["unreviewed_count"], 1)
        with self.assertRaises(LedgerError):
            self.store.record_impact(change_event_id=change["change_event_id"], article_id="wrong-type", business_purpose="conversion", article_type="how_to", first_draft="pass", evidence_ref="preview:wrong", verification="checked", event_key="impact-wrong")
        with self.assertRaises(LedgerError):
            self.store.record_impact(change_event_id=change["change_event_id"], article_id="wrong-purpose", business_purpose="traffic", article_type="comparison", first_draft="pass", evidence_ref="preview:wrong-purpose", verification="checked", event_key="impact-wrong-purpose")
        with self.assertRaises(LedgerError):
            self.store.record_impact(change_event_id=change["change_event_id"], article_id="comparison-next", business_purpose="conversion", article_type="comparison", first_draft="pass", user_assessment="accepted", evidence_ref="preview:next", verification="checked", event_key="impact-no-user-source")
        self.store.record_impact(change_event_id=change["change_event_id"], article_id="comparison-next", business_purpose="conversion", article_type="comparison", first_draft="pass", user_assessment="accepted", user_assessment_source="thread:test#accepted", evidence_ref="preview:next", verification="初稿の見出しを確認", event_key="impact-accepted")
        result = self.store.skill_change_summary()
        self.assertEqual(result["skill_changes"][0]["eligible_article_count"], 1)
        self.assertEqual(result["skill_changes"][0]["first_draft_pass_count"], 1)
        self.assertEqual(result["skill_changes"][0]["user_accepted_count"], 1)
        self.assertIn("スキル改善の一覧", result["日本語一覧"])


if __name__ == "__main__":
    unittest.main()
