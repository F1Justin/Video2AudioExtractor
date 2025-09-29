from __future__ import annotations

import sys

from video2audio.view import AppView
from video2audio.controller import AppController


def main() -> None:
    """应用入口：构建 MVC 并启动主循环。"""
    view = AppView(theme="darkly")
    controller = AppController(view=view)
    view.bind_controller(controller)
    view.start_ui_update_loop()
    view.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 顶层保护，打印异常
        print(f"程序异常退出: {exc}", file=sys.stderr)
        raise


