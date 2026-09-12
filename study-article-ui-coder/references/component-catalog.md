# コンポーネントカタログ

この文書はstandaloneプレビューの固定契約を定める。Astroでは `platform-adapters.md` と対象プロジェクトの正本を優先し、ここにある`edu-` classを直接貼らない。

## 共通規則

- すべてのclassは`edu-`接頭辞のBEM形式とする。
- 記事ごとにclass名、色、DOM階層を変更しない。
- 見出しに含めるべき情報を、見た目だけの太字ラベルへ置き換えない。
- 枠のタイトルがアウトラインに不要なら`p`を使い、不要なH3を増やさない。
- 部品内へ別の主要CTAやリンクカードを入れ子にしない。
- 省略状態をCSSのline-clampで隠さず、スマホでも必要情報を読めるようにする。

## 見出し

```html
<section class="edu-section" aria-labelledby="section-study-method">
  <p class="edu-section__kicker">学習の進め方</p>
  <h2 class="edu-heading-2" id="section-study-method">毎日続けられる方法を選ぶ</h2>
  <p>導入文。</p>
</section>
```

`kicker`は任意で、短いカテゴリー語だけに使う。H2本文と同じ内容を繰り返さない。

H3:

```html
<h3 class="edu-heading-3" id="study-time">学習時間を先に決める</h3>
```

## 強調

```html
<strong class="edu-emphasis">毎日続けられる時間</strong>
<strong class="edu-emphasis edu-emphasis--caution">申込み期限</strong>
```

段落全体を入れない。読み上げ順を変えない。

## 結論枠

使用条件: 本文に結論と理由がある。

```html
<aside class="edu-box edu-box--summary" aria-label="結論">
  <p class="edu-box__label">結論</p>
  <p class="edu-box__lead">短い結論。</p>
  <p>結論を支える理由。</p>
</aside>
```

部品の存在は自動挿入の指示ではない。特に対象ブログではリードから最初の本文見出しへ自然につなぎ、リード直下に同じ説明の結論枠を追加しない。結論そのものは本文に残す。明示指定・維持対象は尊重し、主要節で必要な場合の使用やclass自体は禁止しない。

## 数字を含む枠と余白

数字があるだけで枠にせず、比較・条件確認に役立つ場合に既存の情報枠等を使う。枠タイトルは見出し階層に不要なら`p`、並列項目は`ul`、順序は`ol`。項目名、数値、単位、期間、例外を近くに配置し、数字だけを孤立させない。

HTML構造は「aside → タイトルp → 項目ulまたは説明p → 条件p」を基本候補にする。Astroでは実装済みの`article-callout`構造へ写像し、`edu-`classは使わない。固定の見本金額を現在の事実として流用しない。

寸法の正本は共通CSS・プロジェクト正本であり、本スキルは検査方法を管理する。最初の要素の不要な上margin、最後の要素の不要な下marginをなくす。タイトル・本文・リストの実距離と適用CSSを確認し、一般段落用の余白が枠内へ漏れていないか検査する。空段落・連続改行による調整は禁止。詳細な表示判定は`quality-gates.md`を参照する。

## 情報枠

使用条件: 用語、前提、仕組みの補足が本文理解に必要である。

```html
<aside class="edu-box edu-box--info" aria-label="ポイント">
  <p class="edu-box__label">ポイント</p>
  <p>補足内容。</p>
</aside>
```

広告的な訴求や結論の繰り返しに使わない。

## 注意枠

使用条件: 料金、期限、対象外、例外、失敗条件等の重要制約がある。

```html
<aside class="edu-box edu-box--warning" aria-label="注意">
  <p class="edu-box__label">注意</p>
  <p>確認すべき条件。</p>
</aside>
```

小さな注意をすべて枠にせず、同種の重要条件は一か所へ統合する。

## チェックリスト

使用条件: 各項目を読者が実行・確認できる。

```html
<aside class="edu-box edu-box--checklist" aria-label="チェックリスト">
  <p class="edu-box__label">チェックリスト</p>
  <ul class="edu-checklist">
    <li class="edu-checklist__item">確認項目</li>
  </ul>
</aside>
```

単なる特徴一覧は通常のリストにする。

## 手順

```html
<ol class="edu-steps">
  <li class="edu-steps__item">
    <p class="edu-steps__title">学習時間を決める</p>
    <p>実行内容。</p>
  </li>
</ol>
```

