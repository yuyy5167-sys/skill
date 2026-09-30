# ワークフロー

## 0. 実行前確認

1. メインキーワードと、記事を作成する明示的な指示があることを確認する。「作成してください」「作ってください」など表現が異なり、依頼文に「新規」という語がなくても、既存記事ではなく本スキルの新規記事範囲だと確認できれば対象にする。
2. ユーザーへ`成約用`か`集客用`かを確認する。依頼文に明記されていれば再質問せず、その原文を確認回答として記録する。明記がなく、または「任せる」など選択が確定しない場合は、定義と推奨理由を示して選択を待つ。キーワード・記事型・履歴から推測しない。
3. `article_business_purpose.status: confirmed`、`type: conversion | traffic`、`confirmed_by_user: true`、確認原文と出典、目的別`primary_action`がそろうまで、調査・タイトル・見出し・本文・リンク・画像・ファイル・プレビューへ進まない。依頼原文のログ記録だけは実行できる。
4. 対象が`C:\AIフォルダ\ブログ\site`の新規記事であることを確認する。既存記事のリライトなら本スキルを使用しない。
5. `C:\AIフォルダ\ブログ\クラウドフレア\記事装飾ルールブック.md`を全文読む。
6. 対象プロジェクトの`AGENTS.md`、`src\content.config.ts`、記事ルート、現在のfrontmatterを読み、実装時点のスキーマを確認する。事業目的は実行状態とログへ保持し、未対応のfrontmatterフィールドを追加しない。
7. 既存の未コミット変更を読み取り確認し、ユーザーの作業へ触れない。
8. 必要な依存スキルと表示手段を確認し、現行`SKILL.md`と必要な参照文書を工程直前に読む。PowerShell 5.1以上、Node.js、Python、既存`node_modules`のsatteriとAstroを確認する。PS5.1ではUTF-8 BOM付きps1を`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <script>`で実行できる。`Bypass`は当該子プロセスだけとし、永続ポリシー変更や依存関係の自動インストールをしない。
9. `$article-internal-linker`の現行契約を読み、成約用では講座別アフィリエイトURLとCTA共通CSS、集客用では主リンク先が公開確認済み成約用記事である証拠と内部リンクカード機能を確認する。仮リンクや仮CTAを作らない。
10. 確認済み事業目的、記事ID、`index.md`、サムネイルと各H2見出し画像を含む画像フォルダ、作成理由、主要導線、`draft: true`、上書き・公開禁止を実行範囲通知として示す。ここから1記事分の`orchestrated_prepublication`一括承認が成立し、通知後は最終プレビューのユーザー表示まで進める。

一括承認の範囲内では、計画、タイトル選定、調査、見出し、本文、内部リンク、権利条件を満たす画像、サムネイル、各H2見出し画像、保存、検査、修正、隔離プレビューについて途中承認を追加しない。計画書、TODO、進捗、検収結果は進行共有として提示する。ユーザーが停止または区切りでの一時停止を指示した場合は、安全な区切りで止めて状態を保持し、再開指示を待つ。

スキーマとルールブックが矛盾する場合は、記事ファイルへ未対応フィールドを追加せず、矛盾、影響、必要なサイト側変更を報告する。サイト側変更を記事作成へ便乗して実施しない。既存記事変更、上書き、公開、デプロイ、Git操作、ユーザーにしか決められない判断など、一括承認を超える権限が必要な場合だけ`BLOCKED`として停止する。人間確認後の明示的な公開指示によるGitHub保存だけは、13の事前通知と限定承認がそろった場合に別工程として実行できる。

## 0.25 依頼単位の詳細品質ログ

`$article-production-log`の[接続契約](../../article-production-log/references/integration-contract.md)に従い、ユーザーの今回の発言を一件のログにする。

1. 正規プロジェクト、記事ID、予定記事パス、依頼種別、`run_id`、`parent_run_id`を確定する。
2. ユーザー原文を改変せず`start-log`へ渡し、文脈、明示要件、AI解釈、未確定事項、対象外、初期品質軸を分離する。事業目的確認前は`pending_confirmation`、明示済みまたは確認回答では`conversion | traffic`、確認原文・出典・主要行動を記録する。フックIDがあれば関連付けるが、フックがなくても直接記録する。
3. 取得した`article_log_context`を全工程へ渡す。子は同じ発言の別ログを作らず、担当工程で確認した品質課題と検証だけを親へ返す。
4. 統合検査後、実施内容、変更しなかった範囲、変更前後の証拠、変更ファイル、品質課題、検証、学習分類、継続候補、未解決事項を同じ`log_id`へ`finish-log`する。
5. 記録の`verify-store`が失敗した場合は保存済みと報告せず、記事成果物の状態とは分けて未記録範囲と再実行条件を報告する。

## 0.5 修正履歴と有効ルールの接続

`$article-skill-feedback`の[親子スキル接続契約](../../article-skill-feedback/references/integration-contract.md)に従い、次を行う。修正依頼では品質ログの`log_id`と本台帳の依頼・結果イベントIDを相互参照する。

1. 正規化した`project_root`が`C:\AIフォルダ\ブログ\site`と一致することを確認し、記事ID、予定記事パス、`run_id`、`parent_run_id`、`entry_skill: cloudflare-seo-article-creator`を固定する。
2. `target_skill: cloudflare-seo-article-creator`、`stage: orchestration`で有効ルールを取得する。台帳全体や候補ファイルを直接読んでルールを再解釈しない。
3. 初期の検証済み空集合なら通常工程へ進む。索引が欠落・破損している場合はルール依存の動作だけを止め、既存規約による記事作成を続けられるか判定し、異常と未適用範囲を残す。
4. `article_business_purpose`を必須条件としてルールを取得する。調査後に`article_type`または`grade`が確定・変更された場合は、同じ実行IDと同じ事業目的で再取得する。取得した集合IDと版を全下流へ引き継ぐ。
5. 子工程の直前に、対象スキル・工程に一致するルールだけを既存入力契約へ変換する。受け口がなければ、渡しただけで完了にせず接続変更または`BLOCKED`を記録する。
6. 記事への修正依頼をこの実行で扱う場合は、編集前に原文を`record-request`、実物検証後に結果を`record-result`へ記録する。親子は同じ`event_key`を使う。

継続ルールは`active`だけを使う。現在の明示指示、固定された安全・権限・事実保全規則、各専門スキルの通常裁量を置き換えない。記事修正への「はい」と継続ルール採用を同じ承認として扱わない。

## 1. 入力の固定

