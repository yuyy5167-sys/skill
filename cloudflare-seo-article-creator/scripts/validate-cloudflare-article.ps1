[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArticlePath,

    [string]$ProjectRoot = 'C:\AIフォルダ\ブログ\site',

    [string]$ExpectedTitle,

    [ValidateSet('eligible', 'not_applicable', 'deferred', 'blocked')]
    [string]$ExpectedAffiliateDisposition,

    [ValidateSet('elementary', 'junior_high', 'high')]
    [string]$ExpectedAffiliateCourse,

    [string[]]$ExpectedEmphasisPhrase = @(),

    [ValidateSet('basic', 'parent')]
    [string]$ValidationMode = 'basic',

    [string]$ExpectedEmphasisPlanJson,

    [ValidateSet('prohibit_generic_shinken_zemi_when_affiliate_eligible', 'allow_task_required_only', 'not_applicable')]
    [string]$ExternalLinkPolicy = 'not_applicable',

    [string[]]$AllowedExternalHref = @()
)

$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()
$actualTitle = $null
$articleSha256 = $null
$currentCheck = 'input_contract'
$checks = [ordered]@{
    input_contract = 'not_checked'
    article_structure = 'not_checked'
    title_contract = 'not_checked'
    affiliate = 'not_checked'
    external_links = 'not_checked'
    emphasis = 'not_checked'
    article_integrity = 'not_checked'
}
$emphasisItems = @()
$emphasisResults = @()
$titleContractMatch = 'not_checked'
$affiliateMarkupCount = 0
$expectedEmphasisCount = @($ExpectedEmphasisPhrase).Count
$matchedEmphasisCount = 0
$disallowedExternalLinks = [System.Collections.Generic.List[string]]::new()

function Add-ValidationError {
    param([string]$Message)
    $errors.Add($Message)
    $checks[$script:currentCheck] = 'fail'
}

function Add-ValidationWarning {
    param([string]$Message)
    $warnings.Add($Message)
}

function ConvertTo-NormalizedText {
    param([AllowNull()][string]$Text)

    if ($null -eq $Text) { return '' }
    $decoded = [System.Net.WebUtility]::HtmlDecode($Text)
    $withoutTags = [regex]::Replace($decoded, '<[^>]+>', '')
    return ([regex]::Replace($withoutTags, '\s+', ' ')).Trim()
}

function ConvertTo-NormalizedHref {
    param([AllowNull()][string]$Href)

    if ([string]::IsNullOrWhiteSpace($Href)) { return '' }
    $value = [System.Net.WebUtility]::HtmlDecode($Href).Trim()
    if ($value.StartsWith('//')) { return "https:$value" }
    return $value
}

function Test-ShinkenZemiOfficialHref {
    param([string]$Href)

    $normalized = ConvertTo-NormalizedHref $Href
    try {
        $uri = [System.Uri]$normalized
        if (-not $uri.IsAbsoluteUri) { return $false }
        $hostName = $uri.Host.ToLowerInvariant()
        return (
            $hostName -eq 'benesse.co.jp' -or
            $hostName.EndsWith('.benesse.co.jp') -or
            $hostName -eq 'benesse.ne.jp' -or
            $hostName.EndsWith('.benesse.ne.jp') -or
            $hostName -eq 'benesse.jp' -or
            $hostName.EndsWith('.benesse.jp')
        )
    }
    catch {
        return $false
    }
}

