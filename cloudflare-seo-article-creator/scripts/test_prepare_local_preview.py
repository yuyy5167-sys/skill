"""Behavioral checks for disposable previews. Run with TMPDIR inside task tmp/."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("prepare_preview", Path(__file__).with_name("prepare-local-preview.py"))
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewStorageTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="article-preview-")
        self.work = Path(self.workspace.name) / "ブログ work"
        self.project = self.work / "site"
        self.article = self.project / "src/content/blog/test-article/index.md"
        self.article.parent.mkdir(parents=True)
        self.original = b"\xef\xbb\xbf---\r\ntitle: Test\r\ndraft: true\r\n---\r\n## Section\r\nBody\r\n"
        self.article.write_bytes(self.original)
        (self.project / "node_modules").mkdir()
        (self.project / "node_modules/shared.txt").write_text("keep dependency", encoding="utf-8")
        (self.project / "astro.config.mjs").write_text("export default {};", encoding="utf-8")
        (self.project / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        self.upper_tmp = self.work / "TMP"
        self.upper_tmp.mkdir()

    def tearDown(self):
        self.workspace.cleanup()

    def run_prepare(self, **kwargs):
        return preview.prepare(str(self.project), "test-article", "run-1", work_root=str(self.work), **kwargs)

    def test_preview_and_all_auxiliary_files_are_disposable_source_and_dependencies_survive(self):
        for relative in ["src/.env.local", "src/.cache/old", "packages/sample/node_modules/old",
                         "packages/sample/dist/old", "packages/sample/TMP/old"]:
            item = self.project / relative
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text("not a preview input", encoding="utf-8")
        image = self.article.parent / "images/cover.webp"
        image.parent.mkdir()
        image.write_bytes(b"keep adopted image")
        result = self.run_prepare()
        run = Path(result["run_root"])
        isolated = Path(result["preview_root"])
        self.assertEqual(Path(result["temporary_root"]), self.upper_tmp.resolve())
        for key in ["preview_root", "verification_directory", "scratch_directory",
                    "process_temp_directory", "cleanup_info", "build_output", "preview_config"]:
            self.assertTrue(preview.within(Path(result[key]), run), key)
        for value in result["process_environment"].values():
            self.assertTrue(preview.within(Path(value), run))
        self.assertEqual(Path(result["preview_article"]).read_bytes(), self.original.replace(b"draft: true", b"draft: false", 1))
        self.assertEqual(self.article.read_bytes(), self.original)
        self.assertEqual((isolated / "node_modules").resolve(), (self.project / "node_modules").resolve())
        self.assertTrue((isolated / "node_modules/shared.txt").is_file())
        for relative in ["src/.env.local", "src/.cache", "packages/sample/node_modules",
                         "packages/sample/dist", "packages/sample/TMP"]:
            self.assertFalse((isolated / relative).exists(), relative)
        for key in ["build_output", "verification_directory", "scratch_directory", "process_temp_directory"]:
            folder = Path(result[key])
            folder.mkdir(exist_ok=True)
            (folder / "disposable.txt").write_text("discard", encoding="utf-8")
        # Only remove the shared-dependency link; never traverse its target.
        link = isolated / "node_modules"
        if os.name == "nt":
            os.rmdir(link)
        else:
            link.unlink()
        shutil.rmtree(run)
        self.assertFalse(run.exists())
        self.assertEqual(self.article.read_bytes(), self.original)
        self.assertEqual(image.read_bytes(), b"keep adopted image")
        self.assertTrue((self.project / "node_modules/shared.txt").is_file())

    def test_creates_tmp_when_no_temporary_folder_exists(self):
        self.upper_tmp.rmdir()
        result = self.run_prepare(initialize_only=True)
        self.assertEqual(Path(result["temporary_root"]), self.work.resolve() / "tmp")
        self.assertFalse(Path(result["preview_root"]).exists())

    def test_initialize_before_article_exists_then_reuse_same_run(self):
        self.article.unlink()
        result = self.run_prepare(initialize_only=True)
        scratch_file = Path(result["scratch_directory"]) / "candidate.png"
        scratch_file.write_bytes(b"temporary candidate")
        self.article.write_bytes(self.original)
        completed = self.run_prepare()
        self.assertEqual(result["run_root"], completed["run_root"])
        self.assertEqual(scratch_file.read_bytes(), b"temporary candidate")
        self.assertEqual(completed["status"], "PREVIEW_WORKSPACE_READY")

    def test_rejects_existing_preview_and_unowned_run_folder(self):
        result = self.run_prepare()
        with self.assertRaises(ValueError):
            self.run_prepare()
        self.assertEqual(Path(result["preview_article"]).read_bytes(), self.original.replace(b"draft: true", b"draft: false", 1))
        other_run = self.upper_tmp / "codex-article-work/run-2--test-article"
        other_run.mkdir()
        sentinel = other_run / "other-user-file.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            preview.prepare(str(self.project), "test-article", "run-2", work_root=str(self.work))
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_rejects_output_outside_temporary_run_and_source_as_temporary_folder(self):
        for kwargs in [dict(temporary_root=str(self.project)),
                       dict(temporary_root=str(self.work.parent / "outside-tmp")),
                       dict(preview_root=str(self.work / "outside-preview"))]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_prepare(**kwargs)
        self.assertFalse((self.work / "outside-preview").exists())
        self.assertFalse((self.project / "codex-article-work").exists())
        self.assertEqual(self.article.read_bytes(), self.original)

    @unittest.skipIf(os.name == "nt", "directory symlink creation needs Windows privileges")
    def test_rejects_temporary_root_symlink_escape(self):
        self.upper_tmp.rmdir()
        outside = self.work.parent / "outside"
        outside.mkdir()
        self.upper_tmp.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_prepare(initialize_only=True)
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "directory symlink creation needs Windows privileges")
    def test_rejects_source_symlink_copy_and_keeps_partial_files_in_tmp(self):
        (self.project / "src/linked-input").symlink_to(self.work, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_prepare()
        self.assertEqual(self.article.read_bytes(), self.original)
        self.assertTrue((self.upper_tmp / "codex-article-work/run-1--test-article/CLEANUP-INFO.txt").is_file())

    def test_invalid_ids_and_missing_draft_do_not_modify_source(self):
        with self.assertRaises(ValueError):
            preview.prepare(str(self.project), "../escape", "run-1", work_root=str(self.work))
        self.article.write_bytes(self.original.replace(b"draft: true", b"draft: false"))
        with self.assertRaises(ValueError):
            self.run_prepare()
        self.assertNotIn(b"draft: true", self.article.read_bytes())
        self.assertFalse((self.upper_tmp / "codex-article-work/run-1--test-article/preview").exists())


if __name__ == "__main__":
    unittest.main()