メインキーワードと確認済み事業目的は必須とする。事業目的以外は、次の不足が記事の意図、結論、記事分割、実体験表現、保存先を変える場合だけ質問する。

- 対象読者と記事の目的
- 対象学年またはカテゴリー
- ユーザーが保有する実体験・独自情報
- 既存記事一覧または内部リンク候補の正本
- 新規記事の識別子、日付、保存先

未指定事項を創作せず、影響しないものは既定値または未指定として進める。

記事全体で検索者 `search_reader`、サービス利用者 `service_user`、主要評価軸 `primary_decision_axes`を分けて保持する。評価軸は主検索意図から決め、調査後に確定する。教材の操作・理解・復習・継続・管理は、教材の利用体験を評価するときに用いる。料金・契約・手続きが主質問なら、それを中心に答える。

調査後に`article_profile.type`を`conversion_review_price | conversion_other | traffic`へ確定する。口コミ、評判、料金のいずれかが申込み判断の中心にある成約用記事は`conversion_review_price`とし、お試し・キャンペーンなどその他の成約用は`conversion_other`とする。単語だけでなく、主質問と主要判断項目で分類する。

検索意図と関係のない保護者管理論へ置き換えず、教材側の支援を調べないまま家庭の努力に解決を委ねない。下流工程へ旧来の固定評価軸を併記せず、[入出力契約](input-output-contract.md)の変換規則で引き継ぐ。

## 1.5 読者ニーズ仮説

本スキルはキーワードから検索背景、最優先の疑問、読後の到達点を仮説として整理する。確認済み事実と区別し、調査目的・疑問・必要な根拠・確認条件を定め、仮説への反証や重要な追加疑問も収集する。完全な調査レポートと結論を左右する原資料を読み、2.5で仮説を修正して記事方針を確定する。初期仮説を維持するために根拠を選別しない。

## 2. 競合調査

`$seo-keyword-competitor-research`を直接実行し、指定キーワードの現行Google検索結果と一次情報を調査する。現在のサイトと既存記事一覧を渡し、意図の衝突を確認する。検索意図・記事方針の推奨は判断材料であり、制作方針の自動確定ではない。

次を満たす場合だけ2.5の回答補完・検収へ進む。

- Googleを直接確認している。
- リサーチのQuality Gateが完了している。
- 推奨方針が`新規作成`または前提のそろった`意図を分けて新規作成`である。
- 見出しを変える未解決事項がない。

`既存記事へ統合`、`既存記事をリライト`、`別キーワードを検討`、`追加確認`なら、新規記事を作らず停止状態を返す。

## 2.5 一次情報の補完と疑問一覧の検収

競合の論点整理と、記事が答えるための根拠収集を分ける。公式の商品ページ、FAQ、料金表、利用条件、教材見本、マニュアル等から主質問と判断条件に必要な情報を選ぶ。毎回すべて読むことや出典数の達成を目的にしない。

本スキルは疑問ID、現在の回答、不足、結論への影響、確認済み出典を基に追加調査を直接実行し、事実・出典・確認日・適用条件・確認状態・未解決点を記録する。原資料を読み、回答を統合して記事方針を決定する。

`conversion_review_price`で口コミを扱う場合は、良い口コミと悪い口コミを別々に調査する。各掲載候補には利用状況、評価対象、読者の判断への意味を持たせ、一言感想や同義の水増しを除外する。悪い口コミが見つからない場合は創作せず、確認した情報源と調査結果を記録する。公式仕様から導く注意点は口コミと分離する。料金を扱う場合は、公式情報から基本料金だけでなく、検索判断に関係する支払方法、タブレット代、継続・退会、キャンペーン条件を確認し、確認日と適用範囲を保持する。

本スキルは次を別々に検収する。

1. **疑問の網羅性**：キーワード・読者・公式情報から、結論、対象者、費用、利用可否を変える条件が抜けていないか確認する。これらを全記事の必須見出しにはしない。重要候補を除外した場合は候補と理由を `question_coverage` に保持する。FAQの全項目を記事へ入れない。
2. **回答の充足**：主要な疑問ごとに回答、根拠、適用条件、記事側の解釈、不明点を対応づける。確認状態は [入出力契約](input-output-contract.md)の4状態で管理する。

`supported` は確認範囲で使い、`partially_supported` は主張を限定する。`unverified` は調査範囲・不明点・影響を明示する。`conflicting` は時点・対象・条件の違いを再調査する。補足情報の不明点が主回答を妨げなければ明示して進める。主回答を左右する不足・矛盾がある場合は断定的な構成へ進めず、追加調査または根拠に収まる結論の限定を行う。「確認できない」こと自体が回答になる場合も、調査範囲と判断不能な内容を含む構成を検収する。合理的に解消できず安全な回答範囲も定まらない場合は、既存の `BLOCKED` と根拠・再開条件を返す。

見出し設計に使う調査入力は完全な上流レポートとする。受理済み補完を検索意図・ペルソナ・一次情報・不明点・Quality Gateへ反映し、レポートと`answer_map`の一致を検収する。要約や回答表だけで代替しない。G1合格後に構成を設計する。

## 3. 見出し構成

完了済みリサーチレポートの全内容を入力として`$seo-heading-outline-creator`を直接実行し、タイトル・見出し・順序・各章の役割を決める。スキルの`status: PASS`と後述の二段階再確認を必要条件とする。

- 3タイトル候補と各候補の個別品質判定を保持し、`status: PASS`の推奨案をfrontmatterの`title`へ自動採用する。`title_contract`へ推奨タイトル、採用タイトル、一つの`core_promise`、本文へ移す`supporting_topics`、初見判定を記録する。
- H1は記事設計上だけ保持し、本文へは書かない。
- H2・H3の安定ID、役割、根拠に加え、各H2の`reader_question`と`reader_outcome`を保持する。
- `needs_research`、`needs_user_decision`、`iteration_limit_reached`を完成構成として扱わない。
- 見出しと結論が確定した`primary_decision_axes`に一致し、固定の学習動作へ逆戻りしていないか確認する。
- 各見出しの`required_answer_ids`を`answer_map`へ対応づけ、不明な内容を確認済みのように約束せず、章間で同じ回答を繰り返さない。

読者価値の再確認では、前回の問題台帳、採用理由、詳細な根拠説明を先に読まず、対象キーワード、主検索意図、ペルソナ、タイトル、H2、H3から次を確認する。同一実行者による再確認を独立検証と呼ばない。

