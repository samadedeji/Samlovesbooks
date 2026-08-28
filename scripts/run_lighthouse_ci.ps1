# Lighthouse throttling is a simulation; manual Opera Mini, KaiOS, and JS-disabled checks remain required.
$ErrorActionPreference = "Stop"
$server = $null
try {
    $server = Start-Process python -ArgumentList "run.py" -PassThru
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing | Out-Null
            break
        } catch {
            if ($attempt -eq 29) { throw }
        }
    }
    npx lhci autorun
    exit $LASTEXITCODE
} finally {
    if ($server) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
}
