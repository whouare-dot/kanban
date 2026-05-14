from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox, QMessageBox, QLabel, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QWidget, QGridLayout, QFrame,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from app.models import AppEntry
from app.config_manager import get_all_tags

PRESET_EMOJIS = [
    "🤖", "🖼️", "🎬", "⚙️", "📝", "🌐", "📄", "🔧",
    "📁", "🎵", "📊", "💻", "🎮", "🔍", "🧠", "✨",
    "🛠️", "📦", "🎯", "💡", "🔑", "🌍", "📈", "🗂️",
    "🎨", "🔊", "📷", "📹", "🧩", "⚡", "🔥", "💎",
    "➡️", "📥", "🗑️", "✅", "⭐", "❤️", "👤", "📋",
]


class EmojiPicker(QFrame):
    emoji_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emojiPicker")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            #emojiPicker {
                background: #ffffff; border: 1px solid #e2ded4; border-radius: 10px;
            }
        """)
        cols = 8
        btn_size = 44
        spacing = 4
        margin = 10
        w = margin * 2 + cols * btn_size + (cols - 1) * spacing
        h = margin * 2 + ((len(PRESET_EMOJIS) + cols - 1) // cols) * btn_size + ((len(PRESET_EMOJIS) + cols - 1) // cols - 1) * spacing
        self.setFixedSize(w, h)

        layout = QGridLayout(self)
        layout.setSpacing(spacing)
        layout.setContentsMargins(margin, margin, margin, margin)

        for i, emoji in enumerate(PRESET_EMOJIS):
            btn = QPushButton(emoji)
            btn.setFixedSize(btn_size, btn_size)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; border: none; padding: 0px;
                    font-family: "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI", sans-serif;
                    font-size: 26px; border-radius: 8px;
                }
                QPushButton:hover { background: #f0ede6; }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, e=emoji: self._pick(e))
            layout.addWidget(btn, i // cols, i % cols)

    def _pick(self, emoji: str):
        self.emoji_selected.emit(emoji)
        self.hide()


class AppEditorDialog(QDialog):
    def __init__(self, entry: AppEntry, existing_tags: list[str], parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle(f"编辑 — {entry.name}" if entry.name else "新建应用")
        self.setMinimumSize(520, 500)
        self.setModal(True)
        self._all_tags = existing_tags

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit(entry.name)
        self.name_edit.setPlaceholderText("应用显示名称")
        form.addRow("名称:", self.name_edit)

        self.path_edit = QLineEdit(entry.path)
        self.path_edit.setPlaceholderText("D:/Tools/... (命令模式可选)")
        form.addRow("路径:", self.path_edit)

        self.desc_edit = QLineEdit(entry.description)
        self.desc_edit.setPlaceholderText("简要描述")
        form.addRow("描述:", self.desc_edit)

        # Icon row with emoji picker
        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        self.icon_edit = QLineEdit(entry.icon)
        self.icon_edit.setMaximumWidth(50)
        self.icon_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_edit.setPlaceholderText("📦")
        icon_row.addWidget(self.icon_edit)

        picker_btn = QPushButton("▾ 表情")
        picker_btn.setObjectName("emojiBtn")
        picker_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #5c5950; border: 1px solid #e2ded4;
                border-radius: 6px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background: #f7f5f0; border-color: #d4a853; }
        """)
        picker_btn.setToolTip("从预设表情中选择")
        picker_btn.clicked.connect(self._show_emoji_picker)
        icon_row.addWidget(picker_btn)
        icon_row.addStretch()

        icon_widget = QWidget()
        icon_widget.setLayout(icon_row)
        form.addRow("图标:", icon_widget)

        # Launch type with dropdown indicator
        launch_row = QHBoxLayout()
        launch_row.setSpacing(8)
        self.type_combo = QComboBox()
        self.type_combo.addItem("▸ 直接打开 — 直接打开 (exe/文件夹)", "startfile")
        self.type_combo.addItem("▸ 命令 — Shell 命令 (python/npm 等)", "command")
        idx = 0 if entry.launch_type == "startfile" else 1
        self.type_combo.setCurrentIndex(idx)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        launch_row.addWidget(self.type_combo, stretch=1)
        launch_hint = QLabel("点击展开 ▾")
        launch_hint.setStyleSheet("color: #8b8579; font-size: 10px;")
        launch_row.addWidget(launch_hint)
        launch_widget = QWidget()
        launch_widget.setLayout(launch_row)
        form.addRow("启动方式:", launch_widget)

        self.command_edit = QLineEdit(entry.command)
        self.command_edit.setPlaceholderText("例如 python main.py")
        form.addRow("命令:", self.command_edit)

        self.args_edit = QLineEdit(entry.args)
        self.args_edit.setPlaceholderText("可选参数")
        form.addRow("参数:", self.args_edit)

        layout.addLayout(form)

        # Tags
        tags_label = QLabel("标签:")
        layout.addWidget(tags_label)

        tag_layout = QHBoxLayout()
        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(100)
        for tag in existing_tags:
            checked = tag in entry.tags
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
        tag_layout.addWidget(self.tag_list, stretch=1)

        tag_btn_layout = QVBoxLayout()
        add_tag_btn = QPushButton("+")
        add_tag_btn.setFixedWidth(30)
        add_tag_btn.setToolTip("添加新标签")
        add_tag_btn.clicked.connect(self._add_new_tag)
        tag_btn_layout.addWidget(add_tag_btn)
        tag_btn_layout.addStretch()
        tag_layout.addLayout(tag_btn_layout)
        layout.addLayout(tag_layout)

        self._on_type_changed()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._emoji_picker: EmojiPicker | None = None

    def _show_emoji_picker(self):
        if self._emoji_picker is None:
            self._emoji_picker = EmojiPicker()
            self._emoji_picker.emoji_selected.connect(self._on_emoji_picked)
        pos = self.mapToGlobal(self.icon_edit.pos())
        pos.setY(pos.y() + self.icon_edit.height() + 4)
        self._emoji_picker.move(pos)
        self._emoji_picker.show()

    def _on_emoji_picked(self, emoji: str):
        self.icon_edit.setText(emoji)

    def _on_type_changed(self):
        is_command = self.type_combo.currentData() == "command"
        self.command_edit.setEnabled(is_command)
        self.args_edit.setEnabled(is_command)
        if is_command:
            self.command_edit.setPlaceholderText("例如 python main.py")
        else:
            self.command_edit.setPlaceholderText("(不需要)")

    def _add_new_tag(self):
        text, ok = QInputDialog.getText(self, "添加标签", "新标签名称:")
        if ok and text.strip():
            tag = text.strip()
            existing = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
            if tag not in existing:
                item = QListWidgetItem(tag)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.tag_list.addItem(item)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "错误", "名称为必填项")
            return
        lt = self.type_combo.currentData()
        if lt == "startfile" and not self.path_edit.text().strip():
            QMessageBox.warning(self, "错误", "直接打开模式需要填写路径")
            return
        if lt == "command" and not self.command_edit.text().strip():
            QMessageBox.warning(self, "错误", "命令模式需要填写命令")
            return
        self.accept()

    def get_entry(self) -> AppEntry:
        selected_tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tags.append(item.text())
        return AppEntry(
            name=self.name_edit.text().strip(),
            path=self.path_edit.text().strip(),
            description=self.desc_edit.text().strip(),
            tags=selected_tags,
            icon=self.icon_edit.text().strip() or "📦",
            launch_type=self.type_combo.currentData(),
            command=self.command_edit.text().strip(),
            args=self.args_edit.text().strip(),
        )

    @staticmethod
    def edit_entry(
        entry: AppEntry, existing_tags: list[str], parent=None
    ) -> AppEntry | None:
        dlg = AppEditorDialog(entry, existing_tags, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_entry()
        return None
