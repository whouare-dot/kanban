import json
import os
from pathlib import Path
from app.models import AppEntry

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
DEFAULT_SCAN_PATH = "D:/Tools"

# Canonical descriptions from README.md
KNOWN_PROJECTS: dict[str, dict] = {
    "ComfyUI": {
        "desc": "节点式 Stable Diffusion 图像生成工作流界面",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "sd-webui-aki-v4.11.1-cu128": {
        "desc": "Stable Diffusion WebUI (A1111)，含 ControlNet 等全套插件",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "Video2x": {
        "desc": "AI 视频/图像超分辨率与补帧工具（RealCUGAN/RealESRGAN/RIFE）",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "inpaint-QuShuiYin": {
        "desc": "纯浏览器端图像修复与超分工具（WebGPU/WASM，无需服务端）",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "lada": {
        "desc": "PyTorch + YOLO 封装的计算机视觉/视频分析桌面应用",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "AI File Sorter": {
        "desc": "本地 LLM/VLM 驱动的智能文件分类整理工具",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "Local-File-Organizer": {
        "desc": "离线 AI 文件分析归类工具（Llama3 + LLaVA，纯本地运行）",
        "tags": ["AI / 机器学习"], "icon": "🤖"
    },
    "图吧工具箱": {
        "desc": "集成式 PC 硬件检测与跑分套件（含 CPU-Z/GPU-Z/FurMark/AIDA64 等）",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "czkawka": {
        "desc": "Rust 编写的重复文件查找器与磁盘清理工具（含 GUI/CLI）",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "Mem Reduct": {
        "desc": "轻量级 Windows 内存实时监控与自动清理工具",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "spacesniffer": {
        "desc": "Treemap 可视化磁盘空间占用分析工具",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "ContextMenuManager.NET.4.0.exe": {
        "desc": "Windows 右键菜单管理工具（增删改查右键菜单项）",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "RyTuneX.exe.lnk": {
        "desc": "Windows 10/11 系统优化与隐私调校工具",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "OpenClow": {
        "desc": "空文件夹",
        "tags": ["系统工具"], "icon": "⚙️"
    },
    "ffmpeg-8.0-full_build": {
        "desc": "FFmpeg 全功能静态编译版（支持 AV1/HEVC/硬件加速等 80+ 外部库）",
        "tags": ["多媒体处理"], "icon": "🎬"
    },
    "LosslessCut-win-x64": {
        "desc": "基于 FFmpeg 的无损视频/音频剪切工具（Electron GUI）",
        "tags": ["多媒体处理"], "icon": "🎬"
    },
    "Caesium Image Compressor": {
        "desc": "图片有损/无损压缩工具，支持 PNG/JPEG 等格式",
        "tags": ["多媒体处理"], "icon": "🎬"
    },
    "My_tools": {
        "desc": "自用 Python 工具集（CopyAI 排版、DocToolbox、EditImg、PDF 降噪、fastclick 连点器）",
        "tags": ["个人开发作品"], "icon": "📝"
    },
    "YASIupup": {
        "desc": "基于豆包 LLM API 的雅思词汇学习桌面应用（PySide6 + SQLite）",
        "tags": ["个人开发作品"], "icon": "📝"
    },
    "yandere": {
        "desc": "多站点 Booru 图库增强油猴脚本（瀑布流/中文标签翻译/批量下载）",
        "tags": ["个人开发作品"], "icon": "📝"
    },
    "batesposture": {
        "desc": "基于 MediaPipe + OpenCV 的本地坐姿监测桌面应用（摄像头实时评分）",
        "tags": ["个人开发作品"], "icon": "📝"
    },
    "breaktimerApp": {
        "desc": "屏幕休息提醒工具（Electron + React，托盘运行，全屏覆盖通知）",
        "tags": ["个人开发作品"], "icon": "📝"
    },
    "Internet Download Manager": {
        "desc": "经典多线程下载加速器（IDM），支持浏览器集成与视频嗅探",
        "tags": ["网络与办公"], "icon": "🌐"
    },
    "Office Tool": {
        "desc": "第三方 Office 部署/激活/管理工具",
        "tags": ["网络与办公"], "icon": "📄"
    },
    "Office_Tool_with_runtime_v11.3.12.0_x64.zip": {
        "desc": "Office Tool Plus 便携版（自带 .NET Runtime）",
        "tags": ["网络与办公"], "icon": "📄"
    },
    "platform-tools": {
        "desc": "Android ADB/Fastboot 调试工具包（用于逆向分析）",
        "tags": ["开发与逆向"], "icon": "🔧"
    },
    "MelonLoader.Installer.exe": {
        "desc": "Unity 游戏 Mod 加载器安装器",
        "tags": ["开发与逆向"], "icon": "🔧"
    },
}


def _normalize(p: str) -> str:
    """Normalize a path to forward-slash form for consistent storage."""
    return os.path.normpath(p).replace("\\", "/")


def detect_launch_type(path: Path) -> tuple[str, str]:
    if not path.is_dir():
        return "startfile", ""

    contents = [f.name.lower() for f in path.iterdir()]
    if "main.py" in contents:
        return "command", "python main.py"
    if "app.py" in contents:
        return "command", "python app.py"
    if "package.json" in contents:
        return "command", "npm start"

    exe_files = [f.name for f in path.iterdir() if f.suffix.lower() == ".exe"]
    if exe_files:
        return "startfile", ""

    return "startfile", ""


def load_config(config_path: Path = None) -> tuple[list[AppEntry], dict]:
    if config_path is None:
        config_path = CONFIG_PATH
    if not config_path.exists():
        return [], {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    apps = []
    for item in data.get("apps", []):
        entry = AppEntry.from_dict(item)
        entry.path = _normalize(entry.path)
        apps.append(entry)
    settings = data.get("settings", {})
    # Normalize paths in settings
    if "card_order" in settings:
        settings["card_order"] = {
            tag: [_normalize(p) for p in paths]
            for tag, paths in settings["card_order"].items()
        }
    if "pinned" in settings:
        settings["pinned"] = {
            tag: [_normalize(p) for p in paths]
            for tag, paths in settings["pinned"].items()
        }
    return apps, settings


def save_config(apps: list[AppEntry], settings: dict | None = None,
                config_path: Path = None):
    """Atomically write config to disk (tmp + rename)."""
    if config_path is None:
        config_path = CONFIG_PATH

    data = {"apps": [app.to_dict() for app in apps]}

    if settings is None and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            old = json.load(f)
        settings = old.get("settings", {})
    if settings:
        data["settings"] = settings

    tmp_path = config_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(config_path)


def load_settings() -> dict:
    _, settings = load_config()
    return settings


def save_settings(settings: dict, apps: list[AppEntry] | None = None):
    """Persist settings efficiently. Pass apps to avoid extra disk read."""
    if apps is None:
        apps, _ = load_config()
    save_config(apps, settings)


def get_all_tags(apps: list[AppEntry]) -> list[str]:
    tags = set()
    for app in apps:
        for tag in app.tags:
            tags.add(tag)
    return sorted(tags)


def prune_empty_tags(apps: list[AppEntry]) -> list[str]:
    """Return tag list excluding tags with no assigned apps."""
    used = set()
    for app in apps:
        for tag in app.tags:
            used.add(tag)
    return sorted(used)


def get_scan_path(settings: dict | None = None) -> str:
    """Return the configured scan path, falling back to DEFAULT_SCAN_PATH."""
    if settings is None:
        _, settings = load_config()
    return settings.get("scan_path", DEFAULT_SCAN_PATH)


def scan_tools_directory(scan_path: str | None = None) -> list[dict]:
    """Scan a directory for new projects. Uses configured path if none given."""
    if scan_path is None:
        scan_path = get_scan_path()
    tools_path = Path(scan_path)
    if not tools_path.exists():
        return []

    discovered = []
    existing_paths = set()
    apps, _ = load_config()
    for app in apps:
        existing_paths.add(_normalize(app.path))

    for item in sorted(tools_path.iterdir()):
        if item.name.startswith(".") or item.name == "kanban-launcher":
            continue

        info = KNOWN_PROJECTS.get(item.name, {})

        if item.is_file():
            if item.suffix.lower() in (".exe", ".lnk"):
                abs_path = _normalize(str(item.resolve()))
                if abs_path in existing_paths:
                    continue
                discovered.append({
                    "name": item.stem,
                    "path": abs_path,
                    "description": info.get("desc", ""),
                    "tags": info.get("tags", ["其他"]),
                    "icon": info.get("icon", "📦"),
                    "launch_type": "startfile",
                    "command": "",
                })
            continue

        abs_path = _normalize(str(item.resolve()))
        if abs_path in existing_paths:
            continue

        lt, cmd = detect_launch_type(item)
        discovered.append({
            "name": item.name,
            "path": abs_path,
            "description": info.get("desc", ""),
            "tags": info.get("tags", ["其他"]),
            "icon": info.get("icon", "📦"),
            "launch_type": lt,
            "command": cmd,
        })

    return discovered


def append_to_card_orders(settings: dict, app_path: str, tags: list[str]):
    """Append normalized app_path to card_order entries for each tag and the all-view."""
    if "card_order" not in settings:
        settings["card_order"] = {}
    orders = settings["card_order"]
    npath = _normalize(app_path)
    for tag in (tags + [""]):
        lst = orders.get(tag, [])
        if npath not in lst:
            lst.append(npath)
            orders[tag] = lst


# ── pinned state ──────────────────────────────────────────────

def load_pinned() -> dict:
    _, settings = load_config()
    return settings.get("pinned", {})


def save_pinned(pinned: dict):
    apps, settings = load_config()
    settings["pinned"] = pinned
    save_config(apps, settings)


def toggle_pinned(settings: dict, tag: str, path: str) -> list:
    if "pinned" not in settings:
        settings["pinned"] = {}
    pinned_data = settings["pinned"]
    tag_list = pinned_data.get(tag, [])
    npath = _normalize(path)
    if npath in tag_list:
        tag_list = [p for p in tag_list if p != npath]
    else:
        tag_list.insert(0, npath)
    pinned_data[tag] = tag_list
    return tag_list
