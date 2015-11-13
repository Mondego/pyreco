__FILENAME__ = browser
#!/usr/bin/env python
# Copyright (C) 2007, 2008, 2009 Jan Michael Alonzo <jmalonzo@gmai.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# TODO:
#
# * fix tab relabelling
# * search page interface
# * custom button - w/o margins/padding to make tabs thin
#

from gettext import gettext as _

import gobject
import gtk
import pango
import webkit
from inspector import Inspector

ABOUT_PAGE = """
<html><head><title>PyWebKitGtk - About</title></head><body>
<h1>Welcome to <code>webbrowser.py</code></h1>
<p><a
href="http://code.google.com/p/pywebkitgtk/">http://code.google.com/p/pywebkitgtk/</a><br/>
</p>
</body></html>
"""

class BrowserPage(webkit.WebView):

    def __init__(self):
        webkit.WebView.__init__(self)
        settings = self.get_settings()
        settings.set_property("enable-developer-extras", True)

        # scale other content besides from text as well
        self.set_full_content_zoom(True)

        # make sure the items will be added in the end
        # hence the reason for the connect_after
        self.connect_after("populate-popup", self.populate_popup)

    def populate_popup(self, view, menu):
        # zoom buttons
        zoom_in = gtk.ImageMenuItem(gtk.STOCK_ZOOM_IN)
        zoom_in.connect('activate', zoom_in_cb, view)
        menu.append(zoom_in)

        zoom_out = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
        zoom_out.connect('activate', zoom_out_cb, view)
        menu.append(zoom_out)

        zoom_hundred = gtk.ImageMenuItem(gtk.STOCK_ZOOM_100)
        zoom_hundred.connect('activate', zoom_hundred_cb, view)
        menu.append(zoom_hundred)

        printitem = gtk.ImageMenuItem(gtk.STOCK_PRINT)
        menu.append(printitem)
        printitem.connect('activate', print_cb, view)

        page_properties = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        menu.append(page_properties)
        page_properties.connect('activate', page_properties_cb, view)

        menu.append(gtk.SeparatorMenuItem())

        aboutitem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menu.append(aboutitem)
        aboutitem.connect('activate', about_pywebkitgtk_cb, view)

        menu.show_all()
        return False

class TabLabel (gtk.HBox):
    """A class for Tab labels"""

    __gsignals__ = {
        "close": (gobject.SIGNAL_RUN_FIRST,
                  gobject.TYPE_NONE,
                  (gobject.TYPE_OBJECT,))
        }

    def __init__ (self, title, child):
        """initialize the tab label"""
        gtk.HBox.__init__(self, False, 4)
        self.title = title
        self.child = child
        self.label = gtk.Label(title)
        self.label.props.max_width_chars = 30
        self.label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self.label.set_alignment(0.0, 0.5)

        icon = gtk.image_new_from_stock(gtk.STOCK_ORIENTATION_PORTRAIT, gtk.ICON_SIZE_BUTTON)
        close_image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        close_button = gtk.Button()
        close_button.set_relief(gtk.RELIEF_NONE)
        close_button.connect("clicked", self._close_tab, child)
        close_button.set_image(close_image)
        self.pack_start(icon, False, False, 0)
        self.pack_start(self.label, True, True, 0)
        self.pack_start(close_button, False, False, 0)

        self.set_data("label", self.label)
        self.set_data("close-button", close_button)
        self.connect("style-set", tab_label_style_set_cb)

    def set_label (self, text):
        """sets the text of this label"""
        self.label.set_label(text)

    def _close_tab (self, widget, child):
        self.emit("close", child)

def tab_label_style_set_cb (tab_label, style):
    context = tab_label.get_pango_context()
    metrics = context.get_metrics(tab_label.style.font_desc, context.get_language())
    char_width = metrics.get_approximate_digit_width()
    (width, height) = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
    tab_label.set_size_request(20 * pango.PIXELS(char_width) + 2 * width,
                               pango.PIXELS(metrics.get_ascent() +
    metrics.get_descent()) + 8)


