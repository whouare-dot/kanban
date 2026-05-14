from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal


class Toolbar(QWidget):
    search_changed = pyqtSignal(str)
    search_cleared = pyqtSignal()
    sync_requested = pyqtSignal()
    add_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar")
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("搜索应用...（匹配名称、描述、标签）")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, stretch=1)

        self.sync_btn = QPushButton("扫描")
        self.sync_btn.setObjectName("syncBtn")
        self.sync_btn.setToolTip("扫描 D:\\Tools 中的新项目")
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

        self.add_btn = QPushButton("新建")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.setToolTip("手动添加新应用")
        self.add_btn.clicked.connect(self.add_requested.emit)
        layout.addWidget(self.add_btn)

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_btn)
