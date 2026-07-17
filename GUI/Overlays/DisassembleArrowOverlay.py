"""
This file is part of PINCE.

PINCE is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PINCE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PINCE. If not, see <https://www.gnu.org/licenses/>.
"""

import math

from PyQt6.QtCore import QEvent, QObject, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPalette, QPen, QPolygonF
from PyQt6.QtWidgets import QTableWidget, QToolTip

# How an arrow endpoint is anchored.
# _ROW is a real disassembled row, drawn at its own position and clipped by the viewport.
# _ABOVE and _BELOW are addresses with no displayed row, pinned to an edge.
_ROW = 0
_ABOVE = -1
_BELOW = 1

# Geometry of the arrows, in pixels.
# They are anchored to the left edge of the instruction column and fan out leftwards over the opcodes column,
# putting the arrowheads right next to the instruction text.
_RIGHT_GAP = 2  # gap between the arrowheads and the instruction text
_FIRST_LANE_OFFSET = 6  # distance between the instruction column and the innermost (closest) lane
_LANE_SPACING = 7  # horizontal distance between two neighbouring lanes
_MAX_LANES = 8  # lanes beyond this reuse the outermost column instead of fanning out further
_PEN_WIDTH = 1.6
_HEAD = 5  # arrowhead size
_HOVER_THRESHOLD = 5  # how close (px) the cursor must be to an arrow to hover it
_TOOLTIP_MSEC = 2147483647  # effectively indefinite display time so the tooltip stays up while hovering an arrow

# Categorical palette.
# Overlapping arrows are still separated by their lane's x offset if hues repeat.
_HUES = [210, 145, 32, 280, 190, 340, 55, 0]  # blue, green, orange, purple, teal, pink, yellow, red

# The Wong (colorblind-friendly) theme paints on an orange base (#E69F00, see GUI/Settings/themes.py).
# On that background the palette above is both low-contrast and confusable under red-green colour blindness.
# This replacement is dark enough to clear WCAG 3:1 against the orange and stays distinct under deuteranopia, protanopia and tritanopia.
_WONG_BASE = "#e69f00"  # lower-cased QColor.name() of the Wong theme's Base role
_WONG_COLORS = ["#005A8B", "#903E00", "#006246", "#843D66", "#101014"]  # blue, vermillion, green, purple, near-black


