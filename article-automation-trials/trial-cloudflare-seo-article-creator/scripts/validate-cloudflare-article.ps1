[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArticlePath,

    [string]$ProjectRoot = 'C:\AIフォルダ\ブログ\site',

    [string]$ExpectedTitle,

    [string]$ExpectedArticleProfileJson,

    [string]$ExpectedCtaStrategyJson,

    [string]$ExpectedReviewEvidencePlanJson,

    [string]$ExpectedPriceEvidencePlanJson,

    [ValidateSet('conversion', 'traffic')]
    [string]$ExpectedArticleBusinessPurpose,

    [ValidateSet('eligible', 'not_applicable', 'deferred', 'blocked')]
    [string]$ExpectedAffiliateDisposition,

    [ValidateSet('preschool', 'elementary', 'junior_high', 'high')]
    [string]$ExpectedAffiliateCourse,

    [ValidateSet('shinken_zemi', 'smile_zemi')]
    [string]$ExpectedAffiliateProvider,

    [string[]]$ExpectedEmphasisPhrase = @(),

    [ValidateSet('basic', 'parent')]
    [string]$ValidationMode = 'basic',

    [string]$ExpectedEmphasisPlanJson,

    [string]$ExpectedInternalLinkManifestJson,

    [string]$ExpectedAffiliateLinkManifestJson,

    [ValidateSet('prohibit_generic_shinken_zemi_when_affiliate_eligible', 'allow_task_required_only', 'not_applicable')]
    [string]$ExternalLinkPolicy = 'allow_task_required_only',

    [string[]]$AllowedExternalHref = @(),

    [string]$AllowedExternalApprovalJson = '[]',

    [string]$RenderedHtmlPath
)

$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()
$actualTitle = $null
$articleSha256 = $null
$currentCheck = 'input_contract'
$checks = [ordered]@{
    input_contract = 'not_checked'
    article_profile = 'not_checked'
    review_price_evidence = 'not_checked'
    cta_strategy = 'not_checked'
    article_structure = 'not_checked'
    title_contract = 'not_checked'
    internal_links = 'not_checked'
    affiliate = 'not_checked'
    external_links = 'not_checked'
    emphasis = 'not_checked'
    article_integrity = 'not_checked'
}
$emphasisItems = @()
$emphasisResults = @()
$parsedMarkup = $null
$internalLinkManifest = $null
$expectedInternalLinks = @()
$internalLinkResults = @()
$affiliateLinkManifest = $null
$affiliateManifestLinks = @()
$articleProfile = $null
$reviewEvidencePlan = $null
$priceEvidencePlan = $null
$ctaStrategy = $null
$ctaStrategyMoments = @()
$plannedCtaCount = $null
$titleContractMatch = 'not_checked'
$affiliateMarkupCount = 0
$affiliateSourceVerified = 'not_checked'
$internalLinkCardCount = 0
$expectedInternalLinkCount = 0
$matchedInternalLinkCount = 0
$expectedEmphasisCount = @($ExpectedEmphasisPhrase).Count
$matchedEmphasisCount = 0
$disallowedExternalLinks = [System.Collections.Generic.List[string]]::new()
$externalLinkAudit = $null
$effectiveAffiliateProvider = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateProvider)) { 'shinken_zemi' } else { $ExpectedAffiliateProvider }
$affiliateComponentId = if ($effectiveAffiliateProvider -eq 'smile_zemi') { 'smile_zemi_cta_v1' } else { 'shinken_zemi_cta_v1' }
$affiliateRootClass = if ($effectiveAffiliateProvider -eq 'smile_zemi') { 'smile-zemi-cta' } else { 'shinken-zemi-cta' }
$affiliateButtonClass = if ($effectiveAffiliateProvider -eq 'smile_zemi') { 'smile-zemi-cta__button' } else { 'shinken-zemi-cta__button' }
$affiliateLabel = if ($effectiveAffiliateProvider -eq 'smile_zemi') { 'スマイルゼミ' } else { '進研ゼミ' }

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

function Get-InternalHrefKey {
    param([AllowNull()][string]$Href)

    $normalized = ConvertTo-NormalizedHref $Href
    if ([string]::IsNullOrWhiteSpace($normalized)) { return '' }

    try {
        $uri = if ($normalized.StartsWith('/')) {
            [System.Uri]::new("https://internal.invalid$normalized")
        }
        else {
            [System.Uri]$normalized
        }

        if (-not $uri.IsAbsoluteUri) { return $normalized.TrimEnd('/') }
        $path = $uri.AbsolutePath
        if ($path.Length -gt 1) { $path = $path.TrimEnd('/') }
        return "$path$($uri.Query)"
    }
    catch {
        return $normalized.TrimEnd('/')
    }
}

function Test-ExpectedInternalHref {
    param(
        [AllowNull()][string]$ExpectedHref,
        [AllowNull()][string]$ActualHref
    )

    $expected = ConvertTo-NormalizedHref $ExpectedHref
    $actual = ConvertTo-NormalizedHref $ActualHref
    if ([string]::IsNullOrWhiteSpace($expected) -or [string]::IsNullOrWhiteSpace($actual)) { return $false }
    if ($expected -ceq $actual) { return $true }

    try {
        $expectedUri = [System.Uri]$expected
        $actualUri = [System.Uri]$actual
        if ($expectedUri.IsAbsoluteUri -and $actualUri.IsAbsoluteUri -and $expectedUri.Host -cne $actualUri.Host) {
            return $false
        }
    }
    catch {}

    $expectedKey = Get-InternalHrefKey $expected
    $actualKey = Get-InternalHrefKey $actual
    return -not [string]::IsNullOrWhiteSpace($expectedKey) -and $expectedKey -ceq $actualKey
}

function Test-ExactHref {
    param(
        [AllowNull()][string]$ExpectedHref,
        [AllowNull()][string]$ActualHref
    )

    $expected = ConvertTo-NormalizedHref $ExpectedHref
    $actual = ConvertTo-NormalizedHref $ActualHref
    return -not [string]::IsNullOrWhiteSpace($expected) -and $expected -ceq $actual
}

