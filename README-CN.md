# Kanban Launcher（看板启动器）

基于 PyQt6 构建的 Windows 桌面应用启动面板。将本地工具和项目以卡片网格形式组织，支持标签分类、模糊搜索、拖拽排序，并可调用 AI 自动生成项目描述。

![Python](https://img.shields.io/badge/python-3.10+-blue)
![PyQt](https://img.shields.io/badge/PyQt-6.6+-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## 功能特性

- **标签页导航** — 左侧竖排标签栏，按自定义分类筛选项目
- **卡片网格** — 每个项目以图标 + 名称 + 描述的卡片形式展示
- **即时搜索** — 模糊匹配项目名称、描述和标签，实时过滤
- **扫描同步** — 自动发现扫描目录下的新项目（默认 `D:\Tools`，可在设置中自定义），勾选即可导入
- **AI 智能描述** — 调用 DeepSeek 大模型分析项目文件，自动生成描述、标签和图标
- **双启动模式** — `startfile` 模式直接打开（exe / 文件夹），`command` 模式支持自定义命令行及参数
- **拖拽排序** — 长按卡片拖动调整顺序，支持置顶常用项目
- **键盘操作** — 方向键切换焦点，Enter 启动，Escape 清除搜索
- **安全删除** — 仅从启动器移除条目，绝不触碰磁盘文件


## 快速开始

### 环境要求

- Python 3.10 及以上
- Windows 操作系统（依赖 `os.startfile` 和 `subprocess.CREATE_NEW_CONSOLE`）

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/your-username/kanban-launcher.git
cd kanban-launcher

# 安装依赖
pip install PyQt6

# 从模板创建配置文件
cp config.example.json config.json

# 运行
python main.py
```

## 配置说明

所有数据存储在项目根目录的 `config.json` 中，结构示例如下：

```json
{
  "apps": [
    {
      "name": "示例项目",
      "path": "D:/Tools/my-project",
      "description": "一句话项目简介",
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

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 卡片上显示的项目名称 |
| `path` | string | 项目绝对路径（目录、`.exe` 或 `.lnk` 文件） |
| `description` | string | 卡片下方显示的简短描述 |
| `tags` | string[] | 所属标签列表，决定项目出现在哪个侧边栏分类中 |
| `icon` | string | 卡片上显示的单个 emoji 图标 |
| `launch_type` | string | `"startfile"` — 调用系统默认方式打开；`"command"` — 执行自定义命令 |
| `command` | string | 启动命令（仅 `"command"` 模式有效） |
| `args` | string | 追加到 `command` 之后的命令行参数 |

### 内置标签

`AI / 机器学习` · `系统工具` · `多媒体处理` · `个人开发作品` · `网络与办公` · `开发与逆向`

## AI 分析功能（可选）

扫描同步弹窗中提供 **"AI 描述"** 按钮，点击后自动分析项目的源代码文件，生成中文描述、建议标签和图标 emoji。

- **默认模型**：[DeepSeek](https://platform.deepseek.com/) `deepseek-v4-pro`（可在 `app/ai_service.py` 中更换）
- **分析范围**：优先读取 `README.md`，其次 `package.json`、`main.py` 等常见项目文件（单文件上限 12 KB）
- **隐私说明**：文件内容通过 HTTPS 发送至 DeepSeek API；API Key 仅保存在本地，不上传至任何第三方

### 配置 API Key

**方式一** — 设置环境变量（推荐）：
```powershell
# PowerShell
$env:DEEPSEEK_API_KEY = "sk-你的密钥"
```

```bash
# Git Bash / WSL
export DEEPSEEK_API_KEY="sk-你的密钥"
```

**方式二** — 在程序设置界面中填写（保存至 `config.json`）：
1. 点击工具栏的 **设置** 按钮
2. 在 **项目扫描目录** 中可自定义扫描路径，在 **DeepSeek API Key** 输入框中粘贴密钥
3. 点击 **确定**

> 环境变量的优先级高于配置文件中的值。两种方式任选其一即可。

## 项目结构

```
kanban-launcher/
├── main.py                    # 入口文件，主窗口逻辑
├── config.example.json        # 配置文件模板
├── style.qss                  # Qt 样式表（暖色浅色主题）
├── requirements.txt           # Python 依赖声明
└── app/
    ├── models.py              # AppEntry 数据模型
    ├── config_manager.py      # 配置读写 + D:\Tools 目录扫描
    ├── launcher.py            # 进程启动器（startfile / subprocess）
    ├── ai_service.py          # DeepSeek API 调用与响应解析
    ├── widgets/
    │   ├── sidebar.py         # 左侧标签导航栏
    │   ├── app_card.py        # 项目卡片组件（单击/双击/右键/拖拽）
    │   ├── app_grid.py        # 可滚动的流式卡片网格布局
    │   ├── toolbar.py         # 顶部搜索栏与操作按钮
    │   └── drag_controller.py # 拖拽排序控制器（含动画效果）
    └── dialogs/
        ├── app_editor.py      # 项目新增/编辑弹窗
        ├── sync_dialog.py     # 扫描同步弹窗（含 AI 分析按钮）
        └── settings_dialog.py # 设置弹窗（字体大小 + API Key）
```

## 开发计划

- [ ] 自定义标签管理与排序
- [ ] 按最近使用时间排序
- [ ] 项目使用频率统计
- [ ] 数据导入/导出
- [ ] 多语言支持
- [ ] 项目图标支持自定义图片

## 许可证

本项目采用 [MIT](LICENSE) 许可证。详见 [LICENSE](LICENSE) 文件。
