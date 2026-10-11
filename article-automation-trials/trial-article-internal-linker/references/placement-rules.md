# 候補選定・配置・再実行規則

## 候補のハードゲート

候補は次の全条件を満たす場合だけ採用する。

1. 現在記事と同じ `site_id`
2. URLが絶対URLで、ホストが `allowed_internal_hosts` に含まれる
3. `publication_status: publish` かつ `verified_current: true`
4. 現在記事自身ではない
5. `cannibalization_status: clear`
6. 選定に使える `summary` と `reader_questions` がある
7. 承認済み `destination_scope` と読者の疑問へ直接関係する
8. `traffic`の主リンクでは`destination_business_purpose: conversion`で、記事管理情報・対応する制作ログ・ユーザー承認済み一覧のいずれかを示す`business_purpose_evidence_type`と`business_purpose_evidence_ref`がある

1つでも満たさない候補は挿入しない。必須意図の唯一の候補が不合格なら、該当理由コードで全体を `blocked` とする。

## 自己リンク判定

自己リンク判定では、利用できる識別子をすべて比較する。

- `article_key`
- `wp_post_id`
- `canonical_url`
- `planned_permalink`

いずれかが一致すれば自己リンクとする。現在記事に比較可能な識別子が1つもなければ `current_article_identity_missing`。

## URL比較の正規化

比較時だけ次の正規化を行う。本文に出す `href` は入力値を一字も変えない。

1. `canonical_url` があれば優先する
2. ホスト名を小文字にする
3. HTTPの80番、HTTPSの443番を既定ポートとして除く
4. 空パスと `/` を同一とする
5. 末尾スラッシュの有無だけの違いを同一とする
6. フラグメントを除いて比較する

スキーム、パスの大文字小文字、クエリは保持し、同一視しない。入力URLを修正してよさそうに見えても変更しない。

## 配置決定

`plan` で承認するのは次の4点である。

- `section_id`
- `reader_question_id`
- `purpose`
- `destination_scope`

`insert` は完成本文を見て、承認済みセクションの中から正確な段落を選ぶ。配置ロケーターは次で構成する。

```yaml
section_id: "h2-1"
anchor_context: "本文中で一意になる連続文字列"
operation: "before | after | replace_exact"
occurrence: 1
```

- `anchor_context` がセクション内で一意でなければ、より長い文脈で再選定する
- 一意にできなければ `placement_context_not_unique`
- 必須意図なら全体を `blocked`、任意意図なら理由付きで見送れる
- 別セクションへ移す、読者の疑問やリンク目的を変える、リンク先範囲を広げる場合は `plan` とユーザー承認をやり直す

## 誘導文とアンカーテキスト

- 誘導文は前後の論理を壊さない1〜2文を基本とする
- 読者がリンク先で分かることを具体的に示す
- 「こちら」「詳しくはこちら」だけのアンカーを避ける
- リンク先にない内容、効果、体験、結論を約束しない
- 同一段落へリンクを詰め込まない
- 本文の主張をリンク先へ丸投げしない
- 内部リンクであることを理由に、広告的な煽りや申込みCTAを加えない

## 成約用CTAの件数と公式確認場面

CTAは3件を標準値として検討するが、必須数・上限ではない。記事の検索意図、文章量、読者の判断段階、独立した公式確認理由から件数を決める。

- 短く狭い記事は1〜2件へ減らせる。長く複数の判断条件を扱う記事は4件以上へ増やせる
- 文章量、H2数、過去記事の件数だけでは増減しない
- 5件以上では、全配置の`reader_question`と`official_information_needed`が互いに独立していることを`count_reason`で説明する
- 口コミ・料金記事では、教材内容や良い口コミの後、料金・支払・端末条件の後、悪い口コミ・注意点・向き不向きの後が候補になる
- お試し・キャンペーン記事では、試せる内容、対象・期間、費用・返却・継続条件の説明後が候補になる
- 候補は固定見出しではない。本文を読んだ流れで、読者が公式情報を確認したくなる実際の場面だけを採用する
- 各配置は一意な`placement_id`、`reader_question`、`official_information_needed`、`section_id`、`section_heading`、`destination_purpose`、`lead_copy`を持つ
- 原則として別セクションへ置く。同一H2内に複数置く場合は、異なるH3または十分に離れた説明単位にあり、確認目的と前後文脈が明確に異なる場合だけ許可する
- 同じ`lead_copy`、実質同じ確認目的、連続CTAブロック、本文説明の途中、CTAで本文回答を代替する配置は不合格とする

