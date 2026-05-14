from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QScrollArea, QWidget, QCheckBox,
    QLineEdit, QFrame, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QCursor
from app.models import AppEntry


class AnalyzeWorker(QThread):
    """Background thread for AI project analysis."""
    finished = pyqtSignal(object, object)  # (item_data, result_dict | error_string)
    progress = pyqtSignal(str)  # status message

    def __init__(self, item_data: dict):
        super().__init__()
        self._item_data = item_data

    def run(self):
        from app.ai_service import analyze_project
        try:
            self.progress.emit("正在读取项目文件...")
            result = analyze_project(
                self._item_data["path"],
                self._item_data["name"],
            )
            if result:
                self.finished.emit(self._item_data, result)
            else:
                self.finished.emit(self._item_data, "无法分析（非目录项目或无可读文件）")
        except Exception as e:
            self.finished.emit(self._item_data, str(e))


class DiscoveredItemFrame(QFrame):
    """Widget for one discovered project in the sync list."""

    confirm_toggled = pyqtSignal()

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("discoveredItem")
        self.setStyleSheet("""
            #discoveredItem {
                background: #ffffff;
                border: 1px solid #e8e5e0;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        self._item_data = item_data
        self._analyzed = False
        self._worker: AnalyzeWorker | None = None
        self._tags_str = ", ".join(item_data.get("tags", []))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Row 0: checkbox + name + AI button
        top = QHBoxLayout()
        top.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.toggled.connect(lambda: self.confirm_toggled.emit())
        self.checkbox.setToolTip("确认导入此项目")
        top.addWidget(self.checkbox)

        self.icon_label = QLabel(item_data.get("icon", "📦"))
        self.icon_label.setStyleSheet("font-size: 20px; background: transparent;")
        top.addWidget(self.icon_label)

        self.name_label = QLabel(item_data["name"])
        self.name_label.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #1a1a18; background: transparent;")
        top.addWidget(self.name_label, stretch=1)

        self.path_label = QLabel(item_data["path"])
        self.path_label.setStyleSheet(
            "font-size: 10px; color: #8b8579; background: transparent;")
        top.addWidget(self.path_label)

        top.addStretch()

        self.ai_btn = QPushButton("🤖 AI 描述")
        self.ai_btn.setObjectName("aiDescBtn")
        self.ai_btn.setFixedWidth(90)
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background: #f0ede6; color: #5c5950;
                border: 1px solid #e2ded4; border-radius: 6px;
                padding: 4px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover {
                background: #e6dfcc; border-color: #d4a853; color: #2d2d2a;
            }
            QPushButton:disabled {
                background: #f7f5f0; color: #bbb8ae; border-color: #e8e5e0;
            }
        """)
        self.ai_btn.clicked.connect(self._on_ai_analyze)
        top.addWidget(self.ai_btn)

        layout.addLayout(top)

        # Row 1: description
        desc_row = QHBoxLayout()
        desc_row.setSpacing(6)
        desc_label = QLabel("描述:")
        desc_label.setStyleSheet(
            "font-size: 11px; color: #8b8579; background: transparent; font-weight: 500;")
        desc_label.setFixedWidth(36)
        desc_row.addWidget(desc_label)
        self.desc_edit = QLineEdit(item_data.get("description", ""))
        self.desc_edit.setPlaceholderText("（可选）项目简要描述")
        self.desc_edit.setStyleSheet("""
            QLineEdit {
                background: #f7f5f0; border: 1px solid #e2ded4; border-radius: 4px;
                padding: 3px 8px; font-size: 11px; color: #2d2d2a;
            }
            QLineEdit:focus { border-color: #d4a853; background: #fffdf7; }
        """)
        desc_row.addWidget(self.desc_edit, stretch=1)
        layout.addLayout(desc_row)

        # Row 2: tags
        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_label = QLabel("标签:")
        tags_label.setStyleSheet(
            "font-size: 11px; color: #8b8579; background: transparent; font-weight: 500;")
        tags_label.setFixedWidth(36)
        tags_row.addWidget(tags_label)
        self.tags_edit = QLineEdit(self._tags_str)
        self.tags_edit.setPlaceholderText("多个标签用逗号分隔")
        self.tags_edit.setStyleSheet(self.desc_edit.styleSheet())
        tags_row.addWidget(self.tags_edit, stretch=1)
        layout.addLayout(tags_row)

        # Row 3: icon
        icon_row = QHBoxLayout()
        icon_row.setSpacing(6)
        icon_label = QLabel("图标:")
        icon_label.setStyleSheet(
            "font-size: 11px; color: #8b8579; background: transparent; font-weight: 500;")
        icon_label.setFixedWidth(36)
        icon_row.addWidget(icon_label)
        self.icon_edit = QLineEdit(item_data.get("icon", "📦"))
        self.icon_edit.setMaximumWidth(50)
        self.icon_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_edit.setStyleSheet(self.desc_edit.styleSheet())
        icon_row.addWidget(self.icon_edit)
        icon_row.addStretch()
        layout.addLayout(icon_row)

        # Row 4: status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "font-size: 10px; color: #8b8579; background: transparent; font-style: italic;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    @property
    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def get_item_data(self) -> dict:
        """Return updated item data from the editable fields."""
        tags_str = self.tags_edit.text().strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        data = dict(self._item_data)
        data["description"] = self.desc_edit.text().strip()
        data["tags"] = tags
        data["icon"] = self.icon_edit.text().strip() or "📦"
        return data

    def _on_ai_analyze(self):
        if self._worker and self._worker.isRunning():
            return

        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("⏳ 分析中...")
        self.status_label.setText("正在读取项目文件...")
        self.status_label.setStyleSheet(
            "font-size: 10px; color: #d4a853; background: transparent; font-style: italic;")

        self._worker = AnalyzeWorker(self._item_data)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.start()

    def _on_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_ai_finished(self, item_data: dict, result):
        self._worker = None
        self.ai_btn.setText("🤖 AI 描述")
        self.ai_btn.setEnabled(True)

        if isinstance(result, str):
            # Error
            self.status_label.setText(f"❌ {result}")
            self.status_label.setStyleSheet(
                "font-size: 10px; color: #c44; background: transparent; font-style: italic;")
        else:
            self._analyzed = True
            self.desc_edit.setText(result.get("description", ""))
            self.tags_edit.setText(", ".join(result.get("tags", [])))
            self.icon_edit.setText(result.get("icon", "📦"))
            # Update the icon label at top too
            self.icon_label.setText(result.get("icon", "📦"))
            tags = result.get("tags", [])
            self.status_label.setText(f"✅ AI 分析完成 → 标签: {', '.join(tags)}")
            self.status_label.setStyleSheet(
                "font-size: 10px; color: #5a9; background: transparent; font-style: italic;")


