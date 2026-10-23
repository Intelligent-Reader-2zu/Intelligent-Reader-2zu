param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\samples\open-authored-substitutes')
)

$ErrorActionPreference = 'Stop'
$today = Get-Date -Format 'yyyy-MM-dd'
$sources = @(
    @{ id = 'AUTH-005'; file = 'AUTH-005-substitute-nist-csf-2.0.pdf'; url = 'https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf'; format = 'PDF text'; license = 'NIST public document; verify item terms'; features = @('policy sections', 'numbered categories', 'tables', 'appendix', 'references') },
    @{ id = 'AUTH-006'; file = 'AUTH-006-substitute-webdriver2.html'; url = 'https://www.w3.org/TR/webdriver2/'; format = 'HTML snapshot'; license = 'W3C document license; verify current notice'; features = @('navigation', 'headings', 'algorithms', 'code', 'links', 'tables') }
)

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$records = @()
foreach ($source in $sources) {
    $target = Join-Path $OutputRoot $source.file
    $temporary = "$target.download"
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    Invoke-WebRequest -Uri $source.url -OutFile $temporary -MaximumRedirection 8 -UseBasicParsing
    Move-Item -LiteralPath $temporary -Destination $target -Force
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
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    }
}

[ordered]@{
    manifest_version = 1
    retrieved_on = $today
    purpose = 'substitute documents for missing AUTH-005 and AUTH-006 slots'
    samples = $records
    notes = @(
        'AUTH-005 and AUTH-006 are open-source substitutes, not explicitly authorized real materials.',
        'Do not merge these entries into the authorized-material count without confirming the intended scope.',
        'Publicly reachable does not automatically mean cloud-uploadable.'
    )
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'auth-substitute-manifest.json') -Encoding UTF8

Write-Output ("Manifest written: {0}" -f (Join-Path $OutputRoot 'auth-substitute-manifest.json'))