if ($ValidationMode -eq 'parent') {
    foreach ($required in @('ExpectedTitle', 'ExpectedAffiliateDisposition', 'ExternalLinkPolicy', 'ExpectedEmphasisPlanJson')) {
        if (-not $PSBoundParameters.ContainsKey($required) -or [string]::IsNullOrWhiteSpace([string]$PSBoundParameters[$required])) {
            Add-ValidationError "親完成検査の必須入力がありません: $required"
        }
    }
}
if (-not [string]::IsNullOrWhiteSpace($ExpectedEmphasisPlanJson)) {
    try {
        if (-not $ExpectedEmphasisPlanJson.TrimStart().StartsWith('[')) { throw '強調計画はitems配列のJSONが必要です。' }
        $emphasisItems = @($ExpectedEmphasisPlanJson | ConvertFrom-Json -ErrorAction Stop)
        if ($emphasisItems.Count -eq 0) { throw '強調計画が空です。' }
        foreach ($item in $emphasisItems) {
            if ($null -eq $item -or $item.section_id -isnot [string] -or $item.exact_text -isnot [string] -or
                [string]::IsNullOrWhiteSpace($item.exact_text) -or $item.section_id -cnotmatch '^(lead|H2-[0-9]{2,}|H3-[0-9]{2,}-[0-9]{2,})$') {
                throw '各強調項目にはsection_idと空でないexact_textが必要です。'
            }
            if ($item.PSObject.Properties['heading_text'] -and ($item.heading_text -isnot [string] -or [string]::IsNullOrWhiteSpace($item.heading_text))) {
                throw 'heading_textを指定する場合は空でない見出し文が必要です。'
            }
        }
    }
    catch { Add-ValidationError $_.Exception.Message }
}
elseif ($ValidationMode -eq 'basic') {
    $emphasisItems = @($ExpectedEmphasisPhrase | ForEach-Object { [pscustomobject]@{ section_id = 'any'; exact_text = $_ } })
    foreach ($item in $emphasisItems) {
        if ([string]::IsNullOrWhiteSpace($item.exact_text)) { Add-ValidationError 'ExpectedEmphasisPhraseに空の語句があります。' }
    }
}
$expectedEmphasisCount = @($emphasisItems).Count
if ($checks.input_contract -ne 'fail') { $checks.input_contract = 'pass' }

