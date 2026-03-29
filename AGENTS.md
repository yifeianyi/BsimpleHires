# BsimpleHires - AGENTS.md

> 本文档供 AI Coding Agent 阅读，用于快速理解项目架构和开发规范。

---

## 项目概述

**BsimpleHires** 是一个 Windows 桌面应用程序，用于将音视频文件转换为符合 B 站「Hi-Res 音质」认证的上传格式。核心功能是将视频流直接复制，音频转换为 PCM 24bit 格式，封装为 MOV 容器。

### 核心技术规格
- **目标格式**: MOV 容器 + PCM 24bit 音频 + 原始视频流复制
- **采样率策略**: <48kHz 升至 48kHz，≥48kHz 保持原样
- **运行平台**: Windows（依赖 FFmpeg 可执行文件）

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 编程语言 | Python 3.x |
| GUI 框架 | PyQt6 |
| 媒体处理 | FFmpeg (ffprobe/ffmpeg/ffplay) |
| 打包工具 | PyInstaller |
| UI 设计 | Qt Designer (.ui 文件) |

---

## 项目结构

```
BsimpleHires/
│
├── main.py                 # 程序入口
├── main.spec              # PyInstaller 打包配置
├── models.py              # 数据模型 (FileInfo, FileManager)
│
├── views/                 # UI 视图层
│   ├── mainwindow.py      # 主窗口 (导入文件入口)
│   ├── workpage.py        # 工作页面 (文件列表、转换操作)
│   └── progress_dialog.py # 进度对话框
│
├── services/              # 业务服务层
│   ├── ffmpeg_service.py  # FFmpeg 信息读取服务
│   └── converter_service.py # 视频转换核心服务
│
├── workers/               # 后台工作线程
│   └── conversion_worker.py # 转换任务工作线程
│
├── ui/                    # UI 文件
│   ├── main.ui            # 主界面设计
│   ├── workPage.ui        # 工作页面设计
│   ├── ProgressBar.ui     # 进度条对话框设计
│   ├── UI_main.py         # pyuic6 生成 (勿手动编辑)
│   ├── UI_workPage.py     # pyuic6 生成 (勿手动编辑)
│   └── UI_ProgressBar.py  # pyuic6 生成 (勿手动编辑)
│
├── ffmpeg/                # FFmpeg 可执行文件 (外部依赖)
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ffplay.exe
│
├── assets/                # 资源文件
│   └── logo.ico           # 应用图标
│
├── bug/                   # Bug 记录和调试文档
├── doc/                   # 项目文档
├── test/                  # 测试文件 (空)
├── build/                 # PyInstaller 构建输出
└── dist/                  # 最终可执行文件输出
```

---

## 架构设计

### 分层架构

1. **Models 层** (`models.py`)
   - `FileInfo`: 文件信息数据类，包含音视频元数据
   - `FileManager`: 文件列表管理器，纯数据操作

2. **Views 层** (`views/`)
   - 使用 PyQt6 实现界面
   - `MainWindow`: 应用入口，导入文件按钮
   - `WorkPage`: 核心工作区，文件列表展示、转换控制
   - `ProgressDialog`: 转换进度展示

3. **Services 层** (`services/`)
   - `FFmpegService`: 封装 ffprobe 获取媒体文件信息
   - `ConverterService`: 封装 ffmpeg 转换逻辑，支持批量多线程

4. **Workers 层** (`workers/`)
   - `ConversionWorker`: 继承 QObject，通过 pyqtSignal 与主线程通信
   - `ConversionThreadManager`: 管理转换线程生命周期

### 线程模型

- **主线程**: UI 渲染和用户交互
- **工作线程**: `ConversionWorker` 运行在独立 QThread 中
- **并发转换**: 使用 `ThreadPoolExecutor` 实现多文件并行转换 (默认 2-4 线程)

### 信号槽机制

```python
# ConversionWorker 信号
progress_updated.emit(ConversionProgress)  # 进度更新
finished.emit(list)                         # 转换完成
error.emit(str)                             # 错误通知
cancel_requested.emit()                     # 用户取消
```