1. 主質問への答えまたは判断の入口が、論理的に置ける最も早いH2にある。
2. 各H2から、読者が得る答え、判断材料または次の行動を説明できる。
3. 執筆者の確認・調査・検証作業の羅列になっていない。
4. 興味を作るために未確認事実、根拠のない効果、優位性または煽りを加えていない。
5. タイトルが区切り記号で複数の補足論点を詰め込まず、一つの中心的な読者価値を約束している。

不合格なら見出し設計を直接修正し、見出しスキルの全品質ゲートと二段階再確認を実行する。確定した見出しの文言・順序を本文作成の固定事項として保持する。

## 4. 内部リンク計画と記事設計

見出し構成と読者の疑問から、確認済み`article_business_purpose`、`article_profile`、成約用では標準3件を起点に作成した`cta_strategy`を付けて`$article-internal-linker`の`plan`を直接実行し、目的と採用先を決める。成約用ではアフィリエイトCTAを主導線、内部リンクを補助導線とする。集客用では、記事管理情報、対応する制作ログ、またはユーザー承認済み一覧により成約用と確認でき、現在実行で公開確認した自サイト記事1件を主導線に固定する。タイトルや記事トピックだけで成約用と推測しない。主リンクは`required: true`、`destination_role: conversion_direct`、`presentation: image_card`とし、画像付きカード機能とリンク先画像を確認する。適切な成約用記事がなければ本文作成前に停止する。

実行状態の記事設計へ次をまとめる。

- 対象キーワード、検索意図、読者、記事の結論、読後行動
- 推奨タイトル、H1、H2、H3
- 各見出しの役割、各H2の`reader_question`と`reader_outcome`、`required_answer_ids`、必須要点、使用可能な根拠、未確認事項
- `content_brief`、`question_coverage`、受理済み`answer_map`（条件と確認状態を含む）
- `article_business_purpose`、主要行動、内部リンク意図、必須・任意の区分、`destination_role`、`presentation`
- `article_profile`、適用時の`review_evidence_plan`と`price_evidence_plan`
- 成約用では`cta_strategy`、子スキルの`affiliate_link_plan`、対象講座、CTA共通部品の確認状態。集客用では`planned_count: 0`、主成約記事の`approved_destination_id`、役割確認根拠、公開・カード機能の確認状態。両方で外部リンク方針
- カテゴリー、タグ、記事ID、日付、サムネイル文言の候補、各H2画像で一目で伝える意味

タイトル、構成、結論、内部リンク意図は一括承認の範囲内で自動確定する。記事の目的が変わる入力不足、既存記事への統合・リライト推奨、正本の競合、成約用で`affiliate_link_plan.status: eligible`を確定できない場合、または集客用で主成約記事カードを確定できない場合は本文作成へ進まず`BLOCKED`にする。

## 4.5 実装計画とTODOの直接実行

開始時に調査・記事設計から最終プレビューまでの計画とTODOを提示し、必要な調査・前工程が受理されるたび具体的な実行条件を確定する。設計未確定の制作TODOを開始しない。計画提示は進行共有であり、既存の一括承認範囲内で個別承認を追加しない。中間ファイルは作らない。

実装計画書には、少なくとも次を含める。

- 目的、対象範囲、対象外、承認済みの固定事項
- 実行時スキーマ、ルールブック、入出力契約、操作境界
- 作成する成果物、予定パス、一括承認の範囲
- 依存関係、必要な正本データ、検証方法、品質ゲート、完了条件
- リスク、停止条件、計画変更時の再検証範囲
- 計画バージョンと、その更新条件
- 各TODO、依存関係、成果物、受入基準、検証方法

TODOは、単独で検証できる一つの成果物または判定を持つ意味のまとまりにする。同じ成果物へ連続して手を入れる作業、片方の結果なしでは検証できない作業、分離すると文脈または責任が失われる作業は、実行前に一つのTODOへまとめる。細分化したTODO数を計画の精密さとして扱わない。

```yaml
todo_id: T-01
instruction_version: 1
purpose: "このTODOで満たす目的"
inputs: []
depends_on: []
allowed_scope: "変更または作業してよい範囲"
expected_output: "成果物または確認結果"
acceptance_criteria: []
verification: []
state: pending # pending | in_progress | revision_requested | accepted | blocked
revision_count: 0
same_root_cause_count: 0
structural_redesign_count: 0
last_root_cause: null
acceptance_evidence: []
plan_version: 1
revalidation_scope: []
blocker_type: null
resume_condition: null
```

本スキルが編集設計、調査、本文、画像、UI化、保存、検証を直接実行する。別実行者への分担やモデル別の分担を使用しない。

TODOは依存関係に従って順に直接実行する。同じ記事ファイル、画像、記事設計データに関わる作業は、前工程の検収後に続ける。

依存スキルの実行前に入出力契約の必要な入力を確定する。必須設計不足は`needs_execution_input`として記録し、推測で制作しない。成果物、使用設計版、差分、検証証跡を照合する。設計不備は設計TODOへ、制作不備は該当TODOへ、観測した問題・根本原因・固定事項・再検証条件を付けて戻す。

見出し構成TODOは二段階で検収する。第1段階では、前回の問題台帳、採用理由、詳細な根拠説明を先に見ず、対象キーワード、主検索意図、ペルソナ、タイトル、H2、H3だけで、主質問への早期回答、各H2の`reader_question`・`reader_outcome`、執筆作業中心でないこと、同型反復と抽象化、読者価値の回帰を確認する。第2段階では完全な調査結果と公式根拠を使い、事実、数字、時点、対象範囲、未確認事項、効果・優位性の根拠を検査する。両方の結果と見出しスキルの`status: PASS`を`acceptance_evidence`へ残し、片方だけでは受け入れない。正確性が改善しても、読者の疑問、読後の到達状態、具体性または次の行動が失われた場合は受け入れない。

修正・再検証は、全必須TODOが`accepted`になるまでPDCAとして継続する。不合格時は`revision_count`を増やし、前回と同じ根本原因なら`same_root_cause_count`を増やす。根本原因が変わった場合は`last_root_cause`を更新し、`same_root_cause_count: 1`、`structural_redesign_count: 0`とする。受入時は`same_root_cause_count: 0`、`structural_redesign_count: 0`、`last_root_cause: null`へ戻す。

同じ根本原因による不合格が2回連続し、`structural_redesign_count: 0`の場合は、表面的な言い換えを止め、計画、TODO境界、入力、許可範囲、受入基準、検証方法、根拠不足のどこに原因があるか再診断する。自律的に解消できる場合は構造的な計画更新を1回だけ行い、`structural_redesign_count: 1`として該当TODOを直接やり直す。その後も同じ根本原因が残る場合は再設計を繰り返さず、該当TODOを`blocked`にして`blocker_type`、根拠、影響、`resume_condition`を示す。

