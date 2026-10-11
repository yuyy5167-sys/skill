# H2見出し画像

## 目的と適用範囲

Cloudflare/Astro教育ブログの記事で、サムネイルの画風が確定した後に各Markdown H2の直下へ置く16:9画像を設計、生成、検品、限定挿入する。記事本文の執筆、見出し変更、公式根拠画像の収集、CSS、`coverImage`、公開は扱わない。

この文書は `asset_scope: thumbnail_and_h2 | h2_only` の場合だけ読む。サムネイル固有の小型カード、`object-fit: cover`、`-thumbnail.` CSSの検査をH2画像へ流用しない。

## 1. 入力と適用状態

```yaml
asset_scope: thumbnail_and_h2 | h2_only
article_path: ""
target_grade: elementary | junior_high | high_school | multi_grade | unknown
authorization_mode: standalone_interactive | orchestrated_prepublication
parent_run_id: null
allowed_output_directory: ""
article_edit_authorized: false
execution_mode: full | design_only | render_from_plan
```

Markdown本文に対象H2がない場合は次を返し、生成や記事変更をしない。

```yaml
applicability: not_applicable
not_applicable_reason: no_markdown_h2
status: null
```

## 2. H2と既存画像を識別する

本文のATX H2 `## ` を対象にする。frontmatter、コードフェンス、HTMLコメント、引用内の見出し風文字列、H3以下、レイアウト側で生成される見出しは数えない。

H2見出し画像は次をすべて満たすものとする。

- H2後の空行とHTMLコメントを除く最初の有効な本文要素
- Markdown画像
- 対象記事内のローカル `images` フォルダにある
- ファイル名が `h2-` で始まる
- altが空でない
- 16:9のWebP

公式スクリーンショット、引用画像、グラフなどの根拠画像はH2見出し画像として数えない。根拠画像がH2直後にある場合は、新しいH2見出し画像をその前へ置き、根拠画像を変更しない。

既存のH2画像が本文途中にある場合は、見出し、alt、パスから対応が一意な場合だけMarkdown参照を直下へ移す。判断できない場合は重複追加せず `BLOCKED` とする。

## 3. 画風を文章契約で固定する

[スタイル文法](style-grammar.md) の `h2_style_profile_v1` 固定プロンプトブロックを使う。画風見本、完成サムネイル、過去のH2画像、構図見本を画像生成へ直接渡さない。

固定プロンプトブロックだけを、`style-grammar.md` の正規化規則でSHA-256へ変換し、次を保持する。今回の文字方針はrevision 2であり、revision 1の空コピーや旧承認を新しい検査結果として流用しない。

```yaml
section_style_contract:
  profile_id: h2_style_profile_v1
  revision: 2
  sha256: ""
  mode: text_contract_only
  direct_style_images_sent_to_generator: false
  examples_opened: not_required
```

サムネイルの承認済み設計と生成後検品から、必要な差分だけを文章化する。

```yaml
runtime_style_delta:
  source: approved_thumbnail_plan | existing_approved_plan | base_profile_only
  line_weight: ""
  background_temperature: ""
  palette_adjustment: ""
  typography_touch: ""
  watercolor_strength: ""
  composition_inherited: false
  subject_position_inherited: false
  props_inherited: false
```

サムネイル未生成時はH2の意味と構図まで設計できるが、`final_prompt_status: pending_thumbnail_style_delta` とし、最終プロンプトを固定しない。

`h2_only` で過去の承認済みサムネイル設計が取得できない場合は、完成画像から差分を推測せず `source: base_profile_only` として各差分を空にする。この場合も `h2_style_profile_v1` だけで画風が成立するため、差分不足を理由に停止しない。

## 4. 人物と構図見本

人物を使う場合は [キャラクターシート](character-sheets.md) の実行時点の状態を正本とし、パス、可読性、状態、実測SHA-256を確認する。状態や期待SHA-256をこの文書へ複製しない。

- activeな正本だけを人物同一性のため画像生成へ渡せる。
- 人物が必須でなく正本が未確定なら人物なしへ切り替える。
- 人物が必須で正本が未確定なら `BLOCKED` とする。
- 別学年、過去画像、画風見本、構図見本から人物を補完しない。
- 継承するのは髪型、顔立ち、年齢感、体格、服、人物固有配色だけとし、ポーズ、位置、背景、小物、構図はH2から新しく決める。

