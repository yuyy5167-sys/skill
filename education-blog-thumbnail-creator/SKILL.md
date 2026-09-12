---
name: education-blog-thumbnail-creator
description: Cloudflare/Astro教育ブログの記事内容と対象学年に合わせ、生成前レビューを通過した16:9サムネイルと、承認済み記事の各H2直下へ置く見出し画像を統一画風で生成・検証する。小学生・中学生・高校生向け記事のアイキャッチ作成・編集、またはH2見出し画像の作成・限定挿入に使用する。公式根拠画像の収集、本文執筆、coverImage更新、本番公開には使用しない。
---

# 教育ブログ サムネイル・H2画像作成

`C:\AIフォルダ\ブログ\site` の教育記事用サムネイルとH2見出し画像を、記事内容の伝達、学年別キャラクターの同一性、構図の差別化、生成前レビュー、実表示の可読性まで一貫して扱う。既存のサムネイルだけの依頼は従来どおり処理し、H2画像は明示または親から許可された記事だけで扱う。

## 資産範囲

入力の `asset_scope` は次を使う。

- `thumbnail_only`: サムネイルだけを設計・生成・検証する。単独のサムネイル作成・修正ではこれを既定とする。
- `thumbnail_and_h2`: サムネイルの画風が確定した後、本文中の全H2について見出し画像を設計・生成し、許可範囲内で直下へ挿入する。記事本文、画像保存先、記事編集権限が渡された記事制作ではこれを既定とする。
- `h2_only`: 既存サムネイルを変更せず、H2見出し画像だけを作成・修復する。

`thumbnail_and_h2` または `h2_only` では [H2見出し画像](references/h2-heading-images.md) を必ず読み、同文書の文章スタイル契約、参照分離、一括反映、本文幅検証に従う。H2画像では [差別化・品質ゲート](references/diversity-quality-gates.md) のうち同文書が列挙する品質判定だけを再利用し、サムネイル用の出力規格、カード検査、記事本文変更の対象外規則よりH2文書の限定挿入規則を優先する。Markdown本文にH2がない場合は `BLOCKED` にせず `applicability: not_applicable` とする。

## 親主導の実行方式

`execution_mode`を省略した場合は、従来どおり`full`とする。`full`では以下の各節を担当エージェントが一貫して実行し、既存の生成・検品・保存権限と品質条件を維持する。

- `design_only`: 親エージェントだけが使う。選択した `asset_scope` に応じて第1〜5節の `thumbnail_design` と、必要なら `section_image_designs` を返し、画像生成、編集、保存、記事変更をしない。サムネイル生成前で画風差分が未確定のH2設計は `final_prompt_status: pending_thumbnail_style_delta` とする。返却時は画像資産の`status`と`output`を`null`にする。
- `render_from_plan`: 子エージェントだけが使う。親が確定した `asset_type: thumbnail | section_image` の設計を忠実に実現する。親設計を再導出、再解釈、置換しない。H2画像は1枚を1資産として扱い、別H2の承認を流用しない。

`render_from_plan` のサムネイルでは、`thumbnail_design.article_id`、`design_version`、`thumbnail_message`、`selected_concept`、完全な`image_plan`、`reference_manifest`、`pre_generation_review`がすべて必須である。H2画像では、[H2見出し画像](references/h2-heading-images.md) の完全な `section_image_plan`、文章スタイル契約の版とSHA-256、`runtime_style_delta`、`pre_generation_review`を必須とする。不足、矛盾、未確認の資料があれば補完せず、`handoff_status: needs_parent_input`と`change_request`を返す。

`render_from_plan`の制作サブは、親の確認記録だけで済ませず、プロンプト化の前に`reference_manifest`内の必要なキャラクター正本、画風見本、構図見本、比較画像を自ら開いて確認する。これはメッセージ、コピー、構図を再導出する作業ではなく、親設計どおりの参照を使えることの確認である。必要な参照を開けない、または親の記録と一致しない場合は生成せず、`needs_parent_input`を返す。