計画バージョンは、前提、依存関係、TODO境界、受入基準または再検証範囲が変わる場合だけ更新し、表現修正だけでは増やさない。テストまたは検収で前提が崩れた場合は、理由、影響、変更TODO、再検証範囲を記録してから再開する。権限、ユーザー判断、正本データ、依存ツールの不足、通知済みの記事ルート外への書込み、既存ファイル変更、公開権限が必要な場合は自動継続しない。ユーザー判断が必要なら`state: blocked`、`blocker_type: needs_user_decision`を使用し、新しい状態名を増やさない。

設計版の更新、旧版成果物、裁量、変更要求は[入出力契約](input-output-contract.md)の直接実行用の記録に従う。設計TODOにも同じ状態・原因管理を適用する。実行者だけで解消できる不足をユーザー判断待ちへ変換しない。

## 5. 本文作成

`$readable-article-style`へ、導入文と各見出し配下を構造化して渡す。

- `mode: new`
- `input_format: markdown`
- 各単位に確定見出し、答える疑問、回答・説明順・必要な比較や具体例、使用根拠・条件・限界、前後のつながり、重複禁止箇所を渡す。説明順は`required_points`、前後関係は`connection`、裁量と禁止は`quality_profile`へ対応づける。
- 親が出典ごとの確認日・対象主張・注記の配置を記事全体で決め、各節には`required_points`で掲載内容、`quality_profile`で調査報告の反復禁止を渡す。`allowed_evidence`の確認日は保持し、子へ担当外の注記移動を求めない。
- 全文を渡す最終検査では`review_scope: article`、`article_complete: true`、`quality_report: summary`とする。親が統合した注記も含め、調査報告の反復と日付・出典の対応を確認する。
- 見出しの追加、削除、変更、並べ替えを許可しない。
- `content_brief`と対応回答を、依存スキルが受け取る`reader_profile`、`scope`、`required_points`、`allowed_evidence`、`quality_profile`へ変換する。条件・確認状態・評価軸を落とさず、未対応の実行状態フィールドをそのまま渡さない。
- [改善前後の参照例](content-quality-examples.md)を読み、重要論点では事実→読者への意味→適用条件・限界を説明する。全段落の書式や順番には固定しない。
- 教材評価では説明・ヒント・添削・質問・復習等の支援を調べてから残る不足を説明する。最初から一人でできるかだけで評価しない。
- 実際の教材例は確認範囲だけ述べ、仮定例を体験・実在問題のように書かない。免責文を段落ごとに繰り返さない。調べられる事実を読者に調べ直させず、個別条件や変動情報で本人の確認が必要な場面を分ける。

全単位が`section_pass`で、全文が`article_pass`の場合だけ採用する。`needs_execution_input`や未達本文を完成原稿へ混ぜない。

本文完成後、本スキルは記事全体を読み、主要な疑問ごとに本文の回答箇所と根拠を対応づけてG3を検収する。`article_pass` や「具体的・読みやすい」という自己評価だけで受け入れない。文字数、出典数、表の数、表示・ビルド成功を内容品質の代替にしない。合格した本文だけをリンク・画像工程へ渡す。

本文受理後に`emphasis_plan`を作る。本文中の各H2・H3について、見出しが答える結論を示す短い単語または句を少なくとも1件、`emphasis_id`、`section_id`、`answer_id`、`exact_text`、`role: conclusion`、`reason`へ対応づける。そのほかに読者の判断を助ける独立した条件・期限・注意・行動がある場合は、検査で許可された`condition`、`deadline`、`caution`、`action`の役割で短い語句を追加できる。強調は単語または短い句を基本とし、実表示で原則1行以内、長くても2行以内に収める。重要な要点が複数ある記事では強調箇所を複数設けて拾いやすくするが、記事・節ごとの件数ノルマは置かず、同じ内容の重複や水増しもしない。長い文や段落をまとめて太字にせず、長くなった語句は伝えたい核だけに短縮する。空の計画、結論語句を持たない見出し、見出し自体、単なる装飾の強調は不合格とする。章IDと各語句をUIと最終検査へ同じ内容で渡す。

### 内容の差し戻し

| 原因 | 担当工程 | 再検証範囲 |
| --- | --- | --- |
| 重要な疑問の見落とし | 調査・記事設計 | 回答一覧、構成、結論 |
| 根拠不足・矛盾 | 調査 | 回答、結論、関連見出し |
| 主質問の取り違え | 記事設計 | タイトルから結論まで |
| 見出しの重複・不足 | 見出し | 関係章と全体の流れ |
| 根拠はあるが説明が浅い | 本文 | 該当節と前後関係 |
| 冗長・単調・読みにくい | 推敲 | 意味を保った全文 |

本文作成中に不足を見つけたら、追加調査を直接実行する。見出し確定を理由に再調査を拒まず、根拠なしに見出しや事実を変更しない。受理後に `answer_map` と完全な上流レポートを更新して検収する。意味・条件が変わった回答IDを使う見出し・本文を `revalidation_scope` に戻し、関連するタイトル、表、画像文言、リンクも再検証する。意味の変わらない補足追加で無関係な工程まで作り直さない。根本原因の連続回数と停止条件は4.5を維持する。

## 6. 内部リンク挿入

確認済み`article_business_purpose`、`article_profile`、`cta_strategy`、確定したリンク意図と`approved_destination_id`、リンク先の`destination_role`と`presentation`、完成Markdown、現在実行で公開確認した候補、目的別の`affiliate_link_plan`、現在確認した`site_rendering_capabilities`を`$article-internal-linker`の`insert`へ渡す。対象章・目的・採用先・表示形式・対象講座を変更せず、許可範囲で段落と誘導文を調整する。

- 成約用ではCTAと必要な内部リンクを含む`pass`だけを受理する。集客用ではアフィリエイトCTAが0件で、主成約記事カードを含む`pass`だけを受理する。
- `blocked`または`blocks_draft: true`なら後工程へ進まない。
- 挿入前本文、`expected_link_manifest`、`affiliate_link_manifest`を分けて保持する。
- `expected_link_manifest.new_links`に確定した各リンクが、UI化後のMarkdownと最終HTMLの両方で同じ`href`と表示形式を保つまで、完成にしない。マニフェストが空の場合に内部リンク件数を作る目的でリンクを追加しない。
- 通常の関連記事は本文中の語句へ設定する`text_link`、口コミ・料金紹介・比較・その他の成約へ直接つながる記事は`image_card`とする。画像付きカードは最大2件とし、件数に応じて表示形式を入れ替えない。
- `image_card`の共通変換機能またはリンク先画像の解決を確認できない場合は、テキストリンクへ変更せず`blocked`とする。

