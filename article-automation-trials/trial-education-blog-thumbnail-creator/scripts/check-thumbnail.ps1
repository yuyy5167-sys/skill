[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [int]$ExpectedWidth = 1536,
    [int]$ExpectedHeight = 864,
    [int]$TargetBytes = 307200,
    [int]$RecompressBytes = 512000,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    [pscustomobject]@{
        status = "fail"
        path = $Path
        errors = @("file_not_found")
    } | ConvertTo-Json -Depth 5
    exit 2
}

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$pythonCode = @'
import json
import os
import sys

from PIL import Image

path = sys.argv[1]
with Image.open(path) as image:
    result = {
        "path": os.path.abspath(path),
        "width": image.width,
        "height": image.height,
        "format": (image.format or "").upper(),
        "mode": image.mode,
        "frames": getattr(image, "n_frames", 1),
        "bytes": os.path.getsize(path),
    }
# ASCII JSON preserves Unicode paths through Windows PowerShell's native pipe.
print(json.dumps(result, ensure_ascii=True))
'@

try {
    # Pass source through stdin: PowerShell 5.1 rewrites embedded quotes in -c.
    $metadataJson = $pythonCode | & $PythonCommand -X utf8 - $resolvedPath
    if ($LASTEXITCODE -ne 0) {
        throw "Python image inspection failed with exit code $LASTEXITCODE."
    }
    $metadata = $metadataJson | ConvertFrom-Json
}
catch {
    [pscustomobject]@{
        status = "fail"
        path = $resolvedPath
        errors = @("image_metadata_unreadable")
        detail = $_.Exception.Message
    } | ConvertTo-Json -Depth 5
    exit 2
}

$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

if ($metadata.width -ne $ExpectedWidth -or $metadata.height -ne $ExpectedHeight) {
    $errors.Add("unexpected_dimensions")
}

$actualRatio = [double]$metadata.width / [double]$metadata.height
$expectedRatio = [double]$ExpectedWidth / [double]$ExpectedHeight
if ([math]::Abs($actualRatio - $expectedRatio) -gt 0.001) {
    $errors.Add("unexpected_aspect_ratio")
}

if ($metadata.format -ne "WEBP") {
    $errors.Add("not_webp")
}

if ($metadata.bytes -gt $RecompressBytes) {
    $errors.Add("recompression_required")
}
elseif ($metadata.bytes -gt $TargetBytes) {
    $warnings.Add("above_300kb_target")
}

$status = if ($errors.Count -gt 0) {
    "fail"
}
elseif ($warnings.Count -gt 0) {
    "pass_with_warning"
}
else {
    "pass"
}

[pscustomobject]@{
    status = $status
    path = $metadata.path
    width = $metadata.width
    height = $metadata.height
    aspect_ratio = [math]::Round($actualRatio, 6)
    format = $metadata.format
    mode = $metadata.mode
    frames = $metadata.frames
    bytes = $metadata.bytes
    target_bytes = $TargetBytes
    recompress_bytes = $RecompressBytes
    errors = @($errors)
    warnings = @($warnings)
} | ConvertTo-Json -Depth 5

if ($errors.Count -gt 0) {
    exit 1
}

exit 0