class DisassembleArrowOverlay(QObject):
    """Draws jmp/call references as arrows overlaid on the disassemble table, left of the instructions.

    Each arrow starts at the referrer (caller) address and ends, with an arrowhead, at the referenced
    (called/jumped-to) address. An arrow is drawn as long as at least one of its two instructions is on
    screen, so it stays visible even when its caller or target has scrolled out of view. An endpoint with
    no displayed row of its own is pinned to the nearest edge. Hovering an arrow highlights it and dims
    the rest so its destination is easy to follow, and clicking an arrow asks to follow one of its
    endpoints (see follow_requested).

    Rather than living in its own widget, the arrows are painted straight onto the table's viewport
    after the cells (by wrapping the table's paintEvent) so they hug the instruction column. Mouse
    interaction is handled through an event filter on the viewport.
    """

    # Emitted when an arrow is clicked, carrying its (source_address, target_address).
    # object is used instead of int because a large address overflows the C++ int a pyqtSignal would marshal it through.
    follow_requested = pyqtSignal(object, object)

    def __init__(self, table: QTableWidget, instruction_column: int) -> None:
        """
        Args:
            table (QTableWidget): The disassemble table the arrows are drawn over
            instruction_column (int): Index of the instruction column the arrows are anchored to
        """
        super().__init__(table)
        self.table = table
        self.viewport = table.viewport()
        self.instruction_column = instruction_column
        self.arrows: list[tuple[int, int, str]] = []  # [(source_address, target_address, kind), ...]
        self.address_to_row: dict[int, int] = {}  # displayed address -> table row index
        self.window_first = 0  # address of the first displayed instruction
        self.window_last = 0  # address of the last displayed instruction
        self._dark = False  # whether the current theme is dark, refreshed on every paint
        self._wong = False  # whether the colorblind-friendly Wong theme is active, refreshed on every paint
        # Geometry of the arrows drawn in the last paint, used for hover hit-testing without recomputing.
        self._geometry: list[dict] = []
        self._hovered: tuple[int, int, str] | None = None  # (source, target, kind) of the hovered arrow

        # Wrap the table's paintEvent to draw on top of the freshly painted cells.
        # Follow its mouse and resize events through an event filter on the viewport.
        self._table_paint_event = table.paintEvent
        table.paintEvent = self._paint_event
        self.viewport.setMouseTracking(True)
        self.viewport.installEventFilter(self)

    def set_arrows(
        self,
        arrows: list[tuple[int, int, str]],
        address_to_row: dict[int, int],
        window_first: int,
        window_last: int,
    ) -> None:
        """Replaces the arrows currently shown and repaints them

        Args:
            arrows (list): [(source_address, target_address, kind), ...] where kind is "jmp" or "call"
            address_to_row (dict): Maps every displayed instruction address to its table row index
            window_first (int): Address of the first displayed instruction
            window_last (int): Address of the last displayed instruction
        """
        self.arrows = arrows
        self.address_to_row = address_to_row
        self.window_first = window_first
        self.window_last = window_last
        self._set_hovered(None)  # the previous hover no longer maps to anything, so clear it and restore the cursor
        self.viewport.update()

    def _paint_event(self, event: QPaintEvent) -> None:
        """Paints the table cells (original handler) and then the arrows on top of them"""
        self._table_paint_event(event)
        painter = QPainter(self.viewport)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(painter)
        painter.end()

    def _endpoint(self, address: int, vp_bottom: int) -> tuple[int, int]:
        """Resolves an address to a y coordinate

        Displayed rows keep their real position even when it falls outside the viewport, so the arrow is
        drawn in full and the painter simply clips whatever hangs off the top or bottom edge. An address
        that isn't displayed at all has no row to anchor to, so it is clamped to the nearest edge.

        Returns:
            tuple: (y coordinate, direction) where direction is _ROW, _ABOVE or _BELOW
        """
        row = self.address_to_row.get(address)
        if row is not None:
            return self.table.rowViewportPosition(row) + self.table.rowHeight(row) // 2, _ROW
        # Not part of the disassembled range at all, decide the edge from its address.
        return (0, _ABOVE) if address < self.window_first else (vp_bottom, _BELOW)

    def _arrow_color(self, key: int) -> QColor:
        """Picks an arrow's colour from the palette using a stable per-arrow key, so its colour stays the
        same when other arrows scroll into or out of view"""
        if self._wong:
            return QColor(_WONG_COLORS[key % len(_WONG_COLORS)])
        hue = _HUES[key % len(_HUES)]
        return QColor.fromHsv(hue, 180, 235) if self._dark else QColor.fromHsv(hue, 235, 175)

    @staticmethod
    def _palette_key(source: int, target: int) -> int:
        """A stable value derived only from the arrow's own addresses, so its palette slot never changes
        as other arrows scroll in or out. Hashing the pair mixes the bits so neighbouring aligned
        addresses still spread across the palette. Deterministic here since both parts are ints"""
        return hash((source, target))

    def _assign_lanes(self, resolved: list[tuple]) -> list[int]:
        """Greedily packs arrows into vertical lanes so overlapping ones don't share a column

        Shorter arrows are placed on the inner lanes (closest to the code) so nested branches read
        naturally, the way IDA/Cheat Engine lay them out.

        Args:
            resolved (list): Arrow geometry tuples whose first two items are the endpoint y values

        Returns:
            list: The lane index chosen for each arrow, in the same order as resolved
        """
        intervals = [(min(item[0], item[1]), max(item[0], item[1])) for item in resolved]
        order = sorted(range(len(resolved)), key=lambda i: intervals[i][1] - intervals[i][0])
        lanes: list[list[tuple[int, int]]] = []  # each lane holds the y intervals already occupying it
        result = [0] * len(resolved)
        for i in order:
            top_y, bottom_y = intervals[i]
            chosen = None
            for lane_index, occupied in enumerate(lanes):
                if all(bottom_y < lo or top_y > hi for lo, hi in occupied):
                    chosen = lane_index
                    break
            if chosen is None:
                chosen = len(lanes)
                lanes.append([])
            lanes[chosen].append((top_y, bottom_y))
            result[i] = chosen
        return result

    def _arrow_points(self, y0: int, y1: int, src_dir: int, tgt_dir: int, lane_x: int, anchor_x: int) -> list[QPointF]:
        """Builds the polyline the arrow follows: source stub, vertical run through the lane, target stub"""
        points = []
        if src_dir == _ROW:
            points.append(QPointF(anchor_x, y0))
        points.append(QPointF(lane_x, y0))  # corner where the line turns down into its lane
        points.append(QPointF(lane_x, y1))
        if tgt_dir == _ROW:
            points.append(QPointF(anchor_x, y1))
        return points

    def _draw(self, painter: QPainter) -> None:
        """Resolves the arrows to on-screen geometry and paints them, hovered one on top"""
        self._geometry = []
        if not self.arrows or not self.address_to_row:
            return
        # Detect the mode from the actual background to also track live theme changes and previews.
        base = self.viewport.palette().color(QPalette.ColorRole.Base)
        self._wong = base.name().lower() == _WONG_BASE
        self._dark = base.lightness() < 128
        vp_bottom = self.viewport.height()
        anchor_x = self.table.columnViewportPosition(self.instruction_column) - _RIGHT_GAP
        innermost_x = anchor_x - _FIRST_LANE_OFFSET

        # Resolve each arrow to on-screen geometry, keeping the arrow whenever any part of its vertical span falls
        # inside the viewport while the painter clips whatever runs off an edge.
        # An arrow is dropped only when both endpoints sit past the same edge.
        # One crossing the viewport is still drawn even when neither endpoint is on screen.
        resolved = []
        for source, target, kind in self.arrows:
            y0, src_dir = self._endpoint(source, vp_bottom)
            y1, tgt_dir = self._endpoint(target, vp_bottom)
            src_above = src_dir == _ABOVE or (src_dir == _ROW and y0 < 0)
            src_below = src_dir == _BELOW or (src_dir == _ROW and y0 > vp_bottom)
            tgt_above = tgt_dir == _ABOVE or (tgt_dir == _ROW and y1 < 0)
            tgt_below = tgt_dir == _BELOW or (tgt_dir == _ROW and y1 > vp_bottom)
            if (src_above and tgt_above) or (src_below and tgt_below):
                continue
            resolved.append((y0, y1, src_dir, tgt_dir, kind, source, target))

        lanes = self._assign_lanes(resolved)
        for i, (y0, y1, src_dir, tgt_dir, kind, source, target) in enumerate(resolved):
            lane_x = max(1, innermost_x - min(lanes[i], _MAX_LANES - 1) * _LANE_SPACING)
            self._geometry.append(
                {
                    "key": (source, target, kind),
                    "kind": kind,
                    "color": self._arrow_color(self._palette_key(source, target)),
                    "points": self._arrow_points(y0, y1, src_dir, tgt_dir, lane_x, anchor_x),
                    "tgt_dir": tgt_dir,
                    "lane_x": lane_x,
                    "y1": y1,
                    "anchor_x": anchor_x,
                }
            )

        hovering = any(geometry["key"] == self._hovered for geometry in self._geometry)
        # Draw the non-hovered arrows first (dimmed while hovering), then the hovered one on top.
        for geometry in self._geometry:
            if geometry["key"] != self._hovered:
                self._draw_arrow(painter, geometry, dim=hovering)
        for geometry in self._geometry:
            if geometry["key"] == self._hovered:
                self._draw_arrow(painter, geometry, highlight=True)

    def _draw_arrow(self, painter: QPainter, geometry: dict, dim: bool = False, highlight: bool = False) -> None:
        """Draws a single arrow, optionally dimmed (a sibling of the hovered one) or highlighted"""
        color = QColor(geometry["color"])
        width = _PEN_WIDTH
        if highlight:
            width = _PEN_WIDTH + 1.5
            if self._wong:
                color = color.darker(125)  # deepen against the orange background rather than lighten
            elif self._dark:
                color = color.lighter(125)
            else:
                color = color.darker(115)
        elif dim:
            color.setAlpha(50)

        path = QPainterPath(geometry["points"][0])
        for point in geometry["points"][1:]:
            path.lineTo(point)

        if highlight:
            # A soft, wide halo underneath makes the hovered path pop out from the dimmed ones.
            halo = QColor(color)
            halo.setAlpha(70)
            painter.strokePath(path, self._make_pen(halo, width + 4, geometry["kind"]))
        painter.strokePath(path, self._make_pen(color, width, geometry["kind"]))
        self._draw_head(painter, color, geometry, big=highlight)

    def _make_pen(self, color: QColor, width: float, kind: str) -> QPen:
        """Creates the pen for an arrow, dashed for calls and solid for jumps"""
        pen = QPen(color, width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if kind == "call":
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([4, 3])
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        else:
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen

    def _draw_head(self, painter: QPainter, color: QColor, geometry: dict, big: bool) -> None:
        """Draws the filled triangular arrowhead at the target end of the arrow"""
        size = _HEAD + (2 if big else 0)
        y = geometry["y1"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        if geometry["tgt_dir"] == _ROW:  # points right, into the code
            x = geometry["anchor_x"]
            head = QPolygonF([QPointF(x, y), QPointF(x - size, y - size + 1), QPointF(x - size, y + size - 1)])
        else:
            x = geometry["lane_x"]
            direction = -1 if geometry["tgt_dir"] == _ABOVE else 1  # points up or down, off-screen target
            base_y = y - direction * size
            head = QPolygonF([QPointF(x, y), QPointF(x - size + 1, base_y), QPointF(x + size - 1, base_y)])
        painter.drawPolygon(head)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is not self.viewport:
            return False
        event_type = event.type()
        if event_type == QEvent.Type.Resize:
            self.viewport.update()  # visible rows changed, redraw the arrows
        elif event_type == QEvent.Type.MouseMove:
            self._update_hover(event)
        elif event_type == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            geometry = self._arrow_at(event.position().x(), event.position().y())
            if geometry:
                source, target, _ = geometry["key"]
                self.follow_requested.emit(source, target)
                return True  # consume to keep the click from also changing the row selection
        elif event_type == QEvent.Type.ToolTip:
            geometry = self._arrow_at(event.pos().x(), event.pos().y())
            if geometry:
                # Show our own tooltip and swallow the event to stop the view replacing it with the cell's (usually empty) tooltip,
                # which is what made it vanish after the hover delay.
                QToolTip.showText(event.globalPos(), self._tooltip_text(geometry["key"]), self.viewport, QRect(), _TOOLTIP_MSEC)
                return True
        elif event_type == QEvent.Type.Leave:
            self._set_hovered(None)
            QToolTip.hideText()
        return False

    def _arrow_at(self, x: float, y: float) -> dict | None:
        """Returns the arrow geometry closest to (x, y) within the hover threshold, or None"""
        nearest = None
        nearest_distance = _HOVER_THRESHOLD + 1
        for geometry in self._geometry:
            points = geometry["points"]
            for start, end in zip(points, points[1:]):
                distance = self._distance_to_segment(x, y, start, end)
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest = geometry
        return nearest if nearest_distance <= _HOVER_THRESHOLD else None

    def _update_hover(self, event: QMouseEvent) -> None:
        position = event.position()
        geometry = self._arrow_at(position.x(), position.y())
        hovered = geometry["key"] if geometry else None
        # Only touch the tooltip when the hovered arrow actually changes.
        # Calling showText on every mouse move (even over the same arrow) thrashed the shared tooltip window into half-drawn or flickering states,
        # especially while switching between arrows.
        if hovered == self._hovered:
            return
        self._set_hovered(hovered)  # updates the cursor and repaints
        if hovered:
            QToolTip.showText(event.globalPosition().toPoint(), self._tooltip_text(hovered), self.viewport, QRect(), _TOOLTIP_MSEC)
        else:
            QToolTip.hideText()

    @staticmethod
    def _tooltip_text(key: tuple[int, int, str]) -> str:
        """Builds the 'source -> target (kind)' label shown when hovering an arrow"""
        source, target, kind = key
        return f"{hex(source)} → {hex(target)} ({kind})"

    def _set_hovered(self, hovered: tuple[int, int, str] | None) -> None:
        if hovered != self._hovered:
            self._hovered = hovered
            self.viewport.setCursor(Qt.CursorShape.PointingHandCursor if hovered else Qt.CursorShape.ArrowCursor)
            self.viewport.update()  # repaint the cells and arrows so the highlight/dim is correct

    @staticmethod
    def _distance_to_segment(px: float, py: float, start: QPointF, end: QPointF) -> float:
        """Returns the shortest distance from point (px, py) to the line segment start-end"""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if dx == 0 and dy == 0:
            return math.hypot(px - start.x(), py - start.y())
        t = ((px - start.x()) * dx + (py - start.y()) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(px - (start.x() + t * dx), py - (start.y() + t * dy))