## 6.5 公式・権威メディア画像収集

内部リンク済み本文が受理された後、画像が必要に見えるかどうかにかかわらず毎回`$official-site-evidence-capture`を使う。本文と内部リンクは読み取り専用で渡し、この工程ではMarkdown、画像参照、キャプションを変更しない。

最低限、記事ID、タイトル、メインキーワード、対象読者、記事目的、安定した見出しID、`body_with_internal_links`、提案保存先、現在の画像制約を入力する。次の方針を必須入力とする。

```yaml
evidence_policy:
  required: true
  capture_mode: analyze_final_body # discover用。captureではexplicit_requests
  strategy: screenshot_preferred
  method_priority:
    - element_screenshot
    - pdf_region_capture
    - viewport_screenshot
    - direct_download
  max_claims_per_article: 3
  max_assets_per_claim: 1
  require_attempt_when_visual_claim_exists: true
  no_allowed_asset_action: continue_without_assets
  placement_mode: automatic_when_accepted
```

候補主張は、料金・適用条件など意思決定に直結する事実、手続き、サービス画面・教材、統計・図表、補助的な視覚情報の順で最大3件を選ぶ。1主張につき1画像を原則とする。

依存スキルへはスキーマ1.3、`authorization.mode: orchestrated_prepublication`を渡す。候補探索は`capture_phase: discover`、`capture_mode: analyze_final_body`。取得は`capture_phase: capture`、`capture_mode: explicit_requests`とし、受理した`selected_candidates`の完全レコード、対応する`explicit_requests`、`design_version`を渡す。戦略・方法順・上限・試行条件は`capture_preferences`へ変換する。本スキル固有の`required`・`no_allowed_asset_action`・`placement_mode`は渡さない。

本スキルの実行では`authorization_mode: orchestrated_prepublication`と一括承認参照を渡す。保存先は通知済み記事ルート内の`images\evidence`に固定し、既存ファイル上書きを許可しない。

最初に保存を伴わない候補探索を実行し、`evidence_discovery`を検収して候補ID・主張・必要性・権利・領域・方法・保存先を選定する。次の情報を保持し、未実施の取得結果は補完しない。

- 元ページURL、運営者、情報源区分、適格性の根拠
- 対応見出しと、画像で示す主張
- 利用条件の根拠と、保存・掲載・加工の許可範囲
- 希望取得方法・許可する代替方法。実際の方法・試行結果は取得段階で記録する
- 加工内容、予定ファイル名、絶対保存先

`orchestrated_prepublication`では、権利状態が`allowed`で、ローカル保存・記事掲載が許可され、候補が通知済み保存先内に収まる場合だけ取得・保存・検査する。加工する場合は`modification_allowed: true`も必要とする。`unclear`または`prohibited`はスクリーンショットを含めて取得・保存せず、公式ページへのリンク候補だけを保持する。URL、画像数、保存先、加工内容が承認範囲外へ変わる場合は保存せず`BLOCKED`にする。単独利用時は子スキルの候補別承認を維持する。

HTMLページのスクリーンショットでは、利用可能な`control-in-app-browser`を使い、対象要素を最優先する。要素取得が意味上適用できない場合だけPDF範囲、必要最小限の表示領域、直接取得の順へ進む。表示領域全体はページ文脈自体が根拠になる場合だけ使う。同じURLの取得失敗は最大2回までとし、各試行を1.3の`capture_attempts`へ残す。スクリーンショットが適切な候補で必須試行が失敗した場合は、直接取得へ切り替えて成功状態にしない。

依存スキルの`evidence_capture`出力を変更せず保持する。視覚化すべき主張がなければ`NOT_APPLICABLE`、権利条件を満たす候補がなければ`READY_WITHOUT_ASSETS`、一部取得なら`PARTIAL`、1件以上の保存・検査完了なら`READY`として次工程へ進める。単独利用では`SKIPPED_BY_USER`も受理できる。権利条件を満たす候補があるのに取得機能が使えない、または2回失敗した場合を`READY_WITHOUT_ASSETS`へ変換せず`BLOCKED`とする。適格な画像がないことだけで本文を不合格にしない。

旧1.1・1.2も読めるが、新規2.7では1.3を使う。`CANDIDATES_READY`だけではG4.5を通さない。候補がある場合は選定と取得結果を対応づける。候補なし・視覚化不要なら実際の探索記録を確認して`evidence_result`で無画像を受理する。空の取得要求で候補ありや取得失敗を隠さない。

次工程が画像を使う場合は、スキーマ、ファイル存在、SHA-256、`article_publication_allowed`、帰属表示、加工可否、対応見出しと主張を再検証する。引継ぎデータを失った画像をファイル名だけで採用しない。この工程自体は画像を記事へ配置しない。

`$study-article-ui-coder`を直接実行して配置する。`article_publication_allowed: true`、ハッシュ一致、帰属表示、加工可否、見出し・主張一致、alt、モバイル可読性、現行Astro Markdownとの整合を満たす画像だけを自動配置する。条件を満たさない画像は削除せず`保存済み・未配置`として理由を最終報告へ残す。frontmatter付与とMarkdown保存、隔離プレビューの実表示確認も本スキルが直接実行し、差分と検証証跡を確認する。

## 7. アフィリエイトと外部リンクの判定

親スキルはURLを複製せず、`$article-internal-linker`の`affiliate_link_plan`と`affiliate_link_manifest`を正本として保持する。

```yaml
affiliate:
  required: true | false
  disposition: eligible | not_applicable | blocked
  provider: shinken_zemi | smile_zemi | null
  target_course: preschool | elementary | junior_high | high | null
  affiliate_link_plan: null
  affiliate_link_manifest: null
  component_check: pending
  insert_status: pending
  audit_status: pending
  reason_code: null
cta_strategy:
  default_count: 3
  planned_count: 3
  count_mode: standard
  count_reason: "独立した公式確認場面に基づく理由"
  explicit_user_count_override: null
  official_confirmation_moments: []
```