try {
    $currentCheck = 'article_structure'
    $resolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
    $blogRoot = [System.IO.Path]::GetFullPath((Join-Path $resolvedProjectRoot 'src\content\blog'))
    $resolvedArticlePath = [System.IO.Path]::GetFullPath($ArticlePath)
    $blogPrefix = $blogRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

    if (-not $resolvedArticlePath.StartsWith($blogPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Add-ValidationError "記事ファイルが対象ブログ配下にありません: $resolvedArticlePath"
    }

    if ([System.IO.Path]::GetFileName($resolvedArticlePath) -ne 'index.md') {
        Add-ValidationError '記事ファイル名はindex.mdである必要があります。'
    }

    if (-not (Test-Path -LiteralPath $resolvedArticlePath -PathType Leaf)) {
        Add-ValidationError "記事ファイルが存在しません: $resolvedArticlePath"
        throw '記事ファイルが存在しないため内容検査を継続できません。'
    }

    $articleSha256 = (Get-FileHash -LiteralPath $resolvedArticlePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $content = Get-Content -Raw -LiteralPath $resolvedArticlePath -Encoding UTF8
    $frontmatterMatch = [regex]::Match($content, '\A---\s*\r?\n(?<frontmatter>[\s\S]*?)\r?\n---\s*(?:\r?\n|\z)')

    if (-not $frontmatterMatch.Success) {
        Add-ValidationError '有効なYAML frontmatterを確認できません。'
    }
    else {
        $frontmatter = $frontmatterMatch.Groups['frontmatter'].Value
        $body = $content.Substring($frontmatterMatch.Length)
        $allowedKeys = @('title', 'description', 'date', 'categories', 'tags', 'coverImage', 'draft')
        $topLevelKeys = [regex]::Matches($frontmatter, '(?m)^(?<key>[A-Za-z][A-Za-z0-9_-]*):') | ForEach-Object { $_.Groups['key'].Value }

        foreach ($key in $topLevelKeys) {
            if ($key -notin $allowedKeys) {
                Add-ValidationError "現在のCloudflare記事スキーマで未承認のfrontmatter項目です: $key"
            }
        }

        foreach ($requiredKey in @('title', 'date', 'categories', 'coverImage', 'draft')) {
            if ($requiredKey -notin $topLevelKeys) {
                Add-ValidationError "必須frontmatter項目がありません: $requiredKey"
            }
        }

        if ($frontmatter -notmatch '(?m)^draft:\s*true\s*$') {
            Add-ValidationError 'draftはtrueである必要があります。'
        }

        $titleMatch = [regex]::Match($frontmatter, '(?m)^title:\s*(?<value>[^\r\n]+?)\s*$')
        if ($titleMatch.Success) {
            $actualTitle = $titleMatch.Groups['value'].Value.Trim()
            if ($actualTitle.Length -ge 2) {
                $firstCharacter = $actualTitle.Substring(0, 1)
                $lastCharacter = $actualTitle.Substring($actualTitle.Length - 1, 1)
                if (($firstCharacter -eq '"' -and $lastCharacter -eq '"') -or ($firstCharacter -eq "'" -and $lastCharacter -eq "'")) {
                    $actualTitle = $actualTitle.Substring(1, $actualTitle.Length - 2)
                }
            }
        }

        $currentCheck = 'title_contract'
        if (-not [string]::IsNullOrWhiteSpace($ExpectedTitle)) {
            if ($actualTitle -ceq $ExpectedTitle) {
                $titleContractMatch = 'pass'
                $checks.title_contract = 'pass'
            }
            else {
                $titleContractMatch = 'fail'
                Add-ValidationError "frontmatterのtitleがtitle_contract.selected_titleと一致しません。期待値: $ExpectedTitle / 実値: $actualTitle"
            }
        }

        $currentCheck = 'article_structure'
        if ($body -match '(?m)^\s*#\s+\S') {
            Add-ValidationError '本文にMarkdownのH1があります。H1はfrontmatterのtitleから生成します。'
        }

        if ($body -match '(?i)<\s*h1\b') {
            Add-ValidationError '本文にHTMLのh1があります。'
        }

        if ($body -match '(?i)<\s*(style|script)\b') {
            Add-ValidationError '本文にstyleまたはscript要素があります。'
        }

        if ($body -match '(?i)\sstyle\s*=') {
            Add-ValidationError '本文にインラインstyle属性があります。'
        }

        $placeholderPattern = '(?i)(TODO|example\.com|href\s*=\s*["'']#["'']|\{[^}\r\n]*(URL|画像ID|リンク)[^}\r\n]*\})'
        if ($content -match $placeholderPattern) {
            Add-ValidationError '仮URL、TODO、またはプレースホルダーの可能性がある文字列を検出しました。'
        }

        $currentCheck = 'affiliate'
        $affiliatePattern = "(?is)<div\b[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\bshinken-zemi-cta\b[^\x22\x27]*[\x22\x27][^>]*>"
        $affiliateMarkupCount = [regex]::Matches($body, $affiliatePattern).Count
        if (-not [string]::IsNullOrWhiteSpace($ExpectedAffiliateDisposition)) {
            switch ($ExpectedAffiliateDisposition) {
                'eligible' {
                    if ($affiliateMarkupCount -ne 1) {
                        Add-ValidationError "affiliate.dispositionがeligibleですが、進研ゼミCTA数が1件ではありません: $affiliateMarkupCount"
                    }
                    if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse)) {
                        Add-ValidationError 'affiliate.dispositionがeligibleの場合はExpectedAffiliateCourseが必要です。'
                    }
                    else {
                        $escapedCourse = [regex]::Escape($ExpectedAffiliateCourse)
                        $coursePattern = "(?is)<div\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\bshinken-zemi-cta\b[^\x22\x27]*[\x22\x27])(?=[^>]*data-course\s*=\s*[\x22\x27]$escapedCourse[\x22\x27])[^>]*>"
                        if ($body -notmatch $coursePattern) {
                            Add-ValidationError "進研ゼミCTAのdata-courseが期待講座と一致しません: $ExpectedAffiliateCourse"
                        }
                    }
                }
                'not_applicable' {
                    if ($affiliateMarkupCount -ne 0) {
                        Add-ValidationError "affiliate.dispositionがnot_applicableですが、進研ゼミCTAがあります: $affiliateMarkupCount"
                    }
                }
                'deferred' {
                    if ($affiliateMarkupCount -ne 0) {
                        Add-ValidationError "affiliate.dispositionがdeferredですが、進研ゼミCTAがあります: $affiliateMarkupCount"
                    }
                }
                'blocked' {
                    Add-ValidationError 'affiliate.dispositionがblockedのため、記事を合格にできません。'
                }
            }
        }

        if (-not [string]::IsNullOrWhiteSpace($ExpectedAffiliateDisposition) -and $checks.affiliate -ne 'fail') { $checks.affiliate = 'pass' }

        $currentCheck = 'emphasis'
        if ($checks.input_contract -eq 'pass' -and $emphasisItems.Count -gt 0) {
            $nodeCode = @'
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
(async () => {
  const input = JSON.parse(Buffer.from(process.argv[2], 'base64').toString('utf8'));
  const resolver = createRequire(path.join(input.project_root, 'package.json'));
  const { markdownToHtml, htmlToHast } = await import(pathToFileURL(resolver.resolve('satteri')).href);
  const bytes = fs.readFileSync(input.article_path);
  const source = bytes.toString('utf8').replace(/^\uFEFF/, '');
  const body = source.replace(/^---[ \t]*\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/, '');
  const tree = htmlToHast(markdownToHtml(body).html);
  const sections = new Map([['lead', { heading: '', strong: [] }]]);
  let h2 = 0, h3 = 0, current = 'lead', parent = null;
  const excluded = new Set(['head', 'pre', 'code', 'script', 'style', 'template', 'textarea']);
  const normalize = value => value.replace(/\s+/gu, ' ').trim();
  const hidden = node => {
    const p = node.properties || {};
    return p.hidden === true || p.hidden === '' || p.ariaHidden === true || p.ariaHidden === 'true' ||
      /(?:display\s*:\s*none|visibility\s*:\s*hidden)/i.test(p.style || '');
  };
  const text = node => node.type === 'text' ? node.value :
    (node.type === 'comment' || excluded.has(node.tagName) || hidden(node)) ? '' :
      (node.children || []).map(text).join('');
  const all = [];
  const walk = node => {
    if (node.type === 'comment' || excluded.has(node.tagName) || hidden(node)) return;
    if (/^h[1-6]$/.test(node.tagName || '')) {
      if (node.tagName === 'h2') {
        h2++; h3 = 0; current = 'H2-' + String(h2).padStart(2, '0'); parent = current;
        sections.set(current, { heading: normalize(text(node)), strong: [] });
      } else if (node.tagName === 'h3') {
        h3++; current = 'H3-' + String(h2).padStart(2, '0') + '-' + String(h3).padStart(2, '0');
        sections.set(current, { heading: normalize(text(node)), strong: [] });
      }
      return;
    }
    if (node.tagName === 'strong') {
      const value = normalize(text(node));
      all.push(value); sections.get(current).strong.push(value);
      if (parent && parent !== current) sections.get(parent).strong.push(value);
    }
    for (const child of node.children || []) walk(child);
  };
  walk(tree);
  const items = JSON.parse(input.items_json).map(item => {
    const section = sections.get(item.section_id);
    const texts = item.section_id === 'any' ? all : section?.strong;
    const headingMatch = item.heading_text === undefined || (section && section.heading === normalize(item.heading_text));
    const pass = !!texts && headingMatch && texts.includes(normalize(item.exact_text));
    return { section_id: item.section_id, exact_text: item.exact_text, status: pass ? 'pass' : 'fail',
      reason: pass ? null : !texts ? 'section_not_found' : !headingMatch ? 'heading_mismatch' : 'strong_not_found_in_section' };
  });
  const result = { parser: 'satteri', article_sha256: crypto.createHash('sha256').update(bytes).digest('hex'), items };
  process.stdout.write(JSON.stringify(result).replace(/[\u007f-\uffff]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')));
})().catch(error => { process.stderr.write(error.message); process.exitCode = 1; });
'@
            $itemsJsonForNode = if (-not [string]::IsNullOrWhiteSpace($ExpectedEmphasisPlanJson)) {
                $ExpectedEmphasisPlanJson
            }
            else {
                ConvertTo-Json -InputObject @($emphasisItems) -Depth 8 -Compress
            }
            $requestJson = [pscustomobject]@{
                article_path = $resolvedArticlePath
                project_root = $resolvedProjectRoot
                items_json = $itemsJsonForNode
            } | ConvertTo-Json -Depth 12 -Compress
            $requestBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($requestJson))
            $nodeOutput = $nodeCode | & node - $requestBase64
            if ($LASTEXITCODE -ne 0) { throw 'Markdown解析に失敗しました。簡易正規表現へ切り替えて合格にしません。' }
            $parsed = ($nodeOutput -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
            if ($parsed.article_sha256 -cne $articleSha256) { throw '解析中に記事が変更されました。' }
            $emphasisResults = @($parsed.items)
            foreach ($item in $emphasisResults) {
                if ($item.status -eq 'pass') { $matchedEmphasisCount++ }
                else { Add-ValidationError "指定章の太字が一致しません: $($item.section_id) / $($item.exact_text) / $($item.reason)" }
            }
            if ($emphasisResults.Count -ne $emphasisItems.Count) { Add-ValidationError '強調項目の検査件数が一致しません。' }
            if ($checks.emphasis -ne 'fail') { $checks.emphasis = 'pass' }
        }

        $currentCheck = 'external_links'
        if ($ExternalLinkPolicy -ne 'not_applicable') {
            $articleHrefs = [System.Collections.Generic.List[string]]::new()
            $htmlLinkPattern = "(?is)<a\b[^>]*href\s*=\s*[\x22\x27](?<href>[^\x22\x27]+)[\x22\x27][^>]*>"
            foreach ($htmlLinkMatch in [regex]::Matches($body, $htmlLinkPattern)) {
                $articleHrefs.Add((ConvertTo-NormalizedHref $htmlLinkMatch.Groups['href'].Value))
            }
            foreach ($markdownLinkMatch in [regex]::Matches($body, '(?m)\[[^\]]+\]\((?<href>(?:https?:)?//[^\s)]+)')) {
                $articleHrefs.Add((ConvertTo-NormalizedHref $markdownLinkMatch.Groups['href'].Value))
            }

            $allowedHrefSet = @($AllowedExternalHref | ForEach-Object { ConvertTo-NormalizedHref $_ })
            foreach ($href in @($articleHrefs | Select-Object -Unique)) {
                if ((Test-ShinkenZemiOfficialHref $href) -and $href -notin $allowedHrefSet) {
                    $disallowedExternalLinks.Add($href)
                    Add-ValidationError "許可されていない進研ゼミ公式サイトへの本文リンクがあります: $href"
                }
            }
        }

        if ($PSBoundParameters.ContainsKey('ExternalLinkPolicy') -and $checks.external_links -ne 'fail') { $checks.external_links = 'pass' }
        $currentCheck = 'article_structure'
        $coverMatch = [regex]::Match($frontmatter, '(?m)^coverImage:\s*["'']?(?<path>[^"''\r\n]+)["'']?\s*$')
        if ($coverMatch.Success) {
            $coverPath = $coverMatch.Groups['path'].Value.Trim()
            if ([System.IO.Path]::IsPathRooted($coverPath) -or $coverPath -match '^[a-z][a-z0-9+.-]*://') {
                Add-ValidationError 'coverImageは記事フォルダ内の相対パスで指定してください。'
            }
            else {
                $articleDirectory = Split-Path -Parent $resolvedArticlePath
                $resolvedCoverPath = [System.IO.Path]::GetFullPath((Join-Path $articleDirectory $coverPath))
                $articlePrefix = $articleDirectory.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

                if (-not $resolvedCoverPath.StartsWith($articlePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                    Add-ValidationError 'coverImageが記事フォルダ外を参照しています。'
                }
                elseif (-not (Test-Path -LiteralPath $resolvedCoverPath -PathType Leaf)) {
                    Add-ValidationError "coverImageの実体がありません: $resolvedCoverPath"
                }
                elseif ([System.IO.Path]::GetExtension($resolvedCoverPath) -ne '.webp') {
                    Add-ValidationError '新規記事のcoverImageはWebP形式にしてください。'
                }
            }
        }

        if ($checks.article_structure -ne 'fail') { $checks.article_structure = 'pass' }
        $currentCheck = 'article_integrity'
        if ((Get-FileHash -LiteralPath $resolvedArticlePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $articleSha256) {
            Add-ValidationError '検査中に記事ファイルが変更されました。'
        } else { $checks.article_integrity = 'pass' }

        if ($body -notmatch '(?m)^##\s+\S') {
            Add-ValidationWarning '本文にH2を確認できません。短い記事でない限り構成を再確認してください。'
        }
    }
}
catch {
    Add-ValidationError $_.Exception.Message
}

if ($ValidationMode -eq 'parent') {
    foreach ($key in @($checks.Keys)) {
        if ($checks[$key] -ne 'pass') {
            $currentCheck = $key
            Add-ValidationError "親完成検査が未完了です: $key"
        }
    }
}
$result = [ordered]@{
    status = if ($errors.Count -eq 0) { 'PASS' } else { 'FAIL' }
    validation_mode = $ValidationMode
    parent_contract_pass = ($ValidationMode -eq 'parent' -and $errors.Count -eq 0)
    article_sha256 = $articleSha256
    checks = $checks
    rendered_emphasis = 'not_checked'
    emphasis_items = @($emphasisResults)
    article_path = if ($resolvedArticlePath) { $resolvedArticlePath } else { $ArticlePath }
    actual_title = $actualTitle
    title_contract_match = $titleContractMatch
    affiliate_disposition = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateDisposition)) { 'not_checked' } else { $ExpectedAffiliateDisposition }
    expected_affiliate_course = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse)) { $null } else { $ExpectedAffiliateCourse }
    affiliate_markup_count = $affiliateMarkupCount
    external_link_policy = $ExternalLinkPolicy
    disallowed_external_link_count = $disallowedExternalLinks.Count
    disallowed_external_links = @($disallowedExternalLinks)
    expected_emphasis_count = $expectedEmphasisCount
    matched_emphasis_count = $matchedEmphasisCount
    errors = @($errors)
    warnings = @($warnings)
}

$result | ConvertTo-Json -Depth 4
if ($errors.Count -gt 0) { exit 1 }