`cta_strategy.planned_count`、`official_confirmation_moments`、`affiliate_link_plan.placements`、`affiliate_link_manifest.links`、実CTAの件数と`placement_id`は一致させる。不一致は`cta_strategy_mismatch`、意味の反復は`cta_placement_repetition`、直前文脈との不一致は`cta_context_mismatch`、過度な近接は`cta_spacing_conflict`とする。

## 進研ゼミ講座別アフィリエイトCTA

アフィリエイトCTAは`article_business_purpose: conversion`の主導線であり、内部リンクでも内部リンクカードでもない。ユーザーが提供・承認したプロバイダー別の講座リンクだけを、`affiliate_link_plan.status: eligible` かつ `presentation: cta_button` の場合に限り使える。`traffic`では使用しない。リンク先を検索、推測、差し替え、短縮、パラメータ削除してはならない。

| `target_course` | `href` | 計測用画像の `src` |
|---|---|---|
| `preschool` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892710747` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892710747` |
| `elementary` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693444` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693444` |
| `junior_high` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693441` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693441` |
| `high` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693443` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693443` |

- 幼児向け記事には`preschool`を使う。このリンクの遷移先である幼児向け公式サービスのブランド表記は「こどもちゃれんじ」とする。小学生向け記事には `elementary`、中学生向け記事には `junior_high`、高校生向け記事には `high` だけを使う。複数学年を扱う記事、対象講座が一意に決まらない記事、または進研ゼミへの次の行動を案内しない記事には使わない
- 記事内のタイトル、想定読者、結論、承認済み設計が同じ講座を指すことを確認する。1つでも一致しない場合はアフィリエイトリンクを追加しない
- 共通のCTA件数・公式確認場面の規則に従い、各`placement_id`の承認済みセクションで講座選定・費用・教材内容・適性を説明した後の自然な段落へ置く。記事冒頭、根拠説明の途中、本文の主張を代替する箇所、または記事の主題と無関係な箇所へは置かない
- このリンクは `max_new_links` と `max_links_per_destination` の対象外にし、`affiliate_link_manifest` で内部リンクと分けて管理する
- 既に同じ`placement_id`のCTAが存在する場合は追加しない。承認済み配置の別セクションで同一講座のURLを再利用することだけを理由に重複扱いしない。計画外の講座、未承認URL、またはマニフェストにないアフィリエイトリンクは`affiliate_link_mismatch`とする。既存のURLや表示を自動変更しない

### CTAのDOM契約

件数にかかわらず、各CTAの外側`div`に`data-placement-id`を付け、マニフェストの`placement_id`と一致させる。配置先H2の実際の見出し文字列を`section_heading`として記録する。

サイト側の `site_rendering_capabilities.affiliate_cta_component` が `supported: true` で、対象プロバイダーの `component_id`（進研ゼミは `shinken_zemi_cta_v1`、スマイルゼミは `smile_zemi_cta_v1`）が確認できた場合だけ、対応する構造を挿入する。共通コンポーネントを確認できない場合は、本文を変更せず `affiliate_cta_component_missing` とする。記事内へ `<style>` やインライン `style` を追加しない。

```html
<div class="shinken-zemi-cta" data-course="preschool" data-placement-id="CTA-01">
  <p class="shinken-zemi-cta__lead">こどもちゃれんじ幼児講座の対象年齢・教材内容・受講費を公式サイトで確認できます</p>
  <a class="shinken-zemi-cta__button" href="//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&amp;pid=892710747" rel="nofollow"><img src="//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&amp;pid=892710747" height="1" width="1" border="0" alt="">こどもちゃれんじ幼児講座の公式サイトを見る</a>
  <p class="shinken-zemi-cta__destination">リンク先：こどもちゃれんじ公式サイト</p>
</div>
```

- `data-course` は `preschool`、`elementary`、`junior_high`、`high` のいずれかとし、計画済み講座と一致させる
- `href`、計測画像 `src`、`rel`、`height`、`width`、`border` は講座表の値と固定属性を保持する。HTMLソースでは `&` を `&amp;` と直列化できるが、DOMで復元したURLは表の値と完全一致させる
- 計測画像の `alt` は空文字とし、読者向けの情報を重複させない
- リード文は公式サイトで確認できる内容を具体的に示す。ボタン文は講座名と「公式サイト」を含める。リンク先表示文は遷移先が公式サイトであることを明示する
- 効果保証、体験談、煽り、未確認の特典・締切・限定性、公式広告文のコピーを追加しない

## スマイルゼミ講座別アフィリエイトCTA

