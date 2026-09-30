# プラットフォームアダプター

## 出力先の選択

- 見本、プレビュー、単体HTML: `standalone-html`
- 対応済み教育ブログの記事Markdown: `astro-markdown`
- その他のAstroやCMS: `unsupported_target`

出力先が不明で結果が大きく変わる場合だけ確認する。

## standalone-html

[assets/standalone-article-template.html](../assets/standalone-article-template.html) を基礎にする。

ファイルとして保存する場合は、`%TEMP%\\codex-article-work\\<run-id>--<preview名>\\`を未使用の実行フォルダとして作成し、その中へHTML、検証画像、レンダリング用`dist`、キャッシュ、ログを置く。`CLEANUP-INFO.txt`へ正本の有無、用途、ローカル配信停止後に実行フォルダ全体を削除またはゴミ箱へ移動できることを明記する。`C:\\AIフォルダ\\previews`や対象プロジェクトの`.tmp`、`artifacts`へプレビュー専用ファイルを保存しない。応答内だけで返す場合は、ファイルを作らない。

このファイルは部品カタログでもあり、全要素を記事へコピーする完成原稿ではない。必要な部品だけを残す。短い太字、比較軸保全、自然改行を適用し、枠の余白は同テンプレートのCSSで管理・検査する。

必須:

- `<!doctype html>`、`lang="ja"`、UTF-8、viewport metaを持つ。
- 外部CSS、外部JavaScript、CDN、外部フォントへ依存しない。
- CSSは`.edu-preview`配下へスコープする。
- プレビューであることを画面内に表示する。
- 本文、カード、CTAを320pxへ収める。
- 表ラッパーだけ`overflow-x: auto`を持つ。
- 必要な挙動はHTML標準の`details`等で実現し、不要なJavaScriptを追加しない。

### SVG

外部・ユーザー提供SVGを生のインラインSVGとして取り込まない。承認済みローカルSVGは原則`img`で参照する。

概念図として新規生成するインラインSVGだけ、`svg`、`g`、`path`、`rect`、`circle`、`line`、`polyline`、`polygon`、`text`、`title`、`desc`と座標・viewBox・fill・stroke・ARIA属性を許可する。

`script`、`foreignObject`、アニメーション、style、イベント属性、href、xlink:href、外部参照、CSS `url()`を禁止する。

## astro-markdown

初期対応先:

- プロジェクト: `C:\AIフォルダ\ブログ\site`
- 正本: `C:\AIフォルダ\ブログ\クラウドフレア\記事装飾ルールブック.md`

毎回、正本を全文読み、対象記事frontmatter、共通CSS、変換処理、実装済みコンポーネント、著者欄を確認する。

### 本文へ書かないもの

- H1
- `html`、`head`、`body`
- ヘッダー、ナビゲーション、サイドバー、フッター
- 公開日、自動目次、関連記事、既存著者欄
- CSS、style属性、script
- 未定義class

H1はfrontmatterの`title`からレイアウトが1回だけ生成する。

### 現行の原稿記法

実装状況を確認できた場合だけ、正本に従って次を使う。

```md
【ポイント】
要点。

【注意】
重要条件。

【チェックリスト】
- 確認項目

【結論】
結論。
```

内部リンクカード:

```md
【内部リンクカード】
URL: /公開済み正規URL/
紹介文: リンク先で分かること。
```

タイトルと画像はリンク先frontmatterの`title`と`coverImage`から解決し、推測しない。

### 対応外部品

standaloneの吹き出し、レビューカード、FAQ、CTA、プロフィール等に対応する共通実装が対象Astroにない場合、`edu-` classや独自HTMLを貼らず `unsupported_component` とする。

### デザイン移行

既存正本の配色、トークン、コンポーネントの範囲外となる色・装飾・グローバルUI変更は、サーモン色に限らず `design_migration_required` とする。

移行提案には次を一組で含める。

1. 部品の用途
2. Markdownまたは原稿記法
3. 生成HTML
4. 共通CSS
5. スマホ挙動
6. 既存記事の回帰確認
7. 正本更新

記事本文へページ専用CSSを貼る代替策は禁止する。

既存部品の意図に反する余白は不具合、配色・囲み・見出し意匠の変更はデザイン移行として区別する。いずれも共通CSS編集の許可は別途必要。原因と影響を示し、未承認の編集や未定義classで回避しない。スキルの判断規則を更新しただけではサイトの見た目を変更済みと報告しない。

AstroのMarkdown表とstandaloneのHTMLラッパーは実装が異なる。Markdown原稿の静的監査だけで表のスクロール対応を保証せず、生成後のDOM、全列へのアクセス、キーボード操作と実表示を確認する。

### 保存と公開

新規記事は承認された場合でも`draft: true`を既定とする。記事作成依頼を公開許可と解釈しない。
