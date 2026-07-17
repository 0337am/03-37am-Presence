[CmdletBinding()]
param(
    [string]$Python = "C:\Python314\python.exe",

    [string]$InnoCompiler = "",

    [string]$OutputRoot = "",

    [switch]$Force,

    [switch]$ValidateOnly,

    [switch]$SkipRepositoryStateCheck
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest


function Get-ReleaseMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string]$VersionFile
    )

    $Source = Get-Content `
        -Path $VersionFile `
        -Raw `
        -Encoding UTF8

    $VersionMatch = [regex]::Match(
        $Source,
        (
            '(?m)^APP_VERSION\s*=\s*' +
            '"(?<value>[^"]+)"\s*$'
        )
    )

    $ReleaseMatch = [regex]::Match(
        $Source,
        (
            '(?m)^RELEASE_NAME\s*=\s*' +
            '"(?<value>[^"]+)"\s*$'
        )
    )

    if (-not $VersionMatch.Success) {
        throw (
            "APP_VERSION could not be read from " +
            "$VersionFile"
        )
    }

    if (-not $ReleaseMatch.Success) {
        throw (
            "RELEASE_NAME could not be read from " +
            "$VersionFile"
        )
    }

    return [PSCustomObject]@{
        Version = (
            $VersionMatch.Groups["value"].Value
        )
        ReleaseName = (
            $ReleaseMatch.Groups["value"].Value
        )
    }
}


function Assert-CommandSucceeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    if ($LASTEXITCODE -ne 0) {
        throw (
            "$Description failed with exit code " +
            "$LASTEXITCODE."
        )
    }
}


$RepositoryRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

Set-Location $RepositoryRoot

$VersionFile = Join-Path `
    $RepositoryRoot `
    "src\version.py"

$VersionInfoFile = Join-Path `
    $RepositoryRoot `
    "version_info.txt"

$SpecFile = Join-Path `
    $RepositoryRoot `
    "03-37am Presence.spec"

$InstallerTemplate = Join-Path `
    $RepositoryRoot `
    "installer\03-37am-Presence.iss"

$IconFile = Join-Path `
    $RepositoryRoot `
    "icons\app_icon.ico"

if (-not $InnoCompiler) {
    $InnoCompiler = Join-Path `
        $env:LOCALAPPDATA `
        "Programs\Inno Setup 6\ISCC.exe"
}

$RequiredFiles = @(
    $Python
    $VersionFile
    $VersionInfoFile
    $SpecFile
    $InstallerTemplate
    $IconFile
    $InnoCompiler
)

foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path $RequiredFile -PathType Leaf)) {
        throw "Required file not found: $RequiredFile"
    }
}

$Metadata = Get-ReleaseMetadata `
    -VersionFile $VersionFile

$Version = $Metadata.Version.Trim()
$ReleaseName = $Metadata.ReleaseName.Trim()

if (
    $Version -notmatch
    '^[0-9]+\.[0-9]+\.[0-9]+$'
) {
    throw (
        "APP_VERSION must use the format " +
        "major.minor.patch. Found: $Version"
    )
}

if (-not $ReleaseName) {
    throw "RELEASE_NAME must not be empty."
}

if (
    $ReleaseName.Contains('"') -or
    $ReleaseName.Contains("`r") -or
    $ReleaseName.Contains("`n")
) {
    throw (
        "RELEASE_NAME contains characters which " +
        "cannot be passed safely to Inno Setup."
    )
}

$WindowsVersion = "$Version.0"

$VersionInfoSource = Get-Content `
    -Path $VersionInfoFile `
    -Raw `
    -Encoding UTF8

$WindowsVersionCount = (
    [regex]::Matches(
        $VersionInfoSource,
        [regex]::Escape($WindowsVersion)
    )
).Count

if ($WindowsVersionCount -lt 2) {
    throw (
        "version_info.txt is not aligned with " +
        "APP_VERSION $Version."
    )
}

$SpecSource = Get-Content `
    -Path $SpecFile `
    -Raw `
    -Encoding UTF8

if (
    $SpecSource -notmatch
    'console\s*=\s*False'
) {
    throw (
        "The PyInstaller specification must use " +
        "console=False."
    )
}

if (
    $SpecSource -notmatch
    'version\s*=\s*"version_info\.txt"'
) {
    throw (
        "The PyInstaller specification must use " +
        "version_info.txt."
    )
}

