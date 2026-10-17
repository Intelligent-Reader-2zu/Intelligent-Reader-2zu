param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\samples\external-candidates'),
    [int64]$MaxBytes = 62914560
)

$ErrorActionPreference = 'Stop'
$today = Get-Date -Format 'yyyy-MM-dd'

$sources = @(
    @{ id = 'OPEN-003'; file = 'nist-sp-800-63b.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-63b.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('technical report', 'headings', 'tables', 'footnotes') },
    @{ id = 'OPEN-004'; file = 'w3c-html52.html'; url = 'https://www.w3.org/TR/html52/'; format = 'HTML'; license = 'W3C document license; verify current notice'; features = @('headings', 'code', 'lists', 'links', 'navigation') },
    @{ id = 'OPEN-005'; file = 'rfc-9110.txt'; url = 'https://www.rfc-editor.org/rfc/rfc9110.txt'; format = 'TXT'; license = 'RFC Trust legal notice; verify redistribution terms'; features = @('fixed-width text', 'long lines', 'numbered sections', 'references') },
    @{ id = 'OPEN-006'; file = 'rfc-9110.pdf'; url = 'https://www.rfc-editor.org/rfc/pdfrfc/rfc9110.pdf'; format = 'PDF text'; license = 'RFC Trust legal notice; verify redistribution terms'; features = @('headings', 'code', 'tables', 'references', 'page numbers') },
    @{ id = 'OPEN-007'; file = 'owasp-top-10-2021.pdf'; url = 'https://owasp.org/www-project-top-ten/assets/OWASP_Top_10-2021.pdf'; format = 'PDF text'; license = 'OWASP project license; verify document notice'; features = @('multi-column', 'tables', 'figures', 'headings', 'footnotes') },
    @{ id = 'OPEN-008'; file = 'nist-ai-rmf-100-1.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('long report', 'headings', 'tables', 'appendix', 'references') },
    @{ id = 'OPEN-009'; file = 'nist-sp-800-53r5.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf'; format = 'PDF text'; license = 'US government publication; verify item terms'; features = @('long report', 'tables', 'numbered controls', 'appendix') },
    @{ id = 'OPEN-010'; file = 'docling-technical-report.pdf'; url = 'https://arxiv.org/pdf/2408.09869.pdf'; format = 'PDF text'; license = 'arXiv item license must be recorded'; features = @('two-column', 'figures', 'tables', 'references', 'formula') },
    @{ id = 'OPEN-011'; file = 'layoutlmv3.pdf'; url = 'https://arxiv.org/pdf/2204.08387.pdf'; format = 'PDF text'; license = 'arXiv item license must be recorded'; features = @('two-column', 'figures', 'tables', 'formula', 'references') },
    @{ id = 'OPEN-012'; file = 'rfc-9457.pdf'; url = 'https://www.rfc-editor.org/rfc/pdfrfc/rfc9457.pdf'; format = 'PDF text'; license = 'RFC Trust legal notice; verify redistribution terms'; features = @('headings', 'code', 'references', 'page numbers') },
    @{ id = 'WEB-001'; file = 'w3c-webauthn-3.html'; url = 'https://www.w3.org/TR/webauthn-3/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('navigation', 'headings', 'code', 'links', 'tables') },
    @{ id = 'WEB-002'; file = 'rfc-9110.html'; url = 'https://www.rfc-editor.org/rfc/rfc9110.html'; format = 'HTML snapshot'; license = 'RFC Trust legal notice; verify redistribution terms'; features = @('anchors', 'headings', 'code', 'references') },
    @{ id = 'WEB-003'; file = 'nist-ai-rmf.html'; url = 'https://www.nist.gov/itl/ai-risk-management-framework'; format = 'HTML snapshot'; license = 'NIST website terms; verify page-specific notice'; features = @('navigation', 'article', 'links', 'metadata') },
    @{ id = 'WEB-004'; file = 'openstax-anatomy-intro.html'; url = 'https://openstax.org/books/anatomy-and-physiology-2e/pages/1-introduction'; format = 'HTML snapshot'; license = 'OpenStax CC BY-NC-SA notice; verify page terms'; features = @('headings', 'figures', 'links', 'navigation', 'mixed content') },
    @{ id = 'PD-001'; file = 'official-history-stafford.pdf'; url = 'https://archive.org/download/officialhistory00stafgoog/officialhistory00stafgoog.pdf'; format = 'PDF scan'; license = 'Internet Archive item marked public domain; verify item metadata'; features = @('scan', 'old typography', 'page numbers', 'multi-page') }
)

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$records = @()
$skipped = @()
$manifestPath = Join-Path $OutputRoot 'external-candidate-manifest.json'
$priorSamples = @{}
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $prior = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        foreach ($priorSample in @($prior.samples)) {
            if ($priorSample.sample_id) { $priorSamples[$priorSample.sample_id] = $priorSample }
        }
    } catch {
        Write-Warning "Could not read prior manifest: $($_.Exception.Message)"
    }
}

foreach ($source in $sources) {
    $target = Join-Path $OutputRoot $source.file
    $temporary = "$target.download"
    try {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        Invoke-WebRequest -Uri $source.url -OutFile $temporary -MaximumRedirection 8 -UseBasicParsing
        $downloadedBytes = (Get-Item -LiteralPath $temporary).Length
        if ($downloadedBytes -gt $MaxBytes) {
            $skipped += [ordered]@{ id = $source.id; reason = "downloaded size $downloadedBytes exceeds MaxBytes $MaxBytes"; url = $source.url }
            Remove-Item -LiteralPath $temporary -Force
            continue
        }
        Move-Item -LiteralPath $temporary -Destination $target -Force
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
        $records += [ordered]@{
            sample_id = $source.id
            filename = $source.file
            path = (Resolve-Path -LiteralPath $target).Path
            source_url = $source.url
            retrieved_on = $today
            format = $source.format
            license_or_authorization = $source.license
            cloud_upload_allowed = 'unknown'
            expected_layout_features = $source.features
            bytes = (Get-Item -LiteralPath $target).Length
            sha256 = $hash
        }
        Write-Output ("DOWNLOADED {0} {1}" -f $source.id, $source.file)
    } catch {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        if (Test-Path -LiteralPath $target) {
            if ($priorSamples.ContainsKey($source.id)) {
                $records += $priorSamples[$source.id]
                Write-Warning ("RETAINED {0} from prior manifest after refresh failure" -f $source.id)
            }
        }
        $skipped += [ordered]@{ id = $source.id; reason = $_.Exception.Message; url = $source.url }
        Write-Warning ("SKIPPED {0}: {1}" -f $source.id, $_.Exception.Message)
    }
}

$manifest = [ordered]@{
    manifest_version = 1
    retrieved_on = $today
    purpose = 'candidate documents for local parser benchmark; license review remains required'
    max_bytes = $MaxBytes
    samples = $records
    skipped = $skipped
    notes = @(
    'Publicly reachable does not automatically mean redistributable or cloud-uploadable.',
    'Keep cloud_upload_allowed=unknown until the item-level license and service policy are reviewed.',
    'OpenStax full-book PDFs were deliberately excluded by size; prefer chapter-level HTML or a locally clipped copy after license review.',
    'PD-002 through PD-006 remain unattempted until exact item identifiers and item-level rights pages are verified; do not fill them with guessed mirrors.',
    'OPEN-005, OPEN-006, OPEN-007 and OPEN-012 need official replacement URLs before download; current failures are retained for auditability.'
)
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'external-candidate-manifest.json') -Encoding UTF8
Write-Output ("Manifest written: {0}" -f (Join-Path $OutputRoot 'external-candidate-manifest.json'))
