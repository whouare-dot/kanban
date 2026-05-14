"""AI-powered project analysis using DeepSeek API."""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

import os
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def set_api_key(key: str):
    """Set the API key at runtime (called from main after loading config)."""
    global API_KEY
    if key:
        API_KEY = key
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-flash"

# Files to read for project analysis — ordered by priority.
# README files listed first; they carry the most semantic signal.
ANALYSIS_FILES = [
    "README.md", "readme.md", "README.txt", "README", "readme",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "CMakeLists.txt", "Makefile", "makefile",
    "requirements.txt", "Pipfile", "Pipfile.lock",
    "main.py", "app.py", "index.js", "index.ts", "run.py",
    "composer.json",
]

# Read up to 12 KB from the most important files (README-class)
README_MAX_BYTES = 12000
# Read up to 5 KB from secondary files
SECONDARY_MAX_BYTES = 5000

# Available tags in the launcher
AVAILABLE_TAGS = [
    "AI / 机器学习", "系统工具", "多媒体处理",
    "个人开发作品", "网络与办公", "开发与逆向", "其他",
]

# Available emojis
AVAILABLE_EMOJIS = [
    "🤖", "🖼️", "🎬", "⚙️", "📝", "🌐", "📄", "🔧",
    "📁", "🎵", "📊", "💻", "🎮", "🔍", "🧠", "✨",
    "🛠️", "📦", "🎯", "💡", "🔑", "🌍", "📈", "🗂️",
    "🎨", "🔊", "📷", "📹", "🧩", "⚡", "🔥", "💎",
]

_README_NAMES = {"readme.md", "readme.txt", "readme", "readme.md"}


def _is_readme(name: str) -> bool:
    return name.lower() in _README_NAMES


def _read_project_files(project_path: str) -> str:
    """Read key files from project directory. Prioritises README-class files."""
    path = Path(project_path)
    parts: list[str] = []

    # List top-level contents for context
    try:
        entries = sorted(
            [e.name for e in path.iterdir() if not e.name.startswith(".")],
            key=lambda n: n.lower(),
        )[:40]
        if entries:
            parts.append(
                f"项目顶层结构 (共 {len(entries)} 项):\n"
                + "\n".join(f"  - {e}" for e in entries)
            )
    except Exception:
        pass

    # Read key files — README-class first with larger allowance
    for file_name in ANALYSIS_FILES:
        file_path = path / file_name
        if not file_path.is_file():
            continue
        try:
            max_bytes = README_MAX_BYTES if _is_readme(file_name) else SECONDARY_MAX_BYTES
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
            if content.strip():
                tag = " [README]" if _is_readme(file_name) else ""
                parts.append(f"\n=== {file_name}{tag} ===\n{content}")
        except Exception:
            pass

    if not parts:
        parts.append(f"(空项目目录: {path.name})")

    return "\n".join(parts)


def analyze_project(project_path: str, project_name: str) -> dict:
    """Analyze a project. Returns {description, tags, icon}.

    Raises RuntimeError with a descriptive Chinese message on failure.
    """
    pp = Path(project_path)
    if not pp.exists():
        raise RuntimeError(f"项目路径不存在: {project_path}")
    if not pp.is_dir():
        raise RuntimeError("非目录项目，无法进行 AI 分析")

    file_summary = _read_project_files(project_path)

    system_prompt = (
        "你是一个软件项目分析助手。根据提供的项目文件内容（特别是 README 文件），用中文给出：\n"
        "1. 一句简练描述（20字以内，模仿以下范例风格）：\n"
        '   - "节点式 Stable Diffusion 图像生成工作流界面"\n'
        '   - "本地 LLM/VLM 驱动的智能文件分类整理工具"\n'
        '   - "基于 MediaPipe + OpenCV 的本地坐姿监测桌面应用"\n'
        "2. 最合适的1个标签（从以下严格选择）：" + "、".join(AVAILABLE_TAGS) + "\n"
        "3. 最合适的1个图标emoji（从以下严格选择）：" + " ".join(AVAILABLE_EMOJIS) + "\n\n"
        "重要：如果项目有 README 文件，请重点依据其内容判断项目用途。\n\n"
        "严格按以下JSON格式回复，不要有任何额外文字：\n"
        '{"description": "...", "tags": ["..."], "icon": "..."}'
    )

    user_prompt = f"项目名称: {project_name}\n\n{file_summary}"

    response_text = _call_api(system_prompt, user_prompt)
    result = _parse_response(response_text)
    if result is None:
        raise RuntimeError(
            "AI 返回格式异常，未能提取有效描述。\n请重试或手动填写。"
        )
    return result


