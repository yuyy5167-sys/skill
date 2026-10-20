# 勉強ブログのA〜Eアダプター

## 適用と実装確認

適用先は正規化後に`/Users/yudaikato/Documents/AIフォルダ/ブログ/公開サイト・教材/勉強ブログ`と一致するサイト、profileは`cream-manga-mustard-v1`だけである。今後の新規記事は`parent_directed`とし、親が決めた`ui_design.article_design`と全ブロック割当を使用する。別ブログ・既存の単独整形の`autonomous`を変更しない。

毎回、サイトの`src/content.config.ts`、`src/lib/articleDesignMetadata.mjs`、`src/config/articleDesigns.ts`、動的記事route、`ArticleReadingLayout.astro`、`src/styles/article-editions.css`を現物で確認する。ファイル名の存在だけではcapability確認にしない。schema、解決順、実装部品、出力DOM、適用CSSが対応していることを確認し、`site_rendering_capabilities.article_design`を親へ返す。

必要な設定受け口がなければ`design_migration_required`、指定部品が未実装なら`unsupported_component`とし、旧デザインへ黙って置き換えない。共通CSSの改修が許可済みなら承認範囲の移行工程へ戻し、通常の記事UI化では記事固有のCSS・JS・共通設定編集を代替にしない。

## 設定と互換性

frontmatterの`articleDesign`は`profile`、`design`（A〜E）、trim後の非空`label`、任意booleanの`showMaterialFinder`だけを受け付ける。未知キー・不正値は検出し、無視しない。profileの版と親の整数`ui_design.design_version`は別の情報である。

解決順はfrontmatter→既存10記事の辞書→null。新規は`origin: frontmatter`、既存辞書は`origin: legacy-map`である。frontmatterを明示した場合は辞書の目次短縮文や末尾案内を継承しない。新規の末尾教材診断は既定false、既存10記事は従来の表示を維持する。共通floating診断はこの設定で変更しない。

新規記事は実際のH2から目次を生成し、別の目次配列を執筆しない。「目次」とからし色の下線は共通レイアウトの責務である。

## 見た目と画像

背景`#FCF9F2`、文字`#242422`、からし色`#EDCE68`。本文はスマホ16px/PC17px、line-height 1.9、中央最大約760px。H1/H2/H3・余白・枠・ボタンは共通CSSから取得し、旧standaloneのサーモン配色や見出し寸法を混ぜない。

サムネイルは導入へ1回、最大640px。各H2直下画像は最大560px、16:9、`object-fit: contain`。画像全体を見せ、記事一覧・OGの`coverImage`と同じサムネイルを使用する。画像そのものの生成・`coverImage`の書換えは親の統合工程で行う。

新profileの内部リンクカードは画像全体を表示し、既存の最大2枚・PC画像幅160px・横並び契約を維持する。成約用/集客用の導線条件はデザインから推定しない。進研ゼミ・Z会の`shinken-zemi-cta`、スマイルゼミの`smile-zemi-cta`は固定DOM、URL、rel、data属性、1px計測画像を保持し、共通CSSだけでからし地・濃色文字にする。ボタン下の「リンク先：〜」は追加しない。

## 原稿・DOMの構造

```md
<figure class="edition-thumbnail">

![承認済みの具体的なalt](./images/article-thumbnail.webp)

</figure>

導入文。

<!--article-lead-end-->

## 教材の文脈が分かるH2

![この節の要点を表すalt](./images/h2-01.webp)

<p class="edition-answer">E型で短い答えを明示する場合。</p>

条件と理由を説明する通常本文。
```

上記のパスは記法の例であり、実記事へ未確認のまま貼らない。サムネイル・H2画像の追加後も最終全ブロック割当を照合する。

境界は入力HTMLのトップレベル実コメントとして1個必要。コード例・エスケープ表示・属性中の文字列では満たさず、要素内部へ置かない。`splitArticleLead`が分割時に消費するため、完成DOMにコメントを残すことは要求しない。完成DOMは`[data-article-lead]`→`nav.edition-outline`→`[data-article-content]`がそれぞれ1個で正しい順序か確認する。

