import setproctitle
import os
from fabric import Application
from fabric.utils import get_relative_path, exec_shell_command_async
from modules.bar import Bar
from modules.notch import Notch
import modules.icons as icons
import config.data as data

if __name__ == "__main__":
    setproctitle.setproctitle(data.APP_NAME)

    if not os.path.isfile(data.CONFIG_FILE):
        exec_shell_command_async(f"python {get_relative_path('config/config.py')}")

    bar = Bar()
    notch = Notch()
    bar.notch = notch
    notch.bar = bar
    app = Application("mosaic", bar, notch)

    def set_css():
        css_file = os.path.join(os.path.dirname(__file__), "main.css")
        app.set_stylesheet_from_file(
            css_file,
            exposed_functions={
                "overview_width": lambda: f"min-width: {data.CURRENT_WIDTH * 0.1 * 5 + 92}px;",
                "overview_height": lambda: f"min-height: {data.CURRENT_HEIGHT * 0.1 * 2 + 32 + 56}px;",
            },
        )
        icons.refresh_themed_images()
        bar.refresh_theme()

    app.set_css = set_css

    app.set_css()

    app.run()