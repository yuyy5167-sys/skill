# 引継ぎ契約

スキーマ1.2の既存入力・出力・状態はこの文書のまま維持する。親主導の候補探索と取得には、後述のスキーマ1.3を追加する。スキーマ1.3はスキーマ1.2を黙って置き換えない。

## 原則

保存する成果物ファイルは画像だけとし、JSON、Markdown、ログファイルを追加しない。出典、権利、対応箇所、検査結果は、この構造をチャット内の実行状態として親が保持し、次工程へそのまま渡す。

次工程はファイル名から情報を推測せず、スキーマ、ファイル、ハッシュ、掲載可否を再検証する。引継ぎデータを失った画像は、元ページを再確認して契約を再構築できるまで使用しない。

## 入力

```yaml
evidence_capture_request:
  schema_version: "1.2"
  run_id: ""
  authorization:
    mode: standalone_interactive # standalone_interactive | orchestrated_prepublication
    parent_run_id: null
    article_root: ""
    allowed_output_directory: ""
    may_overwrite: false
    may_publish: false
  article:
    article_id: ""
    title: ""
    main_keyword: ""
    target_reader: ""
    purpose: ""
    final_body_markdown: ""
    sections:
      - section_id: H2-01
        heading: ""
  capture_mode: analyze_final_body # analyze_final_body | explicit_requests
  capture_preferences:
    strategy: best_available # best_available | screenshot_preferred
    method_priority:
      - element_screenshot
      - pdf_region_capture
      - viewport_screenshot
      - direct_download
    max_claims_per_article: 3
    max_assets_per_claim: 1
    require_attempt_when_visual_claim_exists: false
  explicit_requests:
    - request_id: CAP-001
      section_id: H2-01
      intended_claim: ""
      preferred_source_types: []
  proposed_output_directory: ""
  asset_constraints:
    allowed_mime_types:
      - image/png
      - image/jpeg
      - image/webp
    max_file_bytes: null
    max_long_edge_px: null
  search_limits:
    max_source_pages_per_request: 8
    max_retries_per_url: 2
    max_assets_per_request: 1
  consumer:
    name: null
    accepted_schema_versions: ["1.1", "1.2"]
```

`analyze_final_body`では`final_body_markdown`と安定した見出しIDを必須とする。`explicit_requests`では一意な`request_id`、実在する`section_id`、画像で示す`intended_claim`を必須とし、依頼が空なら`NOT_APPLICABLE`とする。`preferred_source_types`は優先候補であり、情報源の適格性や権利条件を緩和しない。記事本文は常に読み取り専用であり、編集権限を切り替える入力を設けない。

`authorization.mode`を省略した1.0入力は`standalone_interactive`として受理できる。`orchestrated_prepublication`では`parent_run_id`、正規化済み`article_root`、その配下の`allowed_output_directory`を必須とし、`may_overwrite`と`may_publish`は常に`false`とする。

`capture_preferences`を省略した入力は`strategy: best_available`として扱い、従来の最適方法選択を維持する。スキーマ1.2を明示した親記事スキルの新規自動実行は`strategy: screenshot_preferred`、`require_attempt_when_visual_claim_exists: true`を渡し、出力`schema_version: "1.2"`を要求する。スキーマ1.3の親主導実行には後述の`discover`と`capture`を使う。

サイト側の容量・寸法制約が未確定なら、候補報告時に具体案を示して保存承認に含める。推測した制約で先に画像を作らない。

## 出力

```yaml
evidence_capture:
  schema_version: "1.2"
  run_id: ""
  authorization_mode: standalone_interactive
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
      result: saved # saved | failed | skipped_no_rights | no_candidate
      reason_code: CAPTURE_SAVED
  assets:
    - asset_id: EVI-001
      absolute_path: ""
      article_relative_path: ""
      request_ids: []
      section_ids: []
      intended_claims: []
      sha256: ""
      bytes: 0
      mime_type: image/png
      width_px: 0
      height_px: 0
      source:
        source_type: official_company
        page_url: ""
        page_title: ""
        publisher: ""
        authority_evidence_urls: []
        accessed_at: ""
      rights:
        status: allowed
        basis_type: official_terms
        basis_url: ""
        checked_at: ""
        local_save_allowed: true
        article_publication_allowed: true
        modification_allowed: false
        attribution_required: true
        required_attribution: ""
      capture:
        method: element_screenshot
        captured_at: ""
        modification: none
        derived_from_asset_id: null
      mobile_check:
        status: pass
        checked_widths: [320, 375, 390]
        notes: ""
  skipped_sources:
    - request_id: ""
      url: ""
      reason_code: RIGHTS_UNCLEAR
      reason: ""
  checks:
    paths_exist: true
    hashes_verified: true
    duplicates_resolved: true
```