class ContentPane (gtk.Notebook):

    __gsignals__ = {
        "focus-view-title-changed": (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_OBJECT, gobject.TYPE_STRING,)),
        "new-window-requested": (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_OBJECT,))
        }

    def __init__ (self):
        """initialize the content pane"""
        gtk.Notebook.__init__(self)
        self.props.scrollable = True
        self.props.homogeneous = True
        self.connect("switch-page", self._switch_page)

        self.show_all()
        self._hovered_uri = None

    def load (self, text):
        """load the given uri in the current web view"""
        child = self.get_nth_page(self.get_current_page())
        view = child.get_child()
        view.open(text)

    def new_tab_with_webview (self, webview):
        """creates a new tab with the given webview as its child"""
        self._construct_tab_view(webview)

    def new_tab (self, url=None):
        """creates a new page in a new tab"""
        # create the tab content
        browser = BrowserPage()
        self._construct_tab_view(browser, url)

    def _construct_tab_view (self, web_view, url=None):
        web_view.connect("hovering-over-link", self._hovering_over_link_cb)
        web_view.connect("populate-popup", self._populate_page_popup_cb)
        web_view.connect("load-finished", self._view_load_finished_cb)
        web_view.connect("create-web-view", self._new_web_view_request_cb)
        web_view.connect("title-changed", self._title_changed_cb)
        inspector = Inspector(web_view.get_web_inspector())

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.add(web_view)
        scrolled_window.show_all()

        # create the tab
        label = TabLabel(url, scrolled_window)
        label.connect("close", self._close_tab)
        label.show_all()

        new_tab_number = self.append_page(scrolled_window, label)
        self.set_tab_label_packing(scrolled_window, False, False, gtk.PACK_START)
        self.set_tab_label(scrolled_window, label)

        # hide the tab if there's only one
        self.set_show_tabs(self.get_n_pages() > 1)

        self.show_all()
        self.set_current_page(new_tab_number)

        # load the content
        self._hovered_uri = None
        if not url:
            web_view.load_string(ABOUT_PAGE, "text/html", "iso-8859-15", "about")
        else:
            web_view.load_uri(url)

    def _populate_page_popup_cb(self, view, menu):
        # misc
        if self._hovered_uri:
            open_in_new_tab = gtk.MenuItem(_("Open Link in New Tab"))
            open_in_new_tab.connect("activate", self._open_in_new_tab, view)
            menu.insert(open_in_new_tab, 0)
            menu.show_all()

    def _open_in_new_tab (self, menuitem, view):
        self.new_tab(self._hovered_uri)

    def _close_tab (self, label, child):
        page_num = self.page_num(child)
        if page_num != -1:
            view = child.get_child()
            view.destroy()
            self.remove_page(page_num)
        self.set_show_tabs(self.get_n_pages() > 1)

    def _switch_page (self, notebook, page, page_num):
        child = self.get_nth_page(page_num)
        view = child.get_child()
        frame = view.get_main_frame()
        self.emit("focus-view-title-changed", frame, frame.props.title)

    def _hovering_over_link_cb (self, view, title, uri):
        self._hovered_uri = uri

    def _title_changed_cb (self, view, frame, title):
        child = self.get_nth_page(self.get_current_page())
        label = self.get_tab_label(child)
        label.set_label(title)
        self.emit("focus-view-title-changed", frame, title)

    def _view_load_finished_cb(self, view, frame):
        child = self.get_nth_page(self.get_current_page())
        label = self.get_tab_label(child)
        title = frame.get_title()
        if not title:
            title = frame.get_uri()
        if title:
            label.set_label(title)

    def _new_web_view_request_cb (self, web_view, web_frame):
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        view = BrowserPage()
        scrolled_window.add(view)
        scrolled_window.show_all()

        vbox = gtk.VBox(spacing=1)
        vbox.pack_start(scrolled_window, True, True)

        window = gtk.Window()
        window.add(vbox)
        view.connect("web-view-ready", self._new_web_view_ready_cb)
        return view

    def _new_web_view_ready_cb (self, web_view):
        self.emit("new-window-requested", web_view)