if (-not $OutputRoot) {
    $RepositoryParent = Split-Path `
        $RepositoryRoot `
        -Parent

    $OutputRoot = Join-Path `
        $RepositoryParent `
        (
            "03-37am-Presence-RELEASES\" +
            "v$Version"
        )
}
elseif (
    -not [System.IO.Path]::IsPathRooted(
        $OutputRoot
    )
) {
    $OutputRoot = [System.IO.Path]::GetFullPath(
        (
            Join-Path `
                $RepositoryRoot `
                $OutputRoot
        )
    )
}

$Branch = "Unavailable"
$Commit = "Unavailable"

try {
    $Branch = (
        git branch --show-current
    ).Trim()

    $Commit = (
        git rev-parse --short HEAD
    ).Trim()
}
catch {
    if (-not $SkipRepositoryStateCheck) {
        throw "Git repository information is unavailable."
    }
}

if (-not $SkipRepositoryStateCheck) {
    $RepositoryChanges = @(
        git status --porcelain
    )

    if ($RepositoryChanges.Count -ne 0) {
        git status --short

        throw (
            "The repository must be clean before " +
            "creating release artifacts."
        )
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "03:37am Presence Release Builder"
Write-Host "========================================"
Write-Host ""
Write-Host "Repository:   $RepositoryRoot"
Write-Host "Branch:       $Branch"
Write-Host "Commit:       $Commit"
Write-Host "Version:      $Version"
Write-Host "Release name: $ReleaseName"
Write-Host "Output:       $OutputRoot"
Write-Host "Python:       $Python"
Write-Host "Inno Setup:   $InnoCompiler"
Write-Host ""

Write-Host "Checking PyInstaller..."

& $Python `
    -c `
    "import PyInstaller; print(PyInstaller.__version__)"

Assert-CommandSucceeded `
    -Description "PyInstaller availability check"

if ($ValidateOnly) {
    Write-Host ""
    Write-Host "========================================" `
        -ForegroundColor Green

    Write-Host (
        "PASSED: Release-build configuration " +
        "is valid."
    ) -ForegroundColor Green

    Write-Host (
        "No build folders or release artifacts " +
        "were created."
    ) -ForegroundColor Green

    Write-Host "========================================" `
        -ForegroundColor Green

    return
}

if (Test-Path $OutputRoot) {
    $ExistingOutput = @(
        Get-ChildItem `
            -Path $OutputRoot `
            -Force `
            -ErrorAction SilentlyContinue
    )

    if ($ExistingOutput.Count -gt 0) {
        if (-not $Force) {
            throw (
                "Output folder is not empty: " +
                "$OutputRoot`n" +
                "Use -Force to replace it."
            )
        }

        Remove-Item `
            -Path $OutputRoot `
            -Recurse `
            -Force
    }
}

New-Item `
    -ItemType Directory `
    -Path $OutputRoot `
    -Force |
    Out-Null

$BuildFolder = Join-Path `
    $RepositoryRoot `
    "build"

$DistFolder = Join-Path `
    $RepositoryRoot `
    "dist"

foreach ($GeneratedFolder in @(
    $BuildFolder
    $DistFolder
)) {
    if (Test-Path $GeneratedFolder) {
        Remove-Item `
            -Path $GeneratedFolder `
            -Recurse `
            -Force
    }
}

Write-Host ""
Write-Host "Building standalone executable..."

& $Python `
    -m PyInstaller `
    --clean `
    --noconfirm `
    $SpecFile

Assert-CommandSucceeded `
    -Description "PyInstaller build"

$BuiltExecutable = Join-Path `
    $DistFolder `
    "03-37am Presence.exe"

if (-not (Test-Path $BuiltExecutable -PathType Leaf)) {
    throw (
        "PyInstaller did not create the expected " +
        "executable: $BuiltExecutable"
    )
}

$StandaloneName = (
    "03-37am-Presence-v" +
    $Version +
    ".exe"
)

$StandalonePath = Join-Path `
    $OutputRoot `
    $StandaloneName

Copy-Item `
    -Path $BuiltExecutable `
    -Destination $StandalonePath `
    -Force

Write-Host ""
Write-Host "Building installer..."

$VersionArgument = (
    '/DMyAppVersion="' +
    $Version +
    '"'
)

$ReleaseArgument = (
    '/DMyReleaseName="' +
    $ReleaseName +
    '"'
)

$OutputArgument = (
    "/O" +
    $OutputRoot
)

& $InnoCompiler `
    "/Qp" `
    $OutputArgument `
    $VersionArgument `
    $ReleaseArgument `
    $InstallerTemplate

Assert-CommandSucceeded `
    -Description "Inno Setup build"

$InstallerName = (
    "03-37am-Presence-Setup-v" +
    $Version +
    ".exe"
)

$InstallerPath = Join-Path `
    $OutputRoot `
    $InstallerName

if (-not (Test-Path $InstallerPath -PathType Leaf)) {
    throw (
        "Inno Setup did not create the expected " +
        "installer: $InstallerPath"
    )
}

$ExpectedDescription = (
    "03:37am Presence - " +
    $ReleaseName
)

foreach ($ArtifactPath in @(
    $StandalonePath
    $InstallerPath
)) {
    $Artifact = Get-Item $ArtifactPath
    $VersionInfo = $Artifact.VersionInfo

    $FileVersion = (
        [string]$VersionInfo.FileVersion
    ).Trim()

    $ProductVersion = (
        [string]$VersionInfo.ProductVersion
    ).Trim()

    $ProductName = (
        [string]$VersionInfo.ProductName
    ).Trim()

    $Description = (
        [string]$VersionInfo.FileDescription
    ).Trim()

    if ($Artifact.Length -le 0) {
        throw "Artifact is empty: $ArtifactPath"
    }

    if ($FileVersion -ne $WindowsVersion) {
        throw (
            "$($Artifact.Name) has file version " +
            "'$FileVersion'; expected " +
            "'$WindowsVersion'."
        )
    }

    if ($ProductVersion -ne $WindowsVersion) {
        throw (
            "$($Artifact.Name) has product version " +
            "'$ProductVersion'; expected " +
            "'$WindowsVersion'."
        )
    }

    if ($ProductName -ne "03:37am Presence") {
        throw (
            "$($Artifact.Name) has unexpected " +
            "product name '$ProductName'."
        )
    }

    if ($Description -ne $ExpectedDescription) {
        throw (
            "$($Artifact.Name) has description " +
            "'$Description'; expected " +
            "'$ExpectedDescription'."
        )
    }
}

$InstallerHash = (
    Get-FileHash `
        -Path $InstallerPath `
        -Algorithm SHA256
).Hash.ToLowerInvariant()

$StandaloneHash = (
    Get-FileHash `
        -Path $StandalonePath `
        -Algorithm SHA256
).Hash.ToLowerInvariant()

$ChecksumPath = Join-Path `
    $OutputRoot `
    "SHA256SUMS.txt"

$ChecksumLines = @(
    "$InstallerHash  $InstallerName"
    "$StandaloneHash  $StandaloneName"
)

[System.IO.File]::WriteAllLines(
    $ChecksumPath,
    $ChecksumLines,
    [System.Text.UTF8Encoding]::new($false)
)

$InstallerSize = (
    Get-Item $InstallerPath
).Length

$StandaloneSize = (
    Get-Item $StandalonePath
).Length

$ManifestPath = Join-Path `
    $OutputRoot `
    "build-manifest.txt"

$ManifestLines = @(
    "03:37am Presence release build"
    "================================"
    "Version: $Version"
    "Release name: $ReleaseName"
    "Windows version: $WindowsVersion"
    "Branch: $Branch"
    "Commit: $Commit"
    (
        "Built: " +
        (
            Get-Date
        ).ToString(
            "yyyy-MM-dd HH:mm:ss zzz"
        )
    )
    ""
    "Artifacts"
    "---------"
    "$InstallerName"
    "Size bytes: $InstallerSize"
    "SHA-256: $InstallerHash"
    ""
    "$StandaloneName"
    "Size bytes: $StandaloneSize"
    "SHA-256: $StandaloneHash"
    ""
    "Code signing: Not signed"
)

[System.IO.File]::WriteAllLines(
    $ManifestPath,
    $ManifestLines,
    [System.Text.UTF8Encoding]::new($false)
)

if (-not $SkipRepositoryStateCheck) {
    $FinalRepositoryChanges = @(
        git status --porcelain
    )

    if ($FinalRepositoryChanges.Count -ne 0) {
        git status --short

        throw (
            "The release build unexpectedly changed " +
            "tracked repository files."
        )
    }
}

Write-Host ""
Write-Host "Release artifacts:"
Write-Host "  $InstallerName"
Write-Host "  $StandaloneName"
Write-Host "  SHA256SUMS.txt"
Write-Host "  build-manifest.txt"

Write-Host ""
Write-Host "Installer SHA-256:"
Write-Host "  $InstallerHash"

Write-Host ""
Write-Host "Standalone SHA-256:"
Write-Host "  $StandaloneHash"

Write-Host ""
Write-Host "Output folder:"
Write-Host "  $OutputRoot"

Write-Host ""
Write-Host "========================================" `
    -ForegroundColor Green

Write-Host "PASSED: Release build completed." `
    -ForegroundColor Green

Write-Host "========================================" `
    -ForegroundColor Green
