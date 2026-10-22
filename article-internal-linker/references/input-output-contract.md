# 入出力契約

## 共通契約

新しい実行はschema_version: "1.3"を使い、[共通配置方針](affiliate-placement-policy.md)を適用する。旧1.0〜1.2は履歴の読取り専用で、新しい完成入力として受理しない。

```yaml
schema_version: "1.3"
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
    component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1 | zkai_cta_v1 | study_sapuri_cta_v1"
    style_source: "現在実行で確認した共通CSSまたはコンポーネントの識別子"
  affiliate_cta_components: [] # 複数プロバイダーが明示された記事では各provider・component_id・supported・style_sourceを記録
```

`article_business_purpose`は親がユーザー確認済みの値を渡す。欠落・未確認・その他の値は`business_purpose_unconfirmed`とする。`current_article` は `article_key`、`wp_post_id`、`canonical_url`、`planned_permalink` のいずれかで識別できなければならない。すべて欠ける場合は `current_article_identity_missing`。サイト自体を識別できない場合は `site_identity_missing` とする。

## 記事デザインの条件付き追加契約

schema 1.3に次の任意項目を追加する。旧profile未指定入力の従来契約は維持するが、対象ブログの今後の新規記事を親から受け取る場合は `articleDesign` を必須とする。未知のprofile、A〜E以外、空ラベル、未知の設定項目、非booleanの末尾表示指定は `article_design_profile_unconfirmed` で停止し、既定表示へ退避しない。

```yaml
articleDesign:
  profile: "cream-manga-mustard-v1"
  design: "A | B | C | D | E"
  label: "空でない記事種別ラベル"
  showMaterialFinder: false # 省略時false。CTA件数や事業目的の根拠にしない
site_rendering_capabilities:
  article_design_profile:
    profile: "cream-manga-mustard-v1"
    supported: true
    verified_in_run_id: "現在のrun_id"
    style_source: "現在実行で確認したprofile解決処理と共通CSSの識別子"
    scoped_to_profile: true
    scope_selector: '.article-edition[data-article-profile="cream-manga-mustard-v1"][data-article-design-origin="frontmatter"]'
  affiliate_cta_component:
    supported: true
    component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1 | zkai_cta_v1 | study_sapuri_cta_v1"
    style_source: "現在実行で確認した共通CSSの識別子"
    appearance_profiles: ["cream-manga-mustard-v1"]
  affiliate_cta_components: [] # 複数providerでは各項目へ同じappearance_profiles確認を持たせる
```

対象・profileの解決・外観・監査は [教育ブログ用CTA外観プロファイル](article-design-profile.md)を正本とする。親/UI用 `site_rendering_capabilities.article_design` と、このリンク表示専用 `article_design_profile` は併存し、確認を代用しない。

`plan`では `articleDesign` を引き継ぎ、実装確認が未了でも外観指定を記録できる。`insert`前には使用するCTA/カードのprofile対応を現在実行で確認し、欠落なら `article_design_profile_component_missing` で元本文を保持して停止する。plan時点の予定や過去の確認だけでtrueを付けない。共通CSSを本スキルで新規実装する権限は追加しない。

`articleDesign` のどの値も `article_business_purpose`、対象講座、`cta_strategy.planned_count` の確認の代替にはしない。以降のURL、計測、属性、固定DOM、配置・件数、意味・案内文、集客用主成約記事カードの契約を維持する。

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
  policy_version: "minimum-two-v1"
  default_count: 3
  planned_count: 3
  count_mode: "standard | decreased | increased | explicit_override"
  count_reason: "目的別標準（traffic=2/conversion=3）から採用件数を決めた理由"
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

`site_rendering_capabilities` は `plan` では省略できる。外観profileを指定した記事の`insert`では、上記の条件付き追加契約も必須とする。`image_card`を`insert`する場合は`internal_link_card.supported: true`とリンク先画像を解決できることを、承認済みの講座別CTAを`insert`する場合はプロバイダーに対応する`supported: true`と`component_id`（進研ゼミは`shinken_zemi_cta_v1`、スマイルゼミは`smile_zemi_cta_v1`、Z会は専用契約の`zkai_cta_v1`）を現在実行で確認する。確認できなければ、それぞれ`internal_link_card_component_missing`または`affiliate_cta_component_missing`で停止する。成約直結記事をカード非対応のため`text_link`へ変更してはならない。

