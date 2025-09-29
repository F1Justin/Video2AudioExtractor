from __future__ import annotations

import os
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

from .model import ConversionTask
from .utils.ffmpeg import probe_duration_seconds, transcode_with_progress


class AppController:
    """应用控制器：协调模型与视图、管理任务与线程池。"""

    def __init__(self, view: "AppView", max_workers: Optional[int] = None) -> None:
        self.view = view
        self.tasks: dict[str, ConversionTask] = {}
        self.ui_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = max(1, cpu_count // 2)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    # ========== 视图调用的接口 ==========
    def handle_file_drop(self, file_paths: list[str]) -> None:
        output_format = self.view.get_selected_format()
        output_dir = Path(self.view.get_output_directory() or "")
        for raw_path in file_paths:
            path = Path(raw_path).expanduser().resolve()
            if not path.exists() or not path.is_file():
                continue
            task = self._create_task(path, output_dir, output_format)
            self.tasks[task.id] = task
            self.view.add_task_to_list(task)
            self.executor.submit(self._worker_run_task, task.id)

    def request_cancel(self, task_id: str) -> None:
        # 简化：此示例不实现真正的进程中断，设置状态为已取消
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = "已取消"
        self._enqueue({"id": task.id, "type": "status", "value": task.status})

    # ========== 工作线程 ==========
    def _worker_run_task(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return
        try:
            # 获取信息
            task.status = "获取信息"
            self._enqueue({"id": task.id, "type": "status", "value": task.status})
            duration = probe_duration_seconds(task.input_path)
            task.total_duration_seconds = duration

            # 转码
            task.status = "处理中"
            self._enqueue({"id": task.id, "type": "status", "value": task.status})

            codec_args = self._codec_args_for_output(task.output_path)

            def on_progress(p: int) -> None:
                task.progress = p
                self._enqueue({"id": task.id, "type": "progress", "value": p})

            rc, stderr_text = transcode_with_progress(
                input_file=task.input_path,
                output_file=Path(task.output_path),
                codec_args=codec_args,
                total_duration_seconds=task.total_duration_seconds,
                on_progress_percent=on_progress,
            )

            if rc == 0:
                task.status = "已完成"
                self._enqueue({"id": task.id, "type": "status", "value": task.status})
            else:
                task.status = "失败"
                task.error_message = stderr_text
                self._enqueue({"id": task.id, "type": "error", "value": task.error_message})
                self._enqueue({"id": task.id, "type": "status", "value": task.status})
        except Exception as exc:  # noqa: BLE001
            task.status = "失败"
            task.error_message = str(exc)
            self._enqueue({"id": task.id, "type": "error", "value": task.error_message})
            self._enqueue({"id": task.id, "type": "status", "value": task.status})

    # ========== 辅助 ==========
    def _enqueue(self, message: Dict[str, Any]) -> None:
        self.ui_queue.put(message)

    def _codec_args_for_output(self, output_path: str) -> list[str]:
        suffix = Path(output_path).suffix.lower()
        if suffix == ".mp3":
            return ["-vn", "-acodec", "libmp3lame", "-b:a", "192k"]
        if suffix == ".wav":
            return ["-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2"]
        if suffix == ".aac":
            return ["-vn", "-acodec", "aac", "-b:a", "192k"]
        return ["-vn"]

    def _create_task(self, input_path: Path, output_dir: Path, fmt: str) -> ConversionTask:
        output_dir = output_dir if output_dir and output_dir.exists() else input_path.parent
        ext = fmt.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        out_name = f"{input_path.stem}{ext}"
        out_path = output_dir / out_name
        # 处理重名：追加 (n)
        counter = 1
        while out_path.exists():
            out_name = f"{input_path.stem} ({counter}){ext}"
            out_path = output_dir / out_name
            counter += 1
        return ConversionTask(
            input_path=input_path,
            output_path=str(out_path),
        )


