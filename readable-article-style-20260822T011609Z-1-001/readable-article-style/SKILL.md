---
name: readable-article-style
description: Write or refine adult-targeted article body text with source-traced readable structure, gentle Japanese tone, and an iterative readability quality gate.
---

# Readable Article Style

ユーザーまたは呼び出し元から渡されたリード・見出し配下の本文を、新規作成（`new`）または推敲（`revise`）する文章専属スキル。対象は大人だが、中学生レベルの理解力でも意味を追える日本語にする。子ども向けの話題・幼い語り方・過度な単純化にはしない。

## 参照範囲

- 通常実行では、同梱の `references/style-guide.md`、`references/template-guide.md`、`references/readability-quality-gate.md` を読む。
- 参照URLを取得・再分析しない。`references/source-analysis.md` は出典の追加・差し替え・再分析を行う保守作業でだけ読む。
- 4本の書き方記事からは構成・説明技法・段落・箇条書き・具体化を、2本のKracie記事からは口調だけを採る。広告、商品導線、分類、FAQ、プロフィール、関連記事、固有の内容・数値・例・口癖は採用しない。

## 呼び出し元との境界

呼び出し元がタイトル、見出し構成、調査、事実確認、SEO、HTML化、公開を担当する場合は、その範囲を尊重する。見出しを追加・削除・変更・並べ替えず、本文単位内にもHTML/Markdownの見出しや見出し相当の小ラベルを作らない。

## 静的サイト連携の境界

- このスキルは記事本文の作成・推敲だけを担当し、Astroのfrontmatter、URLルーティング、画像パス、記事フォルダ構造は変更しない。
- `markdown` または `html_fragment` の入力を受ける場合も、呼び出し元から渡された本文単位の境界と保持対象をそのまま尊重する。
- Cloudflare Workers、Wrangler、GitHub連携、ビルド、デプロイ、サイトのレイアウトやナビゲーションは担当しない。
- この補足は連携境界を定めるものであり、文章ルール、テンプレート、品質ゲート、出力形式を変更しない。
- d MCPその他の外部ナレッジ検索は、このスキルの実行時依存にしない。

構造化された依頼では、各本文単位について少なくとも次を受け取る。

- `mode`: `new` または `revise`
- `section_id`、`section_type`（`lead` または `heading`）、見出し文、見出し階層（リードは該当なし）、親見出し文または「親見出しなし」、担当範囲、前後のつながり
- `new` のテーマ・必須要点・使用可能な根拠
- `revise` の本文と保持対象（事実、結論、条件、引用、リンク、HTML構造など）
- `input_format`: `plain_text`、`markdown`、`html_fragment`

次の項目は任意で受け取る。

- `review_scope`: `section` または `article`。未指定時は本文単位数にかかわらず `section`。
- `article_complete`: `review_scope: article` のときだけ必須。渡された本文単位が記事全文であることを示す `true`。
- `reader_profile`: 対象読者、前提にしてよい知識、読後に理解・判断してほしいこと。未指定時は「大人向け、中学生相当の説明難度、本文外の専門知識は前提にしない」とする。
- `quality_profile`: `required`（合否に使う基準と観察可能な合格状態）、`preferred`（不合格にしない好み）、`prohibited`（避ける表現・書き方と適用範囲）で指定する。
- `max_iterations`: 評価・修正ループの上限。未指定時は5。
- `quality_report`: `none`、`summary`、`full`。構造化された依頼の既定は `none`、直接依頼の既定は `summary`。

複数の本文単位が渡されただけでは記事全文とみなさない。`article_pass` は、順序・見出し階層・前後関係を含む記事全文と `article_complete: true` がある場合だけ判定する。直接依頼で記事全文であることが明示された場合だけ、この二つを推定できる。

`quality_profile.required` または `quality_profile.prohibited` が、事実・結論・根拠・構造の保持または安全性と競合する場合は修正しない。競合箇所と必要な判断を添え、`reason: quality_profile_conflict` で停止する。

