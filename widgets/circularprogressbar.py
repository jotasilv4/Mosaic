import gi
import math
import cairo
from typing import Literal, Iterable
from fabric.core.service import Property
from fabric.widgets.widget import Widget
from fabric.utils.helpers import get_enum_member, clamp

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


class CircularProgressBar(Gtk.DrawingArea, Widget):
    @Property(float, "read-write", default_value=0.0)
    def min_value(self) -> float:
        return self._min_value

    @min_value.setter
    def min_value(self, value: float):
        self._min_value = clamp(value, self.min_value, self.max_value)
        return self.queue_draw()

    @Property(float, "read-write", default_value=1.0)
    def max_value(self) -> float:
        return self._max_value

    @max_value.setter
    def max_value(self, value: float):
        if value == 0:
            raise ValueError("max_value cannot be zero")
        self._max_value = value
        return self.queue_draw()

    @Property(float, "read-write", default_value=1.0)
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        return self.queue_draw()

    @Property(bool, "read-write", default_value=False)
    def pie(self) -> bool:
        return self._pie

    @pie.setter
    def pie(self, value: bool):
        self._pie = value
        return self.queue_draw()

    @Property(int, "read-write", default_value=4)
    def line_width(self) -> int:
        return self._line_width

    @line_width.setter
    def line_width(self, value: int):
        self._line_width = value
        return self.queue_draw()

    @Property(object, "read-write")
    def line_style(self) -> cairo.LineCap:
        return self._line_style

    @line_style.setter
    def line_style(
        self,
        line_style: Literal[
            "none",
            "butt",
            "round",
            "square",
        ]
        | cairo.LineCap,
    ):
        self._line_style = get_enum_member(cairo.LineCap, line_style)
        return self.queue_draw()

    @Property(int, "read-write", default_value=0)
    def angle(self) -> int:
        return self._angle

    @angle.setter
    def angle(self, value: int):
        self._angle = value
        return self.queue_draw()

    @Property(int, "read-write", default_value=0)
    def gap_size(self) -> int:
        return self._gap_size

    @gap_size.setter
    def gap_size(self, value: int):
        self._gap_size = value
        return self.queue_draw()

    def __init__(
        self,
        value: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        line_width: int = 4,
        line_style: Literal[
            "none",
            "butt",
            "round",
            "square",
        ]
        | cairo.LineCap = cairo.LineCap.ROUND,
        pie: bool = False,
        angle: int = 0,
        gap_size: int = 0,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)
        Widget.__init__(
            self,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )
        self._value: float = 1.0
        self._min_value: float = 0.0
        self._max_value: float = 1.0
        self._line_width: int = 4
        self._line_style: cairo.LineCap = cairo.LineCap.ROUND
        self._pie: bool = False
        self._angle: int = 0
        self._gap_size: int = 0

        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.line_width = line_width
        self.line_style = line_style
        self.pie = pie
        self.angle = angle
        self.gap_size = gap_size

        self.connect("draw", self.on_draw)

    def do_calculate_radius(self):
        width = self.get_allocated_width() / 2
        height = (self.get_allocated_height() / 2) - 1
        return int(min(width, height))

    def do_calculate_diameter(self):
        return 2 * self.do_calculate_radius()

    def do_calculate_preferred_size(self):
        d = self.do_calculate_diameter()
        if d > self.get_allocation().width:
            natural = d
        else:
            natural = self.get_allocation().width
        return d, natural

    def do_get_preferred_width(self):
        return self.do_calculate_preferred_size()

    def do_get_preferred_height(self):
        return self.do_calculate_preferred_size()

    def on_draw(self, _, cr: cairo.Context):
        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        style_context = self.get_style_context()
        border = style_context.get_border(Gtk.StateFlags.BACKDROP)
        background_color = style_context.get_background_color(Gtk.StateFlags.NORMAL)
        radius_color = style_context.get_color(Gtk.StateFlags.NORMAL)
        progress_color = style_context.get_border_color(Gtk.StateFlags.NORMAL)

        line_width = max(
            self.line_width,
            border.top,
            border.bottom,
            border.left,
            border.right,
            style_context.get_property("min-width", Gtk.StateFlags.NORMAL),
            style_context.get_property("min-height", Gtk.StateFlags.NORMAL),
        )

        center_x = self.get_allocated_width() / 2
        center_y = self.get_allocated_height() / 2
        radius = self.do_calculate_radius()
        d = radius - line_width
        delta = radius - line_width / 2
        if d < 0:
            delta = 0
            line_width = radius

        cr.set_line_cap(self._line_style)
        cr.set_line_width(line_width)

        # Compute the arc angles (in radians)
        base_start = 1.5 * math.pi + math.radians(self._angle)
        total_angle = 2 * math.pi - math.radians(self._gap_size)
        base_end = base_start + total_angle

        # Draw the track (base circle) with the gap applied.
        Gdk.cairo_set_source_rgba(cr, radius_color)
        if self.pie:
            cr.move_to(center_x, center_y)
            cr.arc(center_x, center_y, delta + (self._line_width / 2), base_start, base_end)
            cr.fill()
        else:
            cr.arc(center_x, center_y, delta, base_start, base_end)
            cr.stroke()

        # Draw the progress arc over the same span.
        Gdk.cairo_set_source_rgba(cr, progress_color)
        if self.pie:
            cr.move_to(center_x, center_y)
        progress_end = base_start + (self.value / self.max_value) * total_angle
        cr.arc(
            center_x,
            center_y,
            delta + (self._line_width / 2) if self.pie else delta,
            base_start,
            progress_end,
        )
        if self.pie:
            cr.fill()
        else:
            cr.stroke()

        cr.restore()
