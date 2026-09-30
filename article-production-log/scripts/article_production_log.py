#!/usr/bin/env python3
"""ブログ記事制作の依頼・結果・証拠を詳細ログへ保存する。"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
CANONICAL_PROJECT = Path(r"C:\AIフォルダ\ブログ\site")
QUALITY_DIMENSIONS = {
    "search_intent",
    "facts_freshness",
    "structure",
    "readability",
    "audience",
    "comparison",
    "cta",
    "internal_links",
    "ui_mobile",
    "images",
    "publication_boundary",
    "article_identity",
    "workflow",
}
REQUEST_TYPES = {
    "initial_request",
    "correction",
    "review",
    "clarification",
    "approval",
    "stop",
    "resume",
}
RESULT_STATUSES = {
    "open",
    "in_progress",
    "blocked",
    "implemented",
    "verified",
    "preview_ready",
    "published",
    "stopped",
    "superseded",
}
CLASSIFICATIONS = {
    "one_off",
    "preference_candidate",
    "existing_rule_execution_gap",
    "skill_gap",
    "factual_update",
    "unclear",
}
REPORT_NAMES = ("品質傾向.md", "再発問題.md", "スキル別問題.md", "継続ルール候補.md")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_component(value: str, fallback: str = "item", limit: int = 64) -> str:
    value = re.sub(r"[^\w.-]+", "-", value.strip(), flags=re.UNICODE)
    value = re.sub(r"[-_.]{2,}", "-", value).strip("-_.")
    return (value or fallback)[:limit]


def norm_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve())


def same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(norm_path(left)) == os.path.normcase(norm_path(right))


def read_text_arg(text: str | None, file_name: str | None, field: str) -> str:
    if file_name:
        return Path(file_name).read_text(encoding="utf-8")
    if text is None:
        raise ValueError(f"{field}が必要です")
    return text


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value != ""))


def json_value(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("JSONはオブジェクトで指定してください")
    return parsed


def md_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def md_text(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "記録なし"
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value) if value else "記録なし"
    return str(value)


def table_cell(value: Any) -> str:
    if value is None or value == "":
        return "記録なし"
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


class FileLock:
    def __init__(self, path: Path, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self.handle: Any = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        started = time.monotonic()
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self.handle.seek(0)
                    if self.handle.tell() == 0:
                        self.handle.write(b"0")
                        self.handle.flush()
                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() - started >= self.timeout:
                    self.handle.close()
                    raise TimeoutError(f"ログロックを取得できません: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.handle is None:
            return
        with contextlib.suppress(OSError):
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


class QualityLogStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.events_path = self.root / "events.jsonl"
        self.records_dir = self.root / "records"
        self.user_log_dir = self.root / "userLog"
        self.artifacts_dir = self.root / "artifacts"
        self.articles_dir = self.root / "articles"
        self.reports_dir = self.root / "reports"
        self.raw_dir = self.root / "raw"
        self.lock_path = self.root / ".store.lock"

    def init(self, render: bool = False) -> dict[str, Any]:
        for directory in (
            self.root,
            self.records_dir,
            self.user_log_dir,
            self.artifacts_dir,
            self.articles_dir,
            self.reports_dir,
            self.raw_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        meta_path = self.root / "meta.json"
        if not meta_path.exists():
            self._atomic_json(
                meta_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "store_type": "article_quality_log",
                    "canonical_project": norm_path(CANONICAL_PROJECT),
                    "created_at": utc_now(),
                },
            )
        self.events_path.touch(exist_ok=True)
        if render or any(not (self.reports_dir / name).exists() for name in REPORT_NAMES):
            self.render_all()
        return {"ok": True, "root": str(self.root), "schema_version": SCHEMA_VERSION}

    def _atomic_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temp, path)

    def _atomic_json(self, path: Path, value: Any) -> None:
        self._atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line_no, line in enumerate(self.events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"events.jsonl {line_no}行目が壊れています: {exc}") from exc
            if event.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"events.jsonl {line_no}行目のschema_versionが不正です")
            events.append(event)
        return events

    def append_event(self, event_type: str, payload: dict[str, Any], event_key: str = "") -> dict[str, Any]:
        existing_events = self.read_events()
        if event_key:
            payload_hash = sha256_bytes(canonical_json(payload).encode("utf-8"))
            for event in existing_events:
                if event.get("event_key") == event_key:
                    if event.get("event_type") != event_type or event.get("payload_sha256") != payload_hash:
                        raise ValueError(f"同じevent_keyに異なる内容があります: {event_key}")
                    return event
        else:
            payload_hash = sha256_bytes(canonical_json(payload).encode("utf-8"))
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "event_key": event_key,
            "event_type": event_type,
            "created_at": utc_now(),
            "payload_sha256": payload_hash,
            "payload": payload,
        }
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def record_path(self, log_id: str) -> Path:
        return self.records_dir / f"{safe_component(log_id)}.json"

    def load_record(self, log_id: str) -> dict[str, Any]:
        path = self.record_path(log_id)
        if not path.exists():
            raise FileNotFoundError(f"log_idが見つかりません: {log_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema_version") != SCHEMA_VERSION or record.get("log_id") != log_id:
            raise ValueError(f"レコード識別子が不正です: {path}")
        return record

    def read_records(self) -> list[dict[str, Any]]:
        records = []
        if not self.records_dir.exists():
            return records
        for path in sorted(self.records_dir.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"不正なschema_versionです: {path}")
            records.append(record)
        return records

    def _capture(self, source: str | Path, log_id: str, phase: str, label: str = "article") -> dict[str, Any]:
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"スナップショット対象がありません: {source_path}")
        digest = sha256_file(source_path)
        suffix = source_path.suffix
        name = f"{safe_component(label)}--{digest[:12]}{suffix}"
        destination = self.artifacts_dir / safe_component(log_id) / phase / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source_path, destination)
        return {
            "phase": phase,
            "label": label,
            "source_path": str(source_path),
            "stored_path": str(destination),
            "sha256": digest,
            "size": source_path.stat().st_size,
            "captured_at": utc_now(),
        }

    def start_log(self, args: argparse.Namespace) -> dict[str, Any]:
        project_root = norm_path(args.project_root)
        if not same_path(project_root, CANONICAL_PROJECT):
            raise ValueError(f"対象外のproject_rootです: {project_root}")
        dimensions = unique(args.quality_dimension)
        invalid = sorted(set(dimensions) - QUALITY_DIMENSIONS)
        if invalid:
            raise ValueError(f"不正な品質軸です: {', '.join(invalid)}")
        request_text = read_text_arg(args.request_text, args.request_text_file, "request_text")
        if request_text == "":
            raise ValueError("request_textは空にできません")
        if args.source_provenance == "hook_verified":
            if not args.source_hook_event_id:
                raise ValueError("hook_verifiedにはsource_hook_event_idが必要です")
            hooks = [event for event in self.read_events() if event.get("event_id") == args.source_hook_event_id and event.get("event_type") == "hook_capture"]
            if len(hooks) != 1 or hooks[0]["payload"].get("user_prompt") != request_text:
                raise ValueError("フックのユーザー原文とrequest_textが一致しません")
        purpose_type = None if args.article_business_purpose == "pending_confirmation" else args.article_business_purpose
        expected_primary_action = {
            "conversion": "affiliate_conversion",
            "traffic": "internal_conversion_article_visit",
        }.get(purpose_type)
        if purpose_type:
            if not args.business_purpose_confirmed_by_user:
                raise ValueError("conversionまたはtrafficにはbusiness_purpose_confirmed_by_userが必要です")
            if not args.business_purpose_confirmation_text.strip() or not args.business_purpose_confirmation_source_ref.strip():
                raise ValueError("確認済み事業目的には確認原文と出典が必要です")
        elif args.business_purpose_confirmed_by_user or args.business_purpose_confirmation_text.strip() or args.business_purpose_confirmation_source_ref.strip():
            raise ValueError("pending_confirmationへ確認済み情報を付けることはできません")
        log_id = args.log_id or str(uuid.uuid4())
        created_at = utc_now()
        record = {
            "schema_version": SCHEMA_VERSION,
            "log_id": log_id,
            "created_at": created_at,
            "updated_at": created_at,
            "status": "open",
            "target": {
                "project_root": project_root,
                "article_id": args.article_id,
                "article_path": norm_path(args.article_path) if args.article_path else "",
                "request_type": args.request_type,
                "title": args.title or "",
                "article_business_purpose": {
                    "status": "confirmed" if purpose_type else "pending_confirmation",
                    "type": purpose_type,
                    "confirmation_text": args.business_purpose_confirmation_text,
                    "confirmation_source_ref": args.business_purpose_confirmation_source_ref,
                    "confirmed_by_user": args.business_purpose_confirmed_by_user,
                    "primary_action": expected_primary_action,
                },
            },
            "source": {
                "source_ref": args.source_ref,
                "session_id": args.session_id or "",
                "turn_id": args.turn_id or "",
                "hook_event_ids": unique([args.source_hook_event_id or ""]),
                "uttered_at": args.uttered_at or "",
                "provenance": args.source_provenance,
            },
            "routing": {
                "entry_skill": args.entry_skill,
                "target_skills": unique(args.target_skill),
                "stage": args.stage,
                "run_id": args.run_id,
                "parent_run_id": args.parent_run_id or "",
            },
            "request": {
                "verbatim": request_text,
                "context": unique(args.context),
                "explicit_requirements": unique(args.explicit_requirement),
                "inferred_requirements": unique(args.inferred_requirement),
                "unknowns": unique(args.unknown),
                "exclusions": unique(args.exclusion),
                "observed_before": args.observed_before or "",
            },
            "quality": {"dimensions": dimensions, "issues": []},
            "evidence": {"before": [], "after": [], "changed_files": [], "verification": []},
            "result": {
                "result_text": "",
                "observed_after": "",
                "unchanged_scope": [],
                "unresolved": [],
                "funnel_alignment": "unassessed",
                "funnel_alignment_reason": "",
            },
            "learning": {
                "classification": "unclear",
                "candidate_key": args.candidate_key or "",
                "improvement_decision": "unassessed",
                "improvement_reason": "",
                "rule_candidate": {
                    "status": "none",
                    "rule_text": "",
                    "scope": [],
                    "not_applicable_to": [],
                    "acceptance_criteria": [],
                },
            },
            "feedback_links": {"request_event_id": args.feedback_request_event_id or "", "result_event_id": ""},
            "user_decision": None,
        }
        request_signature = {
            "target": record["target"],
            "source": record["source"],
            "routing": record["routing"],
            "request": record["request"],
            "quality_dimensions": record["quality"]["dimensions"],
            "feedback_request_event_id": record["feedback_links"]["request_event_id"],
        }
        request_sha256 = sha256_bytes(canonical_json(request_signature).encode("utf-8"))
        with FileLock(self.lock_path):
            if args.event_key:
                for existing in self.read_events():
                    if existing.get("event_key") != args.event_key:
                        continue
                    if (
                        existing.get("event_type") != "log_started"
                        or existing.get("payload", {}).get("request_sha256") != request_sha256
                    ):
                        raise ValueError(f"同じevent_keyに異なる開始内容があります: {args.event_key}")
                    existing_log_id = existing["payload"]["log_id"]
                    existing_record = self.load_record(existing_log_id)
                    return {
                        "ok": True,
                        "idempotent": True,
                        "log_id": existing_log_id,
                        "event_id": existing["event_id"],
                        "markdown_path": existing_record["markdown_path"],
                        "record_path": str(self.record_path(existing_log_id)),
                    }
            if self.record_path(log_id).exists():
                raise ValueError(f"log_idは既に存在します: {log_id}")
            article_path = record["target"]["article_path"]
            if args.snapshot_before and article_path:
                record["evidence"]["before"].append(self._capture(article_path, log_id, "before"))
            filename = self._markdown_filename(record)
            record["markdown_path"] = str(self.user_log_dir / filename)
            payload = {
                "log_id": log_id,
                "request_sha256": request_sha256,
                "record_sha256": sha256_bytes(canonical_json(record).encode("utf-8")),
            }
            event = self.append_event("log_started", payload, args.event_key or "")
            record["event_ids"] = [event["event_id"]]
            self._atomic_json(self.record_path(log_id), record)
            self.render_all()
        return {
            "ok": True,
            "log_id": log_id,
            "event_id": event["event_id"],
            "markdown_path": record["markdown_path"],
            "record_path": str(self.record_path(log_id)),
        }

    def finish_log(self, args: argparse.Namespace) -> dict[str, Any]:
        with FileLock(self.lock_path):
            record = self.load_record(args.log_id)
            dimensions = unique(record["quality"]["dimensions"] + args.quality_dimension)
            invalid = sorted(set(dimensions) - QUALITY_DIMENSIONS)
            if invalid:
                raise ValueError(f"不正な品質軸です: {', '.join(invalid)}")
            issues = [json_value(item) for item in args.issue_json]
            for issue in issues:
                dimension = issue.get("dimension", "")
                if dimension and dimension not in QUALITY_DIMENSIONS:
                    raise ValueError(f"不正な問題の品質軸です: {dimension}")
            record["quality"]["dimensions"] = dimensions
            record["quality"]["issues"].extend(issues)
            record["status"] = args.status
            record["result"]["result_text"] = read_text_arg(args.result_text, args.result_text_file, "result_text")
            record["result"]["observed_after"] = args.observed_after or ""
            record["result"]["unchanged_scope"] = unique(args.unchanged_scope)
            record["result"]["unresolved"] = unique(args.unresolved)
            record["result"]["funnel_alignment"] = args.funnel_alignment
            record["result"]["funnel_alignment_reason"] = args.funnel_alignment_reason
            if args.funnel_alignment != "unassessed" and not args.funnel_alignment_reason.strip():
                raise ValueError("funnel_alignmentを判定した場合はfunnel_alignment_reasonが必要です")
            record["evidence"]["changed_files"] = unique(args.changed_file)
            record["evidence"]["verification"] = unique(args.verification)
            record["learning"]["classification"] = args.classification
            if args.improvement_decision != "unassessed" and not args.improvement_reason.strip():
                raise ValueError("スキル修正を判定した場合はimprovement_reasonが必要です")
            if args.classification in {"one_off", "factual_update"} and args.improvement_decision in {"candidate", "explicit_skill_change_request"}:
                raise ValueError("今回限りの指定・変動事実をスキル修正候補として扱えません")
            record["learning"]["improvement_decision"] = args.improvement_decision
            record["learning"]["improvement_reason"] = args.improvement_reason
            if args.candidate_key:
                record["learning"]["candidate_key"] = args.candidate_key
            if args.rule_candidate_text:
                record["learning"]["rule_candidate"] = {
                    "status": "candidate",
                    "rule_text": args.rule_candidate_text,
                    "scope": unique(args.rule_scope),
                    "not_applicable_to": unique(args.rule_exclusion),
                    "acceptance_criteria": unique(args.acceptance_criterion),
                }
            if args.feedback_request_event_id:
                record["feedback_links"]["request_event_id"] = args.feedback_request_event_id
            if args.feedback_result_event_id:
                record["feedback_links"]["result_event_id"] = args.feedback_result_event_id
            article_path = record["target"]["article_path"]
            if args.snapshot_after and article_path:
                record["evidence"]["after"].append(self._capture(article_path, args.log_id, "after"))
            record["updated_at"] = utc_now()
            payload = {
                "log_id": args.log_id,
                "status": args.status,
                "classification": args.classification,
                "record_sha256": sha256_bytes(canonical_json(record).encode("utf-8")),
            }
            event = self.append_event("log_finished", payload, args.event_key or "")
            record.setdefault("event_ids", []).append(event["event_id"])
            self._atomic_json(self.record_path(args.log_id), record)
            self.render_all()
        return {
            "ok": True,
            "log_id": args.log_id,
            "event_id": event["event_id"],
            "status": record["status"],
            "markdown_path": record["markdown_path"],
        }

    def record_decision(self, args: argparse.Namespace) -> dict[str, Any]:
        decision_text = read_text_arg(args.decision_text, args.decision_text_file, "decision_text")
        with FileLock(self.lock_path):
            record = self.load_record(args.log_id)
            decision = {
                "decision": args.decision,
                "approval_target": args.approval_target or "",
                "decision_text": decision_text,
                "source_ref": args.source_ref,
                "recorded_at": utc_now(),
            }
            event = self.append_event("user_decision_recorded", {"log_id": args.log_id, **decision}, args.event_key or "")
            record["user_decision"] = decision
            record["updated_at"] = utc_now()
            record.setdefault("event_ids", []).append(event["event_id"])
            self._atomic_json(self.record_path(args.log_id), record)
            self.render_all()
        return {"ok": True, "log_id": args.log_id, "event_id": event["event_id"]}

    def hook_event(self, raw: dict[str, Any]) -> dict[str, Any]:
        event_name = str(raw.get("hook_event_name") or raw.get("event_name") or "unknown")
        session_id = str(raw.get("session_id") or "unknown-session")
        turn_id = str(raw.get("turn_id") or raw.get("message_id") or "")
        prompt = raw.get("user_prompt")
        if prompt is None:
            prompt = raw.get("prompt")
        assistant = raw.get("last_assistant_message")
        transcript_path = str(raw.get("transcript_path") or "")
        transcript_hash = ""
        if transcript_path:
            transcript = Path(transcript_path).expanduser()
            if transcript.is_file():
                transcript_hash = sha256_file(transcript)
        captured = {
            "hook_event_name": event_name,
            "session_id": session_id,
            "turn_id": turn_id,
            "cwd": str(raw.get("cwd") or ""),
            "user_prompt": prompt if isinstance(prompt, str) else "",
            "last_assistant_message": assistant if isinstance(assistant, str) else "",
            "transcript_path": transcript_path,
            "transcript_sha256": transcript_hash,
        }
        event_key = f"hook:{sha256_bytes(canonical_json(captured).encode('utf-8'))}"
        with FileLock(self.lock_path):
            event = self.append_event("hook_capture", captured, event_key)
            session_dir = self.raw_dir / "hooks" / safe_component(session_id)
            raw_path = session_dir / f"{event['event_id']}.json"
            if not raw_path.exists():
                self._atomic_json(
                    raw_path,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "event_id": event["event_id"],
                        "captured_at": event["created_at"],
                        **captured,
                    },
                )
        return {
            "ok": True,
            "hook_event_name": event_name,
            "hook_event_id": event["event_id"],
            "raw_path": str(raw_path),
        }

    def _markdown_filename(self, record: dict[str, Any]) -> str:
        date = record["created_at"][:10]
        article = safe_component(record["target"]["article_id"], "article", 48)
        title = record["target"].get("title") or record["target"]["request_type"]
        issue = safe_component(title, "request", 48)
        return f"{date}_{article}_{issue}_{record['log_id'][:8]}.md"

    def render_record(self, record: dict[str, Any]) -> str:
        target = record["target"]
        source = record["source"]
        routing = record["routing"]
        request = record["request"]
        quality = record["quality"]
        evidence = record["evidence"]
        result = record["result"]
        learning = record["learning"]
        business_purpose = target.get("article_business_purpose", {
            "status": "pending_confirmation",
            "type": None,
            "confirmation_text": "",
            "confirmation_source_ref": "",
            "confirmed_by_user": False,
            "primary_action": None,
        })
        candidate = learning["rule_candidate"]
        decision = record.get("user_decision")
        skill_assessment_lines = []
        if "improvement_decision" in learning:
            skill_assessment_lines = [
                "## スキル修正の判定", "",
                f"- 判定: `{learning['improvement_decision']}`",
                f"- 理由: {learning.get('improvement_reason') or '記録なし'}", "",
            ]
        source_provenance_lines = []
        if "provenance" in source:
            source_provenance_lines = [f"- 発言時点: `{source.get('uttered_at') or '不明'}` / 原文の取得: `{source['provenance']}`"]
        amendment_lines = []
        if record.get("amendments"):
            amendment_lines = ["## 過去ログの訂正", "", "保存済み原文は上書きせず、確認できた差分を追記する。", ""]
            for item in record["amendments"]:
                amendment_lines.extend([
                    f"- 保存済み抜粋: {item['original_excerpt']}",
                    f"- 確認した原文の抜粋: {item['corrected_excerpt']}",
                    f"- 参照: `{item['source_ref']}` / 取得: `{item['source_provenance']}`",
                    f"- 訂正理由: {item['reason']}",
                    f"- 記録イベント: `{item['event_id']}`", "",
                ])
        lines = [
            "---",
            f"schema_version: {md_scalar(record['schema_version'])}",
            f"log_id: {md_scalar(record['log_id'])}",
            f"created_at: {md_scalar(record['created_at'])}",
            f"updated_at: {md_scalar(record['updated_at'])}",
            f"status: {md_scalar(record['status'])}",
            f"article_id: {md_scalar(target['article_id'])}",
            f"article_path: {md_scalar(target['article_path'])}",
            f"request_type: {md_scalar(target['request_type'])}",
            f"article_business_purpose: {md_scalar(business_purpose.get('type') or business_purpose.get('status'))}",
            f"quality_dimensions: {md_scalar(quality['dimensions'])}",
            f"target_skills: {md_scalar(routing['target_skills'])}",
            "---",
            "",
            f"# {target.get('title') or target['article_id']} — 記事制作ログ",
            "",
            "## 概要",
            "",
            f"- 対象記事: `{target['article_id']}`",
            f"- 記事パス: `{target['article_path'] or '未確定'}`",
            f"- 依頼種別: `{target['request_type']}`",
            f"- 状態: `{record['status']}`",
            f"- 品質軸: {', '.join(quality['dimensions']) or '未分類'}",
            "",
            "## ユーザー原文",
            "",
                request["verbatim"] or "記録なし",
                "",
                *amendment_lines,
                "## 記事の事業目的",
                "",
                f"- 状態: `{business_purpose.get('status') or '記録なし'}`",
                f"- 種別: `{business_purpose.get('type') or '未確定'}`",
                f"- 主要行動: `{business_purpose.get('primary_action') or '未確定'}`",
                f"- ユーザー確認: `{business_purpose.get('confirmed_by_user', False)}`",
                f"- 確認原文: {business_purpose.get('confirmation_text') or '記録なし'}",
                f"- 確認出典: `{business_purpose.get('confirmation_source_ref') or '記録なし'}`",
                "",
                "## 依頼時の文脈",
            "",
            md_text(request["context"]),
            "",
            "## 要求の分解",
            "",
            "### 明示要件",
            "",
            md_text(request["explicit_requirements"]),
            "",
            "### AIの解釈（明示要件ではない）",
            "",
            md_text(request["inferred_requirements"]),
            "",
            "### 未確定事項",
            "",
            md_text(request["unknowns"]),
            "",
            "### 対象外・保持範囲",
            "",
            md_text(request["exclusions"]),
            "",
            "## 品質課題",
            "",
        ]
        if quality["issues"]:
            lines.extend(["| 問題 | 原因 | 品質軸 | 工程/スキル | 優先度 | 確度 | 状態 |", "|---|---|---|---|---|---|---|"])
            for issue in quality["issues"]:
                owner = issue.get("stage") or issue.get("skill") or ""
                lines.append(
                    "| " + " | ".join(
                        table_cell(issue.get(key, ""))
                        for key in ("problem", "cause", "dimension")
                    ) + f" | {table_cell(owner)} | {table_cell(issue.get('priority'))} | {table_cell(issue.get('certainty'))} | {table_cell(issue.get('status'))} |"
                )
        else:
            lines.append("記録なし")
        lines.extend(
            [
                "",
                "## 変更前",
                "",
                md_text(request["observed_before"]),
                "",
                self._render_artifacts(evidence["before"]),
                "",
                "## 実施内容",
                "",
                md_text(result["result_text"]),
                "",
                "### 変更ファイル",
                "",
                md_text(evidence["changed_files"]),
                "",
                "## 変更しなかった範囲",
                "",
                md_text(result["unchanged_scope"]),
                "",
                "## 変更後",
                "",
                md_text(result["observed_after"]),
                "",
                self._render_artifacts(evidence["after"]),
                "",
                "## 品質検証",
                "",
                md_text(evidence["verification"]),
                "",
                "## 目的別導線の整合",
                "",
                f"- 判定: `{result.get('funnel_alignment', 'unassessed')}`",
                f"- 根拠: {result.get('funnel_alignment_reason') or '記録なし'}",
                "",
                "## 学習分類",
                "",
                f"- 分類: `{learning['classification']}`",
                f"- 再発キー: `{learning['candidate_key'] or 'なし'}`",
                "",
                *skill_assessment_lines,
                "## 継続ルール候補",
                "",
                f"- 状態: `{candidate['status']}`",
                f"- 候補文: {candidate['rule_text'] or '記録なし'}",
                "- 適用範囲:",
                md_text(candidate["scope"]),
                "- 除外条件:",
                md_text(candidate["not_applicable_to"]),
                "- 受入基準:",
                md_text(candidate["acceptance_criteria"]),
                "",
                "> 候補は未承認であり、`article-skill-feedback`で明示承認・検証・有効化されるまで制作入力へ適用しない。",
                "",
                "## ユーザー判断",
                "",
                md_text(decision) if decision else "記録なし",
                "",
                "## 未解決事項",
                "",
                md_text(result["unresolved"]),
                "",
                "## 関連情報",
                "",
                f"- source_ref: `{source['source_ref']}`",
                *source_provenance_lines,
                f"- session_id / turn_id: `{source['session_id']}` / `{source['turn_id']}`",
                f"- raw hook IDs: {', '.join(source['hook_event_ids']) or 'なし'}",
                f"- run_id / parent_run_id: `{routing['run_id']}` / `{routing['parent_run_id']}`",
                f"- entry_skill: `{routing['entry_skill']}`",
                f"- target_skills: {', '.join(routing['target_skills']) or 'なし'}",
                f"- feedback request/result: `{record['feedback_links']['request_event_id']}` / `{record['feedback_links']['result_event_id']}`",
                "",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _render_artifacts(items: list[dict[str, Any]]) -> str:
        if not items:
            return "証拠ファイル: 記録なし"
        return "\n".join(
            f"- `{item['stored_path']}`（SHA-256: `{item['sha256']}`、元: `{item['source_path']}`）"
            for item in items
        )

    def render_all(self) -> None:
        records = self.read_records()
        for record in records:
            markdown_path = Path(record["markdown_path"])
            self._atomic_text(markdown_path, self.render_record(record))
        self._render_article_histories(records)
        self._render_reports(records)

    def _render_article_histories(self, records: list[dict[str, Any]]) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(record["target"]["article_id"], []).append(record)
        for article_id, items in grouped.items():
            lines = [f"# {article_id} 制作履歴", "", "| 日時 | 種別 | 状態 | 品質軸 | 詳細ログ |", "|---|---|---|---|---|"]
            for item in sorted(items, key=lambda value: value["created_at"]):
                rel = os.path.relpath(item["markdown_path"], self.articles_dir / safe_component(article_id)).replace("\\", "/")
                lines.append(
                    f"| {item['created_at']} | {item['target']['request_type']} | {item['status']} | "
                    f"{', '.join(item['quality']['dimensions']) or '未分類'} | [詳細]({rel}) |"
                )
            self._atomic_text(self.articles_dir / safe_component(article_id) / "制作履歴.md", "\n".join(lines) + "\n")

    def _render_reports(self, records: list[dict[str, Any]]) -> None:
        dimension_counts = Counter(d for r in records for d in r["quality"]["dimensions"])
        classification_counts = Counter(r["learning"]["classification"] for r in records)
        quality_lines = ["# 品質傾向", "", f"記録件数: {len(records)}", "", "## 品質軸", ""]
        quality_lines.extend(f"- `{key}`: {count}件" for key, count in dimension_counts.most_common())
        quality_lines.extend(["", "## 学習分類", ""])
        quality_lines.extend(f"- `{key}`: {count}件" for key, count in classification_counts.most_common())
        if not records:
            quality_lines.append("記録なし")

        recurrence = Counter(r["learning"]["candidate_key"] for r in records if r["learning"]["candidate_key"])
        recurring_lines = ["# 再発問題", "", "同じ`candidate_key`を持つ依頼を集計する。", ""]
        recurring_lines.extend(f"- `{key}`: {count}件" for key, count in recurrence.most_common())
        if not recurrence:
            recurring_lines.append("記録なし")

        skill_counts = Counter(skill for r in records for skill in r["routing"]["target_skills"])
        skill_lines = ["# スキル別問題", ""]
        skill_lines.extend(f"- `{key}`: {count}件" for key, count in skill_counts.most_common())
        if not skill_counts:
            skill_lines.append("記録なし")

        candidate_lines = ["# 継続ルール候補", "", "未承認候補だけを表示する。", ""]
        candidates = [r for r in records if r["learning"]["rule_candidate"]["status"] == "candidate"]
        for record in candidates:
            candidate = record["learning"]["rule_candidate"]
            candidate_lines.extend(
                [
                    f"## {record['target']['article_id']} / {record['log_id']}",
                    "",
                    candidate["rule_text"],
                    "",
                    f"- 分類: `{record['learning']['classification']}`",
                    f"- 詳細: `{record['markdown_path']}`",
                    "",
                ]
            )
        if not candidates:
            candidate_lines.append("記録なし")

        report_values = {
            "品質傾向.md": "\n".join(quality_lines) + "\n",
            "再発問題.md": "\n".join(recurring_lines) + "\n",
            "スキル別問題.md": "\n".join(skill_lines) + "\n",
            "継続ルール候補.md": "\n".join(candidate_lines) + "\n",
        }
        for name, text in report_values.items():
            self._atomic_text(self.reports_dir / name, text)

    def verify(self) -> dict[str, Any]:
        errors: list[str] = []
        try:
            events = self.read_events()
        except Exception as exc:
            events = []
            errors.append(str(exc))
        try:
            records = self.read_records()
        except Exception as exc:
            records = []
            errors.append(str(exc))
        event_ids = [event.get("event_id") for event in events]
        if len(event_ids) != len(set(event_ids)):
            errors.append("event_idが重複しています")
        log_ids = [record.get("log_id") for record in records]
        if len(log_ids) != len(set(log_ids)):
            errors.append("log_idが重複しています")
        for record in records:
            if not same_path(record["target"]["project_root"], CANONICAL_PROJECT):
                errors.append(f"対象外project_root: {record['log_id']}")
            markdown_path = Path(record.get("markdown_path", ""))
            if not markdown_path.is_file():
                errors.append(f"Markdownがありません: {record['log_id']}")
            elif markdown_path.read_text(encoding="utf-8") != self.render_record(record):
                errors.append(f"Markdownが構造化正本と一致しません: {record['log_id']}")
            for phase in ("before", "after"):
                for item in record["evidence"].get(phase, []):
                    stored = Path(item["stored_path"])
                    if not stored.is_file():
                        errors.append(f"証拠がありません: {stored}")
                    elif sha256_file(stored) != item["sha256"]:
                        errors.append(f"証拠ハッシュ不一致: {stored}")
            if record["learning"]["rule_candidate"]["status"] not in {"none", "candidate"}:
                errors.append(f"品質ログが未対応のルール状態を持ちます: {record['log_id']}")
            if record["source"].get("provenance") == "hook_verified":
                matching = [event for event in events if event.get("event_type") == "hook_capture" and event.get("event_id") in record["source"].get("hook_event_ids", [])]
                if len(matching) != 1 or matching[0]["payload"].get("user_prompt") != record["request"]["verbatim"]:
                    errors.append(f"フック原文と依頼原文が一致しません: {record['log_id']}")
            for amendment in record.get("amendments", []):
                matching = [event for event in events if event.get("event_type") == "legacy_amendment" and event.get("event_id") == amendment.get("event_id")]
                if len(matching) != 1 or matching[0]["payload"].get("log_id") != record["log_id"]:
                    errors.append(f"過去ログの訂正イベントが不一致です: {record['log_id']}")
                elif any(matching[0]["payload"].get(key) != amendment.get(key) for key in ("original_excerpt", "corrected_excerpt", "source_ref", "source_provenance", "reason")):
                    errors.append(f"過去ログの訂正内容がイベントと不一致です: {record['log_id']}")
                if amendment.get("original_excerpt") not in record["request"]["verbatim"]:
                    errors.append(f"訂正前の抜粋が保存原文にありません: {record['log_id']}")
        for name in REPORT_NAMES:
            if not (self.reports_dir / name).is_file():
                errors.append(f"レポートがありません: {name}")
        return {
            "ok": not errors,
            "root": str(self.root),
            "records": len(records),
            "events": len(events),
            "errors": errors,
        }

    def audit_requests(self, article_id: str, run_id: str, expected_refs: list[str]) -> dict[str, Any]:
        records = [record for record in self.read_records() if record["target"]["article_id"] == article_id and record["routing"]["run_id"] == run_id]
        found = {record["source"]["source_ref"] for record in records}
        unfinished = [record["log_id"] for record in records if record["status"] in {"open", "in_progress"}]
        unassessed = [record["log_id"] for record in records if record["target"]["request_type"] == "correction" and record["learning"].get("improvement_decision", "unassessed") == "unassessed"]
        missing = sorted(set(expected_refs) - found)
        return {"ok": not (missing or unfinished or unassessed), "article_id": article_id, "run_id": run_id, "missing_source_refs": missing, "unfinished_log_ids": unfinished, "unassessed_correction_log_ids": unassessed, "matched_record_count": len(records)}

    def audit_legacy(self, article_id: str = "") -> dict[str, Any]:
        records = [record for record in self.read_records() if not article_id or record["target"]["article_id"] == article_id]
        needs_review = []
        for record in records:
            flags = []
            if not record["source"].get("provenance"):
                flags.append("原文の取得方法が未記録")
            if record["target"]["request_type"] == "correction":
                if not record["quality"].get("issues"):
                    flags.append("修正事項ごとの品質課題が未整理")
                if record["learning"].get("improvement_decision", "unassessed") == "unassessed":
                    flags.append("スキル修正の要否が未判定")
                if not record["feedback_links"].get("request_event_id"):
                    flags.append("改善台帳への依頼リンクが未確認")
            if record["status"] in {"verified", "preview_ready", "published"} and not (record["evidence"].get("before") or record["evidence"].get("after")):
                flags.append("変更前後の保存証拠がない。検証の有無は別途確認")
            if flags:
                needs_review.append({"log_id": record["log_id"], "article_id": record["target"]["article_id"], "source_ref": record["source"]["source_ref"], "確認事項": flags})
        lines = ["# 旧記事ログの確認", "", f"対象レコード: {len(records)}件 / 要確認: {len(needs_review)}件", "", "保存形式が正常でも、原文や過去の検証内容が正しいとは限りません。証拠のない箇所を推測で埋めません。", ""]
        for item in needs_review:
            lines.append(f"- {item['article_id']} / {item['log_id']}: {'、'.join(item['確認事項'])}")
        return {"ok": True, "article_id": article_id or "all", "record_count": len(records), "needs_review": needs_review, "日本語一覧": "\n".join(lines)}

    def amend_legacy(self, args: argparse.Namespace) -> dict[str, Any]:
        if not args.original_excerpt or not args.corrected_excerpt or args.original_excerpt == args.corrected_excerpt:
            raise ValueError("異なる訂正前後の抜粋が必要です")
        if not args.source_ref or not args.reason:
            raise ValueError("訂正の参照元と理由が必要です")
        with FileLock(self.lock_path):
            record = self.load_record(args.log_id)
            if args.original_excerpt not in record["request"]["verbatim"]:
                raise ValueError("保存済み原文に訂正前の抜粋がありません")
            if args.source_provenance == "raw_hook_verified":
                raw = [event for event in self.read_events() if event.get("event_type") == "hook_capture" and event.get("event_id") == args.source_ref]
                if len(raw) != 1 or args.corrected_excerpt not in raw[0]["payload"].get("user_prompt", ""):
                    raise ValueError("rawフック原文の参照と訂正後の抜粋が一致しません")
            payload = {
                "log_id": args.log_id,
                "original_excerpt": args.original_excerpt,
                "corrected_excerpt": args.corrected_excerpt,
                "source_ref": args.source_ref,
                "source_provenance": args.source_provenance,
                "reason": args.reason,
            }
            event = self.append_event("legacy_amendment", payload, args.event_key)
            amendment = {**payload, "event_id": event["event_id"], "recorded_at": event["created_at"]}
            existing = record.setdefault("amendments", [])
            if not any(item.get("event_id") == event["event_id"] for item in existing):
                existing.append(amendment)
                record["updated_at"] = utc_now()
                self._atomic_json(self.record_path(args.log_id), record)
                self.render_all()
            return {"ok": True, "log_id": args.log_id, "event_id": event["event_id"], "markdown_path": record["markdown_path"], "amendment_count": len(existing)}


def add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("init")
    add_root(command)

    command = commands.add_parser("hook-event")
    add_root(command)

    command = commands.add_parser("start-log")
    add_root(command)
    command.add_argument("--project-root", required=True)
    command.add_argument("--article-id", required=True)
    command.add_argument("--article-path", default="")
    command.add_argument("--request-type", choices=sorted(REQUEST_TYPES), required=True)
    request_group = command.add_mutually_exclusive_group(required=True)
    request_group.add_argument("--request-text")
    request_group.add_argument("--request-text-file")
    command.add_argument("--source-ref", required=True)
    command.add_argument("--entry-skill", required=True)
    command.add_argument("--target-skill", action="append", required=True)
    command.add_argument("--stage", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--parent-run-id")
    command.add_argument("--title")
    command.add_argument("--quality-dimension", action="append", default=[])
    command.add_argument("--article-business-purpose", choices=["pending_confirmation", "conversion", "traffic"], default="pending_confirmation")
    command.add_argument("--business-purpose-confirmation-text", default="")
    command.add_argument("--business-purpose-confirmation-source-ref", default="")
    command.add_argument("--business-purpose-confirmed-by-user", action="store_true")
    command.add_argument("--context", action="append", default=[])
    command.add_argument("--explicit-requirement", action="append", default=[])
    command.add_argument("--inferred-requirement", action="append", default=[])
    command.add_argument("--unknown", action="append", default=[])
    command.add_argument("--exclusion", action="append", default=[])
    command.add_argument("--observed-before")
    command.add_argument("--candidate-key")
    command.add_argument("--session-id")
    command.add_argument("--turn-id")
    command.add_argument("--source-hook-event-id")
    command.add_argument("--uttered-at", default="")
    command.add_argument("--source-provenance", choices=["direct", "hook_verified", "reconstructed", "unverified"], default="unverified")
    command.add_argument("--feedback-request-event-id")
    command.add_argument("--snapshot-before", action="store_true")
    command.add_argument("--event-key")
    command.add_argument("--log-id")

    command = commands.add_parser("finish-log")
    add_root(command)
    command.add_argument("--log-id", required=True)
    command.add_argument("--status", choices=sorted(RESULT_STATUSES - {"open"}), required=True)
    result_group = command.add_mutually_exclusive_group(required=True)
    result_group.add_argument("--result-text")
    result_group.add_argument("--result-text-file")
    command.add_argument("--observed-after")
    command.add_argument("--verification", action="append", default=[])
    command.add_argument("--classification", choices=sorted(CLASSIFICATIONS), required=True)
    command.add_argument("--improvement-decision", choices=["not_needed", "candidate", "explicit_skill_change_request", "pending_evidence", "unassessed"], default="unassessed")
    command.add_argument("--improvement-reason", default="")
    command.add_argument("--funnel-alignment", choices=["pass", "fail", "not_applicable", "unassessed"], default="unassessed")
    command.add_argument("--funnel-alignment-reason", default="")
    command.add_argument("--quality-dimension", action="append", default=[])
    command.add_argument("--issue-json", action="append", default=[])
    command.add_argument("--changed-file", action="append", default=[])
    command.add_argument("--unchanged-scope", action="append", default=[])
    command.add_argument("--unresolved", action="append", default=[])
    command.add_argument("--candidate-key")
    command.add_argument("--rule-candidate-text")
    command.add_argument("--rule-scope", action="append", default=[])
    command.add_argument("--rule-exclusion", action="append", default=[])
    command.add_argument("--acceptance-criterion", action="append", default=[])
    command.add_argument("--feedback-request-event-id")
    command.add_argument("--feedback-result-event-id")
    command.add_argument("--snapshot-after", action="store_true")
    command.add_argument("--event-key")

    command = commands.add_parser("record-decision")
    add_root(command)
    command.add_argument("--log-id", required=True)
    command.add_argument("--decision", choices=["approve", "reject", "clarify"], required=True)
    decision_group = command.add_mutually_exclusive_group(required=True)
    decision_group.add_argument("--decision-text")
    decision_group.add_argument("--decision-text-file")
    command.add_argument("--source-ref", required=True)
    command.add_argument("--approval-target")
    command.add_argument("--event-key")

    command = commands.add_parser("render")
    add_root(command)

    command = commands.add_parser("verify-store")
    add_root(command)
    command = commands.add_parser("audit-requests")
    add_root(command)
    command.add_argument("--article-id", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--expected-source-ref", action="append", default=[])
    command = commands.add_parser("audit-legacy")
    add_root(command)
    command.add_argument("--article-id", default="")
    command = commands.add_parser("amend-legacy")
    add_root(command)
    command.add_argument("--log-id", required=True)
    command.add_argument("--original-excerpt", required=True)
    command.add_argument("--corrected-excerpt", required=True)
    command.add_argument("--source-ref", required=True)
    command.add_argument("--source-provenance", choices=["visible_user_message", "raw_hook_verified"], required=True)
    command.add_argument("--reason", required=True)
    command.add_argument("--event-key", required=True)
    return parser


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = QualityLogStore(args.root)
    try:
        if args.command == "init":
            result = store.init(render=True)
        elif args.command == "hook-event":
            store.init()
            raw = json.load(sys.stdin)
            result = store.hook_event(raw)
            if result["hook_event_name"] == "UserPromptSubmit":
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": (
                            "ブログ記事の制作・修正に該当する場合はarticle-production-logを使用し、"
                            f"source_hook_event_id={result['hook_event_id']} を記事ログへ関連付けてください。"
                        ),
                    }
                }
                print(json.dumps(output, ensure_ascii=False))
                return 0
            print("{}")
            return 0
        elif args.command == "start-log":
            store.init()
            result = store.start_log(args)
        elif args.command == "finish-log":
            store.init()
            result = store.finish_log(args)
        elif args.command == "record-decision":
            store.init()
            result = store.record_decision(args)
        elif args.command == "render":
            store.init()
            with FileLock(store.lock_path):
                store.render_all()
            result = {"ok": True, "records": len(store.read_records())}
        elif args.command == "verify-store":
            result = store.verify()
        elif args.command == "audit-requests":
            result = store.audit_requests(args.article_id, args.run_id, args.expected_source_ref)
        elif args.command == "audit-legacy":
            result = store.audit_legacy(args.article_id)
        elif args.command == "amend-legacy":
            result = store.amend_legacy(args)
        else:
            raise ValueError(f"未対応コマンドです: {args.command}")
        print_json(result)
        return 0 if result.get("ok", False) else 1
    except Exception as exc:
        print_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
