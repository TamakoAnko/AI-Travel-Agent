# 一键启动本地依赖：WSL 里的 Redis + Milvus，并同步 .env 的 MILVUS_URI
# 用法：powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$ip = (wsl -d Ubuntu -- hostname -I).Trim().Split(" ")[0]
$envPath = Join-Path $root ".env"
if (Test-Path $envPath) {
    (Get-Content -LiteralPath $envPath) -replace "^MILVUS_URI=.*", "MILVUS_URI=http://${ip}:19530" |
        Set-Content -LiteralPath $envPath -Encoding utf8
}
wsl -d Ubuntu -u root -- service redis-server start
wsl -d Ubuntu -- bash -lc "pgrep -f milvus-server >/dev/null || (nohup ~/milvus-venv/bin/milvus-server --data ~/milvus-data > ~/milvus.log 2>&1 &)"
Start-Sleep -Seconds 8
Write-Host "MILVUS_URI = http://${ip}:19530"
Write-Host "验证：curl http://${ip}:9091/healthz"
