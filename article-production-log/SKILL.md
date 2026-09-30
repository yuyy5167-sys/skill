---
name: article-production-log
description: C:\AIフォルダ\ブログ\site の記事制作・修正依頼を、ユーザー原文、解釈、変更前後、検証、品質課題、改善候補まで依頼単位の詳細Markdownへ記録し、記事別履歴と横断レポートへ集約する。ブログ品質の継続改善、制作ログの作成・更新・監査に使用する。記事本文の編集、継続ルールの承認・有効化、本番公開には使用しない。
---

# ブログ記事制作ログ

## 目的

動画制作ログのように一件ごとの経緯を読める形で残しつつ、ブログ固有の品質軸で再発問題と改善候補を追跡する。保存先はブログリポジトリ外の`C:\AIフォルダ\.skill-improver-data\article-quality-log`とし、記事や公開物へログを混ぜない。

## 実行時に読むファイル

1. 新しい依頼の記録、結果追記、再描画、監査を行う前に[品質ログスキーマ](references/quality-log-schema.md)を読む。
2. 親記事スキル、担当子スキル、`$article-skill-feedback`と接続するときは[接続契約](references/integration-contract.md)を読む。

## 必須原則

- 対象は正規プロジェクト`C:\AIフォルダ\ブログ\site`の記事制作・記事修正だけとする。一般質問、スキル設計、動画制作、ブログ外の文章は記事ログへ関連付けない。
- ユーザーの各発言を一件の依頼として扱う。原文は要約や整文で置き換えず、Markdownの`ユーザー原文`へ全文保存する。
- 明示要件、AIの解釈、未確定事項、対象外を分離する。推測をユーザー指示として記録しない。
- 記録だけで作業完了、品質合格、継続ルール承認を意味しない。結果は実物確認後に追記する。
- 変更前後は可能なら正本ファイルのハッシュ付きスナップショットを保存する。巨大なビルド出力、キャッシュ、全ツール出力は保存しない。
- 品質分類は固定語彙を使う。自由記述だけで横断集計を壊さない。
- 記事への修正依頼は毎回記録する。`finish-log`では原因分類とスキル修正の要否・理由も記録する。今回だけの指定を継続ルールへ昇格させず、スキルを毎回変更しない。
- 新規記事では、事業目的の状態を`pending_confirmation | conversion | traffic`で記録する。確認済みの場合はユーザー原文、出典、`confirmed_by_user`、主要行動も保持し、AIの推測を確認済みにしない。
- `finish-log`では目的別主要導線が設計・成果物・監査で一致したかを`funnel_alignment`として記録する。成約用はアフィリエイトCTA、集客用は主成約記事カードとアフィリエイト0件を判定し、記事の結果状態や一般的な品質評価と混ぜない。
- 過去発言の発言時点と後日の記録時点を分ける。フック原文との完全一致を確認できた場合だけ`hook_verified`とし、復元した文章を原文確認済みと呼ばない。
- 旧ログは`audit-legacy`で不足・差異を調べる。確認できた原文の差異だけ`amend-legacy`で訂正追記し、保存済みの原文や当時の検証記録を上書きしない。証拠のない日時・成功判定を補完しない。
- 継続候補は候補として残すだけにする。提案、明示承認、検証済み有効化、撤回は`$article-skill-feedback`を正本とする。
- ログ保存に失敗した場合は保存済みと報告しない。記事作業を安全に続行できる場合は続け、最終報告に未記録の範囲と再実行条件を含める。

## 標準手順

1. 作業前に`start-log`を実行し、`log_id`と詳細Markdownのパスを取得する。初回指示も修正依頼も記録対象である。
2. `--explicit-requirement`、`--inferred-requirement`、`--unknown`、`--exclusion`を分け、記事、URL、公開境界、変更範囲を`--context`へ入れる。
   新規記事では`--article-business-purpose`を必須とし、確認前は`pending_confirmation`、確認後は`conversion | traffic`と確認原文・出典を渡す。