スマイルゼミのCTAは`article_business_purpose: conversion`の場合に、ユーザーが提供した次の4講座別A8リンクだけを使う。対象記事の学年・講座を一意に確認し、対応する講座リンクだけを使い、資料請求への誘導に限定する。`traffic`では使用しない。リンク先を検索、推測、差し替え、短縮、パラメータ削除してはならない。

| `target_course` | `href` | 計測用画像の `src` |
|---|---|---|
| `preschool` | `https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+6ZUCY` | `https://www16.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+6ZUCY` |
| `elementary` | `https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+60WN6` | `https://www16.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+60WN6` |
| `junior_high` | `https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+6BU5U` | `https://www15.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+6BU5U` |
| `high` | `https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+774PE` | `https://www16.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+774PE` |

- 幼児向け記事には`preschool`、小学生向け記事には`elementary`、中学生向け記事には`junior_high`、高校生向け記事には`high`だけを使う。複数学年向け、講座横断、または判定不能な記事には使わない
- `href`と計測画像`src`は表の値を一字も変更せず、`rel="nofollow"`、`border="0"`、`width="1"`、`height="1"`、`alt=""`を保持する
- 共通のCTA件数・公式確認場面の規則に従い、各`placement_id`の承認済みセクションで教材内容、料金、注意点、向き不向き、キャンペーン条件などを説明した後の自然な段落へ置く。記事冒頭、主張の代替、または広告的な反復配置にはしない
- スマイルゼミCTAの`lead_text`、`button_text`、`destination_text`は、資料請求への案内だけを示す。入会、効果、無料、特典、締切など、確認していない内容を追加しない

### スマイルゼミCTAのDOM契約

件数にかかわらず、各CTAの外側`div`に`data-placement-id`を付け、マニフェストの`placement_id`と一致させる。配置先H2の実際の見出し文字列を`section_heading`として記録する。

サイト側の`smile_zemi_cta_v1`共通CSSが実装済みと現在実行で確認できた場合だけ、次の構造を使う。記事内へ`<style>`やインライン`style`を追加しない。

```html
<div class="smile-zemi-cta" data-course="junior_high" data-placement-id="CTA-01">
  <p class="smile-zemi-cta__lead">詳しくは、スマイルゼミ公式サイトから資料請求へ進めます</p>
  <a class="smile-zemi-cta__button" href="https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+6BU5U" rel="nofollow"><img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+6BU5U" alt="">スマイルゼミ中学生コースの資料を請求する</a>
  <p class="smile-zemi-cta__destination">リンク先：スマイルゼミ中学生コース公式サイト</p>
</div>
```

- `data-course`は`preschool`、`elementary`、`junior_high`、`high`のいずれかとし、計画済み講座と一致させる
- `href`、計測画像`src`、`rel`、`border`、`width`、`height`、`alt`は講座表と固定属性を保持する
- ボタン文は対象講座名と「資料を請求する」を含める。リンク先表示文は公式サイトへの遷移を明示する
- `smile-zemi-cta__button`は緑色の共通CSSで表示し、5幅の実表示でCTA枠外へはみ出さないことを監査する

### CTAの表示契約

`shinken_zemi_cta_v1` の共通CSSは次を満たす。サイト側のCSS実装は本スキルの責任範囲外とし、未実装時に自動作成・変更しない。

- CTA枠は本文幅以内の `width: 100%`、最大幅720px、中央配置、背景 `#fffaf5`、境界線 `#f4d6b5`、角丸12pxを基本とする
- ボタンは幅100%以内・最大420px、最小高さ56px、白文字、`#f6ad49` から `#f08300` のオレンジ系グラデーション、角丸50pxを基本とする
- 計測画像はDOMに保持しつつ、表示寸法を1px×1pxに固定してレイアウトを崩さない
- キーボード操作で識別できるフォーカス表示を持ち、`prefers-reduced-motion: reduce` では移動アニメーションを無効化する
- 320・375・390・768・1280pxの各幅でページとCTAに意図しない横スクロールがなく、ボタンがCTA枠外へはみ出さない

## 内部リンクの役割と表示形式

公開確認済みのリンク先記事を、次の2種類に分ける。成約用かどうかはタイトルやトピックではなく、記事管理情報・対応する制作ログ・ユーザー承認済み一覧のいずれかで確認する。

- `conversion_direct`: 口コミ、料金紹介、比較、その他の成約へ直接つながる記事。画像付き内部リンクカードを使う
- `related_support`: 上記以外で本文と直接関係する関連記事。本文中の内容に合う語句へテキストリンクを設定する

