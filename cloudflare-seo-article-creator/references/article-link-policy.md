# 記事本文のリンク制限と検査

対象は `C:\AIフォルダ\ブログ\site` の新規記事と既存記事修正。成約用・集客用の両方に適用する。

- 読者向け本文へ配置できる誘導は、確認済みの自サイト内部リンクと、その記事で承認済みのアフィリエイトCTAだけである。CTAを追加できるか・件数・講座は既存の目的別契約に従う。
- 公式トップ、FAQ、規約、購入窓口、ログイン、研究論文、参考文献、脚注も、外部URLを本文へ置く理由にはならない。AIが「手続きに必要」「根拠として有用」と判断して例外を作らない。
- 調査は一次情報で続け、根拠URLと確認内容は調査記録に保持する。記事では必要に応じて資料名・発行元をリンクなしで示す。リンクを削除して根拠のない断定へ変えてはならない。
- リンクを外した裸URLや、不要な「詳しくは公式へ」という文へ置き換えない。記事内で回答する。アフィリエイトの代わりに公式通常リンクを置かない。
- 今後ユーザーが当該記事・URLの掲載を明示的に指示した場合だけ、その原文と発言出典を例外マニフェストへ記録する。AIの理由文はユーザー許可の代わりにならない。既定の例外配列は空。
- 既存の口コミ埋め込み等に個別の保持指示がある場合は、その指示を狭く適用する。他の外部URLの許可にはしない。

## 完成前の必須検査

原稿と、今回ビルドした最終HTMLの本文領域を `scripts/audit-article-links.mjs` で検査する。Markdownリンク・参照形式・脚注・HTMLアンカー・画像リンク・内部カード・裸URLを対象にし、画像のsrcや計測画像のsrcを誘導リンクとして誤判定しない。

入力は標準入力JSON。許可アフィリエイトURLは `$article-internal-linker` の承認済みマニフェストから渡す。本文に存在するURLをそのまま許可リストへコピーしない。ホスト名だけの包括許可もしない。

```powershell
$auditInput = @{
  project_root = $projectRoot
  article_path = $articlePath
  rendered_html_path = $builtArticleHtmlPath
  affiliate_manifest = $approvedAffiliateManifest # links配列。CTAなしは @{ links = @() }
  allowed_external_links = @() # 通常は空
} | ConvertTo-Json -Depth 30 -Compress
$auditInput | node 'C:\Users\yuyy2\.codex\skills\cloudflare-seo-article-creator\scripts\audit-article-links.mjs'
if ($LASTEXITCODE -ne 0) { throw '本文リンク検査が不合格です。該当リンクを修正して再検査してください。' }
```

例外1件の形式は `{ href, approved_by_user: true, user_instruction, source_ref }`。このデータ自体は承認を生成しない。実際のユーザー発言と照合する。

- `source.status` と `rendered.status` がともに `PASS`、`disallowed_external_link_count: 0`、記録された記事・HTMLのSHA-256が最終ファイルと一致することを確認する。
- 本文領域がない、未検査、失敗、古い成果物の検査結果では完成・公開準備完了にしない。検出した箇所を修正して再検査する。
- `check:content`、`build:cloudflare`、`check:built` はこの誘導方針を検証しないため、成功しても本検査の代わりにならない。
- `validate-cloudflare-article.ps1` は基本検査でも本検査の原稿側を必ず呼ぶ。完成判定の`-ValidationMode parent`では`-RenderedHtmlPath`が必須で、最終HTML未検査のまま合格できない。ビルド前の事前検査は`basic`または共通検査で行う。`-AllowedExternalHref`だけでは許可できず、例外は`-AllowedExternalApprovalJson`の発言証跡が必要。
- 記事またはビルドHTMLを変更したら、その版で再検査してからプレビューを提示する。
