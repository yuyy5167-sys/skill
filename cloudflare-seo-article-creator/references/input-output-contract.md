# 入出力契約

## 共通状態

1記事の実行は次の状態で管理する。

```yaml
schema_version: "2.6"
run_id: "現在実行の一意な値"
project_root: "C:\\AIフォルダ\\ブログ\\site"
rulebook_path: "C:\\AIフォルダ\\ブログ\\クラウドフレア\\記事装飾ルールブック.md"
authorization:
  mode: orchestrated_prepublication
  source: keyword_and_create_instruction
  bundled_approval:
    article_count: 1
    completion_point: final_preview_presented
    intermediate_confirmation_required: false
    progress_updates_are_approval_gates: false
  scope:
    article_count: 1
    article_root: ""
    may_create_new_article_files: true
    may_save_rights_cleared_assets: true
    may_insert_h2_heading_image_references: true
    may_prepare_isolated_preview: true
    may_overwrite: false
    may_edit_existing_articles: false
    may_publish: false
    may_deploy: false
article:
  mode: new
  main_keyword: ""
  article_id: ""
  title: ""
  date: "YYYY-MM-DD"
  categories: []
  tags: []
  draft: true
  search_reader: "検索して読む人"
  service_user: "教材・サービスを利用する人"
  primary_decision_axes: []
title_contract:
  outline_status: PASS
  candidates_count: 3
  recommended_title: ""
  selected_title: ""
  core_promise: ""
  supporting_topics: []
  all_candidate_gates_pass: true
  parent_first_read: pass
affiliate:
  disposition: eligible | not_applicable | deferred | blocked
  provider: shinken_zemi | null
  target_course: elementary | junior_high | high | null
  affiliate_link_plan: null
  affiliate_link_manifest: null
  component_check: pending
  insert_status: pending
  audit_status: pending
  reason_code: null
external_link_policy:
  mode: prohibit_generic_shinken_zemi_when_affiliate_eligible | allow_task_required_only | not_applicable
  classified_links: []
  allowed_external_links: []
emphasis_plan:
  status: pending
  items: []
  not_emphasized: []
evidence_policy:
  required: true
  capture_mode: analyze_final_body
  strategy: screenshot_preferred
  method_priority:
    - element_screenshot
    - pdf_region_capture
    - viewport_screenshot
    - direct_download
  max_claims_per_article: 3
  max_assets_per_claim: 1
  require_attempt_when_visual_claim_exists: true
  no_allowed_asset_action: continue_without_assets
  placement_mode: automatic_when_accepted
```

`article.mode`が`new`以外、またはキーワードと新規記事作成指示がそろわない場合は本スキルの一括実行対象外とする。`authorization.scope.article_root`は`<project_root>\src\content\blog\<article_id>`へ正規化し、この外へ書き込まない。`project_root`と`rulebook_path`は実行時に存在確認し、移動していた場合は推測で置換しない。

メインキーワードと明示的な記事作成指示があり、対象が既存記事ではなく本スキルの新規記事範囲だと確認できれば、依頼文に「新規」という語がなくても、一括承認は調査から統合検査後の最終プレビュー表示まで有効とする。計画、タイトル、調査、執筆、権利条件を満たす画像、サムネイル、各H2見出し画像、保存、検査、修正、隔離プレビューについて途中承認を追加しない。ユーザーが停止を指示した場合は安全な区切りで止める。

同名記事ルート、既存ファイル、既存記事への統合・リライト推奨がある場合、`may_overwrite: false`を維持して`BLOCKED`にする。一括承認を公開、デプロイ、Git操作、共通CSS変更へ拡張しない。範囲外の権限またはユーザーにしか決められない判断が必要な場合も、推測で進めず`BLOCKED`にする。

## 実装計画とTODO

`schema_version: "2.6"`の新しい記事実行では、計画とTODOを次の形で実行状態に保持する。

```yaml
orchestration:
  plan_version: 1
  execution_mode: direct
  design_version: 1
  todos:
    - todo_id: T-01
      instruction_version: 1
      purpose: "このTODOで満たす目的"
      inputs: []
      depends_on: []
      allowed_scope: "変更または作業してよい範囲"
      expected_output: "成果物または確認結果"
      acceptance_criteria: []
      verification: []
      state: pending
      revision_count: 0
      same_root_cause_count: 0
      structural_redesign_count: 0
      last_root_cause: null
      acceptance_evidence: []
      plan_version: 1
      revalidation_scope: []
      blocker_type: null
      resume_condition: null
  integration_audit: pending
```

一つのTODOは、単独で検証できる一つの成果物または判定を持つ。強く依存する作業は実行前にまとめ、TODOは依存順に直接実行する。前回と同じ根本原因なら`same_root_cause_count`を増やす。原因が変わった場合は連続回数を1、構造的再設計回数を0とし、受入時は両方を0、`last_root_cause`を`null`へ戻す。構造的再設計は一つの根本原因につき`structural_redesign_count: 1`までとし、その後も同じ原因が残る場合は`blocked`にする。ユーザー判断が必要な場合は`blocker_type: needs_user_decision`を使い、新しい状態名を追加しない。