保存済み`assets`の`rights.status`は必ず`allowed`で、`local_save_allowed`と`article_publication_allowed`がともに`true`でなければならない。`source_type`は`official_company`、`public_body`、`academic_or_professional_body`、`authoritative_editorial_media`のいずれかとする。

`capture.method`は`direct_download`、`element_screenshot`、`viewport_screenshot`、`pdf_region_capture`のいずれかとする。加工版は`derived_from_asset_id`で原本へ結び、原本と同じIDを使わない。

`capture_attempts`は1.2で必須とする。視覚化すべき主張がない場合は空配列にできる。候補探索だけで終わった場合も、`no_candidate`または`skipped_no_rights`を記録する。取得を試した場合は希望方法と実際の方法を分け、フォールバックや失敗を省略しない。失敗時の`actual_method`は、実際に呼び出した方法を入れ、呼び出し前に機能不足が判明した場合だけ`null`にできる。

## 状態

| 状態 | 意味 | 親工程 |
| --- | --- | --- |
| `READY` | 1件以上を保存・検査済み | 継続可能 |
| `PARTIAL` | 一部を保存・検査したが、別の必須試行に失敗または未解決がある | 不足を報告して継続可能 |
| `READY_WITHOUT_ASSETS` | 探索したが権利条件を満たす適格候補がない | 画像なしで継続可能 |
| `NOT_APPLICABLE` | 視覚化すべき主張または明示依頼がない | 継続可能 |
| `SKIPPED_BY_USER` | 単独利用で保存候補が承認されなかった | 継続可能 |
| `BLOCKED` | 入力、保存先、承認、依存機能が不足、または権利条件を満たす候補の必須取得が2回失敗 | 解決またはユーザー判断まで保留 |

未解決の`BLOCKED`を親が勝手に成功状態へ変えない。`SKIPPED_BY_USER`は`standalone_interactive`だけで使用する。`orchestrated_prepublication`では、探索したが権利条件を満たす候補がなければ`READY_WITHOUT_ASSETS`とする。権利条件を満たす候補があるのに、スクリーンショット機能が使えない、または2回失敗した場合は`BLOCKED`であり、`READY_WITHOUT_ASSETS`へ変換しない。画像がないことだけで記事本文の品質を不合格にしない。

## 次工程の受理条件

次工程は各画像について次を確認する。

1. `schema_version`を受理できる。
2. `absolute_path`が実在し、承認済み`asset_root`内にある。
3. 現在のSHA-256が`sha256`と一致する。
4. `rights.status`が`allowed`で、`article_publication_allowed`が`true`である。
5. 加工して使う場合は`modification_allowed`が`true`である。
6. `attribution_required`が`true`なら`required_attribution`を保持できる。
7. 記事本文の主張と`intended_claims`が一致する。
8. `mobile_check.status`が`pass`でない場合は、次工程自身で表示可否を再判断する。
9. 1.2では`capture_attempts`があり、視覚化対象がある場合は少なくとも1件の試行記録がある。

一つでも満たさない画像は使用せず、親へ理由を返す。次工程は画像の配置権限を別途持つ必要があり、この契約だけを記事編集許可として扱わない。

## 互換性

- 子スキルは`capture_preferences`のない従来入力を`best_available`として受理できる。
- 親記事スキルは1.1と1.2を読み取れる。
- 旧契約で実行する親記事スキルの新規自動スクリーンショット工程は1.2だけを完了扱いにする。1.1に画像があっても、試行記録がないため自動スクリーンショット完了とは報告しない。
- 1.1の下流利用者へ渡す必要がある場合は、1.2を黙って縮退させず、未対応として報告する。

## スキーマ1.3: 親主導の候補探索と取得

スキーマ1.3では`capture_phase`を必ず明示する。`full`は省略時の既存スキーマ1.2方式であり、新しい親工程には使わない。親工程は最初に`discover`を実行し、親が候補を受理した後だけ`capture`を実行する。

### `discover`入力と出力

```yaml
evidence_capture_request:
  schema_version: "1.3"
  run_id: ""
  capture_phase: discover
  design_version: ""
  authorization: {}
  article:
    article_id: ""
    title: ""
    main_keyword: ""
    target_reader: ""
    purpose: ""
    final_body_markdown: ""
    sections: []
  capture_mode: analyze_final_body
  capture_preferences:
    strategy: best_available
    method_priority: [element_screenshot, pdf_region_capture, viewport_screenshot, direct_download]
    max_claims_per_article: 3
    max_assets_per_claim: 1
    require_attempt_when_visual_claim_exists: false
  proposed_output_directory: ""
  asset_constraints: {}
  search_limits: {}
  consumer:
    name: null
    accepted_schema_versions: ["1.3"]
```