H2/H3はMarkdown標準見出しを使用する。H2画像はH2の直後のMarkdown画像とし、見出しを部品のdivで包まない。見た目を太字だけのpへ置き換えて見出しを欠落させない。

E型の新規記事は`edition-answer`を指定した短い答えだけを強調する。H2画像の次の通常段落は自動強調しない。旧10記事の位置依存強調は`legacy-map`互換専用である。画像の中だけに重要条件・数値を閉じ込めない。

## 実在する本文部品

具体classの機械可読正本は[登録簿](cream-manga-component-registry.json)。広い`edition-*`接頭辞の許可ではない。登録簿のlayout-owned classはレイアウト専用で、本文へ記述しない。

| 目的 | 本文記法・生成DOM | CSSとスマホ挙動 |
|---|---|---|
| 通常本文・見出し・画像 | `plain`、標準Markdown。H2画像は直下のp>img | 共通本文寸法、画像16:9を全体表示 |
| 導入サムネイル | `figure.edition-thumbnail` 内に空行を挟んだMarkdown画像 | 最大640px、狭い幅では100% |
| 短い明示回答 | `p.edition-answer` | 導入は太字、E本文では左からし線。長い条件は次の通常段落へ |
| 漫画的な問いかけ | `div.edition-comic` 内に`p.edition-comic__question`と`p.edition-comic__answer`。承認済み画像は任意 | 問いは吹き出し、回答は左線。実話・体験談を捏造しない |
| 学習ノート | `div.edition-note` 内に`p.edition-note__label`、通常p | 罫線と枠、1列。無意味な余白用空pを作らない |
| 手順 | `ol.edition-steps`、各`li`に手順。任意のstrongとspan | 番号付き縦並び、左線。番号を見出しへ二重に書かない |
| 注釈・式・英文 | `p.edition-annotation`、`p.edition-equation`、`p.edition-sentence` | 左線またはセリフ体。狭い幅でも自然改行 |
| 2つの選択先 | `div.edition-choices` > a > `span.edition-choices__label` + strong + span | 2列要素をスマホでは1列へ。実在する遷移先のみ |
| 質問と答えの導入 | `div.edition-qa` > `p.edition-qa__question` + `p.edition-qa__answer` | Q/Aラベル付き縦並び。自動目次やH2の代用にしない |
| 手順への案内 | `div.edition-routes` > a（任意span） | 縦のリンク列。リンク先アンカーを確認 |
| 家族の関係図 | `figure.edition-family` > figcaption + `p.edition-family__parent` + `div.edition-family__children` > p | 子の項目は均等2列。複雑な家系図へ拡張しない |
| 承認済み本文図 | `figure.edition-visual` > img + 任意figcaption | width100%、比率保持。H2画像の標準Markdownを不要に包まない |
| 短い補足・出典 | `p.edition-caption`、`p.edition-source`または`div.edition-source` | 補足12px。主要条件・本文を小さくする用途は禁止 |
| 既存アンカー保持 | `span.edition-anchor` + id | 既存参照維持用。新規目次は実H2の自動idを使用 |

実装済みの`article-callout`・`scroll-table`・内部リンクカード・正規CTAも適用可能だが、各契約・許可済み名・配置・事業目的を守る。新部品を必要とするときは登録簿へ名前だけを足して完成扱いにせず、共通実装と受入検査を先に行う。

## 機械監査と引き渡し

```sh
python -B scripts/audit_article_markup.py --target astro-markdown --input <原稿> --article-profile cream-manga-mustard-v1 --readability-warnings
```

CTA等の既存専用classは実装確認の上でそれぞれの具体接頭辞を`--allowed-class`へ渡す。`--allowed-class edition`で未登録名を通すことはできない。監査はDOMの意味、事実、画像の対応、全ブロック割当、全幅の見やすさを自動保証しない。

320/375/390/768/1280pxで、画像、目次、該当する部品、比較表の全列、CTA、末尾案内、固定要素まで確認する。文字拡大・キーボード・画像失敗・読み込み時の位置ずれも確認する。親が全候補の設計適合と実表示を確認するまで、機械監査だけで完成としない。
