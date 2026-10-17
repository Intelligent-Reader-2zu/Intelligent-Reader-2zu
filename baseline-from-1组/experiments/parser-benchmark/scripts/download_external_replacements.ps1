param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\samples\external-replacements'),
    [int64]$MaxBytes = 62914560
)

$ErrorActionPreference = 'Stop'
$today = Get-Date -Format 'yyyy-MM-dd'

# These are deliberate substitutes for the unresolved external slots. They preserve
# useful parser risks while avoiding guessed mirrors and unverified public-domain claims.
$sources = @(
    @{ id = 'SUB-OPEN-001'; replacement_for = 'OPEN-001'; file = 'openstax-biology-intro.html'; url = 'https://openstax.org/books/biology-2e/pages/1-introduction'; format = 'HTML snapshot'; license = 'OpenStax CC BY-NC-SA notice; verify page terms'; features = @('headings', 'figures', 'links', 'navigation', 'mixed content') },
    @{ id = 'SUB-OPEN-002'; replacement_for = 'OPEN-002'; file = 'openstax-psychology-intro.html'; url = 'https://openstax.org/books/psychology-2e/pages/1-introduction'; format = 'HTML snapshot'; license = 'OpenStax CC BY-NC-SA notice; verify page terms'; features = @('headings', 'figures', 'links', 'navigation', 'mixed content') },
    @{ id = 'SUB-OPEN-005'; replacement_for = 'OPEN-005'; file = 'w3c-webauthn-2.html'; url = 'https://www.w3.org/TR/webauthn-2/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('headings', 'code', 'lists', 'links', 'algorithms') },
    @{ id = 'SUB-OPEN-006'; replacement_for = 'OPEN-006'; file = 'w3c-dom.html'; url = 'https://www.w3.org/TR/dom/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('headings', 'code', 'lists', 'anchors', 'references') },
    @{ id = 'SUB-OPEN-007'; replacement_for = 'OPEN-007'; file = 'owasp-top-10-2021.html'; url = 'https://owasp.org/Top10/2021/'; format = 'HTML snapshot'; license = 'OWASP project page; verify document notice'; features = @('headings', 'lists', 'links', 'navigation', 'tables') },
    @{ id = 'SUB-OPEN-012'; replacement_for = 'OPEN-012'; file = 'rfc-9457.html'; url = 'https://datatracker.ietf.org/doc/html/rfc9457'; format = 'HTML snapshot'; license = 'IETF RFC Trust legal notice; verify redistribution terms'; features = @('headings', 'lists', 'code', 'references', 'anchors') },
    @{ id = 'SUB-PD-001'; replacement_for = 'PD-001'; file = 'nist-sp-800-171r3.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r3.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('long report', 'headings', 'tables', 'appendix', 'references') },
    @{ id = 'SUB-PD-002'; replacement_for = 'PD-002'; file = 'nist-sp-800-218.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('headings', 'tables', 'numbered practices', 'appendix') },
    @{ id = 'SUB-PD-003'; replacement_for = 'PD-003'; file = 'nist-sp-800-61r3.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('long report', 'headings', 'tables', 'references') },
    @{ id = 'SUB-PD-004'; replacement_for = 'PD-004'; file = 'w3c-css-text-3.html'; url = 'https://www.w3.org/TR/css-text-3/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('headings', 'algorithms', 'definitions', 'tables', 'references') },
    @{ id = 'SUB-PD-005'; replacement_for = 'PD-005'; file = 'w3c-svg2.html'; url = 'https://www.w3.org/TR/SVG2/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('headings', 'code', 'figures', 'links', 'references') },
    @{ id = 'SUB-PD-006'; replacement_for = 'PD-006'; file = 'w3c-png.html'; url = 'https://www.w3.org/TR/PNG/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('headings', 'tables', 'figures', 'definitions', 'references') }
)

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$records = @()
$skipped = @()
$manifestPath = Join-Path $OutputRoot 'external-replacement-manifest.json'
$priorSamples = @{}
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $prior = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        foreach ($priorSample in @($prior.samples)) {
            if ($priorSample.sample_id) { $priorSamples[$priorSample.sample_id] = $priorSample }
        }
    } catch {
        Write-Warning "Could not read prior replacement manifest: $($_.Exception.Message)"
    }
}

foreach ($source in $sources) {
    $target = Join-Path $OutputRoot $source.file
    $temporary = "$target.download"
    try {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        Invoke-WebRequest -Uri $source.url -OutFile $temporary -MaximumRedirection 8 -UseBasicParsing
        $bytes = (Get-Item -LiteralPath $temporary).Length
        if ($bytes -gt $MaxBytes) {
            $skipped += [ordered]@{ id = $source.id; replacement_for = $source.replacement_for; reason = "downloaded size $bytes exceeds MaxBytes $MaxBytes"; url = $source.url }
            Remove-Item -LiteralPath $temporary -Force
            continue
        }
        Move-Item -LiteralPath $temporary -Destination $target -Force
        $records += [ordered]@{
            sample_id = $source.id
            replacement_for = $source.replacement_for
            filename = $source.file
            path = (Resolve-Path -LiteralPath $target).Path
            source_url = $source.url
            retrieved_on = $today
            format = $source.format
            license_or_authorization = $source.license
            cloud_upload_allowed = 'unknown'
            expected_layout_features = $source.features
            bytes = $bytes
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
        }
        Write-Output ("DOWNLOADED {0} -> {1}" -f $source.id, $source.file)
    } catch {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        $retained = $false
        if ((Test-Path -LiteralPath $target -PathType Leaf) -and $priorSamples.ContainsKey($source.id)) {
            $records += $priorSamples[$source.id]
            $retained = $true
            Write-Warning ("RETAINED {0} from prior manifest after refresh failure" -f $source.id)
        }
        if (-not $retained) {
            $skipped += [ordered]@{ id = $source.id; replacement_for = $source.replacement_for; reason = $_.Exception.Message; url = $source.url }
        }
        Write-Warning ("SKIPPED {0}: {1}" -f $source.id, $_.Exception.Message)
    }
}

[ordered]@{
    manifest_version = 1
    retrieved_on = $today
    purpose = 'simple substitutes for unresolved external parser-benchmark slots'
    samples = $records
    skipped = $skipped
    notes = @(
        'These are substitutes, not claims that the original public-domain or exact-format slot was fulfilled.',
        'Publicly reachable does not automatically mean redistributable or cloud-uploadable.',
        'Keep cloud_upload_allowed=unknown until item-level terms and service policy are reviewed.'
    )
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'external-replacement-manifest.json') -Encoding UTF8

Write-Output ("Manifest written: {0}" -f (Join-Path $OutputRoot 'external-replacement-manifest.json'))
