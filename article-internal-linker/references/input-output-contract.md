# 入出力契約

## 共通契約

新しい実行はすべてのモードで `schema_version: "1.2"` を使う。旧1.0・1.1は履歴の読取りだけに使い、1.1の通常1件CTAを新しい`plan | insert | audit`の完成入力にはしない。未対応のバージョンは `unsupported_schema_version` で停止する。

```yaml
schema_version: "1.2"
run_id: "現在実行を一意に識別する値"
mode: "plan | insert | audit"
article_business_purpose: "conversion | traffic"
site_id: "サイトの安定識別子"
allowed_internal_hosts:
  - "example.com"
current_article:
  article_key: "サイト内の安定キーまたはnull"
  wp_post_id: "WordPress投稿IDまたはnull"
  canonical_url: "正規URLまたはnull"
  planned_permalink: "公開前の予定パーマリンクまたはnull"
site_rendering_capabilities:
  internal_link_card:
    supported: true
    resolves_destination_cover_image: true
    style_source: "現在実行で確認した内部リンクカード変換と共通CSSの識別子"
  affiliate_cta_component:
    supported: true
    component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1"
    style_source: "現在実行で確認した共通CSSまたはコンポーネントの識別子"
  affiliate_cta_components: [] # 複数プロバイダーが明示された記事では各provider・component_id・supported・style_sourceを記録
```

`article_business_purpose`は親がユーザー確認済みの値を渡す。欠落・未確認・その他の値は`business_purpose_unconfirmed`とする。`current_article` は `article_key`、`wp_post_id`、`canonical_url`、`planned_permalink` のいずれかで識別できなければならない。すべて欠ける場合は `current_article_identity_missing`。サイト自体を識別できない場合は `site_identity_missing` とする。

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
  article_profile: "conversion_review_price | conversion_other | traffic"
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
  max_image_cards: 2
cta_strategy:
  default_count: 3
  planned_count: 3
  count_mode: "standard | decreased | increased | explicit_override | not_applicable"
  count_reason: "標準3件を採用または増減した理由"
  explicit_user_count_override: null
  official_confirmation_moments:
    - placement_id: "CTA-01"
      reader_question: "この位置で読者が確認したいこと"
      official_information_needed: "公式側で確認すべき内容"
      section_id: "h2-1"
      section_heading: "実際のH2見出し"
      destination_purpose: "公式遷移の目的"
      lead_copy: "本文に合う固有の案内文"
```

`site_rendering_capabilities` は `plan` では省略できる。`image_card`を`insert`する場合は`internal_link_card.supported: true`とリンク先画像を解決できることを、承認済みの講座別CTAを`insert`する場合はプロバイダーに対応する`supported: true`と`component_id`（進研ゼミは`shinken_zemi_cta_v1`、スマイルゼミは`smile_zemi_cta_v1`）を現在実行で確認する。確認できなければ、それぞれ`internal_link_card_component_missing`または`affiliate_cta_component_missing`で停止する。成約直結記事をカード非対応のため`text_link`へ変更してはならない。

`conversion`で進研ゼミまたはスマイルゼミの記事を扱い、タイトル・想定読者・結論・承認済み設計から対象講座を一意に確認できる場合は、`plan` 出力に次を加える。`cta_strategy.default_count`は3だが固定件数ではなく、`planned_count`は独立した公式確認場面の数と一致させる。対象講座、承認済みURL、各配置の意味と自然な配置章を確定できなければ`conversion_affiliate_unresolved`で停止する。`traffic`は常に`status: "not_applicable"`、`planned_count: 0`とし、CTAを計画しない。

```yaml
affiliate_link_plan:
  status: "eligible | not_applicable"
  provider: "shinken_zemi | smile_zemi"
  target_course: "preschool | elementary | junior_high | high | null"
  presentation: "cta_button | null"
  planned_count: 3
  rationale: "対象講座と件数を判断した根拠"
  placements:
    - placement_id: "CTA-01"
      provider: "shinken_zemi | smile_zemi"
      target_course: "preschool | elementary | junior_high | high"
      section_id: "h2-1"
      section_heading: "実際のH2見出し"
      reader_question: "読者の疑問"
      official_information_needed: "公式側で確認すべき内容"
      destination_purpose: "公式遷移の目的"
      lead_copy: "固有の案内文"
      rationale: "この場面に置く根拠"
```

## `plan` 出力

成約用のCTAは件数にかかわらず`affiliate_link_plan.placements`へ全配置を列挙し、各プロバイダーの対象講座を一意に確認する。`planned_count`、`cta_strategy.official_confirmation_moments`、`placements`の件数と`placement_id`を一致させる。複数のプロバイダーを含む`insert`では`site_rendering_capabilities.affiliate_cta_components`に各共通部品の現在確認結果を入れる。

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
    destination_role: "related_support | conversion_direct"
    presentation: "text_link | image_card"
    required: false
    primary_destination: false
    candidate_destination_ids: []
    rationale: "読者に必要な理由"
affiliate_link_plan: null # 成約用で対象講座と全CTA配置を一意に確定できた場合だけ出力
```

