# 白黒漫画サムネイル契約

2026-10-21、ユーザーが白黒漫画・人物なしの試作を採用し、教材名は②と同程度が最適と指定。今後の新規記事のサムネイルに適用する。既存記事の自動置換、H2、本文A〜E、CTA、CSS、公開へ範囲を広げない。

## 選択と資産ごとの契約

正本は [JSON](bw-manga-thumbnail-v1.json)。`asset_visual_profiles.thumbnail: {id: bw-manga-thumbnail-v1, revision: 1}` で選択する。thumbnail専用で、H2への指定は拒否する。新規記事の`section_image`は既存`cream-manga-mustard-v1@1`、本文の`articleDesign.profile`も既存値を保持する。

マップを資産ごとに解決し、個別資産の`visual_profile`と`section_style_contract: {profile_id, revision, sha256}`に保持する。サムネイルにも既存のフィールド名を再利用する。設計・生成要求・親承認・最終報告で**同じ資産内**のID/版/固定文SHAを照合する。サムネイルとH2が同じSHAであることは要求しない。人物ブロックのSHAと原文出典も別途保持し、最終プロンプト変更後は旧承認を失効させる。

生成前に `python3 scripts/validate-visual-profile.py --request-json <依頼JSON> --check-references` を実行する。未知ID/版、要求資産の欠落、矛盾する旧`visual_profile`、H2への誤適用、SHA不一致は生成せず親へ返す。旧単一profile依頼は対応する資産に従い、入力なしの既存依頼は従来仕様を保持する。

## 固定プロンプト

LF・末尾改行1個・UTF-8 BOMなしのSHA-256: `261d6eb62981d6cc5f173e6d0d480da208d59f84445d9b2966e2e5f6d6f45230`。下の固定ブロックを最終プロンプトへ改変せず1回挿入し、人物ブロックを別途選ぶ。旧クリーム・からし色・水彩の指示を混ぜない。

```text
Use case: Japanese education-blog editorial illustration, one finished thumbnail.
Horizontal 16:9 Japanese education-blog thumbnail, ideally 1536 x 864.
REFERENCE ROLE: The supplied approved thumbnail is a STYLE EXAMPLE ONLY. Inherit the bold Japanese type, slightly irregular black ink contours, neutral-gray screentone, airy pure-white paper, faint room detail, pale gray headline underlines, and thin inset hand-drawn rectangular manga panel border. Do not inherit its topic, words, service name, props, layout or exact scene. Never render any text from the reference. Render only EXACT COPY below.
FIXED VISUAL LANGUAGE: Pure white, black and neutral gray ONLY; no cream, yellow, mustard or other tint. Confident manga pen outlines, crisp foreground detail, restrained screen-tone shading, no photo or 3D treatment. The type and large relevant ordinary objects jointly fill the composition; retain an airy white region behind text. Background may suggest a quiet study space with very faint window, shelf or desk lines, subordinate to the foreground. Draw a thin slightly irregular black inset panel border around the whole image. A subtle light-gray underline may sit beneath key text lines; it is an accent, never a heavy text box.
TYPE: Strong, dense, rounded Japanese gothic lettering, opaque black, sharp and correctly spaced, as bold and readable as the reference. One dominant main message; topic identifies the subject; supporting line is smaller but still easy to read at 320 px. Maximum three semantic text groups. Line breaks may follow the specified breaks, never change, duplicate or omit characters. Avoid long tiny text. Text and primary objects must stay separate with generous breathing room and safe margins; frame and desk may approach the edge. Do not mechanically shrink the entire composition to create margins.
Only EXACT COPY may be readable. No extra letters, labels, fake handwriting, invented UI, prices, statistics, scores, ranks, reviews, dates, badges, logos, watermark or service screenshots. Props may have a few nonverbal rules, blank keys, neutral bars or simple geometric marks as specified; no words or numerals. No gradients, heavy shadows, dramatic speed-line bursts or decorative symbols unrelated to the article.
Do not reuse any other newly generated trial thumbnail as a reference.
For each service name, MATCH the preferred typography reference at equal canvas width: similar apparent glyph height (about 12% of image height, roughly 22px at 320px width). This is the preferred STANDARD, not a minimum to exceed. Do not make a giant brand headline. Keep the name intact; wrap qualifiers such as の料金 or の解約, or reflow the layout rather than shrinking or over-enlarging the name. Follow the separately supplied character policy exactly.
```