def _call_api(system_prompt: str, user_prompt: str) -> str:
    """Call DeepSeek chat API. Returns response text. Raises RuntimeError on failure."""
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }).encode("utf-8")

    if not API_KEY:
        raise RuntimeError(
            "未配置 DeepSeek API Key。\n"
            "请设置环境变量 DEEPSEEK_API_KEY，或在 ai_service.py 中填入密钥。"
        )

    try:
        req = urllib.request.Request(API_URL, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            detail = ""
        code = e.code
        if code == 401:
            raise RuntimeError("API Key 无效或已过期") from e
        if code == 429:
            raise RuntimeError("API 请求过于频繁，请稍后重试") from e
        if code == 404:
            raise RuntimeError(f"模型 {MODEL} 不存在或 API 地址错误") from e
        raise RuntimeError(f"API 返回错误 ({code}): {detail[:200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 API 服务器: {e.reason}") from e
    except json.JSONDecodeError:
        raise RuntimeError("API 返回了无效的 JSON 响应") from None
    except KeyError:
        raise RuntimeError("API 响应结构异常，缺少 choices/message/content") from None
    except Exception as e:
        raise RuntimeError(f"网络或系统错误: {e}") from e


def _parse_response(text: str) -> dict | None:
    """Extract JSON from AI response. Handles nested braces and markdown fences."""
    if not text:
        return None

    # 1. Strip markdown code fences: ```json ... ```  or  ``` ... ```
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        text = m.group(1)

    # 2. Try to find the outermost JSON object (handles nested braces)
    #    Find the first '{' and match to its corresponding '}'
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                json_str = text[start:i + 1]
                try:
                    data = json.loads(json_str)
                    return _validate_and_clean(data)
                except json.JSONDecodeError:
                    # Try to fix common AI mistakes: trailing commas, unquoted keys
                    pass
                break

    # 3. Last resort: try to fix and re-parse
    fixed = _try_fix_json(text, start)
    if fixed:
        try:
            data = json.loads(fixed)
            return _validate_and_clean(data)
        except json.JSONDecodeError:
            pass

    return None


def _validate_and_clean(data: dict) -> dict:
    """Validate AI-returned fields and return cleaned dict."""
    desc = str(data.get("description", "")).strip()
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()]
    icon = str(data.get("icon", "📦")).strip()

    valid_tags = [t for t in tags if t in AVAILABLE_TAGS]
    if not valid_tags:
        valid_tags = ["其他"]

    if icon not in AVAILABLE_EMOJIS:
        icon = "📦"

    return {
        "description": desc[:60],
        "tags": valid_tags,
        "icon": icon,
    }


def _try_fix_json(text: str, start: int) -> str | None:
    """Attempt to fix common AI JSON mistakes."""
    # Find the likely JSON region
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end <= start:
        return None

    region = text[start:end]

    # Remove trailing commas before } or ]
    region = re.sub(r',\s*}', '}', region)
    region = re.sub(r',\s*]', ']', region)

    # Fix single quotes used as JSON string delimiters
    # (only if the region doesn't already parse)
    try:
        json.loads(region)
        return region
    except json.JSONDecodeError:
        pass

    return None