表示形式はリンク先の役割で決め、内部リンクの総数や配置件数で入れ替えない。`conversion_direct`を上限回避のため`text_link`へ変えず、`related_support`を件数合わせのためカード化しない。画像付き内部リンクカードは記事全体で最大2件とし、候補が3件以上ある場合は本文との関連性と成約への直結性が高い2件だけを採用する。

`traffic`では`conversion_direct`のうち1件を`required: true`かつ`primary_destination: true`にする。これは記事の検索回答を省略する代替ではなく、本文で疑問へ十分回答した後の次の行動として配置する。適格な主リンクがない場合は執筆前に`primary_conversion_destination_missing`で停止する。`conversion`ではアフィリエイトCTAが主導線で、内部リンクは補助導線とする。

## カード形式の表示契約

`conversion_direct`にだけ、サイトが対応する画像付き内部リンクカードを使う。

Astro記事では、現在実行で対応済みと確認した次の既存記法を使う。URLは確認済み候補の値をそのまま使い、紹介文はリンク先で分かる内容だけを書く。

```md
【内部リンクカード】
URL: /公開済み正規URL/
紹介文: リンク先で分かること。
```

カード形式を使う場合は、次の表示を固定仕様とする。

- 画像を左、ラベル・記事タイトル・紹介文を右に置く
- 画像枠は `16 / 9` とし、画像は枠内を `object-fit: cover` で表示する
- 画面幅680px以下では、画像列の幅を `clamp(84px, 25.6vw, 100px)` とする
  - 320px幅では84px
  - 375px幅では96px
  - 390px幅では約100px
- 画面幅681px以上では、画像列の幅を160pxとする
- 画像をカード幅いっぱいに広げたり、スマホで画像と文章を縦積みにしたりしない
- 紹介文が長くてもカード外への横方向のはみ出しを発生させない

サイト側にカード用コンポーネントや共通CSSがある場合は、それを再利用する。記事ごとのインラインCSSで同じ仕様を複製しない。サイト側がこの表示契約に対応していない場合は、本文へ不完全なカード記法を挿入せず、親スキルへ実装不足を返す。

## 上限制御

1. 先に必須意図を割り当てる
2. 必須意図だけで `max_new_links` を超える場合は `policy_conflict`
3. `conversion_direct`の候補を関連度順に最大2件まで割り当てる
4. 残枠へ任意意図を関連度順に割り当てる
5. 同一リンク先への件数が `max_links_per_destination` を超えないようにする
6. 複数の必須意図が同じリンク先を要求し、上限上どちらかを落とす必要がある場合は `policy_conflict`
7. `image_card`が2件を超える場合は`image_card_limit_reached`とし、`text_link`へ変更しない

## 既存リンクの保護と冪等性

挿入前に本文内の既存リンクを抽出し、`expected_link_manifest.existing_links` へ記録する。リンクごとに、少なくとも出現位置、アンカーテキスト、元の `href` を保持する。

新規リンクの安定キーは次とする。

```text
article_key + intent_id + destination_id
```

- 同じ安定キーが存在する場合は追加しない
- URL比較上同じリンク先がすでに存在し、承認意図を満たす場合は追加しない
- 手動で置かれた既存リンクのアンカーやURLを自動修正しない
- 同じ入力で再実行しても、リンク数や誘導文が増えないこと
- `audit` で既存リンクの変化を検出したら `existing_link_modified`

## トランザクション規則

`insert` は全必須意図を検証してから変更本文を返す。

- 必須意図が1件でも未解決なら、`body_with_internal_links` は入力本文と完全に同じ内容を返す
- 部分挿入した本文、仮URL、プレースホルダーを返さない
- 親スキルは挿入前本文を保持し、`audit` 合格時だけ内部リンク済み本文を採用する

## 監査規則

`audit` はHTMLからリンクを抽出し、期待リンク一覧と比較する。

- 新規リンクがすべて存在し、アンカーと `href` が一致する
- `related_support`が本文中の語句へ設定された`text_link`として存在する
- `conversion_direct`が画像付きの`image_card`として存在し、画像・正式タイトル・紹介文がある
- `image_card`が記事全体で2件を超えず、期待マニフェストの表示形式と一致する
- 既存リンクが消失・変更していない
- 自己リンク、許可ホスト外URL、未公開候補がない
- 同じ安定キーや同じ意図の重複がない
- `{...URL...}`、`TODO`、`example.com` 等の仮値がない
- `affiliate_link_manifest` にないアフィリエイト計測URLや `rel="sponsored"` のリンクを本スキルが追加していない
- `traffic`ではCTA固定クラス、アフィリエイトリンク、計測画像URLが0件である
- `traffic`では`required: true`かつ`primary_destination: true`の成約記事画像カードが1件存在し、成約用役割の確認証拠と一致する
- `affiliate_link_manifest` にあるCTAは、プロバイダー、対象講座、`href`、計測用画像の `src`、`rel="nofollow"`、リード文、ボタン文、リンク先表示文、配置セクションが一致する
- プロバイダー別CTAでは、固定クラス、`data-course`、CTA数、リード文、ボタン文、リンク先表示文、コンポーネントIDが一致する
- プロバイダー別CTAでは、320・375・390・768・1280pxの実表示記録が揃い、ページとCTAの横はみ出し、ボタンの最小高さ・最大幅、計測画像の1px寸法、CTA起因のコンソールエラーがない。記録が欠ける場合は `affiliate_cta_render_unverified`

