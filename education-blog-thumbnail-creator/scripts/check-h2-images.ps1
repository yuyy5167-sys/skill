[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArticlePath,

    [string]$ImageCheckerPath,
    [int]$ExpectedWidth = 1536,
    [int]$ExpectedHeight = 864,
    [int]$TargetBytes = 307200,
    [int]$RecompressBytes = 512000,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

# Resolve defaults after parameter binding, when the script root is available.
if ([string]::IsNullOrWhiteSpace($ImageCheckerPath)) {
    $ImageCheckerPath = Join-Path $PSScriptRoot "check-thumbnail.ps1"
}

function Write-ResultAndExit {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Result,
        [Parameter(Mandatory = $true)]
        [int]$ExitCode
    )

    $Result | ConvertTo-Json -Depth 10
    exit $ExitCode
}

if (-not (Test-Path -LiteralPath $ArticlePath -PathType Leaf)) {
    Write-ResultAndExit -ExitCode 2 -Result ([pscustomobject]@{
        status = "fail"
        article_path = $ArticlePath
        errors = @("article_not_found")
    })
}

if (-not (Test-Path -LiteralPath $ImageCheckerPath -PathType Leaf)) {
    Write-ResultAndExit -ExitCode 2 -Result ([pscustomobject]@{
        status = "fail"
        article_path = (Resolve-Path -LiteralPath $ArticlePath).Path
        errors = @("image_checker_not_found")
    })
}

$resolvedArticlePath = (Resolve-Path -LiteralPath $ArticlePath).Path
$articleDirectory = Split-Path -Parent $resolvedArticlePath
$imageRoot = [System.IO.Path]::GetFullPath((Join-Path $articleDirectory "images"))
$imageRootPrefix = $imageRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$lines = @(Get-Content -LiteralPath $resolvedArticlePath -Encoding UTF8)

$records = [System.Collections.Generic.List[object]]::new()
$inFrontmatter = $false
$frontmatterFinished = $false
$inFence = $false
$fenceMarker = ""
$inHtmlComment = $false

for ($index = 0; $index -lt $lines.Count; $index++) {
    $raw = [string]$lines[$index]
    $lineNumber = $index + 1

    if ($index -eq 0 -and $raw.Trim() -eq "---") {
        $inFrontmatter = $true
        $records.Add([pscustomobject]@{ line = $lineNumber; text = ""; headingEligible = $false })
        continue
    }

    if ($inFrontmatter) {
        if ($raw.Trim() -eq "---") {
            $inFrontmatter = $false
            $frontmatterFinished = $true
        }
        $records.Add([pscustomobject]@{ line = $lineNumber; text = ""; headingEligible = $false })
        continue
    }

    if (-not $frontmatterFinished -and $index -gt 0) {
        $frontmatterFinished = $true
    }

    $trimmed = $raw.TrimStart()
    if (-not $inFence -and $trimmed -match '^(`{3,}|~{3,})') {
        $inFence = $true
        $fenceMarker = $Matches[1].Substring(0, 1)
        $records.Add([pscustomobject]@{ line = $lineNumber; text = $raw; headingEligible = $false })
        continue
    }
    if ($inFence) {
        $records.Add([pscustomobject]@{ line = $lineNumber; text = $raw; headingEligible = $false })
        if (($fenceMarker -eq '`' -and $trimmed -match '^`{3,}\s*$') -or ($fenceMarker -eq '~' -and $trimmed -match '^~{3,}\s*$')) {
            $inFence = $false
            $fenceMarker = ""
        }
        continue
    }

    $visible = $raw
    while ($true) {
        if ($inHtmlComment) {
            $commentEnd = $visible.IndexOf("-->", [System.StringComparison]::Ordinal)
            if ($commentEnd -lt 0) {
                $visible = ""
                break
            }
            $visible = $visible.Substring($commentEnd + 3)
            $inHtmlComment = $false
            continue
        }

        $commentStart = $visible.IndexOf("<!--", [System.StringComparison]::Ordinal)
        if ($commentStart -lt 0) {
            break
        }

        $commentEnd = $visible.IndexOf("-->", $commentStart + 4, [System.StringComparison]::Ordinal)
        if ($commentEnd -ge 0) {
            $visible = $visible.Substring(0, $commentStart) + $visible.Substring($commentEnd + 3)
            continue
        }

        $visible = $visible.Substring(0, $commentStart)
        $inHtmlComment = $true
        break
    }

    $headingEligible = -not ($visible -match '^\s*>')
    $records.Add([pscustomobject]@{ line = $lineNumber; text = $visible; headingEligible = $headingEligible })
}

$headings = [System.Collections.Generic.List[object]]::new()
for ($index = 0; $index -lt $records.Count; $index++) {
    $record = $records[$index]
    if (-not $record.headingEligible) {
        continue
    }

    $match = [regex]::Match($record.text, '^\s{0,3}##(?!#)\s+(.+?)\s*$')
    if (-not $match.Success) {
        continue
    }

    $heading = [regex]::Replace($match.Groups[1].Value, '\s+#+\s*$', '').Trim()
    $headings.Add([pscustomobject]@{
        heading = $heading
        line = $record.line
        recordIndex = $index
    })
}