更新前に完成した2.5以前の記事・成果物を自動変更・自動失格にしない。途中実行は影響する未完了工程から2.6の直接実行へ移行し、必要な設計を確定する。旧版の成果物は下記の影響判定で扱う。旧固定評価軸を併記せず、検索意図に基づく回答・条件・評価軸を保持する。公開権限・ファイル境界は変えない。最終プレビューが未表示なら統合検査後に表示する。

## 直接実行の記録と変更要求

本スキルが編集設計、調査、制作、保存、検証を直接実行する。仮説は調査で検証し、反証・追加疑問を受けて確定設計へ更新する。

以下は本スキルの実行状態で管理し、依存スキルやfrontmatterへ未対応項目として直送しない。

```yaml
execution_brief:
  article_id: ""
  todo_id: ""
  design_version: 1
  purpose: ""
  reader_question: ""
  reader_outcome: ""
  inputs: []
  required_answer_ids: [] # 本文では実在answer_map IDを必須対応。調査等は空でよい
  fixed_decisions: []
  production_steps: [] # 節別の回答・説明順、または画像・UI等の具体指示
  allowed_adjustments: []
  prohibited_changes: []
  expected_output: ""
  acceptance_criteria: []
  verification: []
execution_result:
  used_design_version: 1
  deliverable: null
  verification_evidence: []
  unresolved_items: []
  change_requests:
    - instruction_reference: ""
      problem: ""
      evidence: []
      proposed_change: ""
      affected_sections_or_todos: []
```

- 依存TODOが受理され、必須設計・根拠・参照が揃った場合だけ制作を始める。調査TODOは仮説と調査目的で開始でき、未確定の本文設計を要求しない。
- 本文作成では各必須回答を`required_answer_ids`で追跡し、依存スキルへ渡す`required_points`・`allowed_evidence`に出典、時点、適用条件、確認状態を保持する。根拠が空の事実を断定する指示では実行しない。調査済みの確認限界を回答にする場合は、調査範囲・不明点・結論への影響を明記した設計で進められる。
- 不足・矛盾を推測で埋めない。`needs_execution_input`は追加作業が必要な実行状態としてTODOの状態と区別する。依存スキルがこの状態を持たない場合は既存の未解決出力と上記変更要求を併記し、既存PASS/BLOCKEDを上書きしない。
- 許可する調整は、指定した意味を保つ語尾・接続・段落、許可された部品の実装、生成ツール向け記述などに限る。読者像・主質問・結論・タイトル・見出し文言と順序・サムネイルのコピーと構図・各H2画像の意味と固定文字・リンク先・画像選定は確定設計として保持する。
- 設計不備は直接修正し、根拠不足は調査へ、制作不備は該当TODOへ戻す。実行者だけで解消可能な編集判断をユーザー確認に回さない。
- 設計の意味・構成・根拠・固定事項・受入条件が変わる場合は`design_version`を更新し、差分・理由・影響する回答ID/節/TODOを記録する。許可された語尾調整だけなら版を増やさない。工程・依存関係が変わる場合は`plan_version`も更新する。
- 旧版成果物を最新扱いにしない。差分と参照回答IDを確認し、影響がなければ受理理由、影響があれば再制作・再検証範囲を残す。影響する成果物の受入を保留する。
- 必須設計と受入条件の完全性、指示への適合、読者への回答・根拠・実物品質を別々に検収する。設計自体が誤っていれば成果物を合格にしない。

## 記事目的・疑問・回答の正本

以下は本スキルの実行状態で保持し、中間ファイルや記事frontmatterへ追加しない。`article.search_reader`、`article.service_user`、`article.primary_decision_axes` は `content_brief` と一致させる。検索意図から決めた評価軸を見出し・本文・UIで変えない。学習動作は教材の利用体験を論じる場合に適用し、料金・契約・手続きの主質問を補足扱いへ戻さない。

```yaml
content_brief:
  design_version: 1
  status: confirmed # 仮説段階はhypothesis
  primary_question: "最優先で答える疑問"
  reader_outcome: "読後に理解・判断・実行できること"
  search_reader: "検索して読む人"
  service_user: "教材・サービスを利用する人"
  primary_decision_axes: []
  out_of_scope: []
question_coverage:
  excluded_important_candidates:
    - question: "採用しなかった重要な疑問候補"
      reason: "対象外・重複などの理由"
answer_map:
  - answer_id: A-01
    reader_question: "読者の疑問"
    importance: primary # primary | supporting
    answer_summary: "確認できた回答または確認限界"
    evidence:
      - source_url: "実際に確認した出典"
        checked_at: "確認日"
        supported_claim: "出典で確認できる内容"
        applicable_scope: "年度・対象者・学年・支払方法など"
    interpretation: "事実から考えられる読者への意味"
    limitations: []
    unresolved_points: []
    status: supported # supported | partially_supported | unverified | conflicting
```