class WebToolbar(gtk.Toolbar):

    __gsignals__ = {
        "load-requested": (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,)),
        "new-tab-requested": (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE, ()),
        "view-source-mode-requested": (gobject.SIGNAL_RUN_FIRST,
                                       gobject.TYPE_NONE,
                                       (gobject.TYPE_BOOLEAN, ))
        }

    def __init__(self, location_enabled=True, toolbar_enabled=True):
        gtk.Toolbar.__init__(self)

        # location entry
        if location_enabled:
            self._entry = gtk.Entry()
            self._entry.connect('activate', self._entry_activate_cb)
            entry_item = gtk.ToolItem()
            entry_item.set_expand(True)
            entry_item.add(self._entry)
            self._entry.show()
            self.insert(entry_item, -1)
            entry_item.show()

        # add tab button
        if toolbar_enabled:
            addTabButton = gtk.ToolButton(gtk.STOCK_ADD)
            addTabButton.connect("clicked", self._add_tab_cb)
            self.insert(addTabButton, -1)
            addTabButton.show()

            viewSourceItem = gtk.ToggleToolButton(gtk.STOCK_PROPERTIES)
            viewSourceItem.set_label("View Source Mode")
            viewSourceItem.connect('toggled', self._view_source_mode_cb)
            self.insert(viewSourceItem, -1)
            viewSourceItem.show()

    def location_set_text (self, text):
        self._entry.set_text(text)

    def _entry_activate_cb(self, entry):
        self.emit("load-requested", entry.props.text)

    def _add_tab_cb(self, button):
        self.emit("new-tab-requested")

    def _view_source_mode_cb(self, button):
        self.emit("view-source-mode-requested", button.get_active())

class WebBrowser(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)

        toolbar = WebToolbar()
        content_tabs = ContentPane()
        content_tabs.connect("focus-view-title-changed", self._title_changed_cb, toolbar)
        content_tabs.connect("new-window-requested", self._new_window_requested_cb)
        toolbar.connect("load-requested", load_requested_cb, content_tabs)
        toolbar.connect("new-tab-requested", new_tab_requested_cb, content_tabs)
        toolbar.connect("view-source-mode-requested", view_source_mode_requested_cb, content_tabs)

        vbox = gtk.VBox(spacing=1)
        vbox.pack_start(toolbar, expand=False, fill=False)
        vbox.pack_start(content_tabs)

        self.add(vbox)
        self.set_default_size(800, 600)
        self.connect('destroy', destroy_cb, content_tabs)

        self.show_all()

        content_tabs.new_tab("http://www.google.com")

    def _new_window_requested_cb (self, content_pane, view):
        features = view.get_window_features()
        window = view.get_toplevel()

        scrolled_window = view.get_parent()
        if features.get_property("scrollbar-visible"):
            scrolled_window.props.hscrollbar_policy = gtk.POLICY_NEVER
            scrolled_window.props.vscrollbar_policy = gtk.POLICY_NEVER

        isLocationbarVisible = features.get_property("locationbar-visible")
        isToolbarVisible = features.get_property("toolbar-visible")
        if isLocationbarVisible or isToolbarVisible:
            toolbar = WebToolbar(isLocationbarVisible, isToolbarVisible)
            scrolled_window.get_parent().pack_start(toolbar, False, False, 0)

        window.set_default_size(features.props.width, features.props.height)
        window.move(features.props.x, features.props.y)

        window.show_all()
        return True

    def _title_changed_cb (self, tabbed_pane, frame, title, toolbar):
        if not title:
           title = frame.get_uri()
        self.set_title(_("PyWebKitGtk - %s") % title)
        load_committed_cb(tabbed_pane, frame, toolbar)

# event handlers
def new_tab_requested_cb (toolbar, content_pane):
    content_pane.new_tab("about:blank")

def load_requested_cb (widget, text, content_pane):
    if not text:
        return
    content_pane.load(text)

def load_committed_cb (tabbed_pane, frame, toolbar):
    uri = frame.get_uri()
    if uri:
        toolbar.location_set_text(uri)

def destroy_cb(window, content_pane):
    """destroy window resources"""
    num_pages = content_pane.get_n_pages()
    while num_pages != -1:
        child = content_pane.get_nth_page(num_pages)
        if child:
            view = child.get_child()
        num_pages = num_pages - 1
    window.destroy()
    gtk.main_quit()

# context menu item callbacks
def about_pywebkitgtk_cb(menu_item, web_view):
    web_view.open("http://live.gnome.org/PyWebKitGtk")

def zoom_in_cb(menu_item, web_view):
    """Zoom into the page"""
    web_view.zoom_in()

def zoom_out_cb(menu_item, web_view):
    """Zoom out of the page"""
    web_view.zoom_out()

