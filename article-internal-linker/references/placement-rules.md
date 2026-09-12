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

## 進研ゼミ講座別アフィリエイトCTA

アフィリエイトCTAは内部リンクでも内部リンクカードでもない。ユーザーが提供・承認した次の進研ゼミ3講座だけを、`affiliate_link_plan.status: eligible` かつ `presentation: cta_button` の場合に限り使える。リンク先を検索、推測、差し替え、短縮、パラメータ削除してはならない。

| `target_course` | `href` | 計測用画像の `src` |
|---|---|---|
| `elementary` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693444` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693444` |
| `junior_high` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693441` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693441` |
| `high` | `//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693443` | `//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693443` |

- 小学生向け記事には `elementary`、中学生向け記事には `junior_high`、高校生向け記事には `high` だけを使う。複数学年を扱う記事、対象講座が一意に決まらない記事、または進研ゼミへの次の行動を案内しない記事には使わない
- 記事内のタイトル、想定読者、結論、承認済み設計が同じ講座を指すことを確認する。1つでも一致しない場合はアフィリエイトリンクを追加しない
- 同一記事への追加は最大1件とし、講座選定・費用・教材内容・適性を説明した後、読者が公式情報を確認しやすい自然な段落に置く。記事冒頭、根拠説明の途中、本文の主張を代替する箇所、または記事の主題と無関係な箇所へは置かない
- このリンクは `max_new_links` と `max_links_per_destination` の対象外にし、`affiliate_link_manifest` で内部リンクと分けて管理する
- 既に同一講座のアフィリエイトリンクまたはCTAが存在する場合は、URLや表示を自動変更せず追加もしない。別講座、未承認のValueCommerceリンク、またはマニフェストにないアフィリエイトリンクを検出した場合は `affiliate_link_mismatch` とする

### CTAのDOM契約

サイト側の `site_rendering_capabilities.affiliate_cta_component` が `supported: true`、`component_id: shinken_zemi_cta_v1` の場合だけ、次の構造を挿入する。共通コンポーネントを確認できない場合は、本文を変更せず `affiliate_cta_component_missing` とする。記事内へ `<style>` やインライン `style` を追加しない。

```html
<div class="shinken-zemi-cta" data-course="elementary">
  <p class="shinken-zemi-cta__lead">進研ゼミ小学講座の料金・教材内容は公式サイトで確認できます</p>
  <a class="shinken-zemi-cta__button" href="//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&amp;pid=892693444" rel="nofollow"><img src="//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&amp;pid=892693444" height="1" width="1" border="0" alt="">進研ゼミ小学講座の公式サイトを見る</a>
  <p class="shinken-zemi-cta__destination">リンク先：進研ゼミ小学講座公式サイト</p>
</div>
```

- `data-course` は `elementary`、`junior_high`、`high` のいずれかとし、計画済み講座と一致させる
- `href`、計測画像 `src`、`rel`、`height`、`width`、`border` は講座表の値と固定属性を保持する。HTMLソースでは `&` を `&amp;` と直列化できるが、DOMで復元したURLは表の値と完全一致させる
- 計測画像の `alt` は空文字とし、読者向けの情報を重複させない
- リード文は公式サイトで確認できる内容を具体的に示す。ボタン文は講座名と「公式サイト」を含める。リンク先表示文は遷移先が公式サイトであることを明示する
- 効果保証、体験談、煽り、未確認の特典・締切・限定性、公式広告文のコピーを追加しない

### CTAの表示契約

`shinken_zemi_cta_v1` の共通CSSは次を満たす。サイト側のCSS実装は本スキルの責任範囲外とし、未実装時に自動作成・変更しない。

- CTA枠は本文幅以内の `width: 100%`、最大幅720px、中央配置、背景 `#fffaf5`、境界線 `#f4d6b5`、角丸12pxを基本とする
- ボタンは幅100%以内・最大420px、最小高さ56px、白文字、`#f6ad49` から `#f08300` のオレンジ系グラデーション、角丸50pxを基本とする
- 計測画像はDOMに保持しつつ、表示寸法を1px×1pxに固定してレイアウトを崩さない
- キーボード操作で識別できるフォーカス表示を持ち、`prefers-reduced-motion: reduce` では移動アニメーションを無効化する
- 320・375・390・768・1280pxの各幅でページとCTAに意図しない横スクロールがなく、ボタンがCTA枠外へはみ出さない

