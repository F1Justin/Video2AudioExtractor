from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import uuid


@dataclass
class ConversionTask:
    """转换任务数据模型。

    - `id`: 任务 UUID，作为 UI `Treeview` 行的 `iid`。
    - `input_path`: 源视频文件路径。
    - `output_path`: 目标音频输出路径（字符串）。
    - `status`: 当前状态：'排队中' | '获取信息' | '处理中' | '已完成' | '失败' | '已取消'。
    - `progress`: 进度百分比 0-100。
    - `total_duration_seconds`: 视频总时长（秒），由 ffprobe 获取。
    - `error_message`: 失败时的错误详情。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_path: Path = field(default_factory=Path)
    output_path: str = ""
    status: str = "排队中"
    progress: int = 0
    total_duration_seconds: float = 0.0
    error_message: str = ""