if ($ValidationMode -eq 'parent') {
    foreach ($required in @('ExpectedTitle', 'ExpectedArticleBusinessPurpose', 'ExpectedArticleProfileJson', 'ExpectedCtaStrategyJson', 'ExpectedAffiliateDisposition', 'ExternalLinkPolicy', 'ExpectedEmphasisPlanJson', 'ExpectedInternalLinkManifestJson', 'ExpectedAffiliateLinkManifestJson', 'RenderedHtmlPath')) {
        if (-not $PSBoundParameters.ContainsKey($required) -or [string]::IsNullOrWhiteSpace([string]$PSBoundParameters[$required])) {
            Add-ValidationError "親完成検査の必須入力がありません: $required"
        }
    }
    if ($ExpectedArticleBusinessPurpose -eq 'conversion' -and $ExpectedAffiliateDisposition -ne 'eligible') {
        Add-ValidationError '成約用記事の親完成検査には、挿入・監査済みのアフィリエイトCTAが必要です。ExpectedAffiliateDispositionはeligibleにしてください。'
    }
    if ($ExpectedArticleBusinessPurpose -eq 'traffic' -and $ExpectedAffiliateDisposition -ne 'not_applicable') {
        Add-ValidationError '集客用記事では直接のアフィリエイトCTAを禁止します。ExpectedAffiliateDispositionはnot_applicableにしてください。'
    }
    if ($ExternalLinkPolicy -ne 'allow_task_required_only') {
        Add-ValidationError '新記事の親完成検査では、ただの公式サイト誘導を禁止するためExternalLinkPolicyはallow_task_required_onlyが必要です。'
    }
}

$currentCheck = 'article_profile'
if (-not [string]::IsNullOrWhiteSpace($ExpectedArticleProfileJson)) {
    try {
        $articleProfile = $ExpectedArticleProfileJson | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $articleProfile -or $articleProfile.type -notin @('conversion_review_price', 'conversion_other', 'traffic')) {
            throw 'article_profile.typeはconversion_review_price、conversion_other、trafficのいずれかが必要です。'
        }
        if ($articleProfile.classification_reason -isnot [string] -or [string]::IsNullOrWhiteSpace($articleProfile.classification_reason)) {
            throw 'article_profileには空でないclassification_reasonが必要です。'
        }
        if ($ExpectedArticleBusinessPurpose -eq 'traffic' -and $articleProfile.type -cne 'traffic') {
            throw '集客用記事のarticle_profile.typeはtrafficである必要があります。'
        }
        if ($ExpectedArticleBusinessPurpose -eq 'conversion' -and $articleProfile.type -notin @('conversion_review_price', 'conversion_other')) {
            throw '成約用記事のarticle_profile.typeはconversion_review_priceまたはconversion_otherである必要があります。'
        }
        $checks.article_profile = 'pass'
    }
    catch { Add-ValidationError $_.Exception.Message }
}
elseif ($ValidationMode -eq 'parent') {
    Add-ValidationError '親完成検査にはExpectedArticleProfileJsonが必要です。'
}

$currentCheck = 'review_price_evidence'
if ($null -ne $articleProfile -and $articleProfile.type -ceq 'conversion_review_price') {
    if ([string]::IsNullOrWhiteSpace($ExpectedReviewEvidencePlanJson) -or [string]::IsNullOrWhiteSpace($ExpectedPriceEvidencePlanJson)) {
        Add-ValidationError 'conversion_review_priceには口コミ計画と料金計画をそれぞれrequiredまたはnot_applicableで渡す必要があります。'
    }
    else {
        try {
            $reviewEvidencePlan = $ExpectedReviewEvidencePlanJson | ConvertFrom-Json -ErrorAction Stop
            $priceEvidencePlan = $ExpectedPriceEvidencePlanJson | ConvertFrom-Json -ErrorAction Stop
            if ($reviewEvidencePlan.applicability -notin @('required', 'not_applicable')) {
                throw 'review_evidence_plan.applicabilityはrequiredまたはnot_applicableが必要です。'
            }
            if ($priceEvidencePlan.applicability -notin @('required', 'not_applicable')) {
                throw 'price_evidence_plan.applicabilityはrequiredまたはnot_applicableが必要です。'
            }
            if ($reviewEvidencePlan.applicability -eq 'not_applicable' -and $priceEvidencePlan.applicability -eq 'not_applicable') {
                throw 'conversion_review_priceでは口コミ計画と料金計画の少なくとも一方をrequiredにしてください。'
            }

            if ($reviewEvidencePlan.applicability -eq 'required') {
                $minimumContextElements = 0
                if (-not [int]::TryParse([string]$reviewEvidencePlan.minimum_context_elements, [ref]$minimumContextElements) -or $minimumContextElements -lt 3) {
                    throw 'review_evidence_plan.minimum_context_elementsは3以上が必要です。'
                }
                if ($reviewEvidencePlan.positive_status -notin @('found', 'not_found_after_research') -or
                    $reviewEvidencePlan.negative_status -notin @('found', 'not_found_after_research')) {
                    throw '口コミ計画には良い口コミと悪い口コミの調査状態が必要です。'
                }
                $reviewSources = @($reviewEvidencePlan.searched_sources)
                $reviewEntries = @($reviewEvidencePlan.entries)
                if ($reviewSources.Count -lt 1) { throw '口コミ計画にはsearched_sourcesが1件以上必要です。' }
                if ($reviewEvidencePlan.positive_status -eq 'found' -and @($reviewEntries | Where-Object { $_.sentiment -in @('positive', 'mixed') }).Count -lt 1) {
                    throw 'positive_statusがfoundの場合は良い内容を含む口コミ項目が必要です。'
                }
                if ($reviewEvidencePlan.negative_status -eq 'found' -and @($reviewEntries | Where-Object { $_.sentiment -in @('negative', 'mixed') }).Count -lt 1) {
                    throw 'negative_statusがfoundの場合は悪い内容を含む口コミ項目が必要です。'
                }
                if ($reviewEvidencePlan.negative_status -eq 'not_found_after_research' -and
                    ($reviewEvidencePlan.negative_search_summary -isnot [string] -or [string]::IsNullOrWhiteSpace($reviewEvidencePlan.negative_search_summary))) {
                    throw '悪い口コミを確認できなかった場合はnegative_search_summaryが必要です。'
                }
                foreach ($entry in $reviewEntries) {
                    if ($null -eq $entry -or $entry.sentiment -notin @('positive', 'negative', 'mixed') -or
                        $entry.source_url -isnot [string] -or [string]::IsNullOrWhiteSpace($entry.source_url) -or
                        $entry.checked_at -isnot [string] -or [string]::IsNullOrWhiteSpace($entry.checked_at) -or
                        $entry.summary_text -isnot [string] -or [string]::IsNullOrWhiteSpace($entry.summary_text) -or
                        @($entry.context_elements).Count -lt $minimumContextElements) {
                        throw '各口コミ項目には感情区分、出典、確認日、要約、3要素以上の文脈が必要です。'
                    }
                }
            }

            if ($priceEvidencePlan.applicability -eq 'required') {
                if ($priceEvidencePlan.checked_at -isnot [string] -or [string]::IsNullOrWhiteSpace($priceEvidencePlan.checked_at)) {
                    throw 'price_evidence_planにはchecked_atが必要です。'
                }
                $priceCoverage = @($priceEvidencePlan.coverage)
                $priceItems = @($priceEvidencePlan.items)
                if ($priceCoverage.Count -lt 1 -or $priceItems.Count -lt 1) {
                    throw '料金計画にはcoverageと公式根拠itemsが1件以上必要です。'
                }
                foreach ($coverage in $priceCoverage) {
                    if ($coverage.topic -notin @('base_fee', 'payment_method', 'tablet_cost', 'continuation', 'withdrawal', 'campaign', 'option') -or
                        $coverage.status -notin @('supported', 'partially_supported', 'unverified', 'not_applicable')) {
                        throw '料金coverageのtopicまたはstatusが正しくありません。'
                    }
                }
                foreach ($item in $priceItems) {
                    if ($null -eq $item -or $item.source_url -isnot [string] -or [string]::IsNullOrWhiteSpace($item.source_url) -or
                        $item.checked_at -isnot [string] -or [string]::IsNullOrWhiteSpace($item.checked_at) -or
                        $item.applicable_scope -isnot [string] -or [string]::IsNullOrWhiteSpace($item.applicable_scope) -or
                        $item.supported_fact -isnot [string] -or [string]::IsNullOrWhiteSpace($item.supported_fact)) {
                        throw '各料金根拠には公式URL、確認日、適用範囲、確認事実が必要です。'
                    }
                }
            }
            $checks.review_price_evidence = 'pass'
        }
        catch { Add-ValidationError $_.Exception.Message }
    }
}
elseif ($null -ne $articleProfile) {
    $checks.review_price_evidence = 'pass'
}