`plan` は `blocks_draft` を返さない。`blocked` の場合は `unresolved_inputs` に理由コードと必要な入力を入れ、親スキルの記事設計承認を止める。

`destination_role`は確認済みのリンク先記事の役割で決める。記事管理情報、対応する制作ログ、またはユーザー承認済み一覧で成約用と確認できた記事は`conversion_direct`かつ`image_card`、それ以外の関連記事は`related_support`かつ`text_link`とする。タイトル・キーワード・トピックだけで成約用と推測しない。画像付きカードは記事全体で最大2件とし、3件目以降の`conversion_direct`候補は関連性の高い2件へ絞る。件数に応じて`text_link`へ変更しない。

`traffic`では主成約記事の意図を1件だけ`required: true`、`primary_destination: true`にする。適格な公開済み成約用記事がなければ`primary_conversion_destination_missing`で`blocked`にする。`conversion`の内部リンクは補助導線であり、ユーザーの明示指定がない限り`primary_destination: true`を使わない。

## `insert` 入力

```yaml
body_markdown: "完成したMarkdown本文"
approved_link_intents:
  - intent_id: "li-001"
    section_id: "h2-1"
    reader_question_id: "q1"
    purpose: "リンク目的"
    destination_scope: "承認済みリンク先範囲"
    destination_role: "related_support | conversion_direct"
    presentation: "text_link | image_card"
    required: false
    primary_destination: false
    approved_destination_id: "候補IDまたはnull"
approved_affiliate_link_plan:
  status: "eligible"
  provider: "shinken_zemi | smile_zemi"
  target_course: "preschool | elementary | junior_high | high"
  presentation: "cta_button"
  planned_count: 3
  rationale: "planで承認済みの講座・件数根拠"
  placements: [] # 件数にかかわらず承認済みの全配置と意味情報を列挙する
cta_strategy:
  default_count: 3
  planned_count: 3
  count_mode: "standard | decreased | increased | explicit_override"
  count_reason: "採用件数の理由"
  official_confirmation_moments: [] # planned_countと同数の承認済み配置を渡す
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
    destination_role: "related_support | conversion_direct"
    destination_business_purpose: "conversion | traffic | unknown"
    business_purpose_evidence_type: "article_management_snapshot | production_log | user_approved_list | unknown"
    business_purpose_evidence_ref: "追跡可能な参照"
    cannibalization_status: "clear"
policy:
  max_new_links: 5
  max_links_per_destination: 1
  max_image_cards: 2
```

## `insert` 出力

CTAは3件を標準値として検討するが固定せず、承認済み`cta_strategy.planned_count`と全`placement_id`・プロバイダー・講座・セクション・意味情報をマニフェストの全件と一致させる。既存CTAが同じ配置を満たす場合は再挿入しない。同じURLを使う別セクションは、各配置の公式確認目的が独立し、案内文と前後文脈が異なる場合だけ重複ではない。件数合わせの反復は`cta_placement_repetition`で停止する。

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
    destination_role: "related_support | conversion_direct"
    presentation: "text_link | image_card"
    placement:
      anchor_context: "本文中で一意になる短い文脈"
      operation: "before | after | replace_exact"
      occurrence: 1
    anchor_text: "text_linkの場合の説明的なアンカーテキスト。image_cardではnull"
    card_description: "image_cardの場合の紹介文。text_linkではnull"
    href: "入力で確認したURLをそのまま出力"
skipped_candidates: []
expected_link_manifest:
  existing_links: []
  new_links: [] # destination_roleとpresentationを含める
affiliate_link_manifest:
  links: [] # 進研ゼミまたはスマイルゼミの承認済み講座別リンクだけ。内部リンクとは別に記録する
