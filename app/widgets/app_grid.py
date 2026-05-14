import os

from PyQt6.QtWidgets import QScrollArea, QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from app.models import AppEntry
from app.widgets.app_card import AppCard, CARD_WIDTH, CARD_HEIGHT
from app.widgets.drag_controller import DragController


class FlowContainer(QWidget):
    def __init__(self, parent=None, h_spacing=14, v_spacing=14):
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._margin_left = 28
        self._margin_top = 20
        self._margin_right = 28
        self._margin_bottom = 20
        self._layout_frozen = False

    def set_layout_frozen(self, frozen: bool):
        self._layout_frozen = frozen
        if not frozen:
            self._layout_children()

    def add_card(self, card: AppCard):
        card.setParent(self)
        card.show()

    def remove_card(self, card: AppCard):
        card.setParent(None)
        card.deleteLater()

    def clear(self):
        self._layout_frozen = False
        children = self.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
        for child in children:
            child.setParent(None)
            child.deleteLater()

    def _layout_children(self):
        children = [
            c for c in self.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
            ) if isinstance(c, AppCard) and c.isVisible()
        ]
        if not children:
            return 0

        avail = self.width() - self._margin_left - self._margin_right
        if avail < 50:
            avail = 500

        card_w = CARD_WIDTH
        card_h = CARD_HEIGHT

        x = self._margin_left
        y = self._margin_top
        row_height = 0

        for child in children:
            if x + card_w > self._margin_left + avail and x > self._margin_left:
                x = self._margin_left
                y += row_height + self._v_spacing
                row_height = 0

            child.setGeometry(x, y, card_w, card_h)
            x += card_w + self._h_spacing
            row_height = max(row_height, card_h)

        return y + row_height + self._margin_bottom

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._layout_frozen:
            self._layout_children()

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        h = self._layout_children()
        pw = self.parentWidget()
        ref = pw.size() if pw else self.size()
        return QSize(max(ref.width(), 400), max(h, 200))


