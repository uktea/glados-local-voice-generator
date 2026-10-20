param(
    [Parameter(Mandatory=$true)][string]$YMM4DirPath,
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [string]$AppDirectory = (Join-Path $PSScriptRoot '..\glados-local'),
    [string]$Dotnet = 'dotnet'
)
$ErrorActionPreference = 'Stop'
$ymmResolved = (Resolve-Path -LiteralPath $YMM4DirPath).Path
$pythonResolved = (Resolve-Path -LiteralPath $PythonExe).Path
$appResolved = (Resolve-Path -LiteralPath $AppDirectory).Path
$project = Join-Path $PSScriptRoot 'src\GladosLocalVoice\GladosLocalVoice.csproj'
& $Dotnet build $project -c Release "-p:YMM4DirPath=$ymmResolved"
if ($LASTEXITCODE -ne 0) { throw 'Plugin build failed' }
$dist = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Path $dist -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'src\GladosLocalVoice\bin\Release\net10.0-windows10.0.19041.0\GladosLocalVoice.dll') -Destination $dist
@{ PythonExe=$pythonResolved; AppDirectory=$appResolved; Device='auto'; TimeoutSeconds=180 } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dist 'glados-config.json') -Encoding utf8
$zip = Join-Path $PSScriptRoot 'GladosLocalVoice.zip'
Compress-Archive -LiteralPath (Join-Path $dist 'GladosLocalVoice.dll'),(Join-Path $dist 'glados-config.json') -DestinationPath $zip -Force
Copy-Item -LiteralPath $zip -Destination (Join-Path $PSScriptRoot 'GladosLocalVoice.ymme') -Force
Write-Output "Built: $(Join-Path $PSScriptRoot 'GladosLocalVoice.ymme')"
