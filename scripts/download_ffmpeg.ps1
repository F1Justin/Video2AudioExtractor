param(
  [string]$DestDir = "ffmpeg"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $DestDir)) {
  New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
}

$ffmpegExe = Join-Path $DestDir 'ffmpeg.exe'
$ffprobeExe = Join-Path $DestDir 'ffprobe.exe'

if ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
  Write-Host "ffmpeg.exe 与 ffprobe.exe 已存在，跳过下载。"
  exit 0
}

# 使用 gyan.dev 的预编译静态构建（示例链接，可能更新）
$zipUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z'
$tmp7z = Join-Path $env:TEMP 'ffmpeg.7z'

Write-Host "下载 FFmpeg 压缩包..."
Invoke-WebRequest -Uri $zipUrl -OutFile $tmp7z

# 解压需要 7zip
$sevenZip = (Get-Command 7z -ErrorAction SilentlyContinue)
if (-not $sevenZip) {
  Write-Host "未检测到 7-Zip，尝试使用 PowerShell 解压（可能失败）。"
  # 部分 Windows 不能原生解 7z，这里给出提示
  Write-Host "请安装 7-Zip 并将其添加到 PATH，然后重新运行脚本。"
  exit 1
}

Write-Host "解压 FFmpeg..."
& 7z x -y $tmp7z -o$env:TEMP | Out-Null

$extracted = Get-ChildItem -Path $env:TEMP -Directory | Where-Object { $_.Name -like 'ffmpeg-*' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $extracted) {
  Write-Host "未找到解压结果。"
  exit 1
}

$binDir = Join-Path $extracted.FullName 'bin'
$srcFfmpeg = Join-Path $binDir 'ffmpeg.exe'
$srcFfprobe = Join-Path $binDir 'ffprobe.exe'

Copy-Item -Force $srcFfmpeg $ffmpegExe
Copy-Item -Force $srcFfprobe $ffprobeExe

Write-Host "FFmpeg 已下载到 $DestDir"
exit 0


