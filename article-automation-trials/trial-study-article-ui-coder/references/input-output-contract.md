# 入出力契約

## 親主導モード

`design_mode`を省略した場合は`autonomous`とし、既存の読者・検索意図・記事型・部品選定の手順を維持する。`parent_directed`では次の`ui_design`を必須とし、この設計が既存の自律的な再推定・再構成規則より優先する。

```yaml
design_mode: parent_directed
ui_design:
  article_id: ""
  design_version: 1 # 整数
  audience: ""
  search_intent: ""
  article_type: ""
  section_order: []
  component_assignments:
    - section_id: ""
      source_block: "" # 記事本文中の一意な範囲またはブロックID
      component: plain # plainは装飾しない通常本文として有効
      purpose: ""
      placement: ""
      preserve: []
  allowed_adjustments: []
```

`component_assignments`は本文のすべてのブロックを一意に割り当てる。部品を使わない本文も`plain`として明示する。`design_version`は整数とし、`section_order`、`source_block`、`component`、`purpose`、`placement`、配列の`preserve`の不足、重複、本文との不一致は子が推測で補わない。

`allowed_adjustments`には、親が許可した範囲だけを入れる。例えば、段落分け、接続文、見出し内での許可済みの部品記法への変換、可読性を損なわない余白調整である。読者、検索意図、記事型、見出し順、部品の目的・配置、保持対象を変える必要がある場合は、次を返して親の判断を待つ。

```yaml
change_request:
  design_version: ""
  affected_blocks: []
  problem: ""
  evidence: ""
  proposed_change: ""
  impact: ""
```

このとき出力状態は`needs_parent_input`とする。`parent_directed`の設計は、ファイル書込み、既存記事編集、画像生成、リンク挿入、公開の権限を追加しない。未実装部品が必要な場合は、親設計があっても`unsupported_component`を返す。

## 1. 必須入力

| フィールド | 内容 |
| --- | --- |
| `article_text` | UI化する記事本文 |
| `primary_keyword` または `article_title` | 読者・意図・記事型を判断する中心情報 |

本文がなく、全面執筆が必要な場合はこのスキルの対象外とする。

## 2. 任意入力

| フィールド | 既定・用途 |
| --- | --- |
| `audience` | 本文とキーワードから安全に推定 |
| `article_goal` | 読者理解、比較、申込み判断、実行など |
| `desired_reader_action` | 読後にしてほしい行動 |
| `output_target` | プレビューは`standalone-html`、対応Astro記事は`astro-markdown` |
| `editing_mode` | `structure-light-edit` |
| `allow_illustrative_examples` | boolean、既定`false`。新しい例え話・説明用の仮定例の追加許可 |
| `preserve_elements` | 配列、既定`[]`。対象を特定できる見出し名・位置と、維持する内容 |
| `approved_internal_links` | 公開確認済みの自サイト記事情報 |
| `approved_assets` | 使用が承認された画像・図解 |
| `approved_author_profile` | 公開用プロフィール情報 |
| `approved_citations` | 使用を承認された引用・口コミ |
| `cta_target` | 実在する遷移先とCTA目的 |
| `required_elements` | 必須の部品・内容 |
| `forbidden_elements` | 禁止する部品・表現 |
| `publication_state` | 既定はpreviewまたはdraft |

結果が大きく変わる情報だけ質問し、安全な既定値で進められる場合は止めない。

`approved_assets`は従来の承認済み入力を維持する。`parent_directed`で根拠画像を受け取る場合、親は次の2つを別入力として渡す。子はどちらも改変せず参照する。

```yaml
evidence_result: # 親の統合状態。source_phaseを含む
  schema_version: "1.3"
  status: ""
  source_phase: discover | capture
  selected_candidate_ids: []
  acceptance_evidence: []
evidence_capture: null # capture時だけ子の1.3出力全体を渡す。discoverのみならnull
approved_assets: [] # discoverが正当な無画像結果なら空配列を受理する
```

`evidence_capture`スキーマ1.3の資産を使う場合、`candidate_id`は各`assets[]`の項目、`used_design_version`と`selected_candidate_ids`は`evidence_capture`全体の項目として検証する。あわせて既存のパス・ハッシュ・権利・主張・モバイル検査を確認する。`evidence_result.source_phase: discover`で正当な無画像結果の場合は、`evidence_capture: null`と`approved_assets: []`を合法とする。1.1と1.2の既存スキーマも引き続き受理する。いずれのスキーマも、記事への画像配置権限を自動で与えない。

必須入力、既存の出力項目、編集モードは維持する。新項目なしの親スキル呼出しにも、短い太字、比較軸保全、余白確認を適用する。親スキルの改修を前提にしない。

- 「例え話も入れて」は該当範囲の補足許可へ、「この表は維持して」は維持対象へ反映する。
- `preserve_elements`の各項目は、例えば`{section: "講座比較", element: "最初の表", preserve: "列・比較軸・記載条件"}`のように対象と保持内容を示す。特定できなければ別の部分を推測して変えない。
- 空配列でも原文保全の基本規則は有効。既存の`required_elements`・`forbidden_elements`を引き続き使う。
- 最新の明示指示が以前の指示を更新した場合は範囲を記録する。解消できない必須・禁止・維持指定の競合は黙って上書きしない。
- 補足未許可なら既定の軽微編集で改善する。例え話を追加できないことだけでは停止しない。

