from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMenu, QWidgetAction, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from app.models import AppEntry

CARD_WIDTH = 172
CARD_HEIGHT = 140
LONG_PRESS_MS = 250
DRAG_THRESHOLD = 5

# Pre-built stylesheets for each state combination
_STYLE_NORMAL = """
    #appCard { background: #ffffff; border: 1px solid #e8e5e0; border-radius: 12px; }
    #appCard:hover { background: #fffdf7; border: 1px solid #d4a853; }
"""
_STYLE_SELECTED = """
    #appCard { background: #fef9ee; border: 1px solid #d4a853; border-radius: 12px; }
    #appCard:hover { background: #fef9ee; border: 1px solid #d4a853; }
"""
_STYLE_PINNED = """
    #appCard { background: #f2eee3; border: 1px solid #d4c898; border-radius: 12px; }
    #appCard:hover { background: #f5f0e5; border: 1px solid #d4a853; }
"""
_STYLE_PINNED_SELECTED = """
    #appCard { background: #e8dfc5; border: 1px solid #d4a853; border-radius: 12px; }
    #appCard:hover { background: #e8dfc5; border: 1px solid #d4a853; }
"""


class AppCard(QFrame):
    launch_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    selected = pyqtSignal(object)
    drag_started = pyqtSignal(object)
    pin_toggled = pyqtSignal(object)

    def __init__(self, entry: AppEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("appCard")
        self._selected = False
        self._pinned = False
        self._press_pos = None
        self._long_press_triggered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)

        self._press_timer = QTimer(self)
        self._press_timer.setSingleShot(True)
        self._press_timer.setInterval(LONG_PRESS_MS)
        self._press_timer.timeout.connect(self._on_long_press)

        # Pin icon (top-right corner)
        self.pin_label = QLabel("📌", self)
        self.pin_label.setObjectName("pinIcon")
        self.pin_label.setFixedSize(22, 22)
        self.pin_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pin_label.move(CARD_WIDTH - 24, 2)
        self.pin_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        self.icon_label = QLabel(entry.icon)
        self.icon_label.setObjectName("cardIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(26)
        self.icon_label.setFont(icon_font)
        layout.addWidget(self.icon_label)

        self.name_label = QLabel(entry.name)
        self.name_label.setObjectName("cardName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(36)
        layout.addWidget(self.name_label)

        self.desc_label = QLabel(entry.description)
        self.desc_label.setObjectName("cardDesc")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumHeight(30)
        layout.addWidget(self.desc_label)

        self._update_tooltip()

    def set_font_sizes(self, name_size: int, desc_size: int):
        self.name_label.setStyleSheet(
            f"color: #1a1a18; font-size: {name_size}px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        self.desc_label.setStyleSheet(
            f"color: #8b8579; font-size: {desc_size}px;"
            f" background: transparent; border: none; padding: 0 2px;"
        )

    @property
    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, sel: bool):
        if self._selected == sel:
            return
        self._selected = sel
        self._apply_state_style()

    def set_pinned(self, pinned: bool):
        if self._pinned == pinned:
            return
        self._pinned = pinned
        self.pin_label.setVisible(pinned)
        self._apply_state_style()

    def _apply_state_style(self):
        """Efficiently toggle stylesheet by state without unpolish/polish."""
        if self._selected and self._pinned:
            self.setStyleSheet(_STYLE_PINNED_SELECTED)
        elif self._selected:
            self.setStyleSheet(_STYLE_SELECTED)
        elif self._pinned:
            self.setStyleSheet(_STYLE_PINNED)
        else:
            self.setStyleSheet(_STYLE_NORMAL)

    @property
    def is_pinned(self) -> bool:
        return self._pinned

    def _update_tooltip(self):
        parts = [self.entry.name]
        if self.entry.description:
            parts.append(self.entry.description)
        if self.entry.last_used:
            parts.append(f"上次使用: {self.entry.last_used[:19]}")
        self.setToolTip("\n".join(parts))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._long_press_triggered = False
            self._press_timer.start()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and self._press_timer.isActive():
            delta = (event.pos() - self._press_pos).manhattanLength()
            if delta > DRAG_THRESHOLD:
                self._press_timer.stop()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_timer.stop()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._long_press_triggered:
                pass
            elif self._press_pos is not None:
                self.selected.emit(self.entry)
        self._press_pos = None
        self._long_press_triggered = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._press_timer.stop()
        if event.button() == Qt.MouseButton.LeftButton:
            self.launch_requested.emit(self.entry)
        self._press_pos = None
        super().mouseDoubleClickEvent(event)

    def _on_long_press(self):
        self._long_press_triggered = True
        self.drag_started.emit(self.entry)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #ffffff; border: 1px solid #e8e5e0;
                    border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 24px; border-radius: 4px; }
            QMenu::item:selected { background: #f5f0e8; }
        """)
        pin_action = menu.addAction("📌 取消置顶" if self._pinned else "📌 置顶")
        menu.addSeparator()
        edit_action = menu.addAction("编辑")
        launch_action = menu.addAction("启动")
        # Red delete action
        menu.addSeparator()
        delete_btn = QPushButton("🗑  删除项目")
        delete_btn.setObjectName("menuDeleteBtn")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #d44; border: none;
                text-align: left; padding: 6px 24px; font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #fdf0f0; }
        """)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_widget_action = QWidgetAction(menu)
        delete_widget_action.setDefaultWidget(delete_btn)
        delete_btn.clicked.connect(menu.close)
        delete_btn.clicked.connect(
            lambda: QTimer.singleShot(50, lambda: self.delete_requested.emit(self.entry)))
        menu.addAction(delete_widget_action)

        action = menu.exec(self.mapToGlobal(pos))
        if action == pin_action:
            self.pin_toggled.emit(self.entry)
        elif action == edit_action:
            self.edit_requested.emit(self.entry)
        elif action == launch_action:
            self.launch_requested.emit(self.entry)
