# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""Task pane and list."""

from gi.repository import Gtk, GObject, Gdk, Gio
from GTG.core.tasks2 import Task2, Status
from GTG.core.filters import TaskPaneFilter
from GTG.core.sorters import *
from GTG.gtk.browser.tag_pill import TagPill
from gettext import gettext as _


class TaskBox(Gtk.Box):
    """Box subclass to keep a pointer to the tag object"""

    task = GObject.Property(type=Task2)


def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""
    
    item = row.get_item()
    
    while type(item) is not expected_type:
        item = item.get_item()

    return item


class TaskPane(Gtk.ScrolledWindow):
    """The task pane widget"""
    
    def __init__(self, browser, pane):

        super(TaskPane, self).__init__()
        self.ds = browser.app.ds
        self.app = browser.app
        self.browser = browser
        self.pane = pane

        self.set_vexpand(True)
        self.set_hexpand(True)
        
        wrap_box = Gtk.Box()
        wrap_box.set_orientation(Gtk.Orientation.VERTICAL)

        # -------------------------------------------------------------------------------
        # Title
        # -------------------------------------------------------------------------------
        title_box = Gtk.Box()
        title_box.set_valign(Gtk.Align.START)

        title_box.set_margin_top(32)
        title_box.set_margin_bottom(32)
        title_box.set_margin_start(24)
        title_box.set_margin_end(24)
        
        self.title = Gtk.Label()
        self.title.set_halign(Gtk.Align.START)
        self.title.set_hexpand(True)
        self.title.add_css_class('title-1')
        title_box.append(self.title)
        
        sort_btn = Gtk.MenuButton()
        sort_btn.set_icon_name('view-more-symbolic')
        sort_btn.set_popover(browser.sort_menu)
        sort_btn.add_css_class('flat')
        
        title_box.append(sort_btn)


        # -------------------------------------------------------------------------------
        # Task List
        # -------------------------------------------------------------------------------

        filtered = Gtk.FilterListModel()
        self.filter = TaskPaneFilter(self.app.ds, pane)
        filtered.set_model(self.app.ds.tasks.tree_model)
        filtered.set_filter(self.filter)

        self.sort_model = Gtk.TreeListRowSorter()
        
        main_sorter = Gtk.SortListModel()
        main_sorter.set_model(filtered)
        main_sorter.set_sorter(self.sort_model)

        self.task_selection = Gtk.MultiSelection.new(main_sorter)

        tasks_signals = Gtk.SignalListItemFactory()
        tasks_signals.connect('setup', self.task_setup_cb)
        tasks_signals.connect('bind', self.task_bind_cb)

        view = Gtk.ListView.new(self.task_selection, tasks_signals)
        view.set_hexpand(True)
        view.set_show_separators(True)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-released', self.on_key_released)
        view.add_controller(key_controller)
        view.connect('activate', self.on_listview_activated)

        wrap_box.append(title_box)
        wrap_box.append(view)
        self.set_child(wrap_box)

        self.set_title()


    def set_title(self) -> None:
        """Change pane title."""
        
        if not self.filter.tags:
           if self.pane == 'active':
               self.title.set_text(_('All Open Tasks'))
           if self.pane == 'workview':
               self.title.set_text(_('Actionable Tasks'))
           if self.pane == 'closed':
               self.title.set_text(_('All Closed Tasks'))
               
        else:
           tags = ', '.join('@' + t.name for t in self.filter.tags)

           if self.pane == 'active':
               self.title.set_text(_('{0} (Open)'.format(tags)))
           if self.pane == 'workview':
               self.title.set_text(_('{0} (Actionable)'.format(tags)))
           if self.pane == 'closed':
               self.title.set_text(_('{0} (Closed)'.format(tags)))
            

    def set_filter_pane(self, pane) -> None:
        """Change tasks filter."""

        self.pane = pane
        self.filter.pane = pane
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.set_title()


    def set_filter_tags(self, tags=[]) -> None:
        """Change tasks filter."""

        self.filter.tags = tags
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.set_title()


    def set_sorter(self, method=None) -> None:
        """Change tasks filter."""

        sorter = None

        if method == 'Start':
            sorter = TaskStartSorter()
        if method == 'Due':
            sorter = TaskDueSorter()
        if method == 'Modified':
            sorter = TaskModifiedSorter()
        elif method == 'Added':
            sorter = TaskAddedSorter()
        elif method == 'Tags':
            sorter = TaskTagSorter()
        elif method == 'Title':
            sorter = TaskTitleSorter()

        self.sort_model.set_sorter(sorter)


    def on_listview_activated(self, listview, position, user_data = None):
        """Callback when double clicking on a row."""
        
        self.app.browser.on_edit_active_task()


    def on_key_released(self, controller, keyval, keycode, state):
        """Callback when a key is released. """
        
        is_enter = keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)

        if is_enter:
            self.app.browser.on_edit_active_task()


    def select_last(self) -> None:
        """Select last position in the task list."""
        
        position = self.app.ds.tasks.tree_model.get_n_items()
        self.task_selection.select_item(position - 1, True)
        

    def get_selection(self) -> list:
        """Get the currently selected tasks."""

        selection = self.task_selection.get_selection()
        result, iterator, _ = Gtk.BitsetIter.init_first(selection)
        selected = []
        
        while iterator.is_valid():
            val = iterator.get_value()
            selected.append(unwrap(self.task_selection.get_item(val), Task2))
            iterator.next()

        return selected


    def on_checkbox_toggled(self, button, task=None):
        """Callback when clicking a checkbox."""
        
        if task.status == Status.DISMISSED:
            task.toggle_dismiss()
        else:
            task.toggle_active()


    def task_setup_cb(self, factory, listitem, user_data=None):
        """Setup widgets for rows"""

        box = TaskBox()
        label = Gtk.Label() 
        separator = Gtk.Separator() 
        expander = Gtk.TreeExpander() 
        icons = Gtk.Label() 
        check = Gtk.CheckButton() 
        color = TagPill()
        due = Gtk.Label() 
        due_icon = Gtk.Image.new_from_icon_name('alarm-symbolic') 
        start = Gtk.Label() 
        start_icon = Gtk.Image.new_from_icon_name('media-playback-start-symbolic') 

        padding = str.encode('box { padding: 12px; }')

        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_data(padding)
        box.get_style_context().add_provider(cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        color.set_size_request(16, 16)
        
        # Does this even work?
        color.set_vexpand(False)
        color.set_valign(Gtk.Align.CENTER)

        separator.set_margin_end(12)
        expander.set_margin_start(6)
        expander.set_margin_end(6)
        check.set_margin_end(6)
        icons.set_margin_end(6)

        label.set_hexpand(True)
        label.set_margin_end(6)
        label.set_xalign(0)

        due_icon.set_margin_end(6)
        due.set_margin_end(24)

        start_icon.set_margin_end(6)
        start.set_margin_end(12)

        # DnD stuff
        source = Gtk.DragSource() 
        source.connect('prepare', self.drag_prepare)
        source.connect('drag-begin', self.drag_begin)
        source.connect('drag-end', self.drag_end)
        box.add_controller(source)

        # Set drop for DnD
        # drop = Gtk.DropTarget.new(Task2, Gdk.DragAction.COPY)
        # drop.connect('drop', drag_drop)
        # drop.connect('enter', drop_enter)

        # box.add_controller(drop)

        task_RMB_controller = Gtk.GestureSingle(button=Gdk.BUTTON_SECONDARY)
        task_RMB_controller.connect('end', self.on_task_RMB_click)
        box.add_controller(task_RMB_controller)

        box.append(expander)
        box.append(check)
        box.append(label)
        box.append(due_icon)
        box.append(due)
        box.append(start_icon)
        box.append(start)
        box.append(separator)
        box.append(color)
        box.append(icons)
        listitem.set_child(box)


    # def generate_css(tags: list) -> bytes:
    #     """Generate CSS styles for tags."""
        
    #     style = []
    
    #     for tag in tags:
    #         if tag.color:
    #             color_text = 'rgba(255, 0, 0, 0.25)'
    #             style.append(f'.tag-{tag.name}' + '{' + color_text + '; }')
        
    #     return str.encode('\n'.join(style))


    def task_bind_cb(self, factory, listitem, user_data=None):
        """Bind values to the widgets in setup_cb"""

        expander = listitem.get_child().get_first_child()
        check = expander.get_next_sibling()
        label = check.get_next_sibling()
        due_icon = label.get_next_sibling()
        due = due_icon.get_next_sibling()
        start_icon = due.get_next_sibling()
        start = start_icon.get_next_sibling()
        separator = start.get_next_sibling()
        color = separator.get_next_sibling()
        icons = color.get_next_sibling()

        box = listitem.get_child()
        
        # icons.set_visible(False)
        # color.set_visible(False)

        item = unwrap(listitem, Task2)

        colors = []
        for t in item.tags:
            if t.color and not t.icon:
                colorstr = Gdk.RGBA()
                colorstr.parse('#' + t.color)
                colors.append(colorstr)

        color.set_size_request((16 + 6) * len(colors), 16)
        color.colors = colors

        box.props.task = item
        expander.set_list_row(listitem.get_item())

        check.set_active(item.status == Status.DONE)

        if item.status == Status.ACTIVE:
            box.remove_css_class('closed-task')
        else:
            box.add_css_class('closed-task')

        # Set icons from tags
        icons_text = ''
        for t in item.tags:
            if t.icon:
                icons_text += t.icon

        icons.set_text(icons_text)
        
        # Set row color
        for t in item.tags:
            if t.color:
                color = Gdk.RGBA()
                color.parse('#' + t.color)
                color.alpha = 0.1
                background = str.encode('* { background:' + color.to_string() + '; }')

                cssProvider = Gtk.CssProvider()
                cssProvider.load_from_data(background)
                box.get_style_context().add_provider(cssProvider, 
                                                    Gtk.STYLE_PROVIDER_PRIORITY_USER)

        label.set_text(item.props.title)
        box.set_tooltip_text(item.props.excerpt)
        
        if item.date_due:
            due_icon.set_visible(True)
            due.set_text(item.date_due.to_readable_string())
        else:
            due_icon.set_visible(False)

        if item.date_start:
            start_icon.set_visible(True)
            start.set_text(item.date_start.to_readable_string())
        else:
            start_icon.set_visible(False)

        check.connect('toggled', self.on_checkbox_toggled, item)


    def drag_prepare(self, source, x, y):
        """Callback to prepare for the DnD operation"""

        selection = self.get_selection()
        
        if len(selection) > 1:
            data = Gio.ListStore()
            data.splice(0, 0, selection)

            content = Gdk.ContentProvider.new_for_value(GObject.Value(Gio.ListModel, data))
            return content

        else:
            # Get content from source
            data = source.get_widget().props.task

            # Set it as content provider
            content = Gdk.ContentProvider.new_for_value(data)
            return content


    def drag_begin(self, source, drag):
        """Callback when DnD beings"""

        source.get_widget().set_opacity(0.25)
        icon = Gtk.DragIcon.get_for_drag(drag)
        frame = Gtk.Frame()
        picture = Gtk.Picture.new_for_paintable(
            Gtk.WidgetPaintable.new(source.get_widget()))

        frame.set_child(picture)
        icon.set_child(frame)


    def drag_end(self, source, drag, unused):
        """Callback when DnD ends"""

        if source.get_widget():
            source.get_widget().set_opacity(1)


    def on_task_RMB_click(self, gesture, sequence) -> None:
        """Callback when right-clicking on an open task."""

        task = gesture.get_widget().task

        if task.status == Status.ACTIVE:
            menu = self.browser.open_menu
        else:
            menu = self.browser.closed_menu
            
        menu.set_parent(gesture.get_widget())
        menu.set_halign(Gtk.Align.START)
        menu.set_position(Gtk.PositionType.BOTTOM)

        point = gesture.get_point(sequence)
        rect = Gdk.Rectangle()
        rect.x = point.x
        rect.y = point.y
        menu.set_pointing_to(rect)
        menu.popup()
