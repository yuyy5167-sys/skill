#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$InputPath,

    [Parameter(Mandatory)]
    [string]$OutputPath,

    [Parameter(Mandatory)]
    [int]$X,

    [Parameter(Mandatory)]
    [int]$Y,

    [Parameter(Mandatory)]
    [ValidateRange(1, 100000)]
    [int]$Width,

    [Parameter(Mandatory)]
    [ValidateRange(1, 100000)]
    [int]$Height,

    [ValidateRange(3, 10)]
    [int]$StrokeWidth = 8,

    [ValidateRange(0, 1000)]
    [int]$CornerRadius = 16,

    [ValidatePattern('^#[0-9A-Fa-f]{6}$')]
    [string]$Color = '#E53935',

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-RoundedRectanglePath {
    param(
        [Parameter(Mandatory)] [System.Drawing.Rectangle]$Rectangle,
        [Parameter(Mandatory)] [int]$Radius
    )

    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    if ($Radius -le 0) {
        $path.AddRectangle($Rectangle)
        return $path
    }

    $diameter = [Math]::Min($Radius * 2, [Math]::Min($Rectangle.Width, $Rectangle.Height))
    $arc = [System.Drawing.Rectangle]::new($Rectangle.X, $Rectangle.Y, $diameter, $diameter)
    $path.AddArc($arc, 180, 90)
    $arc.X = $Rectangle.Right - $diameter
    $path.AddArc($arc, 270, 90)
    $arc.Y = $Rectangle.Bottom - $diameter
    $path.AddArc($arc, 0, 90)
    $arc.X = $Rectangle.Left
    $path.AddArc($arc, 90, 90)
    $path.CloseFigure()
    return $path
}

function Assert-UnchangedOutsideAnnotation {
    param(
        [Parameter(Mandatory)] [System.Drawing.Bitmap]$Original,
        [Parameter(Mandatory)] [System.Drawing.Bitmap]$Annotated,
        [Parameter(Mandatory)] [System.Drawing.Rectangle]$AnnotationRectangle
    )

    $allowedArea = $AnnotationRectangle
    $allowedArea.Inflate(1, 1)
    $changedOutsideAnnotation = 0
    for ($row = 0; $row -lt $Original.Height; $row++) {
        for ($column = 0; $column -lt $Original.Width; $column++) {
            if ($column -ge $allowedArea.Left -and $column -lt $allowedArea.Right -and $row -ge $allowedArea.Top -and $row -lt $allowedArea.Bottom) {
                continue
            }
            if ($Original.GetPixel($column, $row).ToArgb() -ne $Annotated.GetPixel($column, $row).ToArgb()) {
                $changedOutsideAnnotation++
                if ($changedOutsideAnnotation -ge 1) {
                    throw "赤枠の許容範囲外にピクセル差分があります: X=$column Y=$row"
                }
            }
        }
    }
}

$inputFullPath = [System.IO.Path]::GetFullPath($InputPath)
$outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
if ($inputFullPath -eq $outputFullPath) {
    throw '原本を上書きできません。OutputPathには別名の加工版を指定してください。'
}
if ((Test-Path -LiteralPath $outputFullPath) -and -not $Force) {
    throw "出力先がすでに存在します: $outputFullPath。別名を使うか、意図した再生成時だけ -Force を指定してください。"
}

$outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    throw "出力先フォルダが存在しません: $outputDirectory"
}

Add-Type -AssemblyName System.Drawing
$source = $null
$canvas = $null
$graphics = $null
$pen = $null
$path = $null
try {
    $source = [System.Drawing.Bitmap]::FromFile($inputFullPath)
    if ($X -lt 0 -or $Y -lt 0 -or $X + $Width -gt $source.Width -or $Y + $Height -gt $source.Height) {
        throw "赤枠の範囲が画像外です。画像: $($source.Width)x$($source.Height)、指定: X=$X Y=$Y W=$Width H=$Height"
    }

    $canvas = [System.Drawing.Bitmap]::new($source.Width, $source.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $canvas.SetResolution($source.HorizontalResolution, $source.VerticalResolution)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
    $graphics.DrawImageUnscaled($source, 0, 0)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

    $pen = [System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml($Color), $StrokeWidth)
    $pen.Alignment = [System.Drawing.Drawing2D.PenAlignment]::Inset
    $rectangle = [System.Drawing.Rectangle]::new($X, $Y, $Width, $Height)
    $path = New-RoundedRectanglePath -Rectangle $rectangle -Radius $CornerRadius
    $graphics.DrawPath($pen, $path)
    $canvas.Save($outputFullPath, [System.Drawing.Imaging.ImageFormat]::Png)

    $check = [System.Drawing.Bitmap]::FromFile($outputFullPath)
    try {
        if ($check.Width -ne $source.Width -or $check.Height -ne $source.Height) {
            throw '出力後の画像寸法が原本と一致しません。'
        }
        Assert-UnchangedOutsideAnnotation -Original $source -Annotated $check -AnnotationRectangle $rectangle
    }
    finally {
        $check.Dispose()
    }

    [pscustomobject]@{
        InputPath = $inputFullPath
        OutputPath = $outputFullPath
        Dimensions = "$($source.Width)x$($source.Height)"
        Rectangle = "X=$X Y=$Y Width=$Width Height=$Height"
        StrokeWidth = $StrokeWidth
        Color = $Color
        PixelIntegrity = '赤枠の許容範囲外に差分なし'
    }
}
finally {
    if ($null -ne $path) { $path.Dispose() }
    if ($null -ne $pen) { $pen.Dispose() }
    if ($null -ne $graphics) { $graphics.Dispose() }
    if ($null -ne $canvas) { $canvas.Dispose() }
    if ($null -ne $source) { $source.Dispose() }
}
