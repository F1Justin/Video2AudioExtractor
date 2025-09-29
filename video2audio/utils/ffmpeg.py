from __future__ import annotations

import json
import contextlib
import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Callable, Optional, Tuple


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def _binary_name(base: str) -> str:
    return f"{base}.exe" if _is_windows() else base


def resolve_ffmpeg_binaries() -> dict[str, str]:
    """解析 ffmpeg/ffprobe 的可执行路径。

    优先级：
    1. 环境变量 `FFMPEG_BIN_DIR`
    2. PyInstaller `_MEIPASS` 下的 `ffmpeg/`
    3. 项目根目录下的 `ffmpeg/`
    4. `PATH` 中可执行文件
    5. 回退为命令名（期望已在 PATH）
    """

    candidates: list[Path] = []
    env_dir = os.environ.get("FFMPEG_BIN_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    meipass_dir = getattr(sys, "_MEIPASS", None)
    if meipass_dir:
        candidates.append(Path(meipass_dir) / "ffmpeg")

    # 项目根目录的 ffmpeg/ 目录
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates.append(project_root / "ffmpeg")

    results: dict[str, str] = {}
    for name in ("ffmpeg", "ffprobe"):
        exe = _binary_name(name)
        # PATH 中查找
        path_in_path = shutil.which(exe)
        if path_in_path:
            results[name] = path_in_path
        else:
            # 依次检查候选目录
            for base in candidates:
                if base and (base / exe).exists():
                    results[name] = str(base / exe)
                    break

    results.setdefault("ffmpeg", _binary_name("ffmpeg"))
    results.setdefault("ffprobe", _binary_name("ffprobe"))
    return results


def probe_duration_seconds(input_path: Path) -> float:
    """使用 ffprobe 获取媒体总时长（秒）。"""
    bins = resolve_ffmpeg_binaries()
    ffprobe = bins["ffprobe"]
    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        str(input_path),
    ]
    run_kwargs = {}
    if _is_windows():
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            run_kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": startupinfo}
        except Exception:
            run_kwargs = {}
    completed = subprocess.run(cmd, capture_output=True, text=True, **run_kwargs)
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe 执行失败: {completed.stderr.strip()}")
    try:
        data = json.loads(completed.stdout or "{}")
        duration_str = (data.get("format") or {}).get("duration")
        return float(duration_str) if duration_str else 0.0
    except Exception as exc:  # noqa: BLE001 - 保底防御
        raise RuntimeError(f"ffprobe 输出解析失败: {exc}") from exc


def transcode_with_progress(
    input_file: Path,
    output_file: Path,
    codec_args: Optional[list[str]],
    total_duration_seconds: float,
    on_progress_percent: Callable[[int], None],
) -> Tuple[int, str]:
    """执行 ffmpeg 转码并通过 `-progress pipe:1` 实时回调进度百分比。

    返回 `(returncode, stderr_text)`。
    """
    bins = resolve_ffmpeg_binaries()
    ffmpeg = bins["ffmpeg"]

    args: list[str] = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(input_file),
    ]
    if codec_args:
        args.extend(codec_args)
    args.extend([
        str(output_file),
        "-progress",
        "pipe:1",
        "-y",
    ])

    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
    }
    if _is_windows():
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            popen_kwargs.update({
                "creationflags": subprocess.CREATE_NO_WINDOW,
                "startupinfo": startupinfo,
            })
        except Exception:
            pass
    process = subprocess.Popen(args, **popen_kwargs)

    try:
        # 读取进度
        if process.stdout is None:
            raise RuntimeError("无法读取 ffmpeg stdout 流")

        last_percent = 0
        microseconds_total = max(1, int(total_duration_seconds * 1_000_000))
        while True:
            line = process.stdout.readline()
            if not line:
                break
            text = line.strip()
            if not text:
                continue
            if text.startswith("out_time_ms="):
                try:
                    processed_us = int(text.split("=", 1)[1])
                    percent = int(min(99, max(0, processed_us * 100 // microseconds_total)))
                    if percent != last_percent:
                        last_percent = percent
                        on_progress_percent(percent)
                except Exception:
                    # 忽略解析异常，继续
                    pass

        # 读取剩余输出并等待结束
        _, stderr_text = process.communicate(timeout=30)
        rc = process.returncode or 0
        if rc == 0:
            try:
                on_progress_percent(100)
            except Exception:
                pass
        return rc, stderr_text or ""
    finally:
        with contextlib.suppress(Exception):
            if process.stdout:
                process.stdout.close()
        with contextlib.suppress(Exception):
            if process.stderr:
                process.stderr.close()