## 人物方針

既定は`thumbnail_character_mode: personless`。JSONの`character_policy_prompts.personless`を1回挿入する。手だけ、画面や本の中の顔、動物、マスコット、擬人化小物も出さない。人物正本の存在や育児記事であることを追加理由にしない。

ユーザーが当該サムネイルで人物を明示したときだけ`person`を選び、`thumbnail_character_instruction: {user_instruction, source_ref}`に原文と会話出典を保持する。人物ブロックだけ`person`へ切り替え、ZERO-CHARACTERS指示と併用しない。学年・役割に合うactive正本を確認し、顔・髪・年齢・体格・服の形を保って白黒明暗へ変換する。未採用中学生や未確認のお父さんの正本を推測しない。この人物なし方針をH2へ転用しない。

## 参照・文字・構図

JSON登録の承認見本を通常1〜2枚目視し、生成にも画風だけの参照として渡す。②は教材名字高の正本でもある。別の画風見本を使う場合も②を同じ表示幅で目視し、見た字高を合わせる。②を第2画像として渡す場合は文字サイズだけの参照と明記する。直接参照できなくても目視・文章化・生成後比較ができれば既存規則で続行できる。必要な正本を開けないときは他の画風へ黙って切り替えない。

- 教材名は②と**同程度**を標準にする。最低値としてさらに大きくしない。画像高の約12%（320px幅で約22pxの字高）は目安で、ブロック幅や文字数ではなく、同一表示幅で並べた見た字高で判断する。ユーザーが大きすぎると指摘した拡大版は見本に登録しない。
- 長い題名は教材名と「の料金・の解約」等を分けて自然に改行する。生成前に `image_plan.brand_name_layout: {service_name, qualifier, topic_lines, size_reference_path}` を具体化する。長い題名が1行で基準より小さくなる場合は、教材名を1行、修飾部を別行とする改行を `exact_copy` と最終プロンプトへ明示し、生成モデルの自動縮小に任せない。教材名そのものを途中で切らず、過小文字や巨大なブランド見出しで収めない。主文を最も強くし、主題・主文・任意補足の最大3組にする。
- 記事本文から主質問、読む価値、本文へ任せる詳細を先に決める。見本のZ会等の名前、コピー、小物、左右配置を転用しない。料金・比較・手続き等の記事の意味から、主役小物と情報構造を選ぶ。
- 新規生成に「元の文字を保持」「父を削除」等の編集指示を混ぜない。参照の役割、固定文、人物ブロック、記事要点、構図、exact_copy、除外要素を区別する。画像編集では変更点と保持点を別途指定する。
- 薄い部屋、大きな小物、太い文字、白地、細いコマ枠の釣り合いを保つ。各辺8%は目安であり、余白のために全体を一律縮小しない。改行と配置で文字切れや小物との衝突を解決する。
- ユーザーの今回の明示指定が優先。生成しただけの試作を採用例へ自動昇格させない。JSONに採用根拠付きで個別登録した例だけを使う。

## 検品・試験

原画像とWebPで、確定文字の1字ずつの一致、教材名の②との字高比較、白地・黒灰、人物方針、意味、小物、差別化を確認する。人物なしは`character_identity: not_applicable`、不混入は`character_policy`で確認する。`brand_name_size`へ正本path、表示幅、観測箇所、理由を記録する。教材名のない一般勉強法なら`not_applicable`とし、商品名を創作しない。

1536×864 WebP、目標300KB以下。320/375/390/768/1280pxの実カード・本文導入・内部カードを確認する。単体縮小プレビューと実サイトCSS検証を分け、未実施を合格にしない。H2の固定文・配色を保ち、異なるprofile間の`runtime_style_delta`は転送しない。

形式/接続試験では資産解決、旧入力、旧新矛盾、未知ID/版、人物の既定/明示指定、H2誤適用拒否、参照欠損、SHAを確認する。再現性の生成試験は異なる3記事×2回の新規サムネイルを対象とし、前の出力・指摘を次の初回入力へ渡さない。今回変更しないH2を6枚再生成する必要はない。5題の試作と限定編集は好み・文字サイズの確認であり、独立反復試験ではない。

完了時は実装、形式/接続、実画像、実サイト、独立反復、ユーザー評価、GitHub保存を分ける。少数の試作だけで毎回の同品質を保証しない。