$currentCheck = 'cta_strategy'
if (-not [string]::IsNullOrWhiteSpace($ExpectedCtaStrategyJson)) {
    try {
        $ctaStrategy = $ExpectedCtaStrategyJson | ConvertFrom-Json -ErrorAction Stop
        $defaultCount = 0
        if (-not [int]::TryParse([string]$ctaStrategy.default_count, [ref]$defaultCount) -or $defaultCount -ne 3) {
            throw 'cta_strategy.default_countは3である必要があります。'
        }
        if (-not [int]::TryParse([string]$ctaStrategy.planned_count, [ref]$plannedCtaCount) -or $plannedCtaCount -lt 0) {
            throw 'cta_strategy.planned_countは0以上の整数が必要です。'
        }
        if (-not $ctaStrategy.PSObject.Properties['official_confirmation_moments']) {
            throw 'cta_strategyにはofficial_confirmation_moments配列が必要です。'
        }
        $ctaStrategyMoments = @($ctaStrategy.official_confirmation_moments)
        if ($ctaStrategyMoments.Count -ne $plannedCtaCount) {
            throw "cta_strategy.planned_countと公式確認場面の件数が一致しません: $plannedCtaCount / $($ctaStrategyMoments.Count)"
        }

        if ($ExpectedArticleBusinessPurpose -eq 'traffic') {
            if ($plannedCtaCount -ne 0 -or $ctaStrategy.count_mode -cne 'not_applicable') {
                throw '集客用記事のCTA計画はplanned_count: 0、count_mode: not_applicableが必要です。'
            }
        }
        elseif ($ExpectedArticleBusinessPurpose -eq 'conversion') {
            if ($plannedCtaCount -lt 1) { throw '成約用記事には1件以上のCTA計画が必要です。' }
            if ($ctaStrategy.count_reason -isnot [string] -or [string]::IsNullOrWhiteSpace($ctaStrategy.count_reason)) {
                throw '成約用cta_strategyにはcount_reasonが必要です。'
            }
            $hasOverride = $ctaStrategy.PSObject.Properties['explicit_user_count_override'] -and $null -ne $ctaStrategy.explicit_user_count_override
            $expectedMode = if ($hasOverride) { 'explicit_override' } elseif ($plannedCtaCount -lt 3) { 'decreased' } elseif ($plannedCtaCount -gt 3) { 'increased' } else { 'standard' }
            if ($ctaStrategy.count_mode -cne $expectedMode) {
                throw "cta_strategy.count_modeが採用件数と一致しません。期待値: $expectedMode / 実値: $($ctaStrategy.count_mode)"
            }
            if ($hasOverride) {
                $overrideCount = 0
                if (-not [int]::TryParse([string]$ctaStrategy.explicit_user_count_override, [ref]$overrideCount) -or $overrideCount -ne $plannedCtaCount) {
                    throw 'explicit_user_count_overrideはplanned_countと一致する整数が必要です。'
                }
            }
        }

        $placementIds = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        $leadCopies = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        foreach ($moment in $ctaStrategyMoments) {
            foreach ($field in @('placement_id', 'reader_question', 'official_information_needed', 'section_id', 'section_heading', 'destination_purpose', 'lead_copy')) {
                if (-not $moment.PSObject.Properties[$field] -or $moment.$field -isnot [string] -or [string]::IsNullOrWhiteSpace($moment.$field)) {
                    throw "各公式確認場面には空でない$fieldが必要です。"
                }
            }
            if (-not $placementIds.Add($moment.placement_id)) { throw "placement_idが重複しています: $($moment.placement_id)" }
            if (-not $leadCopies.Add($moment.lead_copy.Trim())) { throw "CTAのlead_copyが重複しています: $($moment.lead_copy)" }
        }
        $checks.cta_strategy = 'pass'
    }
    catch { Add-ValidationError $_.Exception.Message }
}
elseif ($ValidationMode -eq 'parent') {
    Add-ValidationError '親完成検査にはExpectedCtaStrategyJsonが必要です。'
}

