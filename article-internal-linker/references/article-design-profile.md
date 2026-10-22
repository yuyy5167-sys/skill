# 教育ブログ用CTA外観プロファイル

## 適用と正本

2026-10-20にユーザーが承認した修正版設計書v3を、このブログの今後の新規記事へ適用する。対象は正規化後の `/Users/yudaikato/Documents/AIフォルダ/ブログ/公開サイト・教材/勉強ブログ` に一致し、親から `articleDesign.profile: cream-manga-mustard-v1` を受け取った記事だけ。別ブログ、未指定の旧記事、既存下書きへ自動適用しない。今回の既存10記事は個別設定の互換経路を維持し、新規記事用設定へ書き換えない。

この文書は外観だけを扱い、件数・配置・意味は[共通配置方針](affiliate-placement-policy.md)を正本とする。両目的とも最低2CTA、集客用は主成約記事カード1件を維持する。A〜Eから目的や件数を推定せず、過去の個別0/1件指定を新規実行へ適用しない。URL・計測・属性・ボタン下補足行禁止は維持する。

- `articleDesign` は記事frontmatterと同じオブジェクトを親が渡す。`profile`、`design: A | B | C | D | E`、空でない`label`、`showMaterialFinder`（省略時false）を保持する。ラベルは案内コピーや事業目的ではない。
- profile未指定では従来のプロバイダー別表示契約を使う。未知のprofile、親の指定と最終DOMの不一致、既定への黙示的な退避は許可しない。
- `showMaterialFinder` は本文末尾の教材診断案内の表示設定であり、CTAや集客用主成約記事カードの代替・件数根拠ではない。共通フローティング診断ボタンは別の既存仕様として維持する。
- 新規記事への適用確認は `articleDesign.profile` とサイト実装の両方で行う。共通CSSを編集する権限を本スキルへ追加しない。

## 使う前に確認する実装

`plan`では外観指定まで記録し、まだ未確認のCSSを確認済みにしない。`insert`では現在実行で、サイト共通CSSと生成DOMの次を確認する。確認できなければ本文を変更せず `article_design_profile_component_missing` で `blocked` とする。

1. `site_rendering_capabilities.article_design_profile` が同じprofile、`supported: true`、現在の`verified_in_run_id`、追跡可能な`style_source`、`scoped_to_profile: true`を持つ。
2. CTAを使う各プロバイダーの `affiliate_cta_component` または `affiliate_cta_components` が従来の部品IDに加えて `appearance_profiles: [cream-manga-mustard-v1]` を持つ。進研ゼミ・スマイルゼミ・Z会を一括で対応済みと推測しない。使うプロバイダーごとに確認する。
3. `scope_selector`が示す共通CSSが `.article-edition[data-article-profile="cream-manga-mustard-v1"][data-article-design-origin="frontmatter"]` 配下で適用され、旧10記事や未指定記事へ新しい外観が漏れない。profileを解決するサイト処理が確認できる。
4. 内部リンクカードは既存の変換と部品を使い、このprofile用の外観が同じスコープで適用される。

親/UIの汎用部品対応を示す `site_rendering_capabilities.article_design` とは別の確認であり、一方のtrueをもう一方の確認の代用にしない。実装済みであることと、現在の最終ページで実表示を検査したことも分ける。

## CTAの外観

このprofileでは `placement-rules.md` の従来オレンジ/緑系の背景・文字色・グラデーション・大きな角丸の指定を次で置き換える。それ以外の固定DOMと意味・寸法の契約を保つ。

| 要素 | このprofileの表示 |
| --- | --- |
| 枠 | 本文幅以内、最大720px、中央配置。薄いクリーム又は透明背景、黒系の文字、控えめな境界線 |
| ボタン | からし色 `#EDCE68`、黒系の文字（基本 `#242422`）、細い濃色枠、角丸3pxを基本。従来のオレンジ/緑グラデーションを重ねない |
| ボタンの寸法 | 幅100%以内・最大420px・最小高さ56px。日本語を省略せず折り返す |
| 計測画像 | 元のDOMと固定属性を保持し、表示寸法も1px×1px。本文画像用の幅100%や16:9を適用しない |
| 操作状態 | 下線や枠・明確なフォーカスを併用し、色だけに依存しない。動きを設ける場合はreduced-motionを尊重 |

スタディサプリは専用契約のstudy_sapuri_cta_v1で既存shinken-zemi-ctaを再利用する（URL承認と現行表示確認が前提）。進研ゼミは `shinken-zemi-cta`、スマイルゼミは `smile-zemi-cta`、Z会は互換用の `shinken-zemi-cta` を使う。広告主ごとの `component_id` はそれぞれ `shinken_zemi_cta_v1`・`smile_zemi_cta_v1`・`zkai_cta_v1` のまま。profile用の独自CTA DOM、クラス、記事内CSSを作らない。URLや計測画像を新しい部品の都合で削除・変更しない。

## 内部リンクカード

カードの選定・固定DOM・画像解決・画像左/文章右・幅別寸法・画像カード最大2件は [配置規則](placement-rules.md)を維持する。新profileではクリーム/黒系/からし色、控えめな罫線と角丸なしの共通外観へ合わせる。サムネイルは16:9の枠内で全体を表示する `object-fit: contain` とし、新しい生成サムネイルの文字や人物を切らない。profile未指定の従来 `object-fit: cover` は変更しない。

カードが必要な記事では、そのprofile対応も現在実行で確認する。非対応を理由に主成約記事カードを通常テキストへ変更したり、タイトルや説明を省略したりしない。

## insert/auditの記録と合格条件

- `articleDesign`を親から受け取り、`expected_link_manifest`及びCTAを使う場合の`affiliate_link_manifest`へ `appearance_profile: cream-manga-mustard-v1` を保持する。
- `audit`では `rendered_page_checks.article_design_profile` にprofile、実際のdesign、frontmatter由来であること、CTA/カードの外観一致、使用プロバイダー、確認した共通CSS、各幅の結果を記録する。対象記事外へ表示が漏れないことも回帰確認する。
- CTAの全固定DOM・URL・src・講座・1px寸法・rel・placement_id・件数・案内文は従来どおりマニフェストと照合する。外観一致だけで合格にしない。
- 320・375・390・768・1280pxで、黒文字/からし色ボタン、折返し、枠内寸法、計測画像1px、ページと部品の横はみ出し、フォーカスとCTA起因のコンソールエラーを確認する。内部カードがあれば画像全体と文字が読めることも確認する。
- profile指定とDOMの不一致は `article_design_profile_mismatch`、必要な実表示記録不足は `article_design_profile_render_unverified` とし、いずれも `blocked`/`blocks_draft: true`。実装不足と実表示未確認を混同しない。

最低限、同じC型の成約用と集客用が異なる導線契約を保つこと、各プロバイダーの外観、固定URLと計測、profile欠落/未対応/不一致、旧10記事と未指定記事への非漏出を確認する。
