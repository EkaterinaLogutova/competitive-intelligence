$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

Push-Location $repoRoot
try {
    python -m compileall -q src tests scripts
    python -m competitive_intelligence validate
    python -m unittest discover -s tests -v
}
finally {
    Pop-Location
}

