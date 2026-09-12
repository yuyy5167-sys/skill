# 入出力契約

## 共通契約

すべてのモードで `schema_version: "1.0"` を使う。未対応のバージョンは `unsupported_schema_version` で停止する。

```yaml
schema_version: "1.0"
run_id: "現在実行を一意に識別する値"
mode: "plan | insert | audit"
site_id: "サイトの安定識別子"
allowed_internal_hosts:
  - "example.com"
current_article:
  article_key: "サイト内の安定キーまたはnull"
  wp_post_id: "WordPress投稿IDまたはnull"
  canonical_url: "正規URLまたはnull"
  planned_permalink: "公開前の予定パーマリンクまたはnull"
site_rendering_capabilities:
  affiliate_cta_component:
    supported: true
    component_id: "shinken_zemi_cta_v1"
    style_source: "現在実行で確認した共通CSSまたはコンポーネントの識別子"
```

`current_article` は `article_key`、`wp_post_id`、`canonical_url`、`planned_permalink` のいずれかで識別できなければならない。すべて欠ける場合は `current_article_identity_missing`。サイト自体を識別できない場合は `site_identity_missing` とする。

## 候補情報源と鮮度

候補一覧の正本は、実行ごとに次の優先順位で1つを選ぶ。

1. `article_management_snapshot`: 記事管理ソフトの確認済み最新スナップショット
2. `wordpress_current_readback`: 現在実行でWordPressから読み戻した一覧
3. `user_approved_list`: ユーザーが承認した候補一覧

```yaml
inventory_source:
  source_type: "article_management_snapshot | wordpress_current_readback | user_approved_list"
  verified_at: "ISO 8601日時"
  verified_in_run_id: "run_id"
  source_reference: "読み戻し元を追跡できる識別子"
```

- `verified_current: true` は、現在実行の正本で公開状態を確認できた候補だけに付ける
- 過去キャッシュだけの候補は `verified_current: false`
- 複数の正本にURL・公開状態・記事識別子の矛盾があれば `source_conflict`
- 候補情報源が必要なのに存在しない場合は `missing_link_inventory`

## `plan` 入力

```yaml
article_design:
  title: "記事タイトル"
  conclusion: "記事の結論"
  reader_questions:
    - question_id: "q1"
      text: "読者の疑問"
  sections:
    - section_id: "h2-1"
      heading: "見出し"
      purpose: "この節で解決すること"
      reader_question_ids: ["q1"]
link_inventory: [] # 任意。存在する場合だけ候補IDまで提案する
policy:
  max_new_links: 5
  max_links_per_destination: 1
```

`site_rendering_capabilities` は `plan` では省略できる。承認済みの進研ゼミCTAを `insert` する場合は必須とし、`supported: true` と `component_id: "shinken_zemi_cta_v1"` を現在実行で確認できなければ `affiliate_cta_component_missing` で停止する。

進研ゼミの記事で、タイトル・想定読者・結論・承認済み設計から対象講座を一意に確認できる場合は、`plan` 出力に次を加えられる。対象外、講座横断、または判定不能な場合は `status: "not_applicable"` とし、CTAを計画しない。

```yaml
affiliate_link_plan:
  status: "eligible | not_applicable"
  provider: "shinken_zemi"
  target_course: "elementary | junior_high | high | null"
  presentation: "cta_button | null"
  section_id: "h2-1 | null"
  rationale: "対象講座と配置文脈を一意に判断できる根拠"
```

## `plan` 出力

```yaml
result:
  status: "pass | blocked"
  unresolved_inputs: []
link_intents:
  - intent_id: "li-001"
    section_id: "h2-1"
    reader_question_id: "q1"
    purpose: "補足・比較・手順などの目的"
    destination_scope: "リンク先記事が扱うべき範囲"
    required: false
    candidate_destination_ids: []
    rationale: "読者に必要な理由"
affiliate_link_plan: null # 対象講座が一意で、読者の次の行動を案内する場合だけ出力
```

`plan` は `blocks_draft` を返さない。`blocked` の場合は `unresolved_inputs` に理由コードと必要な入力を入れ、親スキルの記事設計承認を止める。

## `insert` 入力

```yaml
body_markdown: "完成したMarkdown本文"
approved_link_intents:
  - intent_id: "li-001"
    section_id: "h2-1"
    reader_question_id: "q1"
    purpose: "リンク目的"
    destination_scope: "承認済みリンク先範囲"
    required: false
    approved_destination_id: "候補IDまたはnull"
approved_affiliate_link_plan:
  status: "eligible"
  provider: "shinken_zemi"
  target_course: "elementary | junior_high | high"
  presentation: "cta_button"
  section_id: "h2-1"
  rationale: "planで承認済みの根拠"
verified_candidates:
  - destination_id: "dest-001"
    article_key: "article-key"
    wp_post_id: 123
    site_id: "site-id"
    title: "記事タイトル"
    canonical_url: "https://example.com/path/"
    publication_status: "publish"
    verified_current: true
    verified_in_run_id: "現在のrun_id"
    summary: "記事の内容を選定できる要約"
    reader_questions: ["解決する疑問"]
    cannibalization_status: "clear"
policy:
  max_new_links: 5
  max_links_per_destination: 1
```