def zoom_hundred_cb(menu_item, web_view):
    """Zoom 100%"""
    if not (web_view.get_zoom_level() == 1.0):
        web_view.set_zoom_level(1.0)

def print_cb(menu_item, web_view):
    mainframe = web_view.get_main_frame()
    mainframe.print_full(gtk.PrintOperation(), gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG);

def page_properties_cb(menu_item, web_view):
    mainframe = web_view.get_main_frame()
    datasource = mainframe.get_data_source()
    main_resource = datasource.get_main_resource()
    window = gtk.Window()
    window.set_default_size(100, 60)
    vbox = gtk.VBox()
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label("MIME Type :"), False, False)
    hbox.pack_end(gtk.Label(main_resource.get_mime_type()), False, False)
    vbox.pack_start(hbox, False, False)
    hbox2 = gtk.HBox()
    hbox2.pack_start(gtk.Label("URI : "), False, False)
    hbox2.pack_end(gtk.Label(main_resource.get_uri()), False, False)
    vbox.pack_start(hbox2, False, False)
    hbox3 = gtk.HBox()
    hbox3.pack_start(gtk.Label("Encoding : "), False, False)
    hbox3.pack_end(gtk.Label(main_resource.get_encoding()), False, False)
    vbox.pack_start(hbox3, False, False)
    window.add(vbox)
    window.show_all()
    window.present()


def view_source_mode_requested_cb(widget, is_active, content_pane):
    currentTab = content_pane.get_nth_page(content_pane.get_current_page())
    childView = currentTab.get_child()
    childView.set_view_source_mode(is_active)
    childView.reload()

if __name__ == "__main__":
    webbrowser = WebBrowser()
    gtk.main()

########NEW FILE########
__FILENAME__ = inspector
# Copyright (C) 2008 Jan Alonzo <jmalonzo@unpluggable.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import webkit

class Inspector (gtk.Window):
    def __init__ (self, inspector):
        """initialize the WebInspector class"""
        gtk.Window.__init__(self)
        self.set_default_size(600, 480)

        self._web_inspector = inspector

        self._web_inspector.connect("inspect-web-view",
                                    self._inspect_web_view_cb)
        self._web_inspector.connect("show-window",
                                    self._show_window_cb)
        self._web_inspector.connect("attach-window",
                                    self._attach_window_cb)
        self._web_inspector.connect("detach-window",
                                    self._detach_window_cb)
        self._web_inspector.connect("close-window",
                                    self._close_window_cb)
        self._web_inspector.connect("finished",
                                    self._finished_cb)

        self.connect("delete-event", self._close_window_cb)

    def _inspect_web_view_cb (self, inspector, web_view):
        """Called when the 'inspect' menu item is activated"""
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        webview = webkit.WebView()
        scrolled_window.add(webview)
        scrolled_window.show_all()

        self.add(scrolled_window)
        return webview

    def _show_window_cb (self, inspector):
        """Called when the inspector window should be displayed"""
        self.present()
        return True

    def _attach_window_cb (self, inspector):
        """Called when the inspector should displayed in the same
        window as the WebView being inspected
        """
        return False

    def _detach_window_cb (self, inspector):
        """Called when the inspector should appear in a separate window"""
        return False

    def _close_window_cb (self, inspector, view):
        """Called when the inspector window should be closed"""
        self.hide()
        return True

    def _finished_cb (self, inspector):
        """Called when inspection is done"""
        self._web_inspector = 0
        self.destroy()
        return False

########NEW FILE########
__FILENAME__ = test_networkrequest

import webkit
from webkit import NetworkRequest

import gobject
import unittest

class TestNetworkRequest(unittest.TestCase):

    def setUp(self):
        self.request = webkit.NetworkRequest()

    def testsettergetter(self):
        self.request.set_uri("http://example.com/index.php")
        self.assertEqual("http://example.com/index.php", self.request.get_uri())

    def testdefaultinitvalue(self):
        self.assertEqual("about:blank", self.request.get_uri())

    def testsetproxy(self):
        webkit.set_proxy("http://localhost:8080")
        # we're still OK.
        self.assertTrue(True)

    def tearDown(self):
        del self.request

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_networkresponse

import webkit
from webkit import NetworkResponse

import gobject
import unittest

