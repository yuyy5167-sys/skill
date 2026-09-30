# 品質ログスキーマ

## 保存構成

```text
article-quality-log/
├─ meta.json
├─ events.jsonl
├─ records/<log-id>.json
├─ userLog/YYYY-MM-DD_<article>_<issue>_<short-id>.md
├─ artifacts/<log-id>/before|after/
├─ articles/<article-id>/制作履歴.md
├─ reports/品質傾向.md
├─ reports/再発問題.md
├─ reports/スキル別問題.md
├─ reports/継続ルール候補.md
└─ raw/hooks/<session-id>/
```

`records`が依頼単位の構造化正本、`userLog`が人間向け表示、`events.jsonl`が追記専用の操作履歴である。記事別履歴とレポートは`records`から再生成できる派生物とする。

## 依頼レコード

レコードは次の情報群を持つ。

- 識別: `schema_version`、`log_id`、作成・更新日時、状態
- 対象: `project_root`、`article_id`、`article_path`、依頼種別、`article_business_purpose`。目的は`pending_confirmation | conversion | traffic`で、確認原文・出典・`confirmed_by_user`・主要行動を分離する
- 出典: `source_ref`、セッション・ターン、rawフックID
- 出典の時点と確度: `uttered_at`（不明なら空）、`provenance`（direct / hook_verified / reconstructed / unverified）。`created_at`は保存時点であり、過去発言の時点へ転用しない
- 実行経路: `entry_skill`、`target_skills`、`stage`、`run_id`、`parent_run_id`
- 依頼: ユーザー原文、文脈、明示要件、AI解釈、未確定、対象外、観測した変更前
- 品質: 品質軸、問題、原因、優先度、確度、担当工程
- 証拠: 変更前後スナップショット、変更ファイル、検証
- 結果: 状態、実施内容、観測した変更後、`funnel_alignment`（pass / fail / not_applicable / unassessed）と根拠
- 学習: 分類、再発キー、継続候補、適用範囲、除外条件、受入基準
- スキル判定: `improvement_decision`（not_needed / candidate / explicit_skill_change_request / pending_evidence / unassessed）と具体的な理由。記事の結果状態と別に管理する
- 連携: `article-skill-feedback`の依頼・結果イベントID
- ユーザー判断: 明示した判断原文、出典、日時

## 固定語彙

品質軸は次だけを使う。

- `search_intent`: 検索意図と読者の主質問
- `facts_freshness`: 事実、料金、制度、日付、出典
- `structure`: タイトル、導入、見出し、結論、情報順序
- `readability`: 分かりやすさ、文章の自然さ、冗長さ
- `audience`: 学年、保護者・本人、前提知識
- `comparison`: 比較条件、評価軸、公平性
- `cta`: 講座一致、文脈、表現、導線
- `internal_links`: URL、役割、配置、表示形式
- `ui_mobile`: 装飾、レスポンシブ、実表示
- `images`: 内容整合、権利、配置、モバイル表示
- `publication_boundary`: draft、preview、production、公開権限
- `article_identity`: 既存URL、slug、対象記事、保持記事
- `workflow`: 調査、設計、制作、検証、記録の工程

依頼種別は`initial_request | correction | review | clarification | approval | stop | resume`とする。結果状態は`open | in_progress | blocked | implemented | verified | preview_ready | published | stopped | superseded`とする。

学習分類は`one_off | preference_candidate | existing_rule_execution_gap | skill_gap | factual_update | unclear`とし、`$article-skill-feedback`と一致させる。

## Markdownの必須章

1. 概要
2. ユーザー原文
3. 記事の事業目的
4. 依頼時の文脈
5. 要求の分解
6. 品質課題
7. 変更前
8. 実施内容
9. 変更しなかった範囲
10. 変更後
11. 品質検証
12. 目的別導線の整合
13. 学習分類
14. 継続ルール候補
15. ユーザー判断
16. 未解決事項
17. 関連情報

新形式の記録では「スキル修正の判定」を「学習分類」と「継続ルール候補」の間に表示する。旧形式のMarkdownは記録の再描画によって勝手に書き換えない。

旧ログで保存済み原文と確認したユーザー発言に差異がある場合は、`legacy_amendment`イベントと`amendments`配列へ訂正前後の抜粋、参照元、取得方法、理由を追記する。`request.verbatim`は当時の保存値のまま残し、訂正のあるレコードだけ「過去ログの訂正」を表示する。訂正により未確認の日時、品質検証、改善判定まで確認済みにしてはならない。

空欄は章を消さず`記録なし`と表示し、未観測と問題なしを混同しない。

## 証拠と個人情報

- ユーザー原文は正確性を優先して保存するが、ログ共有時は記事制作に不要な秘密情報を別途確認する。
- ファイル証拠はSHA-256、元パス、保存パス、取得日時を持つ。
- rawフックはユーザープロンプトと最終応答だけを保存し、ツール出力やビルド全体を複製しない。トランスクリプトはパスとハッシュだけを記録する。
- rawフックは漏れ防止であり、品質分類の正本ではない。対象記事へ関連付けられた依頼だけを`records`へ昇格する。
- `hook_verified`には対応するrawユーザー原文と依頼原文の完全一致が必要である。`verify-store`は保存内容の整合を確認し、依頼の取りこぼしは期待出典を指定した`audit-requests`で確認する。期待出典自体が不足する場合、全件保存を保証しない。

## 継続候補

候補は完全なルール文、適用プロジェクト、入口・担当スキル、工程、事業目的、記事種別・学年、除外条件、受入基準、根拠ログIDを持つ。類似して見えるだけで適用範囲を広げず、成約用と集客用を無条件に同じルールへしない。ユーザーの明示承認がなければ`candidate`のままにし、記事制作入力へ渡さない。
