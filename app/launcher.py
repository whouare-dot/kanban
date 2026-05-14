import os
import sys
import subprocess
import tempfile
import atexit
import shutil
from pathlib import Path
from app.models import AppEntry

# Common install locations for tools that may not be on PATH in non-interactive shells
TOOL_SEARCH_DIRS = [
    os.path.expandvars(r"%USERPROFILE%\miniconda3"),
    os.path.expandvars(r"%USERPROFILE%\anaconda3"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Python"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Roaming\npm"),
    r"C:\ProgramData\miniconda3",
    r"C:\ProgramData\anaconda3",
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
    os.path.expandvars(r"%ProgramData%\miniconda3"),
    os.path.expandvars(r"%ProgramData%\anaconda3"),
]

TOOL_EXECUTABLES = {
    "conda": ["Scripts/conda.exe", "condabin/conda.bat"],
    "python": ["python.exe"],
    "python3": ["python3.exe"],
    "node": ["node.exe"],
    "npm": ["npm.cmd"],
    "npx": ["npx.cmd"],
}

# Track temp files for cleanup on exit
_temp_files: set[Path] = set()


def _cleanup_temp_files():
    for p in list(_temp_files):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


atexit.register(_cleanup_temp_files)


def resolve_tool_path(tool_name: str) -> str | None:
    """Find the absolute path to a tool executable (conda, python, node, npm)."""
    candidates = TOOL_EXECUTABLES.get(tool_name, [tool_name + ".exe"])

    which = shutil.which(tool_name)
    if which:
        return which

    for base in TOOL_SEARCH_DIRS:
        base_path = Path(base)
        if base_path.is_dir():
            for rel in candidates:
                p = base_path / rel
                if p.is_file():
                    return str(p)

    return None


def resolve_command_paths(cmd: str) -> str:
    """Replace bare tool names with absolute paths for tools not on PATH."""
    import shlex

    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return cmd

    tool_names = {"conda", "python3", "python", "node", "npm", "npx"}
    replaced = []
    for token in tokens:
        if token in tool_names:
            full = resolve_tool_path(token)
            if full:
                if " " in full:
                    replaced.append(f'"{full}"')
                else:
                    replaced.append(full)
                continue
        replaced.append(token)

    # Rejoin preserving original quoting intent
    result = " ".join(replaced)

    # Handle shell operators (&&, ||, |, etc.) — shlex treats them as tokens,
    # so they survive the join correctly. But we need to handle operators that
    # were surrounded by spaces in the original.
    # Simple approach: if shlex failed to parse, fall back to regex
    # If shlex succeeded, the join is correct.
    return result


def _needs_bat_file(cmd: str) -> bool:
    operators = ["&&", "||", "|", ">", ">>", "<"]
    return any(op in cmd for op in operators)


def _write_temp_bat(cmd: str, cwd: str | None = None) -> Path:
    fd, path = tempfile.mkstemp(suffix=".bat", prefix="kanban_launch_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n")
        if cwd:
            f.write(f'cd /d "{cwd}"\r\n')
        f.write(f"echo [Kanban Launcher] Starting...\r\n")
        f.write(f'echo   CWD: {cwd or os.getcwd()}\r\n')
        f.write(f"echo.\r\n")
        f.write(f"{cmd}\r\n")
        f.write("set _EXIT=%ERRORLEVEL%\r\n")
        f.write("echo.\r\n")
        f.write(f"echo [Kanban Launcher] Process exited with code %_EXIT%\r\n")
        f.write("pause\r\n")
    return Path(path)


def launch_app(entry: AppEntry) -> tuple[bool, str]:
    """Launch an app. Returns (success, error_message)."""
    try:
        if entry.launch_type != "command":
            os.startfile(entry.path)
            return True, ""

        cmd = entry.command.strip()
        if entry.args.strip():
            cmd += " " + entry.args.strip()

        if not cmd:
            os.startfile(entry.path)
            return True, ""

        if entry.path and os.path.isdir(entry.path):
            cwd = entry.path
        elif entry.path:
            cwd = os.path.dirname(entry.path)
        else:
            cwd = os.getcwd()

        if not os.path.isdir(cwd):
            cwd = os.getcwd()

        cmd = resolve_command_paths(cmd)

        if _needs_bat_file(cmd):
            bat_path = _write_temp_bat(cmd, cwd)
            _temp_files.add(bat_path)
            subprocess.Popen(
                f'start "" cmd /c "{bat_path}"',
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        return True, ""
    except FileNotFoundError as e:
        return False, f"File not found:\n{e.filename}"
    except Exception as e:
        return False, str(e)
