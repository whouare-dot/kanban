import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMessageBox, QStatusBar,
)
from PyQt6.QtCore import Qt

from app.models import AppEntry
from app.config_manager import (
    load_config, save_config, save_settings, get_all_tags,
    prune_empty_tags, scan_tools_directory, append_to_card_orders,
    toggle_pinned, get_scan_path, DEFAULT_SCAN_PATH, CONFIG_PATH,
)
from app.launcher import launch_app
import app.ai_service as ai_service
from app.widgets.sidebar import Sidebar
from app.widgets.app_grid import AppGrid
from app.widgets.toolbar import Toolbar
from app.dialogs.app_editor import AppEditorDialog
from app.dialogs.sync_dialog import SyncDialog
from app.dialogs.settings_dialog import SettingsDialog, FONT_SIZES


class KanbanLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("看板启动器")
        self.resize(1120, 700)
        self.setMinimumSize(820, 520)

        self._apps: list[AppEntry] = []
        self._current_tag: str = ""
        self._settings: dict = {}
        self._font_size_key: str = "small"

        self._init_ui()
        self._load()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.tag_selected.connect(self._on_tag_changed)
        main_layout.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.toolbar = Toolbar()
        self.toolbar.search_changed.connect(self._on_search_changed)
        self.toolbar.search_cleared.connect(self._on_search_cleared)
        self.toolbar.sync_requested.connect(self._on_sync)
        self.toolbar.add_requested.connect(self._on_add)
        self.toolbar.settings_requested.connect(self._on_settings)
        right_layout.addWidget(self.toolbar)

        self.grid = AppGrid()
        self.grid.launch_requested = self._on_card_launch
        self.grid.edit_requested = self._on_card_edit
        self.grid.delete_requested.connect(self._on_card_delete)
        self.grid.order_changed.connect(self._on_card_order_changed)
        self.grid.pin_toggled.connect(self._on_pin_toggled)
        self.grid.escape_pressed.connect(self._on_search_cleared)
        right_layout.addWidget(self.grid, stretch=1)

        main_layout.addWidget(right, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _load(self):
        self._apps, self._settings = load_config()
        self._font_size_key = self._settings.get("card_font_size", "small")
        # Set API key from config (env var takes precedence in ai_service module)
        api_key = self._settings.get("api_key", "")
        if api_key:
            ai_service.set_api_key(api_key)
        self._apply_font_size()
        self._refresh_all()

    def _apply_font_size(self):
        s = FONT_SIZES.get(self._font_size_key, FONT_SIZES["small"])
        self.grid.set_font_sizes(s["card_name"], s["card_desc"])

    def _refresh_all(self):
        tags = prune_empty_tags(self._apps)
        self.sidebar.set_tags(tags)
        self.grid.set_card_order(self._settings.get("card_order", {}))
        self.grid.set_pinned(self._settings.get("pinned", {}))
        self.grid.set_apps(self._apps)
        self.grid.set_tag(self._current_tag)
        self.status_bar.showMessage(f"{len(self._apps)} 个应用")

    def _on_tag_changed(self, tag: str):
        self._current_tag = tag if tag else ""
        self.grid.set_tag(self._current_tag)

    def _on_search_changed(self, text: str):
        self.grid.set_search(text)

    def _on_search_cleared(self):
        self.toolbar.search_input.clear()
        self.grid.setFocus()

    def _on_card_order_changed(self, tag: str, ordered_paths: list):
        if "card_order" not in self._settings:
            self._settings["card_order"] = {}
        self._settings["card_order"][tag] = ordered_paths
        save_settings(self._settings, self._apps)
        self._refresh_all()

    def _on_pin_toggled(self, tag: str, path: str):
        toggle_pinned(self._settings, tag, path)
        if "card_order" not in self._settings:
            self._settings["card_order"] = {}
        if "pinned" not in self._settings:
            self._settings["pinned"] = {}
        pinned_tag = self._settings["pinned"].get(tag, [])
        order = self._settings["card_order"].get(tag, [])
        if order:
            pinned_set = set(os.path.normpath(p) for p in pinned_tag)
            pinned_in_order = [p for p in order
                               if os.path.normpath(p) in pinned_set]
            unpinned_in_order = [p for p in order
                                 if os.path.normpath(p) not in pinned_set]
            self._settings["card_order"][tag] = pinned_in_order + unpinned_in_order
        save_settings(self._settings, self._apps)
        self._refresh_all()

    def _on_card_delete(self, entry: AppEntry):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 \"{entry.name}\" 吗？\n\n"
            f"路径: {entry.path}\n\n"
            f"此操作仅从启动器中移除，不会删除磁盘文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Remove from apps list
        self._apps = [a for a in self._apps if a.path != entry.path]

        # Remove from card_order and pinned in settings
        for tag_paths in self._settings.get("card_order", {}).values():
            if entry.path in tag_paths:
                tag_paths.remove(entry.path)
        for tag_paths in self._settings.get("pinned", {}).values():
            if entry.path in tag_paths:
                tag_paths.remove(entry.path)

        save_config(self._apps, self._settings)
        self._refresh_all()
        self.status_bar.showMessage(f"已删除: {entry.name}", 3000)

    def _on_card_launch(self, entry: AppEntry):
        ok, err = launch_app(entry)
        if ok:
            entry.last_used = datetime.now(timezone.utc).isoformat()
            save_config(self._apps, self._settings)
            self.status_bar.showMessage(f"已启动: {entry.name}", 3000)
        else:
            detail = err or entry.path
            QMessageBox.warning(self, "启动失败", f"无法启动:\n{detail}")

    def _on_card_edit(self, entry: AppEntry):
        tags = get_all_tags(self._apps)
        result = AppEditorDialog.edit_entry(entry, tags, self)
        if result:
            for a in self._apps:
                if a.path == result.path:
                    a.name = result.name
                    a.description = result.description
                    a.tags = result.tags
                    a.icon = result.icon
                    a.launch_type = result.launch_type
                    a.command = result.command
                    a.args = result.args
                    break
            save_config(self._apps, self._settings)
            self._refresh_all()

    def _on_sync(self):
        scan_path = get_scan_path(self._settings)
        discovered = scan_tools_directory(scan_path)
        if not discovered:
            QMessageBox.information(
                self, "扫描", f"在 {scan_path} 中未发现新项目。")
            return

        dlg = SyncDialog(discovered, self._apps, self)
        if dlg.exec() == SyncDialog.DialogCode.Accepted:
            selected = dlg.get_selected()
            for item_data in selected:
                entry = AppEntry(
                    name=item_data["name"],
                    path=item_data["path"],
                    description=item_data.get("description", ""),
                    tags=item_data["tags"],
                    icon=item_data["icon"],
                    launch_type=item_data["launch_type"],
                    command=item_data["command"],
                )
                self._apps.append(entry)
                append_to_card_orders(self._settings, entry.path, entry.tags)
            save_config(self._apps, self._settings)
            self._refresh_all()
            self.status_bar.showMessage(f"已导入 {len(selected)} 个项目", 5000)

    def _on_add(self):
        tags = get_all_tags(self._apps)
        result = AppEditorDialog.edit_entry(
            AppEntry(name="", path="", description="", tags=[]), tags, self
        )
        if result:
            self._apps.append(result)
            append_to_card_orders(self._settings, result.path, result.tags)
            save_config(self._apps, self._settings)
            self._refresh_all()
            self.status_bar.showMessage(f"已添加: {result.name}", 3000)

    def _on_settings(self):
        current_key = self._settings.get("api_key", "")
        current_scan = self._settings.get("scan_path", "")
        dlg = SettingsDialog(
            self._font_size_key, current_key, current_scan, self)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            changed = False
            new_size = dlg.selected_size
            if new_size != self._font_size_key:
                self._font_size_key = new_size
                self._settings["card_font_size"] = new_size
                changed = True
            new_key = dlg.api_key
            if new_key != current_key:
                self._settings["api_key"] = new_key
                ai_service.set_api_key(new_key)
                changed = True
            new_scan = dlg.scan_path
            if new_scan != current_scan:
                self._settings["scan_path"] = new_scan
                changed = True
            if changed:
                save_settings(self._settings, self._apps)
                self._apply_font_size()
                self._refresh_all()
            if dlg.open_config_requested:
                os.startfile(str(CONFIG_PATH))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    qss_path = Path(__file__).parent / "style.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = KanbanLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
