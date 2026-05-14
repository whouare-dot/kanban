from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import QRect

from app.widgets.app_card import AppCard, CARD_WIDTH, CARD_HEIGHT

SHAKE_AMPLITUDE = 8
SHAKE_DURATION = 350
SHAKE_PROXIMITY = 130
OVERLAY_SCALE = 0.7
OVERLAY_OPACITY = 0.75
FADE_IN_MS = 150
FADE_OUT_MS = 100
BOUNCE_MS = 220


class DragController(QWidget):
    """Handles drag-and-drop reordering of AppCards within an AppGrid.

    Owns the pixmap overlay, insertion indicator, and shake animations.
    The owner AppGrid delegates mouse events to this controller while dragging.
    """

    finished = pyqtSignal(int)  # emits insert_index; -1 means cancelled

    def __init__(self, app_grid):
        super().__init__(app_grid.viewport())
        self._app_grid = app_grid
        self._container = app_grid._container
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

        self._overlay: QLabel | None = None
        self._indicator: QWidget | None = None
        self._dragged_card: AppCard | None = None
        self._dragged_entry = None
        self._fade_anim: QPropertyAnimation | None = None
        self._bounce_anim: QPropertyAnimation | None = None
        self._shaking_cards: dict[AppCard, QPropertyAnimation] = {}
        self._insert_index = -1
        self._last_indicator_index = -1

    # ── public API ────────────────────────────────────────────────

    def start(self, card: AppCard, global_pos: QPoint):
        self._dragged_card = card
        self._dragged_entry = card.entry
        card.setVisible(False)
        self._container.set_layout_frozen(True)

        # Build scaled pixmap overlay
        pixmap = card.grab()
        w = int(CARD_WIDTH * OVERLAY_SCALE)
        h = int(CARD_HEIGHT * OVERLAY_SCALE)
        small = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)

        self._overlay = QLabel(self._container)
        self._overlay.setPixmap(small)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        effect = QGraphicsOpacityEffect(self._overlay)
        effect.setOpacity(0.0)
        self._overlay.setGraphicsEffect(effect)

        local = self._container.mapFromGlobal(global_pos)
        target_x = local.x() - w // 2
        target_y = local.y() - h // 2

        bounce_w = int(w * 0.85)
        bounce_h = int(h * 0.85)
        bounce_x = local.x() - bounce_w // 2
        bounce_y = local.y() - bounce_h // 2
        self._overlay.setGeometry(bounce_x, bounce_y, bounce_w, bounce_h)
        self._overlay.show()

        # Fade-in
        self._fade_anim = QPropertyAnimation(effect, b"opacity")
        self._fade_anim.setDuration(FADE_IN_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(OVERLAY_OPACITY)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        # Scale bounce
        self._bounce_anim = QPropertyAnimation(self._overlay, b"geometry")
        self._bounce_anim.setDuration(BOUNCE_MS)
        self._bounce_anim.setStartValue(
            QRect(bounce_x, bounce_y, bounce_w, bounce_h))
        self._bounce_anim.setEndValue(
            QRect(target_x, target_y, w, h))
        self._bounce_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._bounce_anim.start()

        # Insertion indicator bar
        self._indicator = QWidget(self._container)
        self._indicator.setFixedSize(3, CARD_HEIGHT)
        self._indicator.setStyleSheet(
            "background-color: #d4a853; border-radius: 2px;"
        )
        self._indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._indicator.hide()

        self._app_grid.viewport().grabMouse()
        self._app_grid.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

        self.update(global_pos)

    def update(self, global_pos: QPoint):
        if self._overlay is None:
            return
        local = self._container.mapFromGlobal(global_pos)
        ow = self._overlay.width()
        oh = self._overlay.height()
        self._overlay.move(local.x() - ow // 2, local.y() - oh // 2)

        new_idx = self._calc_index(local)
        self._insert_index = new_idx
        if new_idx != self._last_indicator_index:
            self._position_indicator(new_idx)
            self._last_indicator_index = new_idx

        self._update_shakes(local)

    def end(self, global_pos: QPoint) -> int:
        """Finish drag. Returns the final insertion index, or -1 if cancelled."""
        local = self._container.mapFromGlobal(global_pos)
        index = self._calc_index(local)

        # Check if drop is outside valid container area
        if not self._is_valid_drop(local):
            index = -1

        self._cleanup()
        return index

    def cancel(self):
        self._cleanup()

    def is_dragging(self) -> bool:
        return self._dragged_entry is not None

    # ── internals ─────────────────────────────────────────────────

    def _is_valid_drop(self, local: QPoint) -> bool:
        """Drop is valid if cursor is within the container or near card rows."""
        cw = self._container.width()
        ch = max(self._container.minimumSizeHint().height(), 100)
        margin = 60
        return (-margin < local.x() < cw + margin and
                -margin < local.y() < ch + margin)

    def _cleanup(self):
        self._dragged_entry = None
        if hasattr(self, '_fade_anim') and self._fade_anim:
            self._fade_anim.stop()
            self._fade_anim = None
        if hasattr(self, '_bounce_anim') and self._bounce_anim:
            self._bounce_anim.stop()
            self._bounce_anim = None
        if self._dragged_card:
            self._dragged_card.setVisible(True)
            self._dragged_card = None

        self._app_grid.viewport().releaseMouse()
        self._app_grid.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        for anim in self._shaking_cards.values():
            anim.stop()
        self._shaking_cards.clear()

        if self._overlay:
            self._overlay.setParent(None)
            self._overlay.deleteLater()
            self._overlay = None
        if self._indicator:
            self._indicator.setParent(None)
            self._indicator.deleteLater()
            self._indicator = None

        self._container.set_layout_frozen(False)
        self._insert_index = -1
        self._last_indicator_index = -1

    @property
    def dragged_entry(self):
        return self._dragged_entry

    # ── insertion calculation ─────────────────────────────────────

    def _get_visible_cards(self) -> list[AppCard]:
        cards = []
        for child in self._container.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        ):
            if (isinstance(child, AppCard) and child.isVisible()
                    and child is not self._dragged_card):
                cards.append(child)
        # Sort row-major
        cards.sort(key=lambda c: (c.geometry().top(), c.geometry().left()))
        return cards

    def _calc_index(self, pos: QPoint) -> int:
        cards = self._get_visible_cards()
        if not cards:
            return 0

        best_idx = 0
        best_dist = float("inf")
        h_gap = 14

        for i in range(len(cards) + 1):
            gap = self._gap_center(cards, i, h_gap)
            if gap is None:
                continue
            dist = (pos - gap).manhattanLength()
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return best_idx

    def _gap_center(self, cards: list, i: int, h_gap: int) -> QPoint | None:
        """Return the visual center of the insertion gap at position i."""
        n = len(cards)
        if i < n:
            ref = cards[i]
            gy = ref.geometry().center().y()
            if i == 0:
                gx = ref.geometry().left() - h_gap // 2 - 2
            else:
                prev_right = cards[i - 1].geometry().right()
                curr_left = ref.geometry().left()
                gx = (prev_right + curr_left) // 2
            return QPoint(gx, gy)
        else:
            # After last card
            if n == 0:
                return None
            last = cards[-1]
            gy = last.geometry().center().y()
            gx = last.geometry().right() + h_gap // 2 + 2
            return QPoint(gx, gy)

    # ── indicator ─────────────────────────────────────────────────

    def _position_indicator(self, index: int):
        if self._indicator is None:
            return
        cards = self._get_visible_cards()
        h_gap = 14

        if not cards:
            self._indicator.hide()
            return

        n = len(cards)
        if index < n:
            ref = cards[index]
            gy = ref.geometry().top()
            if index == 0:
                gx = ref.geometry().left() - h_gap // 2 - 2
            else:
                gx = (cards[index - 1].geometry().right() + ref.geometry().left()) // 2
        else:
            last = cards[-1]
            gy = last.geometry().top()
            gx = last.geometry().right() + h_gap // 2 + 2

        self._indicator.setGeometry(gx, gy, 3, CARD_HEIGHT)
        self._indicator.show()

    # ── shake animations ──────────────────────────────────────────

    def _update_shakes(self, overlay_center: QPoint):
        cards = self._get_visible_cards()
        oc = overlay_center

        for card in cards:
            center = card.geometry().center()
            dx = center.x() - oc.x()
            dy = center.y() - oc.y()
            dist = (abs(dx) ** 2 + abs(dy) ** 2) ** 0.5

            if dist < SHAKE_PROXIMITY:
                if card not in self._shaking_cards:
                    direction = 1 if dx > 0 else -1
                    self._start_shake(card, direction)
            else:
                if card in self._shaking_cards:
                    self._stop_shake(card)

    def _start_shake(self, card: AppCard, direction: int):
        original = card.pos()
        anim = QPropertyAnimation(card, b"pos")
        anim.setDuration(SHAKE_DURATION)
        anim.setLoopCount(-1)
        amp = SHAKE_AMPLITUDE
        anim.setKeyValueAt(0.0, original)
        anim.setKeyValueAt(0.2, original + QPoint(int(amp * direction), 0))
        anim.setKeyValueAt(0.5, original + QPoint(int(-amp * 0.6 * direction), 0))
        anim.setKeyValueAt(0.8, original + QPoint(int(amp * 0.3 * direction), 0))
        anim.setKeyValueAt(1.0, original)
        anim.start()
        self._shaking_cards[card] = anim

    def _stop_shake(self, card: AppCard):
        anim = self._shaking_cards.pop(card, None)
        if anim:
            original = anim.keyValueAt(0.0)
            anim.stop()
            card.move(original)
