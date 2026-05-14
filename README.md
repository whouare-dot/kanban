<<<<<<< HEAD
# Kanban Launcher (看板启动器)

A PyQt6-based Windows desktop launcher that organizes local tools and projects into a searchable, tag-filtered card grid. Double-click to launch, drag to reorder, and let AI write descriptions for you.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![PyQt](https://img.shields.io/badge/PyQt-6.6+-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## Features

- **Tag-based navigation** — vertical sidebar with customisable categories
- **Card grid** — each project displayed as a card with icon, name, and description
- **Instant search** — fuzzy-match against name, description, and tags
- **Scan & sync** — auto-discover new projects under a configurable scan directory (default `D:\Tools`), import with one click
- **AI-powered descriptions** — let DeepSeek analyse your project files and suggest descriptions, tags, and icons
- **Dual launch modes** — `startfile` for exe/folders, or custom shell commands with arguments
- **Drag-and-drop reorder** — long-press cards to rearrange, pin frequently-used items
- **Keyboard navigation** — arrow keys to move, Enter to launch, Escape to clear search
- **Delete safely** — removes entries from the launcher only, never touches disk files


## Quick Start

### Prerequisites

- Python 3.10 or later
- Windows (uses `os.startfile` and `subprocess.CREATE_NEW_CONSOLE`)

### Installation

```bash
# Clone the repo
git clone https://github.com/your-username/kanban-launcher.git
cd kanban-launcher

# Install dependencies
pip install PyQt6

# Create your config from the template
cp config.example.json config.json

# Run
python main.py
```

## Configuration

All data lives in `config.json` at the project root. A minimal example:

```json
{
  "apps": [
    {
      "name": "My Project",
      "path": "D:/Tools/my-project",
      "description": "A one-line summary",
      "tags": ["个人开发作品"],
      "icon": "📝",
      "launch_type": "command",
      "command": "python main.py",
      "args": ""
    }
  ],
  "settings": {
    "card_font_size": "medium",
    "card_order": {},
    "pinned": {},
    "scan_path": "D:/Tools",
    "api_key": ""
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Display name on the card |
| `path` | Absolute path to the project (directory, `.exe`, or `.lnk`) |
| `description` | One-line summary shown below the name |
| `tags` | Array of category names; determines which sidebar tab the app appears under |
| `icon` | Single emoji character displayed on the card |
| `launch_type` | `"startfile"` — opens with `os.startfile`; `"command"` — runs a shell command |
| `command` | Shell command to execute (only for `"command"` launch type) |
| `args` | Additional command-line arguments appended to `command` |

### Built-in Tags

`AI / 机器学习` · `系统工具` · `多媒体处理` · `个人开发作品` · `网络与办公` · `开发与逆向`

## AI Analysis (Optional)

The scan-sync dialog includes an **"AI 描述"** button that analyses your project's source files and auto-generates a description, tags, and icon.

- **Model**: [DeepSeek](https://platform.deepseek.com/) `deepseek-v4-pro` (configurable in `app/ai_service.py`)
- **What it reads**: `README.md`, `package.json`, `main.py`, and other common project files (max 12 KB per file)
- **Privacy**: Files are sent to the DeepSeek API; your API key stays local

### Setting up the API Key

**Option A** — Set an environment variable (recommended):
```powershell
$env:DEEPSEEK_API_KEY = "sk-your-key-here"
```

**Option B** — Enter it in the Settings dialog (saved to `config.json`):
1. Click **设置** in the toolbar
2. Customize the **scan path** and paste your key in the **DeepSeek API Key** field
3. Click **OK**

The environment variable takes precedence over the config file value.

## Project Structure

```
kanban-launcher/
├── main.py                    # Entry point, main window
├── config.example.json        # Config template
├── style.qss                  # Qt stylesheet (warm light theme)
├── requirements.txt           # PyQt6
└── app/
    ├── models.py              # AppEntry dataclass
    ├── config_manager.py      # JSON read/write + D:\Tools scanner
    ├── launcher.py            # Process launcher (startfile / subprocess)
    ├── ai_service.py          # DeepSeek API integration for AI analysis
    ├── widgets/
    │   ├── sidebar.py         # Vertical tag navigation
    │   ├── app_card.py        # Individual project card
    │   ├── app_grid.py        # Scrollable flow-layout card grid
    │   ├── toolbar.py         # Search bar + action buttons
    │   └── drag_controller.py # Drag-and-drop reorder logic
    └── dialogs/
        ├── app_editor.py      # Add/edit project dialog
        ├── sync_dialog.py     # Scan & import dialog (with AI button)
        └── settings_dialog.py # Font size + API key settings
```

## License

MIT — see [LICENSE](LICENSE) for details.
=======
# kanban
基于 PyQt6 构建的 Windows 桌面应用启动面板。将本地工具和项目以卡片网格形式组织，支持标签分类、模糊搜索、拖拽排序，并可调用 AI 自动生成项目描述。
