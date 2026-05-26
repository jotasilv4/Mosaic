from inspect import _empty
import operator
from collections.abc import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import DesktopApp, get_desktop_applications, idle_add, remove_handler, truncate
from i3ipc import Connection, Event
import multiprocessing, threading
import config.data as data

# Create a connection manager to share the i3 connection
class I3ConnectionManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = I3ConnectionManager()
        return cls._instance
    
    def __init__(self):
        self.i3 = Connection()
        self.thread = None
        self.callbacks = {
            Event.WORKSPACE: [],
            Event.WINDOW_FOCUS: [],
            Event.WINDOW_TITLE: []
        }
        
        # Set up event handlers
        self.i3.on(Event.WORKSPACE, self._on_workspace_event)
        self.i3.on(Event.WINDOW_FOCUS, self._on_window_focus_event)
        self.i3.on(Event.WINDOW_TITLE, self._on_window_title_event)
    
    def _on_workspace_event(self, i3, event):
        for callback in self.callbacks[Event.WORKSPACE]:
            callback(i3, event)
    
    def _on_window_focus_event(self, i3, event):
        for callback in self.callbacks[Event.WINDOW_FOCUS]:
            callback(i3, event)
    
    def _on_window_title_event(self, i3, event):
        for callback in self.callbacks[Event.WINDOW_TITLE]:
            callback(i3, event)
    
    def register_callback(self, event_type, callback):
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def unregister_callback(self, event_type, callback):
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
    
    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.i3.main, daemon=True)
            self.thread.start()
    
    def command(self, cmd):
        return self.i3.command(cmd)
    
    def get_tree(self):
        return self.i3.get_tree()


class Workspaces(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="workspaces",
            visible=True,
            all_visible=True,
            orientation="h",
            h_align="fill",
            v_align="center"
        )
        
        # Get shared i3 connection
        self.i3_manager = I3ConnectionManager.get_instance()
        
        self.workspaces_box = Box(
            name="workspaces-box",
            spacing=10,
            orientation="h",
            children=[Button(name=f"workspaces-button", on_clicked=lambda b, num=i: self.switch_workspace(num)) 
                     for i in range(1, 11)]
        )
        
        # Initialize workspace state
        focused = self.i3_manager.get_tree().find_focused()
        wsnumber = focused.workspace().num - 1
        self.workspaces_box.children[wsnumber].add_style_class("focused")
        
        # Register callbacks
        self.i3_manager.register_callback(Event.WORKSPACE, self.on_workspaces)
        self.i3_manager.start()
        
        self.children = self.workspaces_box
    
    def on_workspaces(self, i3, e):
        try:
            tree = self.i3_manager.get_tree()
            focused_workspace = tree.find_focused().workspace()
            for i, btn in enumerate(self.workspaces_box.children):
                ws_num = i + 1
                idle_add(btn.remove_style_class, "focused")
                idle_add(btn.remove_style_class, "active")
                ws = next((w for w in tree.workspaces() if w.num == ws_num), None)
                if ws is not None:
                    if ws_num == focused_workspace.num:
                        idle_add(btn.add_style_class, "focused")
                    elif len(ws.leaves()) > 0:
                        idle_add(btn.add_style_class, "active")
        except Exception as ex:
            print("Error updating workspaces:", ex)
    
    def switch_workspace(self, num):
        self.i3_manager.command(f"workspace {num}")


class ActiveWindows(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="active-windows",
            visible=True,
            all_visible=True,
            orientation="h",
            h_align="center",
            v_align="center",
            **kwargs
        )

        self.notch = kwargs["notch"]
        
        # Get shared i3 connection
        self.i3_manager = I3ConnectionManager.get_instance()
        
        # Create a label to display the active window
        self.active_window_label = Label(
            name="active-window-label",
            text="No active window",
            ellipsization="end",
            max_chars_width=24,
        )
        
        # Register for window focus events
        self.i3_manager.register_callback(Event.WINDOW_FOCUS, self.on_window_focus)
        self.i3_manager.register_callback(Event.WINDOW_TITLE, self.on_window_focus)
        self.i3_manager.start()
        
        self.children = [self.active_window_label]
    
    def on_window_focus(self, i3, e):
        try:
            focused = self.i3_manager.get_tree().find_focused()
            window_name = focused.name if focused else "No active window"
            
            if window_name == "fabric":
                window_name = f"{data.APP_NAME_CAP}"
                
            idle_add(self.update_window_label, window_name)
        except Exception as ex:
            print("Error updating active window:", ex)
    
    def update_window_label(self, window_name):
        compact_visible = self.notch.stack.get_visible_child() == self.notch.compact
        active_windows_visible = self.notch.compact_stack.get_visible_child() == self

        if compact_visible and active_windows_visible:
            self.active_window_label.set_label(truncate(window_name, 24))