if ($headings.Count -eq 0) {
    Write-ResultAndExit -ExitCode 0 -Result ([pscustomobject]@{
        status = "not_applicable"
        applicability = "not_applicable"
        not_applicable_reason = "no_markdown_h2"
        article_path = $resolvedArticlePath
        h2_count = 0
        valid_h2_image_count = 0
        items = @()
        errors = @()
    })
}

$items = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()
$seenPaths = @{}

foreach ($headingEntry in $headings) {
    $firstContent = $null
    for ($scan = $headingEntry.recordIndex + 1; $scan -lt $records.Count; $scan++) {
        $candidate = $records[$scan]
        if ([string]::IsNullOrWhiteSpace($candidate.text)) {
            continue
        }
        $firstContent = $candidate
        break
    }

    $itemErrors = [System.Collections.Generic.List[string]]::new()
    $alt = ""
    $relativePath = ""
    $resolvedImagePath = ""
    $assetCheck = $null

    if ($null -eq $firstContent) {
        $itemErrors.Add("missing_h2_image")
    }
    else {
        $imageMatch = [regex]::Match($firstContent.text.Trim(), '^!\[([^\]]*)\]\((?:<([^>]+)>|([^\s\)]+))(?:\s+["''][^"'']*["''])?\)\s*$')
        if (-not $imageMatch.Success) {
            $itemErrors.Add("first_content_is_not_markdown_image")
        }
        else {
            $alt = $imageMatch.Groups[1].Value.Trim()
            $relativePath = if ($imageMatch.Groups[2].Success) { $imageMatch.Groups[2].Value } else { $imageMatch.Groups[3].Value }

            if ([string]::IsNullOrWhiteSpace($alt)) {
                $itemErrors.Add("empty_alt")
            }

            if ($relativePath -match '^(?i:https?:|data:|/)') {
                $itemErrors.Add("nonlocal_h2_image")
            }
            else {
                try {
                    $resolvedImagePath = [System.IO.Path]::GetFullPath((Join-Path $articleDirectory $relativePath))
                }
                catch {
                    $itemErrors.Add("invalid_image_path")
                }

                if ($resolvedImagePath) {
                    if (-not $resolvedImagePath.StartsWith($imageRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                        $itemErrors.Add("image_outside_article_images")
                    }

                    if ([System.IO.Path]::GetFileName($resolvedImagePath) -notmatch '^(?i)h2-') {
                        $itemErrors.Add("not_h2_named_asset")
                    }

                    $pathKey = $resolvedImagePath.ToLowerInvariant()
                    if ($seenPaths.ContainsKey($pathKey)) {
                        $itemErrors.Add("duplicate_h2_image_path")
                    }
                    else {
                        $seenPaths[$pathKey] = $headingEntry.heading
                    }

                    if (-not (Test-Path -LiteralPath $resolvedImagePath -PathType Leaf)) {
                        $itemErrors.Add("image_file_not_found")
                    }
                    elseif ($itemErrors.Count -eq 0) {
                        try {
                            $checkJson = (& $ImageCheckerPath -Path $resolvedImagePath -ExpectedWidth $ExpectedWidth -ExpectedHeight $ExpectedHeight -TargetBytes $TargetBytes -RecompressBytes $RecompressBytes -PythonCommand $PythonCommand | Out-String)
                            $assetCheck = $checkJson | ConvertFrom-Json
                            if ($assetCheck.status -eq "fail") {
                                $itemErrors.Add("asset_validation_failed")
                            }
                        }
                        catch {
                            $itemErrors.Add("asset_validation_unreadable")
                        }
                    }
                }
            }
        }
    }

    foreach ($itemError in $itemErrors) {
        $errors.Add(("line_{0}:{1}:{2}" -f $headingEntry.line, $headingEntry.heading, $itemError))
    }

    $items.Add([pscustomobject]@{
        heading = $headingEntry.heading
        heading_line = $headingEntry.line
        image_line = if ($null -ne $firstContent) { $firstContent.line } else { $null }
        alt = $alt
        relative_path = $relativePath
        resolved_path = $resolvedImagePath
        status = if ($itemErrors.Count -eq 0) { "pass" } else { "fail" }
        errors = @($itemErrors)
        asset_check = $assetCheck
    })
}

$validCount = @($items | Where-Object { $_.status -eq "pass" }).Count
$result = [pscustomobject]@{
    status = if ($errors.Count -eq 0) { "pass" } else { "fail" }
    applicability = "applicable"
    not_applicable_reason = $null
    article_path = $resolvedArticlePath
    h2_count = $headings.Count
    valid_h2_image_count = $validCount
    items = @($items)
    errors = @($errors)
}

Write-ResultAndExit -Result $result -ExitCode $(if ($errors.Count -eq 0) { 0 } else { 1 })
