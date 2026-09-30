# 記事制作ログ接続契約

## 対象と役割

正規プロジェクトは`C:\AIフォルダ\ブログ\site`だけである。

- `$article-production-log`: 一件ごとの詳細記録、証拠、記事別履歴、横断傾向
- `$article-skill-feedback`: 修正イベント、継続候補の提案、明示承認、検証済み有効化、撤回
- 親・子記事スキル: 記事の調査、設計、制作、検証
- プロジェクトフック: ユーザー原文と最終応答の取りこぼし防止

同じ事実を別の意味で重複生成しない。品質ログの`log_id`とフィードバック台帳の`event_id`を相互参照し、両者の状態を独自に推測しない。

## 実行コンテキスト

親は開始時に次を作り、子へ保持して渡す。

```yaml
article_log_context:
  log_root: "C:\\AIフォルダ\\.skill-improver-data\\article-quality-log"
  log_id: ""
  markdown_path: ""
  article_id: ""
  article_path: ""
  request_type: ""
  source_ref: ""
  source_hook_event_id: null
  run_id: ""
  parent_run_id: ""
  entry_skill: "cloudflare-seo-article-creator"
  target_skills: []
  quality_dimensions: []
  article_business_purpose: pending_confirmation | conversion | traffic
  business_purpose_confirmation_text: ""
  business_purpose_confirmation_source_ref: ""
  business_purpose_confirmed_by_user: false
  primary_action: affiliate_conversion | internal_conversion_article_visit | null
  feedback_request_event_id: null
```

一つのユーザー発言に一つの`log_id`を使う。複数工程にまたがる場合は`target_skills`を増やし、子ごとに別ログを作らない。ユーザーが追加の修正依頼を送った場合は新しい`log_id`を作り、同じ`run_id`と記事IDで履歴を結ぶ。

## 開始と完了

初回の新規記事指示は`request_type: initial_request`、事業目的への回答は`clarification`、変更要求は`correction`で`start-log`する。目的確認前は`article_business_purpose: pending_confirmation`、依頼文に明記済みまたは回答後は`conversion | traffic`と確認原文・出典・主要行動を保存する。原文がフックに保存済みなら`--source-hook-event-id`で関連付ける。記事ファイルがまだ存在しなければ変更前スナップショットは省略し、その事実を`observed_before`へ書く。

実物検証後に`finish-log`する。静的検査だけなら`verified`を使わず、実際の到達状態を`implemented`などで記録する。プレビュー確認後だけ`preview_ready`、本番確認後だけ`published`を使う。

`finish-log`には少なくとも次を渡す。

- 実施内容
- 観測した変更後
- 検証内容
- 変更ファイル
- 学習分類
- 品質軸ごとの問題または解消結果
- 変更しなかった範囲
- 未解決事項
- スキル修正の要否と理由。再発判定は同じ記事内の発言数ではなく、適用対象の別記事で確認する
- 目的別主要導線の`funnel_alignment`と根拠。成約用はCTA、集客用は主成約記事カードとアフィリエイト0件を分けて確認する

## フィードバック台帳との連携

修正依頼では品質ログの`start-log`後、`$article-skill-feedback`の`record-request`を行う。結果側も両方へ記録する。品質ログへ`--feedback-request-event-id`と`--feedback-result-event-id`を渡す。

`preference_candidate`または`skill_gap`でも自動提案・自動承認は行わない。今回の記事だけの指定は`one_off`と`not_needed`にする。継続意思が明示された指示、別記事での再発、または根拠のあるスキル欠陥と具体的なユーザーのスキル修正依頼は、改善案件の検討根拠にできる。記事本文の対応完了をスキル修正完了とみなさない。継続候補を作る場合、品質ログの候補文・範囲・除外条件・受入基準を人間が確認できる形にし、フィードバック台帳の`propose-rule`へ同じ`log_id`を根拠として渡す。ユーザーが対象版を明示承認し、検証・有効化されるまで制作入力へ含めない。

## フック障害時

フック未導入、未信頼、失敗でも記事スキルは`start-log`へユーザー原文を直接渡せる。rawフックIDが空でも品質ログは有効である。逆にrawフックだけが存在し、記事・品質軸・結果が関連付いていない状態を完成ログと呼ばない。
