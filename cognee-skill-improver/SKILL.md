---
name: cognee-skill-improver
description: Capture how a Codex skill was used, store what worked and what failed, and turn repeated usage into concrete skill improvements. Use when the goal is to improve an existing skill from real usage history, keep a memory of past skill runs, prepare review briefs, or ingest that history into a local Cognee setup for later search.
---

# Cognee Skill Improver

Use this skill when the user wants a loop like:

1. Use a skill
2. Record what happened
3. Find recurring friction
4. Improve the target skill

This skill is not the Cognee runtime itself. It is the workflow around Cognee that helps Codex improve other skills from usage history.

## データ保存の扱い

利用履歴をファイルに残すのは、ユーザーが履歴の保存またはこのスキルによるデータ作成を明示的に許可した場合だけにする。許可がない場合は、改善候補をチャットで要約し、ファイルを作成しない。

保存を許可された場合は、対象ワークスペース直下に次を使う。

```text
.skill-improver-data/
```

Important files:

- `.skill-improver-data/skill-runs.jsonl`
- `.skill-improver-data/reviews/<skill-name>.md`

## Workflow

### 1. Log each permitted skill run

保存許可のある実行だけを記録する。`<skill-dir>` はこの `SKILL.md` があるスキルフォルダに置き換える。

```bash
python "<skill-dir>/scripts/log_skill_run.py" --skill <skill-name> --request "<user request>" --result "<what happened>"
```

Add as many of these as possible when relevant:

- `--worked`
- `--failed`
- `--change`
- `--tags`

Do not wait for perfect notes. Short, concrete notes are better than missing data.

### 2. Build a review brief before editing a skill

Generate a deterministic review brief:

```bash
python "<skill-dir>/scripts/prepare_skill_review.py" --skill <skill-name>
```

This writes:

```text
.skill-improver-data/reviews/<skill-name>.md
```

Use that review as the main editing brief when updating the target skill's `SKILL.md`, scripts, or references.

### 3. Ingest the review into Cognee when the runtime is ready

Cogneeの実行環境、LLM設定、送信先を確認する。レビュー内容が外部のLLMやサービスへ送られる可能性がある場合は、送信前に対象データと送信先を示してユーザーの承認を得る。承認がない場合は実行しない。

実行環境と送信許可がそろった場合だけ、次を実行する。

```bash
python "<skill-dir>/scripts/ingest_review_to_cognee.py" --skill <skill-name>
```

This script:

- reads the prepared review file
- sends it to the local `.venv-cognee` runtime
- optionally runs `cognify`

Cogneeが未設定の場合は改善作業を止めない。保存許可があればローカルの記録・レビュー生成だけを行い、許可がなければチャット上のレビューで進める。

### 4. Improve the target skill

When editing the target skill:

- read the review file first
- identify repeated failures, not one-off noise
- patch the smallest part of the skill that removes the friction
- prefer improving instructions, examples, and resource scripts before adding more explanation

### 5. Close the loop

保存許可がある場合は、改善後に次を記録する。

- what was changed
- what problem it should fix
- whether the next usage actually improved

## Editing Rules

- Treat repeated failures as stronger evidence than isolated complaints
- Prefer concrete trigger wording in frontmatter descriptions
- Prefer reusable scripts or references when the same work repeats
- Do not rewrite a skill from scratch unless the review shows structural failure

## References

Read [references/review-patterns.md](./references/review-patterns.md) when deciding what should count as a real improvement signal versus noise.
