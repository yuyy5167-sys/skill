# 既存記事修正ワークフロー

## 1. 対象と承認範囲を固定する

対象URL、実在する記事フォルダ、`index.md`、記事固有の `images/` を確認する。タイトルやキーワードだけで複数候補がある場合は編集しない。

開始時に次を記録する。

```yaml
rewrite_contract:
  article_path: ""
  article_url: ""
  business_purpose: conversion | traffic
  user_instruction: ""
  allowed_paths: []
  preserved_frontmatter: []
  requested_frontmatter_changes: []
  heading_policy: preserve | revise_to_current | rebuild
  research_policy: verify_and_update | verify_then_minimal_change | design_only
  image_manifest: []
  cta_policy: ""
  internal_link_policy: ""
  publication_authorized: false
```

同じURLでの内容差し替えは同じ `index.md` を編集する。別フォルダに新記事を作らない。`date`、`draft`、URLに関わるパスやslugは、明示指示がない限り変更しない。

## 2. 保持・更新表を作る

記事を編集する前に、各対象を次のいずれかへ分類する。

| 状態 | 意味 |
| --- | --- |
| `preserve` | 内容・位置・参照を維持する |
| `update` | 現在情報または指定内容へ修正する |
| `remove` | ユーザーが削除を指定、または更新契約上不要と確認済み |
| `add` | 指定された不足要素を追加する |
| `not_applicable` | 今回の修正対象外 |

対象はfrontmatter、導入、各見出し、本文、表、口コミ、埋め込み、撮影写真、スクリーンショット、生成画像、CTA、内部リンクである。

ユーザー撮影写真とスクリーンショットは由来を推測して削除しない。ユーザーの説明、既存キャプション、ファイルの内容から判定し、現在情報と異なる画面は、削除指定がなければ年代注記を付けて残せるか検討する。記事固有の指示を優先する。

## 3. 現行の新記事制作工程へ接続する

`$cloudflare-seo-article-creator` を `approved_existing_rewrite` として使用する。対象記事、事業目的、保持・更新表、画像条件、CTA・内部リンク条件、公開禁止境界を完全に渡す。

新規記事用の既定値が既存記事の明示条件と衝突する場合は、既存記事の現在指示で範囲を狭める。明示条件を無視して新規記事用の構成、CTA数、画像数へ置き換えない。

## 4. 調査と本文

- 変動する料金、特典、端末、保証、対象学年、サービス名称、提供状況は現行の公式情報で確認する。
- `verify_then_minimal_change` では、正しい部分を維持し、古い部分と不自然な文章だけを修正する。
- `verify_and_update` では、見出しの流れを維持する指示があれば、現行情報に合わせて見出し名と本文を更新する。
- `rebuild` は、現在内容と大きく異なり、ユーザーが作り直しを許可した場合だけ使う。
- ユーザーが提供していない体験、成果、写真の由来、口コミ、料金、キャンペーン、URLを作らない。
- 記事固有の「結論を先に置かない」などを別記事へ継承しない。

## 5. CTAと内部リンク

[本文リンク制限と検査](../../cloudflare-seo-article-creator/references/article-link-policy.md) に従う。調査URLは根拠記録に置き、公式FAQ・参考文献を含む非アフィリエイト外部誘導は本文へ出力しない。既存リンクだからという理由で未承認の外部誘導を維持せず、原稿・最終HTMLの双方を共通検査で照合する。今回の明示的な個別保持指示があるURLは原文と出典を記録する。

成約用では `$article-internal-linker` の承認済み講座別CTAを使う。件数、講座、配置、まとめ方にユーザー指定があればその記事だけへ適用する。同じCTAを狭い間隔に詰めず、スマホ表示で余白を確認する。

集客用では直接アフィリエイトCTAを追加せず、公開確認済みの成約用記事へ画像付き内部リンクカードで案内する。タイトルだけで成約用と推測しない。

## 6. 画像工程

[画像一貫性ゲート](image-consistency-gate.md) に従う。本文・導線が確定する前に画像のコピーや構図を固定しない。

各H2は次のモードを持つ。

```yaml
h2_visual_mode:
  heading: ""
  mode: reuse_existing | generate | keep_after_heading_image | remove_outdated | not_applicable
  existing_path: null
  reason: ""
```

`reuse_existing` のH2に重複生成しない。`keep_after_heading_image` は生成したH2画像の後に根拠写真・スクリーンショットを残す。`remove_outdated` は明示された画像だけを本文参照から外し、ファイル自体を無断削除しない。

## 7. 非破壊で反映する

- 新しい画像は未使用の版付きファイル名で保存する。
- 既存画像を上書き・削除しない。
- 対象 `index.md` と記事固有 `images/` 以外を変更しない。
- H2画像は全生成対象が合格してから参照を一括反映する。
- 作業途中の失敗で未参照ファイルが生じても無断削除しない。

## 8. 検証する

少なくとも次を確認する。

- frontmatterと記事ルート
- 指示した保持対象・更新対象・削除対象
- Markdown・HTML構造
- 内部リンク、CTA、計測画像、重複
- ローカル画像参照とHTTP読込
- サムネイルと生成H2画像の形式・寸法・容量
- Astroの本番相当ビルド
- 320、375、390、768、1280pxの表示
- 横はみ出し、画像切れ、文字可読性、CTA間隔
- ブラウザコンソール

`coverImage`を変更した場合は、記事上部、カテゴリ一覧、新着一覧、関連記事カードで実際に新画像が読み込まれていることを確認する。記事ページだけで完了にしない。

すべてのH2を生成画像で覆う契約なら `check-h2-images.ps1` を全件検査に使う。既存画像優先の混在契約では、生成対象へ資産検査を行い、H2ごとの `h2_visual_mode` と実表示を全件照合する。混在契約を機械的なH2画像数一致へ偽装しない。

## 9. プレビューと次の記事

完成版記事URLをユーザーが見えるブラウザへ表示する。URLを文章で返すだけでは表示済みとしない。

ユーザーが承認するまで次の記事へ進まない。承認後も公開指示がなければ、本番反映、Git、Cloudflareは行わない。