順序依存がない場合は`ul`を使う。

## 吹き出し

使用条件: 代表的な疑問または説明の橋渡しである。

```html
<aside class="edu-balloon" aria-label="読者の疑問">
  <span class="edu-balloon__icon" aria-hidden="true">?</span>
  <p class="edu-balloon__text">部活と両立できるか心配です。</p>
</aside>
```

引用ではないため`blockquote`を使わない。架空の体験、専門家の証言、利用者の声に見せない。

## 引用・口コミ

使用条件: `approved_citations`と照合できる。

```html
<figure class="edu-quote">
  <blockquote class="edu-quote__body" cite="https://example.com/source">
    <p>承認された範囲の引用。</p>
  </blockquote>
  <figcaption class="edu-quote__source">
    出典：<a href="https://example.com/source">確認済みの出典名</a>
  </figcaption>
</figure>
```

要約は`blockquote`へ入れず、通常文と出典リンクで示す。長い転載を行わない。

## レビューカード

必須: 名称、要約、特徴、向く人、重要制約。CTAは実在する場合だけ。

```html
<section class="edu-review-card" aria-labelledby="review-service-a">
  <header class="edu-review-card__header">
    <p class="edu-review-card__eyebrow">教材レビュー</p>
    <h3 class="edu-review-card__title" id="review-service-a">サービス名</h3>
  </header>
  <p class="edu-review-card__summary">確認済み情報に基づく要約。</p>
  <div class="edu-review-card__grid">
    <section class="edu-review-card__section" aria-label="向いている人">
      <p class="edu-review-card__label">向いている人</p>
      <ul><li>条件</li></ul>
    </section>
    <section class="edu-review-card__section" aria-label="確認したい点">
      <p class="edu-review-card__label">確認したい点</p>
      <ul><li>制約</li></ul>
    </section>
  </div>
</section>
```

根拠のない星、点数、利用者数を表示しない。画像なしでも壊れない構造にする。

## 比較表

使用条件: 共通項目で比較すると理解を助ける場合。既存表の比較軸・列を保持することを既定とし、幅を狭めるだけの目的で複数の比較軸を1セルへまとめない。

```html
<div class="edu-table-scroll" tabindex="0" aria-label="教材Aと教材Bの比較表。横にスクロールできます">
  <table class="edu-table">
    <caption class="edu-table__caption">教材Aと教材Bの比較</caption>
    <thead>
      <tr><th scope="col">項目</th><th scope="col">教材A</th><th scope="col">教材B</th></tr>
    </thead>
    <tbody>
      <tr><th scope="row">学習形式</th><td>内容</td><td>内容</td></tr>
    </tbody>
  </table>
</div>
```

表の前後に比較結果を文章でも説明する。セルへ長文を詰め込まない。

固有名詞や短い見出しへの不要な`<br>`を避け、自然な折り返しと表内部の横スクロールを使い分ける。列構成の変更が必要なら必要性と情報対応を示す。金額、単位、期間、支払方法、「〜」などの条件を落とさない。通常比較表と料金改定専用部品を混同せず、すべてを3列に固定しない。

## 料金改定表

使用条件: 料金変更について、適用時期と複数の学年・コース別差額を読者が確認する必要がある。

生成前に、変更前と変更後で開始月、支払い方法、税込・税別が同じか確認する。比較条件をそろえられない数値を同じ差額列へ入れない。

必須情報:

- 適用時期
- 統一した比較条件
- 学年または対象区分
- 変更前と変更後の1か月あたりの金額
- 月額差と年間差
- 公式一次情報の出典と確認日

Astro出力では、対象プロジェクトの正本と共通CSSに実装済みである場合だけ、`article-price-summary`と`article-price-table`を使用する。概要は最大額だけで完結させず、同じ節または後続節に全対象の学年別表を置く。

