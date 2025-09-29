### 一、 核心设计理念：模型-视图-控制器 (MVC)

我们将采用经典的 MVC 架构模式，以实现最大程度的解耦和可维护性。

*   **模型 (Model)**: 负责数据和业务逻辑。它不知道界面的存在。
*   **视图 (View)**: 负责展示数据和用户界面。它不包含任何业务逻辑。
*   **控制器 (Controller)**: 作为模型和视图之间的桥梁，处理用户输入，调用模型进行数据操作，并更新视图。

**优势**：当您未来想更换UI库（例如从Tkinter换成PyQt）时，只需重写视图层，模型和控制器层的核心逻辑完全可以复用。

---

### 二、 架构分层与技术参数

#### 1. 视图层 (View)

*   **核心职责**:
    *   构建和布局所有UI元素。
    *   接收用户的直接交互（点击、拖放、选择）。
    *   将用户交互事件转发给控制器。
    *   提供公共接口供控制器调用以更新UI（例如 `update_progress(task_id, percentage)`）。
*   **技术选型**:
    *   **GUI 框架**: **Tkinter** + **`ttkbootstrap`**
        *   **参数**: `theme='darkly'` 或其他现代主题。窗口尺寸建议 `800x600` 起步以容纳详细列表。
    *   **拖放支持**: **`tkinterdnd2`**
        *   **参数**: 绑定 `<<Drop>>` 事件到指定的拖放区域（例如一个大的`ttk.Frame`）。
    *   **核心UI组件及其参数**:
        *   **任务列表**: 使用 `ttk.Treeview`。
            *   **列 (Columns)**: `('filename', 'size', 'progress', 'status')`。
            *   **唯一标识 (iid)**: 每个插入的行必须使用任务的唯一ID (`task.id`) 作为 `iid`，这是后续更新特定行UI的关键。
            *   **进度条显示**: 在 `progress` 列中，由于Tkinter原生支持有限，最佳实践是**动态生成并嵌入一个`ttk.Progressbar`**，或者更简单地显示**文本百分比**（例如 "75%"）。
        *   **选项区**:
            *   **输出格式**: `ttk.Combobox`，设置为 `state="readonly"`，值为 `["MP3", "WAV", "AAC"]`。
            *   **输出目录**: `ttk.Entry` (设置为 `state="readonly"`) + `ttk.Button`。按钮点击时调用 `tkinter.filedialog.askdirectory`。
        *   **状态栏**: `ttk.Label`，`relief=SUNKEN`，位于窗口底部，用于显示总体状态或提示信息。

#### 2. 模型层 (Model)

*   **核心职责**:
    *   定义应用程序的核心数据结构。
*   **技术选型**:
    *   **纯 Python 类**: 创建一个 `ConversionTask` 数据类。
*   **核心属性 (技术参数)**:
    *   `id`: **UUID** (`uuid.uuid4()`)，字符串类型，全局唯一，用于精确地在UI和控制器中追踪任务。
    *   `input_path`: `pathlib.Path` 对象，源文件路径。
    *   `output_path`: 字符串，自动生成的输出文件路径（需处理重名）。
    *   `status`: 字符串，枚举值：`'排队中'`, `'获取信息'`, `'处理中'`, `'已完成'`, `'失败'`, `'已取消'`。
    *   `progress`: 整数，`0` 到 `100`。
    *   `total_duration_seconds`: 浮点数，从 `ffprobe` 获取的视频总时长，是计算进度的基础。
    *   `error_message`: 字符串，用于存储失败时的错误信息。

#### 3. 控制器层 (Controller)

*   **核心职责**:
    *   应用的“大脑”，协调所有操作。
    *   管理任务生命周期。
    *   与外部进程 (FFmpeg) 交互。