## `insert` 出力

```yaml
result:
  status: "pass | pass_zero_links | hold | blocked"
  blocks_draft: false
  reason_codes: []
insertions:
  - stable_key: "article_key:intent_id:destination_id"
    intent_id: "li-001"
    destination_id: "dest-001"
    section_id: "h2-1"
    placement:
      anchor_context: "本文中で一意になる短い文脈"
      operation: "before | after | replace_exact"
      occurrence: 1
    anchor_text: "説明的なアンカーテキスト"
    href: "入力で確認したURLをそのまま出力"
skipped_candidates: []
expected_link_manifest:
  existing_links: []
  new_links: []
affiliate_link_manifest:
  links: [] # 進研ゼミの承認済み講座別リンクだけ。内部リンクとは別に記録する
body_with_internal_links: "合格時の本文。blocked時は元本文と同一"
unresolved_intents: []
```

`insert` は常に `blocks_draft` を返す。

- `pass`: 内部リンクまたは承認済みアフィリエイトCTAを1件以上挿入し、必須条件を満たした
- `pass_zero_links`: 必要情報は揃っているが、挿入すべき任意の内部リンクもアフィリエイトCTAもなかった
- `hold`: 任意リンクだけを安全上見送った。理由を明示する
- `blocked`: 必須意図または入力・方針・検証に問題がある。`blocks_draft: true`

必須リンクに必要な候補一覧や承認済みリンク先が欠ける場合は `missing_link_inventory` で `blocked`。必須リンク数が `max_new_links` を超える、または同じリンク先へ複数の必須意図があり `max_links_per_destination` を満たせない場合は `policy_conflict` で `blocked` とする。

`approved_affiliate_link_plan` がない場合、または対象講座が一意でない場合、アフィリエイトリンクは追加しない。このことだけで内部リンク処理を `blocked` にしてはならない。追加する場合は1記事につき1件までとし、`affiliate_link_manifest.links` に次を記録する。

```yaml
- provider: "shinken_zemi"
  target_course: "elementary | junior_high | high"
  presentation: "cta_button"
  component_id: "shinken_zemi_cta_v1"
  href: "ユーザー提供値をそのまま使う"
  tracking_image_src: "ユーザー提供値をそのまま使う"
  rel: "nofollow"
  lead_text: "公式サイトで確認できる内容を示す短い案内文"
  button_text: "本文の文脈に合う、読者に見える具体的な案内文"
  destination_text: "リンク先が公式サイトだと明示する文"
  section_id: "h2-1"
```

HTMLソースではURL中の `&` を `&amp;` と直列化できる。`audit` ではソース文字列ではなくDOMで復元した `href` と `src` をユーザー提供値と比較し、クエリやパラメータの変更を許可しない。

## `audit` 入力

```yaml
rendered_html: "HTML化後の本文またはページHTML"
expected_link_manifest:
  existing_links: []
  new_links: []
affiliate_link_manifest:
  links: []
verified_candidates: []
rendered_page_checks:
  component_id: "shinken_zemi_cta_v1"
  widths:
    - viewport_width: 320
      page_overflow: false
      cta_overflow: false
      button_min_height_ok: true
      button_max_width_ok: true
      tracking_image_one_px: true
  console_errors: []
```

`affiliate_link_manifest.links` に `presentation: cta_button` がある場合、`rendered_page_checks` は必須であり、320・375・390・768・1280pxの5幅をすべて含める。欠落または未確認なら `affiliate_cta_render_unverified` とする。

## `audit` 出力

```yaml
result:
  status: "pass | blocked"
  blocks_draft: false
  reason_codes: []
checks:
  missing_expected_links: []
  self_links: []
  unpublished_destinations: []
  duplicate_links: []
  placeholders: []
  modified_urls: []
  modified_existing_links: []
  unauthorized_affiliate_links: []
  affiliate_link_mismatches: []
  affiliate_cta_structure_mismatches: []
  affiliate_cta_render_mismatches: []
```

不一致が1件でもあれば `status: blocked`、`blocks_draft: true` とする。

## 理由コード

次の固定コードを使用し、自由文の説明を併記する。

- `missing_link_inventory`
- `unsupported_schema_version`
- `site_identity_missing`
- `source_conflict`
- `policy_conflict`
- `unverified_url`
- `destination_not_published`
- `self_link`
- `insufficient_destination_summary`
- `current_article_identity_missing`
- `cannibalization_unresolved`
- `placement_context_not_unique`
- `body_not_ready`
- `placeholder_detected`
- `url_modified`
- `existing_link_modified`
- `affiliate_link_mismatch`
- `affiliate_cta_component_missing`
- `affiliate_cta_render_unverified`

理由コードを追加する場合は、本ファイルの契約を更新してから使用する。
