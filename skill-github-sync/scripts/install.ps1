param(
    [string]$SkillPath = 'C:\AIフォルダ\skill\skill-github-sync',
    [string]$StatePath = 'C:\AIフォルダ\.skill-github-sync-state',
    [string]$UserCodexPath = 'C:\Users\yuyy2\.codex',
    [string]$UserAgentsSkills = 'C:\Users\yuyy2\.agents\skills'
)
$ErrorActionPreference = 'Stop'
$SkillPath = (Resolve-Path -LiteralPath $SkillPath).Path
$PythonPath = (Get-Command python.exe).Source
$ScriptPath = Join-Path $SkillPath 'scripts\skill_github_sync.py'
if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) { throw '同期スクリプトがありません' }
$BackupPath = Join-Path $StatePath 'installation-backup'
New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
$Utf8 = [System.Text.UTF8Encoding]::new($false)
$InstructionsPath = Join-Path $UserCodexPath 'AGENTS.md'
$OriginalInstructions = [System.IO.File]::ReadAllText($InstructionsPath)
$SavedInstructions = Join-Path $BackupPath 'AGENTS.before.md'
if (-not (Test-Path -LiteralPath $SavedInstructions)) {
    [System.IO.File]::WriteAllText($SavedInstructions, $OriginalInstructions, $Utf8)
}
$StartMarker = '<!-- skill-github-sync:start -->'
$EndMarker = '<!-- skill-github-sync:end -->'
$Rules = @'
<!-- skill-github-sync:start -->
## CodexスキルのGitHub保存

ユーザーに依頼されたスキルの新規作成・修正は、完成と検証の後に既存GitHub（yuyy5167-sys/skill、main）へ自動保存する共通運用を承認済み。通常の保存で毎回の投稿確認を求めない。アプリの権限制約・認証は通常どおり適用する。

- 編集前に `skill-github-sync` を読み、対象と変更前の状態をbeginで登録する。完成後は必要な検証を行ってready、送信可否のturn-policy、sync、結果確認・報告、ackまで行う。
- フックの追加コンテキストにあるsession・turnを使う。フックが使えない時も明示的な同期経路を省かず、補助が未有効であることを報告する。
- 「ローカルだけ」「GitHubへ送らない」はその依頼の指示を優先し、denyとLOCAL_ONLYを永続的に記録する。そのターンでは過去の待機処理も送らない。後日、送信禁止の内容を別の修正へ無断で混ぜない。
- 未完成・検証失敗・所属不明の変更、記事、認証情報、ログ、一時ファイルは送らない。スキル外の依存は範囲を明記して登録したものだけ扱う。
- GitHubの確認が終わったものだけを反映済みと報告する。失敗は完成版と未反映状態を保持し、次の許可されたスキル同期または再試行の依頼時に再開する。通常の相談だけのターンで待機列を送らない。
- 同じパスのGitHub側の別更新を自動で消さず、強制pushや既存履歴の書き換えを使わない。取消し・削除はユーザーの依頼範囲に従う。

実体: `C:\AIフォルダ\skill\skill-github-sync`。スクリプト: `scripts/skill_github_sync.py`。状態: `C:\AIフォルダ\.skill-github-sync-state`。
<!-- skill-github-sync:end -->
'@
if ($OriginalInstructions.Contains($StartMarker)) {
    $First = $OriginalInstructions.IndexOf($StartMarker)
    $Last = $OriginalInstructions.IndexOf($EndMarker, $First)
    if ($Last -lt 0) { throw '共通指示の終端マーカーがありません' }
    $Last += $EndMarker.Length
    $UpdatedInstructions = $OriginalInstructions.Substring(0, $First) + $Rules + $OriginalInstructions.Substring($Last)
} else {
    $UpdatedInstructions = $OriginalInstructions.TrimEnd() + "`r`n`r`n" + $Rules + "`r`n"
}
$HooksPath = Join-Path $UserCodexPath 'hooks.json'
if (Test-Path -LiteralPath $HooksPath) {
    $OriginalHooks = [System.IO.File]::ReadAllText($HooksPath)
    $SavedHooks = Join-Path $BackupPath 'hooks.before.json'
    if (-not (Test-Path -LiteralPath $SavedHooks)) {
        [System.IO.File]::WriteAllText($SavedHooks, $OriginalHooks, $Utf8)
    }
    $Hooks = $OriginalHooks | ConvertFrom-Json
} else {
    $Hooks = [pscustomobject]@{description='スキルの完成版をGitHubへ保存するためのローカル確認。';hooks=[pscustomobject]@{}}
}
if (-not $Hooks.PSObject.Properties['hooks']) { $Hooks | Add-Member -NotePropertyName 'hooks' -NotePropertyValue ([pscustomobject]@{}) }
$CommandText = '"' + $PythonPath + '" -X utf8 "' + $ScriptPath + '" --state "' + $StatePath + '" hook'
foreach ($EventName in @('UserPromptSubmit','Stop')) {
    $Groups = @()
    if ($Hooks.hooks.PSObject.Properties[$EventName]) { $Groups = @($Hooks.hooks.$EventName) }
    $AlreadyInstalled = $false
    foreach ($Group in $Groups) {
        foreach ($Handler in @($Group.hooks)) {
            if ($Handler.command -eq $CommandText) { $AlreadyInstalled = $true }
        }
    }
    if (-not $AlreadyInstalled) {
        $Handler = [pscustomobject]@{type='command';command=$CommandText;commandWindows=$CommandText;timeout=10;statusMessage='スキル同期の完了状態を確認しています'}
        $Groups += [pscustomobject]@{hooks=@($Handler)}
        if ($Hooks.hooks.PSObject.Properties[$EventName]) { $Hooks.hooks.$EventName = $Groups }
        else { $Hooks.hooks | Add-Member -NotePropertyName $EventName -NotePropertyValue $Groups }
    }
}
# Validate the exact JSON before changing the active file.
$HooksJson = $Hooks | ConvertTo-Json -Depth 30
$HooksJson | ConvertFrom-Json | Out-Null
$Links = @((Join-Path $UserCodexPath 'skills\skill-github-sync'),(Join-Path $UserAgentsSkills 'skill-github-sync'))
foreach ($LinkPath in $Links) {
    if (Test-Path -LiteralPath $LinkPath) {
        $Existing = Get-Item -Force -LiteralPath $LinkPath
        if ($Existing.LinkType -ne 'Junction' -or @($Existing.Target)[0] -ne $SkillPath) { throw "スキルの入口が別の内容と衝突しています: $LinkPath" }
    } else {
        New-Item -ItemType Junction -Path $LinkPath -Target $SkillPath | Out-Null
    }
}
[System.IO.File]::WriteAllText($InstructionsPath, $UpdatedInstructions, $Utf8)
[System.IO.File]::WriteAllText($HooksPath, $HooksJson + "`r`n", $Utf8)
$Record = [pscustomobject]@{installed_at=[DateTimeOffset]::UtcNow.ToString('o');skill=$SkillPath;instructions=$InstructionsPath;hooks=$HooksPath;links=$Links;hook_command=$CommandText;trust='信頼登録と実行確認は別途必要'}
[System.IO.File]::WriteAllText((Join-Path $StatePath 'installation.json'), ($Record | ConvertTo-Json -Depth 10), $Utf8)
$Record | ConvertTo-Json -Depth 10