両事業目的で対応広告主の承認済みURL・対象講座・最低2つの自然な配置を確認し、eligibleなaffiliate_link_planを返す。集客用default_count=2、成約用=3。未確認ならaffiliate_unresolvedでblocked。

```yaml
affiliate_link_plan:
  status: "eligible | not_applicable"
  provider: "shinken_zemi | smile_zemi | zkai | study_sapuri"
  target_course: "preschool | elementary | junior_high | high | elementary_junior | toeic_basic | null"
  presentation: "cta_button | null"
  planned_count: 3
  rationale: "対象講座と件数を判断した根拠"
  placements:
    - placement_id: "CTA-01"
      provider: "shinken_zemi | smile_zemi | zkai | study_sapuri"
      target_course: "preschool | elementary | junior_high | high | elementary_junior | toeic_basic"
      section_id: "h2-1"
      section_heading: "実際のH2見出し"
      reader_question: "読者の疑問"
      official_information_needed: "公式側で確認すべき内容"
      destination_purpose: "公式遷移の目的"
      lead_copy: "固有の案内文"
      rationale: "この場面に置く根拠"
```

## `plan` 出力

両事業目的のCTAをaffiliate_link_plan.placementsへ全件列挙する。planned_count、確認場面、placements、マニフェスト、実配置の一意なIDと件数を一致させる。

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
affiliate_link_plan: null # 両事業目的で承認済みURLと最低2配置が確定した場合にeligibleな計画を返す
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
  provider: "shinken_zemi | smile_zemi | zkai | study_sapuri"
  target_course: "preschool | elementary | junior_high | high | elementary_junior | toeic_basic"
  presentation: "cta_button"
  planned_count: 3
  rationale: "planで承認済みの講座・件数根拠"
  placements: [] # 件数にかかわらず承認済みの全配置と意味情報を列挙する
cta_strategy:
  policy_version: "minimum-two-v1"
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
  appearance_profile: null # profile指定時は cream-manga-mustard-v1
  existing_links: []
  new_links: [] # destination_roleとpresentationを含める
affiliate_link_manifest:
  appearance_profile: null # profile指定時は cream-manga-mustard-v1
  links: [] # 進研ゼミ・スマイルゼミ・Z会・スタディサプリの承認済み講座別リンクだけ。内部リンクとは別に記録する
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

`conversion`では`approved_affiliate_link_plan.status: eligible`を必須とする。対象講座、承認済みURL、`cta_strategy`、自然な全配置章、共通部品のいずれかが欠ける場合は`conversion_affiliate_unresolved`で停止する。[CTA補足表記の方針](cta-caption-policy.md)に従い、`destination_text`は新規出力せず、旧フィールドがあっても表示しない。`planned_count`と計画の全配置に従い、`affiliate_link_manifest.links` に次を記録する。

```yaml
- provider: "shinken_zemi | smile_zemi | zkai | study_sapuri"
  placement_id: "承認済み配置の一意なID。件数にかかわらず必須"
  target_course: "preschool | elementary | junior_high | high | elementary_junior | toeic_basic"
  presentation: "cta_button"
  component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1 | zkai_cta_v1 | study_sapuri_cta_v1"
  href: "ユーザー提供値をそのまま使う"
  tracking_image_src: "ユーザー提供値をそのまま使う"
  rel: "nofollow"
  lead_text: "公式サイトで確認できる内容を示す短い案内文"
  button_text: "本文の文脈に合う、読者に見える具体的な案内文"
  section_id: "h2-1"
  section_heading: "配置先H2の実際の見出し文字列"
  reader_question: "この位置で読者が確認したいこと"
  official_information_needed: "公式側で確認すべき内容"
  destination_purpose: "公式遷移の目的"
```

各`lead_text`は対応する`lead_copy`を保持し、別配置と同一または実質同義にしない。各CTAは該当セクションの説明後に置き、連続したCTAブロックや隣接段落への配置を避ける。本文が確認理由を説明していない場合は、CTAだけで補わず記事本文の設計へ戻す。

HTMLソースではURL中の `&` を `&amp;` と直列化できる。`audit` ではソース文字列ではなくDOMで復元した `href` と `src` をユーザー提供値と比較し、クエリやパラメータの変更を許可しない。

