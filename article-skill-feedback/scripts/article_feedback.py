#!/usr/bin/env python3
"""Versioned, approval-gated feedback ledger for one article workflow."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
CLASSIFICATIONS = {
    "one_off",
    "preference_candidate",
    "existing_rule_execution_gap",
    "skill_gap",
    "factual_update",
    "unclear",
}
IMPROVEMENT_DECISIONS = {"not_needed", "candidate", "explicit_skill_change_request", "pending_evidence", "unassessed"}
INTENT_SCOPES = {"article_only", "standing_explicit", "unclear"}


class LedgerError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_path(value: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.realpath(value)))


def nonempty(value: str, name: str) -> str:
    if not value or not value.strip():
        raise LedgerError(f"{name} must not be empty")
    return value


def safe_token(value: str, name: str) -> str:
    nonempty(value, name)
    compact = value.replace("-", "").replace("_", "")
    if not compact.isalnum():
        raise LedgerError(f"{name} must use letters, numbers, hyphen, or underscore")
    return value


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt

            if self.path.stat().st_size == 0:
                self.handle.write(b"0")
                self.handle.flush()
                self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle is not None:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


class FeedbackStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.events_path = self.root / "events.jsonl"
        self.rules_dir = self.root / "rules"
        self.releases_dir = self.root / "releases"
        self.index_path = self.root / "active-rules.json"
        self.lock_path = self.root / ".ledger.lock"

    def init(self) -> dict[str, Any]:
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.events_path.touch(exist_ok=True)
        if not self.index_path.exists():
            self._atomic_json(self.index_path, self._empty_index())
        verified = self.verify()
        return {"status": "initialized", "root": str(self.root), "active_count": verified["active_count"]}

    def _empty_index(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "source_events_sha256": sha256_value([]),
            "rules": [],
        }
        body["active_rule_set_id"] = sha256_value(body["rules"])
        return body

    def _atomic_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp_name)

    def read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            raise LedgerError(f"events file is missing: {self.events_path}")
        events: list[dict[str, Any]] = []
        for line_number, raw in enumerate(self.events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise LedgerError(f"corrupt JSONL at line {line_number}: {exc}") from exc
            required = {"schema_version", "event_id", "event_key", "event_type", "created_at", "payload"}
            if not required.issubset(event) or event["schema_version"] != SCHEMA_VERSION:
                raise LedgerError(f"invalid event schema at line {line_number}")
            events.append(event)
        return events

    def append_event(self, event_type: str, event_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonempty(event_type, "event_type")
        nonempty(event_key, "event_key")
        self.root.mkdir(parents=True, exist_ok=True)
        with FileLock(self.lock_path):
            self.events_path.touch(exist_ok=True)
            events = self.read_events()
            for existing in events:
                if existing["event_key"] == event_key:
                    if existing["event_type"] == event_type and existing["payload"] == payload:
                        result = dict(existing)
                        result["deduplicated"] = True
                        return result
                    raise LedgerError(f"event_key conflict: {event_key}")
            event = {
                "schema_version": SCHEMA_VERSION,
                "event_id": str(uuid.uuid4()),
                "event_key": event_key,
                "event_type": event_type,
                "created_at": utc_now(),
                "payload": payload,
            }
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            result = dict(event)
            result["deduplicated"] = False
            return result

    def find_event(self, event_id: str, event_type: str | None = None) -> dict[str, Any]:
        for event in self.read_events():
            if event["event_id"] == event_id and (event_type is None or event["event_type"] == event_type):
                return event
        raise LedgerError(f"event not found: {event_id}")

    def record_request(self, **values: Any) -> dict[str, Any]:
        for key in ("project_root", "article_id", "article_path", "entry_skill", "target_skill", "stage", "run_id", "request_text", "source_ref"):
            nonempty(str(values.get(key, "")), key)
        intent_scope = values.get("intent_scope", "unclear")
        if intent_scope not in INTENT_SCOPES:
            raise LedgerError(f"unsupported intent_scope: {intent_scope}")
        payload = {
            "project_root": normalized_path(values["project_root"]),
            "article_id": values["article_id"],
            "article_path": values["article_path"],
            "entry_skill": values["entry_skill"],
            "target_skill": values["target_skill"],
            "stage": values["stage"],
            "run_id": values["run_id"],
            "parent_run_id": values.get("parent_run_id"),
            "request_text": values["request_text"],
            "source_ref": values["source_ref"],
            "observed_before": values.get("observed_before", ""),
            "interpretation": values.get("interpretation", ""),
            "candidate_key": values.get("candidate_key", ""),
            "intent_scope": intent_scope,
            "uttered_at": values.get("uttered_at", ""),
        }
        return self.append_event("correction_request", values["event_key"], payload)

    def record_result(self, **values: Any) -> dict[str, Any]:
        request = self.find_event(values["request_event_id"], "correction_request")
        classification = values.get("classification", "unclear")
        if classification not in CLASSIFICATIONS:
            raise LedgerError(f"unsupported classification: {classification}")
        improvement_decision = values.get("improvement_decision", "unassessed")
        if improvement_decision not in IMPROVEMENT_DECISIONS:
            raise LedgerError(f"unsupported improvement_decision: {improvement_decision}")
        if improvement_decision != "unassessed":
            nonempty(values.get("improvement_reason", ""), "improvement_reason")
        payload = {
            "request_event_id": request["event_id"],
            "status": nonempty(values.get("status", ""), "status"),
            "result_text": nonempty(values.get("result_text", ""), "result_text"),
            "observed_after": values.get("observed_after", ""),
            "verification": values.get("verification", ""),
            "changed_files": list(values.get("changed_files", [])),
            "classification": classification,
            "improvement_decision": improvement_decision,
            "improvement_reason": values.get("improvement_reason", ""),
        }
        return self.append_event("correction_result", values["event_key"], payload)

    def propose_rule(self, **values: Any) -> dict[str, Any]:
        status = values.get("status", "proposed")
        if status not in {"proposed", "needs_clarification"}:
            raise LedgerError(f"unsupported proposal status: {status}")
        for key in ("rule_id", "revision", "rule_text"):
            nonempty(values.get(key, ""), key)
        for event_id in values.get("source_event_ids", []):
            self.find_event(event_id)
        scope = values["scope"]
        for key in ("project_roots", "entry_skills", "target_skills", "stages", "business_purposes", "article_types", "grades"):
            if not isinstance(scope.get(key), list) or not scope[key]:
                raise LedgerError(f"scope.{key} must be a non-empty list")
        scope = dict(scope)
        scope["project_roots"] = [normalized_path(p) if p != "*" else "*" for p in scope["project_roots"]]
        supersedes = list(values.get("supersedes", []))
        existing_revisions = [path.stem for path in (self.rules_dir / safe_token(values["rule_id"], "rule_id")).glob("*.json") if path.stem != values["revision"]]
        if existing_revisions and not self.rule_path(values["rule_id"], values["revision"]).exists() and not any(target.startswith(f"{values['rule_id']}@") for target in supersedes):
            raise LedgerError(f"new revision must identify the prior rule in supersedes: {values['rule_id']}")
        for target in supersedes:
            if "@" not in target:
                raise LedgerError(f"supersedes must identify rule_id@revision: {target}")
            old_id, old_revision = target.rsplit("@", 1)
            self.load_rule(old_id, old_revision)
        if f"{values['rule_id']}@{values['revision']}" in supersedes:
            raise LedgerError("a rule cannot supersede itself")
        proposal_base = {
            "schema_version": SCHEMA_VERSION,
            "rule_id": values["rule_id"],
            "revision": values["revision"],
            "status": status,
            "rule_text": values["rule_text"],
            "scope": scope,
            "not_applicable_to": list(values.get("not_applicable_to", [])),
            "source_event_ids": list(values.get("source_event_ids", [])),
            "acceptance_criteria": list(values.get("acceptance_criteria", [])),
            "supersedes": supersedes,
        }
        path = self.rule_path(values["rule_id"], values["revision"])
        if path.exists():
            existing = self.load_rule(values["rule_id"], values["revision"])
            existing_base = dict(existing)
            existing_base.pop("proposal_sha256", None)
            existing_base.pop("created_at", None)
            if not existing_base.get("supersedes"):
                existing_base.pop("supersedes", None)
                proposal_base.pop("supersedes", None)
            if existing_base != proposal_base:
                raise LedgerError(f"rule revision already exists with different content: {path}")
            proposal = existing
        else:
            proposal = dict(proposal_base)
            proposal["created_at"] = utc_now()
            proposal["proposal_sha256"] = sha256_value(proposal)
            self._atomic_json(path, proposal)
        event = self.append_event(
            "rule_proposed",
            values["event_key"],
            {"rule_id": proposal["rule_id"], "revision": proposal["revision"], "proposal_sha256": proposal["proposal_sha256"], "status": status},
        )
        return {"status": status, "proposal": proposal, "event": event}

    def rule_path(self, rule_id: str, revision: str) -> Path:
        return self.rules_dir / safe_token(rule_id, "rule_id") / f"{safe_token(revision, 'revision')}.json"

    def load_rule(self, rule_id: str, revision: str) -> dict[str, Any]:
        path = self.rule_path(rule_id, revision)
        if not path.exists():
            raise LedgerError(f"rule revision is missing: {path}")
        try:
            rule = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"corrupt rule file: {path}") from exc
        observed = rule.get("proposal_sha256")
        unhashed = dict(rule)
        unhashed.pop("proposal_sha256", None)
        if observed != sha256_value(unhashed):
            raise LedgerError(f"rule hash mismatch: {path}")
        return rule

    def decide_rule(self, **values: Any) -> dict[str, Any]:
        rule = self.load_rule(values["rule_id"], values["revision"])
        decision = values["decision"]
        if decision not in {"approve", "reject"}:
            raise LedgerError(f"unsupported decision: {decision}")
        if values["proposal_sha256"].upper() != rule["proposal_sha256"]:
            raise LedgerError("proposal hash does not match the reviewed rule")
        expected_target = f"{rule['rule_id']}@{rule['revision']}"
        if values.get("approval_target") != expected_target:
            raise LedgerError(f"approval_target must be {expected_target}")
        if values.get("approval_kind") != "persistent_rule":
            raise LedgerError("approval_kind must be persistent_rule")
        payload = {
            "rule_id": rule["rule_id"],
            "revision": rule["revision"],
            "proposal_sha256": rule["proposal_sha256"],
            "decision": decision,
            "approval_kind": "persistent_rule",
            "approval_target": expected_target,
            "approval_text": nonempty(values.get("approval_text", ""), "approval_text"),
            "approval_source": nonempty(values.get("approval_source", ""), "approval_source"),
        }
        event = self.append_event("rule_decision", values["event_key"], payload)
        return {"status": "approved_pending_validation" if decision == "approve" else "rejected", "event": event}

    def _approved(self, rule: dict[str, Any]) -> dict[str, Any] | None:
        result = None
        for event in self.read_events():
            payload = event["payload"]
            if event["event_type"] == "rule_decision" and payload.get("rule_id") == rule["rule_id"] and payload.get("revision") == rule["revision"] and payload.get("proposal_sha256") == rule["proposal_sha256"]:
                result = event if payload.get("decision") == "approve" else None
        return result

    def record_release(self, **values: Any) -> dict[str, Any]:
        rule = self.load_rule(values["rule_id"], values["revision"])
        if values["proposal_sha256"].upper() != rule["proposal_sha256"]:
            raise LedgerError("proposal hash does not match release target")
        if self._approved(rule) is None:
            raise LedgerError("matching explicit approval is required before release")
        if values.get("meaning_review_result") != "pass":
            raise LedgerError("meaning review must pass before release")
        nonempty(values.get("meaning_review_note", ""), "meaning_review_note")
        nonempty(values.get("validation_report", ""), "validation_report")
        target_files = []
        for spec in values.get("target_files", []):
            path_text, expected = spec.rsplit("=", 1)
            path = Path(path_text)
            if not path.exists():
                raise LedgerError(f"release target file is missing: {path}")
            observed = sha256_file(path)
            if observed != expected.upper():
                raise LedgerError(f"release target hash mismatch: {path}")
            target_files.append({"path": normalized_path(str(path)), "sha256": observed})
        release_id = safe_token(values["release_id"], "release_id")
        release_base = {
            "schema_version": SCHEMA_VERSION,
            "release_id": release_id,
            "status": "validated",
            "rule_id": rule["rule_id"],
            "revision": rule["revision"],
            "proposal_sha256": rule["proposal_sha256"],
            "validation_report": values["validation_report"],
            "meaning_review_result": "pass",
            "meaning_review_note": values["meaning_review_note"],
            "target_files": target_files,
        }
        path = self.releases_dir / release_base["release_id"] / "release.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_base = dict(existing)
            existing_base.pop("release_sha256", None)
            existing_base.pop("created_at", None)
            if existing_base != release_base:
                raise LedgerError(f"release already exists with different content: {path}")
            release = self.load_release(release_base["release_id"])
        else:
            release = dict(release_base)
            release["created_at"] = utc_now()
            release["release_sha256"] = sha256_value(release)
            self._atomic_json(path, release)
        event = self.append_event(
            "rule_release",
            values["event_key"],
            {"release_id": release["release_id"], "release_sha256": release["release_sha256"], "rule_id": rule["rule_id"], "revision": rule["revision"], "proposal_sha256": rule["proposal_sha256"]},
        )
        return {"status": "validated", "release": release, "event": event}

    def load_release(self, release_id: str, validate_targets: bool = True) -> dict[str, Any]:
        path = self.releases_dir / safe_token(release_id, "release_id") / "release.json"
        if not path.exists():
            raise LedgerError(f"release is missing: {path}")
        try:
            release = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"corrupt release: {path}") from exc
        observed = release.get("release_sha256")
        unhashed = dict(release)
        unhashed.pop("release_sha256", None)
        if observed != sha256_value(unhashed) or release.get("status") != "validated":
            raise LedgerError(f"invalid release: {path}")
        if validate_targets:
            for item in release.get("target_files", []):
                path_item = Path(item["path"])
                if not path_item.exists() or sha256_file(path_item) != item["sha256"]:
                    raise LedgerError(f"release target changed after validation: {path_item}")
        return release

    def activate_rule(self, **values: Any) -> dict[str, Any]:
        rule = self.load_rule(values["rule_id"], values["revision"])
        release = self.load_release(values["release_id"])
        if values["proposal_sha256"].upper() != rule["proposal_sha256"]:
            raise LedgerError("proposal hash does not match activation target")
        if self._approved(rule) is None:
            raise LedgerError("matching approval is missing")
        for key in ("rule_id", "revision", "proposal_sha256"):
            if release[key] != rule[key]:
                raise LedgerError(f"release {key} does not match rule")
        active = self._derive_active_rules(self.read_events())
        for old in active:
            if old["rule_id"] == rule["rule_id"] and old["revision"] != rule["revision"]:
                old_key = f"{old['rule_id']}@{old['revision']}"
                if old_key not in rule.get("supersedes", []):
                    raise LedgerError(f"new revision must declare supersedes: {old_key}")
        payload = {"rule_id": rule["rule_id"], "revision": rule["revision"], "proposal_sha256": rule["proposal_sha256"], "release_id": release["release_id"], "release_sha256": release["release_sha256"]}
        event = self.append_event("rule_activation", values["event_key"], payload)
        index = self.regenerate_index()
        return {"status": "active", "event": event, "active_rule_set_id": index["active_rule_set_id"]}

    def withdraw_rule(self, **values: Any) -> dict[str, Any]:
        rule = self.load_rule(values["rule_id"], values["revision"])
        payload = {
            "rule_id": rule["rule_id"],
            "revision": rule["revision"],
            "proposal_sha256": rule["proposal_sha256"],
            "reason": nonempty(values.get("reason", ""), "reason"),
            "source_ref": nonempty(values.get("source_ref", ""), "source_ref"),
            "withdrawal_kind": values.get("withdrawal_kind", "user_retraction"),
        }
        if payload["withdrawal_kind"] not in {"user_retraction", "technical_rollback"}:
            raise LedgerError("withdrawal_kind must be user_retraction or technical_rollback")
        event = self.append_event("rule_withdrawal", values["event_key"], payload)
        index = self.regenerate_index()
        return {"status": "withdrawn", "event": event, "active_rule_set_id": index["active_rule_set_id"]}

    def _derive_active_rules(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        active: dict[tuple[str, str], dict[str, Any]] = {}
        approved: set[tuple[str, str]] = set()
        for event in events:
            payload = event["payload"]
            key = (payload.get("rule_id", ""), payload.get("revision", ""))
            if event["event_type"] == "rule_decision":
                if payload.get("decision") == "approve":
                    approved.add(key)
                else:
                    approved.discard(key)
                    active.pop(key, None)
            elif event["event_type"] == "rule_activation":
                rule = self.load_rule(*key)
                release = self.load_release(payload["release_id"], validate_targets=False)
                if key not in approved or release["proposal_sha256"] != rule["proposal_sha256"]:
                    raise LedgerError(f"activation lacks valid approval or release: {key}")
                active[key] = {
                    "rule_id": rule["rule_id"],
                    "revision": rule["revision"],
                    "proposal_sha256": rule["proposal_sha256"],
                    "rule_file_sha256": sha256_file(self.rule_path(*key)),
                    "release_id": release["release_id"],
                    "release_sha256": release["release_sha256"],
                    "rule_text": rule["rule_text"],
                    "scope": rule["scope"],
                    "not_applicable_to": rule["not_applicable_to"],
                    "acceptance_criteria": rule["acceptance_criteria"],
                }
                if rule.get("supersedes"):
                    active[key]["supersedes"] = rule["supersedes"]
            elif event["event_type"] == "rule_withdrawal":
                active.pop(key, None)
        rules = sorted(active.values(), key=lambda item: (item["rule_id"], item["revision"]))
        for item in rules:
            self.load_release(item["release_id"], validate_targets=True)
        return rules

    def regenerate_index(self) -> dict[str, Any]:
        events = self.read_events()
        rules = self._derive_active_rules(events)
        index = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "source_events_sha256": sha256_value(events),
            "rules": rules,
            "active_rule_set_id": sha256_value(rules),
        }
        self._atomic_json(self.index_path, index)
        return index

    def verify(self) -> dict[str, Any]:
        events = self.read_events()
        if not self.index_path.exists():
            raise LedgerError(f"active index is missing: {self.index_path}")
        try:
            index = json.loads(self.index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"corrupt active index: {self.index_path}") from exc
        if index.get("schema_version") != SCHEMA_VERSION or index.get("active_rule_set_id") != sha256_value(index.get("rules", [])):
            raise LedgerError("active index schema or set hash is invalid")
        derived = self._derive_active_rules(events)
        if canonical_bytes(index.get("rules", [])) != canonical_bytes(derived):
            raise LedgerError("active index does not match approval and activation events")
        for item in index.get("rules", []):
            rule = self.load_rule(item["rule_id"], item["revision"])
            if item.get("proposal_sha256") != rule["proposal_sha256"] or item.get("rule_file_sha256") != sha256_file(self.rule_path(rule["rule_id"], rule["revision"])):
                raise LedgerError(f"active index rule mismatch: {rule['rule_id']}@{rule['revision']}")
            self.load_release(item["release_id"])
        return {"status": "ok", "event_count": len(events), "active_count": len(index.get("rules", [])), "active_rule_set_id": index["active_rule_set_id"]}

    @staticmethod
    def _matches(values: Iterable[str], actual: str | None) -> bool:
        values = list(values)
        if "*" in values:
            return True
        return actual is not None and actual in values

    def resolve(self, **values: Any) -> dict[str, Any]:
        self.verify()
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        project = normalized_path(values["project_root"])
        def matches_item(item: dict[str, Any]) -> bool:
            scope = item["scope"]
            projects = [normalized_path(p) if p != "*" else "*" for p in scope["project_roots"]]
            if not self._matches(projects, project):
                return False
            if not self._matches(scope["entry_skills"], values["entry_skill"]):
                return False
            if not self._matches(scope["target_skills"], values["target_skill"]):
                return False
            if not self._matches(scope["stages"], values["stage"]):
                return False
            if not self._matches(scope.get("business_purposes", ["*"]), values.get("business_purpose")):
                return False
            if not self._matches(scope["article_types"], values.get("article_type")):
                return False
            if not self._matches(scope["grades"], values.get("grade")):
                return False
            return True

        selected = [item for item in index["rules"] if matches_item(item)]
        pending = []
        decisions: dict[tuple[str, str], dict[str, Any]] = {}
        withdrawn: dict[tuple[str, str], str] = {}
        for event in self.read_events():
            payload = event["payload"]
            key = (payload.get("rule_id", ""), payload.get("revision", ""))
            if event["event_type"] == "rule_decision":
                if payload.get("decision") == "approve":
                    decisions[key] = event
                    withdrawn.pop(key, None)
                else:
                    decisions.pop(key, None)
            elif event["event_type"] == "rule_withdrawal":
                withdrawn[key] = payload.get("withdrawal_kind", "user_retraction")
        active_keys = {(item["rule_id"], item["revision"]) for item in index["rules"]}
        for key, decision in decisions.items():
            if key in active_keys or withdrawn.get(key) == "user_retraction":
                continue
            rule = self.load_rule(*key)
            if not matches_item(rule):
                continue
            if any(f"{key[0]}@{key[1]}" in self.load_rule(*other).get("supersedes", []) for other in decisions if other != key):
                continue
            pending.append({"rule_id": key[0], "revision": key[1], "rule_text": rule["rule_text"], "scope": rule["scope"], "supersedes": rule.get("supersedes", []), "approval_source": decision["payload"]["approval_source"], "status": "confirmed_pending_implementation"})
        superseded = {target for item in selected + pending for target in item.get("supersedes", [])}
        selected = [item for item in selected if f"{item['rule_id']}@{item['revision']}" not in superseded]
        return {"schema_version": SCHEMA_VERSION, "active_rule_set_id": sha256_value(selected), "source_active_rule_set_id": index["active_rule_set_id"], "rules": selected, "pending_wishes": pending}

    def candidate_summary(self) -> dict[str, Any]:
        counts: dict[str, dict[str, Any]] = {}
        events = self.read_events()
        results = {e["payload"]["request_event_id"]: e["payload"] for e in events if e["event_type"] == "correction_result"}
        for event in events:
            if event["event_type"] == "correction_request":
                request = event["payload"]
                key = request.get("candidate_key")
                if key:
                    item = counts.setdefault(key, {"candidate_key": key, "occurrences": 0, "eligible_articles": set(), "explicit_standing_instruction": False, "explicit_skill_change_request": False})
                    item["occurrences"] += 1
                    result = results.get(event["event_id"], {})
                    if result.get("classification") in {"preference_candidate", "existing_rule_execution_gap", "skill_gap"} and result.get("improvement_decision") in {"candidate", "explicit_skill_change_request"}:
                        item["eligible_articles"].add(request["article_id"])
                    item["explicit_standing_instruction"] |= request.get("intent_scope") == "standing_explicit"
                    item["explicit_skill_change_request"] |= result.get("improvement_decision") == "explicit_skill_change_request"
        output = []
        for _, item in sorted(counts.items()):
            eligible_article_count = len(item.pop("eligible_articles"))
            item["eligible_article_count"] = eligible_article_count
            item["review_ready"] = eligible_article_count >= 2 or item["explicit_standing_instruction"] or item["explicit_skill_change_request"]
            item["auto_approved"] = False
            output.append(item)
        return {"status": "observed_only", "candidates": output}

    def record_skill_change(self, **values: Any) -> dict[str, Any]:
        for key in ("source_ref", "request_text", "problem", "cause", "change_summary", "decision_basis"):
            nonempty(values.get(key, ""), key)
        if values["decision_basis"] not in {"explicit_skill_change_request", "standing_instruction", "recurring_articles", "diagnosed_structural_gap"}:
            raise LedgerError("unsupported decision_basis")
        status = values.get("status", "implemented")
        if status not in {"implemented", "verified", "blocked"}:
            raise LedgerError("unsupported skill change status")
        if status == "verified":
            nonempty(values.get("validation_report", ""), "validation_report")
        source_ids = list(values.get("source_event_ids", []))
        for event_id in source_ids:
            self.find_event(event_id, "correction_request")
        files = []
        for filename in values.get("changed_files", []):
            path = Path(filename)
            if not path.is_file():
                raise LedgerError(f"skill change file is missing: {path}")
            files.append({"path": normalized_path(str(path)), "after_sha256": sha256_file(path)})
        if status != "blocked" and not files:
            raise LedgerError("implemented skill change requires changed_files")
        payload = {
            "source_ref": values["source_ref"],
            "request_text": values["request_text"],
            "source_event_ids": source_ids,
            "problem": values["problem"],
            "cause": values["cause"],
            "change_summary": values["change_summary"],
            "decision_basis": values["decision_basis"],
            "status": status,
            "business_purposes": list(values.get("business_purposes", [])) or ["*"],
            "article_types": list(values.get("article_types", [])) or ["*"],
            "target_skills": list(values.get("target_skills", [])) or ["*"],
            "changed_files": files,
            "validation_report": values.get("validation_report", ""),
            "effect_status": "not_observed_yet",
        }
        event = self.append_event("skill_change", values["event_key"], payload)
        return {"status": status, "change_event_id": event["event_id"], "changed_file_count": len(files), "effect_status": "not_observed_yet"}

    def record_impact(self, **values: Any) -> dict[str, Any]:
        change = self.find_event(values["change_event_id"], "skill_change")
        business_purposes = change["payload"].get("business_purposes", ["*"])
        if "*" not in business_purposes and values["business_purpose"] not in business_purposes:
            raise LedgerError("the article business purpose is outside the skill change scope")
        article_types = change["payload"].get("article_types", ["*"])
        if "*" not in article_types and values["article_type"] not in article_types:
            raise LedgerError("the article is outside the skill change scope")
        first_draft = values["first_draft"]
        user_assessment = values.get("user_assessment", "unevaluated")
        if first_draft not in {"pass", "fail", "unreviewed"} or user_assessment not in {"accepted", "rework", "unevaluated"}:
            raise LedgerError("unsupported impact assessment")
        for key in ("article_id", "business_purpose", "article_type", "evidence_ref", "verification"):
            nonempty(values.get(key, ""), key)
        if user_assessment != "unevaluated":
            nonempty(values.get("user_assessment_source", ""), "user_assessment_source")
        payload = {
            "change_event_id": change["event_id"], "article_id": values["article_id"],
            "business_purpose": values["business_purpose"],
            "article_type": values["article_type"], "first_draft": first_draft,
            "user_assessment": user_assessment, "user_assessment_source": values.get("user_assessment_source", ""),
            "evidence_ref": values["evidence_ref"], "verification": values["verification"],
        }
        event = self.append_event("skill_impact", values["event_key"], payload)
        return {"status": "recorded", "impact_event_id": event["event_id"], "change_event_id": change["event_id"]}

    def skill_change_summary(self) -> dict[str, Any]:
        changes = []
        impacts: dict[tuple[str, str], dict[str, Any]] = {}
        for event in self.read_events():
            if event["event_type"] == "skill_impact":
                payload = event["payload"]
                impacts[(payload["change_event_id"], payload["article_id"])] = payload
            elif event["event_type"] == "skill_change":
                changes.append(event)
        output = []
        for event in changes:
            related = [value for (change_id, _), value in impacts.items() if change_id == event["event_id"]]
            output.append({
                "change_event_id": event["event_id"], "status": event["payload"]["status"],
                "problem": event["payload"]["problem"], "decision_basis": event["payload"]["decision_basis"],
                "eligible_article_count": len(related),
                "first_draft_pass_count": sum(item["first_draft"] == "pass" for item in related),
                "first_draft_fail_count": sum(item["first_draft"] == "fail" for item in related),
                "unreviewed_count": sum(item["first_draft"] == "unreviewed" for item in related),
                "user_accepted_count": sum(item["user_assessment"] == "accepted" for item in related),
                "effect_status": "observed" if related else "not_observed_yet",
            })
        def cell(value: Any) -> str:
            return str(value).replace("|", "\\|").replace("\n", " ")
        lines = ["# スキル改善の一覧", "", "| 問題 | 実装状態 | 次の記事で確認した件数 | 初稿で確認できた件数 | あなたの了承 |", "|---|---|---:|---:|---:|"]
        if not output:
            lines.append("| 記録なし | — | 0 | 0 | 0 |")
        for item in output:
            lines.append("| " + " | ".join(cell(value) for value in (item["problem"], item["status"], item["eligible_article_count"], item["first_draft_pass_count"], item["user_accepted_count"])) + " |")
        lines.extend(["", "未確認の記事は成功に含めません。各改善案件の原文・原因・検証・版は構造化記録で確認できます。"])
        return {"status": "ok", "skill_changes": output, "日本語一覧": "\n".join(lines)}


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True)


def add_rule_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rule-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--proposal-sha256", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("init")
    add_common(command)

    command = sub.add_parser("verify-store")
    add_common(command)

    command = sub.add_parser("record-request")
    add_common(command)
    for name in ("project-root", "article-id", "article-path", "entry-skill", "target-skill", "stage", "run-id", "request-text", "source-ref", "event-key"):
        command.add_argument(f"--{name}", required=True)
    command.add_argument("--parent-run-id")
    command.add_argument("--observed-before", default="")
    command.add_argument("--interpretation", default="")
    command.add_argument("--candidate-key", default="")
    command.add_argument("--intent-scope", choices=sorted(INTENT_SCOPES), default="unclear")
    command.add_argument("--uttered-at", default="")

    command = sub.add_parser("record-result")
    add_common(command)
    for name in ("request-event-id", "status", "result-text", "event-key"):
        command.add_argument(f"--{name}", required=True)
    command.add_argument("--observed-after", default="")
    command.add_argument("--verification", default="")
    command.add_argument("--classification", choices=sorted(CLASSIFICATIONS), default="unclear")
    command.add_argument("--changed-file", action="append", default=[])
    command.add_argument("--improvement-decision", choices=sorted(IMPROVEMENT_DECISIONS), default="unassessed")
    command.add_argument("--improvement-reason", default="")

    command = sub.add_parser("propose-rule")
    add_common(command)
    command.add_argument("--rule-id", required=True)
    command.add_argument("--revision", required=True)
    command.add_argument("--rule-text", required=True)
    command.add_argument("--status", choices=["proposed", "needs_clarification"], default="proposed")
    command.add_argument("--project-root", action="append", required=True)
    command.add_argument("--entry-skill", action="append", required=True)
    command.add_argument("--target-skill", action="append", required=True)
    command.add_argument("--stage", action="append", required=True)
    command.add_argument("--business-purpose", action="append", choices=["conversion", "traffic", "*"], required=True)
    command.add_argument("--article-type", action="append", default=[])
    command.add_argument("--grade", action="append", default=[])
    command.add_argument("--not-applicable-to", action="append", default=[])
    command.add_argument("--source-event-id", action="append", default=[])
    command.add_argument("--acceptance-criterion", action="append", default=[])
    command.add_argument("--supersedes", action="append", default=[])
    command.add_argument("--event-key", required=True)

    command = sub.add_parser("decide-rule")
    add_common(command)
    add_rule_identity(command)
    command.add_argument("--decision", choices=["approve", "reject"], required=True)
    command.add_argument("--approval-kind", required=True)
    command.add_argument("--approval-target", required=True)
    command.add_argument("--approval-text", required=True)
    command.add_argument("--approval-source", required=True)
    command.add_argument("--event-key", required=True)

    command = sub.add_parser("record-release")
    add_common(command)
    add_rule_identity(command)
    command.add_argument("--release-id", required=True)
    command.add_argument("--validation-report", required=True)
    command.add_argument("--meaning-review-result", choices=["pass", "fail"], required=True)
    command.add_argument("--meaning-review-note", required=True)
    command.add_argument("--target-file", action="append", default=[])
    command.add_argument("--event-key", required=True)

    command = sub.add_parser("activate-rule")
    add_common(command)
    add_rule_identity(command)
    command.add_argument("--release-id", required=True)
    command.add_argument("--event-key", required=True)

    command = sub.add_parser("withdraw-rule")
    add_common(command)
    command.add_argument("--rule-id", required=True)
    command.add_argument("--revision", required=True)
    command.add_argument("--reason", required=True)
    command.add_argument("--source-ref", required=True)
    command.add_argument("--withdrawal-kind", choices=["user_retraction", "technical_rollback"], default="user_retraction")
    command.add_argument("--event-key", required=True)

    command = sub.add_parser("resolve-rules")
    add_common(command)
    for name in ("project-root", "entry-skill", "target-skill", "stage"):
        command.add_argument(f"--{name}", required=True)
    command.add_argument("--business-purpose", choices=["conversion", "traffic"])
    command.add_argument("--article-type")
    command.add_argument("--grade")

    command = sub.add_parser("list-candidates")
    add_common(command)

    command = sub.add_parser("record-skill-change")
    add_common(command)
    for name in ("source-ref", "request-text", "problem", "cause", "change-summary", "decision-basis", "event-key"):
        command.add_argument(f"--{name}", required=True)
    command.add_argument("--source-event-id", action="append", default=[])
    command.add_argument("--changed-file", action="append", default=[])
    command.add_argument("--business-purpose", action="append", choices=["conversion", "traffic", "*"], default=[])
    command.add_argument("--article-type", action="append", default=[])
    command.add_argument("--target-skill", action="append", default=[])
    command.add_argument("--status", choices=["implemented", "verified", "blocked"], default="implemented")
    command.add_argument("--validation-report", default="")

    command = sub.add_parser("record-impact")
    add_common(command)
    for name in ("change-event-id", "article-id", "article-type", "first-draft", "evidence-ref", "verification", "event-key"):
        command.add_argument(f"--{name}", required=True)
    command.add_argument("--business-purpose", choices=["conversion", "traffic"], required=True)
    command.add_argument("--user-assessment", choices=["accepted", "rework", "unevaluated"], default="unevaluated")
    command.add_argument("--user-assessment-source", default="")

    command = sub.add_parser("list-skill-changes")
    add_common(command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = FeedbackStore(args.root)
    data = vars(args)
    try:
        if args.command == "init":
            result = store.init()
        elif args.command == "verify-store":
            result = store.verify()
        elif args.command == "record-request":
            result = store.record_request(**data)
        elif args.command == "record-result":
            data["changed_files"] = data.pop("changed_file")
            result = store.record_result(**data)
        elif args.command == "propose-rule":
            data["scope"] = {
                "project_roots": data.pop("project_root"),
                "entry_skills": data.pop("entry_skill"),
                "target_skills": data.pop("target_skill"),
                "stages": data.pop("stage"),
                "business_purposes": data.pop("business_purpose"),
                "article_types": data.pop("article_type") or ["*"],
                "grades": data.pop("grade") or ["*"],
            }
            data["source_event_ids"] = data.pop("source_event_id")
            data["acceptance_criteria"] = data.pop("acceptance_criterion")
            result = store.propose_rule(**data)
        elif args.command == "decide-rule":
            result = store.decide_rule(**data)
        elif args.command == "record-release":
            data["target_files"] = data.pop("target_file")
            result = store.record_release(**data)
        elif args.command == "activate-rule":
            result = store.activate_rule(**data)
        elif args.command == "withdraw-rule":
            result = store.withdraw_rule(**data)
        elif args.command == "resolve-rules":
            result = store.resolve(**data)
        elif args.command == "list-candidates":
            result = store.candidate_summary()
        elif args.command == "record-skill-change":
            data["source_event_ids"] = data.pop("source_event_id")
            data["changed_files"] = data.pop("changed_file")
            data["business_purposes"] = data.pop("business_purpose")
            data["article_types"] = data.pop("article_type")
            data["target_skills"] = data.pop("target_skill")
            result = store.record_skill_change(**data)
        elif args.command == "record-impact":
            result = store.record_impact(**data)
        elif args.command == "list-skill-changes":
            result = store.skill_change_summary()
        else:
            raise LedgerError(f"unsupported command: {args.command}")
    except (LedgerError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
