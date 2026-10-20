# 新記事のA〜Eデザイン標準

2026-10-20承認。対象ブログで今後開始する**新規記事**の表示標準は `cream-manga-mustard-v1`。記事の事業目的、`article_profile.type`、文章の内容評価は独立して維持する。この標準を既存記事への一括適用、共通実装変更、本番公開の許可へ拡張しない。

## 選択と版管理

調査・主質問・対象読者・見出しを確定してから親が次を選ぶ。キーワードの語だけで自動選択しない。主型は一つ、補助部品は内容上必要な箇所だけ使う。

| design | 主な用途 | 主な表現 | 避けること |
|---|---|---|---|
| A | 教材の全体像・紹介 | 雑誌風の導入、要点と詳細の段差 | 全節を要約枠へ押し込む |
| B | 向き不向き・悩み・選び方 | 短い漫画導入、判断軸、対象別の整理 | 架空体験、会話の反復、劇的な失敗の捏造 |
| C | 料金・比較・条件 | 条件付き比較表、判断の結論 | 月額だけの比較、根拠のない順位 |
| D | 学習内容・科目・使い方 | 学習ノート風、具体例、段階 | 説明不足の手順化、全段落のカード化 |
| E | 疑問・退会・手続き | 質問→短い回答→条件と手順 | 注意書きや画像直後の最初の段落を自動で回答扱い |

同じCでも成約用は承認済みCTA、集客用は主成約記事への画像カード。大人向け手続き記事を子ども向け学習診断へ無理に誘導しない。

`article_visual_design` は `{profile, design, label, design_version, selection_reason, showMaterialFinder}`。`design_version` は正の整数で、見出し・対応画像・ブロック設計の変更時に更新する。UI・画像の受理記録を現行版へ対応させる。無関係な一文字修正だけで全画像を再生成せず、意味・コピー・構図が変わった資産の検査を無効化して再受理する。最終検査の `design_state` は `design_version / ui_used_design_version / thumbnail_accepted_design_version / section_images_accepted_design_version` を同一現行版として持つ。画像のaccepted版は子のused版を捏造した値ではなく、親が現行見出し・意味・コピー・保存資産との対応を再検収した版であり、その検収証拠を保持する。

## サイト基盤の事前確認

サイトの `src/lib/articleDesignMetadata.mjs`、strictなcontent schema、ルートのresolver、`ArticleReadingLayout.astro`、`article-editions.css` が接続されていることを確認する。`site_rendering_capabilities.article_design` へ profile、metadata_supported、origins、explicit_answer_supported、optional_end_finder_supported、registered_components と検証出典を記録する。未対応なら `design_migration_required`。通常の新規記事工程で共有CSS・辞書・ルートを編集しない。

解決順序は明示frontmatter→承認済み既存10記事のID辞書→従来表示。明示値が不正なら辞書へ逃がさず失敗する。既存記事は `legacy-map`、新設定は `frontmatter` のoriginを持つ。旧10件の短縮目次・Eの旧表示・末尾導線を維持し、新記事に旧位置依存CSSを適用しない。

新記事は次の4項目だけを保存する。labelは読者向けの短い日本語。schema上省略可能でも新規制作では必須。

```yaml
articleDesign:
  profile: cream-manga-mustard-v1
  design: C
  label: 料金の比較ガイド
  showMaterialFinder: false
```

`showMaterialFinder` は記事末尾の診断だけを指す。既存のフローティング診断ランチャーを操作する指定ではない。既定false、学年・読者・主質問に合い設計に記録した場合だけtrue。

## 子スキルとの接続

- UI: `design_mode: parent_directed`。子の完全な `ui_design`（全必須フィールド・全blockへのcomponent割当、plainを含む）を親が作る。`ui_design.article_design` へ上の4項目、`design_version` へ現行版を渡す。A〜Eだけ渡して設計完了にしない。受理後、画像挿入で追加された最終ブロックもcomponent mapと照合する。
- 画像: `visual_profile: {id: cream-manga-mustard-v1, revision: 1}` をサムネイルと全H2に共通適用。子の新profile固定文・SHA・参照契約を正本とし、旧ネイビー・コーラル・ミント・水彩の色指定を混ぜない。人物の顔・髪・年齢・体格・服の形は現行学年シートを保持し、変更許可は色→グレースケールだけ。承認済み母子の追加参照は任意で、役割・承認・path・SHAが確認できる場合だけ使用する。
- リンク: `articleDesign` に上の4項目。CTAの外観対応は `site_rendering_capabilities.article_design_profile`、各CTA部品の `appearance_profiles`、`rendered_page_checks.article_design_profile` で証明する。DOM・講座・href・1px計測・rel・件数・意味別配置は既存正本どおり。新profile限定の色変更をURL変更の許可へ広げない。

## 原稿と画像の統合順序

本文・根拠・目的別導線を受理→UI化→frontmatterと本文保存→画像子が全H2画像を生成・検品後、一括でMarkdown H2直下へ挿入→親が `coverImage` と導入サムネイル1枚を統合→最終component map・構造・導線・実表示を再検査する。未生成の画像パスを完成原稿へ先置きしない。

導入内に `<figure class="edition-thumbnail">` と意味あるaltのMarkdown画像を1枚、導入末尾に本物の `<!--article-lead-end-->` を1個置く。各H2はラッパーの外のMarkdown見出し、直下は `![alt](./images/h2-*.webp)`、続いて本文。Eの短答は明示的な `edition-answer`。注意書きは注意書きのまま残す。目次のHTMLを本文へ作らず、レイアウトが実際のH2から「目次」を1回生成する。

sourceとレイアウト入力HTMLは境界コメント1個。コード例・エスケープ文字列は数えない。分割後の最終HTMLはコメント0個が正常で、`data-article-lead` / `data-article-content` が各1個、導入→目次→本文の順を検査する。

## 検証と受入

新記事は `validate-cloudflare-article.ps1 -ValidationMode parent -RequireArticleDesign -ExpectedArticleDesignJson <4項目> -ExpectedArticleDesignStateJson <現行版記録> -RenderedHtmlPath ...` と既存の全目的別引数で検査する。補助の `audit-article-design.mjs` はstdin JSONの `project_root, article_path, rendered_html_path, require_design, expected_design, design_state` を受け、source/HTMLとハッシュを返す。単独のデザイン検査はCTA・事実・権利・内容検査の代替ではない。

新ID A〜E、旧10件・他の旧記事、invalid metadata、境界0/2、コード例、H2/画像欠落、未登録editionクラス、Eの注意書き、目次順変更、古い設計版、成約/集客、3教材CTAを回帰確認する。サムネイル640px・H2画像560px上限、全体表示、本文760px、スマホ16px/PC17px、320/375/390/768/1280px、キーボード・拡大・画像欠落時の意味・全記事の反復と縦の長さを実表示で確認する。検査未実施をPASSで埋めない。

今回の移行受入では3記事条件×2独立生成でサムネイルとH2の実生成・実画像を確認する。通常記事ごとに6回生成を要求する規則ではない。未合格項目があれば原因工程へ戻し、ローカル実装・画像QA・実表示・スキルGitHub保存・本番公開を分けて報告する。