### 強調計画と出典注記

`required_elements` の `{type: emphasis_plan, items: [...]}` は、`design_mode` にかかわらず必須の反映対象とする。各項目の `section_id`、`exact_text`、役割・理由を確認し、その章の短い `strong`（AstroではMarkdown太字または許可済みHTML）へ変換する。見出しは太字の代用にしない。

章IDは `lead`（最初のH2より前）、`H2-01`（出現順のH2と配下のH3）、`H3-01-01`（第1H2内の第1H3）とする。IDは画面用の見出しアンカーとは別で、同じ見出し文でも出現順で区別する。`heading_text` がある場合はその見出し文とも照合する。別の章、コメント、コード例にある同語句では満たさない。

明示された計画が空・不足・本文と不一致なら、親呼出しでは `needs_parent_input` と不足を返し、計画を黙って削減して合格にしない。計画がない単独利用では既存の短い太字の基準で重要語句を選び、同じ確認を行う。固定件数を埋めず、段落全体・キーワードの反復強調を避け、否定や条件を削らない。

親が記事全体で整理した出典注記は `preserve_elements` により、対象主張・出典・確認日・掲載位置を保持する。UI整形で「今回確認したところ」などの調査報告を足したり、各節へ注記を複製したりしない。適用時期・期限を確認日に置き換えない。

## 3. 承認済み入力の形

### 内部リンク

```yaml
- url: /published-path/
  title: 公開記事の正式タイトル
  description: 記事内容と一致する紹介文
  image: ./verified-image.webp
  published: true
```

`published: true`を確認できない候補、下書き、推測URLは使わない。

### 著者プロフィール

```yaml
name: 公開用著者名
role: 役割または専門領域
intro: 公開用紹介文
image: ./approved-author.webp
url: /about/
```

`name`、`role`、`intro`を必須とし、画像とURLは任意とする。入力がなければ作らない。

### 引用・口コミ

```yaml
- source_label: 出典名
  source_url: https://example.com/source
  approved_text_or_claim: 承認された引用文または要約対象
  use_mode: direct_quote
  verified_at: 2026-08-30
```

`use_mode`は`direct_quote`または`paraphrase`とする。直接引用は承認範囲を変えない。要約は引用符で囲まない。本文内に出典らしい表記があるだけでは承認済みとしない。

## 4. 出力一式

1. `coded_content`: HTMLまたはAstro Markdown
2. `component_map`: 原文ブロックと採用部品の対応
3. `validation_report`: 監査、表示幅、品質基準の結果
4. `unresolved_items`: 未確認事実、URL、画像、未対応部品
5. `change_summary`: 段落移動、接続文、無害化等の変更

`parent_directed`の出力には、さらに次を含める。

```yaml
used_design_version: 1 # 整数
design_conformance:
  result: pass | revise | needs_parent_input
  checked_assignments: []
  deviations: []
  allowed_adjustments_applied: []
```

`design_conformance.result: pass`は、全本文ブロックが指定された割当に対応し、許可範囲外の変更がない場合だけ使う。実表示や原文保全の未実施検査を`pass`にしない。

レンダリング可能ならプレビューも提示する。できない場合は理由と未確認範囲を示す。

`validation_report`には警告ごとの対応または許容理由、実表示の確認範囲、原文保全の照合結果を含める。強調は `emphasis: {markup: pass | fail | not_checked, rendered: pass | fail | not_checked, items: [{section_id, exact_text, markup, rendered}], checked_widths: []}` を含め、計画全項目を照合する。各項目の未実施を合格で埋めない。出典注記の対象・日付・配置の保持結果も原文保全へ記録する。`change_summary`では許可された補足・導出計算を、保持した原文の事実と分ける。変更理由の報告だけで数値変更を合格にしない。

## 5. 出力状態

- `ready_preview`: standaloneプレビューと検査が完了。
- `ready_draft`: 対応Astro記法の下書きと検査が完了。
- `needs_user_decision`: 入力不足で結果が大きく変わる。
- `needs_parent_input`: `parent_directed`の必須設計、またはいずれのモードでも明示された親の強調計画・保持指定が不足・矛盾している。
- `needs_verified_source`: 事実、引用、URL、画像の確認が必要。
- `unsupported_target`: 対応外の出力先。
- `unsupported_component`: 対象プロジェクトに必要部品がない。
- `design_migration_required`: 正本外のグローバルデザイン実装が必要。
- `render_unavailable`: 実表示を確認できない。

## 6. ファイルと公開

既定では応答内に返し、ファイルを書かない。新規Astro記事を承認後に作る場合は`draft: true`を既定とする。既存frontmatterは明示指示なしに変更しない。公開は別の明示承認を必要とする。