*   **技术选型与参数**:
    *   **并发管理**:
        *   **工具**: `concurrent.futures.ThreadPoolExecutor`。
        *   **参数**: `max_workers` 设置为 `os.cpu_count()` 或 `os.cpu_count() // 2`。这是一个关键的性能调优参数，防止CPU满载导致UI卡顿。
    *   **线程间通信**:
        *   **工具**: `queue.Queue`。
        *   **通信协议**: 定义标准化的消息格式。所有从工作线程发送到主线程的消息都应为**字典**，例如:
            ```json
            { "id": "task_uuid", "type": "progress", "value": 55 }
            { "id": "task_uuid", "type": "status", "value": "已完成" }
            { "id": "task_uuid", "type": "error", "value": "FFmpeg error..." }
            ```
    *   **UI 更新机制**:
        *   **机制**: 在主线程中使用 Tkinter 的 `root.after(milliseconds, callback)` 方法。
        *   **参数**: 设置 `milliseconds=100`，即每秒轮询10次队列，以实现流畅的UI更新，这是一个响应性和性能之间的权衡。`callback` 函数负责从队列中取出所有消息并更新UI。
    *   **外部进程调用 (`subprocess`)**:
        *   **获取视频时长 (ffprobe)**:
            *   **命令**: `ffprobe.exe -v quiet -print_format json -show_format "[INPUT_FILE_PATH]"`
            *   **参数**:
                *   `-v quiet`: 抑制不必要的日志。
                *   `-print_format json`: **强制输出为JSON格式**，这是最容易、最可靠的程序化解析方式。
                *   `-show_format`: 只获取容器格式信息，其中包含时长。
            *   **数据提取**: 解析返回的JSON字符串，提取 `format.duration` 字段的值。
        *   **执行转换并获取进度 (ffmpeg)**:
            *   **命令**: `ffmpeg.exe -i "[INPUT_FILE]" [CODEC_PARAMS] "[OUTPUT_FILE]" -progress pipe:1 -y`
            *   **核心参数**:
                *   `-progress pipe:1`: **这是实现进度条的关键**。此参数会使 FFmpeg 将详细的、机器可读的进度信息持续输出到**标准输出流 (stdout)**。
                *   `-y`: 无需确认，直接覆盖输出文件。
            *   **进程创建参数 (`subprocess.Popen`)**:
                *   `stdout=subprocess.PIPE`：捕获标准输出流（用于进度）。
                *   `stderr=subprocess.PIPE`：捕获标准错误流（用于错误信息）。
                *   `encoding='utf-8'`: 指定编码以避免乱码。
                *   `creationflags=subprocess.CREATE_NO_WINDOW` (仅Windows): **必须设置**，用于隐藏FFmpeg执行时弹出的黑色命令行窗口。
            *   **进度解析逻辑**:
                1.  在工作线程中，启动`ffmpeg`进程。
                2.  循环读取进程的 `stdout` 流 (`process.stdout.readline()`)。
                3.  FFmpeg的进度输出格式为 `key=value` 的文本行，例如 `out_time_ms=15234000`。
                4.  实时解析 `out_time_ms` (已处理的微秒数)，除以 `total_duration_seconds * 1,000,000`，得到进度百分比。
                5.  将计算出的进度百分比和任务ID打包成消息放入 `queue.Queue`。

---

### 三、 整体数据流 (用户操作 -> 完成)

1.  **用户操作**: 用户将文件拖入视图的拖放区。
2.  **视图 -> 控制器**: 视图的 `on_drop` 事件被触发，它获取文件路径列表，并调用 `controller.handle_file_drop(file_paths)`。
3.  **控制器**:
    a.  从视图获取当前选项（输出格式、目录）。
    b.  为每个文件路径创建一个 `ConversionTask` 模型实例，状态为`'排队中'`，并将其存入一个字典（`self.tasks[task.id] = task`）。
    c.  调用 `view.add_task_to_list(task)` 在界面上新增一行。
    d.  将处理该 `task` 的工作函数提交到 `ThreadPoolExecutor`。
4.  **工作线程**:
    a.  任务开始，向队列发送状态更新消息 (`'获取信息'`)。
    b.  执行 `ffprobe` 命令获取视频总时长，存入 `task.total_duration_seconds`。
    c.  向队列发送状态更新消息 (`'处理中'`)。
    d.  执行 `ffmpeg` 命令。
    e.  **循环**: 实时读取 `ffmpeg` 的 `stdout`，解析进度，计算百分比，并将进度消息放入队列。
    f.  **结束**:
        *   如果进程返回码为0，发送 `'已完成'` 状态消息。
        *   如果进程返回码非0，读取 `stderr` 获取错误详情，发送 `'失败'` 状态和错误信息消息。
5.  **主线程 (UI 线程)**:
    a.  `root.after()` 定时器触发 `update_ui` 函数。
    b.  `update_ui` 函数从队列中取出所有待处理消息。
    c.  根据消息中的 `id` 和 `type`，调用相应的视图更新方法，如 `view.update_task_in_list(id, {'progress': 75})` 或 `view.update_task_in_list(id, {'status': '失败'})`。
6.  **视图**: 接收到控制器的更新指令，刷新 `Treeview` 中对应行的数据（更新进度条值、修改状态文本、改变行背景色等）。

---

### 四、 打包与部署 (面向 Windows)

*   **工具**: **PyInstaller**
*   **打包命令关键参数**:
    *   `--onefile`: 生成单一的可执行文件，分发方便。
    *   `--windowed` 或 `--noconsole`: **必须**，GUI程序运行时不显示命令行黑窗。
    *   `--add-data "ffmpeg/ffmpeg.exe;ffmpeg"`: **打包核心**。将 `ffmpeg` 目录下的 `ffmpeg.exe` 文件包含进最终的包里，并在运行时将其放在一个名为 `ffmpeg` 的临时文件夹中。`ffprobe.exe` 同理。
    *   `--icon="path/to/your/icon.ico"`: 为你的 `.exe` 文件指定一个图标。

