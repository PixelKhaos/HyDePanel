import gi
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from gi.repository import Gdk, GdkPixbuf, Gray, Gtk

from shared.widget_container import BoxWidget
from utils.widget_config import BarConfig

gi.require_version("Gray", "0.1")
gi.require_version("Gtk", "3.0")


class SystemTray(BoxWidget):
    """A widget to display the system tray items."""

    def __init__(self, widget_config: BarConfig, bar, **kwargs) -> None:
        super().__init__(name="system-tray", **kwargs)

        self.config = widget_config["system_tray"]

        self.watcher = Gray.Watcher()
        self.watcher.connect("item-added", self.on_item_added)

    def on_item_added(self, _, identifier: str):
        item = self.watcher.get_item_for_identifier(identifier)

        if (
            self.config["ignore"]
            and item.get_property("title") in self.config["ignore"]
        ):
            return

        item_button = self.do_bake_item_button(item)
        item.connect("removed", lambda *args: item_button.destroy())
        item.connect(
            "icon-changed",
            lambda icon_item: self.do_update_item_button(icon_item, item_button),
        )
        item_button.show_all()
        self.add(item_button)

    def do_bake_item_button(self, item: Gray.Item) -> Button:
        button = Button()
        # context menu handler
        button.connect(
            "button-press-event",
            lambda button, event: self.on_button_click(button, item, event),
        )
        button.set_tooltip_text(item.get_property("title"))

        self.do_update_item_button(item, button)

        return button

    def do_update_item_button(self, item: Gray.Item, item_button: Button):
        pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), 24)

        # convert the pixmap to a pixbuf
        pixbuf: GdkPixbuf.Pixbuf = (
            pixmap.as_pixbuf(self.config["icon_size"], GdkPixbuf.InterpType.HYPER)
            if pixmap is not None
            else Gtk.IconTheme()
            .get_default()
            .load_icon(
                item.get_icon_name(),
                self.config["icon_size"],
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
        )
        item_button.set_image(Image(pixbuf=pixbuf, pixel_size=self.config["icon_size"]))

    def on_button_click(self, button, item: Gray.Item, event):
        match event.button:
            case 1 | 3:
                menu = item.get_property("menu")
                menu.set_name("system-tray-menu")
                if menu:
                    menu.popup_at_widget(
                        button,
                        Gdk.Gravity.SOUTH,
                        Gdk.Gravity.NORTH,
                        event,
                    )
                else:
                    item.context_menu(event.x, event.y)