親から渡された設計は、サムネイルの保存・記事変更・公開の権限を拡張しない。`render_from_plan`でも、既存の生成後検品、保存境界、実表示検証、品質不合格時の停止条件をそのまま守る。

## 正本と役割分担

- 毎回 [差別化・品質ゲート](references/diversity-quality-gates.md) を読む。
- 人物を使う場合は生成前に [キャラクターシート](references/character-sheets.md) を読む。
- サムネイルを設計する前に [スタイル文法](references/style-grammar.md) を読む。記事から構図候補を作った後、通常実行でも登録済みの承認見本を1〜2枚目視し、画風・文字・余白を合わせる。人物同一性の正本とは区別する。
- H2画像では [スタイル文法](references/style-grammar.md) の `h2_style_profile_v1` を文章契約として使う。画風見本、完成サムネイル、過去のH2画像を画像生成へ直接渡さず、画風見本の目視可否をH2資産の完成条件にしない。
- 参照の役割を `character_sheet`、`style_example`、`composition_guide`、`comparison_image` に分ける。人物の同一性、完成画風、構図候補、差別化比較を相互に代用しない。優先順位と詳細は各参照文書に従う。
- 画像の新規生成・編集は `$imagegen` に委ねる。このスキルは記事分析、参照選択、プロンプト固定、差別化判定、検品、保存境界を担当し、画像生成ツール固有の手順を複製しない。
- 記事へ保存・統合する前は `C:\AIフォルダ\ブログ\クラウドフレア\記事装飾ルールブック.md` の現行版も読む。読めない場合は保存・統合を止める。

正本が読めない、対象学年を一意に決められない、人物を使うのに対応シートを確認できない場合は推測で補わず `BLOCKED` を返す。

## 対象外

- [H2見出し画像](references/h2-heading-images.md) が許可する画像参照の追加・差し替え・移動以外の記事本文変更
- frontmatter、共通CSS、既存画像ファイルの変更
- 公式情報を示す根拠画像やスクリーンショットの収集
- ロゴ、教材画面、評価、料金、順位、日付、キャンペーン条件の創作
- commit、push、デプロイ、本番公開

これらが必要なら、対応する工程または別スキルへ引き渡す。

## 1. 入力を固定する

まず記事本文または承認済み記事設計を読み、次を埋める。

```yaml
article_title: ""
article_path: ""
target_grade: elementary | junior_high | high_school | multi_grade | unknown
target_reader: ""
article_type: recommendation | review | pricing | how_to | trouble | study_method | experience | campaign | other
reader_problem: ""
article_conclusion: ""
desired_action: ""
thumbnail_copy: []
textless_exception: null # 指示原文と対象asset_idがある場合だけ
character_mode: person | personless | undecided
visual_motif: ""
layout_archetype: ""
primary_prop: ""
focus_position: left | center | right
authorization_mode: standalone_interactive | orchestrated_prepublication
parent_run_id: null
allowed_output_directory: ""
execution_mode: full | design_only | render_from_plan
asset_scope: thumbnail_only | thumbnail_and_h2 | h2_only
thumbnail_design: null
section_image_designs: []
generation_approval: null
```