```html
<section class="article-price-summary" aria-label="料金改定の概要">
  <header class="article-price-summary__header">
    <p class="article-price-summary__kicker">2026 → 2027</p>
    <p class="article-price-summary__title"><span>料金改定</span> <span>早見表</span></p>
  </header>
  <dl class="article-price-summary__meta">
    <div><dt>いつから</dt><dd>適用時期</dd></div>
    <div><dt>比較条件</dt><dd>開始月・支払い方法</dd></div>
    <div><dt>表示金額</dt><dd>税込または税別</dd></div>
  </dl>
  <p class="article-price-summary__source">出典：公式一次情報の名称（確認日）</p>
</section>

<figure class="article-price-table">
  <figcaption class="article-price-table__caption">
    <span class="article-price-table__kicker">学年別</span>
    <strong>講座・コース名</strong>
    <span>適用時期</span>
  </figcaption>
  <div class="article-price-table__scroll scroll-table" tabindex="0" aria-label="変更前と変更後の料金比較表">
    <table>
      <thead>
        <tr><th scope="col">学年</th><th scope="col">変更前</th><th scope="col">変更後</th><th scope="col">月の増加</th><th scope="col">年の増加</th></tr>
      </thead>
      <tbody>
        <tr><th scope="row">対象学年</th><td data-label="変更前">確認済み金額</td><td data-label="変更後">確認済み金額</td><td class="article-price-table__increase" data-label="月の増加">確認済み差額</td><td class="article-price-table__increase" data-label="年の増加">確認済み差額</td></tr>
      </tbody>
    </table>
  </div>
  <p class="article-price-table__note">比較条件と計算上の注意。</p>
</figure>
```

- 値上げは色だけで示さず、`+`、列見出し、金額を併用する。
- 最大行を強調する場合は、行見出しへ文字で「最大」と付ける。
- 新設コースなど変更前価格がない場合は、差額を推測せず「新設」と表示する。
- 年間差が月額差の12倍にならない場合は、期間と計算根拠を注記する。
- 680px以下では`data-label`を表示して学年単位のブロックへ変換し、420px以下では金額項目を1列にする。
- Astro本文へ`style`や`script`を入れない。正本・共通CSSが未実装なら`design_migration_required`とする。

## 内部リンクカード

必須: 公開済みURL、正式タイトル、紹介文、承認済み画像。

```html
<aside class="edu-link-card" aria-label="関連記事">
  <a class="edu-link-card__link" href="/published-path/">
    <span class="edu-link-card__media">
      <img class="edu-link-card__image" src="/approved.webp" alt="" width="320" height="180" loading="lazy" decoding="async">
    </span>
    <span class="edu-link-card__body">
      <span class="edu-link-card__label">あわせて読みたい</span>
      <span class="edu-link-card__title">正式タイトル</span>
      <span class="edu-link-card__description">この記事で分かること。</span>
    </span>
  </a>
</aside>
```

カード全体を一つのリンクにし、内部へ別リンクを置かない。同じリンクを繰り返さず、原則としてH2ごとに1枚、記事全体で3枚程度までとする。

## FAQ

使用条件: 本文後も残る実質的な疑問が2件以上ある。

```html
<section class="edu-faq" aria-labelledby="faq-title">
  <h2 class="edu-heading-2" id="faq-title">よくある質問</h2>
  <details class="edu-faq__item">
    <summary class="edu-faq__question">質問文</summary>
    <div class="edu-faq__answer"><p>結論から始める回答。</p></div>
  </details>
</section>
```

本文の単純な繰り返しを作らない。

## CTA

必須: 実在するURLと遷移目的。仮URLでは部品自体を出さない。

```html
<aside class="edu-cta" aria-labelledby="cta-title">
  <p class="edu-cta__eyebrow">次にすること</p>
  <h2 class="edu-cta__title" id="cta-title">条件を公式ページで確認する</h2>
  <p class="edu-cta__text">遷移先で確認できる内容。</p>
  <a class="edu-button edu-button--primary" href="https://example.com/official">公式情報を確認する</a>
</aside>
```

主要CTAは記事末尾を基本とし、同じCTAを各節へ反復しない。外部、広告、内部リンクを表示上区別する。

## 著者プロフィール

使用条件: `approved_author_profile`があるstandalone出力。Astroでは既存著者欄と重複させない。

```html
<aside class="edu-author-profile" aria-labelledby="author-name">
  <img class="edu-author-profile__image" src="/approved-author.webp" alt="著者名" width="96" height="96" loading="lazy" decoding="async">
  <div class="edu-author-profile__body">
    <p class="edu-author-profile__role">役割</p>
    <h2 class="edu-author-profile__name" id="author-name">公開用著者名</h2>
    <p class="edu-author-profile__intro">承認済み紹介文。</p>
  </div>
</aside>
```

画像がない場合は画像要素を省き、本文を全幅にする。権威付けのために経歴を追加しない。