class AppGrid(QScrollArea):
    order_changed = pyqtSignal(str, list)  # tag, ordered paths
    pin_toggled = pyqtSignal(str, str)     # tag, path
    delete_requested = pyqtSignal(object)  # AppEntry
    escape_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appGrid")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._container = FlowContainer()
        self._container.setObjectName("gridContainer")
        self.setWidget(self._container)

        self._apps: list[AppEntry] = []
        self._current_tag: str = ""
        self._search_text: str = ""
        self._font_name_size: int = 12
        self._font_desc_size: int = 10
        self._card_order: dict = {}
        self._pinned: dict = {}

        # Persistent card dict: path -> AppCard
        self._cards: dict[str, AppCard] = {}
        # Ordered list of visible card paths (for keyboard nav)
        self._visible_paths: list[str] = []
        # Currently focused card path (for keyboard nav)
        self._focused_path: str | None = None

        self._drag = DragController(self)

        self.launch_requested = None
        self.edit_requested = None

    # ── public setters ──────────────────────────────────────────

    def set_apps(self, apps: list[AppEntry]):
        new_paths = {a.path for a in apps}
        old_paths = set(self._cards.keys())

        # Remove cards for apps that no longer exist
        for path in old_paths - new_paths:
            card = self._cards.pop(path)
            self._container.remove_card(card)

        self._apps = apps
        self._ensure_cards()
        self._apply_filter()

    def set_tag(self, tag: str):
        self._current_tag = tag
        self._apply_filter()

    def set_search(self, text: str):
        self._search_text = text.strip().lower()
        self._apply_filter()

    def set_card_order(self, card_order: dict):
        self._card_order = card_order

    def set_pinned(self, pinned: dict):
        self._pinned = pinned

    def set_font_sizes(self, name_size: int, desc_size: int):
        self._font_name_size = name_size
        self._font_desc_size = desc_size
        for card in self._cards.values():
            card.set_font_sizes(name_size, desc_size)

    # ── card management ─────────────────────────────────────────

    def _ensure_cards(self):
        """Create AppCard widgets for any apps that don't have one yet."""
        for app in self._apps:
            if app.path not in self._cards:
                card = AppCard(app)
                card.set_font_sizes(self._font_name_size, self._font_desc_size)
                card.selected.connect(self._on_card_selected)
                card.drag_started.connect(self._on_drag_started)
                card.pin_toggled.connect(self._on_pin_toggled)
                card.delete_requested.connect(self.delete_requested.emit)
                if self.launch_requested:
                    card.launch_requested.connect(self.launch_requested)
                if self.edit_requested:
                    card.edit_requested.connect(self.edit_requested)
                self._cards[app.path] = card
                self._container.add_card(card)

    def _apply_filter(self):
        """Show/hide cards based on tag and search, then re-layout."""
        tagged_paths = set()
        pinned_paths = set(
            os.path.normpath(p) for p in self._pinned.get(self._current_tag or "", [])
        )

        # Determine which apps pass the tag filter
        for app in self._apps:
            if self._current_tag and self._current_tag not in app.tags:
                continue
            tagged_paths.add(app.path)

        # Determine which apps pass the search filter (searches name + desc + tags)
        matching_paths = set()
        for app in self._apps:
            if self._search_text and self._search_text not in app.search_text:
                continue
            matching_paths.add(app.path)

        # Build sorted visible list
        tag = self._current_tag or ""
        visible_apps = [a for a in self._apps
                        if a.path in tagged_paths and a.path in matching_paths]

        # Split into pinned and unpinned
        pinned_apps = [a for a in visible_apps
                       if os.path.normpath(a.path) in pinned_paths]
        unpinned_apps = [a for a in visible_apps
                         if os.path.normpath(a.path) not in pinned_paths]

        # Sort pinned by their order
        pin_order = {os.path.normpath(p): i
                     for i, p in enumerate(self._pinned.get(tag, []))}
        pinned_apps.sort(
            key=lambda a: pin_order.get(os.path.normpath(a.path), 999999))

        # Sort unpinned by card_order
        order = self._card_order.get(tag, [])
        if order:
            rank = {os.path.normpath(p): i for i, p in enumerate(order)}
            unpinned_apps.sort(
                key=lambda a: rank.get(os.path.normpath(a.path), 999999))

        sorted_apps = pinned_apps + unpinned_apps
        sorted_paths = [a.path for a in sorted_apps]

        # Show/hide cards
        for path, card in self._cards.items():
            visible = path in sorted_paths
            card.setVisible(visible)
            card.set_pinned(os.path.normpath(path) in pinned_paths)

        self._visible_paths = sorted_paths

        # Clear focus if focused card is no longer visible
        if self._focused_path and self._focused_path not in sorted_paths:
            self._focused_path = None

        self._container._layout_children()
        self._container.updateGeometry()

    def _get_visible_cards_ordered(self) -> list[AppCard]:
        """Return visible AppCards in their current sorted order."""
        cards = []
        for path in self._visible_paths:
            card = self._cards.get(path)
            if card and card.isVisible():
                cards.append(card)
        return cards

    # ── selection ──────────────────────────────────────────────

    def _on_card_selected(self, entry: AppEntry):
        self._set_focused(entry.path)

    def _set_focused(self, path: str):
        old = self._focused_path
        self._focused_path = path
        # Update visual state
        if old and old in self._cards:
            self._cards[old].set_selected(False)
        if path in self._cards:
            self._cards[path].set_selected(True)

    # ── keyboard navigation ─────────────────────────────────────

    def keyPressEvent(self, event):
        if self._drag.is_dragging():
            if event.key() == Qt.Key.Key_Escape:
                self._drag.cancel()
            return

        visible = self._get_visible_cards_ordered()
        if not visible:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Escape:
            self._set_focused(None)
            self.escape_pressed.emit()
            return

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self._focused_path:
                card = self._cards.get(self._focused_path)
                if card and self.launch_requested:
                    self.launch_requested(card.entry)
            return

        # Find current index
        try:
            idx = visible.index(self._cards[self._focused_path]) \
                if self._focused_path else -1
        except (ValueError, KeyError):
            idx = -1

        cols = max(1, (self._container.width() - 28 - 28) // (CARD_WIDTH + 14))

        if event.key() == Qt.Key.Key_Right:
            idx = min(idx + 1, len(visible) - 1) if idx >= 0 else 0
        elif event.key() == Qt.Key.Key_Left:
            idx = max(idx - 1, 0) if idx >= 0 else 0
        elif event.key() == Qt.Key.Key_Down:
            idx = min(idx + cols, len(visible) - 1) if idx >= 0 else 0
        elif event.key() == Qt.Key.Key_Up:
            idx = max(idx - cols, 0) if idx >= 0 else 0
        else:
            super().keyPressEvent(event)
            return

        if 0 <= idx < len(visible):
            self._set_focused(visible[idx].entry.path)
            self.ensureWidgetVisible(visible[idx])

        super().keyPressEvent(event)

    # ── drag-and-drop ──────────────────────────────────────────

    def _on_drag_started(self, entry: AppEntry):
        if self._drag.is_dragging():
            return
        card = self._cards.get(entry.path)
        if card is None:
            return
        self._drag.start(card, QCursor.pos())

    def mouseMoveEvent(self, event):
        if self._drag.is_dragging():
            self._drag.update(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag.is_dragging():
            entry = self._drag.dragged_entry
            insert_idx = self._drag.end(event.globalPosition().toPoint())
            self._on_drag_finished(insert_idx, entry)
        super().mouseReleaseEvent(event)

    def _on_drag_finished(self, insert_idx: int, entry):
        if insert_idx < 0 or entry is None:
            return

        tag = self._current_tag or ""
        pinned_set = set(
            os.path.normpath(p) for p in self._pinned.get(tag, []))
        is_pinned_drag = os.path.normpath(entry.path) in pinned_set

        visible = self._get_visible_cards_ordered()
        visible_entries = [c.entry for c in visible]

        pinned_count = sum(
            1 for a in visible_entries
            if os.path.normpath(a.path) in pinned_set)

        if is_pinned_drag:
            insert_idx = max(0, min(insert_idx, pinned_count))
        else:
            insert_idx = max(pinned_count, min(insert_idx, len(visible_entries)))

        visible_entries = [a for a in visible_entries
                           if a.path != entry.path]
        insert_idx = min(insert_idx, len(visible_entries))
        visible_entries.insert(insert_idx, entry)

        ordered_paths = [a.path for a in visible_entries]
        self.order_changed.emit(tag, ordered_paths)

    def _on_pin_toggled(self, entry):
        tag = self._current_tag or ""
        self.pin_toggled.emit(tag, entry.path)