$currentCheck = 'emphasis'
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
            if ($item.role -isnot [string] -or $item.role -notin @('conclusion', 'condition', 'deadline', 'caution', 'action')) {
                throw '各強調項目には有効なroleが必要です。'
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

$currentCheck = 'internal_links'
if (-not [string]::IsNullOrWhiteSpace($ExpectedInternalLinkManifestJson)) {
    try {
        $internalLinkManifest = $ExpectedInternalLinkManifestJson | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $internalLinkManifest -or -not $internalLinkManifest.PSObject.Properties['new_links']) {
            throw '内部リンク期待マニフェストにはnew_links配列が必要です。'
        }
        $expectedInternalLinks = @($internalLinkManifest.new_links)
        foreach ($link in $expectedInternalLinks) {
            if ($null -eq $link -or $link.destination_role -isnot [string] -or $link.presentation -isnot [string] -or
                $link.href -isnot [string] -or [string]::IsNullOrWhiteSpace($link.href)) {
                throw '内部リンク期待マニフェストの各項目にはdestination_role、presentation、hrefが必要です。'
            }

            $isTextLink = $link.destination_role -ceq 'related_support' -and $link.presentation -ceq 'text_link'
            $isImageCard = $link.destination_role -ceq 'conversion_direct' -and $link.presentation -ceq 'image_card'
            if (-not ($isTextLink -or $isImageCard)) {
                throw '内部リンクのdestination_roleとpresentationの組み合わせが正しくありません。'
            }
            if ($isTextLink -and ($link.anchor_text -isnot [string] -or [string]::IsNullOrWhiteSpace($link.anchor_text))) {
                throw 'text_linkには空でないanchor_textが必要です。'
            }
            if ($isImageCard -and ($link.card_description -isnot [string] -or [string]::IsNullOrWhiteSpace($link.card_description))) {
                throw 'image_cardには空でないcard_descriptionが必要です。'
            }
        }
        if (@($expectedInternalLinks | Where-Object { $_.presentation -eq 'image_card' }).Count -gt 2) {
            throw '内部リンク期待マニフェストの画像付きカードが上限2件を超えています。'
        }
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'traffic') {
            $primaryConversionCards = @($expectedInternalLinks | Where-Object {
                $_.destination_role -ceq 'conversion_direct' -and
                $_.presentation -ceq 'image_card' -and
                $_.PSObject.Properties['required'] -and
                $_.required -eq $true -and
                $_.PSObject.Properties['primary_destination'] -and
                $_.primary_destination -eq $true
            })
            if ($primaryConversionCards.Count -ne 1) {
                throw "集客用記事にはrequired: trueかつprimary_destination: trueの主成約記事画像カードが1件必要です: $($primaryConversionCards.Count)"
            }
        }
    }
    catch { Add-ValidationError $_.Exception.Message }
}

if (-not [string]::IsNullOrWhiteSpace($ExpectedAffiliateLinkManifestJson)) {
    $currentCheck = 'affiliate'
    try {
        $affiliateLinkManifest = $ExpectedAffiliateLinkManifestJson | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $affiliateLinkManifest -or -not $affiliateLinkManifest.PSObject.Properties['links']) {
            throw 'アフィリエイト期待マニフェストにはlinks配列が必要です。'
        }
        $affiliateManifestLinks = @($affiliateLinkManifest.links)
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'conversion' -and $affiliateManifestLinks.Count -lt 1) {
            throw "親完成検査にはアフィリエイト期待マニフェストのlinksが1件以上必要です: $($affiliateManifestLinks.Count)"
        }
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'traffic' -and $affiliateManifestLinks.Count -ne 0) {
            throw "集客用記事のアフィリエイト期待マニフェストは空である必要があります: $($affiliateManifestLinks.Count)"
        }
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'conversion' -and $null -ne $plannedCtaCount -and $affiliateManifestLinks.Count -ne $plannedCtaCount) {
            throw "CTA戦略のplanned_countとアフィリエイト期待マニフェスト件数が一致しません: $plannedCtaCount / $($affiliateManifestLinks.Count)"
        }
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'traffic' -and $null -ne $plannedCtaCount -and $plannedCtaCount -ne 0) {
            throw "集客用記事のplanned_countは0である必要があります: $plannedCtaCount"
        }
        if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -eq 'conversion' -and $affiliateManifestLinks.Count -eq 1 -and
            ([string]::IsNullOrWhiteSpace($ExpectedAffiliateProvider) -or [string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse))) {
            throw '単独CTAの親完成検査にはExpectedAffiliateProviderとExpectedAffiliateCourseが必要です。'
        }
        $multiPlacementIds = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        $manifestLeadTexts = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        foreach ($link in $affiliateManifestLinks) {
            $expectedComponent = if ($link.provider -ceq 'smile_zemi') { 'smile_zemi_cta_v1' } elseif ($link.provider -ceq 'shinken_zemi') { 'shinken_zemi_cta_v1' } else { '' }
            if ($null -eq $link -or [string]::IsNullOrWhiteSpace($expectedComponent) -or
                ($affiliateManifestLinks.Count -eq 1 -and $link.provider -cne $effectiveAffiliateProvider) -or
                $link.presentation -cne 'cta_button' -or $link.component_id -cne $expectedComponent -or $link.target_course -isnot [string] -or
                $link.href -isnot [string] -or [string]::IsNullOrWhiteSpace($link.href) -or
                $link.tracking_image_src -isnot [string] -or [string]::IsNullOrWhiteSpace($link.tracking_image_src) -or
                $link.rel -cne 'nofollow') {
                throw 'アフィリエイト期待マニフェストには講座別のプロバイダー、部品、講座、href、計測画像、nofollowが必要です。'
            }
            if ($affiliateManifestLinks.Count -eq 1 -and -not [string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse) -and $link.target_course -cne $ExpectedAffiliateCourse) {
                throw "アフィリエイト期待マニフェストの対象講座がExpectedAffiliateCourseと一致しません: $ExpectedAffiliateCourse"
            }
            if ($link.placement_id -isnot [string] -or [string]::IsNullOrWhiteSpace($link.placement_id) -or
                $link.section_id -isnot [string] -or [string]::IsNullOrWhiteSpace($link.section_id) -or
                $link.section_heading -isnot [string] -or [string]::IsNullOrWhiteSpace($link.section_heading) -or
                -not $multiPlacementIds.Add($link.placement_id)) {
                throw 'CTAの各項目には重複しないplacement_id、section_id、実際のH2見出しが必要です。'
            }
            foreach ($field in @('lead_text', 'button_text', 'destination_text', 'reader_question', 'official_information_needed', 'destination_purpose')) {
                if (-not $link.PSObject.Properties[$field] -or $link.$field -isnot [string] -or [string]::IsNullOrWhiteSpace($link.$field)) {
                    throw "アフィリエイト期待マニフェストの各項目には空でない$fieldが必要です。"
                }
            }
            if (-not $manifestLeadTexts.Add($link.lead_text.Trim())) {
                throw "CTAのlead_textが重複しています: $($link.lead_text)"
            }
            if ($null -ne $ctaStrategy) {
                $matchingMoment = @($ctaStrategyMoments | Where-Object { $_.placement_id -ceq $link.placement_id })
                if ($matchingMoment.Count -ne 1 -or
                    $matchingMoment[0].section_id -cne $link.section_id -or
                    $matchingMoment[0].section_heading -cne $link.section_heading -or
                    $matchingMoment[0].reader_question -cne $link.reader_question -or
                    $matchingMoment[0].official_information_needed -cne $link.official_information_needed -or
                    $matchingMoment[0].destination_purpose -cne $link.destination_purpose -or
                    $matchingMoment[0].lead_copy -cne $link.lead_text) {
                    throw "CTA戦略と期待マニフェストの意味情報が一致しません: $($link.placement_id)"
                }
            }
        }
    }
    catch { Add-ValidationError $_.Exception.Message }
}