- `supported`：根拠あり。確認範囲で使用する。
- `partially_supported`：一部のみ根拠あり。回答・主張を裏付けられる範囲に限定する。
- `unverified`：調査したが確認できない。調査範囲・不明点・結論への影響を記す。
- `conflicting`：根拠同士が矛盾する。双方の出典を保持し、時点・対象・条件を再調査する。

未調査の項目を `unverified` として調査済みにしない。4状態は情報の確認状態であって、TODOの進捗や実行全体の `BLOCKED` ではない。主回答に影響しない不明点は明示して進められるが、結論を左右する不足・矛盾は追加調査または安全な結論の限定が必要。「確認できない」こと自体が回答になる場合も調査範囲と判断不能な内容を明示し、限定構成を検収する。合理的に解消できず安全な範囲も定まらない場合は既存の停止規則に従う。

`interpretation` を公式発表と混同しない。空欄を推測で補わず、根拠・条件は回答IDで参照する。重要候補がなければ除外一覧は空でよい。検収のために不要な疑問を捏造しない。

### 追加調査の入出力と反映責任

本スキルは疑問ID、現時点の回答、不足情報、結論への影響、確認済み出典を入力に追加調査を直接実行し、事実・出典・確認日・適用条件・確認状態・未解決事項を記録する。

受入判定後に `answer_map` を統合し、完全な上流レポートの検索意図・ペルソナ・一次情報・不明点・Quality Gateを更新して、回答表との一致を検収する。新しい事実を回答表だけへ追加して、見出し設計に古いレポートを使わない。

変更した回答IDを参照する`required_answer_ids`から影響する構成・本文・タイトル・表・画像文言・リンクを特定する。編集設計を直接修正し、本文等の制作物は該当TODOで再制作する。

## 上流成果物

### 競合調査

`$seo-keyword-competitor-research`の完全な出力を保持する。要約だけを見出しスキルへ渡さない。

受理条件:

- Google直接確認済み
- Quality Gate完了
- 主検索意図、ペルソナ、記事方針、根拠、未確認事項がある
- 新規記事を作成できる推奨状態
- 疑問一覧の重要な見落としと回答の充足を別々に検収済み
- 受理した追加調査が完全な上流レポートに反映され、`answer_map`と一致している

### 見出し構成

`$seo-heading-outline-creator`を直接実行した`status: PASS`を必要条件とし、二段階検収にも合格した場合だけ受理する。H1・H2・H3の安定ID、見出し、役割、根拠に加え、各H2の`reader_question`と`reader_outcome`を保持する。

```yaml
outline:
  execution_mode: direct
  design_version: 1
  status: PASS
  heading_review: PASS
  reader_value_first_read: PASS
  evidence_accuracy_review: PASS
  reader_value_regression: none
  sections:
    - section_id: H2-01
      heading: "見出し"
      reader_question: "この章で答える検索者自身の疑問"
      reader_outcome: "読後に可能になる理解・判断・実行"
      required_answer_ids: [] # answer_mapの実在IDへ対応づける
      current_input_basis: []
```

`reader_question`と`reader_outcome`は2.1以降、`reader_value_first_read`、`evidence_accuracy_review`、`reader_value_regression`は2.2以降の新しい見出し工程で必須とする。更新前に完成した記事や見出し構成を自動変更または自動失格にしない。2.1で受入済みの見出しを途中実行へ引き継ぐ場合は、見出し自体を理由なく作り直さず、二段階検収だけを追加して、不合格の場合に限り見出しTODOを再開する。2.1より前の構成を再利用する場合は見出し工程を新契約で再評価し、欠落項目を推測で補完しない。

2.6では、見出しスキルの完全な出力に加えて`title_contract`を保持する。`recommended_title`と`selected_title`は同じ合格候補とし、`core_promise`は読者へ約束する中心価値を一つ記録する。タイトルへ入れない補足論点は`supporting_topics`へ分ける。`all_candidate_gates_pass: true`と`parent_first_read: pass`の両方がない構成を採用せず、frontmatter保存後に`selected_title`との完全一致を検査する。

第1段階は設計理由を先に見ず、見出しだけで主質問への回答・読者価値・具体性・反復を確認する。第2段階は完全な調査と原資料で事実・数字・時点・条件を確認する。不合格なら見出し設計を修正して両段階を再確認する。同一実行者による確認を独立検証と呼ばない。

### 本文

以下は本文の依存スキルへ渡す入力例である。`content_brief`と該当する`answer_map`を、下記の既存項目へ変換して渡す。