- 成約用では`required: true`とする。CTAは3件を標準値として検討するが固定せず、検索意図、文章量、判断段階、独立した公式確認理由の数から1件以上へ増減する。`planned_count`と`official_confirmation_moments`へ採用数と全配置を記録し、各配置に異なる`reader_question`、`official_information_needed`、`destination_purpose`、`lead_copy`を持たせる。
- 口コミ・料金記事では教材内容・良い口コミ、料金・支払・端末条件、悪い口コミ・注意点・向き不向きの説明後が候補になる。お試し・キャンペーン記事では、試せる内容、対象・期間、費用・返却・継続条件の説明後が候補になる。いずれも固定見出しではなく、本文を読んで公式情報を確認したくなる実際の場面だけを採用する。
- 1〜2件へ減らす場合、4件以上へ増やす場合は`count_reason`を具体的に記録する。文章量だけ、見出し数だけ、過去記事の件数だけを理由に増やさない。5件以上は確認目的の独立性を全配置で説明する。
- 成約用で対象講座が一意でない、承認済みアフィリエイト契約がない、自然な公式確認場面が1件もない、講座・URL・共通部品・計画件数が一致しない、または挿入・監査が不合格の場合は`blocked`とする。記事範囲をCTAのために変更せず、CTAなしの完成状態へ変換しない。
- 集客用では`required: false`、`disposition: not_applicable`、`affiliate_link_manifest.links: []`とする。本文・最終HTML・期待マニフェストにアフィリエイトCTA、計測画像、ASP URLが1件でもあれば不合格にする。主導線は公開確認済み成約用記事の画像付き内部リンクカードとする。

本文のリンクは [本文リンク制限と検査](article-link-policy.md) に従い、`internal`、`affiliate_cta`、ユーザーが記事別に明示許可した例外、禁止リンクへ分類する。根拠URLは`answer_map`と出典記録へ保持し、口コミ・論文出典は必要なら資料名をプレーンテキストで示す。手続き・交換・ログイン等の必要性をAIが判断しただけでは外部URLを掲載しない。例外配列`allowed_external_links`は通常空とし、実際のユーザー許可原文・発言出典・対象URLがある場合だけ記録する。

## 8. `study-article-ui-coder`によるAstro Markdown化

完成本文、確認済みリンク、採用可能な`evidence_capture.assets`、対応する`capture_attempts`、配置に必要な見出し・主張・帰属表示、キーワード、学年、記事目的、確定した検索者・利用者・評価軸、適用条件付きの禁止表現、`emphasis_plan`、CTA保持条件、現行ルールブックを`$study-article-ui-coder`へ渡す。`design_mode`は依存スキルの標準である`autonomous`を使用する。

```yaml
design_mode: autonomous
output_target: astro-markdown
editing_mode: structure-light-edit
publication_state: draft
required_elements:
  - type: emphasis_plan
    items: [] # 確定したemphasis_plan.itemsを代入。空のまま渡さない
preserve_elements:
  - section: "承認済みCTA配置章ごとの全配置"
    element: "shinken_zemi_cta_v1"
    preserve: "placement_id、固定DOM、講座、href、計測画像src、rel、固有の表示文、配置、計画件数"
  - section: "承認済み内部リンク配置章"
    element: "internal_link_presentation"
    preserve: "destination_role、presentation、href、アンカーまたは紹介文、配置"
```

出典注記の対象情報・出典・確認日・配置を`preserve_elements`に追加する。

`coded_content`、`component_map`、`validation_report`、`unresolved_items`、`change_summary`を一組で受け取る。`validation_report.emphasis`の全項目を元の計画と照合し、マークアップと実表示の合格を分ける。未表示を`pass`にしない。`unsupported_component`の場合は、既存ルールブックにある単純なMarkdown・固定部品で意味を保つよう再設計してから直接再変換する。共通CSSや未定義classが必要なら`design_migration_required`として停止する。

受理した`coded_content`へ、実行時の`src\content.config.ts`で許可されているフィールドだけを持つfrontmatterを付けて保存する。現在の既定形は次とする。

```md
---
title: "記事タイトル"
date: 2026-08-23
categories:
  - "カテゴリー"
tags:
  - "タグ"
coverImage: "images/eyecatch.webp"
draft: true
---
```

- 本文は導入文の後にH2から始める。
- H1、ページ全体のHTML、共通ヘッダー、目次、関連記事、CSS、JavaScriptを入れない。
- ルールブックで許可されたMarkdownと固定装飾部品だけを使用し、記事固有CSSを作らない。
- メタディスクリプション案は作るが、スキーマが対応していない場合はfrontmatterへ追加せず最終レポートに分ける。
- 仮URL、`TODO`、`example.com`、画像IDなどのプレースホルダーを残さない。
- 根拠画像を配置する場合はalt、必要な帰属表示、記事相対パスを付け、対応見出しの主張を画像だけに依存させない。配置を見送った保存画像は本文へ参照を残さず、`保存済み・未配置`として追跡する。

## 9. 記事ファイルの作成

実行開始時に通知した記事ID、`index.md`、画像フォルダ、作成理由と一致する場合だけ次へ作成する。

```text
C:\AIフォルダ\ブログ\site\src\content\blog\<article-id>\index.md
C:\AIフォルダ\ブログ\site\src\content\blog\<article-id>\images\<approved-thumbnail-name>.webp
C:\AIフォルダ\ブログ\site\src\content\blog\<article-id>\images\h2-<section-image-name>.webp
```