`discover`では`final_body_markdown`と安定した見出しIDを持つ`sections`を必須とする。`explicit_requests`、取得試行、ファイル保存は受理しない。候補探索が完了しても、未取得の`actual_method`、ハッシュ、モバイル検査、保存済み資産を記録しない。

```yaml
evidence_discovery:
  schema_version: "1.3"
  run_id: ""
  article_id: ""
  design_version: ""
  status: CANDIDATES_READY # CANDIDATES_READY | NOT_APPLICABLE | READY_WITHOUT_ASSETS | BLOCKED
  candidates:
    - candidate_id: ""
      request_id: ""
      section_id: ""
      intended_claim: ""
      source_url: ""
      source_type: official_company # official_company | public_body | academic_or_professional_body | authoritative_editorial_media
      publisher: ""
      target_region: "" # 対象要素またはページ領域を一意に特定する記述
      preferred_method: element_screenshot
      allowed_fallback_methods: []
      rights:
        status: allowed
        basis_type: official_terms
        basis_url: ""
        checked_at: ""
        local_save_allowed: true
        article_publication_allowed: true
        modification_allowed: false
        attribution_required: true
        required_attribution: ""
      modification: none
      proposed_path: ""
      asset_constraints: {}
  skipped_sources: []
  checks:
    analysis_complete: true
```

`CANDIDATES_READY`は、権利と対象領域を確認した取得候補が1件以上ある状態であり、取得済みを意味しない。視覚化する主張がなければ`NOT_APPLICABLE`、探索しても保存・掲載条件を満たす候補がなければ`READY_WITHOUT_ASSETS`、必須入力や探索手段が不足すれば`BLOCKED`にする。`skipped_sources`には確認済みのURLと理由だけを記録し、未実施の結果を補わない。

### `capture`入力と出力

```yaml
evidence_capture_request:
  schema_version: "1.3"
  run_id: ""
  capture_phase: capture
  design_version: ""
  authorization: {}
  article:
    article_id: ""
    final_body_markdown: ""
    sections: []
  capture_mode: explicit_requests
  capture_preferences:
    strategy: best_available
    method_priority: [element_screenshot, pdf_region_capture, viewport_screenshot, direct_download]
    max_claims_per_article: 3
    max_assets_per_claim: 1
    require_attempt_when_visual_claim_exists: false
  explicit_requests:
    - request_id: ""
      section_id: ""
      intended_claim: ""
  selected_candidates: [] # discovery.candidatesの完全なレコードだけ
  proposed_output_directory: ""
  asset_constraints: {}
  search_limits: {}
  consumer:
    name: null
    accepted_schema_versions: ["1.3"]
```

`capture`では`explicit_requests`、`selected_candidates`、`design_version`を必須とする。各選定候補は`discover`が返した完全な候補レコードでなければならない。各`selected_candidates[]`は、`request_id`、`section_id`、`intended_claim`が完全一致する1件の`explicit_requests[]`と対応し、各`explicit_requests[]`も同じ3項目で1件の選定候補に対応することを確認する。`request_id`、`section_id`、`intended_claim`、`source_url`、`target_region`、取得方法、権利、加工、保存先、制約を子が変更してはならない。取得前の再確認で不一致または不許可を見つけた場合は、保存せず`BLOCKED`と次を返す。

```yaml
change_request:
  candidate_id: ""
  problem: ""
  evidence: ""
  proposed_change: ""
  impact: ""
```

空の`selected_candidates`を親の成功状態へ変換しない。親が`NOT_APPLICABLE`または`READY_WITHOUT_ASSETS`として完了させるには、対応する`evidence_discovery`の実物を確認する必要がある。候補が`CANDIDATES_READY`であるだけでは、`capture`の成功や画像の取得完了にはならない。

`capture`は既存の`evidence_capture`の資産・試行・検査・状態規則を使い、次の差分を加える。

```yaml
evidence_capture:
  schema_version: "1.3"
  capture_phase: capture
  used_design_version: ""
  selected_candidate_ids: []
  assets:
    - candidate_id: ""
```

資産の各`candidate_id`は`selected_candidate_ids`に含まれ、元の選定候補と一致しなければならない。`actual_method`、`capture_attempts`、ハッシュ、モバイル検査は、実施済みの結果だけを記録する。親または下流UIはスキーマ1.3を受理できることを明示し、既存の1.2受理条件に加えて`candidate_id`、`used_design_version`、`selected_candidate_ids`を検証する。未対応の消費者へ1.3を黙って縮退させない。

スキーマ1.3は、スキーマ1.2の`authorization`、`asset_constraints`、`search_limits`、`capture_preferences`の戦略・方法順・上限・試行条件、情報源適格性、権利、保存、試行、検査、状態の規則を継承する。1.3入力でこれらを省略または緩和しても、1.2の制約は緩和されない。
