$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $projectRoot "config.json"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "config.json was not found in $projectRoot"
}

function Read-SecretText([string]$Prompt) {
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

$env:NEXUS_DEMO_API_KEY = Read-SecretText "Paste the Bitget Demo API key"
$env:NEXUS_DEMO_SECRET = Read-SecretText "Paste the Bitget Demo secret"
$env:NEXUS_DEMO_PASSWORD = Read-SecretText "Paste the Bitget Demo passphrase"

try {
    $python = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "The virtual environment was not found. Complete dependency setup first."
    }

    $env:NEXUS_CONFIG_PATH = $configPath
    $updateScript = Join-Path $PSScriptRoot "update_demo_config.py"
    & $python $updateScript
}
finally {
    Remove-Item Env:NEXUS_DEMO_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:NEXUS_DEMO_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:NEXUS_DEMO_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:NEXUS_CONFIG_PATH -ErrorAction SilentlyContinue
}