class SyncDialog(QDialog):
    def __init__(self, discovered: list[dict], existing_apps: list[AppEntry], parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描同步 — 发现新项目")
        self.setMinimumSize(620, 520)
        self.resize(640, 600)
        self.setModal(True)

        self._items: list[DiscoveredItemFrame] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Header
        header = QLabel(f"在 D:\\Tools 下发现 <b>{len(discovered)}</b> 个新项目, 勾选要导入的项：")
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 13px; color: #2d2d2a; background: transparent;")
        layout.addWidget(header)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical {
                background: #d4cfc0; border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #b8b09a; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(10)

        for item_data in discovered:
            frame = DiscoveredItemFrame(item_data)
            frame.confirm_toggled.connect(self._update_ok_button)
            self._items.append(frame)
            self._container_layout.addWidget(frame)

        self._container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Toolbar row
        tools = QHBoxLayout()
        tools.setSpacing(8)

        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #5c5950;
                border: 1px solid #e2ded4; border-radius: 6px;
                padding: 5px 14px; font-size: 11px;
            }
            QPushButton:hover { background: #f7f5f0; border-color: #d4a853; }
        """)
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        tools.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.setStyleSheet(select_all_btn.styleSheet())
        deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        tools.addWidget(deselect_all_btn)

        tools.addStretch()

        analyze_all_btn = QPushButton("🤖 全部 AI 分析")
        analyze_all_btn.setStyleSheet("""
            QPushButton {
                background: #f0ede6; color: #5c5950;
                border: 1px solid #e2ded4; border-radius: 6px;
                padding: 5px 16px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background: #e6dfcc; border-color: #d4a853; color: #2d2d2a; }
        """)
        analyze_all_btn.clicked.connect(self._analyze_all)
        tools.addWidget(analyze_all_btn)

        layout.addLayout(tools)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #2d2d2a;
                border: 1px solid #e2ded4; border-radius: 8px;
                padding: 6px 24px; font-size: 13px;
            }
            QPushButton:hover { background: #f7f5f0; border-color: #d4a853; }
        """)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._update_ok_button()

    def _update_ok_button(self):
        count = sum(1 for item in self._items if item.is_checked)
        self._ok_button.setText(f"导入 ({count})" if count > 0 else "导入")
        self._ok_button.setEnabled(count > 0)

    def _set_all_checked(self, checked: bool):
        for item in self._items:
            item.set_checked(checked)
        self._update_ok_button()

    def _analyze_all(self):
        delay = 0
        for item in self._items:
            if item._worker and item._worker.isRunning():
                continue
            if item._item_data.get("path") and item._item_data["path"].strip():
                QTimer.singleShot(delay, item._on_ai_analyze)
                delay += 500  # stagger by 500ms to avoid rate limiting

    def get_selected(self) -> list[dict]:
        selected = []
        for item in self._items:
            if item.is_checked:
                selected.append(item.get_item_data())
        return selected

    def _on_accept(self):
        if self.get_selected():
            self.accept()
        else:
            QMessageBox.information(self, "提示", "请至少勾选一个项目导入。")