- タイトルだけで記事の結論を決めない。利用できる場合は本文、見出し、設計書を優先する。タイトルしかない場合は、明示されている学年、教材・サービス、記事タイプ、中心テーマだけを使い、評価、結論、料金、順位、口コミ内容を創作しない。
- 記事本文、記事設計、確認済み事実から、[差別化・品質ゲート](references/diversity-quality-gates.md) の `thumbnail_message` を `thumbnail_copy` とは独立して導出する。ユーザー指定コピーから記事の意味を逆算しない。
- 主題、中心メッセージ、本文へ任せる説明を分ける。主質問と読む価値を示す形でもよく、結論の全説明は不要。補足は誤解防止または価値の具体化に必要な場合だけ使う。条件を省くと誤解する主張は条件を残すかコピーを変更する。自作コピーも生成前に固定し、変更時は記事との一致と文字配置を再確認する。
- ユーザー指定の `thumbnail_copy` は生成前に完全一致の文字列として固定し、`thumbnail_message` との意味、事実、権利の整合を生成前レビューで確認する。整合する場合は指定文字列を優先する。事実、権利、中核メッセージと矛盾する場合は入力固定または根拠確認へ戻し、無断で別の意味へ変更しない。
- `thumbnail_copy` が既存の文字数目安を明らかに超える場合は入力段階で早期警告する。本格的な過密判定は完成予定図と生成前レビューで行い、長すぎる場合は再生成前に短い文言案を提示して `revise` とする。タイトル全文を詰め込まない。
- サムネイルには記事の主題が伝わる短いタイトル文字を標準で入れる。コピー指定がなければ記事から設計し、`image_plan.exact_copy` を確定する。文字なしの例外と生成可否は [文字の契約](references/diversity-quality-gates.md#6-文字) を正本とし、H2にも適用する。
- `authorization_mode`を省略した場合は`standalone_interactive`とする。明確なタイトルと学年がある「サムネイルを作成して」という依頼は画像プレビュー生成の承認として扱えるが、保存と`coverImage`更新は別の明示承認を必要とする。
- `orchestrated_prepublication`は、`cloudflare-seo-article-creator`がキーワードと新規記事作成指示から作成した1記事限定の承認参照を渡し、保存先がその新規記事の`images`内、既存ファイル上書きなし、公開禁止の場合だけ受理する。このモードでは生成前レビューを通過した最良案を追加の承認待ちなしで保存できる。`coverImage`更新は親スキルが新規記事へ行う。
- `execution_mode: design_only`では、親が第1〜5節の設計を完了してから`thumbnail_design`を返す。第6節以降を実行しない。`execution_mode: render_from_plan`では、入力の`thumbnail_design`を第1〜5節の確定結果として扱い、既存の自律的な記事分析・構図選定・コピー変更の規則より優先する。
- `asset_scope` を省略した場合は、単独のサムネイル依頼では `thumbnail_only`、H2画像作成を含む明示依頼または親から記事本文・保存先・記事編集権限が渡された記事制作では `thumbnail_and_h2` とする。権限不足を既定値で補わない。
- 学年、文言の意味、3人以上の人物、変動情報、既存画像の編集対象、保存先が曖昧で結果が変わる場合だけ確認する。

## 2. 参照状態を確定する

人物を使う場合は [キャラクターシート](references/character-sheets.md) の対応を守り、各参照を次のいずれかで記録する。

```yaml
reference_mode: direct_image_reference | viewed_and_transcribed | reference_unavailable
```

- `direct_image_reference`: 生成処理へ正本画像を直接渡せる。
- `viewed_and_transcribed`: Codexが正本画像を目視し、同一性の特徴をプロンプトへ具体化できる。生成後も正本と横並びで照合する。
- `reference_unavailable`: 正本を確認できない。人物を生成せず、人物なし案へ切り替えるか `BLOCKED` とする。

中学生の既存2枚は同じ人物セットとして一致しておらず、正式な正本が未確定である。人物が不要なら人物なし案へ切り替え、人物が必要なら正本が指定されるまで `BLOCKED` とする。どちらかを推測で選ばず、構図見本や過去画像から人物を補完しない。

使用する参照画像は、パス、画像としての可読性、登録上の役割と状態、実測SHA-256を確認する。期待SHA-256はキャラクター正本については [キャラクターシート](references/character-sheets.md)、画風見本と構図見本については [スタイル文法](references/style-grammar.md) を正本とする。不一致時は期待値を自動更新せず、`reference_integrity`へ記録する。人物変更は生成を停止し、役割変更は`needs_parent_input`とする。

`style_reference_changed`は完成画風見本の変更だけに使う。キャラクター正本や構図見本の変更は`reference_integrity`だけへ記録する。特定の画像ライブラリだけがWebP等を読めない場合は破損と断定せず、実際に開ける別手段で確認する。

## 3. 比較対象を選ぶ

`C:\AIフォルダ\ブログ\site\src\content\blog` のMarkdownを列挙し、frontmatterの実在する `coverImage` だけを候補にする。

- 含める: 公開記事と有効な下書きの現在の `coverImage`
- 除外する: `__trashed`、本文内だけの画像、存在しないパス、同一記事の旧版・不採用版
- 直近5枚: frontmatterの `date` 降順。欠損時と同日内は記事ファイル更新日時を補助にする。
- 追加比較: 同じ学年、同じ教材・サービス、同じ記事タイプ

棚卸しが完了しない場合は類似判定を `pass` と報告しない。確認できた範囲と不足を示す。

## 4. 完成予定図を作る

[差別化・品質ゲート](references/diversity-quality-gates.md) に従い、記事タイプに対応する視覚モチーフと構図を選ぶ。

- 人物は必須ではない。人物なし案を常に有効な選択肢にする。
- 記事から導出した `thumbnail_message` を基に、成立する複数の方向があれば意味の異なる軽量なコンセプト案を検討する。ユーザー指定の比較案数を優先し、通常時は案数を埋めるために不要な案を作らない。これは生成前の設計案であり、生成枚数ではない。
- 各案では `narrative_angle` と `information_structure` を分け、少なくとも一方に意味上の違いを持たせる。記事適合性、事実・権利の安全性、小型カード耐性、視覚化可能性、差別化、生成可能性がすべて合格した案から、独自性より明快さと記事適合性を優先して1案を選ぶ。
- 色、数字、装飾の変更だけで別案にしない。
- 生成前に視覚面の6項目フィンガープリントと意味面のフィンガープリントを、セクション3で確定した同じ比較対象と照合し、どちらかの不採用条件に該当する案を作り直す。

構図候補を作った後、[スタイル文法](references/style-grammar.md)の承認見本を確認し、継承する画風・文字・余白と転用しない配置・動作を明示する。生成へ渡せる見本は用途を付けて渡す。目視だけの場合も生成後に見本と照合する。参照画像の実レイアウトを見たこと自体は不合格ではないが、候補が見本の配置へ理由なく変わっていないか再確認する。

[スタイル文法](references/style-grammar.md) の構図見本は必要な場合だけ目視し、記事固有の構図へ変換する。構図見本は画像生成へ直接渡さず、`viewed_and_transcribed`として扱う。鉛筆ラフの画風、人物の外見、セル番号、枠線、グリッド、仮文字を継承しない。

画像生成前に、完成予定図を次の形で具体化する。

```yaml
image_plan:
  article_message: ""
  exact_copy: []
  textless_exception: null # 明示ユーザー指示がある場合だけ {user_instruction, asset_scope: [対象asset_id]}
  target_grade: ""
  character_or_personless: ""
  character_sheet_paths: []
  visual_motif: ""
  composition: ""
  text_position: ""
  subject_position: ""
  primary_prop: ""
  background_structure: ""
  focus_position: ""
  style: "clean editorial line art with very subtle watercolor texture"
  crop_and_safe_margin: ""
  elements_to_exclude: []
```

## 5. 生成前に設計をレビューする

画像生成や画像編集を呼ぶ前に、[差別化・品質ゲート](references/diversity-quality-gates.md) の生成前レビューを行う。

- 記事適合、文字、キャラクター、構図、画風、差別化、生成可能性を確認する。
- 上の詳細検査を廃止せず、記事適合、事実・権利の安全性、小型カード耐性、視覚化可能性、差別化、生成可能性の6つを上位ゲートとしてすべて確認する。対応関係は [差別化・品質ゲート](references/diversity-quality-gates.md) に従う。
- 発見した問題と修正内容を記録し、修正後は変更箇所だけでなく完成予定図全体を再確認する。
- 記事の意味、正確性、可読性、キャラクター同一性、画風、差別化に影響する未解決問題がある間は生成しない。
- 発見した問題と影響箇所を修正・再確認し、必要な品質条件を満たしたら `pass` とする。レビュー全体を自動反復したり、回数を満たすためのレビューを行ったりしない。
- 必要な資料や判断が不足する、または修正しても改善しない場合は、推測で生成せず `BLOCKED` とする。

```yaml
pre_generation_review:
  result: pass | revise | blocked
  problems_found: []
  corrections_applied: []
  unresolved_problems: []
```

## 5.5 親設計からの生成承認

`render_from_plan`では、`thumbnail_design.design_version`、`used_design_version`、`generation_request.design_version`が一致し、`pre_generation_review.result: pass`であっても、画像生成・画像編集を始めない。最初に次を親へ返す。

```yaml
handoff_status: prompt_ready
status: null
generation_request:
  asset_id: "thumbnail"
  request_id: ""
  design_version: ""
  style_profile_sha256: null
  final_prompt: ""
generation_approval: null
```

承認が未到着なら、`handoff_status: prompt_ready`、`status: null`、`generation_approval: null`を維持し、生成しない。親がサムネイルでは`generation_approval: {asset_id, request_id, design_version, final_prompt, result: pass}`、H2画像ではこれに`style_profile_sha256`を加えた承認を返した場合だけ、全項目が`generation_request`と使用設計に完全一致することを確認して生成する。既存の `asset_id` を持たないサムネイル承認は互換入力として `asset_id: thumbnail` と解釈できるが、H2画像では `asset_id` を必須とする。

承認が不一致または`result`が`pass`以外の場合は、`handoff_status: needs_parent_input`、`status: null`、`generation_approval: null`にし、`change_request`へ不一致の項目、受信値、期待値、影響を記録する。設計版または最終プロンプトが変わった時点で、旧承認は履歴だけとし、activeな`generation_approval`として使わない。承認を消費して生成を開始した時点でも、その承認を`generation_approval_history`へ移し、activeな`generation_approval`は`null`に戻す。初回生成、再生成、画像編集のたびに新しい`request_id`で承認を求め、同じ`request_id`の承認は一度だけ消費する。生成結果が不明な場合は、自動再実行せず親へ結果確認または新しい要求を返す。

## 6. プロンプトを固定して生成する

`full`は従来どおりこの節から生成できる。`render_from_plan`は第5.5節の一致する未消費の承認を受け取った後だけ、この節のプロンプトを実行できる。最終プロンプトは承認済みの`generation_request.final_prompt`から1文字も変更しない。

`$imagegen` へ次を明示する。

- 16:9。1536×864pxを希望寸法とするが、プレビューでは画像生成ツールのネイティブな16:9出力も許容する
- 記事の中心メッセージ、視覚モチーフ、構図、焦点位置
- `image_plan.exact_copy` の確定した日本語文字列をすべて画像内へ描き、指定外の文字は追加しないこと。文字なし指定は [文字の契約](references/diversity-quality-gates.md#6-文字) の例外が有効な場合だけ使う
- 使用するキャラクターシートの絶対パスと参照モード
- 人物の同一性、学年感、ポーズ、表情、主役小物
- [スタイル文法](references/style-grammar.md) の薄い水彩を含む標準画風、継承要素、固定してはいけない要素。ユーザーが別画風を明示した場合はその指示を優先する
- 顔、制服・服、主役小物へ文字を重ねない。文字・顔・意味を担う小物には各辺8%を目安に安全余白を取り、机・背景は端まで広げられる。実際の切り抜きで確かめること
- 見本ごとの役割と参照状態、継承する特徴、今回変える表現。文字は見本の自然な丸みと読みやすさを基準に、主見出しと補足を分け、絵の線・色の強さと釣り合わせること
- 実在ロゴ、透かし、未確認の数値・評価・キャンペーンを入れないこと

生成後の報告に使えるよう、実際に渡した最終プロンプトと生成モードを保持する。

初回から一律に二段階生成しない。構図、文字、人物が合格し、水彩質感だけが不足する場合に限り、構図、文字、人物、小物を保持して背景紙と色面だけへ薄い水彩質感を加える編集を候補にする。

## 7. 生成画像を検品し、修正前にもレビューする

`render_from_plan`で再生成または画像編集が必要になった場合、`revision_plan`を親設計と照合する。許可された構図・文字・画風の調整範囲を超える変更、またはメッセージ・コンセプト・コピーの変更が必要な場合は、実行せず`change_request`を親へ返す。裁量内の修正でも、第5.5節の新しい生成承認を受ける。

必ず画像そのものを開き、次を目視する。

- 対象学年、キャラクターの同一性、人物数
- 顔、手、姿勢、表情、主役小物の破綻
- 固定した日本語が実画像に存在し、1文字ずつ一致していて、余分な文字がない。文字なし画像は有効な例外がない限り不合格
- 文字切れ、顔・服・主役小物への重なり、安全余白
- ロゴ、透かし、未承認情報がない
- 16:9、構図、焦点位置
- 水彩が背景紙と色面に限定され、文字と輪郭がシャープである
- 既存比較対象との6項目の観察と意味面の照合、小さいカード表示での識別性。一致数だけでは不採用にしない
- 承認見本との画風・文字の釣り合い、場面の一体感、見本からの配置・動作の無批判な転用がないこと
- 画像と実際の記事カードだけを根拠に `image_only_readback` を先に記録し、その後で `thumbnail_message.one_glance_meaning` と比較する。同じ担当者が行う場合は独立評価とは呼ばない。
- 最初に読む要素が1つに定まり、対象テーマ、最重要メッセージ、補足の順が意図どおりで、意図しない空白、衝突、重なり、装飾過多がない

再生成や画像編集の前に、観測した問題、変更する箇所、保持する箇所、副作用の可能性を `revision_plan` にまとめ、[差別化・品質ゲート](references/diversity-quality-gates.md) で再レビューする。修正計画が `pass` になるまで画像を変更しない。

問題は `message`、`copy`、`hierarchy`、`concept`、`composition`、`style`、`render`、`accuracy`、`tool` に分類し、分類ごとの差し戻し先を使う。`accuracy` は画像編集で直さず、入力固定または根拠確認へ戻す。`message` または `concept` の不一致はコンセプト選定へ戻し、視覚上の問題は観測済みの主問題1つだけを修正する。

```yaml
revision_plan:
  observed_problem: ""
  change_only: ""
  preserve: []
  possible_side_effects: []
  review_result: pass | revise | blocked
```

誤字・文字化けは対象文字だけを指定して最大2回修正する。直らない場合は採用せず、文字を消して合格にしない。その他の修正も、一度に観測済みの主問題1つへ絞り、既に合格した要素を保持する。無限に再生成しない。

同じ根本原因が2回続いた場合は微修正をやめ、構造的に再設計する。表現角度が実質1つで意味面の類似判定に当たる場合は、角度を変える前に情報構造、主役モチーフ、視覚面の構図を変えて再確認する。固定回数で機械的に停止せず、改善が止まり、新しい判断材料もない場合にだけ理由と再開条件を付けて `BLOCKED` とする。

## 8. 保存・実表示を検証する

- `standalone_interactive`では保存承認後だけ、未使用のファイル名で記事の`images`フォルダへ保存する。
- `orchestrated_prepublication`では、親の`parent_run_id`、通知済み記事パス、`allowed_output_directory`が一致し、生成前レビューと生成後検品が合格した場合だけ、追加の承認待ちなしで未使用名へ保存する。
- どちらのモードでも既存ファイルを上書きしない。保存先や対象記事が承認範囲外へ変わる場合は`BLOCKED`にする。
- H2画像は全対象の生成後検品が合格するまで記事へ挿入しない。全画像を未使用名へ保存・再検査してから、H2直下の画像参照だけを1回の編集で反映する。1枚でも `BLOCKED` なら、ユーザーが部分反映を明示しない限り記事本文を変更しない。保存途中で失敗した場合も記事を変更せず、作成済みの未参照ファイルを報告し、無断削除しない。

- `FINAL_ASSET_READY`にする公開用画像はWebPとし、300KB以下を目標とする。
- プレビューが画像生成ツールのネイティブな16:9寸法の場合は、保存権限確認後に1536×864pxへ正規化してから公開用検査を行う。
- 500KB超は再圧縮し、再度目視する。
- `scripts/check-thumbnail.ps1` で形式、寸法、比率、容量を検査する。
- 記事カードまたは同等のレンダリングで320px、375px、390px、768px、PC幅を確認する。
- 各幅で、画像内の確定文字列を読め、対象テーマと最重要メッセージを再記述でき、第一読解、第二読解、補足の順が維持されることを確認する。カード外の見出しやサイトの重ね文字で画像内の文字不足を補って合格にしない。文字切れだけで実表示合格にしない。
- 現行CSSに `-thumbnail.` を含む画像を右寄せする規則があるため、ファイル名と実際の切り抜きを確認する。画像単体の確認だけで実表示合格にしない。
- 本スキルは`coverImage`を更新しない。サムネイルは`standalone_interactive`では別承認を得た掲載工程へ、`orchestrated_prepublication`では親スキルへ最終画像パスを引き渡す。H2画像は承認範囲内に限り、[H2見出し画像](references/h2-heading-images.md) の条件で本文へ限定挿入できる。

## 9. 状態と報告

資産の状態には次だけを使う。`design_only`、`render_from_plan`の承認待ち、または親入力待ちでは`status: null`とし、資産の完成状態を使わない。

- `PREVIEW_READY`: 生成画像の目視検品まで完了。単独利用では保存未承認、親経由では保存前検査中を表す。
- `FINAL_ASSET_READY`: 許可範囲内への保存、機械検査、実表示検査まで完了。`coverImage`更新や公開を意味しない。
- `BLOCKED`: 正本、承認、入力、生成品質、比較対象、検証環境の不足で必須条件を満たせない。

親との保留中の引継ぎ状態は、`design_ready`、`prompt_ready`、`needs_parent_input`だけを`handoff_status`へ入れる。これは`PREVIEW_READY`、`FINAL_ASSET_READY`、`BLOCKED`を表さない。

最終報告には次を含める。

```yaml
thumbnail:
  status: null | PREVIEW_READY | FINAL_ASSET_READY | BLOCKED
  execution_mode: full | design_only | render_from_plan
  handoff_status: null | design_ready | prompt_ready | needs_parent_input
  used_design_version: null
  authorization_mode: standalone_interactive | orchestrated_prepublication
  article_title: ""
  article_path: ""
  target_grade: ""
  article_type: ""
  exact_copy: []
  textless_exception: null # image_planと同じ原文・適用asset_id
  character_mode: person | personless
  character_sheet_paths: []
  reference_mode: direct_image_reference | viewed_and_transcribed | reference_unavailable | not_applicable
  examples_opened: false
  style_reference_changed: false
  reference_integrity:
    result: match | changed | unavailable | not_checked
    checked_at: ""
    changes: [] # 各要素: path, role, expected_sha256, observed_sha256, visual_role_consistent, action
  style_references: [] # 各要素: path, purpose, mode, inherited_features, not_to_copy
  variation_plan: [] # 記事から選んだ構図・動作・主役など
  body_only_details: []
  visual_comparisons: [] # 各要素: path, shared_features, differences_without_copy_or_color, result, reason
  visual_review: [] # 各要素: criterion, observed_location, result, reason
  generation_context:
    tool: ""
    model: null # 非公開なら推測しない
    settings: {}
    executed_at: ""
  visual_motif: ""
  layout_archetype: ""
  focus_position: left | center | right
  difference_summary: ""
  image_plan:
    article_message: ""
    composition: ""
    style: ""
  thumbnail_design:
    article_id: ""
    design_version: ""
    thumbnail_message: {}
    selected_concept: {}
    image_plan: {}
    reference_manifest: [] # 各要素: path, role(character_sheet | style_example | composition_guide | comparison_image), confirmation_status
    pre_generation_review: {}
  thumbnail_message:
    context: ""
    reader_focus: ""
    core_takeaway:
      kind: answer | change | choice | action | warning | outcome
      text: ""
    supporting_facts: []
    one_glance_meaning: ""
    forbidden_implications: []
  concept_directions: []
  selected_concept:
    narrative_angle: ""
    information_structure: ""
    dominant_motif: ""
    reading_order: []
    reason: ""
    visual_roles:
      subject_motif: ""
      conclusion_motif: null
      evidence_motif: null
      decoration: null
  semantic_fingerprint:
    result: pending
    compared_with: []
    difference_summary: ""
  pre_generation_review:
    result: pending
    problems_found: []
    corrections_applied: []
    unresolved_problems: []
  image_only_readback:
    perceived_context: ""
    perceived_focus: ""
    perceived_takeaway: ""
    perceived_support: ""
    observed_reading_order: []
    result: pending
  post_generation_review:
    result: pending
    dominant_problem: ""
    problem_class: ""
    change: ""
    preserve: []
    recheck: []
    attempt_count: 0
    blocked_reason: ""
    resume_condition: ""
  imagegen_mode: ""
  final_prompt: ""
  generation_request: null # request_id, design_version, final_prompt
  generation_approval: null # request_id, design_version, final_prompt, result: pass
  generation_approval_history: [] # 失効・不一致・消費済み承認を履歴として保持
  consumed_generation_request_ids: [] # 同じrequest_idの承認を再利用しない
  change_request: null # 該当設計、不足または矛盾、根拠、提案、影響範囲
  output:
    path: null
    width: null
    height: null
    format: null
    bytes: null
  checks:
    exact_japanese: pending
    character_identity: pending
    watercolor_strength: pending
    outline_crispness: pending
    typography_crispness: pending
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

実施していない検査は `pass` にしない。`checks.exact_japanese` は空配列の形式一致だけで合格にせず、[文字の契約](references/diversity-quality-gates.md#6-文字) に従い実画像の文字を照合する。判定の観測箇所と理由は既存の `visual_review` に、各表示幅の結果は `checks.rendered_widths` に保持する。人物なしの場合、`character_sheet_paths` は空配列、`reference_mode` は `not_applicable` とする。

`style_references[].mode` は `direct_image_reference`（目視・実際に生成へ引渡し済み）、`viewed_and_transcribed`（目視し特徴を指示へ変換）、`reference_unavailable`（目視不可）を使い、人物の `reference_mode` と別に記録する。`examples_opened` は実際の目視から設定する。全承認見本が目視不可なら `BLOCKED` とし、既存の試作は未検証として提示できるが `PREVIEW_READY` / `FINAL_ASSET_READY` にしない。

上の画風見本要件は `asset_type: thumbnail` に適用する。H2画像は文章スタイル契約を正本とするため、`examples_opened: not_required` とし、画風見本が開けないことだけでは停止しない。人物または任意の構図見本を使う場合は、それぞれの参照整合性を別途確認する。

既存の親設計に`composition_guide`や`reference_integrity`がなくても、それだけで拒否しない。制作側が登録表から期待値を取得して整合性を確認し、結果へ`reference_integrity`を追加する。既存設計に正本未確定の中学生人物が含まれる場合は生成せず、`handoff_status: needs_parent_input`、`status: null`として、正本指定または人物なし案への変更を`change_request`へ記録する。確定済み構図へ構図見本がないことを理由に再設計しない。

`six_field_similarity` は互換性のため名称を維持し、6項目の観察と小型表示に基づく判定を入れる。一致数の閾値ではない。サムネイル固有の追加項目は既存 `thumbnail` ブロック内で親へ引き渡す。H2固有の項目は兄弟要素 `section_images` に分け、状態名・保存条件・公開境界を変更しない。

H2画像の最終報告は [H2見出し画像](references/h2-heading-images.md) の `section_images` スキーマを使う。すべての対象H2について保存、限定挿入、本文幅の実表示検証まで完了した場合だけ `FINAL_ASSET_READY` とする。

スキル改訂の完了報告では、実装・形式確認、生成試験、ユーザーの好みとの適合確認を分ける。[改訂時の生成試験](references/diversity-quality-gates.md#11-スキル改訂時の生成試験)は試験を実施する際に使い、通常の記事1件ごとに6枚生成しない。