## カード形式の表示契約

料金、口コミ、比較、使い方など、リンク先の記事自体を大きく紹介する必要がある場合は、サイトが対応する内部リンクカードを使える。本文の流れを補足するだけなら通常のテキストリンクを使い、すべての内部リンクをカード化しない。

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
3. 残枠へ任意意図を関連度順に割り当てる
4. 同一リンク先への件数が `max_links_per_destination` を超えないようにする
5. 複数の必須意図が同じリンク先を要求し、上限上どちらかを落とす必要がある場合は `policy_conflict`

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
- 既存リンクが消失・変更していない
- 自己リンク、許可ホスト外URL、未公開候補がない
- 同じ安定キーや同じ意図の重複がない
- `{...URL...}`、`TODO`、`example.com` 等の仮値がない
- `affiliate_link_manifest` にないアフィリエイト計測URLや `rel="sponsored"` のリンクを本スキルが追加していない
- `affiliate_link_manifest` にある進研ゼミCTAは、対象講座、`href`、計測用画像の `src`、`rel="nofollow"`、リード文、ボタン文、リンク先表示文、配置セクションが一致する
- 進研ゼミCTAでは、固定クラス、`data-course`、CTA数、リード文、ボタン文、リンク先表示文、コンポーネントIDが一致する
- 進研ゼミCTAでは、320・375・390・768・1280pxの実表示記録が揃い、ページとCTAの横はみ出し、ボタンの最小高さ・最大幅、計測画像の1px寸法、CTA起因のコンソールエラーがない。記録が欠ける場合は `affiliate_cta_render_unverified`

## 最低限の受入テスト

実運用前とルール変更後は、少なくとも次を確認する。

1. 公開済み同一サイト記事を自然な段落へ1件挿入できる
2. 同じ入力で2回実行してもリンクが増えない
3. 自己リンクを拒否する
4. 未公開・未確認・許可ホスト外の候補を拒否する
5. 必須意図の解決失敗時に元本文を変更しない
6. 曖昧な配置文脈で必須リンクを勝手に置かない
7. HTML化でURLが変わった場合に監査が失敗する
8. 既存リンクが変わった場合に監査が失敗する
9. 任意リンク候補が0件のとき `pass_zero_links` を返せる
10. 候補一覧自体が欠ける場合は `missing_link_inventory` で停止する
11. カード形式では、PCと320px・375px・390px幅の実表示で、画像が左、文章が右に保たれる
12. カード画像の表示幅が、320pxでは84px、375pxでは96px、390pxでは約100px、681px以上では160pxになる
13. カード形式でページ全体の横スクロールやカード外へのはみ出しが発生しない
14. 小学・中学・高校講座の各 `target_course` で、対応するユーザー提供の `href` と計測用画像の `src` が選ばれる
15. 対象講座が一意に確定しない記事では、アフィリエイトリンクを追加せず、通常の内部リンク処理を継続する
16. アフィリエイトCTAがある場合、HTML化後に `href`、計測用画像の `src`、`rel="nofollow"`、リード文、ボタン文、リンク先表示文、配置セクションが `affiliate_link_manifest` と一致する
17. `shinken_zemi_cta_v1` 対応済みサイトでは、講座別CTAが固定DOM契約で1件だけ挿入される
18. CTA対応が確認できないサイトでは、本文を変更せず `affiliate_cta_component_missing` で停止する
19. 同一講座の既存アフィリエイトリンクやCTAがある場合、自動置換や重複追加をしない
20. CTAのURLをHTMLエスケープしても、DOMで復元した `href` と `src` がユーザー提供値に一致する
21. 320・375・390・768・1280pxの実表示記録が欠ける場合、`affiliate_cta_render_unverified` で監査を失敗させる