class TestWebView(unittest.TestCase):

    def setUp(self):
        self.response = webkit.NetworkResponse()

    def testsettergetter(self):
        self.response.set_uri("http://example.com/index.php")
        self.assertEqual("http://example.com/index.php", self.response.get_uri())

    def testdefaultinitvalue(self):
        self.assertEqual("about:blank", self.response.get_uri())

    def tearDown(self):
        del self.response

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_webbackforwardlist

from webkit import WebHistoryItem, WebBackForwardList, WebView

import gobject
import unittest

class TestWebBackForwardList (unittest.TestCase):
    """Test WebBackForwardList functions"""

    def setUp(self):
        gobject.threads_init()
        self.view = WebView()
        self.bf_list = self.view.get_back_forward_list()

    def testadditem(self):
        item =  WebHistoryItem(uri="http://example.com/", title="Example1")
        self.bf_list.add_item(item)
        self.assertEqual(item, self.bf_list.get_current_item())
        currentItem = self.bf_list.get_current_item()
        self.assertEqual("Example1", currentItem.get_title())
        self.assertEqual("http://example.com/", currentItem.get_uri())

    def testbackforwardlistwithlimit(self):
        item1 =  WebHistoryItem(uri="http://example.com/1/", title="Example1")
        item2 =  WebHistoryItem(uri="http://example.com/2/", title="Example2")
        item3 =  WebHistoryItem(uri="http://example.com/3/", title="Example3")
        item4 =  WebHistoryItem(uri="http://example.com/4/", title="Example4")
        self.bf_list.add_item(item1)
        self.bf_list.add_item(item2)
        self.bf_list.add_item(item3)
        self.bf_list.add_item(item4)
        backList = list()
        backList = self.bf_list.get_back_list_with_limit(10)
        self.assertTrue(backList is not None)
        self.assertEqual("Example4", self.bf_list.get_current_item().get_title())
        self.assertEqual("Example3", backList[0].props.title)
        self.assertEqual("Example2", backList[1].props.title)
        self.assertEqual("Example1", backList[2].props.title)
        self.bf_list.go_to_item(item1)
        self.assertEqual(self.bf_list.get_current_item().get_title(), item1.get_title())
        forwardList = list()
        forwardList = self.bf_list.get_forward_list_with_limit(10)
        self.assertTrue(forwardList is not None)
        self.assertEqual("Example4", forwardList[0].props.title)
        self.assertEqual("Example3", forwardList[1].props.title)
        self.assertEqual("Example2", forwardList[2].props.title)

    def testclearbackforwardlist(self):
        item1 =  WebHistoryItem(uri="http://example.com/1/", title="Example1")
        item2 =  WebHistoryItem(uri="http://example.com/2/", title="Example2")

        self.bf_list.set_limit(0)
        self.bf_list.set_limit(1)
        self.bf_list.add_item(item2)
        self.assertEqual(self.bf_list.get_back_length(), 0)
        self.assertEqual(self.bf_list.get_forward_length(), 0)
        self.assertEqual(self.bf_list.get_current_item(), item2)

    def tearDown(self):
        # nothing here.
        pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_webframe

from webkit import WebFrame, WebView

import gobject
import unittest

class TestWebFrame(unittest.TestCase):

    def setUp(self):
        gobject.threads_init()
        self.view = WebView()
        self.mainFrame = self.view.get_main_frame()

    def testloaduri(self):
        self.mainFrame.load_uri("about:blank")
        self.assertEqual("about:blank", self.mainFrame.get_uri());


    def tearDown(self):
        self.view.destroy()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_webnavigationaction

import webkit
import unittest

class TestWebNavigationAction (unittest.TestCase):
    """Test WebNavigationAction functions"""

    def setUp (self):
        """set up test"""
        self.navigation_action = webkit.WebNavigationAction()

    def testsetreason (self):
        """test for WebNavigationAction.set_reason/get_reason overrides"""
        reasons = ["link-clicked","reload","form-submitted","back-forward","form-resubmitted","other"]
        for r in reasons:
            self.navigation_action.set_reason(r)
            self.assertEqual(r, self.navigation_action.get_reason().value_nick)

    def testoriginaluri (self):
        """test WebNavigationAction.set/get_original_uri"""
        self.navigation_action.set_original_uri("http://www.google.com")
        self.assertEqual("http://www.google.com", self.navigation_action.get_original_uri())

if __name__ == '__main__':
   unittest.main()

########NEW FILE########
