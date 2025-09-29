## Video2AudioExtractor

一个基于 Tkinter + ttkbootstrap 的图形化视频转音频工具，采用 MVC 架构：模型-视图-控制器。支持拖放文件、并发处理、实时进度显示（FFmpeg `-progress pipe:1`）。

### 快速开始

1) 安装依赖：

```bash
pip install -r requirements.txt
```

2) 安装 FFmpeg：
- macOS: 使用 `brew install ffmpeg` 或自行下载并设置到 `PATH`。
- Windows: 下载 `ffmpeg.exe` 与 `ffprobe.exe`，并放入 `PATH` 或项目根目录的 `ffmpeg/` 目录。

3) 运行：

```bash
python main.py
```

### 功能特性
- 拖放多个视频文件到窗口区域
- 选择输出格式（MP3 / WAV / AAC）
- 选择输出目录
- 并发执行（`ThreadPoolExecutor`）
- 队列消息 + 主线程 `after()` 拉取刷新 UI（每 100ms）
- 实时解析 FFmpeg `out_time_ms`，计算进度百分比

### 打包（Windows）

一键打包（完全离线可用）：

```bat
build_win.bat
```

注意：
- 将你已下载的 FFmpeg 目录（例如 `ffmpeg-2025-09-25-git-9970dc32bf-essentials_build/bin`）拷贝到项目根目录。
- 脚本会自动复制 `ffmpeg.exe` 与 `ffprobe.exe` 到项目的 `ffmpeg/` 目录进行打包。
- 输出位于 `dist/Video2AudioExtractor/Video2AudioExtractor.exe`，可在无 Python、无网络环境直接运行。

或使用 PyInstaller（手动）：

```bash
pyinstaller --onefile --windowed \
  --add-data "ffmpeg/ffmpeg.exe;ffmpeg" \
  --add-data "ffmpeg/ffprobe.exe;ffmpeg" \
  --icon "path/to/icon.ico" \
  main.py
```

- 若将 `ffmpeg.exe` 与 `ffprobe.exe` 一起打包，上述运行时会在临时目录提供 `ffmpeg/` 子目录，程序会自动查找。

### 目录结构

```
Video2AudioExtractor/
├─ video2audio/
│  ├─ utils/
│  │  └─ ffmpeg.py
│  ├─ controller.py
│  ├─ model.py
│  ├─ view.py
│  └─ __init__.py
├─ main.py
├─ requirements.txt
├─ README.md
└─ principle.md
```

### 许可证

MIT