```yaml
mode: new
section_id: H2-01
section_type: heading
heading: "見出し"
heading_level: 2
parent_heading: "上位見出しなし"
scope: "この節で扱う範囲"
connection: "前後のつながり"
required_points: [] # 確定した回答・説明順・比較/具体例・必要条件・限界
allowed_evidence: [] # 確認した事実、出典、確認日、適用範囲、確認状態
reader_profile: "検索者、前提知識、サービス利用者、読後の到達点"
quality_profile:
  required:
    - "主要評価軸に沿って、約束した疑問に本文で答える"
    - "事実と解釈を分け、根拠のある範囲と不明点を保持する"
  preferred: []
  prohibited:
    - "検索意図と無関係な保護者管理論への置き換え"
    - "教材評価で支援未調査のまま家庭の努力へ解決を委ねること"
input_format: markdown
review_scope: section
quality_report: summary
```

最終全文検査では`review_scope: article`、`article_complete: true`とする。`article_pass`以外は完成本文として使用しない。

`scope`と`required_points`へ主要評価軸と担当回答を、`allowed_evidence`へ根拠・条件・確認状態を写す。`interpretation`は事実ではなく解釈として区別する。依存スキルに独自の調査や事実補完を求めない。`quality_profile`にはG3の適用基準を追加し、主要疑問ごとの回答箇所・根拠を確認して受け入れる。欠落・競合で`needs_execution_input`なら原因工程へ戻す。

### 調査日・出典注記の統合

書き方は文章スキルの「調査記録と読者向けの説明」を正本とする。親が`answer_map`と出典記録から、確認日の注記が必要な対象主張・出典・日付・掲載位置を記事全体で決める。節単位の`allowed_evidence`には確認日を残し、本文に載せる内容だけを`required_points`、反復を避ける指定を`quality_profile`に写す。適用日・申込期限を確認日に置き換えず、異なる出典の確認日を一つの日付で代表させない。

親が注記を統合した全文を文章スキルの`review_scope: article`で検収し、その後UIの`preserve_elements`へ対象情報・出典・確認日・配置を渡す。最終記事でも制作報告の反復、必要な日付の欠落、出典との対応を確認する。

### 重要語句の強調

本文受理後に次を実行状態へ保持し、記事frontmatterや中間ファイルへ追加しない。

```yaml
emphasis_plan:
  status: accepted
  items:
    - emphasis_id: E-01
      section_id: H2-01
      heading_text: "対象見出しの完全一致文字列" # 任意。指定時はsection_idとの一致も検証する
      answer_id: A-01
      exact_text: "短い重要語句"
      role: conclusion | condition | deadline | caution | action
      reason: "流し読みでも判断に必要な理由"
  not_emphasized:
    - answer_id: A-02
      reason: "本文全体の理解に必要だが、短い強調語句へ切り出すと誤解を招く"
```

章IDは`lead`、`H2-01`、`H3-01-01`のように出現順で付け、表示用アンカーとは区別する。必要なら`heading_text`で見出し文を追加照合する。H2指定は配下のH3を含み、H3指定はそのH3の範囲に限定する。同じ語句が別章にあるだけでは満たさない。

空の計画を`accepted`にしない。固定件数は設けない。主結論、重要条件、期限、注意、次の行動のうち流し読みで失われやすい語句を選び、段落全体、同一語句の反復、装飾目的の強調を禁止する。UI化後は各`exact_text`が対応章の短い`strong`要素にあり、意味・条件が変わっていないことを静的検査と実表示で確認する。

## 内部リンク契約

`$article-internal-linker`の`plan`、`insert`、`audit`を順に直接実行し、公開確認済み採用先を`approved_destination_id`へ固定する。正本情報源と承認契約は変更しない。本スキルは次を保持する。

- 現在の一括承認に結び付いた`link_intents`
- 挿入前本文
- `body_with_internal_links`
- `expected_link_manifest`
- `affiliate_link_plan`と`affiliate_link_manifest`
- 現在実行で確認した`site_rendering_capabilities`
- `result.status`と`blocks_draft`

`blocked`または`blocks_draft: true`なら、内部リンク済み本文を採用しない。候補URLは、現在実行で公開確認済みの正本からだけ渡す。

進研ゼミCTAは、タイトル、想定読者、結論、承認済み設計が同じ講座を指し、自然な配置章があり、`site_rendering_capabilities.affiliate_cta_component`が`supported: true`かつ`component_id: shinken_zemi_cta_v1`の場合だけ`eligible`とする。親は講座URLを複製せず、子スキルの正本契約と出力を使う。`not_applicable`ではCTAを追加せず、講座・URL・部品・監査の不一致は`blocked`として元本文を保持する。

## 公式・権威メディア画像収集契約