body_with_internal_links: "合格時の本文。blocked時は元本文と同一"
unresolved_intents: []
```

`insert` は常に `blocks_draft` を返す。

- `pass`: 目的別主要導線を満たした。`conversion`では承認済みCTA、`traffic`では主成約記事画像カードがあり、必要な内部リンクも挿入した
- `pass_zero_links`: 挿入すべき任意の内部リンクは0件だが、成約用CTAまたは集客用主成約記事カードの目的別主要導線は契約どおり満たした
- `hold`: 任意リンクだけを安全上見送った。理由を明示する
- `blocked`: 必須意図または入力・方針・検証に問題がある。`blocks_draft: true`

必須リンクに必要な候補一覧や承認済みリンク先が欠ける場合は `missing_link_inventory` で `blocked`。必須リンク数が `max_new_links` を超える、または同じリンク先へ複数の必須意図があり `max_links_per_destination` を満たせない場合は `policy_conflict` で `blocked` とする。

`insert`は`approved_link_intents`と`verified_candidates`の`destination_role`が一致することを確認し、`related_support`は本文中の語句へ設定するMarkdownテキストリンク、`conversion_direct`はサイト既定の画像付き内部リンクカード記法として挿入する。`expected_link_manifest.new_links`には`destination_role`と`presentation`を記録する。`image_card`が2件を超える場合は`image_card_limit_reached`で停止し、テキストリンクへの変更で回避しない。

`conversion`では`approved_affiliate_link_plan.status: eligible`を必須とする。対象講座、承認済みURL、`cta_strategy`、自然な全配置章、共通部品のいずれかが欠ける場合は`conversion_affiliate_unresolved`で停止する。`planned_count`と計画の全配置に従い、`affiliate_link_manifest.links` に次を記録する。

```yaml
- provider: "shinken_zemi | smile_zemi"
  placement_id: "承認済み配置の一意なID。件数にかかわらず必須"
  target_course: "preschool | elementary | junior_high | high"
  presentation: "cta_button"
  component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1"
  href: "ユーザー提供値をそのまま使う"
  tracking_image_src: "ユーザー提供値をそのまま使う"
  rel: "nofollow"
  lead_text: "公式サイトで確認できる内容を示す短い案内文"
  button_text: "本文の文脈に合う、読者に見える具体的な案内文"
  destination_text: "リンク先が公式サイトだと明示する文"
  section_id: "h2-1"
  section_heading: "配置先H2の実際の見出し文字列"
  reader_question: "この位置で読者が確認したいこと"
  official_information_needed: "公式側で確認すべき内容"
  destination_purpose: "公式遷移の目的"
```

各`lead_text`は対応する`lead_copy`を保持し、別配置と同一または実質同義にしない。各CTAは該当セクションの説明後に置き、連続したCTAブロックや隣接段落への配置を避ける。本文が確認理由を説明していない場合は、CTAだけで補わず記事本文の設計へ戻す。

HTMLソースではURL中の `&` を `&amp;` と直列化できる。`audit` ではソース文字列ではなくDOMで復元した `href` と `src` をユーザー提供値と比較し、クエリやパラメータの変更を許可しない。

`traffic`では`approved_affiliate_link_plan.status: not_applicable`とし、`affiliate_link_manifest.links: []`を返す。CTA、計測画像、ASP URLが入力本文に既にある場合も自動削除せず`traffic_affiliate_contamination`で停止する。主成約記事カードが挿入後本文と`expected_link_manifest.new_links`に1件なければ`primary_conversion_card_missing`で停止する。

## `audit` 入力

CTA件数にかかわらず、各`placement_id`の固定DOM、URL、計測画像、対象講座、セクション、固有の案内文を確認し、`cta_strategy.planned_count`、公式確認場面、マニフェスト、実CTAの件数が一致することを確認する。

```yaml
rendered_html: "HTML化後の本文またはページHTML"
article_business_purpose: "conversion | traffic"
cta_strategy: {}
expected_link_manifest:
  existing_links: []
  new_links: []
affiliate_link_manifest:
  links: []
verified_candidates: []
rendered_page_checks:
  component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1"
  internal_link_cards:
    actual_count: 0
    images_loaded: true
    presentation_matches_manifest: true
  widths:
    - viewport_width: 320
      page_overflow: false
      cta_overflow: false
      button_min_height_ok: true
      button_max_width_ok: true
      tracking_image_one_px: true
  console_errors: []
```

`affiliate_link_manifest.links` に `presentation: cta_button` がある場合、`rendered_page_checks` は必須であり、320・375・390・768・1280pxの5幅をすべて含める。欠落または未確認なら `affiliate_cta_render_unverified` とする。`expected_link_manifest.new_links`に`image_card`がある場合は、実カード数が期待件数と一致して2件以下であること、各カードに画像・正式タイトル・紹介文があり、画像が読み込まれ、表示形式がマニフェストと一致することも記録する。

`traffic`では、CTA固定クラス、アフィリエイトリンク、計測画像URLが0件であること、`required: true`かつ`primary_destination: true`の`conversion_direct`画像カードが1件存在し、画像・正式タイトル・紹介文が表示されることを必須監査にする。

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
  internal_link_presentation_mismatches: []
  image_card_limit_exceeded: false
  image_card_render_mismatches: []
  unauthorized_affiliate_links: []
  affiliate_link_mismatches: []
  affiliate_cta_structure_mismatches: []
  affiliate_cta_render_mismatches: []
  cta_strategy_mismatches: []
  cta_context_mismatches: []
  cta_repetition_mismatches: []
```

不一致が1件でもあれば `status: blocked`、`blocks_draft: true` とする。

## 理由コード

次の固定コードを使用し、自由文の説明を併記する。

- `missing_link_inventory`
- `business_purpose_unconfirmed`
- `conversion_affiliate_unresolved`
- `primary_conversion_destination_missing`
- `primary_conversion_card_missing`
- `traffic_affiliate_contamination`
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
- `cta_strategy_mismatch`
- `cta_context_mismatch`
- `cta_placement_repetition`
- `cta_spacing_conflict`
- `internal_link_card_component_missing`
- `internal_link_presentation_mismatch`
- `image_card_limit_reached`

理由コードを追加する場合は、本ファイルの契約を更新してから使用する。