## 最低限の受入テスト

実運用前とルール変更後は、少なくとも次を確認する。

1. 公開済み同一サイト記事を自然な段落へ1件挿入できる
2. 通常の関連記事がテキストリンク、口コミ・料金・比較・成約直結記事が画像付きカードになる
3. 画像付きカードが2件を超えず、3件目をテキストリンクへ変更しない
4. 同じ入力で2回実行してもリンクが増えない
5. 自己リンクを拒否する
6. 未公開・未確認・許可ホスト外の候補を拒否する
7. 必須意図の解決失敗時に元本文を変更しない
8. 曖昧な配置文脈で必須リンクを勝手に置かない
9. HTML化でURLが変わった場合に監査が失敗する
10. 既存リンクが変わった場合に監査が失敗する
11. 任意リンク候補が0件のとき `pass_zero_links` を返せる
12. 候補一覧自体が欠ける場合は `missing_link_inventory` で停止する
13. カード形式では、PCと320px・375px・390px幅の実表示で、画像が左、文章が右に保たれる
14. カード画像の表示幅が、320pxでは84px、375pxでは96px、390pxでは約100px、681px以上では160pxになる
15. カード形式でページ全体の横スクロールやカード外へのはみ出しが発生しない
16. 小学・中学・高校講座の各 `target_course` で、対応するユーザー提供の `href` と計測用画像の `src` が選ばれる
17. 成約用で対象講座が一意に確定しない記事では、アフィリエイトリンクを追加せず`conversion_affiliate_unresolved`で全体を停止する。内部リンクだけで完成扱いにしない
18. アフィリエイトCTAがある場合、HTML化後に `href`、計測用画像の `src`、`rel="nofollow"`、リード文、ボタン文、リンク先表示文、配置セクションが `affiliate_link_manifest` と一致する
19. 対応済みサイトでは、対象プロバイダーごとの講座別CTAが固定DOM契約で、承認済み`placement_id`とマニフェストの件数どおりに挿入される
20. CTA対応が確認できないサイトでは、本文を変更せず `affiliate_cta_component_missing` で停止する
21. 同じ配置に既存CTAがある場合、自動置換や重複追加をしない。別セクションの明示配置まで無条件に削らない
22. CTAのURLをHTMLエスケープしても、DOMで復元した `href` と `src` がユーザー提供値に一致する
23. 320・375・390・768・1280pxの実表示記録が欠ける場合、`affiliate_cta_render_unverified` で監査を失敗させる
24. `traffic`で主成約記事を確認できない場合、本文を変更せず`primary_conversion_destination_missing`で停止する
25. `traffic`でCTA・計測画像・ASP URLが混入した場合、`traffic_affiliate_contamination`で監査を失敗させる
26. `traffic`で主成約記事カードが欠ける場合、`primary_conversion_card_missing`で監査を失敗させる
27. `conversion`では承認済みCTAがない状態を内部リンクだけで合格にしない
28. 標準的な口コミ・料金記事では、異なる公式確認目的を持つCTA3件を計画し、計画・マニフェスト・実HTMLの件数と`placement_id`を一致させる
29. 短い単一テーマ記事では1〜2件へ減らした理由があり、3件へ水増ししない
30. 長い記事でも独立した公式確認理由が3つならCTAを4件へ増やさない
31. お試し・キャンペーン記事では、試せる内容、対象・期間、費用・返却・継続条件など実際の判断場面から配置を選ぶ
32. 同じURLを複数回使う場合でも、各`lead_text`と確認目的が異なり、CTAが連続または近接していない
33. `cta_strategy.planned_count`、公式確認場面、配置計画、マニフェスト、実CTAのいずれかが不一致なら`cta_strategy_mismatch`で失敗する
34. 各CTAの直前文脈が`reader_question`と`official_information_needed`を説明していない場合は`cta_context_mismatch`で失敗する