`traffic`もapproved_affiliate_link_plan.status: eligibleを受け取り最低2CTAを挿入し、主成約記事カード1件を保持する。未確認・未計画の既存CTAは自動削除せず、承認・計画との不一致として停止する。

各affiliate_link_manifest.links[]には共通配置方針のplacement_context（before/after/rationale）を必須追加し、plan→insert→UI→auditで保持する。最初が後半ならcta_strategy.first_cta_position_noteも保持する。before/afterの一致だけで意味の自然さを合格にしない。

## `audit` 入力

CTA件数にかかわらず、各`placement_id`の固定DOM、URL、計測画像、対象講座、セクション、固有の案内文を確認し、`cta_strategy.planned_count`、公式確認場面、マニフェスト、実CTAの件数が一致することを確認する。

```yaml
rendered_html: "HTML化後の本文またはページHTML"
article_business_purpose: "conversion | traffic"
cta_strategy: {}
expected_link_manifest:
  appearance_profile: null # profile指定時は cream-manga-mustard-v1
  existing_links: []
  new_links: []
affiliate_link_manifest:
  appearance_profile: null # profile指定時は cream-manga-mustard-v1
  links: []
verified_candidates: []
rendered_page_checks:
  article_design_profile: # profile指定時に必須。未指定記事では省略可
    profile: "cream-manga-mustard-v1"
    design: "A | B | C | D | E"
    origin: "frontmatter"
    style_source: "現在実行で照合した共通CSSの識別子"
    verified_in_run_id: "現在のrun_id"
    providers_checked: [] # 実際に使用したCTAのproviderをすべて記録
    cta_appearance_matches: true # CTAを使わない場合はnull
    card_appearance_matches: true # image_cardを使わない場合はnull
    unprofiled_pages_unchanged: true
    regression_reference: "共通実装変更時の旧10記事/未指定記事の回帰記録と現在のスコープ確認"
  component_id: "shinken_zemi_cta_v1 | smile_zemi_cta_v1 | zkai_cta_v1 | study_sapuri_cta_v1"
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
      profile_appearance_matches: true # profile指定時、該当CTA/カードの外観・全体表示を確認
  console_errors: []
```

`affiliate_link_manifest.links` に `presentation: cta_button` がある場合、`rendered_page_checks` は必須であり、320・375・390・768・1280pxの5幅をすべて含める。欠落または未確認なら `affiliate_cta_render_unverified` とする。`expected_link_manifest.new_links`に`image_card`がある場合は、実カード数が期待件数と一致して2件以下であること、各カードに画像・正式タイトル・紹介文があり、画像が読み込まれ、表示形式がマニフェストと一致することも記録する。

両目的で最低2CTAの原稿・最終HTMLの配置ID、講座、URL、案内文、前後引用、計測画像を監査する。集客用は必須主成約記事画像カード1件と、その画像・正式タイトル・紹介文も監査する。

profile指定時は上記の `article_design_profile`、5幅の `profile_appearance_matches`、各マニフェストの `appearance_profile` も照合する。profile/design/由来が親指定と一致しない場合は `article_design_profile_mismatch`、実表示記録が不足する場合は `article_design_profile_render_unverified` とする。profile未対応は `article_design_profile_component_missing` であり、見えていない状態と混同しない。`traffic`でも主成約記事カードを使うため、このprofile実表示確認を省略しない。旧10記事と未指定記事への非漏出は共通実装変更時の回帰記録を参照し、現在の適用スコープを再確認する。

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
  article_design_profile_mismatches: []
  article_design_profile_render_mismatches: []
```

不一致が1件でもあれば `status: blocked`、`blocks_draft: true` とする。

## 理由コード

次の固定コードを使用し、自由文の説明を併記する。

- `missing_link_inventory`
- `business_purpose_unconfirmed`
- `conversion_affiliate_unresolved`
- `primary_conversion_destination_missing`
- `primary_conversion_card_missing`
- `affiliate_unresolved`
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
- `article_design_profile_unconfirmed`
- `article_design_profile_component_missing`
- `article_design_profile_mismatch`
- `article_design_profile_render_unverified`
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

Z会の3講座・固定URL・既存CSSの再利用条件は [Z会専用CTA契約](zkai-cta.md)と [承認済みリンクデータ](zkai-affiliate-links.json)を参照する。`preschool`等の未提供講座はZ会へ適用しない。
