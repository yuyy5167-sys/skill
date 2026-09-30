from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_github_sync.py"
spec = importlib.util.spec_from_file_location("skill_github_sync", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SyncTests(unittest.TestCase):
    def git(self, folder, *args):
        r = subprocess.run(["git", "-C", str(folder), *args], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        return r.stdout

    def setUp(self):
        temp_root = Path(__file__).resolve().parents[3] / "output" / "tmp" / "skill-sync-tests"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="skill-sync-test-", dir=temp_root)
        self.base = Path(self.temp.name)
        self.global_file = self.base / "git-global"
        self.global_file.write_text("[core]\n autocrlf = true\n", encoding="utf-8")
        self.env = patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(self.global_file)})
        self.env.start()
        self.remote = self.base / "remote.git"
        self.remote.mkdir()
        self.git(self.remote, "init", "--bare", "--quiet", "--initial-branch=main")
        self.other = self.base / "other"
        self.other.mkdir()
        self.git(self.other, "init", "--quiet", "--initial-branch=main")
        self.git(self.other, "config", "user.name", "Fixture")
        self.git(self.other, "config", "user.email", "fixture@example.invalid")
        self.git(self.other, "remote", "add", "origin", str(self.remote))
        (self.other / "demo").mkdir()
        (self.other / "demo" / "SKILL.md").write_bytes(b"initial\n")
        self.git(self.other, "-c", "core.autocrlf=false", "add", "--", "demo/SKILL.md")
        self.git(self.other, "commit", "--quiet", "-m", "Initial")
        self.git(self.other, "push", "--quiet", "origin", "main")
        self.skills = self.base / "skills"
        self.source = self.skills / "demo"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_bytes(b"initial\n")
        self.engine = mod.Engine(self.base / "state")
        self.engine.initialize(str(self.remote), "main", [str(self.skills)])

    def tearDown(self):
        self.env.stop()
        self.assertEqual(self.base.resolve().parent, (Path(__file__).resolve().parents[3] / "output" / "tmp" / "skill-sync-tests").resolve())
        self.temp.cleanup()

    def bytes(self, path="demo/SKILL.md"):
        return self.git(self.remote, "show", "main:" + path)

    def job(self, data=b"changed\n", session="s", turn="t"):
        job = self.engine.begin(self.source, session=session, turn=turn)
        (self.source / "SKILL.md").write_bytes(data)
        return self.engine.ready(job["id"], "fixture behavior validation passed")

    def foreign(self, path, data):
        self.git(self.other, "fetch", "--quiet", "origin")
        self.git(self.other, "reset", "--quiet", "--hard", "origin/main")
        target = self.other / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.git(self.other, "-c", "core.autocrlf=false", "add", "--", path)
        self.git(self.other, "commit", "--quiet", "-m", "Foreign update")
        self.git(self.other, "push", "--quiet", "origin", "main")

    def send(self):
        return self.engine.sync("s", "t", send_allowed=True)

    def test_update_and_byte_preservation(self):
        job = self.engine.begin(self.source, session="s", turn="t")
        data = "日本語\r\nsecond\n".encode("utf-8")
        (self.source / "SKILL.md").write_bytes(data)
        (self.source / "assets").mkdir()
        binary = bytes(range(256))
        (self.source / "assets" / "pixel.bin").write_bytes(binary)
        (self.source / ".env").write_text("private", encoding="utf-8")
        self.engine.ready(job["id"], "text and image fixture checked")
        result = self.send()["jobs"][0]
        self.assertEqual(result["state"], "SYNCED")
        self.assertEqual(self.bytes(), data)
        self.assertEqual(self.bytes("demo/assets/pixel.bin"), binary)
        paths = self.git(self.remote, "ls-tree", "-r", "--name-only", "main").decode()
        self.assertNotIn(".env", paths)
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")

    def test_new_skill(self):
        source = self.skills / "new-skill"
        job = self.engine.begin(source, dest="new-skill", session="s", turn="t")
        (source / "SKILL.md").write_bytes(b"new\n")
        self.engine.ready(job["id"], "new skill checked")
        self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        self.assertEqual(self.bytes("new-skill/SKILL.md"), b"new\n")

    @unittest.skipUnless(os.name == 'nt', 'Windows hook command execution')
    def test_installer_migrates_and_executes_windows_hooks(self):
        shell = shutil.which('pwsh.exe') or shutil.which('powershell.exe')
        self.assertIsNotNone(shell)
        user_codex = self.base / 'fixture codex'
        (user_codex / 'skills').mkdir(parents=True)
        agents = self.base / 'fixture agents'
        agents.mkdir()
        instructions = '既存の指示を保持する。\n'
        (user_codex / 'AGENTS.md').write_text(instructions, encoding='utf-8')
        state = self.base / "日本語 space ' quote" / 'state'
        engine = mod.Engine(state)
        engine.initialize(str(self.remote), 'main', [str(self.skills)])
        old_command = '"' + sys.executable + '" -X utf8 "' + str(SCRIPT) + '" --state "' + str(state) + '" hook'
        mod.atomic_json(state / 'installation.json', {'hook_command':old_command})
        unrelated = {'type':'command','command':'Write-Output unrelated'}
        mod.atomic_json(user_codex / 'hooks.json', {'hooks':{'UserPromptSubmit':[{'hooks':[{'type':'command','command':old_command}]}],'Stop':[{'hooks':[unrelated]}]}})
        installer = SCRIPT.parent / 'install.ps1'
        args = [shell,'-NoProfile','-NonInteractive','-File',str(installer),'-SkillPath',str(SCRIPT.parents[1]),'-StatePath',str(state),'-UserCodexPath',str(user_codex),'-UserAgentsSkills',str(agents)]
        for _ in range(2):
            installed = subprocess.run(args,capture_output=True)
            self.assertEqual(installed.returncode,0,installed.stderr.decode('utf-8','replace'))
        definition = mod.read_json(user_codex / 'hooks.json')
        start_handlers = [h for g in definition['hooks']['UserPromptSubmit'] for h in g['hooks']]
        stop_handlers = [h for g in definition['hooks']['Stop'] for h in g['hooks']]
        self.assertEqual(len(start_handlers),1)
        self.assertEqual(len(stop_handlers),2)
        self.assertIn(unrelated,stop_handlers)
        self.assertTrue((user_codex / 'AGENTS.md').read_text(encoding='utf-8').startswith(instructions))
        self.assertEqual((user_codex / 'AGENTS.md').read_text(encoding='utf-8').count('<!-- skill-github-sync:start -->'),1)
        payload = {'hook_event_name':'UserPromptSubmit','session_id':'installer-smoke','turn_id':'t'}
        started = subprocess.run([shell,'-NoProfile','-NonInteractive','-Command',start_handlers[0]['commandWindows']],input=json.dumps(payload).encode(),capture_output=True,timeout=10)
        self.assertEqual(started.returncode,0,started.stderr.decode('utf-8','replace'))
        self.assertIn('session=installer-smoke',json.loads(started.stdout)['hookSpecificOutput']['additionalContext'])
        payload['hook_event_name'] = 'Stop'
        stopped = subprocess.run([shell,'-NoProfile','-NonInteractive','-Command',start_handlers[0]['commandWindows']],input=json.dumps(payload).encode(),capture_output=True,timeout=10)
        self.assertEqual(stopped.returncode,0,stopped.stderr.decode('utf-8','replace'))
        self.assertEqual(json.loads(stopped.stdout),{})

    def test_no_change_does_not_commit(self):
        job = self.engine.begin(self.source, session="s", turn="t")
        self.engine.ready(job["id"], "already identical")
        self.assertEqual(self.send()["jobs"][0]["state"], "NO_CHANGE")
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"1")

    def test_intended_deletion_only(self):
        self.foreign("demo/old.txt", b"old\n")
        self.engine.config["mappings"]["demo"]["remote"] = self.engine.tree(*self.engine.reference(), "demo")
        (self.source / "old.txt").write_bytes(b"old\n")
        self.engine.config["mappings"]["demo"]["local"] = mod.local_manifest(self.source)
        mod.atomic_json(self.engine.config_path, self.engine.config)
        job = self.engine.begin(self.source, session="s", turn="t")
        (self.source / "old.txt").unlink()
        with self.assertRaises(mod.SyncError):
            self.engine.ready(job["id"], "checked")
        self.engine.ready(job["id"], "checked", ["old.txt"])
        self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        paths = self.git(self.remote, "ls-tree", "-r", "--name-only", "main").decode()
        self.assertNotIn("old.txt", paths)
        self.assertEqual(self.bytes(), b"initial\n")

    def test_remote_conflict_preserved(self):
        self.job()
        self.foreign("demo/SKILL.md", b"foreign\n")
        self.assertEqual(self.send()["jobs"][0]["state"], "NEEDS_ACTION")
        self.assertEqual(self.bytes(), b"foreign\n")

    def test_unrelated_remote_update_preserved(self):
        self.job()
        self.foreign("other/keep.txt", b"keep\n")
        self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        self.assertEqual(self.bytes("other/keep.txt"), b"keep\n")

    def test_lost_push_response_does_not_duplicate(self):
        self.job()
        original = self.engine.git
        count = [0]
        def lose_response(folder, *args, **kw):
            result = original(folder, *args, **kw)
            if args and args[0] == "push":
                count[0] += 1
                raise mod.Retryable("応答が失われました")
            return result
        with patch.object(self.engine, "git", side_effect=lose_response):
            self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        self.assertEqual(count[0], 1)
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")

    def test_failed_push_then_foreign_update_and_resume(self):
        job = self.job()
        original = self.engine.git
        def fail(folder, *args, **kw):
            if args and args[0] == "push":
                raise mod.Retryable("通信失敗")
            return original(folder, *args, **kw)
        with patch.object(self.engine, "git", side_effect=fail):
            self.assertEqual(self.send()["jobs"][0]["state"], "RETRY_PENDING")
        self.foreign("other/new.txt", b"new remote data\n")
        self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        self.assertEqual(self.bytes(), b"changed\n")
        self.assertEqual(self.bytes("other/new.txt"), b"new remote data\n")
        self.assertEqual(mod.read_json(self.engine.job_path(job["id"]))["desired"]["SKILL.md"]["sha256"], mod.digest(b"changed\n"))

    def test_pending_jobs_keep_order_across_sessions(self):
        first = self.job(b"first\n", "old", "one")
        second = self.job(b"second\n", "new", "two")
        jobs = self.engine.sync("third", "three", send_allowed=True)["jobs"]
        self.assertEqual([j["id"] for j in jobs], [first["id"], second["id"]])
        self.assertTrue(all(j["state"] == "SYNCED" for j in jobs))
        self.assertEqual(self.bytes(), b"second\n")

    def test_local_only_never_enters_later_queue(self):
        self.engine.turn_policy("s", "t", "deny")
        job = self.engine.begin(self.source, session="s", turn="t")
        (self.source / "SKILL.md").write_bytes(b"local only\n")
        self.assertEqual(self.engine.ready(job["id"], "checked")["state"], "LOCAL_ONLY")
        self.assertFalse(self.send()["sent"])
        self.assertEqual(self.engine.sync("later", "next", send_allowed=True)["jobs"], [])
        self.assertEqual(self.bytes(), b"initial\n")
        with self.assertRaises(mod.SyncError):
            self.engine.begin(self.source, session="later", turn="next")

    def test_cancelled_predecessor_blocks_later_job(self):
        first = self.job(b"first\n", "s", "one")
        second = self.job(b"second\n", "s", "two")
        self.engine.cancel(first["id"])
        self.assertEqual(mod.read_json(self.engine.job_path(second["id"]))["state"], "NEEDS_ACTION")
        self.assertEqual(self.engine.sync("s", "retry", send_allowed=True, resume_action=True)["jobs"], [])
        self.assertEqual(self.bytes(), b"initial\n")

    def test_edit_owner_and_validation_failure(self):
        job = self.engine.begin(self.source, session="one", turn="one")
        with self.assertRaises(mod.SyncError):
            self.engine.begin(self.source, session="two", turn="two")
        (self.source / "SKILL.md").write_bytes(b"not validated\n")
        with self.assertRaises(mod.SyncError):
            self.engine.ready(job["id"], "")
        self.assertEqual(self.send()["jobs"], [])
        self.assertEqual(self.bytes(), b"initial\n")

    def test_secret_stops_publication_without_disclosure(self):
        job = self.engine.begin(self.source, session="s", turn="t")
        token = b"ghp_" + b"a" * 40
        (self.source / "SKILL.md").write_bytes(token)
        with self.assertRaises(mod.SyncError) as caught:
            self.engine.ready(job["id"], "checked")
        self.assertNotIn(token.decode(), str(caught.exception))
        self.assertEqual(self.send()["jobs"], [])

    def test_hook_recovers_missing_begin_ready_and_send(self):
        context = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "turn_id": "t"}
        self.engine.hook(context)
        (self.source / "SKILL.md").write_bytes(b"recovered\n")
        stop = {**context, "hook_event_name": "Stop", "stop_hook_active": False}
        self.assertEqual(self.engine.hook(stop)["decision"], "block")
        job = self.engine.begin(self.source, session="s", turn="t", recover_turn=True)
        self.engine.ready(job["id"], "recovered work validated")
        self.assertEqual(self.send()["jobs"][0]["state"], "SYNCED")
        self.engine.acknowledge(job["id"], "s", "t")
        self.assertEqual(self.engine.hook({**stop, "stop_hook_active": True}), {})
        self.assertEqual(self.bytes(), b"recovered\n")

    def test_hook_no_change_no_continuation_and_json_cli(self):
        context = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "turn_id": "t"}
        self.engine.hook(context)
        self.assertEqual(self.engine.hook({**context, "hook_event_name": "Stop"}), {})
        r = subprocess.run([sys.executable, str(SCRIPT), "--state", str(self.engine.root), "hook"], input=json.dumps({**context, "hook_event_name": "Stop"}).encode(), capture_output=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout), {})

    def test_real_os_lock_survives_until_owner_exits(self):
        lockpath = self.engine.root / "locks" / "sync.lock"
        code = "import importlib.util,time;from pathlib import Path;s=importlib.util.spec_from_file_location('sync'," + repr(str(SCRIPT)) + ");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nwith m.lock(Path(" + repr(str(lockpath)) + ")):\n print('locked',flush=True);time.sleep(30)"
        child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline().strip(), b"locked")
            with self.assertRaises(mod.Retryable):
                with mod.lock(lockpath):
                    pass
        finally:
            child.terminate()
            child.communicate(timeout=5)
        with mod.lock(lockpath):
            self.assertTrue(lockpath.exists())

    def test_timeout_terminates_only_its_git_process_tree(self):
        self.engine.config["git_timeout"] = 1
        started = __import__('time').monotonic()
        with self.assertRaises(mod.Retryable):
            self.engine.git(self.other, "-c", "alias.fixture-delay=!python -c 'import time; time.sleep(30)'", "fixture-delay")
        self.assertLess(__import__('time').monotonic() - started, 12)
        self.assertEqual(self.bytes(), b"initial\n")

    def test_initialization_can_resume_after_fetch_failure(self):
        other_engine = mod.Engine(self.base / "failed-init")
        original = other_engine.git
        def failing(folder, *args, **kwargs):
            if args and args[0] == "fetch":
                raise mod.Retryable("一時的な取得失敗")
            return original(folder, *args, **kwargs)
        with patch.object(other_engine, "git", side_effect=failing):
            with self.assertRaises(mod.Retryable):
                other_engine.initialize(str(self.remote), "main", [str(self.skills)])
        with self.assertRaises(mod.SyncError):
            other_engine.begin(self.source)
        self.assertEqual(other_engine.initialize(str(self.remote), "main", [str(self.skills)])["skills"], 1)

    def test_junction_dedup_and_external_internal_link(self):
        aliasroot = self.base / "aliases"
        aliasroot.mkdir()
        alias = aliasroot / "demo"
        outside = self.base / "outside"
        outside.mkdir()
        def link(target, source):
            if os.name == "nt":
                result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", "New-Item -ItemType Junction -Path '" + str(target).replace("'", "''") + "' -Target '" + str(source).replace("'", "''") + "' | Out-Null"], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
            else:
                target.symlink_to(source, target_is_directory=True)
        link(alias, self.source)
        self.assertEqual(len(mod.discover([str(self.skills), str(aliasroot)])), 1)
        link(self.source / "outside", outside)
        with self.assertRaises(mod.SyncError):
            mod.local_manifest(self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
