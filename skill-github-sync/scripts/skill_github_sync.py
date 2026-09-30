#!/usr/bin/env python3
"""Completed Codex skill edits -> a configured Git repository. Python stdlib only."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import time
import uuid

DEFAULT_STATE = Path(r"C:\AIフォルダ\.skill-github-sync-state")
TERMINAL = {"SYNCED", "NO_CHANGE", "CANCELLED", "LOCAL_ONLY"}
SENDABLE = {"READY", "COMMITTED", "RETRY_PENDING"}
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".cache", ".venv", "logs", "tmp", ".tmp"}
EXCLUDED_ROOTS = {".system", "codex-primary-runtime"}
TOKEN = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{40,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")


class SyncError(Exception):
    pass


class Retryable(SyncError):
    pass


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(path):
    return os.path.normcase(str(Path(path).resolve(strict=True)))


def safe_rel(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or any(x in {"", ".", ".."} for x in value.split("/")) or any(x in value for x in ("\\", ":", "\n", "\r", "\0")):
        raise SyncError("保存先に不正な相対パスがあります")
    return p.as_posix()


def within(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def read_json(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else default


def file_excluded(rel):
    p = PurePosixPath(rel)
    name = p.name.lower()
    return any(x.lower() in EXCLUDED_DIRS for x in p.parts) or name.endswith((".pyc", ".pyo", ".log", ".tmp", ".swp")) or name in {"auth.json", "credentials.json", ".env", ".env.local", ".env.production"} or name.endswith((".pem", ".key", ".p12", ".pfx"))


def local_manifest(source, *, deadline=None, contents=False, check_tokens=False):
    root = Path(source).resolve(strict=True)
    manifest, blobs = {}, {}

    def walk(folder, ancestors):
        real = folder.resolve(strict=True)
        if not within(real, root) or canonical(real) in ancestors:
            raise SyncError("登録範囲外または循環したリンクがあります")
        next_ancestors = ancestors | {canonical(real)}
        for entry in sorted(folder.iterdir(), key=lambda p: p.name):
            if deadline and time.monotonic() > deadline:
                raise SyncError("スキルの比較基準の取得が制限時間を超えました")
            rel = entry.relative_to(root).as_posix()
            if file_excluded(rel):
                continue
            target = entry.resolve(strict=True)
            if not within(target, root):
                raise SyncError("登録範囲外を指す内部リンクがあります: " + rel)
            if entry.is_dir():
                walk(entry, next_ancestors)
            elif entry.is_file():
                safe_rel(rel)
                data = entry.read_bytes()
                if check_tokens and TOKEN.search(data):
                    raise SyncError("認証情報の可能性があるため送信を停止しました: " + rel)
                mode = "100755" if os.name != "nt" and entry.stat().st_mode & 0o111 else "100644"
                manifest[rel] = {"sha256": digest(data), "size": len(data), "mode": mode}
                if contents:
                    blobs[rel] = data
            else:
                raise SyncError("読み取れないファイルがあります: " + rel)

    walk(root, set())
    return (manifest, blobs) if contents else manifest


def same(a, b):
    # Windows cannot infer executable bits; byte equality remains authoritative.
    return {k: (v["sha256"], v["size"]) for k, v in a.items()} == {k: (v["sha256"], v["size"]) for k, v in b.items()}


def diff(before, after):
    return {p: after.get(p) for p in sorted(set(before) | set(after)) if (before.get(p) or {}).get("sha256") != (after.get(p) or {}).get("sha256")}


def discover(roots):
    found, seen = [], set()
    for raw in roots:
        root = Path(raw)
        if not root.exists():
            continue
        def visit(folder, prefix, depth):
            if folder.name in EXCLUDED_ROOTS or depth > 3:
                return
            real = canonical(folder)
            if (folder / "SKILL.md").is_file():
                if real not in seen:
                    seen.add(real)
                    found.append({"source": str(folder.resolve()), "dest": safe_rel(prefix), "entry": str(folder)})
                return
            for child in sorted(folder.iterdir(), key=lambda p: p.name):
                if child.is_dir() and child.name not in EXCLUDED_DIRS:
                    visit(child, prefix + "/" + child.name if prefix else child.name, depth + 1)
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if child.is_dir():
                visit(child, child.name, 0)
    return found


def process_identity(pid):
    if os.name == "nt":
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        k.OpenProcess.restype = ctypes.c_void_p
        handle = k.OpenProcess(0x1000, False, pid)
        if not handle:
            return None if ctypes.get_last_error() == 87 else "unknown"
        try:
            code = ctypes.c_ulong()
            if not k.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
                return "unknown"
            if code.value != 259:
                return None
            times = [ctypes.c_ulonglong() for _ in range(4)]
            if k.GetProcessTimes(ctypes.c_void_p(handle), *(ctypes.byref(x) for x in times)):
                return str(times[0].value)
            return "unknown"
        finally:
            k.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
        stat = Path(f"/proc/{pid}/stat")
        return stat.read_text().split()[21] if stat.exists() else "unknown"
    except ProcessLookupError:
        return None
    except PermissionError:
        return "unknown"


@contextlib.contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = {"pid": os.getpid(), "identity": process_identity(os.getpid()), "token": uuid.uuid4().hex}
    handle = path.open("a+b")
    handle.seek(0, 2)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        handle.close()
        raise Retryable("別の同期処理が動いています") from error
    try:
        handle.seek(1)
        handle.truncate()
        handle.write(json.dumps(owner).encode())
        handle.flush()
        yield
    finally:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class Engine:
    def __init__(self, state=DEFAULT_STATE):
        self.root = Path(state).resolve()
        self.config_path = self.root / "config.json"
        self.config = read_json(self.config_path, {})

    def require_config(self):
        if not self.config:
            raise SyncError("同期設定がありません")

    def git(self, cwd, *args, input=None, check=True):
        env = os.environ.copy()
        env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([self.config.get("git", "git"), "-C", str(cwd), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **options)
        try:
            stdout, stderr = process.communicate(input=input, timeout=self.config.get("git_timeout", 45))
        except subprocess.TimeoutExpired as e:
            if os.name == "nt":
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.stdout.close()
                process.stderr.close()
            raise Retryable("Git操作がタイムアウトしました。反映は未確認です") from e
        r = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
        if check and r.returncode:
            msg = r.stderr.decode("utf-8", "replace")
            if re.search(r"authentication|permission|denied|protected|GH006|GH013|repository not found", msg, re.I):
                raise SyncError("GitHubの認証・権限・保護条件を確認してください")
            if re.search(r"non-fast-forward|fetch first|rejected", msg, re.I):
                raise Retryable("送信前にリモートが更新されました")
            raise Retryable("Git操作が失敗しました。通信とリポジトリの状態を確認してください")
        return r

    def reference(self):
        self.require_config()
        ref = self.root / "reference"
        if not (ref / ".git").exists():
            ref.mkdir(parents=True, exist_ok=True)
            self.git(ref, "init", "--quiet")
            self.git(ref, "remote", "add", "origin", self.config["remote"])
        cache = self.config.get("cache_repo")
        if cache and self.git(ref, "rev-parse", "--verify", "refs/skill-cache/" + self.config["branch"], check=False).returncode:
            self.git(ref, "fetch", "--quiet", cache, "refs/heads/" + self.config["branch"] + ":refs/skill-cache/" + self.config["branch"])
        self.git(ref, "fetch", "--quiet", "origin", "+refs/heads/" + self.config["branch"] + ":refs/remotes/origin/" + self.config["branch"])
        head = self.git(ref, "rev-parse", "refs/remotes/origin/" + self.config["branch"]).stdout.decode().strip()
        return ref, head

    def tree(self, repo, revision, prefix=""):
        args = ["ls-tree", "-rz", "--full-tree", revision]
        if prefix:
            args += ["--", safe_rel(prefix) + "/"]
        records = []
        for item in self.git(repo, *args).stdout.split(b"\0"):
            if not item:
                continue
            info, rawpath = item.split(b"\t", 1)
            mode, kind, oid = info.decode().split()
            path = rawpath.decode("utf-8")
            if prefix:
                path = path[len(prefix) + 1:]
            safe_rel(path)
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise SyncError("保存先に通常ファイル以外が含まれています")
            records.append((path, mode, oid))
        data = self.git(repo, "cat-file", "--batch", input="".join(x[2] + "\n" for x in records).encode()).stdout if records else b""
        result, offset = {}, 0
        for path, mode, oid in records:
            end = data.index(b"\n", offset)
            header = data[offset:end].decode().split()
            if len(header) != 3 or header[1] != "blob":
                raise SyncError("Git blobを取得できませんでした")
            size = int(header[2])
            blob = data[end + 1:end + 1 + size]
            result[path] = {"sha256": digest(blob), "size": size, "mode": mode}
            offset = end + size + 2
        return result

    def initialize(self, remote, branch, roots, git="git", author=None, cache_repo=None):
        if self.config_path.exists() and self.config.get("mappings"):
            raise SyncError("設定は既にあります。既存状態を上書きしません")
        if self.config and self.config.get("remote") != remote:
            raise SyncError("初期登録途中の保存先を変更できません")
        if re.search(r"https?://[^/]*@", remote):
            raise SyncError("認証情報を含む保存先URLは使えません")
        self.config = {"version": 1, "initialized": False, "remote": remote, "branch": branch, "roots": roots, "git": git, "cache_repo": cache_repo, "mappings": {}, "author": author or {"name": "Codex skill sync", "email": "skill-sync@localhost"}}
        atomic_json(self.config_path, self.config)
        ref, head = self.reference()
        candidates = discover(roots)
        result = []
        for candidate in candidates:
            source, dest = candidate["source"], candidate["dest"]
            if dest in self.config["mappings"]:
                raise SyncError("異なる実体が同じ保存先へ割り当たっています: " + dest)
            local = local_manifest(source)
            remote_tree = self.tree(ref, head, dest)
            self.config["mappings"][dest] = {"source": source, "dest": dest, "local": local, "remote": remote_tree, "remote_head": head}
            changes = diff(remote_tree, local)
            result.append({"source": source, "dest": dest, "add_or_update": sum(v is not None for v in changes.values()), "remote_only_preserved": sum(v is None for v in changes.values())})
        self.config["initialized"] = True
        atomic_json(self.config_path, self.config)
        return {"head": head, "skills": len(result), "inventory": result}

    def job_path(self, jobid):
        if not re.fullmatch(r"[a-f0-9]{32}", jobid):
            raise SyncError("処理IDが不正です")
        return self.root / "jobs" / (jobid + ".json")

    def jobs(self):
        return sorted((read_json(p) for p in (self.root / "jobs").glob("*.json")), key=lambda j: (j["created_ns"], j["id"]))

    def save_job(self, job):
        job["updated_at"] = now()
        atomic_json(self.job_path(job["id"]), job)

    def mapping(self, source, dest=None):
        real = canonical(source)
        for item in self.config["mappings"].values():
            if canonical(item["source"]) == real:
                if dest and item["dest"] != safe_rel(dest):
                    raise SyncError("登録済みの実体の保存先を変更できません")
                return item
        if not (Path(source) / "SKILL.md").is_file() and not dest:
            raise SyncError("新しいスキルの保存先を --dest で指定してください")
        target = safe_rel(dest or Path(source).name)
        if any(target == k or target.startswith(k + "/") or k.startswith(target + "/") for k in self.config["mappings"]):
            raise SyncError("保存先が別の登録と衝突しています")
        item = {"source": str(Path(source).resolve()), "dest": target, "local": {}, "remote": {}, "remote_head": None}
        self.config["mappings"][target] = item
        return item

    def turn_path(self, session, turn):
        return self.root / "turns" / (digest((session + "\0" + turn).encode()) + ".json")

    def begin(self, source, *, dest=None, session="manual", turn="manual", local_only=False, include_existing=False, bootstrap=False, recover_turn=False):
        self.require_config()
        if not self.config.get("initialized", True):
            raise SyncError("初期登録が未完了です")
        Path(source).mkdir(parents=True, exist_ok=True)
        with lock(self.root / "locks" / "state.lock"):
            self.config = read_json(self.config_path)
            mapping = self.mapping(source, dest)
            current = local_manifest(source)
            td = read_json(self.turn_path(session, turn), {})
            before = current
            if recover_turn:
                real = canonical(source)
                if not td or td.get("issues"):
                    raise SyncError("開始時の比較基準が不足しているため登録漏れを補完できません")
                if real in td.get("baseline", {}):
                    before = td["baseline"][real]
                elif any(within(source, r) for r in self.config["roots"]):
                    before = {}
                else:
                    raise SyncError("登録範囲外の変更に開始時の基準がありません")
            prior = [j for j in self.jobs() if j["dest"] == mapping["dest"]]
            for job in prior:
                if job["state"] == "EDITING":
                    if job["session"] == session and job["turn"] == turn:
                        return job
                    raise SyncError("同じスキルが別の処理で編集中です。再開または取消しを確認してください")
            known_local = mapping["local"]
            for previous in prior:
                if "desired" in previous and previous["state"] not in {"CANCELLED", "LOCAL_ONLY"} and not previous.get("requires_rebase"):
                    known_local = previous["desired"]
            if not same(before, known_local) and not include_existing and not bootstrap:
                raise SyncError("未登録または送信対象外の既存変更があります。今回の保存範囲を確定してください")
            expected = dict(mapping["remote"])
            for previous in prior:
                if previous["state"] in SENDABLE | {"NEEDS_ACTION"} and "changes" in previous:
                    for p, value in previous["changes"].items():
                        if value is None:
                            expected.pop(p, None)
                        else:
                            expected[p] = value
            denied = local_only or td.get("send") == "deny"
            job = {"id": uuid.uuid4().hex, "created_ns": time.time_ns(), "created_at": now(), "state": "EDITING", "source": mapping["source"], "dest": mapping["dest"], "session": session, "turn": turn, "before": expected if bootstrap or include_existing else before, "expected_remote": expected, "local_only": denied, "bootstrap": bootstrap, "attempt_commits": [], "reported": False}
            self.save_job(job)
            atomic_json(self.config_path, self.config)
            return job

    def ready(self, jobid, validation, deletions=()):
        if not validation.strip():
            raise SyncError("必要な検証の結果を指定してください")
        with lock(self.root / "locks" / "state.lock"):
            self.config = read_json(self.config_path)
            job = read_json(self.job_path(jobid))
            if not job or job["state"] != "EDITING":
                raise SyncError("編集中の処理ではありません")
            first, blobs = local_manifest(job["source"], contents=True, check_tokens=not job["local_only"])
            if not same(first, local_manifest(job["source"])):
                raise SyncError("保存中にスキルが変化しました")
            changes = diff(job["before"], first)
            requested = {safe_rel(p) for p in deletions}
            removed = {p for p, value in changes.items() if value is None}
            if job["bootstrap"]:
                for p in removed:
                    del changes[p]
            elif removed != requested:
                raise SyncError("意図した削除一覧と検出した削除が一致しません")
            # Preserve already-recorded executable bits on Windows.
            for p, value in changes.items():
                if value is not None and p in job["expected_remote"]:
                    value["mode"] = job["expected_remote"][p]["mode"]
            snap = self.root / "snapshots" / jobid
            # EDITING snapshots are not publishable: an interrupted ready can resume.
            # Only paths in the eventual immutable manifest may be staged.
            for rel, data in blobs.items():
                out = snap / "files" / safe_rel(rel)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            if not same(first, local_manifest(job["source"])):
                raise SyncError("完成版の保存後にスキルが変化しました。編集中として保全します")
            job.update({"desired": first, "changes": changes, "validation": validation, "state": "LOCAL_ONLY" if job["local_only"] else "READY"})
            self.save_job(job)
            if not job["local_only"]:
                self.config["mappings"][job["dest"]]["local"] = first
                atomic_json(self.config_path, self.config)
            return job

    def check_changes(self, job, remote):
        for path, desired in job["changes"].items():
            actual = remote.get(path)
            expected = job["expected_remote"].get(path)
            if actual == desired or actual == expected:
                continue
            raise SyncError("GitHub側の同じパスに別の更新があります: " + path)

    def verify_desired(self, job, remote):
        return all(remote.get(path) == value for path, value in job["changes"].items())

    def sync_job(self, job):
        for attempt in range(2):
            try:
                ref, head = self.reference()
                remote = self.tree(ref, head, job["dest"])
                landed = next((c for c in job["attempt_commits"] if self.git(ref, "merge-base", "--is-ancestor", c, head, check=False).returncode == 0), None)
                if landed and not self.verify_desired(job, remote):
                    raise SyncError("送信済みですが、GitHub側で対象内容が再更新されています")
                if self.verify_desired(job, remote):
                    job.update({"state": "SYNCED" if landed else "NO_CHANGE", "commit": landed, "remote_head": head, "confirmed_at": now()})
                    break
                self.check_changes(job, remote)
                work = self.root / "work" / (job["id"] + "-" + uuid.uuid4().hex[:8])
                work.mkdir(parents=True)
                self.git(work, "init", "--quiet")
                self.git(work, "remote", "add", "origin", self.config["remote"])
                self.git(work, "fetch", "--quiet", str(ref), head)
                self.git(work, "checkout", "--quiet", "-b", "sync", "FETCH_HEAD")
                attrs = work / ".git" / "info" / "attributes"
                attrs.parent.mkdir(parents=True, exist_ok=True)
                paths = [job["dest"] + "/" + safe_rel(p) for p in job["changes"]]
                attrs.write_text("".join(json.dumps(p, ensure_ascii=False) + " -text -filter -working-tree-encoding -ident\n" for p in paths), encoding="utf-8")
                for rel, value in job["changes"].items():
                    out = work / job["dest"] / safe_rel(rel)
                    if not within(out, work):
                        raise SyncError("作業コピーの範囲外です")
                    if value is None:
                        if out.exists():
                            out.unlink()
                    else:
                        data = (self.root / "snapshots" / job["id"] / "files" / rel).read_bytes()
                        if digest(data) != value["sha256"]:
                            raise SyncError("完成版の保存内容が一致しません")
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(data)
                        if digest(out.read_bytes()) != value["sha256"]:
                            raise SyncError("コピーした内容が一致しません")
                for path in paths:
                    relative = path[len(job["dest"]) + 1:]
                    if remote.get(relative) != job["changes"][relative]:
                        self.git(work, "add", "--all", "--force", "--", path)
                for rel, value in job["changes"].items():
                    if value is not None:
                        self.git(work, "update-index", "--chmod=" + ("+x" if value["mode"] == "100755" else "-x"), "--", job["dest"] + "/" + rel)
                staged = self.git(work, "diff", "--cached", "--name-only", "-z").stdout
                actual_paths = {p.decode("utf-8") for p in staged.split(b"\0") if p}
                wanted_paths = {job["dest"] + "/" + p for p, value in job["changes"].items() if remote.get(p) != value}
                if actual_paths != wanted_paths:
                    raise SyncError("コミット対象が予定した変更と一致しません")
                tree_oid = self.git(work, "write-tree").stdout.decode().strip()
                if not self.verify_desired(job, self.tree(work, tree_oid, job["dest"])):
                    raise SyncError("ステージしたGit blobが完成版と一致しません")
                author = self.config["author"]
                self.git(work, "-c", "user.name=" + author["name"], "-c", "user.email=" + author["email"], "commit", "--quiet", "-m", "Sync skill " + job["dest"] + " (" + job["id"][:12] + ")")
                commit = self.git(work, "rev-parse", "HEAD").stdout.decode().strip()
                # Keep the object in reference before push so uncertain outcomes can be verified.
                self.git(ref, "fetch", "--quiet", str(work), "HEAD:refs/skill-sync/" + job["id"] + "/" + commit)
                job["attempt_commits"].append(commit)
                job.update({"state": "COMMITTED", "work": str(work)})
                self.save_job(job)
                self.git(work, "push", "--quiet", "origin", "HEAD:refs/heads/" + self.config["branch"])
                ref, head = self.reference()
                remote = self.tree(ref, head, job["dest"])
                if self.git(ref, "merge-base", "--is-ancestor", commit, head, check=False).returncode or not self.verify_desired(job, remote):
                    raise SyncError("送信後の履歴と対象内容を確認できませんでした")
                job.update({"state": "SYNCED", "commit": commit, "remote_head": head, "confirmed_at": now()})
                break
            except Retryable as error:
                job.update({"state": "RETRY_PENDING", "reason": str(error)})
                self.save_job(job)
                if attempt == 1:
                    return job
            except SyncError as error:
                job.update({"state": "NEEDS_ACTION", "reason": str(error)})
                self.save_job(job)
                return job
        with lock(self.root / "locks" / "state.lock"):
            self.config = read_json(self.config_path)
            self.config["mappings"][job["dest"]].update({"remote": remote, "remote_head": head})
            atomic_json(self.config_path, self.config)
            job.pop("reason", None)
            self.save_job(job)
        return job

    def sync(self, session, turn, *, send_allowed, resume_action=False):
        self.require_config()
        td = read_json(self.turn_path(session, turn), {})
        if not send_allowed or td.get("send") == "deny":
            return {"sent": False, "reason": "このターンは送信対象外です", "jobs": []}
        with lock(self.root / "locks" / "sync.lock"):
            blocked, results = set(), []
            self.config = read_json(self.config_path)
            for job in self.jobs():
                if resume_action and job["state"] == "NEEDS_ACTION" and not job.get("requires_rebase"):
                    job["state"] = "READY"
                if job["state"] in TERMINAL:
                    continue
                if job["dest"] in blocked or job["state"] not in SENDABLE:
                    blocked.add(job["dest"])
                    continue
                result = self.sync_job(job)
                results.append(self.public_job(result))
                if result["state"] not in {"SYNCED", "NO_CHANGE"}:
                    blocked.add(job["dest"])
            return {"sent": True, "jobs": results}

    def cancel(self, jobid):
        with lock(self.root / "locks" / "state.lock"):
            self.config = read_json(self.config_path)
            job = read_json(self.job_path(jobid))
            if not job or job["state"] in {"SYNCED", "NO_CHANGE"}:
                raise SyncError("送信済みの内容は取消しで消せません")
            job["state"] = "CANCELLED"
            self.save_job(job)
            for later in self.jobs():
                if later["dest"] == job["dest"] and later["created_ns"] > job["created_ns"] and later["state"] not in TERMINAL:
                    later.update({"state": "NEEDS_ACTION", "reason": "先行処理が取消されたため比較基準の確認が必要です", "requires_rebase": True})
                    self.save_job(later)
            self.config["mappings"][job["dest"]]["local"] = job["before"]
            atomic_json(self.config_path, self.config)
            return self.public_job(job)

    def acknowledge(self, jobid, session=None, turn=None):
        with lock(self.root / "locks" / "state.lock"):
            job = read_json(self.job_path(jobid))
            if not job:
                raise SyncError("処理が見つかりません")
            job["reported"] = True
            job["reported_manifest"] = local_manifest(job["source"])
            self.save_job(job)
            if session and turn:
                tp = self.turn_path(session, turn)
                td = read_json(tp, {"session": session, "turn": turn})
                td.setdefault("handled", {})[canonical(job["source"])] = job["reported_manifest"]
                atomic_json(tp, td)
            return self.public_job(job)

    def public_job(self, job):
        result = {k: job.get(k) for k in ("id", "dest", "state", "reason", "commit", "remote_head", "confirmed_at")}
        result["files"] = len(job.get("changes", {}))
        if job.get("commit") and self.config.get("remote", "").startswith("https://github.com/"):
            result["url"] = self.config["remote"].removesuffix(".git") + "/commit/" + job["commit"]
        return result

    def turn_policy(self, session, turn, send):
        path = self.turn_path(session, turn)
        td = read_json(path, {"session": session, "turn": turn})
        td["send"] = send
        atomic_json(path, td)
        return {"send": send}

    def hook(self, payload):
        self.require_config()
        event, session, turn = payload.get("hook_event_name"), payload.get("session_id", ""), payload.get("turn_id", "")
        if not session or not turn:
            return {"systemMessage": "スキル同期フックのターン情報が不足しています。手動経路で同期結果を確認してください。"}
        path = self.turn_path(session, turn)
        td = read_json(path)
        if event == "UserPromptSubmit":
            if td:
                return {}
            td = {"session": session, "turn": turn, "send": "unset", "baseline": {}, "sources": {}, "issues": [], "continued": False}
            deadline = time.monotonic() + 7
            candidates = {canonical(x["source"]): x["source"] for x in discover(self.config["roots"])}
            candidates.update({canonical(m["source"]): m["source"] for m in self.config["mappings"].values()})
            for real, source in candidates.items():
                try:
                    td["baseline"][real] = local_manifest(source, deadline=deadline)
                    td["sources"][real] = source
                except (OSError, SyncError) as error:
                    td["issues"].append(type(error).__name__)
            atomic_json(path, td)
            context = f"スキル同期ターン: session={session}, turn={turn}。スキル編集時にskill-github-syncでbegin→検証→ready→sync→ackを実行し、送信可否をturn-policyに記録する。"
            if td["issues"]:
                context += " 比較基準に不足があります。未確認の変更を送らず、結果を報告する。"
            return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}
        if event != "Stop":
            return {}
        if payload.get("stop_hook_active") or (td and td.get("continued")):
            return {}
        if not td:
            return {"systemMessage": "スキル同期の開始基準がありません。編集したスキルは手動経路で確認してください。"}
        relevant = [j for j in self.jobs() if j["session"] == session and j["turn"] == turn]
        changes, problems = [], list(td.get("issues", []))
        candidates = {canonical(x["source"]): x["source"] for x in discover(self.config["roots"])}
        candidates.update(td["sources"])
        deadline = time.monotonic() + 7
        for real, source in candidates.items():
            try:
                current = local_manifest(source, deadline=deadline)
                previous = td["baseline"].get(real, {})
                handled = same(td.get("handled", {}).get(real, {}), current) if real in td.get("handled", {}) else False
                handled = handled or any(canonical(j["source"]) == real and j.get("reported") and same(j.get("reported_manifest", {}), current) for j in relevant)
                if not handled and not same(current, previous):
                    changes.append(source)
            except (OSError, SyncError) as error:
                problems.append(type(error).__name__)
        unfinished = [j["id"] for j in relevant if not j.get("reported")]
        if not changes and not unfinished and not problems:
            return {}
        td["continued"] = True
        atomic_json(path, td)
        detail = ", ".join(changes[:6]) if changes else "登録済み処理"
        return {"decision": "block", "reason": "スキル同期の終了確認を一度行ってください。対象: " + detail + ". session=" + session + ", turn=" + turn + ". skill-github-syncを読み、今回の依頼に属するかと検証結果を確認し、begin/ready/syncの漏れを補完して結果を報告・ackしてください。送信禁止・未完成・所属不明・基準不足の変更は送らず、その理由を報告してください。"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Codexスキルの完成版をGitHubへ保存する")
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--remote", required=True)
    init.add_argument("--branch", default="main")
    init.add_argument("--root", action="append", required=True)
    init.add_argument("--git", default="git")
    init.add_argument("--cache-repo")
    init.add_argument("--author-name", default="Codex skill sync")
    init.add_argument("--author-email", default="skill-sync@localhost")
    sub.add_parser("inventory")
    sub.add_parser("status")
    begin = sub.add_parser("begin")
    begin.add_argument("--source", required=True)
    begin.add_argument("--dest")
    begin.add_argument("--local-only", action="store_true")
    begin.add_argument("--include-existing", action="store_true")
    begin.add_argument("--bootstrap", action="store_true")
    begin.add_argument("--recover-turn", action="store_true")
    ready = sub.add_parser("ready")
    ready.add_argument("--job", required=True)
    ready.add_argument("--validation", required=True)
    ready.add_argument("--delete", action="append", default=[])
    for command in ("sync", "retry"):
        sp = sub.add_parser(command)
        sp.add_argument("--send-allowed", action="store_true", required=True)
    for command in ("ack", "cancel"):
        sp = sub.add_parser(command)
        sp.add_argument("--job", required=True)
    policy = sub.add_parser("turn-policy")
    policy.add_argument("--send", choices=("allow", "deny"), required=True)
    sub.add_parser("hook")
    for name in ("begin", "sync", "retry", "turn-policy", "ack"):
        sp = sub.choices[name]
        sp.add_argument("--session", default=os.environ.get("CODEX_THREAD_ID", "manual"))
        sp.add_argument("--turn", default="manual")
    args = parser.parse_args(argv)
    engine = Engine(args.state)
    try:
        if args.command == "init":
            result = engine.initialize(args.remote, args.branch, args.root, args.git, {"name": args.author_name, "email": args.author_email}, args.cache_repo)
        elif args.command == "inventory":
            result = {"configured": list(engine.config.get("mappings", {}).values()), "discovered": discover(engine.config.get("roots", []))}
        elif args.command == "status":
            result = {"jobs": [engine.public_job(j) for j in engine.jobs()]}
        elif args.command == "begin":
            result = engine.public_job(engine.begin(args.source, dest=args.dest, session=args.session, turn=args.turn, local_only=args.local_only, include_existing=args.include_existing, bootstrap=args.bootstrap, recover_turn=args.recover_turn))
        elif args.command == "ready":
            result = engine.public_job(engine.ready(args.job, args.validation, args.delete))
        elif args.command in {"sync", "retry"}:
            result = engine.sync(args.session, args.turn, send_allowed=args.send_allowed, resume_action=args.command == "retry")
        elif args.command == "cancel":
            result = engine.cancel(args.job)
        elif args.command == "ack":
            result = engine.acknowledge(args.job, args.session, args.turn)
        elif args.command == "turn-policy":
            result = engine.turn_policy(args.session, args.turn, args.send)
        else:
            result = engine.hook(json.load(sys.stdin))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (SyncError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, SyncError) else "ファイルまたは設定の確認が必要です（" + type(error).__name__ + "）"
        result = {"systemMessage": "スキル同期: " + message} if args.command == "hook" else {"ok": False, "reason": message}
        print(json.dumps(result, ensure_ascii=False))
        return 0 if args.command == "hook" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
