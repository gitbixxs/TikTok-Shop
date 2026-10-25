[CmdletBinding()]
param(
    [string]$BaseUrl = $env:BASEROW_BASE_URL,
    [string]$Email = $env:BASEROW_EMAIL,
    [string]$Password = $env:BASEROW_PASSWORD,
    [string]$JwtToken = $env:BASEROW_JWTTOKEN,
    [int]$DatabaseId = 128,
    [string]$SchemaPath = (Join-Path $PSScriptRoot "tiktok_shop_baserow_schema.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "https://baserow.mafrapi.eu"
}
$BaseUrl = $BaseUrl.TrimEnd("/")

if (-not (Test-Path $SchemaPath)) {
    throw "Schema file not found: $SchemaPath"
}

$schema = Get-Content -Path $SchemaPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($JwtToken)) {
    if ([string]::IsNullOrWhiteSpace($Email) -or [string]::IsNullOrWhiteSpace($Password)) {
        Write-Host "[TikTok-Shop Setup] Hinweis: Fuer Baserow-Tabellenanlage bitte -JwtToken oder -Email/-Password angeben." -ForegroundColor Yellow
        exit 0
    }
    $authResp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/user/token-auth/" -ContentType "application/json" -Body (@{
        email = $Email
        password = $Password
    } | ConvertTo-Json)
    $JwtToken = $authResp.access_token
}

$headers = @{
    Authorization = "JWT $JwtToken"
    "Content-Type" = "application/json"
}

$existingTables = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/database/tables/database/$DatabaseId/" -Headers $headers

foreach ($tbl in $schema.tables) {
    $found = $existingTables | Where-Object { $_.name -eq $tbl.name } | Select-Object -First 1
    if ($null -eq $found) {
        Write-Host "[TikTok-Shop Setup] Creating table $($tbl.name)..." -ForegroundColor Cyan
        $found = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/database/tables/database/$DatabaseId/" -Headers $headers -Body (@{
            name = $tbl.name
        } | ConvertTo-Json)
    } else {
        Write-Host "[TikTok-Shop Setup] Table $($tbl.name) already exists (ID: $($found.id))." -ForegroundColor Green
    }
}
Write-Host "[TikTok-Shop Setup] Done." -ForegroundColor Green
