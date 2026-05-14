from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt


class Sidebar(QWidget):
    tag_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(148)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("  标签")
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(46)
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("tagList")
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

    def set_tags(self, tags: list[str]):
        self.list_widget.clear()

        all_item = QListWidgetItem("  全部")
        all_item.setData(Qt.ItemDataRole.UserRole, "")
        self.list_widget.addItem(all_item)

        for tag in tags:
            item = QListWidgetItem(f"  {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)

    def _on_selection_changed(self, row: int):
        if row < 0:
            return
        item = self.list_widget.item(row)
        if item:
            tag = item.data(Qt.ItemDataRole.UserRole)
            self.tag_selected.emit(tag)

    def select_tag(self, tag: str):
        key = "" if tag == "全部" else tag
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                self.list_widget.setCurrentRow(row)
                return
