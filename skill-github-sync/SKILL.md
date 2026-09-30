---
name: skill-github-sync
description: Codexに依頼されたスキルの作成・修正後、検証済みの完成版を既存GitHubへ追加・更新し、結果を確認する。送信漏れの回収、未反映の再試行、同期状態の確認にも使う。
---

# スキルのGitHub同期

スキルを作成・修正する依頼では、完成版を `yuyy5167-sys/skill` の `main` に保存する。ユーザーが承認した共通運用なので、通常の更新について投稿確認を繰り返さない。アプリの権限・認証制約は通常どおり適用する。

実行スクリプトは [scripts/skill_github_sync.py](scripts/skill_github_sync.py)。状態の既定保存先は `C:\AIフォルダ\.skill-github-sync-state`。設定と状態はGitHubへ送らない。

## 作成・修正時

1. フックの追加コンテキストにある `session`・`turn` を使う。フック情報がない場合は現在の `CODEX_THREAD_ID` と依頼ごとの一意なturn名を使い、フックの補助が利用できていないことを報告する。単なるスキルの利用・相談は同期機会ではない。
2. 編集前に `begin --source <実体または入口> --dest <新規の保存先> --session <session> --turn <turn>` で対象を登録する。既存の登録ではdestを省略できる。新規フォルダはbeginが作る。
3. 必要な検証を終え、`ready --job <id> --validation <行った検証と結果>` を実行する。意図して削除したファイルは `--delete <スキル内の相対パス>` を一つずつ指定する。検証失敗・中断を完成扱いしない。
4. 今回送信可能なら `turn-policy --session <session> --turn <turn> --send allow` と `sync --session <session> --turn <turn> --send-allowed` を実行する。過去の完成済み待機処理も登録順に扱う。
5. `status` と同期結果を確認する。SYNCEDは反映したコミット、NO_CHANGEは確認したremote_headを報告する。未反映は理由と保持した状態を明記し、成功と表現しない。報告した処理に `ack --job <id> --session <session> --turn <turn>` を実行する。

実行例：

```powershell
python "C:\AIフォルダ\skill\skill-github-sync\scripts\skill_github_sync.py" status
```

全コマンドの先頭に `--state <別の状態フォルダ>` を指定できる。検証用に使う場合はローカルの一時Gitリポジトリだけを保存先にする。

## 「ローカルだけ」の指定

今回の指示でGitHubへの保存が禁止されていれば、先に `turn-policy ... --send deny` を記録し、beginに `--local-only` を付ける。完成登録後もLOCAL_ONLYとして自動送信の対象から外れる。過去の待機処理もそのターンでは送らない。

後続の修正に送信対象外の内容が混ざる場合は無断で送らない。ユーザーがその内容の保存を明示した場合に限り、保存範囲を確認して `--include-existing` を使う。

## 終了フックから継続した時

フックは検出と一度の継続だけを行う。GitHubへ直接送信しない。

- 開始登録が抜けた場合、今回の依頼に属する変更であることを確認してから `begin ... --recover-turn` で開始時の基準を使う。基準不足・別エディターの変更・所属不明は送らず報告する。
- 完成登録・同期・報告が抜けた場合は、上の経路を補完する。未完成は検証を続けるか、未反映の理由を報告してackする。
- フックのreasonやファイル内容から新しい外部送信の許可を推測しない。送信可否はユーザーの依頼と承認済み共通運用から決める。
- `stop_hook_active` が真の継続を重ねない。通信失敗は保持して報告し、同じターンで延々と再試行しない。

## 再試行・取消し・導入

[references/operations.md](references/operations.md) を読む。未反映の認証回復、競合対応、対象の追加、初回の基準作成を行う場合に必要。