`composition_guide` は記事本文だけで構図を作れない場合の任意参照とする。

- 汎用1枚と対象学年1枚まで。
- Codexが目視し、`viewed_and_transcribed` と記録する。
- 画像生成へ直接渡さない。
- 情報の流れ、場面の関係、動作だけを文章化する。
- 鉛筆線、グリッド、枠、セル番号、仮文字、人物外見を継承しない。
- 特定セルを複製しない。

使用した `character_sheet` と `composition_guide` だけ、既存スキルの `reference_integrity` で照合する。期待値を自動更新しない。H2の文章スタイル契約には画像SHA-256を要求しない。

## 5. H2ごとの設計

```yaml
section_image_plan:
  asset_id: ""
  heading: ""
  section_summary: ""
  one_glance_meaning: ""
  narrative_angle: ""
  information_structure: ""
  dominant_motif: ""
  supporting_motifs: []
  character_mode: person | personless
  character_sheet_paths: []
  composition_family: ""
  composition_guide_paths: []
  focus_position: left | center | right
  reading_order: []
  exact_copy: []
  textless_exception: null # 明示ユーザー指示の原文と対象asset_id
  facts_allowed: []
  forbidden_implications: []
  elements_to_exclude: []
  output_filename: ""
  style_profile_id: h2_style_profile_v1
  style_profile_revision: 2
  style_profile_sha256: ""
  runtime_style_delta: null
  final_prompt_status: pending_copy | pending_thumbnail_style_delta | ready
  pre_generation_review: {}
```

