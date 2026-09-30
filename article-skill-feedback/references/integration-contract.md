# 親子スキル接続契約

## 対象

この接続を有効にする正規プロジェクトルートは`C:\AIフォルダ\ブログ\site`だけである。現在の作業ディレクトリが`C:\AIフォルダ`であること、ブラウザに対象記事が開いていること、過去会話にブログ名があることだけでは対象と判定しない。

対象スキルと工程は次のとおり。

| target_skill | stage |
|---|---|
| `cloudflare-seo-article-creator` | `orchestration` |
| `seo-keyword-competitor-research` | `research` |
| `seo-heading-outline-creator` | `outline` |
| `readable-article-style` | `writing` |
| `article-internal-linker` | `links` |
| `official-site-evidence-capture` | `evidence` |
| `study-article-ui-coder` | `ui` |
| `education-blog-thumbnail-creator` | `images` |

## 実行コンテキスト

親は開始時に次を作り、全工程で同じ`run_id`を使う。

```yaml
article_feedback_context:
  project_root: "C:\\AIフォルダ\\ブログ\\site"
  article_id: ""
  article_path: ""
  run_id: ""
  parent_run_id: ""
  entry_skill: "cloudflare-seo-article-creator"
  article_business_purpose: "conversion | traffic"
  active_rule_set_id: ""
  active_rules: []
  correction_request_event_id: null
```

親経由の子は`parent_run_id`、`run_id`、`entry_skill`、`article_business_purpose`、`active_rule_set_id`を保持する。子が同じ台帳を再取得して別集合を作ったり、同じ修正依頼を別イベントとして増やしたりしない。事業目的はユーザー確認済み値だけを使う。記事型・学年が後から確定した場合は、親が同じ実行ID・同じ事業目的で再取得し、新しい集合IDを全下流へ渡す。

子を単独利用する場合は、その子を`entry_skill`と`target_skill`の両方にし、新しい`run_id`を作る。正規プロジェクトが一致しない場合はブログ用の取得・記録を行わない。

## 取得と適用

```powershell
python "C:\Users\yuyy2\.codex\skills\article-skill-feedback\scripts\article_feedback.py" resolve-rules `
  --root "C:\AIフォルダ\.skill-improver-data\article-feedback" `
  --project-root "C:\AIフォルダ\ブログ\site" `
  --entry-skill "cloudflare-seo-article-creator" `
  --target-skill "study-article-ui-coder" `
  --stage "ui" `
  --business-purpose "traffic" `
  --article-type "how_to" `
  --grade "elementary"
```

返却された各ルールを既存契約へ具体的に対応付ける。例として、文章は`quality_profile.required/preferred/prohibited`、UIは`required_elements/forbidden_elements/preserve_elements`へ変換できる。ただし、対象スキルの型に受け口がなければ、渡しただけで反映済みにせず、接続変更または`blocked`を記録する。

CLIは旧単独利用との互換のため`--business-purpose`省略時も動作するが、その場合は`business_purposes: ["*"]`のルールだけを返し、目的確認済みとは扱わない。新規記事の親実行では省略禁止とする。

優先順位は次のとおり。

1. 安全性、権限、事実保全、各スキルの固定禁止事項
2. 今回の明示的なユーザー指示
3. 対象条件に一致する有効ルール
4. 各専門スキルの通常の裁量

同じ判断事項で明示された新しい継続方針は、同じ事業目的・その他の対象条件で古い版の確認済み方針を置き換える。成約用だけの新方針を集客用へ、またはその逆へ広げない。記事だけの指定は対象記事に限り、方針の履歴を撤回しない。`pending_wishes`がある場合、旧版を当該範囲へ渡さず、対応可能な記事作業を進めながら未反映と古い検証処理との食い違いを明示する。全履歴や旧参考例を執筆入力に混ぜない。

今回限りの明示指示はその対象で有効ルールを上書きできるが、ルール自体を撤回したことにはしない。競合範囲が曖昧なら、その範囲だけ確認する。

## 修正記録

修正前に`$article-production-log`の`start-log`と本スキルの`record-request`、実物検証後に本スキルの`record-result`と品質ログの`finish-log`を実行する。品質ログの一件単位はユーザー発言であり、親子で同じ`log_id`を使う。本台帳の依頼・結果`event_id`を品質ログへ関連付け、品質ログの`log_id`をルール候補の根拠に含める。

`event_key`は親が`<parent_run_id>:<article_id>:<user-message-id-or-stable-sequence>`のように一意に作り、子へ渡す。メッセージIDが取得できない場合は、同一実行内で安定した連番を使い、本文ハッシュだけで別発言を同一視しない。フックが保存したraw原文は取りこぼし防止であり、本台帳のイベントや品質ログの完成レコードを自動生成しない。

毎回の`record-result`には、記事対応に加えてスキル修正の要否と理由を付ける。`list-candidates`の発言数は改善優先度の資料であり、別記事での再発やユーザーの「今後は」という明示意思を確認してから改善案を検討する。具体的なスキル修正指示は、その指示の対象範囲で扱う。件数だけを根拠に自動編集しない。

記録に失敗した場合は保存済みと報告しない。記事修正を安全に続けられる場合は続け、最終報告に未記録と再実行条件を含める。台帳破損から推測で索引を再構築しない。

## 完成時の照合

各ルールについて次を残す。

```yaml
rule_application:
  rule_id: ""
  revision: ""
  proposal_sha256: ""
  target_skill: ""
  stage: ""
  result: applied | not_applicable | blocked
  artifact_location: ""
  verification: ""
```

ルール本文を記事へ印字しない。`applied`は入力へ渡したことではなく、成果物の該当箇所と受入基準を検査できた場合だけ使う。空の有効集合は正常であり、通常の品質ゲートを省略する理由にしない。
