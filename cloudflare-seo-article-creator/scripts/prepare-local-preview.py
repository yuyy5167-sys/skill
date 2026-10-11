#!/usr/bin/env python3
"""Prepare a disposable article preview inside the working folder's tmp/TMP."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


EXCLUDED = {".git", "node_modules", "dist", "tmp", ".tmp", ".astro",
            ".astro-cache", ".vite-cache", ".npm-cache", ".cache", "__pycache__"}


def within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return path.resolve() != parent.resolve()
    except ValueError:
        return False


def temporary_directory(work_root: Path, explicit: str | None) -> Path:
    if explicit:
        selected = Path(explicit).absolute()
    else:
        existing = {child.name: child for child in work_root.iterdir() if child.name in ("tmp", "TMP")}
        selected = existing.get("tmp") or existing.get("TMP") or work_root / "tmp"
    if selected.parent.resolve() != work_root or selected.is_symlink():
        raise ValueError("一時フォルダは作業フォルダ直下の実フォルダにしてください")
    selected.mkdir(exist_ok=True)
    selected = selected.resolve()
    if selected.parent != work_root:
        raise ValueError("一時フォルダが作業フォルダの外を指しています")
    return selected


def copy_inputs(source: Path, destination: Path) -> None:
    def ignore(folder, names):
        omitted = []
        for name in names:
            if name.lower() in EXCLUDED or name.startswith(".env"):
                omitted.append(name)
            elif (Path(folder) / name).is_symlink():
                raise ValueError("入力のシンボリックリンクはコピーしません: " + str(Path(folder) / name))
        return omitted

    for name in ("src", "public", "packages"):
        item = source / name
        if item.is_symlink():
            raise ValueError("入力フォルダのシンボリックリンクはコピーしません: " + str(item))
        if item.is_dir():
            shutil.copytree(item, destination / name, ignore=ignore)
    for name in ("astro.config.mjs", "package.json", "tsconfig.json"):
        item = source / name
        if item.is_symlink():
            raise ValueError("入力ファイルのシンボリックリンクはコピーしません: " + str(item))
        if item.is_file():
            shutil.copy2(item, destination / name)


def dependency_link(link: Path, target: Path) -> str:
    if os.name == "nt":
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        command = "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path " + quote(link) + " -Target " + quote(target) + " | Out-Null"
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "junction"
    link.symlink_to(target, target_is_directory=True)
    return "symlink"


def prepare(project_root: str, article_id: str, run_id: str, *,
            work_root: str | None = None, temporary_root: str | None = None,
            preview_root: str | None = None, initialize_only: bool = False) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,119}", article_id):
        raise ValueError("記事IDが不正です")
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,80}", run_id):
        raise ValueError("実行IDが不正です")
    project = Path(project_root).resolve(strict=True)
    working = Path(work_root).resolve(strict=True) if work_root else project
    if not project.is_dir() or not working.is_dir():
        raise ValueError("プロジェクトと作業フォルダは実在するフォルダにしてください")
    if project != working and not within(project, working):
        raise ValueError("プロジェクトが作業フォルダの外にあります")
    temporary = temporary_directory(working, temporary_root)
    if temporary == project or within(project, temporary) or any(
            temporary == project / name or within(temporary, project / name)
            for name in ("src", "public", "packages", "node_modules", ".git")):
        raise ValueError("正規プロジェクトや記事・依存関係の保存先を一時フォルダにはできません")
    container = temporary / "codex-article-work"
    if container.is_symlink() or not within(container, temporary):
        raise ValueError("一時実行ルートが一時フォルダの外を指しています")
    run = container / (run_id + "--" + article_id)
    if run.is_symlink() or not within(run, container):
        raise ValueError("実行フォルダが一時実行ルートの外を指しています")
    preview = Path(preview_root).absolute() if preview_root else run / "preview"
    if preview.is_symlink() or preview.resolve() != (run / "preview").resolve():
        raise ValueError("プレビュー出力先は実行フォルダ内の preview/ に限定します")
    identity = {"schema_version": "2.0", "work_root": str(working),
                "project_root": str(project), "temporary_root": str(temporary),
                "run_id": run_id, "article_id": article_id}
    manifest = run / "preview-manifest.json"
    if run.exists():
        if manifest.is_symlink() or not manifest.is_file() or json.loads(manifest.read_text(encoding="utf-8")) != identity:
            raise ValueError("既存の実行フォルダを今回の一時作業として確認できません")
    else:
        run.mkdir(parents=True, exist_ok=False)
        manifest.write_text(json.dumps(identity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    folders = {"verification_directory": run / "verification",
               "scratch_directory": run / "scratch",
               "process_temp_directory": run / "process-tmp"}
    for folder in folders.values():
        if folder.is_symlink() or not within(folder, run):
            raise ValueError("一時作業用フォルダが実行フォルダの外を指しています")
        folder.mkdir(exist_ok=True)
    cleanup = run / "CLEANUP-INFO.txt"
    if cleanup.is_symlink():
        raise ValueError("削除説明ファイルが外部へのリンクです")
    source_article = project / "src" / "content" / "blog" / article_id / "index.md"
    cleanup.write_text(
        "これは記事の表示確認にだけ使う一時実行フォルダです。\n"
        f"作成・準備日時: {datetime.now(timezone.utc).isoformat()}\n"
        f"実行ID: {run_id}\n記事ID: {article_id}\n正本記事: {source_article}\n"
        "preview/ はサイトの隔離コピーとビルド結果・キャッシュです。\n"
        "scratch/ は調査途中の資料・画像候補・変換途中のファイル、\n"
        "verification/ は表示確認のスクリーンショット・ログ、\n"
        "process-tmp/ は実行プロセスの一時ファイルです。\n"
        "記事原本・採用画像・制作履歴・共有ライブラリの実体はこのフォルダの外にあります。\n"
        "ユーザーの閲覧・確認が済み、ローカル配信と作業プロセスを停止した後は、\n"
        "この実行フォルダ全体を削除またはゴミ箱へ移動できます。\n"
        "preview/node_modules は共有先へのリンクです。削除するときはリンクだけを外し、\n"
        "共有先をたどって削除しないでください。ブラウザへの表示だけでは閲覧完了と判定しません。\n",
        encoding="utf-8")
    result = {**identity, "status": "TEMPORARY_WORKSPACE_READY", "run_root": str(run),
              "preview_root": str(preview), "source_article": str(source_article),
              "temporary_work_root": str(container), "cleanup_info": str(cleanup),
              **{key: str(value) for key, value in folders.items()},
              "process_environment": {key: str(folders["process_temp_directory"])
                                      for key in ("TMPDIR", "TEMP", "TMP")}}
    result["process_environment"]["npm_config_cache"] = str(preview / ".npm-cache")
    if initialize_only:
        return result
    if preview.exists():
        raise ValueError("プレビュー出力先が既に存在します。上書きしません")
    if not within(source_article, project / "src" / "content" / "blog") or not source_article.is_file():
        raise ValueError("正本記事が見つからないか記事ルートの外を指しています")
    node_modules = project / "node_modules"
    if not node_modules.is_dir() or not (project / "astro.config.mjs").is_file():
        raise ValueError("既存の node_modules と Astro設定が必要です。自動インストールは行いません")
    original = source_article.read_bytes()
    text = original.decode("utf-8-sig")
    frontmatter = re.match(r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---", text, re.S)
    pattern = re.compile(r"^draft:[ \t]*true[ \t]*(?=\r?$)", re.M)
    if not frontmatter or len(pattern.findall(frontmatter.group("body"))) != 1:
        raise ValueError("正本記事の一意な draft: true を確認できません")
    changed_body = pattern.sub("draft: false", frontmatter.group("body"), count=1)
    changed = text[:frontmatter.start("body")] + changed_body + text[frontmatter.end("body"):]
    changed_bytes = (b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + changed.encode("utf-8")
    preview.mkdir()
    copy_inputs(project, preview)
    article_copy = preview / "src" / "content" / "blog" / article_id / "index.md"
    if article_copy.read_bytes() != original:
        raise ValueError("コピー中に正本記事の内容が変わりました")
    article_copy.write_bytes(changed_bytes)
    link_kind = dependency_link(preview / "node_modules", node_modules.resolve())
    config = preview / "codex-preview.config.mjs"
    config.write_text(
        "import baseConfig from './astro.config.mjs';\n"
        "import { defineConfig } from 'astro/config';\n\n"
        "export default defineConfig({\n"
        "  ...baseConfig,\n  root: '.',\n  outDir: './dist',\n  cacheDir: './.astro-cache',\n"
        "  vite: { ...(baseConfig.vite ?? {}), cacheDir: '.vite-cache' },\n});\n",
        encoding="utf-8")
    if source_article.read_bytes() != original:
        raise ValueError("プレビュー準備中に正本記事が変更されました")
    result.update({"status": "PREVIEW_WORKSPACE_READY", "source_draft_preserved": True,
                   "source_article_sha256": hashlib.sha256(original).hexdigest(),
                   "preview_article": str(article_copy), "preview_config": str(config),
                   "preview_config_argument": config.name,
                   "node_modules_source": str(node_modules.resolve()), "node_modules_link_kind": link_kind,
                   "build_output": str(preview / "dist")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--run-id", default=uuid.uuid4().hex)
    parser.add_argument("--work-root")
    parser.add_argument("--temporary-root")
    parser.add_argument("--preview-root")
    parser.add_argument("--initialize-only", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(**vars(args))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