根拠画像は6.5で権利・保存範囲が合格した場合だけ、同じ記事フォルダの`images\evidence\`へ保存できる。既存の同名記事・画像を上書きしない。競合時は自動改名や上書きをせず`BLOCKED`にする。

## 10. サムネイルと各H2見出し画像

`$education-blog-thumbnail-creator`の`execution_mode: full`、`asset_scope: thumbnail_and_h2`を直接実行する。完成本文からサムネイルを設計・生成・検品し、その画風が確定した後に全Markdown H2の見出し画像を設計・生成・検品・限定挿入する。サムネイルではキャラクター正本、スタイル文法、承認見本、比較画像を確認し、H2画像では依存スキルの文章スタイル契約と参照分離規則を守る。

```yaml
article_title: ""
article_path: ""
target_grade: elementary | junior_high | high_school | multi_grade | unknown
target_reader: ""
article_type: recommendation | review | pricing | how_to | trouble | study_method | experience | campaign | other
reader_problem: ""
article_conclusion: ""
desired_action: ""
thumbnail_copy: [] # 未指定なら画像スキルがタイトル文字を設計する
textless_exception: null # ユーザー指示原文と対象asset_idがある場合だけ
character_mode: person | personless | undecided
visual_motif: ""
layout_archetype: ""
primary_prop: ""
focus_position: left | center | right
execution_mode: full
asset_scope: thumbnail_and_h2
authorization_mode: orchestrated_prepublication
parent_run_id: ""
allowed_output_directory: "<article-root>\\images"
article_edit_authorized: true
```

一括承認参照、保存済みの完成記事パス、通知済み記事ルート内の未使用の保存先、この新規記事に対するH2画像参照の限定編集権限を渡す。権限は承認済み画像の直下挿入・差し替え・一意に対応する参照移動だけに限定し、本文、見出し、frontmatter、CSSの変更へ拡張しない。生成・編集のたびに、生成前レビュー、参照状態、最終プロンプト、生成後の実画像検品を確認する。`$imagegen`を直接呼ばない。

コピー未確定も途中状態とする。子の`exact_copy`と最終プロンプト・実画像・保存画像を照合し、通常の空コピー、親の独自判断による文字なし指定、後から重ね文字を加える未確認の前提を受理しない。

生成前レビュー未完了は途中状態で、画像完成ではない。サムネイルの参照状態、最終プロンプト、生成後の`image_only_readback`と実表示を保持する。各H2画像では見出し、`one_glance_meaning`、構図、固定文字、スタイル契約の版・SHA-256、実画像検品を保持する。設計変更が必要なら該当画像TODOを直接やり直す。保存は既存の一括承認範囲・新規パス・生成後品質合格を条件とする。

H2画像は全対象を生成・目視してから未使用名へ保存し、保存後の全件再検査が合格した場合だけH2直下の画像参照を1回の編集で反映する。1枚でも`BLOCKED`なら部分挿入せず、保存途中で失敗した場合も記事を変更しない。作成済みの未参照ファイルは報告し、無断で削除しない。

画像設計後にH2の文言または意味が変わった場合は該当画像の承認と検査を無効化する。H2の追加・削除で件数が変わった場合は、全H2画像の対応関係と構造検査をやり直す。タイトルまたは記事の中心的な約束が変わった場合はサムネイルも再検証する。

`thumbnail.status`と`section_images.status`がともに`FINAL_ASSET_READY`になった場合だけG7を合格にする。新規記事のfrontmatterへサムネイルの最終画像を`coverImage`として設定し、H2画像については全H2直下の参照、実在ファイル、alt、形式、寸法、容量、実表示を確認する。どちらかが`PREVIEW_READY`、`BLOCKED`または未検証なら記事を完成扱いにしないが、本文が安全に完成していれば未完了状態を表示した記事プレビューは開ける。

## 11. 検証

1. `$education-blog-thumbnail-creator`の`scripts/check-h2-images.ps1`へ正本記事パスを渡し、全H2画像の構造・実在・形式検査を行う。
2. ビルド前は`basic`または共通`audit-article-links.mjs`で原稿の事前検査を行う。手順6の最終ビルド後、`scripts/validate-cloudflare-article.ps1`へ`-ValidationMode parent`、`-RenderedHtmlPath`、`-ExpectedArticleBusinessPurpose conversion|traffic`、`-ArticlePath`、`-ProjectRoot`、`-ExpectedTitle`、`-ExpectedArticleProfileJson`、`-ExpectedCtaStrategyJson`、適用時の`-ExpectedReviewEvidencePlanJson`と`-ExpectedPriceEvidencePlanJson`、目的別`-ExpectedAffiliateDisposition`、`-ExpectedEmphasisPlanJson`、`-ExpectedInternalLinkManifestJson`、`-ExpectedAffiliateLinkManifestJson`、`-ExternalLinkPolicy allow_task_required_only`を渡す。例外は通常空とし、明示許可がある場合だけ`-AllowedExternalApprovalJson`へ原文・出典付きで渡す。成約用の単独CTAでは`-ExpectedAffiliateProvider`と`-ExpectedAffiliateCourse`も渡す。JSONは同じPowerShell内の変数で渡し、コマンド文字列へ直接埋め込んだり中間ファイルを作成したりしない。原稿・最終HTMLの両方が合格するまで完成にしない。
3. `npm run build`を実行し、既存ビルドを壊していないことを確認する。この通常ビルドの正規プロジェクト側`dist`は再生成可能だが、隔離プレビューの一時成果物には混ぜない。
4. `scripts/prepare-local-preview.ps1`へプロジェクトルート、記事ID、`run-id`を渡し、既定の`%TEMP%\\codex-article-work\\<run-id>--<article-id>\\`へ許可リスト方式の隔離コピーを作る。`-PreviewRoot`を指定する場合も、この一時ルート配下の未使用実行フォルダに限定する。正本の`draft: true`を変更しない。
5. 隔離コピー内の記事だけを`draft: false`にし、元プロジェクトの`node_modules`を一時ジャンクションから再利用する。Astro・Viteのキャッシュとビルド出力は隔離コピー内に置き、依存関係を再インストールしない。`CLEANUP-INFO.txt`の削除条件を確認し、`C:\\AIフォルダ\\previews`、正規プロジェクトの`.tmp`、`artifacts`には一時成果物を作らない。
6. 隔離コピーをビルドし、手順2で用意した親完成検査へ最終記事HTMLを渡す。原稿とHTMLのリンク検査合格後、`127.0.0.1`の空きポートで配信し、利用可能な`control-in-app-browser`で記事URLを開く。URL提示だけを表示済みにしない。
7. 320px、375px、390px、768px、1280pxで、表以外の横はみ出し、画像、見出しID、アンカー、コンソールエラーを実査する。保存する検証画像・ログは、隔離コピー内の`verification`配下へ置く。強調計画の全語句が指定章の表示本文で太字になり通常文字と見分けられること、Markdown記法が露出していないことを確認する。各強調箇所の実際の折返しも確認し、原則1行、最大2行に収める。3行以上になる場合は短い単語・句へ直して再検証する。各H2画像では画像全体、文字、数字、矢印、主役、縦横比、不要な枠を記事本文幅で確認する。
8. レンダリング済みHTMLを`$article-internal-linker`の`audit`へ事業目的、`cta_strategy`、`expected_link_manifest`、`affiliate_link_manifest`、5画面幅の表示記録とともに渡す。成約用は計画件数どおりのCTA、集客用は主成約記事カードとアフィリエイト0件を、内部リンクの表示形式・画像読込み・URL・属性・重複・表示とともに子スキルの正本契約で監査する。
9. 統合検査TODOを除く全必須TODOが一度`accepted`になった後、タイトル、導入、見出し、本文、結論、事実と出典、内部リンク、公式画像、サムネイルの表示文字、各H2画像の意味と配置、装飾の役割、スマートフォン表示を一つの記事として横断検査する。不合格なら原因となったTODOを`revision_requested`へ戻し、その成果物に依存するTODOを`revalidation_scope`へ追加する。必要な範囲の再検証と統合検査の再実行が終わるまで完成状態を返さない。
10. 正本SHA-256を最終取得して静的検査結果と照合する。隔離コピーの`source_article_sha256`が同じ正本を指し、コピーのfrontmatterの`draft`以外が正本と一致することを確認する。記事・コピー・画像に変更があれば影響する検査を無効化して再確認する。統合検査が合格したら、最終操作として完成版の記事URLをユーザーが見えるアプリ内ブラウザへ開くか、既存タブをそのURLへ移動する。表示後に現在URLと記事画面を確認し、`preview.presented_to_user: true`、`preview.presentation_stage: after_final_audit`を記録する。URLの報告、スクリーンショット、検査中に開いた履歴だけで代替しない。
11. 利用可能な表示手段がない、最終URLへ移動できない、または記事画面を確認できない場合は`preview.status: display_blocked`、`preview.presented_to_user: false`とし、完成状態を返さない。
12. 実際に到達した状態で`$article-production-log`の`finish-log`へ目的別導線の`funnel_alignment`と検証根拠を記録し、`verify-store`を行う。表示できない場合は`preview_ready`や`verified`へ誇張せず、観測事実と未解決事項を残す。

## 12. 最終報告

統合検査後の完成版プレビューをユーザーへ表示でき、成約用はアフィリエイトCTA、集客用は主成約記事カードとアフィリエイト0件の挿入・監査、およびすべての品質ゲートが合格した場合に、状態表に従って最終結果を返す。最終報告はプレビュー表示の後に行う。

- 記事ファイル、サムネイル、全H2見出し画像の絶対パス
- キーワード、確認済み事業目的、主要行動、タイトル、カテゴリー、記事ID
- リサーチ、見出し、本文、内部リンク、静的検査、ビルドの各状態
- 内部リンク一覧
- 根拠画像収集の状態、スクリーンショット試行一覧、希望方法と実際の方法、保存画像一覧、出典、権利、モバイル確認、未取得理由、保存済み・未配置の画像と理由
- 使用した装飾部品とサムネイル参照画像
- 画像スキルの`thumbnail`と`section_images`の状態、H2件数、生成・保存・挿入件数、各画像の最終プロンプトと検査結果、実際に確認した画面幅
- メタディスクリプション案
- 成約用では`article_profile`、口コミ・料金証拠計画の適用結果、`cta_strategy`の標準数・採用数・増減理由・公式確認場面、対象講座、CTA件数、共通部品確認、挿入・最終監査。集客用では主成約記事、役割確認根拠、カード監査、アフィリエイト0件。両方で許可外部リンクと理由
- 未実施の画面確認や人間確認
- プレビューURL、表示状態、確認幅、`presented_to_user: true`、表示時点が統合検査後であること、正本が`draft: true`のままであること
- 本番公開、commit、push、デプロイを行っていないこと
- 品質ログの`log_id`、詳細Markdownの絶対パス、`verify-store`の結果。ログ未完了なら未記録範囲と再実行条件

この新記事を後で公開する場合のGitHub保存について、保存理由、リポジトリ、remote、非`main`のpush先、対象記事ID、対象`index.md`の絶対パスを示す。既存運用で別の指定がなければpush先は`publish/<article-id>`とし、公開指示後に最新のリモート`main`から作成する。push先を一意に確定できなければ未確定と明記し、推測しない。ここではGit操作を実行せず、この通知後に同じ記事を指す「公開して」という指示が届いた場合だけ13へ進む。

## 13. 明示的な公開指示後のGitHub保存

この工程は通常の新記事作成とは別の後続工程である。次をすべて満たす場合だけ実行する。

1. 対象記事が本スキルで`READY_FOR_HUMAN_REVIEW`まで到達し、統合検査後の最終プレビューをユーザーへ表示済みである。
2. 12の最終報告後に、ユーザーが同じ記事を一意に指して明示的に「公開して」と指示した。
3. 指示前に、保存理由、対象リポジトリ、remote、非`main`のpush先、記事ID、`index.md`の絶対パスを通知済みである。
4. 現在の正本`index.md`が、ユーザーへ表示した最終版と同じである。変更されていれば影響する検査と人間確認へ戻る。

実行手順:

1. `C:\AIフォルダ\ブログ\site`が対象Gitリポジトリで、通知済みremoteとpush先が現在の設定に一致することを読み取り確認する。push先が`main`、未確定、または別リポジトリを指す場合は停止する。
2. `git status --short`とステージ済み差分を確認する。ユーザーのdirty worktree、既存ステージ、別記事の変更を取り込まない。リモートを更新確認し、最新のリモート`main`から隔離した作業場所と通知済みの非`main`ブランチを作る。既存の同名リモートブランチがある場合は、最新のリモート`main`を基点とし、対象`index.md`以外の未マージ差分を含まない場合だけ再利用する。条件を満たさなければ上書き、force push、別名への自動変更をせず停止する。元の作業ツリーをcheckout、reset、stash、cleanしない。
3. 同じ制作実行で確定した`src/content/blog/<article-id>/index.md`だけを隔離側の同一パスへ反映する。GitHub保存のために本文、frontmatter、`draft`、リンク、画像参照を変更しない。
4. `git add -- src/content/blog/<article-id>/index.md`のように対象パスを明示してステージする。`git add .`、記事フォルダ全体、画像ディレクトリ、globを使わない。
5. `git diff --cached --name-only`の結果が対象`index.md`の1件だけで、追加・更新の内容がユーザー確認済み最終版と一致し、`git diff --cached --check`が合格することを確認する。別パス、rename、削除、想定外差分があればcommitしない。
6. 対象記事を識別できるメッセージでcommitし、通知済みの非`main`ブランチへforceなしでpushする。PR作成・マージ、`main`への直接pushは行わない。
7. リモート上の対象ブランチがpushしたcommitを指すことを確認する。ローカルcommitだけ、push失敗、認証失敗、リモート不一致ではGitHub保存済みとしない。
8. 対象`index.md`、commit SHA、push先、リモート確認結果、除外した範囲、Cloudflare公開を実施していないことを報告する。

対象記事またはpush先が曖昧、最終確認後に正本が変化、既存push先に対象外の未マージ差分がある、リモート基点との競合、対象外パスの混入、認証・push・リモート確認の失敗、または`index.md`だけではGitHub側の必須検証を通せない場合は停止する。画像や共通ファイルを自動追加せず、観測した問題と再開条件を報告する。この工程はCloudflareへのデプロイや本番公開を実行しない。