`$official-site-evidence-capture`へ完成本文を読み取り専用で毎回渡す。新規2.6は依存スキルのスキーマ1.3、`authorization.mode: orchestrated_prepublication`を使用する。`capture_phase: discover / capture_mode: analyze_final_body`で候補を受け、選んだ完全候補レコードを`capture_phase: capture / capture_mode: explicit_requests`へ渡す。戦略・方法順・上限・試行条件は`capture_preferences`へ写す。本スキル固有の`required`・`no_allowed_asset_action`・`placement_mode`は渡さない。

本スキルの実行での保存は、候補が`authorization.scope.article_root\images\evidence`内にあり、権利状態が`allowed`で、`local_save_allowed`と`article_publication_allowed`がともに`true`の場合だけ認める。単独利用時の候補別承認は依存スキルの正本契約に従う。

候補段階は`evidence_discovery`（依存スキルの1.3引継ぎ契約）をそのまま保持する。`analysis_complete`、主張・候補・除外理由を読み、候補ID、対象領域、URL、方法と許可代替、権利、加工、保存先を確定する。取得入力の`selected_candidates`に完全レコード、`explicit_requests`に対応するrequest_id・section_id・intended_claimを写し、`design_version`を付ける。

`CANDIDATES_READY`は途中状態である。`NOT_APPLICABLE`または`READY_WITHOUT_ASSETS`は実際の探索と権利条件が妥当な場合だけ無画像として受理する。統合結果は次とし、未生成の依存スキル出力を創作しない。

```yaml
evidence_result:
  schema_version: "1.3"
  status: pending # READY | PARTIAL | READY_WITHOUT_ASSETS | NOT_APPLICABLE | BLOCKED
  source_phase: discover # discover | capture
  selected_candidate_ids: []
  acceptance_evidence: []
```

適格な必要候補があるのに空選定で取得工程を省略しない。候補・条件変更は変更要求として扱い、権限外操作は行わない。

保存後は、依存スキルが返す次の情報を含む`evidence_capture`ブロックをそのまま保持する。

```yaml
evidence_capture:
  schema_version: "1.3"
  capture_phase: capture
  used_design_version: 1
  selected_candidate_ids: []
  run_id: ""
  status: READY
  article_id: ""
  asset_root: ""
  capture_attempts:
    - request_id: CAP-001
      section_id: H2-01
      intended_claim: ""
      source_url: ""
      preferred_method: element_screenshot
      actual_method: element_screenshot
      result: saved
      reason_code: CAPTURE_SAVED
  assets: []
  skipped_sources: []
  checks:
    paths_exist: true
    hashes_verified: true
    duplicates_resolved: true
```

保存成果物ファイルは画像だけとし、出典管理用のJSON、Markdown、ログを作らない。各`capture_attempts`には対象主張、希望方法、実際の方法、結果、理由コードを含める。各`assets`には、絶対・記事相対パス、SHA-256、寸法、MIME、対応見出しと主張、元ページ、運営者、情報源区分、権利根拠、掲載・加工可否、取得方法、モバイル確認を含める。

本スキルの実行では`READY`、`PARTIAL`、`READY_WITHOUT_ASSETS`、`NOT_APPLICABLE`を受理できる。単独利用では`SKIPPED_BY_USER`も受理できる。`BLOCKED`は入力・権限・依存機能を解決するまで受理しない。権利条件を満たす候補があるのに取得機能が使えない、または2回失敗した状態を`READY_WITHOUT_ASSETS`へ変換しない。画像が0件でも、それだけを理由に本文や記事全体を不合格にしない。

旧1.1・1.2を読めるが、新規2.6は1.3を使用する。取得時は`capture_attempts`、選定ID、各assetの`candidate_id`、使用設計版を照合する。無画像のときは`evidence_discovery`を検収し、`evidence_result.source_phase: discover`に理由を残す。候補探索だけを取得完了とは報告しない。

次工程は、対応スキーマ、ファイル存在、SHA-256、`article_publication_allowed: true`、帰属表示、加工可否を再検証する。引継ぎデータを失った画像や、ファイル名からしか出典を判断できない画像を使用しない。この契約は記事編集・画像配置の権限を付与しない。

## 教育記事UIコーディング契約

`$study-article-ui-coder`へ次を渡す。

```yaml
design_mode: autonomous
article_text: "body_with_internal_links"
primary_keyword: ""
audience: ""
article_goal: ""
desired_reader_action: ""
required_elements:
  - "確定した主要評価軸に沿う本文・結論と、条件・確認限界の保持"
  - type: emphasis_plan
    items:
      - emphasis_id: E-01
        section_id: H2-01
        answer_id: A-01
        exact_text: "短い重要語句"
        role: conclusion | condition | deadline | caution | action
        reason: "流し読みでも判断に必要な理由"
preserve_elements:
  - section: "承認済みCTA配置章"
    element: "shinken_zemi_cta_v1"
    preserve: "固定DOM、対象講座、href、計測画像src、rel、表示文、配置"
forbidden_elements:
  - "検索意図と異なる固定の学習動作・保護者管理論への置き換え"
  - "許可されていない進研ゼミ公式サイトへの単純誘導リンク"
approved_internal_links: []
approved_assets: []
evidence_capture: null # 取得時は子の1.3出力全体。無画像時はnull
evidence_result: null # 検収した統合状態を渡す
asset_placement:
  mode: automatic_when_accepted
  require_hash_match: true
  require_publication_allowed: true
  require_section_claim_match: true
  require_attribution_and_alt: true
  require_mobile_readability: true
  unaccepted_action: saved_unplaced
output_target: astro-markdown
editing_mode: structure-light-edit
publication_state: draft
```

