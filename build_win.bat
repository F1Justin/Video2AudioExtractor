@echo off
setlocal ENABLEDELAYEDEXPANSION

REM 一键打包脚本（Windows）
REM 1) 创建虚拟环境（可选）
REM 2) 安装依赖与 PyInstaller
REM 3) 下载 ffmpeg/ffprobe 到 ffmpeg/ 目录（如未存在）
REM 4) 使用 PyInstaller 打包为单文件无控制台的 EXE

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo 未找到 python，请先安装 Python 3.x 并添加到 PATH。
  pause
  exit /b 1
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo 离线打包模式：使用本地依赖与已下载的 FFmpeg。
echo 若已配置好本地 Python/依赖，继续；否则请确保可用的本地 PyInstaller。

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
  echo 未找到 pyinstaller，请先在这台机器上安装 PyInstaller（离线环境可提前将 wheel 放入本地源）。
  pause
  exit /b 1
)

if not exist ffmpeg mkdir ffmpeg

REM 优先使用你提供的本地 FFmpeg 目录（离线拷贝）
REM 例如：ffmpeg-2025-09-25-git-9970dc32bf-essentials_build\bin
set LOCAL_FFMPEG_BIN=ffmpeg-2025-09-25-git-9970dc32bf-essentials_build\bin
if exist "%LOCAL_FFMPEG_BIN%\ffmpeg.exe" (
  copy /Y "%LOCAL_FFMPEG_BIN%\ffmpeg.exe" ffmpeg\ffmpeg.exe >nul
)
if exist "%LOCAL_FFMPEG_BIN%\ffprobe.exe" (
  copy /Y "%LOCAL_FFMPEG_BIN%\ffprobe.exe" ffmpeg\ffprobe.exe >nul
)

if not exist ffmpeg\ffmpeg.exe (
  echo 未检测到 ffmpeg\\ffmpeg.exe。请将已下载的 ffmpeg.exe/ffprobe.exe 放入 ffmpeg\ 目录。
  echo 或修改此脚本中的 LOCAL_FFMPEG_BIN 指向你的本地 FFmpeg bin 目录。
  pause
  exit /b 1
)

echo 开始打包...
REM 使用 spec 确保数据文件与依赖打包完全
pyinstaller --noconfirm app.spec

if %errorlevel% neq 0 (
  echo 打包失败。
  pause
  exit /b 1
)

echo 打包完成。输出文件位于 dist\Video2AudioExtractor\Video2AudioExtractor.exe
pause


