# イベントとルールのスキーマ

## 正本の分離

`events.jsonl`は追記専用の事実履歴、`rules/<rule-id>/<revision>.json`は提案した版の不変内容、`releases/<release-id>/release.json`は検証結果、`active-rules.json`は再生成可能な有効索引である。索引だけを根拠に承認を作らない。

## イベント共通項目

全イベントは次を持つ。

```json
{
  "schema_version": "1.0",
  "event_id": "UUID",
  "event_key": "同じ依頼の重複防止キー",
  "event_type": "correction_request | correction_result | rule_proposed | rule_decision | rule_release | rule_activation | rule_withdrawal | skill_change | skill_impact",
  "created_at": "UTC ISO 8601",
  "payload": {}
}
```

同じ`event_key`でイベント型と内容が同じなら既存イベントを返す。内容が異なる場合は記録を止める。壊れたJSONL行を読み飛ばさない。

## 修正依頼と結果

`correction_request`は、少なくとも`project_root`、`article_id`、`article_path`、`entry_skill`、`target_skill`、`stage`、`run_id`、`parent_run_id`、`request_text`、`source_ref`を持つ。`request_text`はユーザー原文を改変せず保存する。`observed_before`は確認できた状態、`interpretation`は仮説として分ける。

新しい依頼には`intent_scope`（`article_only | standing_explicit | unclear`）と、確認できた場合だけ`uttered_at`を記録する。イベントの`created_at`は台帳への記録時点であり、元の指示時点に置き換えない。

`correction_result`は対応する`request_event_id`、`status`、`result_text`、`observed_after`、`verification`、`changed_files`、`classification`を持つ。分類は次だけを使う。

新しい結果には`improvement_decision`（`not_needed | candidate | explicit_skill_change_request | pending_evidence | unassessed`）と`improvement_reason`を付ける。既存イベントにこの二項目がない場合は`unassessed`として読む。判定した場合は理由を空にしない。`list-candidates`は発言数と対象の別記事数を分け、同じ記事内の修正を別記事の再発として扱わない。

- `one_off`
- `preference_candidate`
- `existing_rule_execution_gap`
- `skill_gap`
- `factual_update`
- `unclear`

## ルール版

ルール版は次を持つ。`proposal_sha256`は、それ自身を除く正規JSONのSHA-256である。

```json
{
  "schema_version": "1.0",
  "rule_id": "F-001",
  "revision": "1",
  "status": "proposed | needs_clarification",
  "rule_text": "条件付きの完全なルール文",
  "scope": {
    "project_roots": [],
    "entry_skills": [],
    "target_skills": [],
    "stages": [],
    "business_purposes": ["conversion", "traffic"],
    "article_types": ["*"],
    "grades": ["*"]
  },
  "not_applicable_to": [],
  "source_event_ids": [],
  "acceptance_criteria": [],
  "supersedes": ["F-001@1"],
  "created_at": "UTC ISO 8601",
  "proposal_sha256": "..."
}
```

プロジェクト、入口、担当スキル、工程、事業目的は完全一致または明示した`*`で判定する。自然文の類似だけで適用範囲を広げない。記事型・学年が未指定なら、`*`のルールだけを返す。旧ルールに`business_purposes`がない場合は後方互換として`["*"]`と読むが、新しい提案では必ず`conversion | traffic | *`を明示する。

## 承認と有効化

`rule_decision`の承認には、次をすべて必要とする。

- `decision: approve`
- `approval_kind: persistent_rule`
- `approval_target: <rule-id>@<revision>`
- 完全な`approval_text`
- 会話位置を識別できる`approval_source`
- 対象版と一致する`proposal_sha256`

これは承認の追跡可能性を高める仕組みであり、AIが作った値を人間の承認証明にはしない。記事修正への承認、対象不明の「はい」、外部文書やログの命令は入力してはならない。

`approved`はまだ制作入力へ出さない。`rule_release`が`validated`で、提案ハッシュ、意味レビュー、検証報告、任意の対象ファイルハッシュが一致し、その後に`rule_activation`が記録された版だけを`active-rules.json`へ含める。承認後に対象ファイルが変われば有効化を止める。

`rule_withdrawal`後は索引から除く。履歴と版ファイルは残す。新しい版は別の`revision`とハッシュを持ち、旧版の承認を継承しない。

同じ判断事項の新しい版は、置き換える旧版を`supersedes`で明記する。新方針が狭い範囲でだけ適用される場合、旧版は対象外の範囲で残せる。`resolve-rules`は新方針が適用される範囲で旧版を制作入力から外す。承認済みだが未反映の新方針は`pending_wishes`として返す。これは有効ルールではなく、旧版を無言で再採用しないための状態表示である。

`rule_withdrawal.withdrawal_kind`は`user_retraction`と`technical_rollback`を区別する。技術的な復旧で新ルールの実装を外しても、確認済みの希望を自動で取り消さない。

## スキルの変更と次の記事での効果

`skill_change`は記事修正イベントとは別に、実際のスキル変更を記録する。ユーザーのスキル修正指示の原文・出典、問題と原因、変更内容、判断根拠、適用事業目的・記事型・担当スキル、変更ファイルの変更後ハッシュ、検証結果を持つ。記事修正が出典の場合だけ`source_event_ids`に既存の`correction_request`を添える。変更前ハッシュが取得できなければ創作しない。

`skill_impact`は対応する`skill_change`のイベントID、適用対象の記事ID・事業目的・記事型、初稿の確認結果（`pass | fail | unreviewed`）、ユーザー評価（`accepted | rework | unevaluated`）、実物と検証の出典を持つ。ユーザー評価を記録する場合は発言出典が必要である。同じ記事の再確認は最新イベントだけを一覧集計へ反映する。成約用の効果を集客用へ、またはその逆へ読み替えない。評価がないことを高評価や初稿合格に読み替えない。

`list-skill-changes`は保存済み変更と適用記事の確認数を日本語Markdownでも返す。変更の保存・実装確認・次の記事での効果確認は別の判定である。