`audience`には検索者とサービス利用者の違いを、`article_goal`には主要評価軸と主質問を、`desired_reader_action`には読後の到達点を含める。`required_elements`・`forbidden_elements`は本文の意味保持条件とする。`emphasis_plan`は固定件数を持たず、短い完全一致語句、章、回答ID、役割、理由を渡す。CTA挿入済みの場合は`preserve_elements`で固定DOMと属性を保持する。旧固定評価軸を併記しない。本文とUIの両接続で、回答・出典・適用条件・不明点・評価軸、強調語句、CTAが失われていないか確認する。依存スキル自身の固定指示と競合する場合は接続を合格にせず、変更が必要な依存スキル箇所を提示して権限を確認する。

依存スキルはファイルを書かず、`coded_content`、`component_map`、`validation_report`、`unresolved_items`、`change_summary`を返す。採用画像は、パス・ハッシュ・掲載可否・加工可否・帰属表示・alt・対応見出しと主張・モバイル可読性が確認できる場合だけ配置する。条件を満たさない保存画像は`unresolved_items`へ`saved_unplaced`として理由を返す。受理済み`coded_content`だけを保存して差分を確認する。`autonomous`実行では子が返さない`used_design_version`を要求せず、親が保持する現行設計と`validation_report.emphasis`、本文、保持対象を照合する。`needs_parent_input`なら親が設計入力を補完する。`unsupported_component`は既存部品で再設計して直接再変換する。共通CSS変更が必要なら`design_migration_required`として停止する。

## アフィリエイトと外部リンク契約

親は子スキルの正本URLを複製せず、次の統合状態だけを保持する。

```yaml
affiliate:
  disposition: eligible | not_applicable | deferred | blocked
  provider: shinken_zemi | null
  target_course: elementary | junior_high | high | null
  affiliate_link_plan: null
  affiliate_link_manifest: null
  component_check: pending
  insert_status: pending
  audit_status: pending
  reason_code: null
  placeholders_inserted: []
external_link_policy:
  mode: prohibit_generic_shinken_zemi_when_affiliate_eligible | allow_task_required_only | not_applicable
  classified_links:
    - href: ""
      kind: internal | affiliate_cta | generic_official_navigation | task_required_official | evidence_reference
      reason: ""
  allowed_external_links:
    - href: ""
      reason: "読者が本文から直接移動する必要"
```

- `eligible`は、子スキルの`affiliate_link_plan.status: eligible`、対象講座、配置章、共通部品確認がそろう場合だけ使用する。CTAを最大1件挿入し、HTML化後の`audit`合格を必要とする。
- `not_applicable`は、複数学年、講座横断、対象不明、または進研ゼミへの次行動を案内しない場合に使い、CTA 0件と理由を記録する。
- `deferred`と`affiliate_inventory_pending`は、記事に必要な承認済みアフィリエイト契約が実際に存在しない場合だけ使う。
- `blocked`は、講座不一致、未承認URL、共通部品欠落、挿入・監査不合格に使う。`not_applicable`や`deferred`へ変換しない。

すべての状態で禁止する。

- アフィリエイトURLの検索、推測、補完、短縮、改変
- `{AFFILIATE_URL}`、`TODO`、`#`などの仮値
- リンク先がないCTAや申込み誘導
- 内部リンクへの計測URL混入
- `eligible`で監査前に「アフィリエイト対応済み」と報告すること
- `not_applicable`の理由がないままCTAを省略すること

`eligible`では、同じ公式講座トップへ単に誘導する非アフィリエイトリンクを`generic_official_navigation`として禁止する。公式FAQ・規約等は根拠記録へ保持し、手続き・交換・ログイン等のため本文から直接移動する必要がある場合だけ`task_required_official`として`allowed_external_links`へURLと理由を記録する。静的検査は許可外の進研ゼミ公式リンクを検出し、意味上の分類は親の設計検収で確定する。

## サムネイル・H2見出し画像契約

`$education-blog-thumbnail-creator`を次の入力で直接実行する。完成本文を読み、サムネイルの画風確定後に全Markdown H2の見出し画像まで設計・生成・検品・限定挿入する。入力の権限は通知済みの新規記事ルート内に限定する。

