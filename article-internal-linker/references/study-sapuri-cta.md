# スタディサプリのCTA契約

[共通配置方針](affiliate-placement-policy.md)と[外観契約](article-design-profile.md)を併読する。providerはstudy_sapuri、component_idはstudy_sapuri_cta_v1。既存のshinken-zemi-cta / __lead / __buttonを表示上の共通CSSとして再利用する（Z会と同様、CSS名を広告主名の根拠にしない）。記事内CSSや独自DOMを追加しない。

- URL正本は[リンク登録簿](study-sapuri-affiliate-links.json)。linksの各項目にtarget_course、href、tracking_image_src、approved_by_user: true、user_instruction、source_refを必要とする。登録がない場合はstudy_sapuri_affiliate_unresolvedとして停止する。過去ログの候補は出典・適用範囲の確認前に登録・利用しない。
- highは高校・大学受験の学校教科、elementary_juniorは小中講座共通のユーザー提供リンク、toeic_basicはENGLISHのTOEICベーシック。学校講座のURLをENGLISHに流用しない。未登録の英会話等へ広げない。大人の学校教科学習と講座の学年を混同しない。
- 学校講座を一つに特定できない記事でも配置ごとに対象を一意に定める。リンクの文言にスタディサプリと対象講座を明記する。終了した合格特訓・パーソナルコーチプランへ申込み可能と案内しない。
- href/srcは登録値を保持し、rel=nofollowと提供された1px計測画像のborder=0,width=1,height=1,alt空を維持する。未確認の計測タグを作らない。
- 各divにdata-courseと一意なdata-placement-idを付け、pの案内文、aのボタン1個と計測画像で構成する。ボタン下のリンク先補足行は追加しない。
- planで適合するリンクと位置を確認し、insert前に表示部品の対応を現行サイトで確認する。原稿・最終HTML・5幅の表示と文脈をauditする。registryが空である現在は「表示部品まで検査基盤対応・承認リンク待ち」であり、講座のアフィリエイト運用済みと報告しない。
