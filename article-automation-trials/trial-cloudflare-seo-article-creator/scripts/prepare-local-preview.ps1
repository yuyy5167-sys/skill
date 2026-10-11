#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,119}$')]
    [string]$ArticleId,

    [ValidatePattern('^[a-zA-Z0-9-]{1,80}$')]
    [string]$RunId = ([guid]::NewGuid().ToString('N')),

    [string]$PreviewRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-NormalizedDirectoryPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    return $fullPath.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
}

function Assert-PathWithin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate,

        [Parameter(Mandatory = $true)]
        [string]$Parent,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $candidateFull = Get-NormalizedDirectoryPath -Path $Candidate
    $parentFull = Get-NormalizedDirectoryPath -Path $Parent
    $parentPrefix = $parentFull + [System.IO.Path]::DirectorySeparatorChar

    if (-not $candidateFull.StartsWith($parentPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label が許可された範囲外です: $candidateFull"
    }
}

$projectResolved = Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop
$projectFull = Get-NormalizedDirectoryPath -Path $projectResolved.Path

$sourceArticleRoot = Join-Path $projectFull "src\content\blog\$ArticleId"
$sourceArticleFile = Join-Path $sourceArticleRoot 'index.md'
$sourceNodeModules = Join-Path $projectFull 'node_modules'
$sourceAstroConfig = Join-Path $projectFull 'astro.config.mjs'

Assert-PathWithin -Candidate $sourceArticleRoot -Parent (Join-Path $projectFull 'src\content\blog') -Label '記事パス'

if (-not (Test-Path -LiteralPath $sourceArticleFile -PathType Leaf)) {
    throw "記事ファイルが見つかりません: $sourceArticleFile"
}
if (-not (Test-Path -LiteralPath $sourceNodeModules -PathType Container)) {
    throw "node_modules が見つかりません。依存関係を自動インストールせず停止します: $sourceNodeModules"
}
if (-not (Test-Path -LiteralPath $sourceAstroConfig -PathType Leaf)) {
    throw "Astro設定が見つかりません: $sourceAstroConfig"
}

$utf8Encoding = [System.Text.UTF8Encoding]::new($false, $true)
$sourceText = [System.IO.File]::ReadAllText($sourceArticleFile, $utf8Encoding)
$sourceArticleHash = (Get-FileHash -LiteralPath $sourceArticleFile -Algorithm SHA256).Hash
$frontmatterMatch = [regex]::Match($sourceText, '(?s)\A---\s*\r?\n(?<frontmatter>.*?)\r?\n---')
if (-not $frontmatterMatch.Success) {
    throw '記事のfrontmatterを確認できません。'
}
if ($frontmatterMatch.Groups['frontmatter'].Value -notmatch '(?m)^draft:\s*true\s*$') {
    throw '正本記事が draft: true ではありません。正本を変更せず停止します。'
}

$tempBase = Get-NormalizedDirectoryPath -Path ([System.IO.Path]::GetTempPath())
$temporaryWorkRoot = Join-Path $tempBase 'codex-article-work'
[void](New-Item -ItemType Directory -Path $temporaryWorkRoot -Force)
if ([string]::IsNullOrWhiteSpace($PreviewRoot)) {
    $previewFull = Join-Path $temporaryWorkRoot ("{0}--{1}" -f $RunId, $ArticleId)
}
else {
    $previewFull = Get-NormalizedDirectoryPath -Path $PreviewRoot
}

Assert-PathWithin -Candidate $previewFull -Parent $temporaryWorkRoot -Label 'プレビュー出力先'
if (Test-Path -LiteralPath $previewFull) {
    throw "プレビュー出力先が既に存在します。上書きしません: $previewFull"
}

[void](New-Item -ItemType Directory -Path $previewFull)
$verificationDirectory = Join-Path $previewFull 'verification'
[void](New-Item -ItemType Directory -Path $verificationDirectory)

$cleanupInfoPath = Join-Path $previewFull 'CLEANUP-INFO.txt'
$cleanupInfo = @"
これはローカル記事プレビュー用の一時フォルダです。

作成日時: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')
実行ID: $RunId
記事ID: $ArticleId
正本記事: $sourceArticleFile