$expectedEmphasisCount = @($emphasisItems).Count
$expectedInternalLinkCount = @($expectedInternalLinks).Count
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

        $currentCheck = 'internal_links'
        $internalLinkCardCount = [regex]::Matches($body, '(?m)^\s*【内部リンクカード】\s*$').Count
        if ($internalLinkCardCount -gt 2) {
            Add-ValidationError "画像付き内部リンクカードが上限2件を超えています: $internalLinkCardCount"
        }
        if ($checks.internal_links -ne 'fail') { $checks.internal_links = 'pass' }

        $currentCheck = 'affiliate'
        $escapedAffiliateRootClass = [regex]::Escape($affiliateRootClass)
        $escapedAffiliateButtonClass = [regex]::Escape($affiliateButtonClass)
        $affiliatePattern = "(?is)<div\b[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$escapedAffiliateRootClass\b[^\x22\x27]*[\x22\x27][^>]*>"
        $affiliateMarkupCount = [regex]::Matches($body, $affiliatePattern).Count
        if ($ExpectedArticleBusinessPurpose -eq 'traffic') {
            $allAffiliateCtaPattern = '(?is)<div\b[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b(?:shinken-zemi-cta|smile-zemi-cta)\b[^\x22\x27]*[\x22\x27][^>]*>'
            $affiliateMarkupCount = [regex]::Matches($body, $allAffiliateCtaPattern).Count
        }
        if (-not [string]::IsNullOrWhiteSpace($ExpectedAffiliateDisposition)) {
            switch ($ExpectedAffiliateDisposition) {
                'eligible' {
                    if ($ValidationMode -eq 'parent' -and $affiliateManifestLinks.Count -gt 0) {
                        $allCtaPattern = '(?is)<div\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b(?:shinken-zemi-cta|smile-zemi-cta)\b[^\x22\x27]*[\x22\x27])[^>]*>.*?</div>'
                        $allCtaBlocks = @([regex]::Matches($body, $allCtaPattern))
                        $affiliateMarkupCount = $allCtaBlocks.Count
                        $sourceValid = $true
                        if ($affiliateMarkupCount -ne $affiliateManifestLinks.Count) {
                            Add-ValidationError "CTA実件数と承認済み配置件数が一致しません: $affiliateMarkupCount / $($affiliateManifestLinks.Count)"
                            $sourceValid = $false
                        }
                        $h2Sections = @([regex]::Matches($body, '(?m)^##[ \t]+(?<heading>[^\r\n]+?)\s*$'))
                        foreach ($expectedAffiliate in $affiliateManifestLinks) {
                            $rootClass = if ($expectedAffiliate.provider -ceq 'smile_zemi') { 'smile-zemi-cta' } else { 'shinken-zemi-cta' }
                            $buttonClass = if ($expectedAffiliate.provider -ceq 'smile_zemi') { 'smile-zemi-cta__button' } else { 'shinken-zemi-cta__button' }
                            $leadClass = if ($expectedAffiliate.provider -ceq 'smile_zemi') { 'smile-zemi-cta__lead' } else { 'shinken-zemi-cta__lead' }
                            $destinationClass = if ($expectedAffiliate.provider -ceq 'smile_zemi') { 'smile-zemi-cta__destination' } else { 'shinken-zemi-cta__destination' }
                            $placement = [regex]::Escape($expectedAffiliate.placement_id)
                            $classEscape = [regex]::Escape($rootClass)
                            $chosen = @($allCtaBlocks | Where-Object {
                                $opening = $_.Value.Substring(0, $_.Value.IndexOf('>') + 1)
                                $opening -match "(?is)\bclass\s*=\s*[\x22\x27][^\x22\x27]*\b$classEscape\b[^\x22\x27]*[\x22\x27]" -and
                                $opening -match "(?is)\bdata-placement-id\s*=\s*[\x22\x27]$placement[\x22\x27]"
                            })
                            if ($chosen.Count -ne 1) {
                                Add-ValidationError "配置IDに対応するCTAは1件必要です: $($expectedAffiliate.placement_id) / $($chosen.Count)"
                                $sourceValid = $false
                                continue
                            }
                            $block = $chosen[0]
                            $ctaBlock = $block.Value
                            $opening = $ctaBlock.Substring(0, $ctaBlock.IndexOf('>') + 1)
                            $course = [regex]::Escape($expectedAffiliate.target_course)
                            if ($opening -notmatch "(?is)\bdata-course\s*=\s*[\x22\x27]$course[\x22\x27]") {
                                Add-ValidationError "配置IDの対象講座が一致しません: $($expectedAffiliate.placement_id)"
                                $sourceValid = $false
                            }
                            $buttonEscape = [regex]::Escape($buttonClass)
                            $buttonTag = [regex]::Match($ctaBlock, "(?is)<a\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$buttonEscape\b[^\x22\x27]*[\x22\x27])[^>]*>")
                            $hrefMatch = if ($buttonTag.Success) { [regex]::Match($buttonTag.Value, '(?is)\bhref\s*=\s*[\x22\x27](?<href>[^\x22\x27]+)[\x22\x27]') } else { $null }
                            if ($null -eq $hrefMatch -or -not $hrefMatch.Success -or -not (Test-ExactHref $expectedAffiliate.href $hrefMatch.Groups['href'].Value) -or
                                $buttonTag.Value -notmatch '(?is)\brel\s*=\s*[\x22\x27][^\x22\x27]*\bnofollow\b[^\x22\x27]*[\x22\x27]') {
                                Add-ValidationError "配置IDのリンクURL・nofollowが一致しません: $($expectedAffiliate.placement_id)"
                                $sourceValid = $false
                            }
                            $trackingFound = $false
                            foreach ($image in @([regex]::Matches($ctaBlock, '(?is)<img\b[^>]*>'))) {
                                $src = [regex]::Match($image.Value, '(?is)\bsrc\s*=\s*[\x22\x27](?<src>[^\x22\x27]+)[\x22\x27]')
                                if ($src.Success -and (Test-ExactHref $expectedAffiliate.tracking_image_src $src.Groups['src'].Value)) {
                                    $trackingFound = $image.Value -match '(?is)\bheight\s*=\s*[\x22\x27]1[\x22\x27]' -and
                                        $image.Value -match '(?is)\bwidth\s*=\s*[\x22\x27]1[\x22\x27]' -and
                                        $image.Value -match '(?is)\bborder\s*=\s*[\x22\x27]0[\x22\x27]'
                                    break
                                }
                            }
                            if (-not $trackingFound) {
                                Add-ValidationError "配置IDの計測画像・固定属性が一致しません: $($expectedAffiliate.placement_id)"
                                $sourceValid = $false
                            }
                            $leadEscape = [regex]::Escape($leadClass)
                            $destinationEscape = [regex]::Escape($destinationClass)
                            $leadElement = [regex]::Match($ctaBlock, "(?is)<p\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$leadEscape\b[^\x22\x27]*[\x22\x27])[^>]*>(?<text>.*?)</p>")
                            $buttonElement = [regex]::Match($ctaBlock, "(?is)<a\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$buttonEscape\b[^\x22\x27]*[\x22\x27])[^>]*>(?<text>.*?)</a>")
                            $destinationElement = [regex]::Match($ctaBlock, "(?is)<p\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$destinationEscape\b[^\x22\x27]*[\x22\x27])[^>]*>(?<text>.*?)</p>")
                            if (-not $leadElement.Success -or (ConvertTo-NormalizedText $leadElement.Groups['text'].Value) -cne (ConvertTo-NormalizedText $expectedAffiliate.lead_text) -or
                                -not $buttonElement.Success -or (ConvertTo-NormalizedText $buttonElement.Groups['text'].Value) -cne (ConvertTo-NormalizedText $expectedAffiliate.button_text) -or
                                -not $destinationElement.Success -or (ConvertTo-NormalizedText $destinationElement.Groups['text'].Value) -cne (ConvertTo-NormalizedText $expectedAffiliate.destination_text)) {
                                Add-ValidationError "配置IDの表示文が期待マニフェストと一致しません: $($expectedAffiliate.placement_id)"
                                $sourceValid = $false
                            }
                            $section = @($h2Sections | Where-Object { $_.Groups['heading'].Value.Trim() -ceq $expectedAffiliate.section_heading })
                            if ($section.Count -ne 1) {
                                Add-ValidationError "配置先H2を一意に確認できません: $($expectedAffiliate.section_heading)"
                                $sourceValid = $false
                            }
                            else {
                                $sectionStart = $section[0].Index + $section[0].Length
                                $nextSection = @($h2Sections | Where-Object { $_.Index -gt $section[0].Index } | Select-Object -First 1)
                                $sectionEnd = if ($nextSection.Count -eq 0) { $body.Length } else { $nextSection[0].Index }
                                if ($block.Index -lt $sectionStart -or $block.Index -ge $sectionEnd) {
                                    Add-ValidationError "CTAが計画したH2内にありません: $($expectedAffiliate.placement_id)"
                                    $sourceValid = $false
                                }
                            }
                        }
                        $affiliateSourceVerified = if ($sourceValid) { 'pass' } else { 'fail' }
                    }
                    else {
                    if ($affiliateMarkupCount -ne 1) {
                        Add-ValidationError "affiliate.dispositionがeligibleですが、$affiliateLabel CTA数が1件ではありません: $affiliateMarkupCount"
                    }
                    if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse)) {
                        Add-ValidationError 'affiliate.dispositionがeligibleの場合はExpectedAffiliateCourseが必要です。'
                    }
                    else {
                        $escapedCourse = [regex]::Escape($ExpectedAffiliateCourse)
                        $coursePattern = "(?is)<div\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$escapedAffiliateRootClass\b[^\x22\x27]*[\x22\x27])(?=[^>]*data-course\s*=\s*[\x22\x27]$escapedCourse[\x22\x27])[^>]*>"
                        if ($body -notmatch $coursePattern) {
                            Add-ValidationError "$affiliateLabel CTAのdata-courseが期待講座と一致しません: $ExpectedAffiliateCourse"
                        }
                    }
                    if ($ValidationMode -eq 'parent' -and $affiliateManifestLinks.Count -eq 1) {
                        $expectedAffiliate = $affiliateManifestLinks[0]
                        $sourceValid = $true
                        $ctaBlockPattern = "(?is)<div\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$escapedAffiliateRootClass\b[^\x22\x27]*[\x22\x27])[^>]*>.*?</div>"
                        $ctaBlocks = @([regex]::Matches($body, $ctaBlockPattern))
                        if ($ctaBlocks.Count -ne 1) {
                            Add-ValidationError "アフィリエイトCTAの固定DOMブロック数が1件ではありません: $($ctaBlocks.Count)"
                            $sourceValid = $false
                        }
                        else {
                            $ctaBlock = $ctaBlocks[0].Value
                            $buttonTagPattern = "(?is)<a\b(?=[^>]*class\s*=\s*[\x22\x27][^\x22\x27]*\b$escapedAffiliateButtonClass\b[^\x22\x27]*[\x22\x27])[^>]*>"
                            $buttonTag = [regex]::Match($ctaBlock, $buttonTagPattern)
                            $buttonHrefMatch = if ($buttonTag.Success) { [regex]::Match($buttonTag.Value, "(?is)\bhref\s*=\s*[\x22\x27](?<href>[^\x22\x27]+)[\x22\x27]") } else { $null }
                            if ($null -eq $buttonHrefMatch -or -not $buttonHrefMatch.Success -or -not (Test-ExactHref $expectedAffiliate.href $buttonHrefMatch.Groups['href'].Value)) {
                                Add-ValidationError 'アフィリエイトCTAに期待マニフェストのhrefを持つボタンリンクがありません。'
                                $sourceValid = $false
                            }
                            if ($buttonTag.Success -and $buttonTag.Value -notmatch '(?is)\brel\s*=\s*[\x22\x27][^\x22\x27]*\bnofollow\b[^\x22\x27]*[\x22\x27]') {
                                Add-ValidationError 'アフィリエイトCTAボタンにrel="nofollow"がありません。'
                                $sourceValid = $false
                            }

                            $trackingImageFound = $false
                            foreach ($imageTag in @([regex]::Matches($ctaBlock, '(?is)<img\b[^>]*>'))) {
                                $srcMatch = [regex]::Match($imageTag.Value, "(?is)\bsrc\s*=\s*[\x22\x27](?<src>[^\x22\x27]+)[\x22\x27]")
                                if ($srcMatch.Success -and (Test-ExactHref $expectedAffiliate.tracking_image_src $srcMatch.Groups['src'].Value)) {
                                    $trackingImageFound = $true
                                    if ($imageTag.Value -notmatch '(?is)\bheight\s*=\s*[\x22\x27]1[\x22\x27]' -or
                                        $imageTag.Value -notmatch '(?is)\bwidth\s*=\s*[\x22\x27]1[\x22\x27]' -or
                                        $imageTag.Value -notmatch '(?is)\bborder\s*=\s*[\x22\x27]0[\x22\x27]') {
                                        Add-ValidationError 'アフィリエイトCTAの計測画像に固定の1px属性がありません。'
                                        $sourceValid = $false
                                    }
                                    break
                                }
                            }
                            if (-not $trackingImageFound) {
                                Add-ValidationError 'アフィリエイトCTAに期待マニフェストの計測画像がありません。'
                                $sourceValid = $false
                            }
                        }
                        $affiliateSourceVerified = if ($sourceValid) { 'pass' } else { 'fail' }
                    }
                    }
                }
                'not_applicable' {
                    if ($ValidationMode -eq 'parent' -and $ExpectedArticleBusinessPurpose -ne 'traffic') {
                        Add-ValidationError '成約用記事はアフィリエイトCTA必須のため、not_applicableでは合格にできません。'
                    }
                    if ($affiliateMarkupCount -ne 0) {
                        Add-ValidationError "affiliate.dispositionがnot_applicableですが、アフィリエイトCTAがあります: $affiliateMarkupCount"
                    }
                    if ($ExpectedArticleBusinessPurpose -eq 'traffic' -and $body -match '(?i)(?:ck\.jp\.ap\.valuecommerce\.com/servlet/referral|ad\.jp\.ap\.valuecommerce\.com/servlet/gifbanner|px\.a8\.net/svt/ejp|www\d+\.a8\.net/0\.gif)') {
                        Add-ValidationError '集客用記事にアフィリエイトURLまたは計測画像URLが混入しています。'
                    }
                }
                'deferred' {
                    if ($ValidationMode -eq 'parent') {
                        Add-ValidationError '親完成検査では事業目的ごとにeligibleまたはnot_applicableを確定する必要があり、deferredでは合格にできません。'
                    }
                    if ($affiliateMarkupCount -ne 0) {
                        Add-ValidationError "affiliate.dispositionがdeferredですが、$affiliateLabel CTAがあります: $affiliateMarkupCount"
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
  const textLinks = [];
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
    if (node.tagName === 'a') {
      const href = String((node.properties || {}).href || '');
      textLinks.push({ href, text: normalize(text(node)), section_id: current });
    }
    for (const child of node.children || []) walk(child);
  };
  walk(tree);
  const items = JSON.parse(input.items_json).map(item => {
    const section = sections.get(item.section_id);
    const texts = item.section_id === 'any' ? all : section?.strong;
    const headingMatch = item.heading_text === undefined || (section && section.heading === normalize(item.heading_text));
    const exactText = normalize(item.exact_text);
    const conclusionTextIsHeading = item.role === 'conclusion' && section && exactText === section.heading;
    const pass = !!texts && headingMatch && !conclusionTextIsHeading && texts.includes(exactText);
    return { section_id: item.section_id, exact_text: item.exact_text, status: pass ? 'pass' : 'fail',
      reason: pass ? null : !texts ? 'section_not_found' : !headingMatch ? 'heading_mismatch' : conclusionTextIsHeading ? 'heading_is_not_conclusion_phrase' : 'strong_not_found_in_section' };
  });
  const heading_coverage = [...sections.entries()]
    .filter(([section_id]) => section_id.startsWith('H2-') || section_id.startsWith('H3-'))
    .map(([section_id, section]) => ({
      section_id,
      heading: section.heading,
      conclusion_item_count: JSON.parse(input.items_json).filter(item => item.section_id === section_id && item.role === 'conclusion').length
    }));
  const result = { parser: 'satteri', article_sha256: crypto.createHash('sha256').update(bytes).digest('hex'), items, heading_coverage, text_links: textLinks };
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
            $parsedMarkup = $parsed
            $emphasisResults = @($parsed.items)
            foreach ($item in $emphasisResults) {
                if ($item.status -eq 'pass') { $matchedEmphasisCount++ }
                else { Add-ValidationError "指定章の太字が一致しません: $($item.section_id) / $($item.exact_text) / $($item.reason)" }
            }
            foreach ($coverage in @($parsed.heading_coverage)) {
                if ($coverage.conclusion_item_count -lt 1) {
                    Add-ValidationError "見出しの結論を示す強調計画がありません: $($coverage.section_id) / $($coverage.heading)"
                }
            }
            if ($emphasisResults.Count -ne $emphasisItems.Count) { Add-ValidationError '強調項目の検査件数が一致しません。' }
            if ($checks.emphasis -ne 'fail') { $checks.emphasis = 'pass' }
        }

        $currentCheck = 'internal_links'
        if ($ValidationMode -eq 'parent') {
            if ($null -eq $parsedMarkup) {
                Add-ValidationError '内部リンク期待マニフェストを照合するためのMarkdown解析結果がありません。'
            }
            else {
                $cardPattern = '(?m)^\s*【内部リンクカード】\s*\r?\n\s*URL:\s*(?<href>[^\r\n]+)\s*\r?\n\s*紹介文:\s*(?<description>[^\r\n]+)\s*$'
                $cardRecords = @([regex]::Matches($body, $cardPattern) | ForEach-Object {
                    [pscustomobject]@{
                        href = ConvertTo-NormalizedHref $_.Groups['href'].Value
                        description = ConvertTo-NormalizedText $_.Groups['description'].Value
                    }
                })
                $expectedImageCardCount = @($expectedInternalLinks | Where-Object { $_.presentation -eq 'image_card' }).Count
                if ($internalLinkCardCount -ne $expectedImageCardCount) {
                    Add-ValidationError "画像付き内部リンクカード数が期待マニフェストと一致しません: 期待値 $expectedImageCardCount / 実値 $internalLinkCardCount"
                }

                foreach ($link in $expectedInternalLinks) {
                    $matched = $false
                    if ($link.presentation -eq 'text_link') {
                        $expectedAnchor = ConvertTo-NormalizedText $link.anchor_text
                        foreach ($actualLink in @($parsedMarkup.text_links)) {
                            if ((Test-ExpectedInternalHref $link.href $actualLink.href) -and (ConvertTo-NormalizedText $actualLink.text) -ceq $expectedAnchor) {
                                $matched = $true
                                break
                            }
                        }
                    }
                    else {
                        $expectedDescription = ConvertTo-NormalizedText $link.card_description
                        foreach ($card in $cardRecords) {
                            if ((Test-ExpectedInternalHref $link.href $card.href) -and $card.description -ceq $expectedDescription) {
                                $matched = $true
                                break
                            }
                        }
                    }

                    $internalLinkResults += [pscustomobject]@{
                        href = $link.href
                        destination_role = $link.destination_role
                        presentation = $link.presentation
                        required = ($link.PSObject.Properties['required'] -and $link.required -eq $true)
                        primary_destination = ($link.PSObject.Properties['primary_destination'] -and $link.primary_destination -eq $true)
                        status = if ($matched) { 'pass' } else { 'fail' }
                    }
                    if ($matched) { $matchedInternalLinkCount++ }
                    else { Add-ValidationError "期待マニフェストの内部リンクが本文にありません、または表示形式が一致しません: $($link.href) / $($link.presentation)" }
                }
            }
        }
        if ($checks.internal_links -ne 'fail') { $checks.internal_links = 'pass' }

        $currentCheck = 'external_links'
        if ($ExternalLinkPolicy -ne 'allow_task_required_only') {
            Add-ValidationError '外部リンク検査は省略できません。ExternalLinkPolicyはallow_task_required_onlyを使用してください。'
        }
        $externalApprovals = @($AllowedExternalApprovalJson | ConvertFrom-Json -ErrorAction Stop)
        $approvalHrefs = @($externalApprovals | ForEach-Object { ConvertTo-NormalizedHref $_.href })
        foreach ($href in $AllowedExternalHref) {
            if ((ConvertTo-NormalizedHref $href) -cnotin $approvalHrefs) {
                Add-ValidationError "外部URLの許可原文・発言出典がありません: $href"
            }
        }
        $linkAuditInput = [ordered]@{
            project_root = $resolvedProjectRoot
            article_path = $resolvedArticlePath
            affiliate_manifest = @{ links = @($affiliateManifestLinks) }
            allowed_external_links = @($externalApprovals)
        }
        if (-not [string]::IsNullOrWhiteSpace($RenderedHtmlPath)) { $linkAuditInput.rendered_html_path = $RenderedHtmlPath }
        $linkAuditJson = $linkAuditInput | ConvertTo-Json -Depth 30 -Compress
        $linkAuditOutput = $linkAuditJson | & node (Join-Path $PSScriptRoot 'audit-article-links.mjs')
        $linkAuditExitCode = $LASTEXITCODE
        $externalLinkAudit = ($linkAuditOutput -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
        if ($externalLinkAudit.article_sha256 -cne $articleSha256) {
            Add-ValidationError 'リンク検査の対象記事ハッシュが一致しません。'
        }
        foreach ($violation in @($externalLinkAudit.violations)) {
            if ($null -ne $violation) {
                $disallowedExternalLinks.Add($violation.href)
                Add-ValidationError "許可されていない外部誘導があります: $($violation.phase) / $($violation.href)"
            }
        }
        if ($linkAuditExitCode -ne 0 -or $externalLinkAudit.status -ne 'PASS') {
            Add-ValidationError "本文リンク検査が不合格です: $($externalLinkAudit.error)"
        }
        if ($checks.external_links -ne 'fail') { $checks.external_links = 'pass' }
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
    article_business_purpose = if ([string]::IsNullOrWhiteSpace($ExpectedArticleBusinessPurpose)) { 'not_checked' } else { $ExpectedArticleBusinessPurpose }
    article_profile_type = if ($null -eq $articleProfile) { 'not_checked' } else { $articleProfile.type }
    review_evidence_applicability = if ($null -eq $reviewEvidencePlan) { 'not_checked' } else { $reviewEvidencePlan.applicability }
    price_evidence_applicability = if ($null -eq $priceEvidencePlan) { 'not_checked' } else { $priceEvidencePlan.applicability }
    cta_default_count = if ($null -eq $ctaStrategy) { $null } else { $ctaStrategy.default_count }
    cta_planned_count = $plannedCtaCount
    cta_confirmation_moment_count = @($ctaStrategyMoments).Count
    parent_contract_pass = ($ValidationMode -eq 'parent' -and $errors.Count -eq 0)
    article_sha256 = $articleSha256
    checks = $checks
    rendered_emphasis = 'not_checked'
    emphasis_items = @($emphasisResults)
    article_path = if ($resolvedArticlePath) { $resolvedArticlePath } else { $ArticlePath }
    actual_title = $actualTitle
    title_contract_match = $titleContractMatch
    affiliate_disposition = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateDisposition)) { 'not_checked' } else { $ExpectedAffiliateDisposition }
    expected_affiliate_provider = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateProvider)) { $null } else { $ExpectedAffiliateProvider }
    expected_affiliate_course = if ([string]::IsNullOrWhiteSpace($ExpectedAffiliateCourse)) { $null } else { $ExpectedAffiliateCourse }
    affiliate_markup_count = $affiliateMarkupCount
    affiliate_manifest_link_count = @($affiliateManifestLinks).Count
    affiliate_source_verification = $affiliateSourceVerified
    internal_link_card_count = $internalLinkCardCount
    expected_internal_link_count = $expectedInternalLinkCount
    matched_internal_link_count = $matchedInternalLinkCount
    internal_link_items = @($internalLinkResults)
    external_link_policy = $ExternalLinkPolicy
    disallowed_external_link_count = $disallowedExternalLinks.Count
    disallowed_external_links = @($disallowedExternalLinks)
    external_link_audit = $externalLinkAudit
    expected_emphasis_count = $expectedEmphasisCount
    matched_emphasis_count = $matchedEmphasisCount
    errors = @($errors)
    warnings = @($warnings)
}

$result | ConvertTo-Json -Depth 4
if ($errors.Count -gt 0) { exit 1 }