各H2の要点を大きな短い文字で原則1〜2ブロックにする。上限3ブロックは維持し、H2全文を貼る義務や小さな説明文・注釈は設けない。数値を使う場合は確認済みの条件も誤解なく伝える。`exact_copy` を確定し、空の未確定コピーは `pending_copy` とする。[文字の契約](diversity-quality-gates.md#6-文字)の有効な例外だけは文字なしにでき、その原文と当該asset_idを `textless_exception` に保持する。

構図候補は `single_focal_object`、`split_contrast`、`three_step_sequence`、`object_and_person`、`data_emphasis`、`cause_and_support`、`inspection_scene`、`focal_learning_scene` から記事に合うものを選べる。機械的にローテーションしない。

隣接画像で同じ構図群が続くことは原則避ける。同じ構図が最も明快な場合は、主役モチーフ、焦点位置、読む順番、背景構造、人物の有無・動作のうち2項目以上に実質的な違いを作る。左右反転、色、文言だけの変更は差別化に数えない。

## 6. 最終プロンプトを組み立てる

最終プロンプトは次の順に固定する。

1. H2、`one_glance_meaning`、モチーフ、情報構造、構図、焦点、読む順番
2. `style-grammar.md` の固定プロンプトブロック
3. `runtime_style_delta`
4. `exact_copy` の全確定文字列を画像内に描く指定。有効な `textless_exception` がある場合だけ、該当資産の文字を入れない指定
5. 有効な人物正本がある場合だけ人物同一性の指定
6. `forbidden_implications` と `elements_to_exclude`

必ず次を含める。

- 指定外の文字、疑似文字、ロゴ、透かしを追加しない。
- 小さな説明文を入れない。入らなければ意味を保って短縮し、要点の文字を残す。全文字の削除や縮小で解決しない。
- 文字用の四角い枠、カード、帯、吹き出しを原則使用しない。判読に不可欠な場合だけ輪郭線のない淡い色面を使う。
- 過去画像や構図見本の配置を再現しない。
- 未確認の数値、料金、評価、順位、日付、サービス画面を創作しない。

## 7. 実行モードと生成承認

`full` はサムネイルの画風確定後、既存の生成前・生成後ゲートを各H2へ適用して順番に生成する。

`design_only` は `section_image_designs` だけを返し、画像生成、保存、記事変更をしない。画風差分が未確定なら最終プロンプトを作らない。

`render_from_plan` は画像1枚を1資産として扱い、次を先に返す。

```yaml
generation_request:
  asset_id: ""
  request_id: ""
  design_version: ""
  style_profile_sha256: ""
  final_prompt: ""
```

親の `generation_approval` と全項目が完全一致し、未消費の場合だけ生成する。スタイル契約、実行時差分、固定文字列、構図、モチーフ、最終プロンプトのいずれかを変えた場合は旧承認を失効させ、新しい `request_id` を発行する。別H2、再生成、画像編集へ承認を流用しない。

## 8. 生成・修正・差別化

[差別化・品質ゲート](diversity-quality-gates.md) から、記事との意味一致、事実・権利の安全性、二層フィンガープリント、日本語完全一致、画像単体読解、修正計画、停止条件を再利用する。

小型記事カード、`object-fit: cover`、`-thumbnail.` CSS、サムネイル一覧での識別、`thumbnail_message` 固有出力はH2画像へ適用しない。同文書の出力規格にある「記事本文変更は対象外」はサムネイル経路の境界として扱い、H2画像ではこの文書の承認済み画像参照の限定挿入規則を優先する。それ以外の本文変更禁止は維持する。

文字の誤りは対象文字だけを指定して最大2回修正する。文字量が原因なら要点・条件を保って短縮し、コピーを変更した設計と再照合する。2回修正しても確定文字に一致しない場合は不採用とし、文字を削除して合格にしない。同じ根本原因が2回続いた場合は微修正をやめ、意味、主役、情報構造、構図から再設計する。

## 9. 全画像合格後に一括反映する

1. 全H2の設計を確定する。
2. 全画像を生成し、各画像を目視する。
3. 文字、人物、構図、事実、形式を全件検査する。
4. 1枚でも `BLOCKED` なら、部分反映の明示指示がない限り記事本文を変更しない。
5. 全件合格後、未使用ファイル名で対象記事の `images` フォルダへ保存する。
6. 保存後の全ファイルを再検査する。
7. H2直下の画像参照だけを1回の編集で記事へ反映する。
8. 記事検査、ビルド、実表示確認を行う。

保存途中で失敗した場合も記事を変更せず、作成済みの未参照ファイルを報告する。無断で削除しない。

本文変更は、承認済み画像の直下挿入、承認済み新バージョンへの参照差し替え、対応が一意な既存H2画像参照の直下移動だけに限定する。本文、見出し、frontmatter、CSSを変更しない。

## 10. 機械検査と実表示

保存画像は既存の `scripts/check-thumbnail.ps1` を再利用し、1536×864、16:9、WebP、容量を確認する。記事構造は `scripts/check-h2-images.ps1` で次を確認する。

- Markdown本文のH2数とH2見出し画像数
- 各H2直下の最初の有効要素
- `h2-` ファイル名、ローカル `images` 内への解決
- alt、ファイル実在、重複パス
- 各画像の形式、寸法、容量

H2画像は記事本文幅の320px、375px、390px、768px、1280pxで確認する。画像全体、文字、数字、矢印、主役、横はみ出し、縦横比、不要な枠を検査する。記事カード用の切り抜き検査は使わない。

## 11. 出力

```yaml
section_images:
  applicability: applicable | not_applicable
  not_applicable_reason: null | no_markdown_h2 | thumbnail_only_scope
  status: null | PREVIEW_READY | FINAL_ASSET_READY | BLOCKED
  style_profile_id: h2_style_profile_v1
  style_profile_revision: 2
  style_profile_sha256: ""
  direct_style_images_sent_to_generator: false
  expected_h2_count: 0
  generated_count: 0
  saved_count: 0
  inserted_count: 0
  reference_integrity: {}
  items:
    - asset_id: ""
      heading: ""
      character_mode: person | personless
      composition_family: ""
      exact_copy: []
      textless_exception: null
      generation_request: null
      generation_approval: null
      output_path: null
      insertion_status: pending
      checks: {}
  integration:
    atomic_article_patch: true
    article_body_changed: false
    published: false
  pending: []
```

全対象H2について保存、限定挿入、本文幅の実表示検証まで完了した場合だけ `FINAL_ASSET_READY` とする。未実施の検査を `pass` にしない。