`html_fragment` は呼び出し元が既存の段落・リストのブロック境界、保持タグ・属性・リンク位置を対応づけて渡す。本文だけを返し、ブロック境界、段落数、リスト構造、見出し構造を変更しない。構造変更が必要なら本文を返さず `needs_parent_input` にする。

ユーザーから直接依頼され、構造化された入力がない場合は、依頼文・提示本文・明示された事実だけを使う。事実や保持条件が不足していて安全に補えないときだけ、必要最小限の確認を求める。

## 実行手順

1. 入力、評価範囲、保持対象を検証する。構造化された依頼で必須情報がない、親見出しが未受領で「親見出しなし」とも明示されていない、または `article` に必要な全文性が確認できない場合は、`reason: insufficient_input` で停止する。
2. `lead` はLテンプレート、`heading` はTテンプレートを、本文単位の読者の問い・要点・根拠・前後関係から選ぶ。選択理由を内部メモに記録する。
3. `new` は渡された根拠の範囲で書く。`revise` は既存の事実・結論・条件・引用・リンク・HTML構造を保持し、意味・根拠・結論の変更が必要なら `reason: content_change_requires_parent` で停止する。
4. 現在版、読者の問い、必須要点、根拠、保持対象、`reader_profile`、適用する品質基準を固定する。
5. `references/readability-quality-gate.md` に従い、前回の指摘を見ずに、段落・節の役割、読解摩擦、初見読解、保持対象を評価する。評価者自身の専門知識で本文の不足を補わない。
6. 場所、未達基準、読者への影響、根本原因、保持対象内の修正方針を示せる問題だけを登録する。好みだけの言い換え、根拠のない短文化、意味を変える単純化は登録しない。
7. 問題があれば、P基準、論理・前提、構成、文の負荷、仕上げの順で必要最小限に修正する。`html_fragment` で段落・リスト構造の変更が必要なら `reason: structure_change_requires_parent` で停止する。
8. 修正後は、修正箇所だけでなく節または記事全文を、前回の点数・問題一覧を見ずに再評価する。その後に保持対象と直前版を照合し、回帰がないことを確認する。
9. 評価から修正、独立再読、回帰確認、判定までを1回と数える。初回評価で修正不要なら1回、本文評価前の入力不足・競合で停止した場合は0回とする。
10. 同じ根本原因が根拠に基づく修正後も2回連続で改善しない場合は、言い換えを繰り返さず `reason: quality_plateau` で停止する。上限に達しても未解決の実行可能な指摘が残る場合は `reason: quality_gate_exhausted` で停止する。上限到達を合格にしない。

## 出力契約

構造化された依頼では、各本文単位を入力順に返す。`complete` なら既存どおり `template_id` と `body` を返す。`quality_report: none` では、既存の出力形に品質フィールドを追加しない。

`quality_report: summary` または `full` では、各本文単位に次の `quality` を追加できる。

- `scope`: `section` または `article`
- `gate_status`: `section_pass` または `article_pass`
- `iterations`
- `reader_profile`: 判定に使った読者像と前提知識の要約
- `applied_profile`: 適用したユーザー固有基準の要約
- `unresolved_findings`: 合格時は空
- `preservation_check`

`review_scope: article` では、各本文単位の結果に加えて、記事全体の `article_quality` を一つ返す。ユーザーからの直接依頼では、完成本文の後に反復回数と合格範囲を簡潔に示す。

`needs_parent_input` なら `body` は空にし、次のいずれかの `reason` を返す。

- `insufficient_input`
- `structure_change_requires_parent`
- `quality_gate_exhausted`
- `content_change_requires_parent`
- `quality_profile_conflict`
- `quality_plateau`

停止時は未達基準、該当箇所、試した修正、残った根本原因、不足情報または呼び出し元の判断事項を添える。未確定の本文を完成記事へ組み込ませない。`quality_report: full` が明示された構造化依頼だけは、非完成である旨を付けた候補本文と未解決問題を `quality.resume_state` に分離できる。

詳細な書き方規範は [references/style-guide.md](references/style-guide.md)、テンプレートと選択順は [references/template-guide.md](references/template-guide.md)、合否基準と反復手順は [references/readability-quality-gate.md](references/readability-quality-gate.md) を読む。
