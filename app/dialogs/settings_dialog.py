import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QWidget, QDialogButtonBox,
    QLineEdit, QFrame, QFileDialog,
)
from PyQt6.QtCore import Qt
from app.config_manager import CONFIG_PATH, DEFAULT_SCAN_PATH

FONT_SIZES = {
    "small":  {"card_name": 12, "card_desc": 10},
    "medium": {"card_name": 14, "card_desc": 11},
    "large":  {"card_name": 16, "card_desc": 13},
}

# Shared stylesheet snippet for input fields
_INPUT_STYLE = """
    QLineEdit {
        background: #ffffff; border: 1px solid #e2ded4; border-radius: 6px;
        padding: 7px 10px; font-size: 12px; color: #2d2d2a;
    }
    QLineEdit:focus { border-color: #d4a853; }
"""


class SettingsDialog(QDialog):
    def __init__(self, current_size: str, current_api_key: str = "",
                 current_scan_path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(440, 530)
        self.setModal(True)
        self._selected_size = current_size
        self._api_key = current_api_key
        self._scan_path = current_scan_path
        self._open_config = False

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # ── Font size ──────────────────────────────────────────
        size_label = QLabel("卡片文字大小")
        size_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #2d2d2a;")
        layout.addWidget(size_label)

        self._size_group = QButtonGroup(self)
        sizes_layout = QHBoxLayout()
        sizes_layout.setSpacing(8)
        for key, label in [("small", "小"), ("medium", "中"), ("large", "大")]:
            btn = QRadioButton(label)
            btn.setChecked(key == current_size)
            btn.toggled.connect(lambda checked, k=key: self._on_size_toggled(k, checked))
            self._size_group.addButton(btn)
            sizes_layout.addWidget(btn)
        sizes_layout.addStretch()
        layout.addLayout(sizes_layout)

        # Preview
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setStyleSheet("""
            #previewFrame {
                background: #ffffff; border: 1px solid #e8e5e0;
                border-radius: 8px; padding: 12px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setSpacing(4)
        self._preview_name = QLabel("示例应用")
        self._preview_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_desc = QLabel("这是卡片的示例描述")
        self._preview_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_desc.setStyleSheet("color: #8b8579;")
        preview_layout.addWidget(self._preview_name)
        preview_layout.addWidget(self._preview_desc)
        layout.addWidget(preview_frame)
        self._apply_preview(current_size)

        # ── Separator ──────────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background: #e8e5e0; max-height: 1px; border: none;")
        layout.addWidget(sep1)

        # ── Scan path ──────────────────────────────────────────
        scan_label = QLabel("项目扫描目录")
        scan_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #2d2d2a;")
        layout.addWidget(scan_label)

        scan_hint = QLabel(
            f"扫描同步时自动发现此目录下的新项目。\n默认: {DEFAULT_SCAN_PATH}"
        )
        scan_hint.setWordWrap(True)
        scan_hint.setStyleSheet("font-size: 11px; color: #8b8579; background: transparent;")
        layout.addWidget(scan_hint)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(6)

        self.scan_edit = QLineEdit(current_scan_path)
        self.scan_edit.setPlaceholderText(DEFAULT_SCAN_PATH)
        self.scan_edit.setClearButtonEnabled(True)
        self.scan_edit.setStyleSheet(_INPUT_STYLE)
        scan_row.addWidget(self.scan_edit, stretch=1)

        browse_btn = QPushButton("浏览...")
        browse_btn.setToolTip("选择扫描目录")
        browse_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #e2ded4;
                border-radius: 6px; padding: 7px 14px; font-size: 12px; color: #5c5950;
            }
            QPushButton:hover { background: #f7f5f0; border-color: #d4a853; }
        """)
        browse_btn.clicked.connect(self._browse_scan_path)
        scan_row.addWidget(browse_btn)

        layout.addLayout(scan_row)

        # ── Separator ──────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: #e8e5e0; max-height: 1px; border: none;")
        layout.addWidget(sep2)

        # ── API Key ────────────────────────────────────────────
        api_label = QLabel("DeepSeek API Key")
        api_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #2d2d2a;")
        layout.addWidget(api_label)

        api_hint = QLabel(
            "用于 AI 项目分析功能。密钥仅保存在本地 config.json 中。\n"
            "默认模型: deepseek-v4-pro"
        )
        api_hint.setWordWrap(True)
        api_hint.setStyleSheet("font-size: 11px; color: #8b8579; background: transparent;")
        layout.addWidget(api_hint)

        api_row = QHBoxLayout()
        api_row.setSpacing(6)

        self.api_edit = QLineEdit(current_api_key)
        self.api_edit.setPlaceholderText("sk-... 或留空使用环境变量 DEEPSEEK_API_KEY")
        self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_edit.setClearButtonEnabled(True)
        self.api_edit.setStyleSheet(_INPUT_STYLE)
        api_row.addWidget(self.api_edit, stretch=1)

        self._show_key_btn = QPushButton("👁")
        self._show_key_btn.setFixedWidth(34)
        self._show_key_btn.setToolTip("显示/隐藏密钥")
        self._show_key_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #e2ded4;
                border-radius: 6px; padding: 4px; font-size: 14px;
            }
            QPushButton:hover { background: #f7f5f0; border-color: #d4a853; }
        """)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        api_row.addWidget(self._show_key_btn)

        layout.addLayout(api_row)

        # ── Open config ────────────────────────────────────────
        config_btn = QPushButton("在编辑器中打开 config.json")
        config_btn.setObjectName("openConfigBtn")
        config_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #5c5950; border: 1px solid #e2ded4;
                border-radius: 8px; padding: 8px 16px; font-size: 12px;
            }
            QPushButton:hover {
                background: #f7f5f0; border-color: #d4a853; color: #2d2d2a;
            }
        """)
        config_btn.clicked.connect(self._on_open_config)
        layout.addWidget(config_btn)

        layout.addStretch()

        # ── OK / Cancel ─────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── slots ──────────────────────────────────────────────────

    def _on_size_toggled(self, key: str, checked: bool):
        if checked:
            self._selected_size = key
            self._apply_preview(key)

    def _apply_preview(self, size_key: str):
        s = FONT_SIZES[size_key]
        self._preview_name.setStyleSheet(
            f"font-size: {s['card_name']}px; font-weight: 600;")
        self._preview_desc.setStyleSheet(
            f"font-size: {s['card_desc']}px; color: #8b8579;")

    def _toggle_key_visibility(self):
        if self.api_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("🙈")
        else:
            self.api_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("👁")

    def _browse_scan_path(self):
        current = self.scan_edit.text().strip() or DEFAULT_SCAN_PATH
        # Start from the current value or its parent if it exists
        start_dir = current if os.path.isdir(current) else os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            self, "选择项目扫描目录", start_dir)
        if path:
            self.scan_edit.setText(path)

    def _on_open_config(self):
        self._open_config = True

    # ── properties ─────────────────────────────────────────────

    @property
    def selected_size(self) -> str:
        return self._selected_size

    @property
    def api_key(self) -> str:
        return self.api_edit.text().strip()

    @property
    def scan_path(self) -> str:
        raw = self.scan_edit.text().strip()
        return raw if raw else DEFAULT_SCAN_PATH

    @property
    def open_config_requested(self) -> bool:
        return self._open_config
