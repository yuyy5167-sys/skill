# Z会の講座別CTA契約

Z会の記事では、ユーザーが提供した3講座のリンクを [承認済みリンクデータ](zkai-affiliate-links.json)から読み取る。別のASP・教材・幼児講座等へ一般化しない。

- `provider: zkai`、`component_id: zkai_cta_v1`とする。
- `cream-manga-mustard-v1`指定では[外観プロファイル](article-design-profile.md)を追加で読み、Z会としての対応を現在実行で確認する。旧オレンジ系表示はこのprofileへ適用せず、共通DOM・URL・計測・件数・案内文は維持する。未対応なら `article_design_profile_component_missing` で停止する。
- 既存サイトでZ会にも使われている`shinken-zemi-cta`と、その`__lead`、`__button`の共通CSSを再利用する。部品IDは広告主を表し、CSS名は既存実装との互換用である。新しいCSSは作らない。
- 集客用・成約用とも[共通配置方針](affiliate-placement-policy.md)に従い最低2件を設置する。Z会のURL・対象講座の条件は維持する。
- 配置ごとに、小学生は`elementary`、中学生は`junior_high`、高校生・大学受験生は`high`へ確定する。学年横断記事では各CTAの直前説明と対象講座を一致させ、単一のリンクを全学年共通として案内しない。資料請求・入会の条件を本文で確認した対象講座だけに案内する。
- `href`と計測画像`src`はデータの値を完全保持する。`rel="nofollow"`、`border="0"`、`width="1"`、`height="1"`、`alt=""`を保持する。URLの検索・推測・置換はしない。
- 共通のCTA件数と意味の規則を使う。各配置に一意な`data-placement-id`と講座の`data-course`を付け、計画・マニフェスト・実DOMを一致させる。
- リード文ではその位置で確認したい教材・条件を伝え、ボタンにはZ会と対象講座を含める。ボタン下の遷移先補足行は[共通方針](cta-caption-policy.md)に従い追加しない。未確認の無料・特典・期限・効果は加えない。
- 原稿・最終HTMLでURL、計測画像、固定属性、配置、表示文、件数を監査する。320・375・390・768・1280pxの表示監査も共通契約を維持する。

挿入時は、外側div、`__lead`のp要素、`__button`のa要素とその内側の1px計測画像から成る既存DOMを使う。アフィリエイトURLは内部リンクへ数えない。