```yaml
image_asset_request:
  execution_mode: full
  asset_scope: thumbnail_and_h2
  authorization_mode: orchestrated_prepublication
  parent_run_id: ""
  article_path: ""
  allowed_output_directory: "<article-root>\\images"
  article_edit_authorized: true
```

出力は兄弟要素の`thumbnail`と`section_images`として保持し、参照モード、検査状態、最終プロンプト、件数を要約で置き換えない。

```yaml
thumbnail:
  execution_mode: full
  status: null # 未生成はnull。生成後PREVIEW_READY | FINAL_ASSET_READY | BLOCKED
  used_design_version: 1
  thumbnail_design: null
  pre_generation_review: null
  image_only_readback: null
  authorization_mode: orchestrated_prepublication
  parent_run_id: "" # 依存スキルの既存契約に従い、run_idを渡す互換フィールド
  allowed_output_directory: ""
  article_title: ""
  article_path: ""
  target_grade: ""
  article_type: ""
  exact_copy: []
  character_mode: person | personless
  character_sheet_paths: []
  reference_mode: direct_image_reference | viewed_and_transcribed | reference_unavailable | not_applicable
  examples_opened: false
  style_reference_changed: false
  visual_motif: ""
  layout_archetype: ""
  focus_position: left | center | right
  difference_summary: ""
  imagegen_mode: ""
  final_prompt: ""
  output:
    path: null
    width: null
    height: null
    format: null
    bytes: null
  checks:
    exact_japanese: pending
    character_identity: pending
    six_field_similarity: pending
    small_card_distinguishable: pending
    asset_validation: pending
    rendered_widths: []
  integration:
    cover_image_updated: false
    article_body_changed: false
    published: false
  pending: []
```

```yaml
section_images:
  applicability: applicable
  not_applicable_reason: null
  status: null # 未生成はnull。生成後PREVIEW_READY | FINAL_ASSET_READY | BLOCKED
  style_profile_id: h2_style_profile_v1
  style_profile_revision: 1
  style_profile_sha256: ""
  direct_style_images_sent_to_generator: false
  expected_h2_count: 0
  generated_count: 0
  saved_count: 0
  inserted_count: 0
  reference_integrity: {}
  items: []
  integration:
    atomic_article_patch: true
    article_body_changed: false # 一括挿入前はfalse。FINAL_ASSET_READYではtrue
    published: false
  pending: []
```

サムネイルとH2見出し画像の設計・生成・検品は依存スキルの完全な正本契約に従う。生成・編集前に各資産の`pre_generation_review.result: pass`、必要な参照状態、最終プロンプトを確認する。生成結果が不明な場合は自動再実行せず、実行状態を確認する。

- 人物を使う場合、`reference_mode: reference_unavailable`は受理しない。人物なしなら`not_applicable`を受理する。
- 本スキルの`PREVIEW_READY`は生成途中状態であり記事完成条件ではない。依存スキル単独利用ではユーザー確認用状態として扱う。
- `thumbnail.status: FINAL_ASSET_READY`でも、新規記事の`coverImage`を実在パスへ更新して確認するまでG7は合格しない。
- `section_images.status: FINAL_ASSET_READY`でも、期待H2数と生成・保存・挿入件数が一致し、`check-h2-images.ps1`と本文幅の実表示検査が合格するまでG7は合格しない。
- H2画像は全件合格後の一括挿入だけを受理する。部分挿入、既存画像の上書き、保存失敗後の記事変更を受理しない。
- `style_reference_changed: true`は自動スキル編集を許可しない。変更内容をユーザーへ報告する。
- 実施していない目視・類似・実表示検査を`pass`として補完しない。

## ファイル出力契約

一括承認の`article_root`内だけへ次を作る。

```text
<project_root>\src\content\blog\<article_id>\index.md
<project_root>\src\content\blog\<article_id>\images\<approved-thumbnail-name>.webp
<project_root>\src\content\blog\<article_id>\images\h2-<section-image-name>.webp
<project_root>\src\content\blog\<article_id>\images\evidence\<approved-image>
```

根拠画像は、本スキルの実行では権利条件と一括承認範囲が合格した場合だけ作る。単独利用では候補ごとの保存承認を必要とする。記事のfrontmatterは実行時スキーマに合わせる。H1は本文へ入れない。画像パスは記事フォルダ内の実在ファイルを指す相対パスにする。

リサーチレポート、記事設計書、TODO、品質レポートは既定でファイル保存せず、実行状態と最終報告だけに保持する。

## 静的検査入力契約

`scripts/validate-cloudflare-article.ps1`には中間ファイルを作らず、実行状態から次の名前付き引数を直接渡す。`basic`（既定）は簡易検査であり、本スキルの完成判定には必ず`parent`を使う。