---

## 开发规范

### 代码风格

- **命名规范**: 
  - 类名: PascalCase (如 `ConversionWorker`)
  - 方法/变量: snake_case (如 `get_file_info`)
  - 常量: 全大写
- **缩进**: 4 个空格
- **编码**: UTF-8

### UI 开发流程

1. 使用 Qt Designer 编辑 `.ui` 文件
2. 使用 `pyuic6` 生成 Python 代码:
   ```bash
   pyuic6 -o ui/UI_main.py ui/main.ui
   ```
3. **警告**: 不要手动编辑 `UI_*.py` 文件，所有自定义逻辑写在对应的 views 文件中

### 资源路径处理

项目支持开发环境和打包后环境，使用统一的资源路径函数:

```python
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的环境"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 临时目录
    except AttributeError:
        base_path = os.path.abspath(".")  # 开发环境
    return os.path.join(base_path, relative_path)
```

---

## 构建与打包

### 开发运行

```bash
# 激活虚拟环境
venv\Scripts\activate

# 运行程序
python main.py
```

### 打包命令

```bash
# 使用 PyInstaller 打包
pyinstaller main.spec

# 输出目录
# - build/ : 临时构建文件
# - dist/BsimpleHires.exe : 最终可执行文件
```

### 打包配置要点 (`main.spec`)

- **外部依赖**: FFmpeg 不打包进 exe，保持外部文件夹形式
- **Hidden Imports**: 需要显式导入所有 views/services/workers/ui 模块
- **排除模块**: 排除 numpy/scipy/matplotlib 等减少体积
- **单文件模式**: `console=False` 生成 GUI 程序

---

## 依赖说明

### 必需依赖

```
PyQt6>=6.0
```

### 外部二进制依赖

项目依赖 FFmpeg 可执行文件，查找优先级:
1. 系统 PATH 中的 ffmpeg/ffprobe
2. 程序同级目录 `ffmpeg/` 文件夹

开发时需确保 `ffmpeg/` 目录包含:
- `ffmpeg.exe`
- `ffprobe.exe`

---

## 测试策略

**现状**: 项目暂无自动化测试套件。

**测试方式**:
- 手动功能测试通过 UI 操作
- Bug 记录在 `bug/` 目录下的 Markdown 文件
- 测试文件可放在 `test/` 目录 (已被 .gitignore 忽略)

---

## 常见问题与注意事项

### 1. 模块导入问题

打包后可能出现 `ModuleNotFoundError`，需在 `main.spec` 的 `hiddenimports` 中添加:

```python
hidden_imports = [
    'views.mainwindow',
    'views.workpage',
    'services.converter_service',
    # ... 其他自定义模块
]
```

### 2. 多线程安全

- UI 更新必须在主线程进行
- `ConversionWorker` 使用信号槽与主线程通信
- 线程池并发数根据文件数量动态计算 (最多 4 线程)

### 3. FFmpeg 路径

- 开发环境: 查找项目根目录的 `ffmpeg/` 文件夹
- 打包后: 查找 exe 同级目录的 `ffmpeg/` 文件夹
- 优先使用系统 PATH 中的 FFmpeg

### 4. 文件编码

所有 Python 文件使用 UTF-8 编码，确保中文字符正确处理。

---

## 调试技巧

- 启用详细日志: 代码中已包含大量 `print()` 调试信息
- FFmpeg 命令输出: 转换服务会打印完整 ffmpeg 命令和输出
- 进度追踪: 通过 `ConversionProgress` 对象传递详细进度信息

---

## 扩展建议

1. **添加设置功能**: 可在 `views/` 新增 `settings_dialog.py`
2. **支持更多格式**: 修改 `converter_service.py` 中的 ffmpeg 参数
3. **预设配置**: 在 `services/` 添加预设管理服务
4. **日志系统**: 用标准库 `logging` 替换现有的 `print()` 调试
