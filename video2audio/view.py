from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import ttkbootstrap as tb
except Exception:  # noqa: BLE001 - 允许在无 ttkbootstrap 时回退到 ttk
    tb = None  # type: ignore

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # noqa: BLE001 - 若无拖拽库，使用普通 Tk
    DND_FILES = None  # type: ignore
    TkinterDnD = tk.Tk  # type: ignore


class AppView:
    """视图层：构建 UI、转发事件、接收控制器更新。"""

    def __init__(self, theme: str = "darkly") -> None:
        # 初始化根窗口
        if tb is not None:
            self.root = tb.Window(themename=theme)
        else:
            self.root = TkinterDnD()  # type: ignore[call-arg]
        self.root.title("Video2AudioExtractor")
        self.root.geometry("900x640")

        self.controller: Optional["AppController"] = None

        # 选项区
        self.format_var = tk.StringVar(value="MP3")
        self.output_dir_var = tk.StringVar(value=str(Path.home()))

        self._build_widgets()

        # 队列轮询间隔
        self._poll_interval_ms = 100

        # 存储 Treeview 行数据
        self.tree_columns = ("filename", "size", "progress", "status")

    # ========= 控制器绑定 =========
    def bind_controller(self, controller: "AppController") -> None:
        self.controller = controller

    # ========= UI 构建 =========
    def _build_widgets(self) -> None:
        # 顶部选项区
        top = ttk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="输出格式").pack(side=tk.LEFT)
        self.format_box = ttk.Combobox(top, textvariable=self.format_var, state="readonly", values=["MP3", "WAV", "AAC"])
        self.format_box.pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="输出目录").pack(side=tk.LEFT, padx=(16, 0))
        self.output_entry = ttk.Entry(top, textvariable=self.output_dir_var, state="readonly", width=50)
        self.output_entry.pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="选择...", command=self._choose_output_dir).pack(side=tk.LEFT)

        # 拖放区域 + 列表
        main = ttk.Frame(self.root)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        drop_frame = ttk.LabelFrame(main, text="拖放文件到此区域")
        drop_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=6)
        drop_target = ttk.Label(drop_frame, text="将视频文件拖到这里", anchor=tk.CENTER)
        drop_target.pack(fill=tk.X, padx=10, pady=12)

        if DND_FILES:
            drop_target.drop_target_register(DND_FILES)
            drop_target.dnd_bind("<<Drop>>", self._on_drop_event)
        else:
            # 无拖拽库时，提供按钮选择
            ttk.Button(drop_frame, text="选择文件...", command=self._fallback_choose_files).pack(pady=6)

        # 任务列表
        tree = ttk.Treeview(main, columns=self.tree_columns, show="headings", height=16)
        tree.heading("filename", text="文件名")
        tree.heading("size", text="大小")
        tree.heading("progress", text="进度")
        tree.heading("status", text="状态")

        tree.column("filename", stretch=True, width=420)
        tree.column("size", width=100, anchor=tk.E)
        tree.column("progress", width=120, anchor=tk.CENTER)
        tree.column("status", width=120, anchor=tk.CENTER)

        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree = tree

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status.pack(side=tk.BOTTOM, fill=tk.X)

    # ========= 公共接口（供控制器调用） =========
    def add_task_to_list(self, task: "ConversionTask") -> None:
        size_str = self._format_size(task.input_path.stat().st_size) if task.input_path.exists() else "-"
        self.tree.insert("", tk.END, iid=task.id, values=(task.input_path.name, size_str, "0%", task.status))

    def update_task_in_list(self, task_id: str, fields: Dict[str, Any]) -> None:
        item = self.tree.item(task_id)
        if not item:
            return
        vals = list(item.get("values") or [])
        # columns: filename, size, progress, status
        if "progress" in fields:
            percent = int(fields["progress"]) if isinstance(fields["progress"], int) else fields["progress"]
            vals[2] = f"{percent}%"
        if "status" in fields:
            vals[3] = fields["status"]
        self.tree.item(task_id, values=vals)

    def get_selected_format(self) -> str:
        return str(self.format_var.get())

    def get_output_directory(self) -> str:
        return str(self.output_dir_var.get())

    # ========= 事件回调 =========
    def _choose_output_dir(self) -> None:
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)

    def _fallback_choose_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择视频文件")
        if paths and self.controller:
            self.controller.handle_file_drop(list(paths))

    def _on_drop_event(self, event: Any) -> None:
        if not self.controller:
            return
        raw_data = event.data  # e.g. "{path1} {path2}"
        paths = self._parse_dnd_paths(raw_data)
        if paths:
            self.controller.handle_file_drop(paths)

    # ========= 轮询 UI 队列 =========
    def start_ui_update_loop(self) -> None:
        self.root.after(self._poll_interval_ms, self._poll_queue)

    def _poll_queue(self) -> None:
        if not self.controller:
            return
        updated = False
        while True:
            try:
                msg = self.controller.ui_queue.get_nowait()
            except Exception:
                break
            msg_type = msg.get("type")
            task_id = msg.get("id")
            if msg_type == "progress":
                self.update_task_in_list(task_id, {"progress": msg.get("value", 0)})
                updated = True
            elif msg_type == "status":
                self.update_task_in_list(task_id, {"status": msg.get("value", "")})
                updated = True
            elif msg_type == "error":
                self.update_task_in_list(task_id, {"status": "失败"})
                self.status_var.set(str(msg.get("value")))
                updated = True
        if updated:
            self.status_var.set("已更新")
        self.root.after(self._poll_interval_ms, self._poll_queue)

    # ========= 运行 =========
    def run(self) -> None:
        self.root.mainloop()

    # ========= 工具 =========
    def _parse_dnd_paths(self, dnd_data: str) -> List[str]:
        # 兼容带空格文件名，tk 的 DND 会使用大括号包裹
        parts: List[str] = []
        current = []
        in_brace = False
        for ch in dnd_data:
            if ch == "{" and not in_brace:
                in_brace = True
                current = []
                continue
            if ch == "}" and in_brace:
                in_brace = False
                parts.append("".join(current))
                current = []
                continue
            if ch == " " and not in_brace:
                if current:
                    parts.append("".join(current))
                    current = []
                continue
            current.append(ch)
        if current:
            parts.append("".join(current))
        return [p for p in (x.strip() for x in parts) if p]

    @staticmethod
    def _format_size(size: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        s = float(size)
        idx = 0
        while s >= 1024 and idx < len(units) - 1:
            s /= 1024
            idx += 1
        if idx == 0:
            return f"{int(s)} {units[idx]}"
        return f"{s:.1f} {units[idx]}"