```powershell
-ValidationMode parent
-ArticlePath <正本index.md>
-ProjectRoot <project_root>
-ExpectedTitle <title_contract.selected_title>
-ExpectedAffiliateDisposition <eligible | not_applicable | deferred | blocked>
-ExpectedAffiliateCourse <elementary | junior_high | high> # eligibleの場合だけ必須
-ExpectedEmphasisPlanJson <emphasis_plan.itemsを配列としてConvertTo-Json -Depth 8 -Compressした文字列>
-ExternalLinkPolicy <prohibit_generic_shinken_zemi_when_affiliate_eligible | allow_task_required_only | not_applicable>
-AllowedExternalHref <external_link_policy.allowed_external_links[].hrefの配列>
```

JSONをシェルのコマンド文字列へ直接連結せず、同じPowerShell内の変数で渡す。単独`basic`の既存`-ExpectedEmphasisPhrase`は維持するが、`parent`の章付き計画を代替しない。

親の受入条件は、`status: PASS`、`validation_mode: parent`、`parent_contract_pass: true`、`checks`の`input_contract`・`article_structure`・`title_contract`・`affiliate`・`external_links`・`emphasis`・`article_integrity`がすべて`pass`、`article_path`と`article_sha256`が最終正本と一致すること。未実施・項目欠落・`basic`の`PASS`を完成にしない。`rendered_emphasis: not_checked`は静的検査の範囲表示であり、実表示で別途全語句を確認する。

強調の静的検査は既存のNode.jsと対象プロジェクトのsatteriでMarkdown/HTMLを解析し、章と表示本文の`strong`を照合する。コメント・コード・明示的な非表示要素を除外し、解析に失敗した場合は正規表現だけで`PASS`へ切り替えない。

静的検査は、タイトル完全一致、CTA件数と対象講座、計画済み強調語句のマークアップ、許可外の進研ゼミ公式リンクを確認する。タイトルの興味・詰め込み、強調語句を重要とする意味判断、公式リンクを本文に残す必要性は、見出し・記事設計・UIの各ゲートで判定する。CTAの正確なURL、計測画像、属性、固定DOM、5画面幅表示は`$article-internal-linker`の`audit`、H2画像の対応と実在は`check-h2-images.ps1`を正本とし、親検査へ重複実装しない。

## 最終出力

```yaml
result:
  status: READY_FOR_HUMAN_REVIEW | READY_FOR_HUMAN_REVIEW_WITH_AFFILIATE_DEFERRED | BLOCKED
  publication_status: not_published
  affiliate_disposition: eligible | not_applicable | deferred | blocked
  affiliate_reason_code: null
orchestration:
  plan_version: 1
  required_todos: accepted
  blocked_todos: []
  integration_audit: pass
  reader_value_regression: none
artifacts:
  article_path: "絶対パス"
  thumbnail_path: "絶対パス"
  h2_heading_image_paths: []
  evidence_assets: []
checks:
  research: pass
  question_coverage: pass
  answer_evidence_review: pass
  outline: pass
  title_contract: pass
  body: article_pass
  emphasis_plan: pass
  content_acceptance: pass # 本文の回答箇所と根拠で検収。ビルド・表示とは別
  internal_links: pass
  affiliate_insert: pass | not_applicable | deferred
  affiliate_audit: pass | not_applicable | deferred
  disallowed_external_links: 0
  evidence_capture: accepted_status # pass | partial | valid_no_assets | not_applicable。本スキルの実行でskipped_by_userは使わない
  evidence_capture_schema: "1.3"
  evidence_selection_review: pass
  screenshot_attempts_verified: true # 無画像時はnot_applicableと理由。未取得をtrueにしない
  saved_unplaced_assets: []
  thumbnail: final_asset_ready
  section_images: final_asset_ready
  h2_image_structure: pass
  article_validation: pass
  build: pass
  rendered_audit: pass
preview:
  status: opened_verified
  url: "http://127.0.0.1:<port>/<article-route>/"
  checked_widths: [320, 375, 390, 768, 1280]
  source_draft_preserved: true
  presented_to_user: true
  presentation_stage: after_final_audit
  presentation_method: in_app_browser
human_review:
  required: true
  publication_approved: false
```

`eligible`はCTA挿入と最終監査の合格、`not_applicable`は理由とCTA 0件の確認後に`READY_FOR_HUMAN_REVIEW`へ進める。`deferred`だけが未完了で他の必須工程が合格した場合は`READY_FOR_HUMAN_REVIEW_WITH_AFFILIATE_DEFERRED`とする。`blocked`またはその他の必須工程不合格は`BLOCKED`にする。本文プレビューを開けたがサムネイルまたはH2見出し画像が未完了なら、`preview.status: opened_with_asset_pending`を返し、完成状態にはしない。統合検査後の最終記事画面をユーザーへ表示できない場合は`preview.status: display_blocked`、`preview.presented_to_user: false`とし、URL提示だけで完成扱いにしない。