このフォルダには、正本記事の隔離コピー、プレビュー用のdist、Astro・Viteキャッシュ、検証画像、ローカルログが入ります。
正本記事、採用済み画像、公開済みサイト、正規プロジェクトのnode_modulesには影響しません。

ローカル配信を停止し、この実行の検証記録が不要になった後は、この実行フォルダ全体を削除またはゴミ箱へ移動できます。
"@
[System.IO.File]::WriteAllText(
    $cleanupInfoPath,
    $cleanupInfo,
    $utf8Encoding
)

$allowedDirectories = @('src', 'public', 'packages')
foreach ($directoryName in $allowedDirectories) {
    $sourceDirectory = Join-Path $projectFull $directoryName
    if (Test-Path -LiteralPath $sourceDirectory -PathType Container) {
        Copy-Item -LiteralPath $sourceDirectory -Destination (Join-Path $previewFull $directoryName) -Recurse
    }
}

$allowedFiles = @('astro.config.mjs', 'package.json', 'tsconfig.json')
foreach ($fileName in $allowedFiles) {
    $sourceFile = Join-Path $projectFull $fileName
    if (Test-Path -LiteralPath $sourceFile -PathType Leaf) {
        Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $previewFull $fileName)
    }
}

$previewArticleFile = Join-Path $previewFull "src\content\blog\$ArticleId\index.md"
if (-not (Test-Path -LiteralPath $previewArticleFile -PathType Leaf)) {
    throw "隔離コピーの記事ファイルを確認できません: $previewArticleFile"
}

$previewText = [System.IO.File]::ReadAllText($previewArticleFile, $utf8Encoding)
if ($previewText -cne $sourceText) {
    throw 'コピー中に記事の内容が変わりました。正本を変更せず停止します。'
}
$draftPattern = [regex]::new('(?m)^draft:[ \t]*true[ \t]*(?=\r?$)')
$frontmatter = $frontmatterMatch.Groups['frontmatter']
if ($draftPattern.Matches($frontmatter.Value).Count -ne 1) {
    throw 'frontmatter内の draft: true が一意ではありません。正本を変更せず停止します。'
}
$previewFrontmatter = $draftPattern.Replace($frontmatter.Value, 'draft: false', 1)
$previewText = $previewText.Substring(0, $frontmatter.Index) + $previewFrontmatter + $previewText.Substring($frontmatter.Index + $frontmatter.Length)
[System.IO.File]::WriteAllText(
    $previewArticleFile,
    $previewText,
    $utf8Encoding
)

$junctionPath = Join-Path $previewFull 'node_modules'
[void](New-Item -ItemType Junction -Path $junctionPath -Target $sourceNodeModules)

$wrapperConfigPath = Join-Path $previewFull 'codex-preview.config.mjs'
$wrapperConfig = @'
import baseConfig from './astro.config.mjs';
import { defineConfig } from 'astro/config';

export default defineConfig({
  ...baseConfig,
  cacheDir: './.astro-cache',
  vite: {
    ...(baseConfig.vite ?? {}),
    cacheDir: '.vite-cache',
  },
});
'@
[System.IO.File]::WriteAllText(
    $wrapperConfigPath,
    $wrapperConfig,
    $utf8Encoding
)

if ((Get-FileHash -LiteralPath $sourceArticleFile -Algorithm SHA256).Hash -ne $sourceArticleHash) {
    throw 'プレビュー準備中に正本記事が変更されました。検証を完了扱いにせず停止します。'
}

$result = [ordered]@{
    schema_version = '1.1'
    status = 'PREVIEW_WORKSPACE_READY'
    project_root = $projectFull
    source_article = $sourceArticleFile
    source_draft_preserved = $true
    source_article_sha256 = $sourceArticleHash
    powershell_version = $PSVersionTable.PSVersion.ToString()
    preview_root = $previewFull
    preview_article = $previewArticleFile
    preview_config = $wrapperConfigPath
    node_modules_source = $sourceNodeModules
    build_output = (Join-Path $previewFull 'dist')
    temporary_work_root = $temporaryWorkRoot
    verification_directory = $verificationDirectory
    cleanup_info = $cleanupInfoPath
    article_id = $ArticleId
}

$result | ConvertTo-Json -Depth 4