3. 正本記事が存在する場合は`--snapshot-before`で変更前を保存する。
4. 実装・検証後に`finish-log`を実行する。変更ファイル、観測後、検証、品質課題、分類、`--improvement-decision`と理由、改善候補を記録し、必要なら`--snapshot-after`を付ける。
5. ユーザーが継続ルールを明示承認した場合だけ`record-decision`へ記録し、同じ承認を`$article-skill-feedback`の対象版へ結び付ける。
6. `verify-store`で整合性を確認する。依頼の出典一覧が分かる場合は`audit-requests`へ期待する`source_ref`を渡し、未記録・未完了・スキル判定未実施を確認する。レポートは各更新時に再生成される。
7. 過去の品質ログを使ってスキルを改めるときは`audit-legacy --article-id`で原文出典、問題分解、改善判定、変更証拠の不足を先に調べる。表示されたユーザー発言またはrawフックで差異が確かめられた箇所だけ`amend-legacy`へ抜粋・参照元・理由を渡す。監査で要確認のままの事項は修正根拠に昇格させない。

## コマンド

```powershell
python "C:\Users\yuyy2\.codex\skills\article-production-log\scripts\article_production_log.py" start-log `
  --root "C:\AIフォルダ\.skill-improver-data\article-quality-log" `
  --project-root "C:\AIフォルダ\ブログ\site" `
  --article-id "example-slug" `
  --article-path "C:\AIフォルダ\ブログ\site\src\content\blog\example.md" `
  --request-type "correction" `
  --request-text "ユーザー原文" `
  --source-ref "current-thread:turn" `
  --entry-skill "cloudflare-seo-article-creator" `
  --target-skill "readable-article-style" `
  --stage "writing" `
  --run-id "UUID" `
  --quality-dimension "readability" `
  --article-business-purpose "conversion" `
  --business-purpose-confirmation-text "成約用の記事です" `
  --business-purpose-confirmation-source-ref "current-thread:turn" `
  --business-purpose-confirmed-by-user `
  --snapshot-before
```

```powershell
python "C:\Users\yuyy2\.codex\skills\article-production-log\scripts\article_production_log.py" finish-log `
  --root "C:\AIフォルダ\.skill-improver-data\article-quality-log" `
  --log-id "UUID" `
  --status "verified" `
  --result-text "実施結果" `
  --observed-after "実物で確認した状態" `
  --verification "検証内容" `
  --classification "skill_gap" `
  --improvement-decision "candidate" `
  --improvement-reason "既存手順では今回の要求を扱えず、再利用できる変更が必要" `
  --funnel-alignment "pass" `
  --funnel-alignment-reason "成約用の承認済みCTAを挿入・監査した" `
  --changed-file "絶対パス" `
  --snapshot-after
```

`hook-event`はプロジェクトフック専用で、標準入力のJSONからユーザー原文または最終応答を取りこぼし防止用のrawイベントへ保存する。rawイベントは記事ログへ自動昇格しない。

旧ログの監査は`audit-legacy --root <ログ保存先> --article-id <記事ID>`を使う。原文差異を確認した場合の追記は`amend-legacy --root <ログ保存先> --log-id <ID> --original-excerpt <保存済み抜粋> --corrected-excerpt <確認した原文抜粋> --source-ref <発言の参照> --source-provenance visible_user_message --reason <訂正理由> --event-key <一意キー>`を使う。`raw_hook_verified`では`--source-ref`へ対応するrawフックのイベントIDを渡し、訂正後の抜粋との一致を検査する。`--event-key`は再実行で同じ訂正を二重登録しないため必須である。

## 完了条件

- 対象依頼に対応する`userLog/*.md`が存在し、ユーザー原文、対象、解釈、変更前、変更内容、変更後、検証、品質分類、改善候補、未解決事項を区別して読める。
- `records/<log_id>.json`、`events.jsonl`、記事別履歴、4種類の横断レポートの参照が一致する。
- `verify-store`が`ok: true`である。
- `audit-requests`が対象実行で示す未記録・未判定を見落としていない。期待出典を提示できない場合は漏れなしと断言しない。
- 継続候補が自動で有効ルールへ変換されていない。
