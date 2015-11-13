__FILENAME__ = about
# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


from os.path import join
from hamster.lib.configuration import runtime
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk

class About(object):
    def __init__(self, parent = None):
        about = gtk.AboutDialog()
        self.window = about
        infos = {
            "program-name" : _("Time Tracker"),
            "name" : _("Time Tracker"), #this should be deprecated in gtk 2.10
            "version" : runtime.version,
            "comments" : _(u"Project Hamster — track your time"),
            "copyright" : _(u"Copyright © 2007–2010 Toms Bauģis and others"),
            "website" : "http://projecthamster.wordpress.com/",
            "website-label" : _("Project Hamster Website"),
            "title": _("About Time Tracker"),
            "wrap-license": True
        }

        about.set_authors(["Toms Bauģis <toms.baugis@gmail.com>",
                           "Patryk Zawadzki <patrys@pld-linux.org>",
                           "Pēteris Caune <cuu508@gmail.com>",
                           "Juanje Ojeda <jojeda@emergya.es>"])
        about.set_artists(["Kalle Persson <kalle@kallepersson.se>"])

        about.set_translator_credits(_("translator-credits"))

        for prop, val in infos.items():
            about.set_property(prop, val)

        about.set_logo_icon_name("hamster-time-tracker")

        about.connect("response", lambda self, *args: self.destroy())
        about.show_all()

########NEW FILE########
__FILENAME__ = client
# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2007-2009 Toms Baugis <toms.baugis@gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


import datetime as dt
from calendar import timegm
import dbus, dbus.mainloop.glib
from gi.repository import GObject as gobject
from hamster.lib import Fact
from hamster.lib import trophies

def from_dbus_fact(fact):
    """unpack the struct into a proper dict"""
    return Fact(fact[4],
                start_time  = dt.datetime.utcfromtimestamp(fact[1]),
                end_time = dt.datetime.utcfromtimestamp(fact[2]) if fact[2] else None,
                description = fact[3],
                activity_id = fact[5],
                category = fact[6],
                tags = fact[7],
                date = dt.datetime.utcfromtimestamp(fact[8]).date(),
                delta = dt.timedelta(days = fact[9] // (24 * 60 * 60),
                                     seconds = fact[9] % (24 * 60 * 60)),
            id = fact[0]
            )

class Storage(gobject.GObject):
    """Hamster client class, communicating to hamster storage daemon via d-bus.
       Subscribe to the `tags-changed`, `facts-changed` and `activities-changed`
       signals to be notified when an appropriate factoid of interest has been
       changed.

       In storage a distinguishment is made between the classificator of
       activities and the event in tracking log.
       When talking about the event we use term 'fact'. For the classificator
       we use term 'activity'.
       The relationship is - one activity can be used in several facts.
       The rest is hopefully obvious. But if not, please file bug reports!
    """
    __gsignals__ = {
        "tags-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "facts-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "activities-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "toggle-called": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self._connection = None # will be initiated on demand

        self.bus.add_signal_receiver(self._on_tags_changed, 'TagsChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_facts_changed, 'FactsChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_activities_changed, 'ActivitiesChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_toggle_called, 'ToggleCalled', 'org.gnome.Hamster')

        self.bus.add_signal_receiver(self._on_dbus_connection_change, 'NameOwnerChanged',
                                     'org.freedesktop.DBus', arg0='org.gnome.Hamster')
    @staticmethod
    def _to_dict(columns, result_list):
        return [dict(zip(columns, row)) for row in result_list]

    @property
    def conn(self):
        if not self._connection:
            self._connection = dbus.Interface(self.bus.get_object('org.gnome.Hamster',
                                                              '/org/gnome/Hamster'),
                                              dbus_interface='org.gnome.Hamster')
        return self._connection

    def _on_dbus_connection_change(self, name, old, new):
        self._connection = None

    def _on_tags_changed(self):
        self.emit("tags-changed")

    def _on_facts_changed(self):
        self.emit("facts-changed")

    def _on_activities_changed(self):
        self.emit("activities-changed")

    def _on_toggle_called(self):
        self.emit("toggle-called")

    def toggle(self):
        """toggle visibility of the main application window if any"""
        self.conn.Toggle()

    def get_todays_facts(self):
        """returns facts of the current date, respecting hamster midnight
           hamster midnight is stored in gconf, and presented in minutes
        """
        return [from_dbus_fact(fact) for fact in self.conn.GetTodaysFacts()]

    def get_facts(self, date, end_date = None, search_terms = ""):
        """Returns facts for the time span matching the optional filter criteria.
           In search terms comma (",") translates to boolean OR and space (" ")
           to boolean AND.
           Filter is applied to tags, categories, activity names and description
        """
        date = timegm(date.timetuple())
        end_date = end_date or 0
        if end_date:
            end_date = timegm(end_date.timetuple())

        return [from_dbus_fact(fact) for fact in self.conn.GetFacts(date,
                                                                    end_date,
                                                                    search_terms)]

    def get_activities(self, search = ""):
        """returns list of activities name matching search criteria.
           results are sorted by most recent usage.
           search is case insensitive
        """
        return self._to_dict(('name', 'category'), self.conn.GetActivities(search))

    def get_categories(self):
        """returns list of categories"""
        return self._to_dict(('id', 'name'), self.conn.GetCategories())

    def get_tags(self, only_autocomplete = False):
        """returns list of all tags. by default only those that have been set for autocomplete"""
        return self._to_dict(('id', 'name', 'autocomplete'), self.conn.GetTags(only_autocomplete))


    def get_tag_ids(self, tags):
        """find tag IDs by name. tags should be a list of labels
           if a requested tag had been removed from the autocomplete list, it
           will be ressurrected. if tag with such label does not exist, it will
           be created.
           on database changes the `tags-changed` signal is emitted.
        """
        return self._to_dict(('id', 'name', 'autocomplete'), self.conn.GetTagIds(tags))

    def update_autocomplete_tags(self, tags):
        """update list of tags that should autocomplete. this list replaces
           anything that is currently set"""
        self.conn.SetTagsAutocomplete(tags)

    def get_fact(self, id):
        """returns fact by it's ID"""
        return from_dbus_fact(self.conn.GetFact(id))

    def add_fact(self, fact, temporary_activity = False):
        """Add fact. activity name can use the
        `[-]start_time[-end_time] activity@category, description #tag1 #tag2`
        syntax, or params can be stated explicitly.
        Params will take precedence over the derived values.
        start_time defaults to current moment.
        """
        if not fact.activity:
            return None

        serialized = fact.serialized_name()

        start_timestamp = timegm((fact.start_time or dt.datetime.now()).timetuple())

        end_timestamp = fact.end_time or 0
        if end_timestamp:
            end_timestamp = timegm(end_timestamp.timetuple())

        new_id = self.conn.AddFact(serialized,
                                   start_timestamp,
                                   end_timestamp,
                                   temporary_activity)

        # TODO - the parsing should happen just once and preferably here
        # we should feed (serialized_activity, start_time, end_time) into AddFact and others
        if new_id:
            trophies.checker.check_fact_based(fact)
        return new_id

    def stop_tracking(self, end_time = None):
        """Stop tracking current activity. end_time can be passed in if the
        activity should have other end time than the current moment"""
        end_time = timegm((end_time or dt.datetime.now()).timetuple())
        return self.conn.StopTracking(end_time)

    def remove_fact(self, fact_id):
        "delete fact from database"
        self.conn.RemoveFact(fact_id)

    def update_fact(self, fact_id, fact, temporary_activity = False):
        """Update fact values. See add_fact for rules.
        Update is performed via remove/insert, so the
        fact_id after update should not be used anymore. Instead use the ID
        from the fact dict that is returned by this function"""


        start_time = timegm((fact.start_time or dt.datetime.now()).timetuple())

        end_time = fact.end_time or 0
        if end_time:
            end_time = timegm(end_time.timetuple())

        new_id =  self.conn.UpdateFact(fact_id,
                                       fact.serialized_name(),
                                       start_time,
                                       end_time,
                                       temporary_activity)

        trophies.checker.check_update_based(fact_id, new_id, fact)
        return new_id


    def get_category_activities(self, category_id = None):
        """Return activities for category. If category is not specified, will
        return activities that have no category"""
        category_id = category_id or -1
        return self._to_dict(('id', 'name', 'category_id', 'category'), self.conn.GetCategoryActivities(category_id))

    def get_category_id(self, category_name):
        """returns category id by name"""
        return self.conn.GetCategoryId(category_name)

    def get_activity_by_name(self, activity, category_id = None, resurrect = True):
        """returns activity dict by name and optionally filtering by category.
           if activity is found but is marked as deleted, it will be resurrected
           unless told otherwise in the resurrect param
        """
        category_id = category_id or 0
        return self.conn.GetActivityByName(activity, category_id, resurrect)

    # category and activity manipulations (normally just via preferences)
    def remove_activity(self, id):
        self.conn.RemoveActivity(id)

    def remove_category(self, id):
        self.conn.RemoveCategory(id)

    def change_category(self, id, category_id):
        return self.conn.ChangeCategory(id, category_id)

    def update_activity(self, id, name, category_id):
        return self.conn.UpdateActivity(id, name, category_id)

    def add_activity(self, name, category_id = -1):
        return self.conn.AddActivity(name, category_id)

    def update_category(self, id, name):
        return self.conn.UpdateCategory(id, name)

    def add_category(self, name):
        return self.conn.AddCategory(name)

########NEW FILE########
__FILENAME__ = edit_activity
# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
import time
import datetime as dt

""" TODO: hook into notifications and refresh our days if some evil neighbour
          edit fact window has dared to edit facts
"""
import widgets
from hamster.lib.configuration import runtime, conf, load_ui_file
from lib import Fact

class CustomFactController(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self,  parent=None, fact_date=None, fact_id=None):
        gobject.GObject.__init__(self)

        self._gui = load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')
        self.window.set_size_request(600, 200)
        self.parent, self.fact_id = parent, fact_id

        #TODO - should somehow hint that time is not welcome here
        self.activity = widgets.ActivityEntry()
        self.activity.connect("changed", self.on_activity_changed)
        self.get_widget("activity_box").add(self.activity)

        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        self.date = fact_date
        if not self.date:
            self.date = (dt.datetime.now() - dt.timedelta(hours=self.day_start.hour,
                                                          minutes=self.day_start.minute)).date()


        self.dayline = widgets.DayLine()
        self._gui.get_object("day_preview").add(self.dayline)

        self.activity.grab_focus()
        if fact_id:
            fact = runtime.storage.get_fact(fact_id)
            label = fact.start_time.strftime("%H:%M")
            if fact.end_time:
                label += fact.end_time.strftime(" %H:%M")

            label += " " + fact.serialized_name()
            with self.activity.handler_block(self.activity.checker):
                self.activity.set_text(label)
                self.activity.select_region(len(label) - len(fact.serialized_name()), -1)


            buf = gtk.TextBuffer()
            buf.set_text(fact.description or "")
            self.get_widget('description').set_buffer(buf)

            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))

        else:
            self.get_widget("delete_button").set_sensitive(False)


        self._gui.connect_signals(self)
        self.validate_fields()
        self.window.show_all()

    def on_prev_day_clicked(self, button):
        self.date = self.date - dt.timedelta(days=1)
        self.validate_fields()

    def on_next_day_clicked(self, button):
        self.date = self.date + dt.timedelta(days=1)
        self.validate_fields()

    def draw_preview(self, start_time, end_time=None):
        day_facts = runtime.storage.get_facts(self.date)
        self.dayline.plot(self.date, day_facts, start_time, end_time)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()


    def figure_description(self):
        buf = self.get_widget('description').get_buffer()
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)\
                         .decode("utf-8")
        return description.strip()


    def localized_fact(self):
        """makes sure fact is in our date"""
        fact = Fact(self.activity.get_text())
        if fact.start_time:
            fact.start_time = dt.datetime.combine(self.date, fact.start_time.time())

        if fact.end_time:
            fact.end_time = dt.datetime.combine(self.date, fact.end_time.time())

        return fact



    def on_save_button_clicked(self, button):
        fact = self.localized_fact()
        fact.description = self.figure_description()
        if not fact.activity:
            return False

        if self.fact_id:
            runtime.storage.update_fact(self.fact_id, fact)
        else:
            runtime.storage.add_fact(fact)

        self.close_window()

    def on_activity_changed(self, combo):
        self.validate_fields()

    def validate_fields(self, widget = None):
        fact = self.localized_fact()

        now = dt.datetime.now()
        self.get_widget("button-next-day").set_sensitive(self.date < now.date())

        if self.date != now.date():
            now = dt.datetime.combine(self.date, now.time())

        self.draw_preview(fact.start_time or now,
                          fact.end_time or now)

        looks_good = fact.activity is not None and fact.start_time is not None
        self.get_widget("save_button").set_sensitive(looks_good)
        return looks_good


    def on_delete_clicked(self, button):
        runtime.storage.remove_fact(self.fact_id)
        self.close_window()

    def on_cancel_clicked(self, button):
        self.close_window()

    def on_close(self, widget, event):
        self.close_window()

    def on_window_key_pressed(self, tree, event_key):
        popups = self.activity.popup.get_property("visible");

        if (event_key.keyval == gdk.KEY_Escape or \
           (event_key.keyval == gdk.KEY_w and event_key.state & gdk.ModifierType.CONTROL_MASK)):
            if popups:
                return False

            self.close_window()

        elif event_key.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter):
            if popups:
                return False
            if self.get_widget('description').has_focus():
                return False
            self.on_save_button_clicked(None)



    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            self.window = None
            self._gui = None
            self.emit("on-close")

########NEW FILE########
__FILENAME__ = external
# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2008, 2010 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import logging
from hamster.lib.configuration import conf
from gi.repository import GObject as gobject
import dbus, dbus.mainloop.glib

try:
    import evolution
    from evolution import ecal
except:
    evolution = None

class ActivitiesSource(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        self.source = conf.get("activities_source")
        self.__gtg_connection = None

        if self.source == "evo" and not evolution:
            self.source == "" # on failure pretend that there is no evolution
        elif self.source == "gtg":
            gobject.GObject.__init__(self)
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    def get_activities(self, query = None):
        if not self.source:
            return []

        if self.source == "evo":
            return [activity for activity in get_eds_tasks()
                         if query is None or activity['name'].startswith(query)]

        elif self.source == "gtg":
            conn = self.__get_gtg_connection()
            if not conn:
                return []

            activities = []

            tasks = []
            try:
                tasks = conn.GetTasks()
            except dbus.exceptions.DBusException:  #TODO too lame to figure out how to connect to the disconnect signal
                self.__gtg_connection = None
                return self.get_activities(query) # reconnect


            for task in tasks:
                if query is None or task['title'].lower().startswith(query):
                    name = task['title']
                    if len(task['tags']):
                        name = "%s, %s" % (name, " ".join([tag.replace("@", "#") for tag in task['tags']]))

                    activities.append({"name": name,
                                       "category": ""})

            return activities

    def __get_gtg_connection(self):
        bus = dbus.SessionBus()
        if self.__gtg_connection and bus.name_has_owner("org.gnome.GTG"):
            return self.__gtg_connection

        if bus.name_has_owner("org.gnome.GTG"):
            self.__gtg_connection = dbus.Interface(bus.get_object('org.gnome.GTG', '/org/gnome/GTG'),
                                                   dbus_interface='org.gnome.GTG')
            return self.__gtg_connection
        else:
            return None



def get_eds_tasks():
    try:
        sources = ecal.list_task_sources()
        tasks = []
        if not sources:
            # BUG - http://bugzilla.gnome.org/show_bug.cgi?id=546825
            sources = [('default', 'default')]

        for source in sources:
            category = source[0]

            data = ecal.open_calendar_source(source[1], ecal.CAL_SOURCE_TYPE_TODO)
            if data:
                for task in data.get_all_objects():
                    if task.get_status() in [ecal.ICAL_STATUS_NONE, ecal.ICAL_STATUS_INPROCESS]:
                        tasks.append({'name': task.get_summary(), 'category' : category})
        return tasks
    except Exception, e:
        logging.warn(e)
        return []

########NEW FILE########
__FILENAME__ = idle
# - coding: utf-8 -

# Copyright (C) 2008 Patryk Zawadzki <patrys at pld-linux.org>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import datetime as dt
import logging
import dbus
from dbus.lowlevel import Message
from gi.repository import GConf as gconf
from gi.repository import GObject as gobject

class DbusIdleListener(gobject.GObject):
    """
    Listen for idleness coming from org.gnome.ScreenSaver

    Monitors org.gnome.ScreenSaver for idleness. There are two types,
    implicit (due to inactivity) and explicit (lock screen), that need to be
    handled differently. An implicit idle state should subtract the
    time-to-become-idle (as specified in the gconf) from the last activity,
    but an explicit idle state should not.

    The signals are inspected for the "ActiveChanged" and "Lock"
    members coming from the org.gnome.ScreenSaver interface and the
    and is_screen_locked members are updated appropriately.
    """
    __gsignals__ = {
        "idle-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    }
    def __init__(self):
        gobject.GObject.__init__(self)

        self.screensaver_uri = "org.gnome.ScreenSaver"
        self.screen_locked = False
        self.idle_from = None
        self.timeout_minutes = 0 # minutes after session is considered idle
        self.idle_was_there = False # a workaround variable for pre 2.26

        try:
            self.bus = dbus.SessionBus()
        except:
            return 0
        # Listen for chatter on the screensaver interface.
        # We cannot just add additional match strings to narrow down
        # what we hear because match strings are ORed together.
        # E.g., if we were to make the match string
        # "interface='org.gnome.ScreenSaver', type='method_call'",
        # we would not get only screensaver's method calls, rather
        # we would get anything on the screensaver interface, as well
        # as any method calls on *any* interface. Therefore the
        # bus_inspector needs to do some additional filtering.
        self.bus.add_match_string_non_blocking("interface='%s'" %
                                                           self.screensaver_uri)
        self.bus.add_message_filter(self.bus_inspector)


    def bus_inspector(self, bus, message):
        """
        Inspect the bus for screensaver messages of interest
        """

        # We only care about stuff on this interface.  We did filter
        # for it above, but even so we still hear from ourselves
        # (hamster messages).
        if message.get_interface() != self.screensaver_uri:
            return True

        member = message.get_member()

        if member in ("SessionIdleChanged", "ActiveChanged"):
            logging.debug("%s -> %s" % (member, message.get_args_list()))

            idle_state = message.get_args_list()[0]
            if idle_state:
                self.idle_from = dt.datetime.now()

                # from gnome screensaver 2.24 to 2.28 they have switched
                # configuration keys and signal types.
                # luckily we can determine key by signal type
                if member == "SessionIdleChanged":
                    delay_key = "/apps/gnome-screensaver/idle_delay"
                else:
                    delay_key = "/desktop/gnome/session/idle_delay"

                client = gconf.Client.get_default()
                self.timeout_minutes = client.get_int(delay_key)

            else:
                self.screen_locked = False
                self.idle_from = None

            if member == "ActiveChanged":
                # ActiveChanged comes before SessionIdleChanged signal
                # as a workaround for pre 2.26, we will wait a second - maybe
                # SessionIdleChanged signal kicks in
                def dispatch_active_changed(idle_state):
                    if not self.idle_was_there:
                        self.emit('idle-changed', idle_state)
                    self.idle_was_there = False

                gobject.timeout_add_seconds(1, dispatch_active_changed, idle_state)

            else:
                # dispatch idle status change to interested parties
                self.idle_was_there = True
                self.emit('idle-changed', idle_state)

        elif member == "Lock":
            # in case of lock, lock signal will be sent first, followed by
            # ActiveChanged and SessionIdle signals
            logging.debug("Screen Lock Requested")
            self.screen_locked = True

        return


    def getIdleFrom(self):
        if not self.idle_from:
            return dt.datetime.now()

        if self.screen_locked:
            return self.idle_from
        else:
            # Only subtract idle time from the running task when
            # idleness is due to time out, not a screen lock.
            return self.idle_from - dt.timedelta(minutes = self.timeout_minutes)

########NEW FILE########
__FILENAME__ = charting
# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
import datetime as dt
import time
import graphics, stuff
import locale

class Bar(graphics.Sprite):
    def __init__(self, key, value, normalized, label_color):
        graphics.Sprite.__init__(self, cache_as_bitmap=True)
        self.key, self.value, self.normalized = key, value, normalized

        self.height = 0
        self.width = 20
        self.interactive = True
        self.fill = None

        self.label = graphics.Label(value, size=8, color=label_color)
        self.label_background = graphics.Rectangle(self.label.width + 4, self.label.height + 4, 4, visible=False)
        self.add_child(self.label_background)
        self.add_child(self.label)
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        # invisible rectangle for the mouse, covering whole area
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill("#000", 0)

        size = round(self.width * self.normalized)

        self.graphics.rectangle(0, 0, size, self.height, 3)
        self.graphics.rectangle(0, 0, min(size, 3), self.height)
        self.graphics.fill(self.fill)

        self.label.y = (self.height - self.label.height) / 2

        horiz_offset = min(10, self.label.y * 2)

        if self.label.width < size - horiz_offset * 2:
            #if it fits in the bar
            self.label.x = size - self.label.width - horiz_offset
        else:
            self.label.x = size + 3

        self.label_background.x = self.label.x - 2
        self.label_background.y = self.label.y - 2


class Chart(graphics.Scene):
    __gsignals__ = {
        "bar-clicked": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
    }

    def __init__(self, max_bar_width = 20, legend_width = 70, value_format = "%.2f", interactive = True):
        graphics.Scene.__init__(self)

        self.selected_keys = [] # keys of selected bars

        self.bars = []
        self.labels = []
        self.data = None

        self.max_width = max_bar_width
        self.legend_width = legend_width
        self.value_format = value_format
        self.graph_interactive = interactive

        self.plot_area = graphics.Sprite(interactive = False)
        self.add_child(self.plot_area)

        self.bar_color, self.label_color = None, None

        self.connect("on-enter-frame", self.on_enter_frame)

        if self.graph_interactive:
            self.connect("on-mouse-over", self.on_mouse_over)
            self.connect("on-mouse-out", self.on_mouse_out)
            self.connect("on-click", self.on_click)

    def find_colors(self):
        bg_color = "#eee" #self.get_style().bg[gtk.StateType.NORMAL].to_string()
        self.bar_color = self.colors.contrast(bg_color, 30)

        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = "#aaa" #self.get_style().fg[gtk.StateType.NORMAL].to_string()
        self.label_color = self.colors.contrast(fg_color,  80)


    def on_mouse_over(self, scene, bar):
        if bar.key not in self.selected_keys:
            bar.fill = "#999" #self.get_style().base[gtk.StateType.PRELIGHT].to_string()

    def on_mouse_out(self, scene, bar):
        if bar.key not in self.selected_keys:
            bar.fill = self.bar_color

    def on_click(self, scene, event, clicked_bar):
        if not clicked_bar: return
        self.emit("bar-clicked", clicked_bar.key)

    def plot(self, keys, data):
        self.data = data

        bars = dict([(bar.key, bar.normalized) for bar in self.bars])

        max_val = float(max(data or [0]))

        new_bars, new_labels = [], []
        for key, value in zip(keys, data):
            if max_val:
                normalized = value / max_val
            else:
                normalized = 0
            bar = Bar(key, locale.format(self.value_format, value), normalized, self.label_color)
            bar.interactive = self.graph_interactive

            if key in bars:
                bar.normalized = bars[key]
                self.tweener.add_tween(bar, normalized=normalized)
            new_bars.append(bar)

            label = graphics.Label(stuff.escape_pango(key), size = 8, alignment = pango.Alignment.RIGHT)
            new_labels.append(label)


        self.plot_area.remove_child(*self.bars)
        self.remove_child(*self.labels)

        self.bars, self.labels = new_bars, new_labels
        self.add_child(*self.labels)
        self.plot_area.add_child(*self.bars)

        self.show()
        self.redraw()


    def on_enter_frame(self, scene, context):
        # adjust sizes and positions on redraw

        legend_width = self.legend_width
        if legend_width < 1: # allow fractions
            legend_width = int(self.width * legend_width)

        self.find_colors()

        self.plot_area.y = 0
        self.plot_area.height = self.height - self.plot_area.y
        self.plot_area.x = legend_width + 8
        self.plot_area.width = self.width - self.plot_area.x

        y = 0
        for i, (label, bar) in enumerate(zip(self.labels, self.bars)):
            bar_width = min(round((self.plot_area.height - y) / (len(self.bars) - i)), self.max_width)
            bar.y = y
            bar.height = bar_width
            bar.width = self.plot_area.width

            if bar.key in self.selected_keys:
                bar.fill = "#aaa" #self.get_style().bg[gtk.StateType.SELECTED].to_string()

                if bar.normalized == 0:
                    bar.label.color = "#666" #self.get_style().fg[gtk.StateType.SELECTED].to_string()
                    bar.label_background.fill = "#aaa" #self.get_style().bg[gtk.StateType.SELECTED].to_string()
                    bar.label_background.visible = True
                else:
                    bar.label_background.visible = False
                    if bar.label.x < round(bar.width * bar.normalized):
                        bar.label.color = "#666" #self.get_style().fg[gtk.StateType.SELECTED].to_string()
                    else:
                        bar.label.color = self.label_color

            if not bar.fill:
                bar.fill = self.bar_color

                bar.label.color = self.label_color
                bar.label_background.fill = None

            label.y = y + (bar_width - label.height) / 2 + self.plot_area.y

            label.width = legend_width
            if not label.color:
                label.color = self.label_color

            y += bar_width + 1




class HorizontalDayChart(graphics.Scene):
    """Pretty much a horizontal bar chart, except for values it expects tuple
    of start and end time, and the whole thing hangs in air"""
    def __init__(self, max_bar_width, legend_width):
        graphics.Scene.__init__(self)
        self.max_bar_width = max_bar_width
        self.legend_width = legend_width
        self.start_time, self.end_time = None, None
        self.connect("on-enter-frame", self.on_enter_frame)

    def plot_day(self, keys, data, start_time = None, end_time = None):
        self.keys, self.data = keys, data
        self.start_time, self.end_time = start_time, end_time
        self.show()
        self.redraw()

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        rowcount, keys = len(self.keys), self.keys

        start_hour = 0
        if self.start_time:
            start_hour = self.start_time
        end_hour = 24 * 60
        if self.end_time:
            end_hour = self.end_time


        # push graph to the right, so it doesn't overlap
        legend_width = self.legend_width or self.longest_label(keys)

        self.graph_x = legend_width
        self.graph_x += 8 #add another 8 pixes of padding

        self.graph_width = self.width - self.graph_x

        # TODO - should handle the layout business in graphics
        self.layout = context.create_layout()
        default_font = "Sans Serif" #pango.FontDescription(self.get_style().font_desc.to_string())
        default_font.set_size(8 * pango.SCALE)
        self.layout.set_font_description(default_font)


        #on the botttom leave some space for label
        self.layout.set_text("1234567890:")
        label_w, label_h = self.layout.get_pixel_size()

        self.graph_y, self.graph_height = 0, self.height - label_h - 4

        if not self.data:  #if we have nothing, let's go home
            return


        positions = {}
        y = 0
        bar_width = min(self.graph_height / float(len(self.keys)), self.max_bar_width)
        for i, key in enumerate(self.keys):
            positions[key] = (y + self.graph_y, round(bar_width - 1))

            y = y + round(bar_width)
            bar_width = min(self.max_bar_width,
                            (self.graph_height - y) / float(max(1, len(self.keys) - i - 1)))



        max_bar_size = self.graph_width - 15


        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = "#666" #self.get_style().fg[gtk.StateType.NORMAL].to_string()
        label_color = self.colors.contrast(fg_color,  80)

        self.layout.set_alignment(pango.Alignment.RIGHT)
        self.layout.set_ellipsize(pango.ELLIPSIZE_END)

        # bars and labels
        self.layout.set_width(legend_width * pango.SCALE)

        factor = max_bar_size / float(end_hour - start_hour)

        # determine bar color
        bg_color = "#eee" #self.get_style().bg[gtk.StateType.NORMAL].to_string()
        base_color = self.colors.contrast(bg_color,  30)

        for i, label in enumerate(keys):
            g.set_color(label_color)

            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, positions[label][0] + (positions[label][1] - label_h) / 2)
            context.show_layout(self.layout)

            if isinstance(self.data[i], list) == False:
                self.data[i] = [self.data[i]]

            for row in self.data[i]:
                bar_x = round((row[0]- start_hour) * factor)
                bar_size = round((row[1] - start_hour) * factor - bar_x)

                g.fill_area(round(self.graph_x + bar_x),
                              positions[label][0],
                              bar_size,
                              positions[label][1],
                              base_color)

        #white grid and scale values
        self.layout.set_width(-1)

        context.set_line_width(1)

        pace = ((end_hour - start_hour) / 3) / 60 * 60
        last_position = positions[keys[-1]]


        grid_color = "#aaa" # self.get_style().bg[gtk.StateType.NORMAL].to_string()

        for i in range(start_hour + 60, end_hour, pace):
            x = round((i - start_hour) * factor)

            minutes = i % (24 * 60)

            self.layout.set_markup(dt.time(minutes / 60, minutes % 60).strftime("%H<small><sup>%M</sup></small>"))
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(self.graph_x + x - label_w / 2,
                            last_position[0] + last_position[1] + 4)
            g.set_color(label_color)
            context.show_layout(self.layout)


            g.set_color(grid_color)
            g.move_to(round(self.graph_x + x) + 0.5, self.graph_y)
            g.line_to(round(self.graph_x + x) + 0.5,
                                 last_position[0] + last_position[1])


        context.stroke()

########NEW FILE########
__FILENAME__ = configuration
# -*- coding: utf-8 -*-

# Copyright (C) 2008, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

"""
gconf part of this code copied from Gimmie (c) Alex Gravely via Conduit (c) John Stowers, 2006
License: GPLv2
"""

import os
from hamster.client import Storage
from xdg.BaseDirectory import xdg_data_home
import logging
import datetime as dt

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import GConf as gconf

import logging
log = logging.getLogger("configuration")



class Controller(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent=None, ui_file=""):
        gobject.GObject.__init__(self)

        self.parent = parent

        if ui_file:
            self._gui = load_ui_file(ui_file)
            self.window = self.get_widget('window')
        else:
            self._gui = None
            self.window = gtk.Window()

        self.window.connect("delete-event", self.window_delete_event)
        if self._gui:
            self._gui.connect_signals(self)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)


    def window_delete_event(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            """
            for obj, handler in self.external_listeners:
                obj.disconnect(handler)
            """
            self.window.destroy()
            self.window = None
            self.emit("on-close")

    def show(self):
        self.window.show()


def load_ui_file(name):
    """loads interface from the glade file; sorts out the path business"""
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(runtime.data_dir, name))
    return ui



class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if '__instance' not in vars(cls):
            cls.__instance = object.__new__(cls, *args, **kwargs)
        return cls.__instance

class RuntimeStore(Singleton):
    """XXX - kill"""
    data_dir = ""
    home_data_dir = ""
    storage = None

    def __init__(self):
        try:
            from hamster import defs
            self.data_dir = os.path.join(defs.DATA_DIR, "hamster-time-tracker")
            self.version = defs.VERSION
        except:
            # if defs is not there, we are running from sources
            module_dir = os.path.dirname(os.path.realpath(__file__))
            self.data_dir = os.path.join(module_dir, '..', '..', '..', 'data')
            self.version = "uninstalled"

        self.data_dir = os.path.realpath(self.data_dir)
        self.storage = Storage()
        self.home_data_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster-time-tracker"))


runtime = RuntimeStore()


class OneWindow(object):
    def __init__(self, get_dialog_class):
        self.dialogs = {}
        self.get_dialog_class = get_dialog_class
        self.dialog_close_handlers = {}

    def on_close_window(self, dialog):
        for key, assoc_dialog in list(self.dialogs.iteritems()):
            if dialog == assoc_dialog:
                del self.dialogs[key]

        handler = self.dialog_close_handlers.pop(dialog)
        dialog.disconnect(handler)


    def show(self, parent = None, **kwargs):
        params = str(sorted(kwargs.items())) #this is not too safe but will work for most cases

        if params in self.dialogs:
            window = self.dialogs[params].window
            self.dialogs[params].show()
            window.present()
        else:
            if parent:
                dialog = self.get_dialog_class()(parent, **kwargs)

                if isinstance(parent, gtk.Widget):
                    dialog.window.set_transient_for(parent.get_toplevel())

                if hasattr(dialog, "connect"):
                    self.dialog_close_handlers[dialog] = dialog.connect("on-close", self.on_close_window)
            else:
                dialog = self.get_dialog_class()(**kwargs)

                # no parent means we close on window close
                dialog.window.connect("destroy",
                                      lambda window, params: gtk.main_quit(),
                                      params)

            self.dialogs[params] = dialog

class Dialogs(Singleton):
    """makes sure that we have single instance open for windows where it makes
       sense"""
    def __init__(self):
        def get_edit_class():
            from hamster.edit_activity import CustomFactController
            return CustomFactController
        self.edit = OneWindow(get_edit_class)

        def get_overview_class():
            from hamster.overview import Overview
            return Overview
        self.overview = OneWindow(get_overview_class)

        def get_about_class():
            from hamster.about import About
            return About
        self.about = OneWindow(get_about_class)

        def get_prefs_class():
            from hamster.preferences import PreferencesEditor
            return PreferencesEditor
        self.prefs = OneWindow(get_prefs_class)

dialogs = Dialogs()


class GConfStore(gobject.GObject, Singleton):
    """
    Settings implementation which stores settings in GConf
    Snatched from the conduit project (http://live.gnome.org/Conduit)
    """
    GCONF_DIR = "/apps/hamster-time-tracker/"
    VALID_KEY_TYPES = (bool, str, int, list, tuple)
    DEFAULTS = {
        'enable_timeout'              :   False,       # Should hamster stop tracking on idle
        'stop_on_shutdown'            :   False,       # Should hamster stop tracking on shutdown
        'notify_on_idle'              :   False,       # Remind also if no activity is set
        'notify_interval'             :   27,          # Remind of current activity every X minutes
        'day_start_minutes'           :   5 * 60 + 30, # At what time does the day start (5:30AM)
        'overview_window_box'         :   [],          # X, Y, W, H
        'overview_window_maximized'   :   False,       # Is overview window maximized
        'standalone_window_box'       :   [],          # X, Y, W, H
        'standalone_window_maximized' :   False,       # Is overview window maximized
        'activities_source'           :   "",          # Source of TODO items ("", "evo", "gtg")
        'last_report_folder'          :   "~",         # Path to directory where the last report was saved
    }

    __gsignals__ = {
        "conf-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
    }
    def __init__(self):
        gobject.GObject.__init__(self)
        self._client = gconf.Client.get_default()
        self._client.add_dir(self.GCONF_DIR[:-1], gconf.ClientPreloadType.PRELOAD_RECURSIVE)
        self._notifications = []

    def _fix_key(self, key):
        """
        Appends the GCONF_PREFIX to the key if needed

        @param key: The key to check
        @type key: C{string}
        @returns: The fixed key
        @rtype: C{string}
        """
        if not key.startswith(self.GCONF_DIR):
            return self.GCONF_DIR + key
        else:
            return key

    def _key_changed(self, client, cnxn_id, entry, data=None):
        """
        Callback when a gconf key changes
        """
        key = self._fix_key(entry.key)[len(self.GCONF_DIR):]
        value = self._get_value(entry.value, self.DEFAULTS[key])

        self.emit('conf-changed', key, value)


    def _get_value(self, value, default):
        """calls appropriate gconf function by the default value"""
        vtype = type(default)

        if vtype is bool:
            return value.get_bool()
        elif vtype is str:
            return value.get_string()
        elif vtype is int:
            return value.get_int()
        elif vtype in (list, tuple):
            l = []
            for i in value.get_list():
                l.append(i.get_string())
            return l

        return None

    def get(self, key, default=None):
        """
        Returns the value of the key or the default value if the key is
        not yet in gconf
        """

        #function arguments override defaults
        if default is None:
            default = self.DEFAULTS.get(key, None)
        vtype = type(default)

        #we now have a valid key and type
        if default is None:
            log.warn("Unknown key: %s, must specify default value" % key)
            return None

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return None

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if key not in self._notifications:
            self._client.notify_add(key, self._key_changed, None)
            self._notifications.append(key)

        value = self._client.get(key)
        if value is None:
            self.set(key, default)
            return default

        value = self._get_value(value, default)
        if value is not None:
            return value

        log.warn("Unknown gconf key: %s" % key)
        return None

    def set(self, key, value):
        """
        Sets the key value in gconf and connects adds a signal
        which is fired if the key changes
        """
        log.debug("Settings %s -> %s" % (key, value))
        if key in self.DEFAULTS:
            vtype = type(self.DEFAULTS[key])
        else:
            vtype = type(value)

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return False

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if vtype is bool:
            self._client.set_bool(key, value)
        elif vtype is str:
            self._client.set_string(key, value)
        elif vtype is int:
            self._client.set_int(key, value)
        elif vtype in (list, tuple):
            #Save every value as a string
            strvalues = [str(i) for i in value]
            #self._client.set_list(key, gconf.VALUE_STRING, strvalues)

        return True


conf = GConfStore()

########NEW FILE########
__FILENAME__ = desktop
# - coding: utf-8 -

# Copyright (C) 2007-2012 Toms Baugis <toms.baugis@gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import datetime as dt
from calendar import timegm
import logging
from gi.repository import GObject as gobject


from hamster import idle
from hamster.lib.configuration import conf
from hamster.lib import trophies
import dbus


class DesktopIntegrations(object):
    def __init__(self, storage):
        self.storage = storage # can't use client as then we get in a dbus loop
        self._last_notification = None

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()

        self.conf_enable_timeout = conf.get("enable_timeout")
        self.conf_notify_on_idle = conf.get("notify_on_idle")
        self.conf_notify_interval = conf.get("notify_interval")
        conf.connect('conf-changed', self.on_conf_changed)

        self.idle_listener = idle.DbusIdleListener()
        self.idle_listener.connect('idle-changed', self.on_idle_changed)

        gobject.timeout_add_seconds(60, self.check_hamster)


    def check_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""
        try:
            # can't use the client because then we end up in a dbus loop
            # as this is initiated in storage
            todays_facts = self.storage._Storage__get_todays_facts()
            self.check_user(todays_facts)
            trophies.check_ongoing(todays_facts)
        except Exception, e:
            logging.error("Error while refreshing: %s" % e)
        finally:  # we want to go on no matter what, so in case of any error we find out about it sooner
            return True


    def check_user(self, todays_facts):
        """check if we need to notify user perhaps"""
        interval = self.conf_notify_interval
        if interval <= 0 or interval >= 121:
            return

        now = dt.datetime.now()
        message = None

        last_activity = todays_facts[-1] if todays_facts else None

        # update duration of current task
        if last_activity and not last_activity['end_time']:
            delta = now - last_activity['start_time']
            duration = delta.seconds /  60

            if duration and duration % interval == 0:
                message = _(u"Working on %s") % last_activity['name']
                self.notify_user(message)

        elif self.conf_notify_on_idle:
            #if we have no last activity, let's just calculate duration from 00:00
            if (now.minute + now.hour * 60) % interval == 0:
                self.notify_user(_(u"No activity"))


    def notify_user(self, summary="", details=""):
        if not hasattr(self, "_notification_conn"):
            self._notification_conn = dbus.Interface(self.bus.get_object('org.freedesktop.Notifications',
                                                                         '/org/freedesktop/Notifications',
                                                                           follow_name_owner_changes=True),
                                                           dbus_interface='org.freedesktop.Notifications')
        conn = self._notification_conn

        notification = conn.Notify("Project Hamster",
                                   self._last_notification or 0,
                                   "hamster-time-tracker",
                                   summary,
                                   details,
                                   [],
                                   {"urgency": dbus.Byte(0), "transient" : True},
                                   -1)
        self._last_notification = notification


    def on_idle_changed(self, event, state):
        # state values: 0 = active, 1 = idle
        if state == 1 and self.conf_enable_timeout:
            idle_from = self.idle_listener.getIdleFrom()
            idle_from = timegm(idle_from.timetuple())
            self.storage.StopTracking(idle_from)


    def on_conf_changed(self, event, key, value):
        if hasattr(self, "conf_%s" % key):
            setattr(self, "conf_%s" % key, value)

########NEW FILE########
__FILENAME__ = graphics
# - coding: utf-8 -

# Copyright (c) 2008-2012 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.
# See http://github.com/tbaugis/hamster_experiments/blob/master/README.textile

from collections import defaultdict
import math
import datetime as dt


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo

import cairo
from gi.repository import GdkPixbuf

import re

try:
    import pytweener
except: # we can also live without tweener. Scene.animate will not work
    pytweener = None

import colorsys
from collections import deque

# lemme know if you know a better way how to get default font
_test_label = gtk.Label("Hello")
_font_desc = _test_label.get_style().font_desc.to_string()


class ColorUtils(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")
    hex_color_long = re.compile("#([a-fA-F0-9]{4})([a-fA-F0-9]{4})([a-fA-F0-9]{4})")

    # d3 colors
    category10 = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")
    category20 = ("#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
                  "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
                  "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
                  "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5")
    category20b = ("#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939",
                   "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39",
                   "#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b",
                   "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6")
    category20c = ("#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d",
                   "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476",
                   "#a1d99b", "#c7e9c0", "#756bb1", "#9e9ac8", "#bcbddc",
                   "#dadaeb", "#636363", "#969696", "#bdbdbd", "#d9d9d9")

    def parse(self, color):
        """parse string or a color tuple into color usable for cairo (all values
        in the normalized (0..1) range"""
        assert color is not None

        #parse color into rgb values
        if isinstance(color, basestring):
            match = self.hex_color_long.match(color)
            if match:
                color = [int(color, 16) / 65535.0 for color in match.groups()]
            else:
                match = self.hex_color_normal.match(color)
                if match:
                    color = [int(color, 16) / 255.0 for color in match.groups()]
                else:
                    match = self.hex_color_short.match(color)
                    color = [int(color + color, 16) / 255.0 for color in match.groups()]

        elif isinstance(color, gdk.Color):
            color = [color.red / 65535.0,
                     color.green / 65535.0,
                     color.blue / 65535.0]

        elif isinstance(color, (list, tuple)):
            # otherwise we assume we have color components in 0..255 range
            if color[0] > 1 or color[1] > 1 or color[2] > 1:
                color = [c / 255.0 for c in color]
        else:
            color = [color.red, color.green, color.blue]


        return color

    def rgb(self, color):
        """returns rgb[a] tuple of the color with values in range 0.255"""
        return [c * 255 for c in self.parse(color)]

    def gdk(self, color):
        """returns gdk.Color object of the given color"""
        c = self.parse(color)
        return gdk.Color.from_floats(c)

    def hex(self, color):
        c = self.parse(color)
        return "#" + "".join(["%02x" % (color * 255) for color in c])

    def is_light(self, color):
        """tells you if color is dark or light, so you can up or down the
        scale for improved contrast"""
        return colorsys.rgb_to_hls(*self.rgb(color))[1] > 150

    def darker(self, color, step):
        """returns color darker by step (where step is in range 0..255)"""
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])

    def contrast(self, color, step):
        """if color is dark, will return a lighter one, otherwise darker"""
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        if self.is_light(color):
            return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])
        else:
            return colorsys.hls_to_rgb(hls[0], hls[1] + step, hls[2])
        # returns color darker by step (where step is in range 0..255)

Colors = ColorUtils() # this is a static class, so an instance will do

def get_gdk_rectangle(x, y, w, h):
    rect = gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = x or 0, y or 0, w or 0, h or 0
    return rect


class Graphics(object):
    """If context is given upon contruction, will perform drawing
       operations on context instantly. Otherwise queues up the drawing
       instructions and performs them in passed-in order when _draw is called
       with context.

       Most of instructions are mapped to cairo functions by the same name.
       Where there are differences, documenation is provided.

       See http://cairographics.org/documentation/pycairo/2/reference/context.html
       for detailed description of the cairo drawing functions.
    """
    __slots__ = ('context', 'colors', 'extents', 'paths', '_last_matrix',
                 '__new_instructions', '__instruction_cache', 'cache_surface',
                 '_cache_layout')
    colors = Colors # pointer to the color utilities instance

    def __init__(self, context = None):
        self.context = context
        self.extents = None     # bounds of the object, only if interactive
        self.paths = None       # paths for mouse hit checks
        self._last_matrix = None
        self.__new_instructions = [] # instruction set until it is converted into path-based instructions
        self.__instruction_cache = []
        self.cache_surface = None
        self._cache_layout = None

    def clear(self):
        """clear all instructions"""
        self.__new_instructions = []
        self.__instruction_cache = []
        self.paths = []

    def stroke(self, color=None, alpha=1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke")

    def fill(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill")

    def mask(self, pattern):
        self._add_instruction("mask", pattern)

    def stroke_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke_preserve")

    def fill_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill_preserve")

    def new_path(self):
        self._add_instruction("new_path")

    def paint(self):
        self._add_instruction("paint")

    def set_font_face(self, face):
        self._add_instruction("set_font_face", face)

    def set_font_size(self, size):
        self._add_instruction("set_font_size", size)

    def set_source(self, image, x = 0, y = 0):
        self._add_instruction("set_source", image)

    def set_source_surface(self, surface, x = 0, y = 0):
        self._add_instruction("set_source_surface", surface, x, y)

    def set_source_pixbuf(self, pixbuf, x = 0, y = 0):
        self._add_instruction("set_source_pixbuf", pixbuf, x, y)

    def save_context(self):
        self._add_instruction("save")

    def restore_context(self):
        self._add_instruction("restore")

    def clip(self):
        self._add_instruction("clip")

    def rotate(self, radians):
        self._add_instruction("rotate", radians)

    def translate(self, x, y):
        self._add_instruction("translate", x, y)

    def scale(self, x_factor, y_factor):
        self._add_instruction("scale", x_factor, y_factor)

    def move_to(self, x, y):
        self._add_instruction("move_to", x, y)

    def line_to(self, x, y = None):
        if y is not None:
            self._add_instruction("line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("line_to", x2, y2)


    def rel_line_to(self, x, y = None):
        if x is not None and y is not None:
            self._add_instruction("rel_line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("rel_line_to", x2, y2)

    def curve_to(self, x, y, x2, y2, x3, y3):
        """draw a curve. (x2, y2) is the middle point of the curve"""
        self._add_instruction("curve_to", x, y, x2, y2, x3, y3)

    def close_path(self):
        self._add_instruction("close_path")

    def set_line_style(self, width = None, dash = None, dash_offset = 0):
        """change width and dash of a line"""
        if width is not None:
            self._add_instruction("set_line_width", width)

        if dash is not None:
            self._add_instruction("set_dash", dash, dash_offset)



    def _set_color(self, context, r, g, b, a):
        """the alpha has to changed based on the parent, so that happens at the
        time of drawing"""
        if a < 1:
            context.set_source_rgba(r, g, b, a)
        else:
            context.set_source_rgb(r, g, b)

    def set_color(self, color, alpha = 1):
        """set active color. You can use hex colors like "#aaa", or you can use
        normalized RGB tripplets (where every value is in range 0..1), or
        you can do the same thing in range 0..65535.
        also consider skipping this operation and specify the color on stroke and
        fill.
        """
        color = self.colors.parse(color) # parse whatever we have there into a normalized triplet
        if len(color) == 4 and alpha is None:
            alpha = color[3]
        r, g, b = color[:3]
        self._add_instruction("set_color", r, g, b, alpha)


    def arc(self, x, y, radius, start_angle, end_angle):
        """draw arc going counter-clockwise from start_angle to end_angle"""
        self._add_instruction("arc", x, y, radius, start_angle, end_angle)

    def circle(self, x, y, radius):
        """draw circle"""
        self._add_instruction("arc", x, y, radius, 0, math.pi * 2)

    def ellipse(self, x, y, width, height, edges = None):
        """draw 'perfect' ellipse, opposed to squashed circle. works also for
           equilateral polygons"""
        # the automatic edge case is somewhat arbitrary
        steps = edges or max((32, width, height)) / 2

        angle = 0
        step = math.pi * 2 / steps
        points = []
        while angle < math.pi * 2:
            points.append((width / 2.0 * math.cos(angle),
                           height / 2.0 * math.sin(angle)))
            angle += step

        min_x = min((point[0] for point in points))
        min_y = min((point[1] for point in points))

        self.move_to(points[0][0] - min_x + x, points[0][1] - min_y + y)
        for p_x, p_y in points:
            self.line_to(p_x - min_x + x, p_y - min_y + y)
        self.line_to(points[0][0] - min_x + x, points[0][1] - min_y + y)

    def arc_negative(self, x, y, radius, start_angle, end_angle):
        """draw arc going clockwise from start_angle to end_angle"""
        self._add_instruction("arc_negative", x, y, radius, start_angle, end_angle)

    def rectangle(self, x, y, width, height, corner_radius = 0):
        """draw a rectangle. if corner_radius is specified, will draw
        rounded corners. corner_radius can be either a number or a tuple of
        four items to specify individually each corner, starting from top-left
        and going clockwise"""
        if corner_radius <= 0:
            self._add_instruction("rectangle", x, y, width, height)
            return

        # convert into 4 border and  make sure that w + h are larger than 2 * corner_radius
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4
        corner_radius = [min(r, min(width, height) / 2) for r in corner_radius]

        x2, y2 = x + width, y + height
        self._rounded_rectangle(x, y, x2, y2, corner_radius)

    def _rounded_rectangle(self, x, y, x2, y2, corner_radius):
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4

        self._add_instruction("move_to", x + corner_radius[0], y)
        self._add_instruction("line_to", x2 - corner_radius[1], y)
        self._add_instruction("curve_to", x2 - corner_radius[1] / 2, y, x2, y + corner_radius[1] / 2, x2, y + corner_radius[1])
        self._add_instruction("line_to", x2, y2 - corner_radius[2])
        self._add_instruction("curve_to", x2, y2 - corner_radius[2] / 2, x2 - corner_radius[2] / 2, y2, x2 - corner_radius[2], y2)
        self._add_instruction("line_to", x + corner_radius[3], y2)
        self._add_instruction("curve_to", x + corner_radius[3] / 2, y2, x, y2 - corner_radius[3] / 2, x, y2 - corner_radius[3])
        self._add_instruction("line_to", x, y + corner_radius[0])
        self._add_instruction("curve_to", x, y + corner_radius[0] / 2, x + corner_radius[0] / 2, y, x + corner_radius[0], y)


    def fill_area(self, x, y, width, height, color, opacity = 1):
        """fill rectangular area with specified color"""
        self.save_context()
        self.rectangle(x, y, width, height)
        self._add_instruction("clip")
        self.rectangle(x, y, width, height)
        self.fill(color, opacity)
        self.restore_context()

    def fill_stroke(self, fill = None, stroke = None, opacity = 1, line_width = None):
        """fill and stroke the drawn area in one go"""
        if line_width: self.set_line_style(line_width)

        if fill and stroke:
            self.fill_preserve(fill, opacity)
        elif fill:
            self.fill(fill, opacity)

        if stroke:
            self.stroke(stroke)

    def create_layout(self, size = None):
        """utility function to create layout with the default font. Size and
        alignment parameters are shortcuts to according functions of the
        pango.Layout"""
        if not self.context:
            # TODO - this is rather sloppy as far as exception goes
            #        should explain better
            raise "Can not create layout without existing context!"

        layout = pangocairo.create_layout(self.context)
        font_desc = pango.FontDescription(_font_desc)
        if size: font_desc.set_absolute_size(size * pango.SCALE)

        layout.set_font_description(font_desc)
        return layout

    def show_label(self, text, size = None, color = None, font_desc = None):
        """display text. unless font_desc is provided, will use system's default font"""
        font_desc = pango.FontDescription(font_desc or _font_desc)
        if color: self.set_color(color)
        if size: font_desc.set_absolute_size(size * pango.SCALE)
        self.show_layout(text, font_desc)

    def show_text(self, text):
        self._add_instruction("show_text", text)

    def text_path(self, text):
        """this function is most likely to change"""
        self._add_instruction("text_path", text)

    def _show_layout(self, context, layout, text, font_desc, alignment, width, wrap,
                     ellipsize, single_paragraph_mode):
        layout.set_font_description(font_desc)
        layout.set_markup(text)
        layout.set_width(int(width or -1))
        layout.set_single_paragraph_mode(single_paragraph_mode)
        if alignment is not None:
            layout.set_alignment(alignment)

        if width > 0:
            if wrap is not None:
                layout.set_wrap(wrap)
            else:
                layout.set_ellipsize(ellipsize or pango.EllipsizeMode.END)

        pangocairo.show_layout(context, layout)


    def show_layout(self, text, font_desc, alignment = pango.Alignment.LEFT,
                    width = -1, wrap = None, ellipsize = None,
                    single_paragraph_mode = False):
        """display text. font_desc is string of pango font description
           often handier than calling this function directly, is to create
           a class:Label object
        """
        layout = self._cache_layout = self._cache_layout or pangocairo.create_layout(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)))
        self._add_instruction("show_layout", layout, text, font_desc,
                              alignment, width, wrap, ellipsize, single_paragraph_mode)


    def _add_instruction(self, function, *params):
        if self.context:
            if function == "set_color":
                self._set_color(self.context, *params)
            elif function == "show_layout":
                self._show_layout(self.context, *params)
            else:
                getattr(self.context, function)(*params)
        else:
            self.paths = None
            self.__new_instructions.append((function, params))


    def _draw(self, context, opacity):
        """draw accumulated instructions in context"""

        # if we have been moved around, we should update bounds
        fresh_draw = len(self.__new_instructions or []) > 0
        if fresh_draw: #new stuff!
            self.paths = []
            self.__instruction_cache = self.__new_instructions
            self.__new_instructions = []
        else:
            if not self.__instruction_cache:
                return

        for instruction, args in self.__instruction_cache:
            if fresh_draw:
                if instruction in ("new_path", "stroke", "fill", "clip"):
                    self.paths.append((instruction, "path", context.copy_path()))

                elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                    self.paths.append((instruction, "transform", args))

            if instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            elif opacity < 1 and instruction == "paint":
                context.paint_with_alpha(opacity)
            else:
                getattr(context, instruction)(*args)



    def _draw_as_bitmap(self, context, opacity):
        """
            instead of caching paths, this function caches the whole drawn thing
            use cache_as_bitmap on sprite to enable this mode
        """
        matrix = context.get_matrix()
        matrix_changed = matrix != self._last_matrix
        new_instructions = self.__new_instructions is not None and len(self.__new_instructions) > 0

        if not new_instructions and not matrix_changed:
            context.save()
            context.identity_matrix()
            context.translate(self.extents.x, self.extents.y)
            context.set_source_surface(self.cache_surface)
            if opacity < 1:
                context.paint_with_alpha(opacity)
            else:
                context.paint()
            context.restore()
            return


        if new_instructions:
            self.__instruction_cache = list(self.__new_instructions)
            self.__new_instructions = deque()

        self.paths = []
        self.extents = None

        if not self.__instruction_cache:
            # no instructions - nothing to do
            return

        # instructions that end path
        path_end_instructions = ("new_path", "clip", "stroke", "fill", "stroke_preserve", "fill_preserve")

        # measure the path extents so we know the size of cache surface
        # also to save some time use the context to paint for the first time
        extents = gdk.Rectangle()
        for instruction, args in self.__instruction_cache:
            if instruction in path_end_instructions:
                self.paths.append((instruction, "path", context.copy_path()))
                exts = context.path_extents()
                exts = get_gdk_rectangle(int(exts[0]), int(exts[1]),
                                         int(exts[2]-exts[0]), int(exts[3]-exts[1]))
                if extents.width and extents.height:
                    extents = gdk.rectangle_union(extents, exts)
                else:
                    extents = exts
            elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                self.paths.append((instruction, "transform", args))


            if instruction in ("set_source_pixbuf", "set_source_surface"):
                # draw a rectangle around the pathless instructions so that the extents are correct
                pixbuf = args[0]
                x = args[1] if len(args) > 1 else 0
                y = args[2] if len(args) > 2 else 0
                context.rectangle(x, y, pixbuf.get_width(), pixbuf.get_height())
                context.clip()

            if instruction == "paint" and opacity < 1:
                context.paint_with_alpha(opacity)
            elif instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            else:
                getattr(context, instruction)(*args)


        # avoid re-caching if we have just moved
        just_transforms = new_instructions == False and \
                          matrix and self._last_matrix \
                          and all([matrix[i] == self._last_matrix[i] for i in range(4)])

        # TODO - this does not look awfully safe
        extents.x += matrix[4] - 5
        extents.y += matrix[5] - 5
        self.extents = extents

        if not just_transforms:
            # now draw the instructions on the caching surface
            w = int(extents.width) + 10
            h = int(extents.height) + 10
            self.cache_surface = context.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
            ctx = cairo.Context(self.cache_surface)
            ctx.translate(-extents.x, -extents.y)

            ctx.transform(matrix)
            for instruction, args in self.__instruction_cache:
                if instruction == "set_color":
                    self._set_color(ctx, args[0], args[1], args[2], args[3])
                elif instruction == "show_layout":
                    self._show_layout(ctx, *args)
                else:
                    getattr(ctx, instruction)(*args)

        self._last_matrix = matrix


class Parent(object):
    """shared functions across scene and sprite"""

    def find(self, id):
        """breadth-first sprite search by ID"""
        for sprite in self.sprites:
            if sprite.id == id:
                return sprite

        for sprite in self.sprites:
            found = sprite.find(id)
            if found:
                return found

    def traverse(self, attr_name = None, attr_value = None):
        """traverse the whole sprite tree and return child sprites which have the
        attribute and it's set to the specified value.
        If falue is None, will return all sprites that have the attribute
        """
        for sprite in self.sprites:
            if (attr_name is None) or \
               (attr_value is None and hasattr(sprite, attr_name)) or \
               (attr_value is not None and getattr(sprite, attr_name, None) == attr_value):
                yield sprite

            for child in sprite.traverse(attr_name, attr_value):
                yield child

    def log(self, *lines):
        """will print out the lines in console if debug is enabled for the
           specific sprite"""
        if getattr(self, "debug", False):
            print dt.datetime.now().time(),
            for line in lines:
                print line,
            print

    def _add(self, sprite, index = None):
        """add one sprite at a time. used by add_child. split them up so that
        it would be possible specify the index externally"""
        if sprite == self:
            raise Exception("trying to add sprite to itself")

        if sprite.parent:
            sprite.x, sprite.y = self.from_scene_coords(*sprite.to_scene_coords())
            sprite.parent.remove_child(sprite)

        if index is not None:
            self.sprites.insert(index, sprite)
        else:
            self.sprites.append(sprite)
        sprite.parent = self


    def _sort(self):
        """sort sprites by z_order"""
        self.__dict__['_z_ordered_sprites'] = sorted(self.sprites, key=lambda sprite:sprite.z_order)

    def add_child(self, *sprites):
        """Add child sprite. Child will be nested within parent"""
        for sprite in sprites:
            self._add(sprite)
        self._sort()
        self.redraw()

    def remove_child(self, *sprites):
        """Remove one or several :class:`Sprite` sprites from scene """

        # first drop focus
        scene = self.get_scene()

        if scene:
            child_sprites = list(self.all_child_sprites())
            if scene._focus_sprite in child_sprites:
                scene._focus_sprite = None


        for sprite in sprites:
            if sprite in self.sprites:
                self.sprites.remove(sprite)
                sprite._scene = None
                sprite.parent = None
            self.disconnect_child(sprite)
        self._sort()
        self.redraw()


    def clear(self):
        """Remove all child sprites"""
        self.remove_child(*self.sprites)


    def destroy(self):
        """recursively removes all sprite children so that it is freed from
        any references and can be garbage collected"""
        for sprite in self.sprites:
            sprite.destroy()
        self.clear()


    def all_child_sprites(self):
        """returns all child and grandchild sprites in a flat list"""
        for sprite in self.sprites:
            for child_sprite in sprite.all_child_sprites():
                yield child_sprite
            yield sprite


    def get_mouse_sprites(self):
        """returns list of child sprites that the mouse can interact with.
        by default returns all visible sprites, but override
        to define your own rules"""
        return (sprite for sprite in self._z_ordered_sprites if sprite.visible)


    def connect_child(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def connect_child_after(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect_after(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def disconnect_child(self, sprite, *handlers):
        """disconnects from child event. if handler is not specified, will
        disconnect from all the child sprite events"""
        handlers = handlers or self._child_handlers.get(sprite, [])
        for handler in list(handlers):
            if sprite.handler_is_connected(handler):
                sprite.disconnect(handler)
            if handler in self._child_handlers.get(sprite, []):
                self._child_handlers[sprite].remove(handler)

        if not self._child_handlers[sprite]:
            del self._child_handlers[sprite]

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, getattr(self, "id", None) or str(id(self)))


class Sprite(Parent, gobject.GObject):
    """The Sprite class is a basic display list building block: a display list
       node that can display graphics and can also contain children.
       Once you have created the sprite, use Scene's add_child to add it to
       scene
    """

    __gsignals__ = {
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-focus": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-blur": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-render": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    transformation_attrs = set(('x', 'y', 'rotation', 'scale_x', 'scale_y', 'pivot_x', 'pivot_y'))

    visibility_attrs = set(('opacity', 'visible', 'z_order'))

    cache_attrs = set(('_stroke_context', '_matrix', '_prev_parent_matrix', '_scene'))

    graphics_unrelated_attrs = set(('drag_x', 'drag_y', 'sprites', 'mouse_cursor', '_sprite_dirty', 'id'))

    #: mouse-over cursor of the sprite. Can be either a gdk cursor
    #: constants, or a pixbuf or a pixmap. If set to False, will be using
    #: scene's cursor. in order to have the cursor displayed, the sprite has
    #: to be interactive
    mouse_cursor = None

    #: whether the widget can gain focus
    can_focus = None

    def __init__(self, x = 0, y = 0, opacity = 1, visible = True, rotation = 0,
                 pivot_x = 0, pivot_y = 0, scale_x = 1, scale_y = 1,
                 interactive = False, draggable = False, z_order = 0,
                 mouse_cursor = None, cache_as_bitmap = False,
                 snap_to_pixel = True, debug = False, id = None,
                 can_focus = False):
        gobject.GObject.__init__(self)

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

        self._scene = None

        self.debug = debug

        self.id = id

        #: list of children sprites. Use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

        #: instance of :ref:`graphics` for this sprite
        self.graphics = Graphics()

        #: boolean denoting whether the sprite responds to mouse events
        self.interactive = interactive

        #: boolean marking if sprite can be automatically dragged
        self.draggable = draggable

        #: relative x coordinate of the sprites' rotation point
        self.pivot_x = pivot_x

        #: relative y coordinates of the sprites' rotation point
        self.pivot_y = pivot_y

        #: sprite opacity
        self.opacity = opacity

        #: boolean visibility flag
        self.visible = visible

        #: pointer to parent :class:`Sprite` or :class:`Scene`
        self.parent = None

        #: sprite coordinates
        self.x, self.y = x, y

        #: rotation of the sprite in radians (use :func:`math.degrees` to convert to degrees if necessary)
        self.rotation = rotation

        #: scale X
        self.scale_x = scale_x

        #: scale Y
        self.scale_y = scale_y

        #: drawing order between siblings. The one with the highest z_order will be on top.
        self.z_order = z_order

        #: x position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_x = 0

        #: y position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_y = 0

        #: Whether the sprite should be cached as a bitmap. Default: true
        #: Generally good when you have many static sprites
        self.cache_as_bitmap = cache_as_bitmap

        #: Should the sprite coordinates always rounded to full pixel. Default: true
        #: Mostly this is good for performance but in some cases that can lead
        #: to rounding errors in positioning.
        self.snap_to_pixel = snap_to_pixel

        #: focus state
        self.focused = False


        if mouse_cursor is not None:
            self.mouse_cursor = mouse_cursor

        if can_focus is not None:
            self.can_focus = can_focus



        self.__dict__["_sprite_dirty"] = True # flag that indicates that the graphics object of the sprite should be rendered

        self._matrix = None
        self._prev_parent_matrix = None

        self._stroke_context = None

        self.connect("on-click", self.__on_click)



    def __setattr__(self, name, val):
        if isinstance(getattr(type(self), name, None), property) and \
           getattr(type(self), name).fset is not None:
            getattr(type(self), name).fset(self, val)
            return

        prev = self.__dict__.get(name, "hamster_graphics_no_value_really")
        if type(prev) == type(val) and prev == val:
            return
        self.__dict__[name] = val

        # prev parent matrix walks downwards
        if name == '_prev_parent_matrix' and self.visible:
            # downwards recursive invalidation of parent matrix
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        if name in self.cache_attrs or name in self.graphics_unrelated_attrs:
            return

        """all the other changes influence cache vars"""

        if name == 'visible' and self.visible == False:
            # when transforms happen while sprite is invisible
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        # on moves invalidate our matrix, child extent cache (as that depends on our transforms)
        # as well as our parent's child extents as we moved
        # then go into children and invalidate the parent matrix down the tree
        if name in self.transformation_attrs:
            self._matrix = None
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None
        elif name not in self.visibility_attrs:
            # if attribute is not in transformation nor visibility, we conclude
            # that it must be causing the sprite needs re-rendering
            self.__dict__["_sprite_dirty"] = True

        # on parent change invalidate the matrix
        if name == 'parent':
            self._prev_parent_matrix = None
            return

        if name == 'opacity' and getattr(self, "cache_as_bitmap", None) and hasattr(self, "graphics"):
            # invalidating cache for the bitmap version as that paints opacity in the image
            self.graphics._last_matrix = None

        if name == 'z_order' and getattr(self, "parent", None):
            self.parent._sort()


        self.redraw()


    def _get_mouse_cursor(self):
        """Determine mouse cursor.
        By default look for self.mouse_cursor is defined and take that.
        Otherwise use gdk.CursorType.FLEUR for draggable sprites and gdk.CursorType.HAND2 for
        interactive sprites. Defaults to scenes cursor.
        """
        if self.mouse_cursor is not None:
            return self.mouse_cursor
        elif self.interactive and self.draggable:
            return gdk.CursorType.FLEUR
        elif self.interactive:
            return gdk.CursorType.HAND2

    def bring_to_front(self):
        """adjusts sprite's z-order so that the sprite is on top of it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[-1].z_order + 1

    def send_to_back(self):
        """adjusts sprite's z-order so that the sprite is behind it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[0].z_order - 1

    def has_focus(self):
        """True if the sprite has the global input focus, False otherwise."""
        scene = self.get_scene()
        return scene and scene._focus_sprite == self

    def grab_focus(self):
        """grab window's focus. Keyboard and scroll events will be forwarded
        to the sprite who has the focus. Check the 'focused' property of sprite
        in the on-render event to decide how to render it (say, add an outline
        when focused=true)"""
        scene = self.get_scene()
        if scene and scene._focus_sprite != self:
            scene._focus_sprite = self

    def blur(self):
        """removes focus from the current element if it has it"""
        scene = self.get_scene()
        if scene and scene._focus_sprite == self:
            scene._focus_sprite = None

    def __on_click(self, sprite, event):
        if self.interactive and self.can_focus:
            self.grab_focus()

    def get_parents(self):
        """returns all the parent sprites up until scene"""
        res = []
        parent = self.parent
        while parent and isinstance(parent, Scene) == False:
            res.insert(0, parent)
            parent = parent.parent

        return res


    def get_extents(self):
        """measure the extents of the sprite's graphics."""
        if self._sprite_dirty:
            # redrawing merely because we need fresh extents of the sprite
            context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
            context.transform(self.get_matrix())
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False
            self.graphics._draw(context, 1)


        if not self.graphics.paths:
            self.graphics._draw(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)), 1)

        if not self.graphics.paths:
            return None

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))

        # bit of a hack around the problem - looking for clip instructions in parent
        # so extents would not get out of it
        clip_extents = None
        for parent in self.get_parents():
            context.transform(parent.get_local_matrix())
            if parent.graphics.paths:
                clip_regions = []
                for instruction, type, path in parent.graphics.paths:
                    if instruction == "clip":
                        context.append_path(path)
                        context.save()
                        context.identity_matrix()

                        clip_regions.append(context.fill_extents())
                        context.restore()
                        context.new_path()
                    elif instruction == "restore" and clip_regions:
                        clip_regions.pop()

                for ext in clip_regions:
                    ext = get_gdk_rectangle(int(ext[0]), int(ext[1]), int(ext[2] - ext[0]), int(ext[3] - ext[1]))
                    intersect, clip_extents = gdk.rectangle_intersect((clip_extents or ext), ext)

        context.transform(self.get_local_matrix())

        for instruction, type, path in self.graphics.paths:
            if type == "path":
                context.append_path(path)
            else:
                getattr(context, instruction)(*path)

        context.identity_matrix()


        ext = context.path_extents()
        ext = get_gdk_rectangle(int(ext[0]), int(ext[1]),
                                int(ext[2] - ext[0]), int(ext[3] - ext[1]))
        if clip_extents:
            intersect, ext = gdk.rectangle_intersect(clip_extents, ext)

        if not ext.width and not ext.height:
            ext = None

        self.__dict__['_stroke_context'] = context

        return ext


    def check_hit(self, x, y):
        """check if the given coordinates are inside the sprite's fill or stroke path"""
        extents = self.get_extents()

        if not extents:
            return False

        if extents.x <= x <= extents.x + extents.width and extents.y <= y <= extents.y + extents.height:
            return self._stroke_context is None or self._stroke_context.in_fill(x, y)
        else:
            return False

    def get_scene(self):
        """returns class:`Scene` the sprite belongs to"""
        if self._scene is None:
            parent = getattr(self, "parent", None)
            if parent:
                self._scene = parent.get_scene()
        return self._scene

    def redraw(self):
        """queue redraw of the sprite. this function is called automatically
           whenever a sprite attribute changes. sprite changes that happen
           during scene redraw are ignored in order to avoid echoes.
           Call scene.redraw() explicitly if you need to redraw in these cases.
        """
        scene = self.get_scene()
        if scene:
            scene.redraw()

    def animate(self, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
        """Request parent Scene to Interpolate attributes using the internal tweener.
           Specify sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Example::
             # tween some_sprite to coordinates (50,100) using default duration and easing
             self.animate(x = 50, y = 100)
        """
        scene = self.get_scene()
        if scene:
            return scene.animate(self, duration, easing, on_complete,
                                 on_update, round, **kwargs)
        else:
            for key, val in kwargs.items():
                setattr(self, key, val)
            return None

    def stop_animation(self):
        """stop animation without firing on_complete"""
        scene = self.get_scene()
        if scene:
            scene.stop_animation(self)

    def get_local_matrix(self):
        if self._matrix is None:
            matrix, x, y, pivot_x, pivot_y = cairo.Matrix(), self.x, self.y, self.pivot_x, self.pivot_y

            if self.snap_to_pixel:
                matrix.translate(int(x) + int(pivot_x), int(y) + int(pivot_y))
            else:
                matrix.translate(x + pivot_x, self.y + pivot_y)

            if self.rotation:
                matrix.rotate(self.rotation)


            if self.snap_to_pixel:
                matrix.translate(int(-pivot_x), int(-pivot_y))
            else:
                matrix.translate(-pivot_x, -pivot_y)


            if self.scale_x != 1 or self.scale_y != 1:
                matrix.scale(self.scale_x, self.scale_y)

            self._matrix = matrix

        return cairo.Matrix() * self._matrix


    def get_matrix(self):
        """return sprite's current transformation matrix"""
        if self.parent:
            return self.get_local_matrix() * (self._prev_parent_matrix or self.parent.get_matrix())
        else:
            return self.get_local_matrix()


    def from_scene_coords(self, x=0, y=0):
        """Converts x, y given in the scene coordinates to sprite's local ones
        coordinates"""
        matrix = self.get_matrix()
        matrix.invert()
        return matrix.transform_point(x, y)

    def to_scene_coords(self, x=0, y=0):
        """Converts x, y from sprite's local coordinates to scene coordinates"""
        return self.get_matrix().transform_point(x, y)

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.visible is False:
            return

        if (self._sprite_dirty): # send signal to redo the drawing when sprite is dirty
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False


        no_matrix = parent_matrix is None
        parent_matrix = parent_matrix or cairo.Matrix()

        # cache parent matrix
        self._prev_parent_matrix = parent_matrix

        matrix = self.get_local_matrix()

        context.save()
        context.transform(matrix)


        if self.cache_as_bitmap:
            self.graphics._draw_as_bitmap(context, self.opacity * opacity)
        else:
            self.graphics._draw(context, self.opacity * opacity)

        context.new_path() #forget about us

        if self.debug:
            exts = self.get_extents()
            if exts:
                debug_colors = ["#c17d11", "#73d216", "#3465a4",
                                "#75507b", "#cc0000", "#edd400", "#f57900"]
                depth = len(self.get_parents())
                color = debug_colors[depth % len(debug_colors)]
                context.save()
                context.identity_matrix()

                scene = self.get_scene()
                if scene:
                    # go figure - seems like the context we are given starts
                    # in window coords when calling identity matrix
                    scene_alloc = self.get_scene().get_allocation()
                    context.translate(scene_alloc.x, scene_alloc.y)


                context.rectangle(exts.x, exts.y, exts.width, exts.height)
                context.set_source_rgb(*Colors.parse(color))
                context.stroke()
                context.restore()

        for sprite in self._z_ordered_sprites:
            sprite._draw(context, self.opacity * opacity, matrix * parent_matrix)


        context.restore()

        # having parent and not being given parent matrix means that somebody
        # is calling draw directly - avoid caching matrix for such a case
        # because when we will get called properly it won't be respecting
        # the parent's transformations otherwise
        if isinstance(self.parent, Sprite) and no_matrix:
            self._prev_parent_matrix = None

    # using _do functions so that subclassees can override these
    def _do_mouse_down(self, event): self.emit("on-mouse-down", event)
    def _do_double_click(self, event): self.emit("on-double-click", event)
    def _do_triple_click(self, event): self.emit("on-triple-click", event)
    def _do_mouse_up(self, event): self.emit("on-mouse-up", event)
    def _do_click(self, event): self.emit("on-click", event)
    def _do_mouse_over(self): self.emit("on-mouse-over")
    def _do_mouse_move(self, event): self.emit("on-mouse-move", event)
    def _do_mouse_out(self): self.emit("on-mouse-out")
    def _do_focus(self): self.emit("on-focus")
    def _do_blur(self): self.emit("on-blur")
    def _do_key_press(self, event):
        self.emit("on-key-press", event)
        return False

    def _do_key_release(self, event):
        self.emit("on-key-release", event)
        return False


class BitmapSprite(Sprite):
    """Caches given image data in a surface similar to targets, which ensures
       that drawing it will be quick and low on CPU.
       Image data can be either :class:`cairo.ImageSurface` or :class:`GdkPixbuf.Pixbuf`
    """
    def __init__(self, image_data = None, cache_mode = None, **kwargs):
        Sprite.__init__(self, **kwargs)

        self.width, self.height = 0, 0
        self.cache_mode = cache_mode or cairo.CONTENT_COLOR_ALPHA
        #: image data
        self.image_data = image_data

        self._surface = None

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        if not self._surface:
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.new_path()

    def update_surface_cache(self):
        """for efficiency the image data is cached on a surface similar to the
        target one. so if you do custom drawing after setting the image data,
        it won't be reflected as the sprite has no idea about what is going on
        there. call this function to trigger cache refresh."""
        self._surface = None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Sprite.__setattr__(self, name, val)
        if name == 'image_data':
            self._surface = None
            if self.image_data:
                self.__dict__['width'] = self.image_data.get_width()
                self.__dict__['height'] = self.image_data.get_height()

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.image_data is None or self.width is None or self.height is None:
            return

        if not self._surface:
            # caching image on surface similar to the target
            surface = context.get_target().create_similar(self.cache_mode,
                                                          self.width,
                                                          self.height)

            local_context = cairo.Context(surface)
            if isinstance(self.image_data, GdkPixbuf.Pixbuf):
                gdk.cairo_set_source_pixbuf(local_context, self.image_data, 0, 0)
            else:
                local_context.set_source_surface(self.image_data)
            local_context.paint()

            # add instructions with the resulting surface
            self.graphics.clear()
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.clip()
            self.graphics.set_source_surface(surface)
            self.graphics.paint()
            self.__dict__['_surface'] = surface


        Sprite._draw(self,  context, opacity, parent_matrix)


class Image(BitmapSprite):
    """Displays image by path. Currently supports only PNG images."""
    def __init__(self, path, **kwargs):
        BitmapSprite.__init__(self, **kwargs)

        #: path to the image
        self.path = path

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name == 'path': # load when the value is set to avoid penalty on render
            self.image_data = cairo.ImageSurface.create_from_png(self.path)



class Icon(BitmapSprite):
    """Displays icon by name and size in the theme"""
    def __init__(self, name, size=24, **kwargs):
        BitmapSprite.__init__(self, **kwargs)
        self.theme = gtk.IconTheme.get_default()

        #: icon name from theme
        self.name = name

        #: icon size in pixels
        self.size = size

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name in ('name', 'size'): # no other reason to discard cache than just on path change
            if self.__dict__.get('name') and self.__dict__.get('size'):
                self.image_data = self.theme.load_icon(self.name, self.size, 0)
            else:
                self.image_data = None


class Label(Sprite):
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    cache_attrs = Sprite.cache_attrs | set(("_letter_sizes", "__surface", "_ascent", "_bounds_width", "_measures"))

    def __init__(self, text = "", size = None, color = None,
                 alignment = pango.Alignment.LEFT, single_paragraph = False,
                 max_width = None, wrap = None, ellipsize = None, markup = "",
                 font_desc = None, **kwargs):
        Sprite.__init__(self, **kwargs)
        self.width, self.height = None, None


        self._test_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 0, 0))
        self._test_layout = pangocairo.create_layout(self._test_context)


        #: absolute font size in pixels. this will execute set_absolute_size
        #: instead of set_size, which is fractional
        self.size = size

        #: pango.FontDescription, defaults to system font
        self.font_desc = pango.FontDescription(font_desc or _font_desc)

        #: color of label either as hex string or an (r,g,b) tuple
        self.color = color

        self._bounds_width = None

        #: wrapping method. Can be set to pango. [WRAP_WORD, WRAP_CHAR,
        #: WRAP_WORD_CHAR]
        self.wrap = wrap


        #: Ellipsize mode. Can be set to pango.[EllipsizeMode.NONE,
        #: EllipsizeMode.START, EllipsizeMode.MIDDLE, EllipsizeMode.END]
        self.ellipsize = ellipsize

        #: alignment. one of pango.[Alignment.LEFT, Alignment.RIGHT, Alignment.CENTER]
        self.alignment = alignment

        #: If setting is True, do not treat newlines and similar characters as
        #: paragraph separators; instead, keep all text in a single paragraph,
        #: and display a glyph for paragraph separator characters. Used when you
        #: want to allow editing of newlines on a single text line.
        #: Defaults to False
        self.single_paragraph = single_paragraph


        #: maximum  width of the label in pixels. if specified, the label
        #: will be wrapped or ellipsized depending on the wrap and ellpisize settings
        self.max_width = max_width

        self.__surface = None

        #: label text. upon setting will replace markup
        self.text = text

        #: label contents marked up using pango markup. upon setting will replace text
        self.markup = markup

        self._measures = {}

        self.connect("on-render", self.on_render)

        self.graphics_unrelated_attrs = self.graphics_unrelated_attrs | set(("__surface", "_bounds_width", "_measures"))

    def __setattr__(self, name, val):
        if name == "font_desc":
            if isinstance(val, basestring):
                val = pango.FontDescription(val)
            elif isinstance(val, pango.FontDescription):
                val = val.copy()

        if self.__dict__.get(name, "hamster_graphics_no_value_really") != val:
            if name == "width" and val and self.__dict__.get('_bounds_width') and val * pango.SCALE == self.__dict__['_bounds_width']:
                return

            Sprite.__setattr__(self, name, val)


            if name == "width":
                # setting width means consumer wants to contrain the label
                if val is None or val == -1:
                    self.__dict__['_bounds_width'] = None
                else:
                    self.__dict__['_bounds_width'] = val * pango.SCALE


            if name in ("width", "text", "markup", "size", "font_desc", "wrap", "ellipsize", "max_width"):
                self._measures = {}
                # avoid chicken and egg
                if hasattr(self, "size") and (hasattr(self, "text") or hasattr(self, "markup")):
                    if self.size:
                        self.font_desc.set_absolute_size(self.size * pango.SCALE)
                    markup = getattr(self, "markup", "")
                    self.__dict__['width'], self.__dict__['height'] = self.measure(markup or getattr(self, "text", ""), escape = len(markup) == 0)



            if name == 'text':
                if val:
                    self.__dict__['markup'] = ""
                self.emit('on-change')
            elif name == 'markup':
                if val:
                    self.__dict__['text'] = ""
                self.emit('on-change')


    def measure(self, text, escape = True, max_width = None):
        """measures given text with label's font and size.
        returns width, height and ascent. Ascent's null in case if the label
        does not have font face specified (and is thusly using pango)"""

        if escape:
            text = text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if (max_width, text) in self._measures:
            return self._measures[(max_width, text)]

        width, height = None, None

        context = self._test_context

        layout = self._test_layout
        layout.set_font_description(self.font_desc)
        layout.set_markup(text)
        layout.set_single_paragraph_mode(self.single_paragraph)

        if self.alignment:
            layout.set_alignment(self.alignment)

        if self.wrap is not None:
            layout.set_wrap(self.wrap)
            layout.set_ellipsize(pango.EllipsizeMode.NONE)
        else:
            layout.set_ellipsize(self.ellipsize or pango.EllipsizeMode.END)

        if max_width is not None:
            layout.set_width(max_width * pango.SCALE)
        else:
            if self.max_width:
                max_width = self.max_width * pango.SCALE

            layout.set_width(int(self._bounds_width or max_width or -1))

        width, height = layout.get_pixel_size()

        self._measures[(max_width, text)] = width, height
        return self._measures[(max_width, text)]


    def on_render(self, sprite):
        if not self.text and not self.markup:
            self.graphics.clear()
            return

        self.graphics.set_color(self.color)

        rect_width = self.width

        max_width = 0
        if self.max_width:
            max_width = self.max_width * pango.SCALE

            # when max width is specified and we are told to align in center
            # do that (the pango instruction takes care of aligning within
            # the lines of the text)
            if self.alignment == pango.Alignment.CENTER:
                self.graphics.move_to(-(self.max_width - self.width)/2, 0)

        bounds_width = max_width or self._bounds_width or -1

        text = ""
        if self.markup:
            text = self.markup
        else:
            # otherwise escape pango
            text = self.text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        self.graphics.show_layout(text, self.font_desc,
                                  self.alignment,
                                  bounds_width,
                                  self.wrap,
                                  self.ellipsize,
                                  self.single_paragraph)

        if self._bounds_width:
            rect_width = self._bounds_width / pango.SCALE

        self.graphics.rectangle(0, 0, rect_width, self.height)
        self.graphics.clip()



class Rectangle(Sprite):
    def __init__(self, w, h, corner_radius = 0, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: width
        self.width = w

        #: height
        self.height = h

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        #: corner radius. Set bigger than 0 for rounded corners
        self.corner_radius = corner_radius
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_line_style(width = self.line_width)
        self.graphics.rectangle(0, 0, self.width, self.height, self.corner_radius)
        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Polygon(Sprite):
    def __init__(self, points, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: list of (x,y) tuples that the line should go through. Polygon
        #: will automatically close path.
        self.points = points

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if not self.points:
            self.graphics.clear()
            return

        self.graphics.move_to(*self.points[0])
        self.graphics.line_to(self.points)

        if self.fill:
            self.graphics.close_path()

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Circle(Sprite):
    def __init__(self, width, height, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: circle width
        self.width = width

        #: circle height
        self.height = height

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if self.width == self.height:
            radius = self.width / 2.0
            self.graphics.circle(radius, radius, radius)
        else:
            self.graphics.ellipse(0, 0, self.width, self.height)

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Scene(Parent, gtk.DrawingArea):
    """ Drawing area for displaying sprites.
        Add sprites to the Scene by calling :func:`add_child`.
        Scene is descendant of `gtk.DrawingArea <http://www.pygtk.org/docs/pygtk/class-gtkdrawingarea.html>`_
        and thus inherits all it's methods and everything.
    """

    __gsignals__ = {
       # "draw": "override",
       # "configure_event": "override",
        "on-enter-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-finish-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-resize": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),

        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),

        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),

        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, interactive = True, framerate = 60,
                       background_color = None, scale = False, keep_aspect = True,
                       style_class=None):
        gtk.DrawingArea.__init__(self)

        self._style = self.get_style_context()

        #: widget style. One of gtk.STYLE_CLASS_*. By default it's BACKGROUND
        self.style_class = style_class or gtk.STYLE_CLASS_BACKGROUND
        self._style.add_class(self.style_class) # so we know our colors

        #: list of sprites in scene. use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

        #: framerate of animation. This will limit how often call for
        #: redraw will be performed (that is - not more often than the framerate). It will
        #: also influence the smoothness of tweeners.
        self.framerate = framerate

        #: Scene width. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.width = None

        #: Scene height. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.height = None

        #: instance of :class:`pytweener.Tweener` that is used by
        #: :func:`animate` function, but can be also accessed directly for advanced control.
        self.tweener = False
        if pytweener:
            self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.ease_in_out)

        #: instance of :class:`ColorUtils` class for color parsing
        self.colors = Colors

        #: read only info about current framerate (frames per second)
        self.fps = 0 # inner frames per second counter

        #: Last known x position of the mouse (set on expose event)
        self.mouse_x = None

        #: Last known y position of the mouse (set on expose event)
        self.mouse_y = None

        #: Background color of the scene. Use either a string with hex color or an RGB triplet.
        self.background_color = background_color

        #: Mouse cursor appearance.
        #: Replace with your own cursor or set to False to have no cursor.
        #: None will revert back the default behavior
        self.mouse_cursor = None

        #: in contrast to the mouse cursor, this one is merely a suggestion and
        #: can be overidden by child sprites
        self.default_mouse_cursor = None

        self._blank_cursor = gdk.Cursor(gdk.CursorType.BLANK_CURSOR)

        self.__previous_mouse_signal_time = None


        #: Miminum distance in pixels for a drag to occur
        self.drag_distance = 1

        self._last_frame_time = None
        self._mouse_sprite = None
        self._drag_sprite = None
        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self.__drag_start_y = None, None

        self._mouse_in = False
        self.__last_cursor = None

        self.__drawing_queued = False

        #: When specified, upon window resize the content will be scaled
        #: relative to original window size. Defaults to False.
        self.scale = scale

        #: Should the stage maintain aspect ratio upon scale if
        #: :attr:`Scene.scale` is enabled. Defaults to true.
        self.keep_aspect = keep_aspect

        self._original_width, self._original_height = None,  None

        self._focus_sprite = None # our internal focus management

        self.__last_mouse_move = None
        self.connect("draw", self.on_draw)

        if interactive:
            self.set_can_focus(True)
            self.set_events(gdk.EventMask.POINTER_MOTION_MASK
                            | gdk.EventMask.LEAVE_NOTIFY_MASK | gdk.EventMask.ENTER_NOTIFY_MASK
                            | gdk.EventMask.BUTTON_PRESS_MASK | gdk.EventMask.BUTTON_RELEASE_MASK
                            | gdk.EventMask.SCROLL_MASK
                            | gdk.EventMask.KEY_PRESS_MASK)
            self.connect("motion-notify-event", self.__on_mouse_move)
            self.connect("enter-notify-event", self.__on_mouse_enter)
            self.connect("leave-notify-event", self.__on_mouse_leave)
            self.connect("button-press-event", self.__on_button_press)
            self.connect("button-release-event", self.__on_button_release)
            self.connect("scroll-event", self.__on_scroll)
            self.connect("key-press-event", self.__on_key_press)
            self.connect("key-release-event", self.__on_key_release)



    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        if name == '_focus_sprite':
            prev_focus = getattr(self, '_focus_sprite', None)
            if prev_focus:
                prev_focus.focused = False
                self.__dict__['_focus_sprite'] = val # drop cache to avoid echoes
                prev_focus._do_blur()

            if val:
                val.focused = True
                val._do_focus()
        elif name == "style_class":
            if hasattr(self, "style_class"):
                self._style.remove_class(self.style_class)
            self._style.add_class(val)

        self.__dict__[name] = val

    # these two mimic sprite functions so parent check can be avoided
    def from_scene_coords(self, x, y): return x, y
    def to_scene_coords(self, x, y): return x, y
    def get_matrix(self): return cairo.Matrix()
    def get_scene(self): return self


    def animate(self, sprite, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
        """Interpolate attributes of the given object using the internal tweener
           and redrawing scene after every tweener update.
           Specify the sprite and sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Redraw is requested right after creating the animation.
           Example::

             # tween some_sprite to coordinates (50,100) using default duration and easing
             scene.animate(some_sprite, x = 50, y = 100)
        """
        if not self.tweener: # here we complain
            raise Exception("pytweener was not found. Include it to enable animations")

        tween = self.tweener.add_tween(sprite,
                                       duration=duration,
                                       easing=easing,
                                       on_complete=on_complete,
                                       on_update=on_update,
                                       round=round,
                                       **kwargs)
        self.redraw()
        return tween


    def stop_animation(self, sprites):
        """stop animation without firing on_complete"""
        if isinstance(sprites, list) is False:
            sprites = [sprites]

        for sprite in sprites:
            self.tweener.kill_tweens(sprite)


    def redraw(self):
        """Queue redraw. The redraw will be performed not more often than
           the `framerate` allows"""
        if self.__drawing_queued == False: #if we are moving, then there is a timeout somewhere already
            self.__drawing_queued = True
            self._last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / self.framerate, self.__redraw_loop)

    def __redraw_loop(self):
        """loop until there is nothing more to tween"""
        self.queue_draw() # this will trigger do_expose_event when the current events have been flushed

        self.__drawing_queued = self.tweener and self.tweener.has_tweens()
        return self.__drawing_queued


    def on_draw(self, scene, context):
        w, h = self.get_allocated_width(), self.get_allocated_height()

        # clip to the visible part
        if self.background_color:
            context.rectangle(0, 0, w, h)
            color = self.colors.parse(self.background_color)
            context.set_source_rgb(*color)
            context.fill_preserve()

        if self.scale:
            aspect_x = self.width / self._original_width
            aspect_y = self.height / self._original_height
            if self.keep_aspect:
                aspect_x = aspect_y = min(aspect_x, aspect_y)
            context.scale(aspect_x, aspect_y)

        cursor, self.mouse_x, self.mouse_y, mods = self.get_window().get_pointer()

        # update tweens
        now = dt.datetime.now()
        delta = (now - (self._last_frame_time or dt.datetime.now()))
        delta = delta.seconds + delta.microseconds / 1000000.0
        self._last_frame_time = now
        if self.tweener:
            self.tweener.update(delta)

        self.fps = 1 / delta


        # start drawing
        self.emit("on-enter-frame", context)
        for sprite in self._z_ordered_sprites:
            sprite._draw(context)

        self.__check_mouse(self.mouse_x, self.mouse_y)
        self.emit("on-finish-frame", context)

        # reset the mouse signal time as redraw means we are good now
        self.__previous_mouse_signal_time = None


    def do_configure_event(self, event):
        if self._original_width is None:
            self._original_width = float(event.width)
            self._original_height = float(event.height)

        width, height = self.width, self.height
        self.width, self.height = event.width, event.height

        if width != event.width or height != event.height:
            self.emit("on-resize", event) # so that sprites can listen to it



    def all_mouse_sprites(self):
        """Returns flat list of the sprite tree for simplified iteration"""
        def all_recursive(sprites):
            if not sprites:
                return

            for sprite in sprites:
                if sprite.visible:
                    yield sprite

                    for child in all_recursive(sprite.get_mouse_sprites()):
                        yield child

        return all_recursive(self.get_mouse_sprites())


    def get_sprite_at_position(self, x, y):
        """Returns the topmost visible interactive sprite for given coordinates"""
        over = None
        for sprite in self.all_mouse_sprites():
            if sprite.interactive and sprite.check_hit(x, y):
                over = sprite

        return over


    def __check_mouse(self, x, y):
        if x is None or self._mouse_in == False:
            return

        cursor = None
        over = None

        if self.mouse_cursor is not None:
            cursor = self.mouse_cursor

        if cursor is None and self._drag_sprite:
            drag_cursor = self._drag_sprite._get_mouse_cursor()
            if drag_cursor:
                cursor = drag_cursor

        #check if we have a mouse over
        if self._drag_sprite is None:
            over = self.get_sprite_at_position(x, y)
            if self._mouse_sprite and self._mouse_sprite != over:
                self._mouse_sprite._do_mouse_out()
                self.emit("on-mouse-out", self._mouse_sprite)

            if over and cursor is None:
                sprite_cursor = over._get_mouse_cursor()
                if sprite_cursor:
                    cursor = sprite_cursor

            if over and over != self._mouse_sprite:
                over._do_mouse_over()
                self.emit("on-mouse-over", over)

            self._mouse_sprite = over

        if cursor is None:
            cursor = self.default_mouse_cursor or gdk.CursorType.ARROW # default
        elif cursor is False:
            cursor = self._blank_cursor

        if self.__last_cursor is None or cursor != self.__last_cursor:
            if isinstance(cursor, gdk.Cursor):
                self.get_window().set_cursor(cursor)
            else:
                self.get_window().set_cursor(gdk.Cursor(cursor))

            self.__last_cursor = cursor


    """ mouse events """
    def __on_mouse_move(self, scene, event):
        if self.__last_mouse_move:
            gobject.source_remove(self.__last_mouse_move)

        self.mouse_x, self.mouse_y = event.x, event.y

        # don't emit mouse move signals more often than every 0.05 seconds
        timeout = dt.timedelta(seconds=0.05)
        if self.__previous_mouse_signal_time and dt.datetime.now() - self.__previous_mouse_signal_time < timeout:
            self.__last_mouse_move = gobject.timeout_add((timeout - (dt.datetime.now() - self.__previous_mouse_signal_time)).microseconds / 1000,
                                                         self.__on_mouse_move,
                                                         scene,
                                                         event.copy())
            return

        state = event.state


        if self._mouse_down_sprite and self._mouse_down_sprite.interactive \
           and self._mouse_down_sprite.draggable and gdk.ModifierType.BUTTON1_MASK & event.state:
            # dragging around
            if not self.__drag_started:
                drag_started = (self.__drag_start_x is not None and \
                               (self.__drag_start_x - event.x) ** 2 + \
                               (self.__drag_start_y - event.y) ** 2 > self.drag_distance ** 2)

                if drag_started:
                    self._drag_sprite = self._mouse_down_sprite
                    self._mouse_down_sprite.emit("on-drag-start", event)
                    self.emit("on-drag-start", self._drag_sprite, event)
                    self.start_drag(self._drag_sprite, self.__drag_start_x, self.__drag_start_y)

        else:
            # avoid double mouse checks - the redraw will also check for mouse!
            if not self.__drawing_queued:
                self.__check_mouse(event.x, event.y)

        if self._drag_sprite:
            diff_x, diff_y = event.x - self.__drag_start_x, event.y - self.__drag_start_y
            if isinstance(self._drag_sprite.parent, Sprite):
                matrix = self._drag_sprite.parent.get_matrix()
                matrix.invert()
                diff_x, diff_y = matrix.transform_distance(diff_x, diff_y)

            self._drag_sprite.x, self._drag_sprite.y = self._drag_sprite.drag_x + diff_x, self._drag_sprite.drag_y + diff_y

            self._drag_sprite.emit("on-drag", event)
            self.emit("on-drag", self._drag_sprite, event)

        if self._mouse_sprite:
            sprite_event = gdk.Event.copy(event)
            sprite_event.x, sprite_event.y = self._mouse_sprite.from_scene_coords(event.x, event.y)
            self._mouse_sprite._do_mouse_move(sprite_event)

        self.emit("on-mouse-move", event)
        self.__previous_mouse_signal_time = dt.datetime.now()


    def start_drag(self, sprite, cursor_x = None, cursor_y = None):
        """start dragging given sprite"""
        cursor_x, cursor_y = cursor_x or sprite.x, cursor_y or sprite.y

        self._mouse_down_sprite = self._drag_sprite = sprite
        sprite.drag_x, sprite.drag_y = self._drag_sprite.x, self._drag_sprite.y
        self.__drag_start_x, self.__drag_start_y = cursor_x, cursor_y
        self.__drag_started = True


    def __on_mouse_enter(self, scene, event):
        self._mouse_in = True

    def __on_mouse_leave(self, scene, event):
        self._mouse_in = False
        if self._mouse_sprite:
            self._mouse_sprite._do_mouse_out()
            self.emit("on-mouse-out", self._mouse_sprite)
            self._mouse_sprite = None


    def __on_button_press(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if not self.__drag_started:
            self.__drag_start_x, self.__drag_start_y = event.x, event.y

        self._mouse_down_sprite = target

        # differentiate between the click count!
        if event.type == gdk.EventType.BUTTON_PRESS:
            self.emit("on-mouse-down", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_mouse_down(target_event)
            else:
                scene._focus_sprite = None  # lose focus if mouse ends up nowhere
        elif event.type == gdk.EventType._2BUTTON_PRESS:
            self.emit("on-double-click", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_double_click(target_event)
        elif event.type == gdk.EventType._3BUTTON_PRESS:
            self.emit("on-triple-click", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_triple_click(target_event)

        self.__check_mouse(event.x, event.y)
        return True


    def __on_button_release(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)

        if target:
            target._do_mouse_up(event)
        self.emit("on-mouse-up", event)

        # trying to not emit click and drag-finish at the same time
        click = not self.__drag_started or (event.x - self.__drag_start_x) ** 2 + \
                                           (event.y - self.__drag_start_y) ** 2 < self.drag_distance
        if (click and self.__drag_started == False) or not self._drag_sprite:
            if target and target == self._mouse_down_sprite:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_click(target_event)

            self.emit("on-click", event, target)

        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self__drag_start_y = None, None

        if self._drag_sprite:
            self._drag_sprite.drag_x, self._drag_sprite.drag_y = None, None
            drag_sprite, self._drag_sprite = self._drag_sprite, None
            drag_sprite.emit("on-drag-finish", event)
            self.emit("on-drag-finish", drag_sprite, event)
        self.__check_mouse(event.x, event.y)
        return True


    def __on_scroll(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if target:
            target.emit("on-mouse-scroll", event)
        self.emit("on-mouse-scroll", event)
        return True

    def __on_key_press(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_press(event)
        if not handled:
            self.emit("on-key-press", event)
        return True

    def __on_key_release(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_release(event)
        if not handled:
            self.emit("on-key-release", event)
        return True

########NEW FILE########
__FILENAME__ = i18n
# - coding: utf-8 -
import os
import locale, gettext


def setup_i18n():
    #determine location of po files
    try:
        from hamster import defs
    except:
        defs = None


    # to avoid confusion, we won't translate unless running installed
    # reason for that is that bindtextdomain is expecting
    # localedir/language/LC_MESSAGES/domain.mo format, but we have
    # localedir/language.mo at it's best (after build)
    # and there does not seem to be any way to run straight from sources
    if defs:
        locale_dir = os.path.realpath(os.path.join(defs.DATA_DIR, "locale"))

        for module in (locale,gettext):
            module.bindtextdomain('hamster-time-tracker', locale_dir)
            module.textdomain('hamster-time-tracker')

            module.bind_textdomain_codeset('hamster-time-tracker','utf8')

        gettext.install("hamster-time-tracker", locale_dir, unicode = True)

    else:
        gettext.install("hamster-time-tracker-uninstalled")


def C_(ctx, s):
    """Provide qualified translatable strings via context.
        Taken from gnome-games.
    """
    translated = gettext.gettext('%s\x04%s' % (ctx, s))
    if '\x04' in translated:
        # no translation found, return input string
        return s
    return translated

########NEW FILE########
__FILENAME__ = layout
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Copyright (c) 2014 Toms Baugis <toms.baugis@gmail.com>
# Dual licensed under the MIT or GPL Version 2 licenses.

import datetime as dt
import math
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from collections import defaultdict

import graphics


class Widget(graphics.Sprite):
    """Base class for all widgets. You can use the width and height attributes
    to request a specific width."""

    _sizing_attributes = set(("visible", "min_width", "min_height",
                              "expand", "fill", "spacing",
                              "horizontal_spacing", "vertical_spacing", "x_align",
                              "y_align"))

    min_width = None  #: minimum width of the widget
    min_height = None #: minimum height of the widget

    #: Whether the child should receive extra space when the parent grows.
    expand = True

    #: Whether extra space given to the child should be allocated to the
    #: child or used as padding. Edit :attr:`x_align` and
    #: :attr:`y_align` properties to adjust alignment when fill is set to False.
    fill = True

    #: horizontal alignment within the parent. Works when :attr:`fill` is False
    x_align = 0.5

    #: vertical alignment within the parent. Works when :attr:`fill` is False
    y_align = 0.5

    #: child padding - shorthand to manipulate padding in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`padding_top`, :attr:`padding_right`, :attr:`padding_bottom`
    #: and :attr:`padding_left`
    padding = None
    padding_top = None    #: child padding - top
    padding_right = None  #: child padding - right
    padding_bottom = None #: child padding - bottom
    padding_left = None   #: child padding - left

    #: widget margins - shorthand to manipulate margin in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`margin_top`, :attr:`margin_right`, :attr:`margin_bottom` and
    #: :attr:`margin_left`
    margin = 0
    margin_top = 0     #: top margin
    margin_right = 0   #: right margin
    margin_bottom = 0  #: bottom margin
    margin_left = 0    #: left margin

    enabled = True #: whether the widget is enabled

    mouse_cursor = False #: Mouse cursor. see :attr:`graphics.Sprite.mouse_cursor` for values

    def __init__(self, width = None, height = None, expand = None, fill = None,
                 x_align = None, y_align = None,
                 padding_top = None, padding_right = None,
                 padding_bottom = None, padding_left = None, padding = None,
                 margin_top = None, margin_right = None,
                 margin_bottom = None, margin_left = None, margin = None,
                 enabled = None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        def set_if_not_none(name, val):
            # set values - avoid pitfalls of None vs 0/False
            if val is not None:
                setattr(self, name, val)

        set_if_not_none("min_width", width)
        set_if_not_none("min_height", height)

        self._enabled = enabled if enabled is not None else self.__class__.enabled

        set_if_not_none("fill", fill)
        set_if_not_none("expand", expand)
        set_if_not_none("x_align", x_align)
        set_if_not_none("y_align", y_align)

        # set padding
        # (class, subclass, instance, and constructor)
        if padding is not None or self.padding is not None:
            self.padding = padding if padding is not None else self.padding
        self.padding_top = padding_top or self.__class__.padding_top or self.padding_top or 0
        self.padding_right = padding_right or self.__class__.padding_right or self.padding_right or 0
        self.padding_bottom = padding_bottom or self.__class__.padding_bottom or self.padding_bottom or 0
        self.padding_left = padding_left or self.__class__.padding_left or self.padding_left or 0

        if margin is not None or self.margin is not None:
            self.margin = margin if margin is not None else self.margin
        self.margin_top = margin_top or self.__class__.margin_top or self.margin_top or 0
        self.margin_right = margin_right or self.__class__.margin_right or self.margin_right or 0
        self.margin_bottom = margin_bottom or self.__class__.margin_bottom or self.margin_bottom or 0
        self.margin_left = margin_left or self.__class__.margin_left or self.margin_left or 0


        #: width in pixels that have been allocated to the widget by parent
        self.alloc_w = width if width is not None else self.min_width

        #: height in pixels that have been allocated to the widget by parent
        self.alloc_h = height if height is not None else self.min_height

        self.connect_after("on-render", self.__on_render)
        self.connect("on-mouse-over", self.__on_mouse_over)
        self.connect("on-mouse-out", self.__on_mouse_out)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-key-press", self.__on_key_press)

        self._children_resize_queued = True
        self._scene_resize_handler = None


    def __setattr__(self, name, val):
        # forward width and height to min_width and min_height as i've ruined the setters a bit i think
        if name == "width":
            name = "min_width"
        elif name == "height":
            name = "min_height"
        elif name == 'enabled':
            name = '_enabled'
        elif name == "padding":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.padding_top = self.padding_right = self.padding_bottom = self.padding_left = val[0]
            elif len(val) == 2:
                self.padding_top = self.padding_bottom = val[0]
                self.padding_right = self.padding_left = val[1]

            elif len(val) == 3:
                self.padding_top = val[0]
                self.padding_right = self.padding_left = val[1]
                self.padding_bottom = val[2]
            elif len(val) == 4:
                self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = val
            return

        elif name == "margin":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.margin_top = self.margin_right = self.margin_bottom = self.margin_left = val[0]
            elif len(val) == 2:
                self.margin_top = self.margin_bottom = val[0]
                self.margin_right = self.margin_left = val[1]
            elif len(val) == 3:
                self.margin_top = val[0]
                self.margin_right = self.margin_left = val[1]
                self.margin_bottom = val[2]
            elif len(val) == 4:
                self.margin_top, self.margin_right, self.margin_bottom, self.margin_left = val
            return


        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        graphics.Sprite.__setattr__(self, name, val)

        # in widget case visibility affects placement and everything so request repositioning from parent
        if name == 'visible' and getattr(self, "parent", None) and getattr(self.parent, "resize_children", None):
            self.parent.resize_children()

        elif name == '_enabled' and getattr(self, "sprites", None):
            self._propagate_enabledness()

        if name in self._sizing_attributes:
            self.queue_resize()

    def _propagate_enabledness(self):
        # runs down the tree and marks all child sprites as dirty as
        # enabledness is inherited
        self._sprite_dirty = True
        for sprite in self.sprites:
            next_call = getattr(sprite, "_propagate_enabledness", None)
            if next_call:
                next_call()

    def _with_rotation(self, w, h):
        """calculate the actual dimensions after rotation"""
        res_w = abs(w * math.cos(self.rotation) + h * math.sin(self.rotation))
        res_h = abs(h * math.cos(self.rotation) + w * math.sin(self.rotation))
        return res_w, res_h

    @property
    def horizontal_padding(self):
        """total calculated horizontal padding. A read-only property."""
        return self.padding_left + self.padding_right

    @property
    def vertical_padding(self):
        """total calculated vertical padding.  A read-only property."""
        return self.padding_top + self.padding_bottom

    def __on_mouse_over(self, sprite):
        cursor, mouse_x, mouse_y, mods = sprite.get_scene().get_window().get_pointer()
        if self.tooltip and not gdk.ModifierType.BUTTON1_MASK & mods:
            self._set_tooltip(self.tooltip)


    def __on_mouse_out(self, sprite):
        if self.tooltip:
            self._set_tooltip(None)

    def __on_mouse_down(self, sprite, event):
        if self.can_focus:
            self.grab_focus()
        if self.tooltip:
            self._set_tooltip(None)

    def __on_key_press(self, sprite, event):
        if event.keyval in (gdk.KEY_Tab, gdk.KEY_ISO_Left_Tab):
            idx = self.parent.sprites.index(self)

            if event.state & gdk.ModifierType.SHIFT_MASK: # going backwards
                if idx > 0:
                    idx -= 1
                    self.parent.sprites[idx].grab_focus()
            else:
                if idx < len(self.parent.sprites) - 1:
                    idx += 1
                    self.parent.sprites[idx].grab_focus()


    def queue_resize(self):
        """request the element to re-check it's child sprite sizes"""
        self._children_resize_queued = True
        parent = getattr(self, "parent", None)
        if parent and isinstance(parent, graphics.Sprite) and hasattr(parent, "queue_resize"):
            parent.queue_resize()


    def get_min_size(self):
        """returns size required by the widget"""
        if self.visible == False:
            return 0, 0
        else:
            return ((self.min_width or 0) + self.horizontal_padding + self.margin_left + self.margin_right,
                    (self.min_height or 0) + self.vertical_padding + self.margin_top + self.margin_bottom)



    def insert(self, index = 0, *widgets):
        """insert widget in the sprites list at the given index.
        by default will prepend."""
        for widget in widgets:
            self._add(widget, index)
            index +=1 # as we are moving forwards
        self._sort()


    def insert_before(self, target):
        """insert this widget into the targets parent before the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target), self)

    def insert_after(self, target):
        """insert this widget into the targets parent container after the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target) + 1, self)


    @property
    def width(self):
        """width in pixels"""
        alloc_w = self.alloc_w

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_w = self.parent.width

            def res(scene, event):
                if self.parent:
                    self.queue_resize()
                else:
                    scene.disconnect(self._scene_resize_handler)
                    self._scene_resize_handler = None


            if not self._scene_resize_handler:
                # TODO - disconnect on reparenting
                self._scene_resize_handler = self.parent.connect("on-resize", res)


        min_width = (self.min_width or 0) + self.margin_left + self.margin_right
        w = alloc_w if alloc_w is not None and self.fill else min_width
        w = max(w or 0, self.get_min_size()[0])
        return w - self.margin_left - self.margin_right

    @property
    def height(self):
        """height in pixels"""
        alloc_h = self.alloc_h

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_h = self.parent.height

        min_height = (self.min_height or 0) + self.margin_top + self.margin_bottom
        h = alloc_h if alloc_h is not None and self.fill else min_height
        h = max(h or 0, self.get_min_size()[1])
        return h - self.margin_top - self.margin_bottom

    @property
    def enabled(self):
        """whether the user is allowed to interact with the
        widget. Item is enabled only if all it's parent elements are"""
        enabled = self._enabled
        if not enabled:
            return False

        if self.parent and isinstance(self.parent, Widget):
            if self.parent.enabled == False:
                return False

        return True


    def __on_render(self, sprite):
        self.do_render()
        if self.debug:
            self.graphics.save_context()

            w, h = self.width, self.height
            if hasattr(self, "get_height_for_width_size"):
                w2, h2 = self.get_height_for_width_size()
                w2 = w2 - self.margin_left - self.margin_right
                h2 = h2 - self.margin_top - self.margin_bottom
                w, h = max(w, w2), max(h, h2)

            self.graphics.rectangle(0.5, 0.5, w, h)
            self.graphics.set_line_style(3)
            self.graphics.stroke("#666", 0.5)
            self.graphics.restore_context()

            if self.pivot_x or self.pivot_y:
                self.graphics.fill_area(self.pivot_x - 3, self.pivot_y - 3, 6, 6, "#666")


    def do_render(self):
        """this function is called in the on-render event. override it to do
           any drawing. subscribing to the "on-render" event will work too, but
           overriding this method is preferred for easier subclassing.
        """
        pass





def get_min_size(sprite):
    if hasattr(sprite, "get_min_size"):
        min_width, min_height = sprite.get_min_size()
    else:
        min_width, min_height = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

    min_width = min_width * sprite.scale_x
    min_height = min_height * sprite.scale_y

    return min_width, min_height

def get_props(sprite):
    # gets all the relevant info for containers and puts it in a uniform dict.
    # this way we can access any object without having to check types and such
    keys = ("margin_top", "margin_right", "margin_bottom", "margin_left",
            "padding_top", "padding_right", "padding_bottom", "padding_left")
    res = dict((key, getattr(sprite, key, 0)) for key in keys)
    res["expand"] = getattr(sprite, "expand", True)

    return sprite, res


class Container(Widget):
    """The base container class that all other containers inherit from.
       You can insert any sprite in the container, just make sure that it either
       has width and height defined so that the container can do alignment, or
       for more sophisticated cases, make sure it has get_min_size function that
       returns how much space is needed.

       Normally while performing layout the container will update child sprites
       and set their alloc_h and alloc_w properties. The `alloc` part is short
       for allocated. So use that when making rendering decisions.
    """
    cache_attrs = Widget.cache_attrs | set(('_cached_w', '_cached_h'))
    _sizing_attributes = Widget._sizing_attributes | set(('padding_top', 'padding_right', 'padding_bottom', 'padding_left'))

    def __init__(self, contents = None, **kwargs):
        Widget.__init__(self, **kwargs)

        #: contents of the container - either a widget or a list of widgets
        self.contents = contents
        self._cached_w, self._cached_h = None, None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Widget.__setattr__(self, name, val)
        if name == 'contents':
            if val:
                if isinstance(val, graphics.Sprite):
                    val = [val]
                self.add_child(*val)
            if self.sprites and self.sprites != val:
                self.remove_child(*list(set(self.sprites) ^ set(val or [])))

        if name in ("alloc_w", "alloc_h") and val:
            self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
            self._children_resize_queued = True


    @property
    def contents(self):
        return self.sprites


    def _Widget__on_render(self, sprite):
        if self._children_resize_queued:
            self.resize_children()
            self.__dict__['_children_resize_queued'] = False
        Widget._Widget__on_render(self, sprite)


    def _add(self, *sprites):
        Widget._add(self, *sprites)
        self.queue_resize()

    def remove_child(self, *sprites):
        Widget.remove_child(self, *sprites)
        self.queue_resize()

    def queue_resize(self):
        self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
        Widget.queue_resize(self)

    def get_min_size(self):
        # by default max between our requested size and the biggest child
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]
            width = max([get_min_size(sprite)[0] for sprite in sprites] or [0])
            width += self.horizontal_padding  + self.margin_left + self.margin_right

            height = max([get_min_size(sprite)[1] for sprite in sprites] or [0])
            height += self.vertical_padding + self.margin_top + self.margin_bottom

            self._cached_w, self._cached_h = max(width, self.min_width or 0), max(height, self.min_height or 0)

        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        return self.get_min_size()


    def resize_children(self):
        """default container alignment is to pile stuff just up, respecting only
        padding, margin and element's alignment properties"""
        width = self.width - self.horizontal_padding
        height = self.height - self.vertical_padding

        for sprite, props in (get_props(sprite) for sprite in self.sprites if sprite.visible):
            sprite.alloc_w = width
            sprite.alloc_h = height

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]

            sprite.x = self.padding_left + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0)
            sprite.y = self.padding_top + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0)


        self.__dict__['_children_resize_queued'] = False


class Bin(Container):
    """A container with only one child. Adding new children will throw the
    previous ones out"""
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    @property
    def child(self):
        """child sprite. shorthand for self.sprites[0]"""
        return self.sprites[0] if self.sprites else None

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y

            width = max(width, w)
            height = max(height, h)

        #width = width + self.horizontal_padding + self.margin_left + self.margin_right
        #height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height


    def add_child(self, *sprites):
        if not sprites:
            return

        sprite = sprites[-1] # there can be just one

        # performing add then remove to not screw up coordinates in
        # a strange reparenting case
        Container.add_child(self, sprite)
        if self.sprites and self.sprites[0] != sprite:
            self.remove_child(*list(set(self.sprites) ^ set([sprite])))



class Fixed(Container):
    """Basic container that does not care about child positions. Handy if
       you want to place stuff yourself or do animations.
    """
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    def resize_children(self):
        # don't want
        pass



class Box(Container):
    """Align children either horizontally or vertically.
        Normally you would use :class:`HBox` or :class:`VBox` to be
        specific but this one is suited so you can change the packing direction
        dynamically.
    """
    #: spacing in pixels between children
    spacing = 5

    #: whether the box is packing children horizontally (from left to right) or vertically (from top to bottom)
    orient_horizontal = True

    def __init__(self, contents = None, horizontal = None, spacing = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

        if horizontal is not None:
            self.orient_horizontal = horizontal

        if spacing is not None:
            self.spacing = spacing

    def get_total_spacing(self):
        # now lay them out
        padding_sprites = 0
        for sprite in self.sprites:
            if sprite.visible:
                if getattr(sprite, "expand", True):
                    padding_sprites += 1
                else:
                    if hasattr(sprite, "get_min_size"):
                        size = sprite.get_min_size()[0] if self.orient_horizontal else sprite.get_min_size()[1]
                    else:
                        size = getattr(sprite, "width", 0) * sprite.scale_x if self.orient_horizontal else getattr(sprite, "height", 0) * sprite.scale_y

                    if size > 0:
                        padding_sprites +=1
        return self.spacing * max(padding_sprites - 1, 0)


    def resize_children(self):
        if not self.parent:
            return

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        sprites = [get_props(sprite) for sprite in self.sprites if sprite.visible]

        # calculate if we have any spare space
        sprite_sizes = []
        for sprite, props in sprites:
            if self.orient_horizontal:
                sprite.alloc_h = height / sprite.scale_y
                size = get_min_size(sprite)[0]
                size = size + props["margin_left"] + props["margin_right"]
            else:
                sprite.alloc_w = width / sprite.scale_x
                size = get_min_size(sprite)[1]
                if hasattr(sprite, "get_height_for_width_size"):
                    size = max(size, sprite.get_height_for_width_size()[1] * sprite.scale_y)
                size = size + props["margin_top"] + props["margin_bottom"]
            sprite_sizes.append(size)


        remaining_space = width if self.orient_horizontal else height
        if sprite_sizes:
            remaining_space = remaining_space - sum(sprite_sizes) - self.get_total_spacing()


        interested_sprites = [sprite for sprite, props in sprites if getattr(sprite, "expand", True)]


        # in order to stay pixel sharp we will recalculate remaining bonus
        # each time we give up some of the remaining space
        remaining_interested = len(interested_sprites)
        bonus = 0
        if remaining_space > 0 and interested_sprites:
            bonus = int(remaining_space / remaining_interested)

        actual_h = 0
        x_pos, y_pos = 0, 0

        for (sprite, props), min_size in zip(sprites, sprite_sizes):
            sprite_bonus = 0
            if sprite in interested_sprites:
                sprite_bonus = bonus
                remaining_interested -= 1
                remaining_space -= bonus
                if remaining_interested:
                    bonus = int(float(remaining_space) / remaining_interested)


            if self.orient_horizontal:
                sprite.alloc_w = (min_size + sprite_bonus) / sprite.scale_x
            else:
                sprite.alloc_h = (min_size + sprite_bonus) / sprite.scale_y

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]


            sprite.x = self.padding_left + x_pos + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0.5)
            sprite.y = self.padding_top + y_pos + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0.5)


            actual_h = max(actual_h, h * sprite.scale_y)

            if (min_size + sprite_bonus) > 0:
                if self.orient_horizontal:
                    x_pos += int(max(w, sprite.alloc_w * sprite.scale_x)) + self.spacing
                else:
                    y_pos += max(h, sprite.alloc_h * sprite.scale_y) + self.spacing


        if self.orient_horizontal:
            for sprite, props in sprites:
                sprite.__dict__['alloc_h'] = actual_h

        self.__dict__['_children_resize_queued'] = False

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y


            if self.orient_horizontal:
                width += w
                height = max(height, h)
            else:
                width = max(width, w)
                height = height + h

        if self.orient_horizontal:
            width = width + self.get_total_spacing()
        else:
            height = height + self.get_total_spacing()

        width = width + self.horizontal_padding + self.margin_left + self.margin_right
        height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height



    def get_min_size(self):
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]

            width, height = 0, 0
            for sprite in sprites:
                if hasattr(sprite, "get_min_size"):
                    w, h = sprite.get_min_size()
                else:
                    w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

                w, h = w * sprite.scale_x, h * sprite.scale_y

                if self.orient_horizontal:
                    width += w
                    height = max(height, h)
                else:
                    width = max(width, w)
                    height = height + h

            if self.orient_horizontal:
                width = width + self.get_total_spacing()
            else:
                height = height + self.get_total_spacing()

            width = width + self.horizontal_padding + self.margin_left + self.margin_right
            height = height + self.vertical_padding + self.margin_top + self.margin_bottom

            w, h = max(width, self.min_width or 0), max(height, self.min_height or 0)
            self._cached_w, self._cached_h = w, h

        return self._cached_w, self._cached_h


class HBox(Box):
    """A horizontally aligned box. identical to ui.Box(horizontal=True)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = True


class VBox(Box):
    """A vertically aligned box. identical to ui.Box(horizontal=False)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = False



class _DisplayLabel(graphics.Label):
    cache_attrs = Box.cache_attrs | set(('_cached_w', '_cached_h'))

    def __init__(self, text="", **kwargs):
        graphics.Label.__init__(self, text, **kwargs)
        self._cached_w, self._cached_h = None, None
        self._cached_wh_w, self._cached_wh_h = None, None

    def __setattr__(self, name, val):
        graphics.Label.__setattr__(self, name, val)

        if name in ("text", "markup", "size", "wrap", "ellipsize", "max_width"):
            if name != "max_width":
                self._cached_w, self._cached_h = None, None
            self._cached_wh_w, self._cached_wh_h = None, None


    def get_min_size(self):
        if self._cached_w:
            return self._cached_w, self._cached_h

        text = self.markup or self.text
        escape = len(self.markup) == 0

        if self.wrap is not None or self.ellipsize is not None:
            self._cached_w = self.measure(text, escape, 1)[0]
            self._cached_h = self.measure(text, escape, -1)[1]
        else:
            self._cached_w, self._cached_h = self.measure(text, escape, -1)
        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        if self._cached_wh_w:
            return self._cached_wh_w, self._cached_wh_h

        text = self.markup or self.text
        escape = len(self.markup) == 0
        self._cached_wh_w, self._cached_wh_h = self.measure(text, escape, self.max_width)

        return self._cached_wh_w, self._cached_wh_h


class Label(Bin):
    """a widget that displays a limited amount of read-only text"""
    #: pango.FontDescription to use for the label
    font_desc = None

    #: image attachment. one of top, right, bottom, left
    image_position = "left"

    #: font size
    size = None

    fill = False
    padding = 0
    x_align = 0.5

    def __init__(self, text = "", markup = "", spacing = 5, image = None,
                 image_position = None, size = None, font_desc = None,
                 overflow = False, color = "#000", background_color = None,
                 **kwargs):

        # TODO - am initiating table with fill = false but that yields suboptimal label placement and the 0,0 points to whatever parent gave us
        Bin.__init__(self, **kwargs)

        #: image to put next to the label
        self.image = image

        # the actual container that contains the label and/or image
        self.container = Box(spacing = spacing, fill = False,
                             x_align = self.x_align, y_align = self.y_align)

        if image_position is not None:
            self.image_position = image_position

        self.display_label = _DisplayLabel(text = text, markup = markup, color=color, size = size)
        self.display_label.x_align = 0 # the default is 0.5 which makes label align incorrectly on wrapping

        if font_desc or self.font_desc:
            self.display_label.font_desc = font_desc or self.font_desc

        self.display_label.size = size or self.size

        self.background_color = background_color

        #: either the pango `wrap <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-wrap-mode-constants>`_
        #: or `ellipsize <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-ellipsize-mode-constants>`_ constant.
        #: if set to False will refuse to become smaller
        self.overflow = overflow

        self.add_child(self.container)

        self._position_contents()
        self.connect_after("on-render", self.__on_render)

    def get_mouse_sprites(self):
        return None

    @property
    def text(self):
        """label text. This attribute and :attr:`markup` are mutually exclusive."""
        return self.display_label.text

    @property
    def markup(self):
        """pango markup to use in the label.
        This attribute and :attr:`text` are mutually exclusive."""
        return self.display_label.markup

    @property
    def color(self):
        """label color"""
        return self.display_label.color

    def __setattr__(self, name, val):
        if name in ("text", "markup", "color", "size"):
            if self.display_label.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            setattr(self.display_label, name, val)
        elif name in ("spacing"):
            setattr(self.container, name, val)
        else:
            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            Bin.__setattr__(self, name, val)


        if name in ('x_align', 'y_align') and hasattr(self, "container"):
            setattr(self.container, name, val)

        elif name == "alloc_w" and hasattr(self, "display_label") and getattr(self, "overflow") is not False:
            self._update_max_width()

        elif name == "min_width" and hasattr(self, "display_label"):
            self.display_label.width = val - self.horizontal_padding

        elif name == "overflow" and hasattr(self, "display_label"):
            if val is False:
                self.display_label.wrap = None
                self.display_label.ellipsize = None
            elif isinstance(val, pango.WrapMode) and val in (pango.WrapMode.WORD, pango.WrapMode.WORD_CHAR, pango.WrapMode.CHAR):
                self.display_label.wrap = val
                self.display_label.ellipsize = None
            elif isinstance(val, pango.EllipsizeMode) and val in (pango.EllipsizeMode.START, pango.EllipsizeMode.MIDDLE, pango.EllipsizeMode.END):
                self.display_label.wrap = None
                self.display_label.ellipsize = val

            self._update_max_width()
        elif name in ("font_desc", "size"):
            setattr(self.display_label, name, val)

        if name in ("text", "markup", "image", "image_position", "overflow", "size"):
            if hasattr(self, "overflow"):
                self._position_contents()
                self.container.queue_resize()


    def _update_max_width(self):
        # updates labels max width, respecting image and spacing
        if self.overflow is False:
            self.display_label.max_width = -1
        else:
            w = (self.alloc_w or 0) - self.horizontal_padding - self.container.spacing
            if self.image and self.image_position in ("left", "right"):
                w -= self.image.width - self.container.spacing
            self.display_label.max_width = w

        self.container.queue_resize()


    def _position_contents(self):
        if self.image and (self.text or self.markup):
            self.image.expand = False
            self.container.orient_horizontal = self.image_position in ("left", "right")

            if self.image_position in ("top", "left"):
                if self.container.sprites != [self.image, self.display_label]:
                    self.container.clear()
                    self.container.add_child(self.image, self.display_label)
            else:
                if self.container.sprites != [self.display_label, self.image]:
                    self.container.clear()
                    self.container.add_child(self.display_label, self.image)
        elif self.image or (self.text or self.markup):
            sprite = self.image or self.display_label
            if self.container.sprites != [sprite]:
                self.container.clear()
                self.container.add_child(sprite)


    def __on_render(self, sprite):
        w, h = self.width, self.height
        w2, h2 = self.get_height_for_width_size()
        w, h = max(w, w2), max(h, h2)
        self.graphics.rectangle(0, 0, w, h)

        if self.background_color:
            self.graphics.fill(self.background_color)
        else:
            self.graphics.new_path()

########NEW FILE########
__FILENAME__ = pytweener
# pyTweener
#
# Tweening functions for python
#
# Heavily based on caurina Tweener: http://code.google.com/p/tweener/
#
# Released under M.I.T License - see above url
# Python version by Ben Harling 2009
# All kinds of slashing and dashing by Toms Baugis 2010, 2014
import math
import collections
import datetime as dt
import time
import re

class Tweener(object):
    def __init__(self, default_duration = None, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.current_tweens = collections.defaultdict(set)
        self.default_easing = tween or Easing.Cubic.ease_in_out
        self.default_duration = default_duration or 1.0

    def has_tweens(self):
        return len(self.current_tweens) > 0


    def add_tween(self, obj, duration = None, easing = None, on_complete = None,
                  on_update = None, round = False, delay = None, **kwargs):
        """
            Add tween for the object to go from current values to set ones.
            Example: add_tween(sprite, x = 500, y = 200, duration = 0.4)
            This will move the sprite to coordinates (500, 200) in 0.4 seconds.
            For parameter "easing" you can use one of the pytweener.Easing
            functions, or specify your own.
            The tweener can handle numbers, dates and color strings in hex ("#ffffff").
            This function performs overwrite style conflict solving - in case
            if a previous tween operates on same attributes, the attributes in
            question are removed from that tween.
        """
        if duration is None:
            duration = self.default_duration

        easing = easing or self.default_easing

        tw = Tween(obj, duration, delay, easing, on_complete, on_update, round, **kwargs )

        if obj in self.current_tweens:
            for current_tween in tuple(self.current_tweens[obj]):
                prev_keys = set((key for (key, tweenable) in current_tween.tweenables))
                dif = prev_keys & set(kwargs.keys())

                for key, tweenable in tuple(current_tween.tweenables):
                    if key in dif:
                        current_tween.tweenables.remove((key, tweenable))

                if not current_tween.tweenables:
                    current_tween.finish()
                    self.current_tweens[obj].remove(current_tween)


        self.current_tweens[obj].add(tw)
        return tw


    def get_tweens(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        return self.current_tweens.get(obj, None)

    def kill_tweens(self, obj = None):
        """Stop tweening an object, without completing the motion or firing the
        on_complete"""
        if obj is not None:
            try:
                del self.current_tweens[obj]
            except:
                pass
        else:
            self.current_tweens = collections.defaultdict(set)

    def remove_tween(self, tween):
        """"remove given tween without completing the motion or firing the on_complete"""
        if tween.target in self.current_tweens and tween in self.current_tweens[tween.target]:
            self.current_tweens[tween.target].remove(tween)
            if not self.current_tweens[tween.target]:
                del self.current_tweens[tween.target]

    def finish(self):
        """jump the the last frame of all tweens"""
        for obj in self.current_tweens:
            for tween in self.current_tweens[obj]:
                tween.finish()
        self.current_tweens = {}

    def update(self, delta_seconds):
        """update tweeners. delta_seconds is time in seconds since last frame"""

        for obj in tuple(self.current_tweens):
            for tween in tuple(self.current_tweens[obj]):
                done = tween.update(delta_seconds)
                if done:
                    self.current_tweens[obj].remove(tween)
                    if tween.on_complete: tween.on_complete(tween.target)

            if not self.current_tweens[obj]:
                del self.current_tweens[obj]

        return self.current_tweens


class Tween(object):
    __slots__ = ('tweenables', 'target', 'delta', 'duration', 'delay',
                 'ease', 'delta', 'complete', 'round',
                 'on_complete', 'on_update')

    def __init__(self, obj, duration, delay, easing, on_complete, on_update, round,
                 **kwargs):
        """Tween object use Tweener.add_tween( ... ) to create"""

        #: should the tween values truncated to integers or not. Default is False.
        self.round = round

        #: duration of the tween
        self.duration = duration

        #: delay before the animation should be started
        self.delay = delay or 0

        self.target = obj

        #: easing function
        self.ease = easing

        # list of (property, start_value, delta)
        self.tweenables = set()
        for key, value in kwargs.items():
            self.tweenables.add((key, Tweenable(getattr(self.target, key), value)))

        self.delta = 0

        #: callback to execute on complete
        self.on_complete = on_complete

        #: callback to execute on update
        self.on_update = on_update

        self.complete = False

    def finish(self):
        self.update(self.duration)

    def update(self, ptime):
        """Update tween with the time since the last frame"""
        delta = self.delta + ptime
        total_duration = self.delay + self.duration

        if delta > total_duration:
            delta = total_duration

        if delta < self.delay:
            pass
        elif delta == total_duration:
            for key, tweenable in self.tweenables:
                setattr(self.target, key, tweenable.target_value)
        else:
            fraction = self.ease((delta - self.delay) / (total_duration - self.delay))

            for key, tweenable in self.tweenables:
                res = tweenable.update(fraction)
                if isinstance(res, float) and self.round:
                    res = int(res)
                setattr(self.target, key, res)

        if delta == total_duration or len(self.tweenables) == 0:
            self.complete = True

        self.delta = delta

        if self.on_update:
            self.on_update(self.target)

        return self.complete




class Tweenable(object):
    """a single attribute that has to be tweened from start to target"""
    __slots__ = ('start_value', 'change', 'decode_func', 'target_value', 'update')

    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")


    def __init__(self, start_value, target_value):
        self.decode_func = lambda x: x
        self.target_value = target_value

        def float_update(fraction):
            return self.start_value + self.change * fraction

        def date_update(fraction):
            return dt.date.fromtimestamp(self.start_value + self.change * fraction)

        def datetime_update(fraction):
            return dt.datetime.fromtimestamp(self.start_value + self.change * fraction)

        def color_update(fraction):
            val = [max(min(self.start_value[i] + self.change[i] * fraction, 255), 0)  for i in range(3)]
            return "#%02x%02x%02x" % (val[0], val[1], val[2])


        if isinstance(start_value, int) or isinstance(start_value, float):
            self.start_value = start_value
            self.change = target_value - start_value
            self.update = float_update
        else:
            if isinstance(start_value, dt.datetime) or isinstance(start_value, dt.date):
                if isinstance(start_value, dt.datetime):
                    self.update = datetime_update
                else:
                    self.update = date_update

                self.decode_func = lambda x: time.mktime(x.timetuple())
                self.start_value = self.decode_func(start_value)
                self.change = self.decode_func(target_value) - self.start_value

            elif isinstance(start_value, basestring) \
             and (self.hex_color_normal.match(start_value) or self.hex_color_short.match(start_value)):
                self.update = color_update
                if self.hex_color_normal.match(start_value):
                    self.decode_func = lambda val: [int(match, 16)
                                                    for match in self.hex_color_normal.match(val).groups()]

                elif self.hex_color_short.match(start_value):
                    self.decode_func = lambda val: [int(match + match, 16)
                                                    for match in self.hex_color_short.match(val).groups()]

                if self.hex_color_normal.match(target_value):
                    target_value = [int(match, 16)
                                    for match in self.hex_color_normal.match(target_value).groups()]
                else:
                    target_value = [int(match + match, 16)
                                    for match in self.hex_color_short.match(target_value).groups()]

                self.start_value = self.decode_func(start_value)
                self.change = [target - start for start, target in zip(self.start_value, target_value)]



"""Robert Penner's classes stripped from the repetetive c,b,d mish-mash
(discovery of Patryk Zawadzki). This way we do the math once and apply to
all the tweenables instead of repeating it for each attribute
"""

def inverse(method):
    def real_inverse(t, *args, **kwargs):
        t = 1 - t
        return 1 - method(t, *args, **kwargs)
    return real_inverse

def symmetric(ease_in, ease_out):
    def real_symmetric(t, *args, **kwargs):
        if t < 0.5:
            return ease_in(t * 2, *args, **kwargs) / 2

        return ease_out((t - 0.5) * 2, *args, **kwargs) / 2 + 0.5
    return real_symmetric

class Symmetric(object):
    def __init__(self, ease_in = None, ease_out = None):
        self.ease_in = ease_in or inverse(ease_out)
        self.ease_out = ease_out or inverse(ease_in)
        self.ease_in_out = symmetric(self.ease_in, self.ease_out)


class Easing(object):
    """Class containing easing classes to use together with the tweener.
       All of the classes have :func:`ease_in`, :func:`ease_out` and
       :func:`ease_in_out` functions."""

    Linear = Symmetric(lambda t: t, lambda t: t)
    Quad = Symmetric(lambda t: t*t)
    Cubic = Symmetric(lambda t: t*t*t)
    Quart = Symmetric(lambda t: t*t*t*t)
    Quint = Symmetric(lambda t: t*t*t*t*t)
    Strong = Quint #oh i wonder why but the ported code is the same as in Quint

    Circ = Symmetric(lambda t: 1 - math.sqrt(1 - t * t))
    Sine = Symmetric(lambda t: 1 - math.cos(t * (math.pi / 2)))


    def _back_in(t, s=1.70158):
        return t * t * ((s + 1) * t - s)
    Back = Symmetric(_back_in)


    def _bounce_out(t):
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t = t - 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t = t - 2.25 / 2.75
            return 7.5625 * t * t + .9375
        else:
            t = t - 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    Bounce = Symmetric(ease_out = _bounce_out)


    def _elastic_in(t, springiness = 0, wave_length = 0):
        if t in(0, 1):
            return t

        wave_length = wave_length or (1 - t) * 0.3

        if springiness <= 1:
            springiness = t
            s = wave_length / 4
        else:
            s = wave_length / (2 * math.pi) * math.asin(t / springiness)

        t = t - 1
        return -(springiness * math.pow(2, 10 * t) * math.sin((t * t - s) * (2 * math.pi) / wave_length))
    Elastic = Symmetric(_elastic_in)


    def _expo_in(t):
        if t in (0, 1): return t
        return math.pow(2, 10 * t) * 0.001
    Expo = Symmetric(_expo_in)



class _Dummy(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

if __name__ == "__main__":
    import datetime as dt

    tweener = Tweener()
    objects = []

    object_count, update_times = 1000, 100

    for i in range(object_count):
        objects.append(_Dummy(i-100, i-100, i-100))


    total = dt.datetime.now()

    t = dt.datetime.now()
    print "Adding %d tweens..." % object_count
    for i, o in enumerate(objects):
        tweener.add_tween(o, a = i,
                             b = i,
                             c = i,
                             duration = 0.1 * update_times,
                             easing=Easing.Circ.ease_in_out)
    print dt.datetime.now() - t

    t = dt.datetime.now()
    print "Updating %d times......" % update_times
    for i in range(update_times):  #update 1000 times
        tweener.update(0.1)
    print dt.datetime.now() - t

########NEW FILE########
__FILENAME__ = stuff
# - coding: utf-8 -

# Copyright (C) 2008-2010, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


# some widgets that repeat all over the place
# cells, columns, trees and other

import logging
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango

from itertools import groupby
import datetime as dt
import calendar
import time
import re
import locale
import os

def format_duration(minutes, human = True):
    """formats duration in a human readable format.
    accepts either minutes or timedelta"""

    if isinstance(minutes, dt.timedelta):
        minutes = duration_minutes(minutes)

    if not minutes:
        if human:
            return ""
        else:
            return "00:00"

    hours = minutes / 60
    minutes = minutes % 60
    formatted_duration = ""

    if human:
        if minutes % 60 == 0:
            # duration in round hours
            formatted_duration += ("%dh") % (hours)
        elif hours == 0:
            # duration less than hour
            formatted_duration += ("%dmin") % (minutes % 60.0)
        else:
            # x hours, y minutes
            formatted_duration += ("%dh %dmin") % (hours, minutes % 60)
    else:
        formatted_duration += "%02d:%02d" % (hours, minutes)


    return formatted_duration


def format_range(start_date, end_date):
    dates_dict = dateDict(start_date, "start_")
    dates_dict.update(dateDict(end_date, "end_"))

    if start_date == end_date:
        # label of date range if looking on single day
        # date format for overview label when only single day is visible
        # Using python datetime formatting syntax. See:
        # http://docs.python.org/library/time.html#time.strftime
        title = start_date.strftime(("%B %d, %Y"))
    elif start_date.year != end_date.year:
        # label of date range if start and end years don't match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    elif start_date.month != end_date.month:
        # label of date range if start and end month do not match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    else:
        # label of date range for interval in same month
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

    return title



def week(view_date):
    # aligns start and end date to week
    start_date = view_date - dt.timedelta(view_date.weekday() + 1)
    start_date = start_date + dt.timedelta(locale_first_weekday())
    end_date = start_date + dt.timedelta(6)
    return start_date, end_date

def month(view_date):
    # aligns start and end date to month
    start_date = view_date - dt.timedelta(view_date.day - 1) #set to beginning of month
    first_weekday, days_in_month = calendar.monthrange(view_date.year, view_date.month)
    end_date = start_date + dt.timedelta(days_in_month - 1)
    return start_date, end_date


def duration_minutes(duration):
    """returns minutes from duration, otherwise we keep bashing in same math"""
    if isinstance(duration, list):
        res = dt.timedelta()
        for entry in duration:
            res += entry

        return duration_minutes(res)
    elif isinstance(duration, dt.timedelta):
        return duration.seconds / 60 + duration.days * 24 * 60
    else:
        return duration


def zero_hour(date):
    return dt.datetime.combine(date.date(), dt.time(0,0))

# it seems that python or something has bug of sorts, that breaks stuff for
# japanese locale, so we have this locale from and to ut8 magic in some places
# see bug 562298
def locale_from_utf8(utf8_str):
    try:
        retval = unicode (utf8_str, "utf-8").encode(locale.getpreferredencoding())
    except:
        retval = utf8_str
    return retval

def locale_to_utf8(locale_str):
    try:
        retval = unicode (locale_str, locale.getpreferredencoding()).encode("utf-8")
    except:
        retval = locale_str
    return retval

def locale_first_weekday():
    """figure if week starts on monday or sunday"""
    first_weekday = 6 #by default settle on monday

    try:
        process = os.popen("locale first_weekday week-1stday")
        week_offset, week_start = process.read().split('\n')[:2]
        process.close()
        week_start = dt.date(*time.strptime(week_start, "%Y%m%d")[:3])
        week_offset = dt.timedelta(int(week_offset) - 1)
        beginning = week_start + week_offset
        first_weekday = int(beginning.strftime("%w"))
    except:
        logging.warn("WARNING - Failed to get first weekday from locale")

    return first_weekday


def totals(iter, keyfunc, sumfunc):
    """groups items by field described in keyfunc and counts totals using value
       from sumfunc
    """
    data = sorted(iter, key=keyfunc)
    res = {}

    for k, group in groupby(data, keyfunc):
        res[k] = sum([sumfunc(entry) for entry in group])

    return res


def dateDict(date, prefix = ""):
    """converts date into dictionary, having prefix for all the keys"""
    res = {}

    res[prefix+"a"] = date.strftime("%a")
    res[prefix+"A"] = date.strftime("%A")
    res[prefix+"b"] = date.strftime("%b")
    res[prefix+"B"] = date.strftime("%B")
    res[prefix+"c"] = date.strftime("%c")
    res[prefix+"d"] = date.strftime("%d")
    res[prefix+"H"] = date.strftime("%H")
    res[prefix+"I"] = date.strftime("%I")
    res[prefix+"j"] = date.strftime("%j")
    res[prefix+"m"] = date.strftime("%m")
    res[prefix+"M"] = date.strftime("%M")
    res[prefix+"p"] = date.strftime("%p")
    res[prefix+"S"] = date.strftime("%S")
    res[prefix+"U"] = date.strftime("%U")
    res[prefix+"w"] = date.strftime("%w")
    res[prefix+"W"] = date.strftime("%W")
    res[prefix+"x"] = date.strftime("%x")
    res[prefix+"X"] = date.strftime("%X")
    res[prefix+"y"] = date.strftime("%y")
    res[prefix+"Y"] = date.strftime("%Y")
    res[prefix+"Z"] = date.strftime("%Z")

    for i, value in res.items():
        res[i] = locale_to_utf8(value)

    return res

def escape_pango(text):
    if not text:
        return text

    text = text.replace ("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

########NEW FILE########
__FILENAME__ = trophies
# - coding: utf-8 -

# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

"""Deal with trophies if there.
   For now the trophy configuration of hamster reside in gnome-achievements, in
   github:
   http://github.com/tbaugis/gnome-achievements/blob/master/data/achievements/hamster-time-tracker.trophies.xml
   Eventually they will move into hamster.
"""

try:
    from gnome_achievements import client as trophies_client
    storage = trophies_client.Storage()
except:
    storage = None

from hamster.lib import Fact
import stuff
import datetime as dt

def unlock(achievement_id):
    if not storage: return
    storage.unlock_achievement("hamster-time-tracker", achievement_id)

def check(achievement_id):
    if not storage: return None
    return storage.check_achievement("hamster-time-tracker", achievement_id)

def increment(counter_id, context = ""):
    if not storage: return 0
    return storage.increment_counter("hamster-time-tracker", counter_id, context)



def check_ongoing(todays_facts):
    if not storage or not todays_facts: return

    last_activity = None
    if todays_facts[-1].end_time is None:
        last_activity = todays_facts[-1]
        last_activity.delta = dt.datetime.now() - last_activity.start_time

    # overwhelmed: tracking for more than 16 hours during one day
    total = stuff.duration_minutes([fact.delta for fact in todays_facts])
    if total > 16 * 60:
        unlock("overwhelmed")

    if last_activity:
        # Welcome! – track an activity for 10 minutes
        if last_activity.delta >= dt.timedelta(minutes = 10):
            unlock("welcome")

        # in_the_zone - spend 6 hours non-stop on an activity
        if last_activity.delta >= dt.timedelta(hours = 6):
            unlock("in_the_zone")

        # insomnia - meet the new day while tracking an activity
        if last_activity.start_time.date() != dt.date.today():
            unlock("insomnia")


class Checker(object):
    def __init__(self):
        # use runtime flags where practical
        self.flags = {}


    def check_update_based(self, prev_id, new_id, fact):
        if not storage: return

        if not self.flags.get('last_update_id') or prev_id != self.flags['last_update_id']:
            self.flags['same_updates_in_row'] = 0
        elif self.flags['last_update_id'] == prev_id:
            self.flags['same_updates_in_row'] +=1
        self.flags['last_update_id'] = new_id


        # all wrong – edited same activity 5 times in a row
        if self.flags['same_updates_in_row'] == 5:
            unlock("all_wrong")


    def check_fact_based(self, fact):
        """quite possibly these all could be called from the service as
           there is bigger certainty as to what did actually happen"""

        # checks fact based trophies
        if not storage: return

        # explicit over implicit
        if not fact.activity:  # TODO - parse_activity could return None for these cases
            return

        # full plate - use all elements of syntax parsing
        derived_fact = Fact(fact.original_activity)
        if all((derived_fact.category, derived_fact.description,
                derived_fact.tags, derived_fact.start_time, derived_fact.end_time)):
            unlock("full_plate")


        # Jumper - hidden - made 10 switches within an hour (radical)
        if not fact.end_time: # end time normally denotes switch
            last_ten = self.flags.setdefault('last_ten_ongoing', [])
            last_ten.append(fact)
            last_ten = last_ten[-10:]

            if len(last_ten) == 10 and (last_ten[-1].start_time - last_ten[0].start_time) <= dt.timedelta(hours=1):
                unlock("jumper")

        # good memory - entered three past activities during a day
        if fact.end_time and fact.start_time.date() == dt.date.today():
            good_memory = increment("past_activities", dt.date.today().strftime("%Y%m%d"))
            if good_memory == 3:
                unlock("good_memory")

        # layering - entered 4 activities in a row in one of previous days, each one overlapping the previous one
        # avoiding today as in that case the layering might be automotical
        last_four = self.flags.setdefault('last_four', [])
        last_four.append(fact)
        last_four = last_four[-4:]
        if len(last_four) == 4:
            layered = True
            for prev, next in zip(last_four, last_four[1:]):
                if next.start_time.date() == dt.date.today() or \
                   next.start_time < prev.start_time or \
                   (prev.end_time and prev.end_time < next.start_time):
                    layered = False

            if layered:
                unlock("layered")

        # wait a minute! - Switch to a new activity within 60 seconds
        if len(last_four) >= 2:
            prev, next = last_four[-2:]
            if prev.end_time is None and next.end_time is None and (next.start_time - prev.start_time) < dt.timedelta(minutes = 1):
                unlock("wait_a_minute")


        # alpha bravo charlie – used delta times to enter at least 50 activities
        if fact.start_time and fact.original_activity.startswith("-"):
            counter = increment("hamster-time-tracker", "alpha_bravo_charlie")
            if counter == 50:
                unlock("alpha_bravo_charlie")


        # cryptic - hidden - used word shorter than 4 letters for the activity name
        if len(fact.activity) < 4:
            unlock("cryptic")

        # madness – hidden – entered an activity in all caps
        if fact.activity == fact.activity.upper():
            unlock("madness")

        # verbose - hidden - description longer than 5 words
        if fact.description and len([word for word in fact.description.split(" ") if len(word.strip()) > 2]) >= 5:
            unlock("verbose")

        # overkill - used 8 or more tags on a single activity
        if len(fact.tags) >=8:
            unlock("overkill")

        # ponies - hidden - discovered the ponies
        if fact.ponies:
            unlock("ponies")


        # TODO - after the trophies have been unlocked there is not much point in going on
        #        patrys complains about who's gonna garbage collect. should think
        #        about this
        if not check("ultra_focused"):
            activity_count = increment("hamster-time-tracker", "focused_%s@%s" % (fact.activity, fact.category or ""))
            # focused – 100 facts with single activity
            if activity_count == 100:
                unlock("focused")

            # ultra focused – 500 facts with single activity
            if activity_count == 500:
                unlock("ultra_focused")

        # elite - hidden - start an activity at 13:37
        if dt.datetime.now().hour == 13 and dt.datetime.now().minute == 37:
            unlock("elite")



checker = Checker()

########NEW FILE########
__FILENAME__ = overview
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import bisect
import datetime as dt
import itertools
import webbrowser

from collections import defaultdict

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
import cairo

import hamster.client
from hamster.lib import graphics
from hamster.lib import layout
from hamster import reports
from hamster.lib import stuff
from hamster import widgets

from hamster.lib.configuration import dialogs
from hamster.lib.configuration import Controller


from hamster.lib.pytweener import Easing

from widgets.dates import RangePick
from widgets.facttree import FactTree


class HeaderBar(gtk.HeaderBar):
    def __init__(self):
        gtk.HeaderBar.__init__(self)
        self.set_show_close_button(True)

        box = gtk.Box(False)
        time_back = gtk.Button.new_from_icon_name("go-previous-symbolic", gtk.IconSize.MENU)
        time_forth = gtk.Button.new_from_icon_name("go-next-symbolic", gtk.IconSize.MENU)

        box.add(time_back)
        box.add(time_forth)
        gtk.StyleContext.add_class(box.get_style_context(), "linked")
        self.pack_start(box)

        self.range_pick = RangePick(dt.datetime.today()) # TODO - use hamster day
        self.pack_start(self.range_pick)

        self.add_activity_button = gtk.Button()
        self.add_activity_button.set_image(gtk.Image.new_from_icon_name("list-add-symbolic",
                                                                        gtk.IconSize.MENU))
        self.pack_end(self.add_activity_button)

        self.search_button = gtk.ToggleButton()
        self.search_button.set_image(gtk.Image.new_from_icon_name("edit-find-symbolic",
                                                                  gtk.IconSize.MENU))
        self.pack_end(self.search_button)

        self.system_button = gtk.MenuButton()
        self.system_button.set_image(gtk.Image.new_from_icon_name("emblem-system-symbolic",
                                                                  gtk.IconSize.MENU))
        self.pack_end(self.system_button)

        self.system_menu = gtk.Menu()
        self.system_button.set_popup(self.system_menu)
        self.menu_export = gtk.MenuItem(label="Export...")
        self.system_menu.append(self.menu_export)
        self.menu_prefs = gtk.MenuItem(label="Tracking Settings")
        self.system_menu.append(self.menu_prefs)
        self.system_menu.show_all()


        time_back.connect("clicked", self.on_time_back_click)
        time_forth.connect("clicked", self.on_time_forth_click)
        self.connect("button-press-event", self.on_button_press)

    def on_button_press(self, bar, event):
        """swallow clicks on the interactive parts to avoid triggering
        switch to full-window"""
        return True

    def on_time_back_click(self, button):
        self.range_pick.prev_range()

    def on_time_forth_click(self, button):
        self.range_pick.next_range()


class StackedBar(layout.Widget):
    def __init__(self, width=0, height=0, vertical=None, **kwargs):
        layout.Widget.__init__(self, **kwargs)

        #: orientation, horizontal by default
        self.vertical = vertical or False

        #: allocated width
        self.width = width

        #: allocated height
        self.height = height

        self._items = []
        self.connect("on-render", self.on_render)

        #: color scheme to use, graphics.colors.category10 by default
        self.colors = graphics.Colors.category10
        self.colors = ["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"]

        self._seen_keys = []


    def set_items(self, items):
        """expects a list of key, value to work with"""
        res = []
        max_value = sum((rec[1] for rec in items))
        for key, val in items:
            res.append((key, val, val * 1.0 / max_value))
        self._items = res


    def _take_color(self, key):
        if key in self._seen_keys:
            index = self._seen_keys.index(key)
        else:
            self._seen_keys.append(key)
            index = len(self._seen_keys) - 1
        return self.colors[index % len(self.colors)]


    def on_render(self, sprite):
        if not self._items:
            self.graphics.clear()
            return

        max_width = self.alloc_w - 1 * len(self._items)
        for i, (key, val, normalized) in enumerate(self._items):
            color = self._take_color(key)

            width = int(normalized * max_width)
            self.graphics.rectangle(0, 0, width, self.height)
            self.graphics.fill(color)
            self.graphics.translate(width + 1, 0)


class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0, color=None, use_markup=False):
        self.x = x
        self.y = y
        self.color = color
        self.use_markup = use_markup

    def _set_text(self, text):
        if self.use_markup:
            self.layout.set_markup(text)
        else:
            self.layout.set_text(text, -1)

    def _show(self, g):
        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

    def show(self, g, text, x=0, y=0):
        g.save_context()
        g.move_to(x or self.x, y or self.y)
        self._set_text(text)
        self._show(g)
        g.restore_context()


class HorizontalBarChart(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.x_align = 0
        self.y_align = 0
        self.values = []

        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.label_height = self.layout.get_pixel_size()[1]

        self._max = 0

    def set_values(self, values):
        """expects a list of 2-tuples"""
        self.values = values
        self.height = len(self.values) * 14
        self._max = max(rec[1] for rec in values) if values else 0

    def _draw(self, context, opacity, matrix):
        g = graphics.Graphics(context)
        g.save_context()
        g.translate(self.x, self.y)

        for i, (label, value) in enumerate(self.values):
            g.set_color("#333")
            self.layout.set_markup(stuff.escape_pango(label))
            label_w, label_h = self.layout.get_pixel_size()

            y = int(i * label_h * 1.5)
            g.move_to(100 - label_w, y)
            pangocairo.show_layout(context, self.layout)

            w = (self.alloc_w - 110) * value.total_seconds() / self._max.total_seconds()
            w = max(1, int(round(w)))
            g.rectangle(110, y, int(w), int(label_h))
            g.fill("#999")

        g.restore_context()



class Totals(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_size_request(200, 70)
        self.category_totals = layout.Label(color=self._style.get_color(gtk.StateFlags.NORMAL),
                                            overflow=pango.EllipsizeMode.END,
                                            x_align=0,
                                            expand=False)
        self.stacked_bar = StackedBar(height=25, x_align=0, expand=False)

        box = layout.VBox(padding=10, spacing=5)
        self.add_child(box)

        box.add_child(self.category_totals, self.stacked_bar)

        self.totals = {}
        self.mouse_cursor = gdk.CursorType.HAND2

        self.instructions_label = layout.Label("Click to see stats",
                                               color=self._style.get_color(gtk.StateFlags.NORMAL),
                                               padding=10,
                                               expand=False)

        box.add_child(self.instructions_label)
        self.collapsed = True

        main = layout.HBox(padding_top=10)
        box.add_child(main)

        self.stub_label = layout.Label(markup="<b>Here be stats,\ntune in laters!</b>",
                                       color="#bbb",
                                       size=60)

        self.activities_chart = HorizontalBarChart()
        self.categories_chart = HorizontalBarChart()
        self.tag_chart = HorizontalBarChart()

        main.add_child(self.activities_chart, self.categories_chart, self.tag_chart)




        # for use in animation
        self.height_proxy = graphics.Sprite(x=0)
        self.height_proxy.height = 70
        self.add_child(self.height_proxy)

        self.connect("on-click", self.on_click)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)


    def set_facts(self, facts):
        totals = defaultdict(lambda: defaultdict(dt.timedelta))
        for fact in facts:
            for key in ('category', 'activity'):
                totals[key][getattr(fact, key)] += fact.delta

            for tag in fact.tags:
                totals["tag"][tag] += fact.delta


        for key, group in totals.iteritems():
            totals[key] = sorted(group.iteritems(), key=lambda x: x[1], reverse=True)
        self.totals = totals

        self.activities_chart.set_values(totals['activity'])
        self.categories_chart.set_values(totals['category'])
        self.tag_chart.set_values(totals['tag'])

        self.stacked_bar.set_items([(cat, delta.total_seconds() / 60.0) for cat, delta in totals['category']])
        self.category_totals.markup = ", ".join("<b>%s:</b> %s" % (stuff.escape_pango(cat), stuff.format_duration(hours)) for cat, hours in totals['category'])

    def on_click(self, scene, sprite, event):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.change_height(70)
            self.instructions_label.visible = True
            self.instructions_label.opacity = 0
            self.instructions_label.animate(opacity=1, easing=Easing.Expo.ease_in)
        else:
            self.change_height(300)
            self.instructions_label.visible = False

        self.mouse_cursor = gdk.CursorType.HAND2 if self.collapsed else None

    def on_mouse_enter(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(100)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())


    def on_mouse_leave(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(70)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())

    def change_height(self, new_height):
        self.stop_animation(self.height_proxy)
        def on_update_dummy(sprite):
            self.set_size_request(200, sprite.height)

        self.animate(self.height_proxy,
                     height=new_height,
                     on_update=on_update_dummy,
                     easing=Easing.Expo.ease_out)




class Overview(Controller):
    def __init__(self, parent = None):
        Controller.__init__(self, parent)

        self.window.set_position(gtk.WindowPosition.CENTER)
        self.window.set_default_icon_name("hamster-time-tracker")
        self.window.set_default_size(700, 500)

        self.storage = hamster.client.Storage()
        self.storage.connect("facts-changed", self.on_facts_changed)
        self.storage.connect("activities-changed", self.on_facts_changed)

        self.header_bar = HeaderBar()
        self.window.set_titlebar(self.header_bar)

        main = gtk.Box(orientation=1)
        self.window.add(main)

        self.report_chooser = None


        self.search_box = gtk.Revealer()

        space = gtk.Box(border_width=5)
        self.search_box.add(space)
        self.filter_entry = gtk.Entry()
        self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY,
                                                  "edit-find-symbolic")
        self.filter_entry.connect("changed", self.on_search_changed)
        self.filter_entry.connect("icon-press", self.on_search_icon_press)

        space.pack_start(self.filter_entry, True, True, 0)
        main.pack_start(self.search_box, False, True, 0)


        window = gtk.ScrolledWindow()
        window.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        self.fact_tree = FactTree()
        self.fact_tree.connect("on-activate-row", self.on_row_activated)
        self.fact_tree.connect("on-delete-called", self.on_row_delete_called)

        window.add(self.fact_tree)
        main.pack_start(window, True, True, 1)

        self.totals = Totals()
        main.pack_start(self.totals, False, True, 1)

        date_range = stuff.week(dt.datetime.today()) # TODO - do the hamster day
        self.header_bar.range_pick.set_range(*date_range)
        self.header_bar.range_pick.connect("range-selected", self.on_range_selected)
        self.header_bar.add_activity_button.connect("clicked", self.on_add_activity_clicked)
        self.header_bar.search_button.connect("toggled", self.on_search_toggled)

        self.header_bar.menu_prefs.connect("activate", self.on_prefs_clicked)
        self.header_bar.menu_export.connect("activate", self.on_export_clicked)


        self.window.connect("key-press-event", self.on_key_press)

        self.facts = []
        self.find_facts()
        self.window.show_all()


    def on_key_press(self, window, event):
        if self.filter_entry.has_focus():
            if event.keyval == gdk.KEY_Escape:
                self.filter_entry.set_text("")
                self.header_bar.search_button.set_active(False)
                return True
            elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down,
                                  gdk.KEY_Page_Up, gdk.KEY_Page_Down,
                                  gdk.KEY_Return):
                self.fact_tree.on_key_press(self, event)
                return True

        if self.fact_tree.has_focus() or self.totals.has_focus():
            if event.keyval == gdk.KEY_Tab:
                pass # TODO - deal with tab as our scenes eat up navigation

        if event.state & gdk.ModifierType.CONTROL_MASK:
            # the ctrl+things
            if event.keyval == gdk.KEY_f:
                self.header_bar.search_button.set_active(True)


    def find_facts(self):
        start, end = self.header_bar.range_pick.get_range()
        search_active = self.header_bar.search_button.get_active()
        search = "" if not search_active else self.filter_entry.get_text()
        search = "%s*" % search if search else "" # search anywhere

        self.facts = self.storage.get_facts(start, end, search_terms=search)
        self.fact_tree.set_facts(self.facts)
        self.totals.set_facts(self.facts)


    def on_range_selected(self, button, range_type, start, end):
        self.find_facts()

    def on_search_changed(self, entry):
        if entry.get_text():
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      "edit-clear-symbolic")
        else:
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      None)
        self.find_facts()

    def on_search_icon_press(self, entry, position, event):
        if position == gtk.EntryIconPosition.SECONDARY:
            self.filter_entry.set_text("")

    def on_facts_changed(self, event):
        self.find_facts()

    def on_add_activity_clicked(self, button):
        dialogs.edit.show(self)

    def on_row_activated(self, tree, day, fact):
        dialogs.edit.show(self, fact_date=fact.date, fact_id=fact.id)

    def on_row_delete_called(self, tree, fact):
        self.storage.remove_fact(fact.id)
        self.find_facts()

    def on_search_toggled(self, button):
        active = button.get_active()
        self.search_box.set_reveal_child(active)
        if active:
            self.filter_entry.grab_focus()


    def on_prefs_clicked(self, menu):
        dialogs.prefs.show(self)


    def on_export_clicked(self, menu):
        if self.report_chooser:
            self.report_chooser.present()
            return

        start, end = self.header_bar.range_pick.get_range()

        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, start, end, format, path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                try:
                    gtk.show_uri(gdk.Screen(), "file://%s" % os.path.split(path)[0], 0L)
                except:
                    pass # bug 626656 - no use in capturing this one i think

        def on_report_chooser_closed(widget):
            self.report_chooser = None


        self.report_chooser = widgets.ReportChooserDialog()
        self.report_chooser.connect("report-chosen", on_report_chosen)
        self.report_chooser.connect("report-chooser-closed", on_report_chooser_closed)
        self.report_chooser.show(start, end)

########NEW FILE########
__FILENAME__ = preferences
# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

import datetime as dt

from gettext import ngettext

from hamster.lib.configuration import Controller


def get_prev(selection, model):
    (model, iter) = selection.get_selected()

    #previous item
    path = model.get_path(iter)[0] - 1
    if path >= 0:
        return model.get_iter_from_string(str(path))
    else:
        return None

class CategoryStore(gtk.ListStore):
    def __init__(self):
        #id, name, color_code, order
        gtk.ListStore.__init__(self, int, str)

    def load(self):
        category_list = runtime.storage.get_categories()

        for category in category_list:
            self.append([category['id'], category['name']])

        self.unsorted_category = self.append([-1, _("Unsorted")]) # all activities without category


class ActivityStore(gtk.ListStore):
    def __init__(self):
        #id, name, category_id, order
        gtk.ListStore.__init__(self, int, str, int)

    def load(self, category_id):
        self.clear()

        if category_id is None:
            return

        activity_list = runtime.storage.get_category_activities(category_id)

        for activity in activity_list:
            self.append([activity['id'],
                         activity['name'],
                         activity['category_id']])


formats = ["fixed", "symbolic", "minutes"]
appearances = ["text", "icon", "both"]

from hamster.lib.configuration import runtime, conf
import widgets
from lib import stuff, trophies



class PreferencesEditor(Controller):
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TargetFlags.SAME_WIDGET, 0),
        ('MY_TREE_MODEL_ROW', gtk.TargetFlags.SAME_APP, 0),
        ]


    def __init__(self, parent = None):
        Controller.__init__(self, parent, ui_file="preferences.ui")
        # Translators: 'None' refers here to the Todo list choice in Hamster preferences (Tracking tab)
        self.activities_sources = [("", _("None")),
                                   ("evo", "Evolution"),
                                   ("gtg", "Getting Things Gnome")]
        self.todo_combo = gtk.ComboBoxText()
        for code, label in self.activities_sources:
            self.todo_combo.append_text(label)
        self.todo_combo.connect("changed", self.on_todo_combo_changed)
        self.get_widget("todo_pick").add(self.todo_combo)


        # create and fill activity tree
        self.activity_tree = self.get_widget('activity_list')
        self.get_widget("activities_label").set_mnemonic_widget(self.activity_tree)
        self.activity_store = ActivityStore()

        self.external_listeners = []

        self.activityColumn = gtk.TreeViewColumn(_("Name"))
        self.activityColumn.set_expand(True)
        self.activityCell = gtk.CellRendererText()
        self.external_listeners.extend([
            (self.activityCell, self.activityCell.connect('edited', self.activity_name_edited_cb, self.activity_store))
        ])
        self.activityColumn.pack_start(self.activityCell, True)
        self.activityColumn.set_attributes(self.activityCell, text=1)
        self.activityColumn.set_sort_column_id(1)
        self.activity_tree.append_column(self.activityColumn)

        self.activity_tree.set_model(self.activity_store)

        self.selection = self.activity_tree.get_selection()

        self.external_listeners.extend([
            (self.selection, self.selection.connect('changed', self.activity_changed, self.activity_store))
        ])


        # create and fill category tree
        self.category_tree = self.get_widget('category_list')
        self.get_widget("categories_label").set_mnemonic_widget(self.category_tree)
        self.category_store = CategoryStore()

        self.categoryColumn = gtk.TreeViewColumn(_("Category"))
        self.categoryColumn.set_expand(True)
        self.categoryCell = gtk.CellRendererText()

        self.external_listeners.extend([
            (self.categoryCell, self.categoryCell.connect('edited', self.category_edited_cb, self.category_store))
        ])

        self.categoryColumn.pack_start(self.categoryCell, True)
        self.categoryColumn.set_attributes(self.categoryCell, text=1)
        self.categoryColumn.set_sort_column_id(1)
        self.categoryColumn.set_cell_data_func(self.categoryCell, self.unsorted_painter)
        self.category_tree.append_column(self.categoryColumn)

        self.category_store.load()
        self.category_tree.set_model(self.category_store)

        selection = self.category_tree.get_selection()
        self.external_listeners.extend([
            (selection, selection.connect('changed', self.category_changed_cb, self.category_store))
        ])

        self.day_start = widgets.TimeInput(dt.time(5,30))
        self.get_widget("day_start_placeholder").add(self.day_start)


        self.load_config()

        # Allow enable drag and drop of rows including row move
        self.activity_tree.enable_model_drag_source(gdk.ModifierType.BUTTON1_MASK,
                                                    self.TARGETS,
                                                    gdk.DragAction.DEFAULT|
                                                    gdk.DragAction.MOVE)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                                  gdk.DragAction.MOVE)

        self.activity_tree.connect("drag_data_get", self.drag_data_get_data)

        self.category_tree.connect("drag_data_received", self.on_category_drop)

        #select first category
        selection = self.category_tree.get_selection()
        selection.select_path((0,))

        self.prev_selected_activity = None
        self.prev_selected_category = None

        self.external_listeners.extend([
            (self.day_start, self.day_start.connect("time-entered", self.on_day_start_changed))
        ])

        self.show()


    def show(self):
        self.get_widget("notebook1").set_current_page(0)
        self.window.show_all()


    def on_todo_combo_changed(self, combo):
        conf.set("activities_source", self.activities_sources[combo.get_active()][0])


    def load_config(self, *args):
        self.get_widget("shutdown_track").set_active(conf.get("stop_on_shutdown"))
        self.get_widget("idle_track").set_active(conf.get("enable_timeout"))
        self.get_widget("notify_interval").set_value(conf.get("notify_interval"))

        self.get_widget("notify_on_idle").set_active(conf.get("notify_on_idle"))
        self.get_widget("notify_on_idle").set_sensitive(conf.get("notify_interval") <=120)

        day_start = conf.get("day_start_minutes")
        day_start = dt.time(day_start / 60, day_start % 60)
        self.day_start.set_time(day_start)

        self.tags = [tag["name"] for tag in runtime.storage.get_tags(only_autocomplete=True)]
        self.get_widget("autocomplete_tags").set_text(", ".join(self.tags))


        current_source = conf.get("activities_source")
        for i, (code, label) in enumerate(self.activities_sources):
            if code == current_source:
                self.todo_combo.set_active(i)


    def on_autocomplete_tags_view_focus_out_event(self, view, event):
        buf = self.get_widget("autocomplete_tags")
        updated_tags = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0) \
                          .decode("utf-8")
        if updated_tags == self.tags:
            return

        self.tags = updated_tags

        runtime.storage.update_autocomplete_tags(updated_tags)


    def drag_data_get_data(self, treeview, context, selection, target_id,
                           etime):
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, 0) #get activity ID
        selection.set(selection.target, 0, str(data))

    def select_activity(self, id):
        model = self.activity_tree.get_model()
        i = 0
        for row in model:
            if row[0] == id:
                self.activity_tree.set_cursor((i, ))
            i += 1

    def select_category(self, id):
        model = self.category_tree.get_model()
        i = 0
        for row in model:
            if row[0] == id:
                self.category_tree.set_cursor((i, ))
            i += 1



    def on_category_list_drag_motion(self, treeview, drag_context, x, y, eventtime):
        self.prev_selected_category = None
        try:
            target_path, drop_position = treeview.get_dest_row_at_pos(x, y)
            model, source = treeview.get_selection().get_selected()

        except:
            return

        drop_yes = ("drop_yes", gtk.TARGET_SAME_APP, 0)
        drop_no = ("drop_no", gtk.TARGET_SAME_APP, 0)

        if drop_position != gtk.TREE_VIEW_DROP_AFTER and \
           drop_position != gtk.TREE_VIEW_DROP_BEFORE:
            treeview.enable_model_drag_dest(self.TARGETS, gdk.DragAction.MOVE)
        else:
            treeview.enable_model_drag_dest([drop_no], gdk.DragAction.MOVE)



    def on_category_drop(self, treeview, context, x, y, selection,
                                info, etime):
        model = self.category_tree.get_model()
        data = selection.data
        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            changed = runtime.storage.change_category(int(data), model[iter][0])

            context.finish(changed, True, etime)
        else:
            context.finish(False, True, etime)

        return

    # callbacks
    def category_edited_cb(self, cell, path, new_text, model):
        new_text = new_text.decode("utf-8")
        id = model[path][0]
        if id == -1:
            return False #ignoring unsorted category

        #look for dupes
        categories = runtime.storage.get_categories()
        for category in categories:
            if category['name'].lower() == new_text.lower():
                if id == -2: # that was a new category
                    self.category_store.remove(model.get_iter(path))
                self.select_category(category['id'])
                return False

        if id == -2: #new category
            id = runtime.storage.add_category(new_text)
            model[path][0] = id
        else:
            runtime.storage.update_category(id, new_text)

        model[path][1] = new_text


    def activity_name_edited_cb(self, cell, path, new_text, model):
        new_text = new_text.decode("utf-8")

        id = model[path][0]
        category_id = model[path][2]

        activities = runtime.storage.get_category_activities(category_id)
        prev = None
        for activity in activities:
            if id == activity['id']:
                prev = activity['name']
            else:
                # avoid two activities in same category with same name
                if activity['name'].lower() == new_text.lower():
                    if id == -1: # that was a new activity
                        self.activity_store.remove(model.get_iter(path))
                    self.select_activity(activity['id'])
                    return False

        if id == -1: #new activity -> add
            model[path][0] = runtime.storage.add_activity(new_text, category_id)
        else: #existing activity -> update
            new = new_text
            runtime.storage.update_activity(id, new, category_id)
            # size matters - when editing activity name just changed the case (bar -> Bar)
            if prev != new and prev.lower() == new.lower():
                trophies.unlock("size_matters")

        model[path][1] = new_text
        return True


    def category_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()
        id = 0
        if iter is None:
            self.activity_store.clear()
        else:
            self.prev_selected_activity = None

            id = model[iter][0]
            self.activity_store.load(model[iter][0])

        #start with nothing
        self.get_widget('activity_edit').set_sensitive(False)
        self.get_widget('activity_remove').set_sensitive(False)

        return True

    def _get_selected_category(self):
        selection = self.get_widget('category_list').get_selection()
        (model, iter) = selection.get_selected()

        return model[iter][0] if iter else None


    def activity_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        # treat any selected case
        unsorted_selected = self._get_selected_category() == -1
        self.get_widget('activity_edit').set_sensitive(iter != None)
        self.get_widget('activity_remove').set_sensitive(iter != None)


    def _del_selected_row(self, tree):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        removable_id = model[iter][0]
        model.remove(iter)
        return removable_id

    def unsorted_painter(self, column, cell, model, iter, data):
        cell_id = model.get_value(iter, 0)
        cell_text = model.get_value(iter, 1)
        if cell_id == -1:
            text = '<span color="#555" style="italic">%s</span>' % cell_text # TODO - should get color from theme
            cell.set_property('markup', text)
        else:
            cell.set_property('text', cell_text)

        return

    def on_activity_list_button_pressed(self, tree, event):
        self.activityCell.set_property("editable", False)


    def on_activity_list_button_released(self, tree, event):
        if event.button == 1 and tree.get_path_at_pos(int(event.x), int(event.y)):
            # Get treeview path.
            path, column, x, y = tree.get_path_at_pos(int(event.x), int(event.y))

            if self.prev_selected_activity == path:
                self.activityCell.set_property("editable", True)
                tree.set_cursor_on_cell(path, self.activityColumn, self.activityCell, True)

            self.prev_selected_activity = path

    def on_category_list_button_pressed(self, tree, event):
        self.activityCell.set_property("editable", False)

    def on_category_list_button_released(self, tree, event):
        if event.button == 1 and tree.get_path_at_pos(int(event.x), int(event.y)):
            # Get treeview path.
            path, column, x, y = tree.get_path_at_pos(int(event.x), int(event.y))

            if self.prev_selected_category == path and \
               self._get_selected_category() != -1: #do not allow to edit unsorted
                self.categoryCell.set_property("editable", True)
                tree.set_cursor_on_cell(path, self.categoryColumn, self.categoryCell, True)
            else:
                self.categoryCell.set_property("editable", False)


            self.prev_selected_category = path


    def on_activity_remove_clicked(self, button):
        self.remove_current_activity()

    def on_activity_edit_clicked(self, button):
        self.activityCell.set_property("editable", True)

        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)[0]
        self.activity_tree.set_cursor_on_cell(path, focus_column = self.activityColumn, start_editing = True)



    """keyboard events"""
    def on_activity_list_key_pressed(self, tree, event_key):
        key = event_key.keyval
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        if (event_key.keyval == gdk.KEY_Delete):
            self.remove_current_activity()

        elif key == gdk.KEY_F2 :
            self.activityCell.set_property("editable", True)
            path = model.get_path(iter)[0]
            tree.set_cursor_on_cell(path, focus_column = self.activityColumn, start_editing = True)

    def remove_current_activity(self):
        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        runtime.storage.remove_activity(model[iter][0])
        self._del_selected_row(self.activity_tree)


    def on_category_remove_clicked(self, button):
        self.remove_current_category()

    def on_category_edit_clicked(self, button):
        self.categoryCell.set_property("editable", True)

        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)[0]
        self.category_tree.set_cursor_on_cell(path, focus_column = self.categoryColumn, start_editing = True)


    def on_category_list_key_pressed(self, tree, event_key):
        key = event_key.keyval

        if self._get_selected_category() == -1:
            return #ignoring unsorted category

        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        if  key == gdk.KEY_Delete:
            self.remove_current_category()
        elif key == gdk.KEY_F2:
            self.categoryCell.set_property("editable", True)
            path = model.get_path(iter)[0]
            tree.set_cursor_on_cell(path, focus_column = self.categoryColumn, start_editing = True)

    def remove_current_category(self):
        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        id = model[iter][0]
        if id != -1:
            runtime.storage.remove_category(id)
            self._del_selected_row(self.category_tree)

    def on_preferences_window_key_press(self, widget, event):
        # ctrl+w means close window
        if (event.keyval == gdk.KEY_w \
            and event.state & gdk.ModifierType.CONTROL_MASK):
            self.close_window()

        # escape can mean several things
        if event.keyval == gdk.KEY_Escape:
            #check, maybe we are editing stuff
            if self.activityCell.get_property("editable"):
                self.activityCell.set_property("editable", False)
                return
            if self.categoryCell.get_property("editable"):
                self.categoryCell.set_property("editable", False)
                return

            self.close_window()

    """button events"""
    def on_category_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """

        new_category = self.category_store.insert_before(self.category_store.unsorted_category,
                                                         [-2, _(u"New category")])

        self.categoryCell.set_property("editable", True)
        self.category_tree.set_cursor_on_cell((len(self.category_tree.get_model()) - 2, ),
                                         focus_column = self.category_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)


    def on_activity_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()

        new_activity = self.activity_store.append([-1, _(u"New activity"), category_id])

        (model, iter) = self.selection.get_selected()

        self.activityCell.set_property("editable", True)
        self.activity_tree.set_cursor_on_cell(model.get_path(new_activity),
                                              focus_column = self.activity_tree.get_column(0),
                                              focus_cell = None,
                                              start_editing = True)

    def on_activity_remove_clicked(self, button):
        removable_id = self._del_selected_row(self.activity_tree)
        runtime.storage.remove_activity(removable_id)


    def on_shutdown_track_toggled(self, checkbox):
        conf.set("stop_on_shutdown", checkbox.get_active())

    def on_idle_track_toggled(self, checkbox):
        conf.set("enable_timeout", checkbox.get_active())

    def on_notify_on_idle_toggled(self, checkbox):
        conf.set("notify_on_idle", checkbox.get_active())

    def on_notify_interval_format_value(self, slider, value):
        if value <=120:
            # notify interval slider value label
            label = ngettext("%(interval_minutes)d minute",
                             "%(interval_minutes)d minutes",
                             value) % {'interval_minutes': value}
        else:
            # notify interval slider value label
            label = _(u"Never")

        return label

    def on_notify_interval_value_changed(self, scale):
        value = int(scale.get_value())
        conf.set("notify_interval", value)
        self.get_widget("notify_on_idle").set_sensitive(value <= 120)

    def on_day_start_changed(self, widget):
        day_start = self.day_start.get_time()
        if day_start is None:
            return

        day_start = day_start.hour * 60 + day_start.minute

        conf.set("day_start_minutes", day_start)



    def on_close_button_clicked(self, button):
        self.close_window()


    def close_window(self):
        if self.parent:
            for obj, handler in self.external_listeners:
                obj.disconnect(handler)

            self._gui = None
            self.wNameColumn = None
            self.categoryColumn = None

        Controller.close_window(self)

########NEW FILE########
__FILENAME__ = reports
# - coding: utf-8 -

# Copyright (C) 2008-2012 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2008 Nathan Samson <nathansamson at gmail dot com>
# Copyright (C) 2008 Giorgos Logiotatidis  <seadog at sealabs dot net>
# Copyright (C) 2012 Ted Smith <tedks at cs.umd.edu>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.
import os, sys
import datetime as dt
from xml.dom.minidom import Document
import csv
import copy
import itertools
import re
from string import Template

from hamster.lib.configuration import runtime
from hamster.lib import stuff, trophies
from hamster.lib.i18n import C_
try:
    import json
except ImportError:
    # fallback for python < 2.6
    json_dumps = lambda s: s
else:
    json_dumps = json.dumps

from calendar import timegm

from StringIO import StringIO

def simple(facts, start_date, end_date, format, path = None):
    facts = copy.deepcopy(facts) # dont want to do anything bad to the input
    report_path = stuff.locale_from_utf8(path)

    if format == "tsv":
        writer = TSVWriter(report_path)
    elif format == "xml":
        writer = XMLWriter(report_path)
    elif format == "ical":
        writer = ICalWriter(report_path)
    else: #default to HTML
        writer = HTMLWriter(report_path, start_date, end_date)

    writer.write_report(facts)

    # some assembly required - hidden - saved a report for single day
    if start_date == end_date:
        trophies.unlock("some_assembly_required")

    # I want this on my desk - generated over 10 different reports
    if trophies.check("on_my_desk") == False:
        current = trophies.increment("reports_generated")
        if current == 10:
            trophies.unlock("on_my_desk")

    return writer


class ReportWriter(object):
    #a tiny bit better than repeating the code all the time
    def __init__(self, path = None, datetime_format = "%Y-%m-%d %H:%M:%S"):
        self.file = open(path, "w") if path else StringIO()
        self.datetime_format = datetime_format

    def export(self):
        return self.file.getvalue()

    def write_report(self, facts):
        try:
            for fact in facts:
                fact.activity= fact.activity
                fact.description = (fact.description or u"")
                fact.category = (fact.category or _("Unsorted"))

                if self.datetime_format:
                    fact.start_time = fact.start_time.strftime(self.datetime_format)

                    if fact.end_time:
                        fact.end_time = fact.end_time.strftime(self.datetime_format)
                    else:
                        fact.end_time = ""

                fact.tags = ", ".join(fact.tags)

                self._write_fact(fact)

            self._finish(facts)
        finally:
            if isinstance(self.file, file):
                self.file.close()

    def _start(self, facts):
        raise NotImplementedError

    def _write_fact(self, fact):
        raise NotImplementedError

    def _finish(self, facts):
        raise NotImplementedError

class ICalWriter(ReportWriter):
    """a lame ical writer, could not be bothered with finding a library"""
    def __init__(self, path):
        ReportWriter.__init__(self, path, datetime_format = "%Y%m%dT%H%M%S")
        self.file.write("BEGIN:VCALENDAR\nVERSION:1.0\n")


    def _write_fact(self, fact):
        #for now we will skip ongoing facts
        if not fact.end_time: return

        if fact.category == _("Unsorted"):
            fact.category = None

        self.file.write("""BEGIN:VEVENT
CATEGORIES:%(category)s
DTSTART:%(start_time)s
DTEND:%(end_time)s
SUMMARY:%(activity)s
DESCRIPTION:%(description)s
END:VEVENT
""" % dict(fact))

    def _finish(self, facts):
        self.file.write("END:VCALENDAR\n")

class TSVWriter(ReportWriter):
    def __init__(self, path):
        ReportWriter.__init__(self, path)
        self.csv_writer = csv.writer(self.file, dialect='excel-tab')

        headers = [# column title in the TSV export format
                   _("activity"),
                   # column title in the TSV export format
                   _("start time"),
                   # column title in the TSV export format
                   _("end time"),
                   # column title in the TSV export format
                   _("duration minutes"),
                   # column title in the TSV export format
                   _("category"),
                   # column title in the TSV export format
                   _("description"),
                   # column title in the TSV export format
                   _("tags")]
        self.csv_writer.writerow([h for h in headers])

    def _write_fact(self, fact):
        fact.delta = stuff.duration_minutes(fact.delta)
        self.csv_writer.writerow([fact.activity,
                                  fact.start_time,
                                  fact.end_time,
                                  fact.delta,
                                  fact.category,
                                  fact.description,
                                  fact.tags])
    def _finish(self, facts):
        pass

class XMLWriter(ReportWriter):
    def __init__(self, path):
        ReportWriter.__init__(self, path)
        self.doc = Document()
        self.activity_list = self.doc.createElement("activities")

    def _write_fact(self, fact):
        activity = self.doc.createElement("activity")
        activity.setAttribute("name", fact.activity)
        activity.setAttribute("start_time", fact.start_time)
        activity.setAttribute("end_time", fact.end_time)
        activity.setAttribute("duration_minutes", str(stuff.duration_minutes(fact.delta)))
        activity.setAttribute("category", fact.category)
        activity.setAttribute("description", fact.description)
        activity.setAttribute("tags", fact.tags)
        self.activity_list.appendChild(activity)

    def _finish(self, facts):
        self.doc.appendChild(self.activity_list)
        self.file.write(self.doc.toxml())



class HTMLWriter(ReportWriter):
    def __init__(self, path, start_date, end_date):
        ReportWriter.__init__(self, path, datetime_format = None)
        self.start_date, self.end_date = start_date, end_date

        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))

        if start_date.year != end_date.year:
            self.title = _(u"Activity report for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            self.title = _(u"Activity report for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date == end_date:
            self.title = _(u"Activity report for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
        else:
            self.title = _(u"Activity report for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict


        # read the template, allow override
        self.override = os.path.exists(os.path.join(runtime.home_data_dir, "report_template.html"))
        if self.override:
            template = os.path.join(runtime.home_data_dir, "report_template.html")
        else:
            template = os.path.join(runtime.data_dir, "report_template.html")

        self.main_template = ""
        with open(template, 'r') as f:
            self.main_template =f.read()


        self.fact_row_template = self._extract_template('all_activities')

        self.by_date_row_template = self._extract_template('by_date_activity')

        self.by_date_template = self._extract_template('by_date')

        self.fact_rows = []

    def _extract_template(self, name):
        pattern = re.compile('<%s>(.*)</%s>' % (name, name), re.DOTALL)

        match = pattern.search(self.main_template)

        if match:
            self.main_template = self.main_template.replace(match.group(), "$%s_rows" % name)
            return match.groups()[0]

        return ""


    def _write_fact(self, fact):
        # no having end time is fine
        end_time_str, end_time_iso_str = "", ""
        if fact.end_time:
            end_time_str = fact.end_time.strftime('%H:%M')
            end_time_iso_str = fact.end_time.isoformat()

        category = ""
        if fact.category != _("Unsorted"): #do not print "unsorted" in list
            category = fact.category


        data = dict(
            date = fact.date.strftime(
                   # date column format for each row in HTML report
                   # Using python datetime formatting syntax. See:
                   # http://docs.python.org/library/time.html#time.strftime
                   C_("html report","%b %d, %Y")),
            date_iso = fact.date.isoformat(),
            activity = fact.activity,
            category = category,
            tags = fact.tags,
            start = fact.start_time.strftime('%H:%M'),
            start_iso = fact.start_time.isoformat(),
            end = end_time_str,
            end_iso = end_time_iso_str,
            duration = stuff.format_duration(fact.delta) or "",
            duration_minutes = "%d" % (stuff.duration_minutes(fact.delta)),
            duration_decimal = "%.2f" % (stuff.duration_minutes(fact.delta) / 60.0),
            description = fact.description or ""
        )
        self.fact_rows.append(Template(self.fact_row_template).safe_substitute(data))


    def _finish(self, facts):

        # group by date
        by_date = []
        for date, date_facts in itertools.groupby(facts, lambda fact:fact.date):
            by_date.append((date, [dict(fact) for fact in date_facts]))
        by_date = dict(by_date)

        date_facts = []
        date = self.start_date
        while date <= self.end_date:
            str_date = date.strftime(
                        # date column format for each row in HTML report
                        # Using python datetime formatting syntax. See:
                        # http://docs.python.org/library/time.html#time.strftime
                        C_("html report","%b %d, %Y"))
            date_facts.append([str_date, by_date.get(date, [])])
            date += dt.timedelta(days=1)


        data = dict(
            title = self.title,

            totals_by_day_title = _("Totals by Day"),
            activity_log_title = _("Activity Log"),
            totals_title = _("Totals"),

            activity_totals_heading = _("activities"),
            category_totals_heading = _("categories"),
            tag_totals_heading = _("tags"),

            show_prompt = _("Distinguish:"),

            header_date = _("Date"),
            header_activity = _("Activity"),
            header_category = _("Category"),
            header_tags = _("Tags"),
            header_start = _("Start"),
            header_end = _("End"),
            header_duration = _("Duration"),
            header_description = _("Description"),

            data_dir = runtime.data_dir,
            show_template = _("Show template"),
            template_instructions = _("You can override it by storing your version in %(home_folder)s") % {'home_folder': runtime.home_data_dir},

            start_date = timegm(self.start_date.timetuple()),
            end_date = timegm(self.end_date.timetuple()),
            facts = json_dumps([dict(fact) for fact in facts]),
            date_facts = json_dumps(date_facts),

            all_activities_rows = "\n".join(self.fact_rows)
        )

        for key, val in data.iteritems():
            if isinstance(val, basestring):
                data[key] = val.encode("utf-8")

        self.file.write(Template(self.main_template).safe_substitute(data))

        if self.override:
            # my report is better than your report - overrode and ran the default report
            trophies.unlock("my_report")

        return

########NEW FILE########
__FILENAME__ = db
# - coding: utf-8 -

# Copyright (C) 2007-2009, 2012, 2014 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


"""separate file for database operations"""
import logging

try:
    import sqlite3 as sqlite
except ImportError:
    try:
        logging.warn("Using sqlite2")
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        logging.error("Neither sqlite3 nor pysqlite2 found")
        raise

import os, time
import datetime
import storage
from shutil import copy as copyfile
import itertools
import datetime as dt
try:
    from gi.repository import Gio as gio
except ImportError:
    print "Could not import gio - requires pygobject. File monitoring will be disabled"
    gio = None

from hamster.lib import Fact
from hamster.lib import trophies

class Storage(storage.Storage):
    con = None # Connection will be created on demand
    def __init__(self, unsorted_localized="Unsorted", database_dir=None):
        """
        XXX - you have to pass in name for the uncategorized category
        Delayed setup so we don't do everything at the same time
        """
        storage.Storage.__init__(self)

        self._unsorted_localized = unsorted_localized

        self.__con = None
        self.__cur = None
        self.__last_etag = None


        self.db_path = self.__init_db_file(database_dir)

        if gio:
            # add file monitoring so the app does not have to be restarted
            # when db file is rewritten
            def on_db_file_change(monitor, gio_file, event_uri, event):
                if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
                    if gio_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE,
                                           gio.FileQueryInfoFlags.NONE,
                                           None).get_etag() == self.__last_etag:
                        # ours
                        return
                elif event == gio.FileMonitorEvent.CREATED:
                    # treat case when instead of a move, a remove and create has been performed
                    self.con = None

                if event in (gio.FileMonitorEvent.CHANGES_DONE_HINT, gio.FileMonitorEvent.CREATED):
                    print "DB file has been modified externally. Calling all stations"
                    self.dispatch_overwrite()

                    # plan "b" – synchronize the time tracker's database from external source while the tracker is running
                    if trophies:
                        trophies.unlock("plan_b")


            self.__database_file = gio.File.new_for_path(self.db_path)
            self.__db_monitor = self.__database_file.monitor_file(gio.FileMonitorFlags.WATCH_MOUNTS | \
                                                                  gio.FileMonitorFlags.SEND_MOVED | \
                                                                  gio.FileMonitorFlags.WATCH_HARD_LINKS,
                                                                  None)
            self.__db_monitor.connect("changed", on_db_file_change)

        self.run_fixtures()

    def __init_db_file(self, database_dir):
        if not database_dir:
            try:
                from xdg.BaseDirectory import xdg_data_home
                database_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster-applet"))
            except ImportError:
                print "Could not import xdg - will store hamster.db in home folder"
                database_dir = os.path.realpath(os.path.expanduser("~"))

        if not os.path.exists(database_dir):
            os.makedirs(database_dir, 0744)

        # handle the move to xdg_data_home
        old_db_file = os.path.expanduser("~/.gnome2/hamster-applet/hamster.db")
        new_db_file = os.path.join(database_dir, "hamster.db")
        if os.path.exists(old_db_file):
            if os.path.exists(new_db_file):
                logging.info("Have two database %s and %s" % (new_db_file, old_db_file))
            else:
                os.rename(old_db_file, new_db_file)

        db_path = os.path.join(database_dir, "hamster.db")

        # check if we have a database at all
        if not os.path.exists(db_path):
            # if not there, copy from the defaults
            try:
                from hamster import defs
                data_dir = os.path.join(defs.DATA_DIR, "hamster-time-tracker")
            except:
                # if defs is not there, we are running from sources
                module_dir = os.path.dirname(os.path.realpath(__file__))
                if os.path.exists(os.path.join(module_dir, "data")):
                    # running as flask app. XXX - detangle
                    data_dir = os.path.join(module_dir, "data")
                else:
                    data_dir = os.path.join(module_dir, '..', '..', 'data')

            data_dir = os.path.realpath(data_dir)

            logging.info("Database not found in %s - installing default from %s!" % (db_path, data_dir))
            copyfile(os.path.join(data_dir, 'hamster.db'), db_path)

            #change also permissions - sometimes they are 444
            os.chmod(db_path, 0664)

        return db_path


    def register_modification(self):
        if gio:
            # db.execute calls this so we know that we were the ones
            # that modified the DB and no extra refesh is not needed
            self.__last_etag = self.__database_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE,
                                                               gio.FileQueryInfoFlags.NONE,
                                                               None).get_etag()

    #tags, here we come!
    def __get_tags(self, only_autocomplete = False):
        if only_autocomplete:
            return self.fetchall("select * from tags where autocomplete != 'false' order by name")
        else:
            return self.fetchall("select * from tags order by name")

    def __get_tag_ids(self, tags):
        """look up tags by their name. create if not found"""

        db_tags = self.fetchall("select * from tags where name in (%s)"
                                            % ",".join(["?"] * len(tags)), tags) # bit of magic here - using sqlites bind variables

        changes = False

        # check if any of tags needs resurrection
        set_complete = [str(tag["id"]) for tag in db_tags if tag["autocomplete"] == "false"]
        if set_complete:
            changes = True
            self.execute("update tags set autocomplete='true' where id in (%s)" % ", ".join(set_complete))


        found_tags = [tag["name"] for tag in db_tags]

        add = set(tags) - set(found_tags)
        if add:
            statement = "insert into tags(name) values(?)"

            self.execute([statement] * len(add), [(tag,) for tag in add])

            return self.__get_tag_ids(tags)[0], True # all done, recurse
        else:
            return db_tags, changes

    def __update_autocomplete_tags(self, tags):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]  # split by comma

        #first we will create new ones
        tags, changes = self.__get_tag_ids(tags)
        tags = [tag["id"] for tag in tags]

        #now we will find which ones are gone from the list
        query = """
                    SELECT b.id as id, b.autocomplete, count(a.fact_id) as occurences
                      FROM tags b
                 LEFT JOIN fact_tags a on a.tag_id = b.id
                     WHERE b.id not in (%s)
                  GROUP BY b.id
                """ % ",".join(["?"] * len(tags)) # bit of magic here - using sqlites bind variables

        gone = self.fetchall(query, tags)

        to_delete = [str(tag["id"]) for tag in gone if tag["occurences"] == 0]
        to_uncomplete = [str(tag["id"]) for tag in gone if tag["occurences"] > 0 and tag["autocomplete"] == "true"]

        if to_delete:
            self.execute("delete from tags where id in (%s)" % ", ".join(to_delete))

        if to_uncomplete:
            self.execute("update tags set autocomplete='false' where id in (%s)" % ", ".join(to_uncomplete))

        return changes or len(to_delete + to_uncomplete) > 0

    def __get_categories(self):
        return self.fetchall("SELECT id, name FROM categories ORDER BY lower(name)")

    def __update_activity(self, id, name, category_id):
        query = """
                   UPDATE activities
                       SET name = ?,
                           search_name = ?,
                           category_id = ?
                     WHERE id = ?
        """
        self.execute(query, (name, name.lower(), category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        self.__remove_index(affected_ids)


    def __change_category(self, id, category_id):
        # first check if we don't have an activity with same name before us
        activity = self.fetchone("select name from activities where id = ?", (id, ))
        existing_activity = self.__get_activity_by_name(activity['name'], category_id)

        if existing_activity and id == existing_activity['id']: # we are already there, go home
            return False

        if existing_activity: #ooh, we have something here!
            # first move all facts that belong to movable activity to the new one
            update = """
                       UPDATE facts
                          SET activity_id = ?
                        WHERE activity_id = ?
            """

            self.execute(update, (existing_activity['id'], id))

            # and now get rid of our friend
            self.__remove_activity(id)

        else: #just moving
            statement = """
                       UPDATE activities
                          SET category_id = ?
                        WHERE id = ?
            """

            self.execute(statement, (category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        if existing_activity:
            affected_ids.extend([res[0] for res in self.fetchall("select id from facts where activity_id = ?", (existing_activity['id'],))])
        self.__remove_index(affected_ids)

        return True

    def __add_category(self, name):
        query = """
                   INSERT INTO categories (name, search_name)
                        VALUES (?, ?)
        """
        self.execute(query, (name, name.lower()))
        return self.__last_insert_rowid()

    def __update_category(self, id,  name):
        if id > -1: # Update, and ignore unsorted, if that was somehow triggered
            update = """
                       UPDATE categories
                           SET name = ?, search_name = ?
                         WHERE id = ?
            """
            self.execute(update, (name, name.lower(), id))

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]
        self.__remove_index(affected_ids)


    def __get_activity_by_name(self, name, category_id = None, resurrect = True):
        """get most recent, preferably not deleted activity by it's name"""

        if category_id:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                          AND category_id = ?
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """

            res = self.fetchone(query, (self._unsorted_localized, name, category_id))
        else:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """
            res = self.fetchone(query, (self._unsorted_localized, name, ))

        if res:
            keys = ('id', 'name', 'deleted', 'category')
            res = dict([(key, res[key]) for key in keys])
            res['deleted'] = res['deleted'] or False

            # if the activity was marked as deleted, resurrect on first call
            # and put in the unsorted category
            if res['deleted'] and resurrect:
                update = """
                            UPDATE activities
                               SET deleted = null, category_id = -1
                             WHERE id = ?
                        """
                self.execute(update, (res['id'], ))

            return res

        return None

    def __get_category_id(self, name):
        """returns category by it's name"""

        query = """
                   SELECT id from categories
                    WHERE lower(name) = lower(?)
                 ORDER BY id desc
                    LIMIT 1
        """

        res = self.fetchone(query, (name, ))

        if res:
            return res['id']

        return None

    def __get_fact(self, id):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category, coalesce(c.id, -1) as category_id,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE a.id = ?
                 ORDER BY e.name
        """

        return self.__group_tags(self.fetchall(query, (self._unsorted_localized, id)))[0]

    def __group_tags(self, facts):
        """put the fact back together and move all the unique tags to an array"""
        if not facts: return facts  #be it None or whatever

        grouped_facts = []
        for fact_id, fact_tags in itertools.groupby(facts, lambda f: f["id"]):
            fact_tags = list(fact_tags)

            # first one is as good as the last one
            grouped_fact = fact_tags[0]

            # we need dict so we can modify it (sqlite.Row is read only)
            # in python 2.5, sqlite does not have keys() yet, so we hardcode them (yay!)
            keys = ["id", "start_time", "end_time", "description", "name",
                    "activity_id", "category", "tag"]
            grouped_fact = dict([(key, grouped_fact[key]) for key in keys])

            grouped_fact["tags"] = [ft["tag"] for ft in fact_tags if ft["tag"]]
            grouped_facts.append(grouped_fact)
        return grouped_facts


    def __touch_fact(self, fact, end_time = None):
        end_time = end_time or dt.datetime.now()
        # tasks under one minute do not count
        if end_time - fact['start_time'] < datetime.timedelta(minutes = 1):
            self.__remove_fact(fact['id'])
        else:
            end_time = end_time.replace(microsecond = 0)
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (end_time, fact['id']))

    def __squeeze_in(self, start_time):
        """ tries to put task in the given date
            if there are conflicts, we will only truncate the ongoing task
            and replace it's end part with our activity """

        # we are checking if our start time is in the middle of anything
        # or maybe there is something after us - so we know to adjust end time
        # in the latter case go only few hours ahead. everything else is madness, heh
        query = """
                   SELECT a.*, b.name
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                    WHERE ((start_time < ? and end_time > ?)
                           OR (start_time > ? and start_time < ? and end_time is null)
                           OR (start_time > ? and start_time < ?))
                 ORDER BY start_time
                    LIMIT 1
                """
        fact = self.fetchone(query, (start_time, start_time,
                                     start_time - dt.timedelta(hours = 12),
                                     start_time, start_time,
                                     start_time + dt.timedelta(hours = 12)))
        end_time = None
        if fact:
            if start_time > fact["start_time"]:
                #we are in middle of a fact - truncate it to our start
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact["id"]))

            else: #otherwise we have found a task that is after us
                end_time = fact["start_time"]

        return end_time

    def __solve_overlaps(self, start_time, end_time):
        """finds facts that happen in given interval and shifts them to
        make room for new fact
        """
        if end_time is None or start_time is None:
            return

        # possible combinations and the OR clauses that catch them
        # (the side of the number marks if it catches the end or start time)
        #             |----------------- NEW -----------------|
        #      |--- old --- 1|   |2 --- old --- 1|   |2 --- old ---|
        # |3 -----------------------  big old   ------------------------ 3|
        query = """
                   SELECT a.*, b.name, c.name as category
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                LEFT JOIN categories c on b.category_id = c.id
                    WHERE (end_time > ? and end_time < ?)
                       OR (start_time > ? and start_time < ?)
                       OR (start_time < ? and end_time > ?)
                 ORDER BY start_time
                """
        conflicts = self.fetchall(query, (start_time, end_time,
                                          start_time, end_time,
                                          start_time, end_time))

        for fact in conflicts:
            # won't eliminate as it is better to have overlapping entries than loosing data
            if start_time < fact["start_time"] and end_time > fact["end_time"]:
                continue

            # split - truncate until beginning of new entry and create new activity for end
            if fact["start_time"] < start_time < fact["end_time"] and \
               fact["start_time"] < end_time < fact["end_time"]:

                logging.info("splitting %s" % fact["name"])
                # truncate until beginning of the new entry
                self.execute("""UPDATE facts
                                   SET end_time = ?
                                 WHERE id = ?""", (start_time, fact["id"]))
                fact_name = fact["name"]

                # create new fact for the end
                new_fact = Fact(fact["name"],
                                category = fact["category"],
                                description = fact["description"])
                new_fact_id = self.__add_fact(new_fact.serialized_name(), end_time, fact["end_time"])

                # copy tags
                tag_update = """INSERT INTO fact_tags(fact_id, tag_id)
                                     SELECT ?, tag_id
                                       FROM fact_tags
                                      WHERE fact_id = ?"""
                self.execute(tag_update, (new_fact_id, fact["id"])) #clone tags

                if trophies:
                    trophies.unlock("split")

            # overlap start
            elif start_time < fact["start_time"] < end_time:
                logging.info("Overlapping start of %s" % fact["name"])
                self.execute("UPDATE facts SET start_time=? WHERE id=?",
                             (end_time, fact["id"]))

            # overlap end
            elif start_time < fact["end_time"] < end_time:
                logging.info("Overlapping end of %s" % fact["name"])
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact["id"]))


    def __add_fact(self, serialized_fact, start_time, end_time = None, temporary = False):
        fact = Fact(serialized_fact,
                    start_time = start_time,
                    end_time = end_time)

        start_time = start_time or fact.start_time
        end_time = end_time or fact.end_time

        if not fact.activity or start_time is None:  # sanity check
            return 0


        # get tags from database - this will create any missing tags too
        tags = [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.get_tag_ids(fact.tags)]

        # now check if maybe there is also a category
        category_id = None
        if fact.category:
            category_id = self.__get_category_id(fact.category)
            if not category_id:
                category_id = self.__add_category(fact.category)

                if trophies:
                    trophies.unlock("no_hands")

        # try to find activity, resurrect if not temporary
        activity_id = self.__get_activity_by_name(fact.activity,
                                                  category_id,
                                                  resurrect = not temporary)
        if not activity_id:
            activity_id = self.__add_activity(fact.activity,
                                              category_id, temporary)
        else:
            activity_id = activity_id['id']

        # if we are working on +/- current day - check the last_activity
        if (dt.timedelta(days=-1) <= dt.datetime.now() - start_time <= dt.timedelta(days=1)):
            # pull in previous facts
            facts = self.__get_todays_facts()

            previous = None
            if facts and facts[-1]["end_time"] == None:
                previous = facts[-1]

            if previous and previous['start_time'] <= start_time:
                # check if maybe that is the same one, in that case no need to restart
                if previous["activity_id"] == activity_id \
                   and set(previous["tags"]) == set([tag[1] for tag in tags]) \
                   and (previous["description"] or "") == (fact.description or ""):
                    return None

                # if no description is added
                # see if maybe previous was too short to qualify as an activity
                if not previous["description"] \
                   and 60 >= (start_time - previous['start_time']).seconds >= 0:
                    self.__remove_fact(previous['id'])

                    # now that we removed the previous one, see if maybe the one
                    # before that is actually same as the one we want to start
                    # (glueing)
                    if len(facts) > 1 and 60 >= (start_time - facts[-2]['end_time']).seconds >= 0:
                        before = facts[-2]
                        if before["activity_id"] == activity_id \
                           and set(before["tags"]) == set([tag[1] for tag in tags]):
                            # resume and return
                            update = """
                                       UPDATE facts
                                          SET end_time = null
                                        WHERE id = ?
                            """
                            self.execute(update, (before["id"],))

                            return before["id"]
                else:
                    # otherwise stop
                    update = """
                               UPDATE facts
                                  SET end_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (start_time, previous["id"]))


        # done with the current activity, now we can solve overlaps
        if not end_time:
            end_time = self.__squeeze_in(start_time)
        else:
            self.__solve_overlaps(start_time, end_time)


        # finally add the new entry
        insert = """
                    INSERT INTO facts (activity_id, start_time, end_time, description)
                               VALUES (?, ?, ?, ?)
        """
        self.execute(insert, (activity_id, start_time, end_time, fact.description))

        fact_id = self.__last_insert_rowid()

        #now link tags
        insert = ["insert into fact_tags(fact_id, tag_id) values(?, ?)"] * len(tags)
        params = [(fact_id, tag[0]) for tag in tags]
        self.execute(insert, params)

        self.__remove_index([fact_id])
        return fact_id

    def __last_insert_rowid(self):
        return self.fetchone("SELECT last_insert_rowid();")[0]


    def __get_todays_facts(self):
        try:
            from hamster.lib.configuration import conf
            day_start = conf.get("day_start_minutes")
        except:
            day_start = 5 * 60 # default day start to 5am
        day_start = dt.time(day_start / 60, day_start % 60)
        today = (dt.datetime.now() - dt.timedelta(hours = day_start.hour,
                                                  minutes = day_start.minute)).date()
        return self.__get_facts(today)


    def __get_facts(self, date, end_date = None, search_terms = ""):
        try:
            from hamster.lib.configuration import conf
            day_start = conf.get("day_start_minutes")
        except:
            day_start = 5 * 60 # default day start to 5am
        day_start = dt.time(day_start / 60, day_start % 60)

        split_time = day_start
        datetime_from = dt.datetime.combine(date, split_time)

        end_date = end_date or date
        datetime_to = dt.datetime.combine(end_date, split_time) + dt.timedelta(days = 1)

        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE (a.end_time >= ? OR a.end_time IS NULL) AND a.start_time <= ?
        """

        if search_terms:
            # check if we need changes to the index
            self.__check_index(datetime_from, datetime_to)

            search_terms = search_terms.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').replace("'", "''")
            query += """ AND a.id in (SELECT id
                                        FROM fact_index
                                       WHERE fact_index MATCH '%s')""" % search_terms



        query += " ORDER BY a.start_time, e.name"

        facts = self.fetchall(query, (self._unsorted_localized,
                                      datetime_from,
                                      datetime_to))

        #first let's put all tags in an array
        facts = self.__group_tags(facts)

        res = []
        for fact in facts:
            # heuristics to assign tasks to proper days

            # if fact has no end time, set the last minute of the day,
            # or current time if fact has happened in last 12 hours
            if fact["end_time"]:
                fact_end_time = fact["end_time"]
            elif (dt.datetime.now().date() == fact["start_time"].date()) or \
                 (dt.datetime.now() - fact["start_time"]) <= dt.timedelta(hours=12):
                fact_end_time = dt.datetime.now().replace(microsecond = 0)
            else:
                fact_end_time = fact["start_time"]

            fact_start_date = fact["start_time"].date() \
                - dt.timedelta(1 if fact["start_time"].time() < split_time else 0)
            fact_end_date = fact_end_time.date() \
                - dt.timedelta(1 if fact_end_time.time() < split_time else 0)
            fact_date_span = fact_end_date - fact_start_date

            # check if the task spans across two dates
            if fact_date_span.days == 1:
                datetime_split = dt.datetime.combine(fact_end_date, split_time)
                start_date_duration = datetime_split - fact["start_time"]
                end_date_duration = fact_end_time - datetime_split
                if start_date_duration > end_date_duration:
                    # most of the task was done during the previous day
                    fact_date = fact_start_date
                else:
                    fact_date = fact_end_date
            else:
                # either doesn't span or more than 24 hrs tracked
                # (in which case we give up)
                fact_date = fact_start_date

            if fact_date < date or fact_date > end_date:
                # due to spanning we've jumped outside of given period
                continue

            fact["date"] = fact_date
            fact["delta"] = fact_end_time - fact["start_time"]
            res.append(fact)

        return res

    def __remove_fact(self, fact_id):
        statements = ["DELETE FROM fact_tags where fact_id = ?",
                      "DELETE FROM facts where id = ?"]
        self.execute(statements, [(fact_id,)] * 2)

        self.__remove_index([fact_id])

    def __get_category_activities(self, category_id):
        """returns list of activities, if category is specified, order by name
           otherwise - by activity_order"""
        query = """
                   SELECT a.id, a.name, a.category_id, b.name as category
                     FROM activities a
                LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                    WHERE category_id = ?
                      AND deleted is null
                 ORDER BY lower(a.name)
        """

        return self.fetchall(query, (category_id, ))


    def __get_activities(self, search):
        """returns list of activities for autocomplete,
           activity names converted to lowercase"""

        query = """
                   SELECT a.name AS name, b.name AS category
                     FROM activities a
                LEFT JOIN categories b ON coalesce(b.id, -1) = a.category_id
                LEFT JOIN facts f ON a.id = f.activity_id
                    WHERE deleted IS NULL
                      AND a.search_name LIKE ? ESCAPE '\\'
                 GROUP BY a.id
                 ORDER BY max(f.start_time) DESC, lower(a.name)
                    LIMIT 50
        """
        search = search.lower()
        search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        activities = self.fetchall(query, (u'%s%%' % search, ))

        return activities

    def __remove_activity(self, id):
        """ check if we have any facts with this activity and behave accordingly
            if there are facts - sets activity to deleted = True
            else, just remove it"""

        query = "select count(*) as count from facts where activity_id = ?"
        bound_facts = self.fetchone(query, (id,))['count']

        if bound_facts > 0:
            self.execute("UPDATE activities SET deleted = 1 WHERE id = ?", (id,))
        else:
            self.execute("delete from activities where id = ?", (id,))

        # Finished! - deleted an activity with more than 50 facts on it
        if trophies and bound_facts >= 50:
            trophies.unlock("finished")

    def __remove_category(self, id):
        """move all activities to unsorted and remove category"""

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]

        update = "update activities set category_id = -1 where category_id = ?"
        self.execute(update, (id, ))

        self.execute("delete from categories where id = ?", (id, ))

        self.__remove_index(affected_ids)


    def __add_activity(self, name, category_id = None, temporary = False):
        # first check that we don't have anything like that yet
        activity = self.__get_activity_by_name(name, category_id)
        if activity:
            return activity['id']

        #now do the create bit
        category_id = category_id or -1

        deleted = None
        if temporary:
            deleted = 1


        query = """
                   INSERT INTO activities (name, search_name, category_id, deleted)
                        VALUES (?, ?, ?, ?)
        """
        self.execute(query, (name, name.lower(), category_id, deleted))
        return self.__last_insert_rowid()

    def __remove_index(self, ids):
        """remove affected ids from the index"""
        if not ids:
            return

        ids = ",".join((str(id) for id in ids))
        self.execute("DELETE FROM fact_index where id in (%s)" % ids)


    def __check_index(self, start_date, end_date):
        """check if maybe index needs rebuilding in the time span"""
        index_query = """SELECT id
                           FROM facts
                          WHERE (end_time >= ? OR end_time IS NULL)
                            AND start_time <= ?
                            AND id not in(select id from fact_index)"""

        rebuild_ids = ",".join([str(res[0]) for res in self.fetchall(index_query, (start_date, end_date))])

        if rebuild_ids:
            query = """
                       SELECT a.id AS id,
                              a.start_time AS start_time,
                              a.end_time AS end_time,
                              a.description as description,
                              b.name AS name, b.id as activity_id,
                              coalesce(c.name, ?) as category,
                              e.name as tag
                         FROM facts a
                    LEFT JOIN activities b ON a.activity_id = b.id
                    LEFT JOIN categories c ON b.category_id = c.id
                    LEFT JOIN fact_tags d ON d.fact_id = a.id
                    LEFT JOIN tags e ON e.id = d.tag_id
                        WHERE a.id in (%s)
                     ORDER BY a.id
            """ % rebuild_ids

            facts = self.__group_tags(self.fetchall(query, (self._unsorted_localized, )))

            insert = """INSERT INTO fact_index (id, name, category, description, tag)
                             VALUES (?, ?, ?, ?, ?)"""
            params = [(fact['id'], fact['name'], fact['category'], fact['description'], " ".join(fact['tags'])) for fact in facts]

            self.executemany(insert, params)


    """ Here be dragons (lame connection/cursor wrappers) """
    def get_connection(self):
        if self.con is None:
            self.con = sqlite.connect(self.db_path, detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
            self.con.row_factory = sqlite.Row

        return self.con

    connection = property(get_connection, None)

    def fetchall(self, query, params = None):
        con = self.connection
        cur = con.cursor()

        logging.debug("%s %s" % (query, params))

        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        res = cur.fetchall()
        cur.close()

        return res

    def fetchone(self, query, params = None):
        res = self.fetchall(query, params)
        if res:
            return res[0]
        else:
            return None

    def execute(self, statement, params = ()):
        """
        execute sql statement. optionally you can give multiple statements
        to save on cursor creation and closure
        """
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        if isinstance(statement, list) == False: # we expect to receive instructions in list
            statement = [statement]
            params = [params]

        for state, param in zip(statement, params):
            logging.debug("%s %s" % (state, param))
            cur.execute(state, param)

        if not self.__con:
            con.commit()
            cur.close()
            self.register_modification()

    def executemany(self, statement, params = []):
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        logging.debug("%s %s" % (statement, params))
        cur.executemany(statement, params)

        if not self.__con:
            con.commit()
            cur.close()
            self.register_modification()



    def start_transaction(self):
        # will give some hints to execute not to close or commit anything
        self.__con = self.connection
        self.__cur = self.__con.cursor()

    def end_transaction(self):
        self.__con.commit()
        self.__cur.close()
        self.__con, self.__cur = None, None
        self.register_modification()

    def run_fixtures(self):
        self.start_transaction()

        """upgrade DB to hamster version"""
        version = self.fetchone("SELECT version FROM version")["version"]
        current_version = 9

        if version < 8:
            # working around sqlite's utf-f case sensitivity (bug 624438)
            # more info: http://www.gsak.net/help/hs23820.htm
            self.execute("ALTER TABLE activities ADD COLUMN search_name varchar2")

            activities = self.fetchall("select * from activities")
            statement = "update activities set search_name = ? where id = ?"
            for activity in activities:
                self.execute(statement, (activity['name'].lower(), activity['id']))

            # same for categories
            self.execute("ALTER TABLE categories ADD COLUMN search_name varchar2")
            categories = self.fetchall("select * from categories")
            statement = "update categories set search_name = ? where id = ?"
            for category in categories:
                self.execute(statement, (category['name'].lower(), category['id']))

        if version < 9:
            # adding full text search
            self.execute("""CREATE VIRTUAL TABLE fact_index
                                           USING fts3(id, name, category, description, tag)""")


        # at the happy end, update version number
        if version < current_version:
            #lock down current version
            self.execute("UPDATE version SET version = %d" % current_version)
            print "updated database from version %d to %d" % (version, current_version)

            # oldtimer – database version structure had been performed on startup (thus we know that user has been on at least 2 versions)
            if trophies:
                trophies.unlock("oldtimer")

        self.end_transaction()

########NEW FILE########
__FILENAME__ = storage
# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2007-2012 Toms Baugis <toms.baugis@gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import datetime as dt
from hamster.lib import Fact

class Storage(object):
    def run_fixtures(self):
        pass

    # signals that are called upon changes
    def tags_changed(self): pass
    def facts_changed(self): pass
    def activities_changed(self): pass

    def dispatch_overwrite(self):
        self.tags_changed()
        self.facts_changed()
        self.activities_changed()


    # facts
    def add_fact(self, fact, start_time, end_time, temporary = False):
        fact = Fact(fact, start_time = start_time, end_time = end_time)
        start_time = fact.start_time or dt.datetime.now().replace(second = 0, microsecond = 0)

        self.start_transaction()
        result = self.__add_fact(fact.serialized_name(), start_time, end_time, temporary)
        self.end_transaction()

        if result:
            self.facts_changed()
        return result

    def get_fact(self, fact_id):
        """Get fact by id. For output format see GetFacts"""
        return self.__get_fact(fact_id)


    def update_fact(self, fact_id, fact, start_time, end_time, temporary = False):
        self.start_transaction()
        self.__remove_fact(fact_id)
        result = self.__add_fact(fact, start_time, end_time, temporary)
        self.end_transaction()
        if result:
            self.facts_changed()
        return result


    def stop_tracking(self, end_time):
        """Stops tracking the current activity"""
        facts = self.__get_todays_facts()
        if facts and not facts[-1]['end_time']:
            self.__touch_fact(facts[-1], end_time)
            self.facts_changed()


    def remove_fact(self, fact_id):
        """Remove fact from storage by it's ID"""
        self.start_transaction()
        fact = self.__get_fact(fact_id)
        if fact:
            self.__remove_fact(fact_id)
            self.facts_changed()
        self.end_transaction()


    def get_facts(self, start_date, end_date, search_terms):
        return self.__get_facts(start_date, end_date, search_terms)


    def get_todays_facts(self):
        """Gets facts of today, respecting hamster midnight. See GetFacts for
        return info"""
        return self.__get_todays_facts()


    # categories
    def add_category(self, name):
        res = self.__add_category(name)
        self.activities_changed()
        return res

    def get_category_id(self, category):
        return self.__get_category_id(category)

    def update_category(self, id, name):
        self.__update_category(id, name)
        self.activities_changed()

    def remove_category(self, id):
        self.__remove_category(id)
        self.activities_changed()


    def get_categories(self):
        return self.__get_categories()


    # activities
    def add_activity(self, name, category_id = -1):
        new_id = self.__add_activity(name, category_id)
        self.activities_changed()
        return new_id

    def update_activity(self, id, name, category_id):
        self.__update_activity(id, name, category_id)
        self.activities_changed()

    def remove_activity(self, id):
        result = self.__remove_activity(id)
        self.activities_changed()
        return result

    def get_category_activities(self, category_id = -1):
        return self.__get_category_activities(category_id = category_id)

    def get_activities(self, search = ""):
        return self.__get_activities(search)

    def change_category(self, id, category_id):
        changed = self.__change_category(id, category_id)
        if changed:
            self.activities_changed()
        return changed

    def get_activity_by_name(self, activity, category_id, resurrect = True):
        category_id = category_id or None
        if activity:
            return dict(self.__get_activity_by_name(activity, category_id, resurrect) or {})
        else:
            return {}

    # tags
    def get_tags(self, only_autocomplete):
        return self.__get_tags(only_autocomplete)

    def get_tag_ids(self, tags):
        tags, new_added = self.__get_tag_ids(tags)
        if new_added:
            self.tags_changed()
        return tags

    def update_autocomplete_tags(self, tags):
        changes = self.__update_autocomplete_tags(tags)
        if changes:
            self.tags_changed()

########NEW FILE########
__FILENAME__ = activityentry
# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import bisect
import cairo
import datetime as dt
import re

from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
from collections import defaultdict

from hamster import client
from hamster.lib import Fact, looks_like_time
from hamster.lib import stuff
from hamster.lib import graphics




def extract_search(text):
    fact = Fact(text)
    search = fact.activity or ""
    if fact.category:
        search += "@%s" % fact.category
    if fact.tags:
        search += " #%s" % (" #".join(fact.tags))
    return search

class DataRow(object):
    """want to split out visible label, description, activity data
      and activity data with time (full_data)"""
    def __init__(self, label, data=None, full_data=None, description=None):
        self.label = label
        self.data = data or label
        self.full_data = full_data or data or label
        self.description = description or ""

class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.height = self.layout.get_pixel_size()[1]

    def show(self, g, text, color=None):
        g.move_to(self.x, self.y)

        self.layout.set_markup(text)
        g.save_context()
        if color:
            g.set_color(color)
        pangocairo.show_layout(g.context, self.layout)
        g.restore_context()


class CompleteTree(graphics.Scene):
    """
    ASCII Art

    | Icon | Activity - description |

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-select-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }


    def __init__(self):
        graphics.Scene.__init__(self, style_class=gtk.STYLE_CLASS_VIEW)

        self.set_can_focus(False)

        self.row_positions = []

        self.current_row = None
        self.rows = []

        self.style = self._style

        self.label = Label(x=5, y=3)
        self.row_height = self.label.height + 10

        self.connect("on-key-press", self.on_key_press)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)

    def _get_mouse_row(self, event):
        hover_row = None
        for row, y in zip(self.rows, self.row_positions):
            if y <= event.y <= (y + self.row_height):
                hover_row = row
                break
        return hover_row

    def on_mouse_move(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.current_row = row
            self.redraw()

    def on_mouse_down(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.set_current_row(self.rows.index(row))

    def on_key_press(self, scene, event):
        if event.keyval == gdk.KEY_Up:
            idx = self.rows.index(self.current_row) if self.current_row else 1
            self.set_current_row(idx - 1)

        elif event.keyval == gdk.KEY_Down:
            idx = self.rows.index(self.current_row) if self.current_row else -1
            self.set_current_row(idx + 1)

    def set_current_row(self, idx):
        idx = max(0, min(len(self.rows) - 1, idx))
        row = self.rows[idx]
        self.current_row = row
        self.redraw()
        self.emit("on-select-row", row)

    def set_rows(self, rows):
        self.current_row = None
        self.rows = rows
        self.set_row_positions()

    def set_row_positions(self):
        """creates a list of row positions for simpler manipulation"""
        self.row_positions = [i * self.row_height for i in range(len(self.rows))]
        self.set_size_request(0, self.row_positions[-1] + self.row_height if self.row_positions else 0)

    def on_enter_frame(self, scene, context):
        if not self.height:
            return

        colors = {
            "normal": self.style.get_color(gtk.StateFlags.NORMAL),
            "normal_bg": self.style.get_background_color(gtk.StateFlags.NORMAL),
            "selected": self.style.get_color(gtk.StateFlags.SELECTED),
            "selected_bg": self.style.get_background_color(gtk.StateFlags.SELECTED),
        }

        g = graphics.Graphics(context)
        g.set_line_style(1)
        g.translate(0.5, 0.5)


        for row, y in zip(self.rows, self.row_positions):
            g.save_context()
            g.translate(0, y)

            color, bg = colors["normal"], colors["normal_bg"]
            if row == self.current_row:
                color, bg = colors["selected"], colors["selected_bg"]
                g.fill_area(0, 0, self.width, self.row_height, bg)

            label = row.label
            if row.description:
                description_color = graphics.Colors.contrast(color, 50)
                description_color = graphics.Colors.hex(description_color)

                label += '<span color="%s"> - %s</span>' % (description_color, row.description)

            self.label.show(g, label, color=color)

            g.restore_context()



class ActivityEntry(gtk.Entry):
    def __init__(self, **kwargs):
        gtk.Entry.__init__(self)

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        box = gtk.Frame()
        box.set_shadow_type(gtk.ShadowType.IN)
        self.popup.add(box)

        self.complete_tree = CompleteTree()
        self.tree_checker = self.complete_tree.connect("on-select-row", self.on_tree_select_row)
        self.complete_tree.connect("on-click", self.on_tree_click)
        box.add(self.complete_tree)

        self.storage = client.Storage()
        self.load_suggestions()
        self.ignore_stroke = False

        self.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY, "go-down-symbolic")

        self.checker = self.connect("changed", self.on_changed)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("icon-press", self.on_icon_press)



    def on_changed(self, entry):
        text = self.get_text()

        with self.complete_tree.handler_block(self.tree_checker):
            self.show_suggestions(text)
            if self.complete_tree.rows:
                self.complete_tree.set_current_row(0)

        if self.ignore_stroke:
            self.ignore_stroke = False
            return

        def complete():
            text, suffix = self.complete_first()
            if suffix:
                #self.ignore_stroke = True
                with self.handler_block(self.checker):
                    self.update_entry("%s%s" % (text, suffix))
                    self.select_region(len(text), -1)
        gobject.timeout_add(0, complete)

    def on_focus_out(self, entry, event):
        self.popup.hide()

    def on_icon_press(self, entry, icon, event):
        self.show_suggestions("")

    def on_key_press(self, entry, event=None):
        if event.keyval in (gdk.KEY_BackSpace, gdk.KEY_Delete):
            self.ignore_stroke = True

        elif event.keyval in (gdk.KEY_Return, gdk.KEY_Escape):
            self.popup.hide()
            self.set_position(-1)

        elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down):
            if not self.popup.get_visible():
                self.show_suggestions(self.get_text())
            self.complete_tree.on_key_press(self, event)
            return True

    def on_tree_click(self, entry, tree, event):
        self.popup.hide()

    def on_tree_select_row(self, tree, row):
        with self.handler_block(self.checker):
            label = row.full_data
            self.update_entry(label)
            self.set_position(-1)


    def load_suggestions(self):
        self.todays_facts = self.storage.get_todays_facts()

        # list of facts of last month
        now = dt.datetime.now()
        last_month = self.storage.get_facts(now - dt.timedelta(days=30), now)

        # naive recency and frequency rank
        # score is as simple as you get 30-days_ago points for each occurence
        suggestions = defaultdict(int)
        for fact in last_month:
            days = 30 - (now - dt.datetime.combine(fact.date, dt.time())).total_seconds() / 60 / 60 / 24
            label = fact.activity
            if fact.category:
                label += "@%s" % fact.category

            suggestions[label] += days

            if fact.tags:
                label += " #%s" % (" #".join(fact.tags))
                suggestions[label] += days

        for rec in self.storage.get_activities():
            label = rec["name"]
            if rec["category"]:
                label += "@%s" % rec["category"]
            suggestions[label] += 0

        self.suggestions = sorted(suggestions.iteritems(), key=lambda x: x[1], reverse=True)

    def complete_first(self):
        text = self.get_text()
        fact, search = Fact(text), extract_search(text)
        if not self.complete_tree.rows or not fact.activity:
            return text, None

        label = self.complete_tree.rows[0].data
        if label.startswith(search):
            return text, label[len(search):]

        return text, None


    def update_entry(self, text):
        self.set_text(text or "")


    def update_suggestions(self, text=""):
        """
            * from previous activity | set time | minutes ago | start now
            * to ongoing | set time

            * activity
            * [@category]
            * #tags, #tags, #tags

            * we will leave description for later

            all our magic is space separated, strictly, start-end can be just dash

            phases:

            [start_time] | [-end_time] | activity | [@category] | [#tag]
        """
        now = dt.datetime.now()

        text = text.lstrip()

        time_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")
        time_range_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])-([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")
        delta_re = re.compile("^-[0-9]{1,3}$")

        # when the time is filled, we need to make sure that the chunks parse correctly



        delta_fragment_re = re.compile("^-[0-9]{0,3}$")


        templates = {
            "start_time": "",
            "start_delta": ("start activity -n minutes ago", "-"),
        }

        # need to set the start_time template before
        prev_fact = self.todays_facts[-1] if self.todays_facts else None
        if prev_fact and prev_fact.end_time:
            templates["start_time"] = ("from previous activity %s ago" % stuff.format_duration(now - prev_fact.end_time),
                                       prev_fact.end_time.strftime("%H:%M "))

        variants = []

        fact = Fact(text)

        # figure out what we are looking for
        # time -> activity[@category] -> tags -> description
        # presence of each next attribute means that we are not looking for the previous one
        # we still might be looking for the current one though
        looking_for = "start_time"
        fields = ["start_time", "end_time", "activity", "category", "tags", "description", "done"]
        for field in reversed(fields):
            if getattr(fact, field, None):
                looking_for = field
                if text[-1] == " ":
                    looking_for = fields[fields.index(field)+1]
                break


        fragments = [f for f in re.split("[\s|#]", text)]
        current_fragment = fragments[-1] if fragments else ""

        if not text.strip():
            variants = [templates[name] for name in ("start_time",
                                                     "start_delta") if templates[name]]
        elif looking_for == "start_time" and text == "-":
            if len(current_fragment) > 1: # avoid blank "-"
                templates["start_delta"] = ("%s minutes ago" % (-int(current_fragment)), current_fragment)
            variants.append(templates["start_delta"])


        res = []
        for (description, variant) in variants:
            res.append(DataRow(variant, description=description))

        # regular activity
        if (looking_for in ("start_time", "end_time") and not looks_like_time(text.split(" ")[-1])) or \
            looking_for in ("activity", "category"):

            search = extract_search(text)

            matches = []
            for match, score in self.suggestions:
                if search in match:
                    if match.startswith(search):
                        score += 10**8 # boost beginnings
                    matches.append((match, score))

            matches = sorted(matches, key=lambda x: x[1], reverse=True)[:7] # need to limit these guys, sorry

            for match, score in matches:
                label = (fact.start_time or now).strftime("%H:%M")
                if fact.end_time:
                    label += fact.end_time.strftime("-%H:%M")

                markup_label = label + " " + (stuff.escape_pango(match).replace(search, "<b>%s</b>" % search) if search else match)
                label += " " + match

                res.append(DataRow(markup_label, match, label))

        if not res:
            # in case of nothing to show, add preview so that the user doesn't
            # think they are lost
            label = (fact.start_time or now).strftime("%H:%M")
            if fact.end_time:
                label += fact.end_time.strftime("-%H:%M")

            if fact.activity:
                label += " " + fact.activity
            if fact.category:
                label += "@" + fact.category

            if fact.tags:
                label += " #" + " #".join(fact.tags)

            res.append(DataRow(stuff.escape_pango(label), description="Start tracking"))

        self.complete_tree.set_rows(res)


    def show_suggestions(self, text):
        if not self.get_window():
            return

        entry_alloc = self.get_allocation()
        entry_x, entry_y = self.get_window().get_origin()[1:]
        x, y = entry_x + entry_alloc.x, entry_y + entry_alloc.y + entry_alloc.height

        self.popup.show_all()

        self.update_suggestions(text)

        tree_w, tree_h = self.complete_tree.get_size_request()

        self.popup.move(x, y)
        self.popup.resize(entry_alloc.width, tree_h)
        self.popup.show_all()

########NEW FILE########
__FILENAME__ = dates
# - coding: utf-8 -

# Copyright (C) 2008-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
import datetime as dt
import calendar
import re


from hamster.lib import stuff
from hamster.lib.configuration import load_ui_file

class RangePick(gtk.ToggleButton):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        # day|week|month|manual, start, end
        'range-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    }


    def __init__(self, today):
        gtk.ToggleButton.__init__(self)

        self._ui = load_ui_file("date_range.ui")

        self.popup = self.get_widget("range_popup")

        self.today = today

        hbox = gtk.HBox()
        hbox.set_spacing(3)
        self.label = gtk.Label()
        hbox.add(self.label)
        hbox.add(gtk.Arrow(gtk.ArrowType.DOWN, gtk.ShadowType.ETCHED_IN))
        self.add(hbox)

        self.start_date, self.end_date = None, None
        self.current_range = None

        self.popup.connect("focus-out-event", self.on_focus_out)
        self.connect("toggled", self.on_toggle)

        self._ui.connect_signals(self)
        self.connect("destroy", self.on_destroy)
        self._hiding = False

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None
        self._ui = None

    def on_toggle(self, button):
        if self.get_active():
            if self._hiding:
                self._hiding = False
                self.set_active(False)
                return


            self.show()
        else:
            self.hide()


    def set_range(self, start_date, end_date=None):
        end_date = end_date or start_date
        self.start_date, self.end_date = start_date, end_date
        self.label.set_markup('<b>%s</b>' % stuff.format_range(start_date, end_date).encode("utf-8"))

    def get_range(self):
        return self.start_date, self.end_date

    def emit_range(self, range, start, end):
        self.set_range(start, end)
        self.emit("range-selected", range, start, end)
        self.hide()


    def prev_range(self):
        start, end = self.start_date, self.end_date

        if self.current_range == "day":
            start, end = start - dt.timedelta(1), end - dt.timedelta(1)
        elif self.current_range == "week":
            start, end = start - dt.timedelta(7), end - dt.timedelta(7)
        elif self.current_range == "month":
            end = start - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(end.year, end.month)
            start = end - dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (end - start) + dt.timedelta(days = 1)
            start = start - days
            end = end - days
        self.emit_range(self.current_range, start, end)


    def next_range(self):
        start, end = self.start_date, self.end_date

        if self.current_range == "day":
            start, end = start + dt.timedelta(1), end + dt.timedelta(1)
        elif self.current_range == "week":
            start, end = start + dt.timedelta(7), end + dt.timedelta(7)
        elif self.current_range == "month":
            start = end + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(start.year, start.month)
            end = start + dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (end - start) + dt.timedelta(days = 1)
            start = start + days
            end = end + days

        self.emit_range(self.current_range, start, end)



    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._ui.get_object(name)


    def on_focus_out(self, popup, event):
        x, y = self.get_pointer()
        button_w, button_h = self.get_allocation().width, self.get_allocation().height
        # avoid double-toggling when focus goes from window to the toggle button
        if 0 <= x <= button_w and 0 <= y <= button_h:
            self._hiding = True

        self.set_active(False)


    def hide(self):
        self.set_active(False)
        self.popup.hide()

    def show(self):
        dummy, x, y = self.get_window().get_origin()

        alloc = self.get_allocation()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)

        self.get_widget("day_preview").set_text(stuff.format_range(self.today, self.today))
        self.get_widget("week_preview").set_text(stuff.format_range(*stuff.week(self.today)))
        self.get_widget("month_preview").set_text(stuff.format_range(*stuff.month(self.today)))

        start_cal = self.get_widget("start_calendar")
        start_cal.select_month(self.start_date.month - 1, self.start_date.year)
        start_cal.select_day(self.start_date.day)

        end_cal = self.get_widget("end_calendar")
        end_cal.select_month(self.end_date.month - 1, self.end_date.year)
        end_cal.select_day(self.end_date.day)

        self.popup.show_all()
        self.get_widget("day").grab_focus()
        self.set_active(True)


    def on_day_clicked(self, button):
        self.current_range = "day"
        self.emit_range("day", self.today, self.today)

    def on_week_clicked(self, button):
        self.current_range = "week"
        self.start_date, self.end_date = stuff.week(self.today)
        self.emit_range("week", self.start_date, self.end_date)

    def on_month_clicked(self, button):
        self.current_range = "month"
        self.start_date, self.end_date = stuff.month(self.today)
        self.emit_range("month", self.start_date, self.end_date)

    def on_manual_range_apply_clicked(self, button):
        self.current_range = "manual"
        cal_date = self.get_widget("start_calendar").get_date()
        self.start_date = dt.datetime(cal_date[0], cal_date[1] + 1, cal_date[2])

        cal_date = self.get_widget("end_calendar").get_date()
        self.end_date = dt.datetime(cal_date[0], cal_date[1] + 1, cal_date[2])

        # make sure we always have a valid range
        if self.end_date < self.start_date:
            self.start_date, self.end_date = self.end_date, self.start_date

        self.emit_range("manual", self.start_date, self.end_date)

########NEW FILE########
__FILENAME__ = dayline
# -*- coding: utf-8 -*-

# Copyright (C) 2007-2010 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import time
import datetime as dt

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo

from hamster.lib import stuff, graphics, pytweener
from hamster.lib.configuration import conf


class Selection(graphics.Sprite):
    def __init__(self, start_time = None, end_time = None):
        graphics.Sprite.__init__(self, z_order = 100)
        self.start_time, self.end_time  = None, None
        self.width, self.height = None, None
        self.fill = None # will be set to proper theme color on render
        self.fixed = False

        self.start_label = graphics.Label("", 11, "#333", visible = False)
        self.end_label = graphics.Label("", 11, "#333", visible = False)
        self.duration_label = graphics.Label("", 11, "#FFF", visible = False)

        self.add_child(self.start_label, self.end_label, self.duration_label)
        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        if not self.fill: # not ready yet
            return

        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill_preserve(self.fill, 0.3)
        self.graphics.stroke(self.fill)


        # adjust labels
        self.start_label.visible = self.start_time is not None and self.start_time != self.end_time
        if self.start_label.visible:
            self.start_label.text = self.start_time.strftime("%H:%M")
            if self.x - self.start_label.width - 5 > 0:
                self.start_label.x = -self.start_label.width - 5
            else:
                self.start_label.x = 5

            self.start_label.y = self.height + 2

        self.end_label.visible = self.end_time is not None and self.start_time != self.end_time
        if self.end_label.visible:
            self.end_label.text = self.end_time.strftime("%H:%M")
            self.end_label.x = self.width + 5
            self.end_label.y = self.height + 2



            duration = self.end_time - self.start_time
            duration = int(duration.seconds / 60)
            self.duration_label.text =  "%02d:%02d" % (duration / 60, duration % 60)

            self.duration_label.visible = self.duration_label.width < self.width
            if self.duration_label.visible:
                self.duration_label.y = (self.height - self.duration_label.height) / 2
                self.duration_label.x = (self.width - self.duration_label.width) / 2
        else:
            self.duration_label.visible = False



class DayLine(graphics.Scene):
    def __init__(self, start_time = None):
        graphics.Scene.__init__(self)
        self.set_can_focus(False) # no interaction

        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        start_time = start_time or dt.datetime.now()

        self.view_time = start_time or dt.datetime.combine(start_time.date(), self.day_start)

        self.scope_hours = 24


        self.fact_bars = []
        self.categories = []

        self.connect("on-enter-frame", self.on_enter_frame)

        self.plot_area = graphics.Sprite(y=15)

        self.chosen_selection = Selection()
        self.plot_area.add_child(self.chosen_selection)

        self.drag_start = None
        self.current_x = None

        self.date_label = graphics.Label(color=self._style.get_color(gtk.StateFlags.NORMAL),
                                         x=5, y=16)

        self.add_child(self.plot_area, self.date_label)


    def plot(self, date, facts, select_start, select_end = None):
        for bar in self.fact_bars:
            self.plot_area.sprites.remove(bar)

        self.fact_bars = []
        for fact in facts:
            fact_bar = graphics.Rectangle(0, 0, fill="#aaa", stroke="#aaa") # dimensions will depend on screen situation
            fact_bar.fact = fact

            if fact.category in self.categories:
                fact_bar.category = self.categories.index(fact.category)
            else:
                fact_bar.category = len(self.categories)
                self.categories.append(fact.category)

            self.plot_area.add_child(fact_bar)
            self.fact_bars.append(fact_bar)

        self.view_time = dt.datetime.combine(date, self.day_start)
        self.date_label.text = self.view_time.strftime("%b %d")

        self.chosen_selection.start_time = select_start
        self.chosen_selection.end_time = select_end

        self.chosen_selection.width = None
        self.chosen_selection.fixed = True
        self.chosen_selection.visible = True

        self.redraw()


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        self.plot_area.height = self.height - 30


        vertical = min(self.plot_area.height / 5, 7)
        minute_pixel = (self.scope_hours * 60.0 - 15) / self.width

        g.set_line_style(width=1)
        g.translate(0.5, 0.5)


        colors = {
            "normal": self._style.get_color(gtk.StateFlags.NORMAL),
            "normal_bg": self._style.get_background_color(gtk.StateFlags.NORMAL),
            "selected": self._style.get_color(gtk.StateFlags.SELECTED),
            "selected_bg": self._style.get_background_color(gtk.StateFlags.SELECTED),
        }

        bottom = self.plot_area.y + self.plot_area.height

        for bar in self.fact_bars:
            bar.y = vertical * bar.category + 5
            bar.height = vertical

            bar_start_time = bar.fact.start_time - self.view_time
            minutes = bar_start_time.seconds / 60 + bar_start_time.days * self.scope_hours  * 60

            bar.x = round(minutes / minute_pixel) + 0.5
            bar.width = round((bar.fact.delta).seconds / 60 / minute_pixel)


        if self.chosen_selection.start_time and self.chosen_selection.width is None:
            # we have time but no pixels
            minutes = round((self.chosen_selection.start_time - self.view_time).seconds / 60 / minute_pixel) + 0.5
            self.chosen_selection.x = minutes
            if self.chosen_selection.end_time:
                self.chosen_selection.width = round((self.chosen_selection.end_time - self.chosen_selection.start_time).seconds / 60 / minute_pixel)
            else:
                self.chosen_selection.width = 0
            self.chosen_selection.height = self.chosen_selection.parent.height

            # use the oportunity to set proper colors too
            self.chosen_selection.fill = colors['selected_bg']
            self.chosen_selection.duration_label.color = colors['selected']




        #time scale
        g.set_color("#000")

        background = colors["normal_bg"]
        text = colors["normal"]

        tick_color = g.colors.contrast(background, 80)

        layout = g.create_layout(size = 10)
        for i in range(self.scope_hours * 60):
            time = (self.view_time + dt.timedelta(minutes=i))

            g.set_color(tick_color)
            if time.minute == 0:
                g.move_to(round(i / minute_pixel), bottom - 15)
                g.line_to(round(i / minute_pixel), bottom)
                g.stroke()
            elif time.minute % 15 == 0:
                g.move_to(round(i / minute_pixel), bottom - 5)
                g.line_to(round(i / minute_pixel), bottom)
                g.stroke()



            if time.minute == 0 and time.hour % 4 == 0:
                if time.hour == 0:
                    g.move_to(round(i / minute_pixel), self.plot_area.y)
                    g.line_to(round(i / minute_pixel), bottom)
                    label_minutes = time.strftime("%b %d")
                else:
                    label_minutes = time.strftime("%H<small><sup>%M</sup></small>")

                g.set_color(text)
                layout.set_markup(label_minutes)

                g.move_to(round(i / minute_pixel) + 2, 0)
                pangocairo.show_layout(context, layout)

        #current time
        if self.view_time < dt.datetime.now() < self.view_time + dt.timedelta(hours = self.scope_hours):
            minutes = round((dt.datetime.now() - self.view_time).seconds / 60 / minute_pixel)
            g.rectangle(minutes, 0, self.width, self.height)
            g.fill(colors['normal_bg'], 0.7)

            g.move_to(minutes, self.plot_area.y)
            g.line_to(minutes, bottom)
            g.stroke("#f00", 0.4)

########NEW FILE########
__FILENAME__ = facttree
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import bisect
import cairo
import datetime as dt

from collections import defaultdict

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango

from hamster.lib import graphics
from hamster.lib import stuff



class ActionRow(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self)
        self.visible = False

        self.restart = graphics.Icon("view-refresh-symbolic", size=18,
                                     interactive=True,
                                     mouse_cursor=gdk.CursorType.HAND1,
                                     y=4)
        self.add_child(self.restart)

        self.width = 50 # Simon says



class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0, color=None):
        self.x = x
        self.y = y
        self.color = color
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.height = self.layout.get_pixel_size()[1]

    def _set_text(self, text):
        self.layout.set_markup(text)

    def _show(self, g):
        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

    def show(self, g, text, x=0, y=0):
        g.save_context()
        g.move_to(x or self.x, y or self.y)
        self._set_text(text)
        self._show(g)
        g.restore_context()



class FactRow(object):
    def __init__(self):
        self.time_label = Label()
        self.activity_label = Label(x=100)

        self.category_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_size(10 * pango.SCALE)
        self.category_label.layout.set_font_description(fontdesc)


        self.description_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_style(pango.Style.ITALIC)
        self.description_label.layout.set_font_description(fontdesc)

        self.tag_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_size(8 * pango.SCALE)
        self.tag_label.layout.set_font_description(fontdesc)

        self.duration_label = Label()
        self.duration_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.duration_label.layout.set_width(90 * pango.SCALE)

        self.width = 0


    def height(self, fact):
        res = self.activity_label.height + 2 * 3
        if fact.description:
            res += self.description_label.height

        if fact.tags:
            res += self.tag_label.height + 5

        return res


    def _show_tags(self, g, tags, color, bg):
        label = self.tag_label
        label.color = bg

        g.save_context()
        g.translate(2.5, 2.5)
        for tag in tags:
            label._set_text(tag)
            w, h = label.layout.get_pixel_size()
            g.rectangle(0, 0, w + 6, h + 5, 2)
            g.fill(color, 0.5)
            g.move_to(3, 2)
            label._show(g)

            g.translate(w + 10, 0)

        g.restore_context()



    def show(self, g, colors, fact, current=False):
        g.save_context()

        color, bg = colors["normal"], colors["normal_bg"]
        if current:
            color, bg = colors["selected"], colors["selected_bg"]
            g.fill_area(0, 0, self.width, self.height(fact), bg)

        g.translate(5, 2)

        time_label = fact.start_time.strftime("%H:%M -")
        if fact.end_time:
            time_label += fact.end_time.strftime(" %H:%M")

        g.set_color(color)
        self.time_label.show(g, time_label)

        self.activity_label.show(g, stuff.escape_pango(fact.activity))
        if fact.category:
            g.save_context()
            g.set_color(color if current else "#999")
            x = self.activity_label.x + self.activity_label.layout.get_pixel_size()[0]
            self.category_label.show(g, "  - %s" % stuff.escape_pango(fact.category), x=x, y=2)
            g.restore_context()

        if fact.description or fact.tags:
            g.save_context()
            g.translate(self.activity_label.x, self.activity_label.height + 3)

            if fact.tags:
                self._show_tags(g, fact.tags, color, bg)
                g.translate(0, self.tag_label.height + 5)

            if fact.description:
                self.description_label.show(g, "<small>%s</small>" % fact.description)
            g.restore_context()

        self.duration_label.show(g, stuff.format_duration(fact.delta), x=self.width - 105)

        g.restore_context()




class FactTree(graphics.Scene, gtk.Scrollable):
    """
    The fact tree is a painter - it maintains scroll state and shows what we can
    see. That means it does not show all the facts there are, but rather only
    those tht you can see.
    It's also painter as it reuses labels. Caching is futile, we do all the painting
    every tie



    ASCII Art!
    | Weekday    | Start - End | Activity - category   [actions]| Duration |
    | Month, Day |             | tags, description              |          |
    |            | Start - End | Activity - category            | Duration |

    Inline edit?

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-activate-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'on-delete-called': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }



    hadjustment = gobject.property(type=gtk.Adjustment, default=None)
    hscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)
    vadjustment = gobject.property(type=gtk.Adjustment, default=None)
    vscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)

    def __init__(self):
        graphics.Scene.__init__(self, style_class=gtk.STYLE_CLASS_VIEW)

        self.date_label = Label(10, 3)
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_weight(pango.Weight.BOLD)
        self.date_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.date_label.layout.set_width(80 * pango.SCALE)
        self.date_label.layout.set_font_description(fontdesc)

        self.fact_row = FactRow()

        self.action_row = ActionRow()
        #self.add_child(self.action_row)

        self.row_positions = []
        self.row_heights = []

        self.y = 0
        self.day_padding = 20

        self.hover_day = None
        self.hover_fact = None
        self.current_fact = None

        self.style = self._style

        self.visible_range = None
        self.set_size_request(500, 400)

        self.connect("on-mouse-scroll", self.on_scroll)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)

        self.connect("on-resize", self.on_resize)
        self.connect("on-key-press", self.on_key_press)
        self.connect("notify::vadjustment", self._on_vadjustment_change)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-double-click", self.on_double_click)


    def on_mouse_down(self, scene, event):
        self.grab_focus()
        if self.hover_fact:
            self.set_current_fact(self.facts.index(self.hover_fact))


    def activate_row(self, day, fact):
        self.emit("on-activate-row", day, fact)

    def delete_row(self, fact):
        if fact:
            self.emit("on-delete-called", fact)

    def on_double_click(self, scene, event):
        if self.hover_fact:
            self.activate_row(self.hover_day, self.hover_fact)

    def on_key_press(self, scene, event):
        if event.keyval == gdk.KEY_Up:
            idx = self.facts.index(self.current_fact) if self.current_fact else 1
            self.set_current_fact(idx - 1)

        elif event.keyval == gdk.KEY_Down:
            idx = self.facts.index(self.current_fact) if self.current_fact else -1
            self.set_current_fact(idx + 1)

        elif event.keyval == gdk.KEY_Page_Down:
            self.y += self.height * 0.8
            self.on_scroll()

        elif event.keyval == gdk.KEY_Page_Up:
            self.y -= self.height * 0.8
            self.on_scroll()

        elif event.keyval == gdk.KEY_Return:
            self.activate_row(self.hover_day, self.current_fact)

        elif event.keyval == gdk.KEY_Delete:
            self.delete_row(self.current_fact)


    def set_current_fact(self, idx):
        idx = max(0, min(len(self.facts) - 1, idx))
        fact = self.facts[idx]
        self.current_fact = fact

        if fact.y < self.y:
            self.y = fact.y
        if (fact.y + 25) > (self.y + self.height):
            self.y = fact.y - self.height + 25

        self.on_scroll()


    def get_visible_range(self):
        start, end = (bisect.bisect(self.row_positions, self.y) - 1,
                      bisect.bisect(self.row_positions, self.y + self.height))

        y = self.y
        return [{"i": start + i, "y": pos - y, "h": height, "day": day, "facts": facts}
                    for i, (pos, height, (day, facts)) in enumerate(zip(self.row_positions[start:end],
                                                                        self.row_heights[start:end],
                                                                        self.days[start:end]))]


    def on_mouse_move(self, tree, event):
        hover_day, hover_fact = None, None

        for rec in self.visible_range:
            if rec['y'] <= event.y <= (rec['y'] + rec['h']):
                hover_day = rec
                break

        blank_day = hover_day and not hover_day.get('facts')

        if self.hover_day:
            for fact in self.hover_day.get('facts', []):
                if (fact.y - self.y) <= event.y <= (fact.y - self.y + fact.height):
                    hover_fact = fact
                    break

        if hover_day != self.hover_day:
            self.hover_day = hover_day
            self.redraw()

        if hover_fact != self.hover_fact:
            self.hover_fact = hover_fact
            self.move_actions()

    def move_actions(self):
        if self.hover_fact:
            self.action_row.visible = True
            self.action_row.x = self.width - 80 - self.action_row.width
            self.action_row.y = self.hover_fact.y - self.y
        else:
            self.action_row.visible = False


    def _on_vadjustment_change(self, scene, vadjustment):
        if not self.vadjustment:
            return
        self.vadjustment.connect("value_changed", self.on_scroll_value_changed)
        self.set_size_request(500, 300)


    def set_facts(self, facts):
        current_fact, current_date = self.current_fact, self.hover_day

        self.y = 0
        self.hover_fact = None
        if self.vadjustment:
            self.vadjustment.set_value(0)

        if facts:
            start, end = facts[0].date, facts[-1].date
            self.current_fact = facts[0]
        else:
            start = end = dt.datetime.now()
            self.current_fact = None

        by_date = defaultdict(list)
        for fact in facts:
            by_date[fact.date].append(fact)

        days = []
        for i in range((end-start).days + 1):
            current_date = start + dt.timedelta(days=i)
            days.append((current_date, by_date[current_date]))

        self.days = days
        self.facts = facts

        self.set_row_heights()

        if self.height:
            if current_fact:
                fact_ids = [fact.id for fact in facts]
                if current_fact.id in fact_ids:
                    self.set_current_fact(fact_ids.index(current_fact.id))

            elif current_date:
                for i, fact in enumerate(facts):
                    if fact.date == current_date:
                        self.set_current_fact(i)
                        break

            self.on_scroll()


    def set_row_heights(self):
        """
            the row height is defined by following factors:
                * how many facts are there in the day
                * does the fact have description / tags

            This func creates a list of row start positions to be able to
            quickly determine what to display
        """
        if not self.height:
            return

        y, pos, heights = 0, [], []

        for date, facts in self.days:
            height = 0
            for fact in facts:
                fact_height = self.fact_row.height(fact)
                fact.y = y + height
                fact.height = fact_height

                height += fact.height

            height += self.day_padding

            if not facts:
                height = 10
            else:
                height = max(height, 60)

            pos.append(y)
            heights.append(height)
            y += height


        self.row_positions, self.row_heights = pos, heights

        maxy = max(y, 1)

        self.vadjustment.set_lower(0)
        self.vadjustment.set_upper(max(maxy, self.height))
        self.vadjustment.set_page_size(self.height)


    def on_resize(self, scene, event):
        self.set_row_heights()
        self.fact_row.width = self.width - 105
        self.on_scroll()


    def on_scroll_value_changed(self, scroll):
        self.y = int(scroll.get_value())
        self.on_scroll()


    def on_scroll(self, scene=None, event=None):
        y_pos = self.y
        direction = 0
        if event and event.direction == gdk.ScrollDirection.UP:
            direction = -1
        elif event and event.direction == gdk.ScrollDirection.DOWN:
            direction = 1

        y_pos += 15 * direction
        y_pos = max(0, min(self.vadjustment.get_upper() - self.height, y_pos))
        self.vadjustment.set_value(y_pos)
        self.y = y_pos

        self.move_actions()
        self.redraw()

        self.visible_range = self.get_visible_range()


    def on_enter_frame(self, scene, context):
        has_focus = self.get_toplevel().has_toplevel_focus()
        if has_focus:
            colors = {
                "normal": self.style.get_color(gtk.StateFlags.NORMAL),
                "normal_bg": self.style.get_background_color(gtk.StateFlags.NORMAL),
                "selected": self.style.get_color(gtk.StateFlags.SELECTED),
                "selected_bg": self.style.get_background_color(gtk.StateFlags.SELECTED),
            }
        else:
            colors = {
                "normal": self.style.get_color(gtk.StateFlags.BACKDROP),
                "normal_bg": self.style.get_background_color(gtk.StateFlags.BACKDROP),
                "selected": self.style.get_color(gtk.StateFlags.BACKDROP),
                "selected_bg": self.style.get_background_color(gtk.StateFlags.BACKDROP),
            }


        if not self.height:
            return

        g = graphics.Graphics(context)

        g.set_line_style(1)
        g.translate(0.5, 0.5)

        g.fill_area(0, 0, 105, self.height, "#dfdfdf")


        y = int(self.y)

        for rec in self.visible_range:
            g.save_context()
            g.translate(0, rec['y'])

            if not rec['facts']:
                "do a collapsy thing"
                g.rectangle(0, 0, self.width, 10)
                g.clip()
                g.rectangle(0, 0, self.width, 10)
                g.fill("#eee")

                g.move_to(0, 0)
                g.line_to(self.width, 0)
                g.stroke("#ccc")
                g.restore_context()
                continue


            g.set_color(colors["normal"])
            self.date_label.show(g, rec['day'].strftime("%A\n%b %d"))

            g.translate(105, 0)
            for fact in rec['facts']:
                self.fact_row.show(g, colors, fact, fact==self.current_fact)
                g.translate(0, self.fact_row.height(fact))


            g.restore_context()

########NEW FILE########
__FILENAME__ = reportchooserdialog
# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


import pygtk
pygtk.require('2.0')

import os
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from hamster.lib.configuration import conf

class ReportChooserDialog(gtk.Dialog):
    __gsignals__ = {
        # format, path, start_date, end_date
        'report-chosen': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, gobject.TYPE_STRING)),
        'report-chooser-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self):
        gtk.Dialog.__init__(self)


        self.dialog = gtk.FileChooserDialog(title = _(u"Save Report — Time Tracker"),
                                            parent = self,
                                            action = gtk.FileChooserAction.SAVE,
                                            buttons=(gtk.STOCK_CANCEL,
                                                     gtk.ResponseType.CANCEL,
                                                     gtk.STOCK_SAVE,
                                                     gtk.ResponseType.OK))

        # try to set path to last known folder or fall back to home
        report_folder = os.path.expanduser(conf.get("last_report_folder"))
        if os.path.exists(report_folder):
            self.dialog.set_current_folder(report_folder)
        else:
            self.dialog.set_current_folder(os.path.expanduser("~"))

        self.filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        self.filters[filter] = "html"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab-Separated Values (TSV)"))
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.tsv")
        filter.add_pattern("*.txt")
        self.filters[filter] = "tsv"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("XML"))
        filter.add_mime_type("text/xml")
        filter.add_pattern("*.xml")
        self.filters[filter] = "xml"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("iCal"))
        filter.add_mime_type("text/calendar")
        filter.add_pattern("*.ics")
        self.filters[filter] = "ical"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.dialog.add_filter(filter)


    def show(self, start_date, end_date):
        """setting suggested name to something readable, replace backslashes
           with dots so the name is valid in linux"""

        # title in the report file name
        vars = {"title": _("Time track"),
                "start": start_date.strftime("%x").replace("/", "."),
                "end": end_date.strftime("%x").replace("/", ".")}
        if start_date != end_date:
            filename = "%(title)s, %(start)s - %(end)s.html" % vars
        else:
            filename = "%(title)s, %(start)s.html" % vars

        self.dialog.set_current_name(filename)

        response = self.dialog.run()

        if response != gtk.ResponseType.OK:
            self.emit("report-chooser-closed")
            self.dialog.destroy()
            self.dialog = None
        else:
            self.on_save_button_clicked()


    def present(self):
        self.dialog.present()

    def on_save_button_clicked(self):
        path, format = None,  None

        format = "html"
        if self.dialog.get_filter() in self.filters:
            format = self.filters[self.dialog.get_filter()]
        path = self.dialog.get_filename()

        # append correct extension if it is missing
        # TODO - proper way would be to change extension on filter change
        # only pointer in web is http://www.mail-archive.com/pygtk@daa.com.au/msg08740.html
        if path.endswith(".%s" % format) == False:
            path = "%s.%s" % (path.rstrip("."), format)

        categories = []

        conf.set("last_report_folder", os.path.dirname(path))

        # format, path, start_date, end_date
        self.emit("report-chosen", format, path)
        self.dialog.destroy()
        self.dialog = None

########NEW FILE########
__FILENAME__ = tags
# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
import cairo
from math import pi

from hamster.lib import graphics, stuff
from hamster.lib.configuration import runtime

class TagsEntry(gtk.Entry):
    __gsignals__ = {
        'tags-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gtk.Entry.__init__(self)
        self.tags = None
        self.filter = None # currently applied filter string
        self.filter_tags = [] #filtered tags

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        self.scroll_box = gtk.ScrolledWindow()
        self.scroll_box.set_shadow_type(gtk.ShadowType.IN)
        self.scroll_box.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.ShadowType.NONE)

        self.tag_box = TagBox()
        self.tag_box.connect("tag-selected", self.on_tag_selected)
        self.tag_box.connect("tag-unselected", self.on_tag_unselected)


        viewport.add(self.tag_box)
        self.scroll_box.add(viewport)
        self.popup.add(self.scroll_box)

        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("key-release-event", self._on_key_release_event)
        self.connect("focus-out-event", self._on_focus_out_event)

        self._parent_click_watcher = None # bit lame but works

        self.external_listeners = [
            (runtime.storage, runtime.storage.connect('tags-changed', self.refresh_tags))
        ]
        self.show()
        self.populate_suggestions()
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        for obj, handler in self.external_listeners:
            obj.disconnect(handler)
        self.popup.destroy()
        self.popup = None


    def refresh_tags(self, event):
        self.tags = None

    def get_tags(self):
        # splits the string by comma and filters out blanks
        return [tag.strip() for tag in self.get_text().decode('utf8', 'replace').split(",") if tag.strip()]

    def on_tag_selected(self, tag_box, tag):
        cursor_tag = self.get_cursor_tag()
        if cursor_tag and tag.lower().startswith(cursor_tag.lower()):
            self.replace_tag(cursor_tag, tag)
            tags = self.get_tags()
        else:
            tags = self.get_tags()
            tags.append(tag)

        self.tag_box.selected_tags = tags


        self.set_text("%s, " % ", ".join(tags))
        self.set_position(len(self.get_text()))

        self.populate_suggestions()
        self.show_popup()

    def on_tag_unselected(self, tag_box, tag):
        tags = self.get_tags()
        while tag in tags: #it could be that dear user is mocking us and entering same tag over and over again
            tags.remove(tag)

        self.tag_box.selected_tags = tags

        self.set_text("%s, " % ", ".join(tags))
        self.set_position(len(self.get_text()))


    def hide_popup(self):
        self.popup.hide()
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None

    def show_popup(self):
        if not self.filter_tags:
            self.popup.hide()
            return

        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        alloc = self.get_allocation()
        x, y = self.get_parent_window().get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)

        w = alloc.width

        height = self.tag_box.count_height(w)


        self.tag_box.modify_bg(gtk.StateType.NORMAL, "#eee") #self.get_style().base[gtk.StateType.NORMAL])

        self.scroll_box.set_size_request(w, height)
        self.popup.resize(w, height)
        self.popup.show_all()



    def complete_inline(self):
        return

    def refresh_activities(self):
        # scratch activities and categories so that they get repopulated on demand
        self.activities = None
        self.categories = None

    def populate_suggestions(self):
        self.tags = self.tags or [tag["name"] for tag in runtime.storage.get_tags(only_autocomplete=True)]

        cursor_tag = self.get_cursor_tag()

        self.filter = cursor_tag

        entered_tags = self.get_tags()
        self.tag_box.selected_tags = entered_tags

        self.filter_tags = [tag for tag in self.tags if (tag or "").lower().startswith((self.filter or "").lower())]

        self.tag_box.draw(self.filter_tags)



    def _on_focus_out_event(self, widget, event):
        self.hide_popup()

    def _on_button_press_event(self, button, event):
        self.populate_suggestions()
        self.show_popup()

    def _on_key_release_event(self, entry, event):
        if (event.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter)):
            if self.popup.get_property("visible"):
                if self.get_text():
                    self.hide_popup()
                return True
            else:
                if self.get_text():
                    self.emit("tags-selected")
                return False
        elif (event.keyval == gdk.KEY_Escape):
            if self.popup.get_property("visible"):
                self.hide_popup()
                return True
            else:
                return False
        else:
            self.populate_suggestions()
            self.show_popup()

            if event.keyval not in (gdk.KEY_Delete, gdk.KEY_BackSpace):
                self.complete_inline()


    def get_cursor_tag(self):
        #returns the tag on which the cursor is on right now
        if self.get_selection_bounds():
            cursor = self.get_selection_bounds()[0]
        else:
            cursor = self.get_position()

        text = self.get_text().decode('utf8', 'replace')

        return text[text.rfind(",", 0, cursor)+1:max(text.find(",", cursor+1)+1, len(text))].strip()


    def replace_tag(self, old_tag, new_tag):
        tags = self.get_tags()
        if old_tag in tags:
            tags[tags.index(old_tag)] = new_tag

        if self.get_selection_bounds():
            cursor = self.get_selection_bounds()[0]
        else:
            cursor = self.get_position()

        self.set_text(", ".join(tags))
        self.set_position(len(self.get_text()))

    def _on_key_press_event(self, entry, event):
        if event.keyval == gdk.KEY_Tab:
            if self.popup.get_property("visible"):
                #we have to replace
                if self.get_text() and self.get_cursor_tag() != self.filter_tags[0]:
                    self.replace_tag(self.get_cursor_tag(), self.filter_tags[0])
                    return True
                else:
                    return False
            else:
                return False

        return False


class TagBox(graphics.Scene):
    __gsignals__ = {
        'tag-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
        'tag-unselected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
    }

    def __init__(self, interactive = True):
        graphics.Scene.__init__(self)
        self.interactive = interactive
        self.hover_tag = None
        self.tags = []
        self.selected_tags = []
        self.layout = None

        if self.interactive:
            self.connect("on-mouse-over", self.on_mouse_over)
            self.connect("on-mouse-out", self.on_mouse_out)
            self.connect("on-click", self.on_tag_click)

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_mouse_over(self, area, tag):
        tag.color = tag.graphics.colors.darker(tag.color, -20)

    def on_mouse_out(self, area, tag):
        if tag.text in self.selected_tags:
            tag.color = (242, 229, 97)
        else:
            tag.color = (241, 234, 170)


    def on_tag_click(self, area, event, tag):
        if not tag: return

        if tag.text in self.selected_tags:
            self.emit("tag-unselected", tag.text)
        else:
            self.emit("tag-selected", tag.text)
        self.on_mouse_out(area, tag) #paint
        self.redraw()

    def draw(self, tags):
        new_tags = []
        for label in tags:
            tag = Tag(label)
            if label in self.selected_tags:
                tag.color = (242, 229, 97)
            new_tags.append(tag)

        for tag in self.tags:
            self.sprites.remove(tag)

        self.add_child(*new_tags)
        self.tags = new_tags

        self.show()
        self.redraw()

    def count_height(self, width):
        # reposition tags and see how much space we take up
        self.width = width
        w, h = self.on_enter_frame(None, None)
        return h + 6

    def on_enter_frame(self, scene, context):
        cur_x, cur_y = 4, 4
        tag = None
        for tag in self.tags:
            if cur_x + tag.width >= self.width - 5:  #if we do not fit, we wrap
                cur_x = 5
                cur_y += tag.height + 6

            tag.x = cur_x
            tag.y = cur_y

            cur_x += tag.width + 6 #some padding too, please

        if tag:
            cur_y += tag.height + 2 # the last one

        return cur_x, cur_y

class Tag(graphics.Sprite):
    def __init__(self, text, interactive = True, color = "#F1EAAA"):
        graphics.Sprite.__init__(self, interactive = interactive)

        self.width, self.height = 0,0

        font = gtk.Style().font_desc
        font_size = int(font.get_size() * 0.8 / pango.SCALE) # 80% of default

        self.label = graphics.Label(text, size = font_size, color = (30, 30, 30), y = 1)
        self.color = color
        self.add_child(self.label)

        self.corner = int((self.label.height + 3) / 3) + 0.5
        self.label.x = self.corner + 6

        self.text = stuff.escape_pango(text)
        self.connect("on-render", self.on_render)

    def __setattr__(self, name, value):
        graphics.Sprite.__setattr__(self, name, value)
        if name == 'text' and hasattr(self, 'label'):
            self.label.text = value
            self.__dict__['width'], self.__dict__['height'] = int(self.label.x + self.label.width + self.label.height * 0.3), self.label.height + 3

    def on_render(self, sprite):
        self.graphics.set_line_style(width=1)

        self.graphics.move_to(0.5, self.corner)
        self.graphics.line_to([(self.corner, 0.5),
                               (self.width + 0.5, 0.5),
                               (self.width + 0.5, self.height - 0.5),
                               (self.corner, self.height - 0.5),
                               (0.5, self.height - self.corner)])
        self.graphics.close_path()
        self.graphics.fill_stroke(self.color, "#b4b4b4")

        self.graphics.circle(6, self.height / 2, 2)
        self.graphics.fill_stroke("#fff", "#b4b4b4")

########NEW FILE########
__FILENAME__ = timeinput
# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

import datetime as dt
import calendar
import re

from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from hamster.lib.stuff import format_duration

class TimeInput(gtk.Entry):
    __gsignals__ = {
        'time-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, time = None, start_time = None):
        gtk.Entry.__init__(self)
        self.news = False
        self.set_width_chars(7) #7 is like 11:24pm

        self.set_time(time)
        self.set_start_time(start_time)

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        time_box = gtk.ScrolledWindow()
        time_box.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.ALWAYS)
        time_box.set_shadow_type(gtk.ShadowType.IN)

        self.time_tree = gtk.TreeView()
        self.time_tree.set_headers_visible(False)
        self.time_tree.set_hover_selection(True)

        self.time_tree.append_column(gtk.TreeViewColumn("Time",
                                                        gtk.CellRendererText(),
                                                        text=0))
        self.time_tree.connect("button-press-event",
                               self._on_time_tree_button_press_event)

        time_box.add(self.time_tree)
        self.popup.add(time_box)

        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("focus-in-event", self._on_focus_in_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self._parent_click_watcher = None # bit lame but works

        self.connect("changed", self._on_text_changed)
        self.show()
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None

    def set_time(self, time):
        time = time or dt.time()
        if isinstance(time, dt.time): # ensure that we operate with time and strip seconds
            self.time = dt.time(time.hour, time.minute)
        else:
            self.time = dt.time(time.time().hour, time.time().minute)

        self.set_text(self._format_time(time))

    def set_start_time(self, start_time):
        """ set the start time. when start time is set, drop down list
            will start from start time and duration will be displayed in
            brackets
        """
        start_time = start_time or dt.time()
        if isinstance(start_time, dt.time): # ensure that we operate with time
            self.start_time = dt.time(start_time.hour, start_time.minute)
        else:
            self.start_time = dt.time(start_time.time().hour, start_time.time().minute)

    def _on_text_changed(self, widget):
        self.news = True

    def figure_time(self, str_time):
        if not str_time:
            return self.time

        # strip everything non-numeric and consider hours to be first number
        # and minutes - second number
        numbers = re.split("\D", str_time)
        numbers = filter(lambda x: x!="", numbers)

        hours, minutes = None, None

        if len(numbers) == 1 and len(numbers[0]) == 4:
            hours, minutes = int(numbers[0][:2]), int(numbers[0][2:])
        else:
            if len(numbers) >= 1:
                hours = int(numbers[0])
            if len(numbers) >= 2:
                minutes = int(numbers[1])

        if (hours is None or minutes is None) or hours > 24 or minutes > 60:
            return self.time #no can do

        return dt.time(hours, minutes)


    def _select_time(self, time_text):
        #convert forth and back so we have text formated as we want
        time = self.figure_time(time_text)
        time_text = self._format_time(time)

        self.set_text(time_text)
        self.set_position(len(time_text))
        self.hide_popup()
        if self.news:
            self.emit("time-entered")
            self.news = False

    def get_time(self):
        self.time = self.figure_time(self.get_text())
        self.set_text(self._format_time(self.time))
        return self.time

    def _format_time(self, time):
        if time is None:
            return ""
        return time.strftime("%H:%M").lower()


    def _on_focus_in_event(self, entry, event):
        self.show_popup()

    def _on_button_press_event(self, button, event):
        self.show_popup()

    def _on_focus_out_event(self, event, something):
        self.hide_popup()
        if self.news:
            self.emit("time-entered")
            self.news = False

    def hide_popup(self):
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None
        self.popup.hide()

    def show_popup(self):
        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        # will be going either 24 hours or from start time to start time + 12 hours
        start_time = dt.datetime.combine(dt.date.today(), self.start_time) # we will be adding things
        i_time = start_time # we will be adding things

        if self.start_time:
            end_time = i_time + dt.timedelta(hours = 12)
            i_time += dt.timedelta(minutes = 15)
        else:
            end_time = i_time + dt.timedelta(days = 1)


        focus_time = dt.datetime.combine(dt.date.today(), self.figure_time(self.get_text()))
        hours = gtk.ListStore(gobject.TYPE_STRING)


        i, focus_row = 0, None
        while i_time < end_time:
            row_text = self._format_time(i_time)
            if self.start_time:
                delta = (i_time - start_time).seconds / 60
                delta_text = format_duration(delta)

                row_text += " (%s)" % delta_text

            hours.append([row_text])


            if focus_time and i_time <= focus_time <= i_time + \
                                                     dt.timedelta(minutes = 30):
                focus_row = i

            if self.start_time:
                i_time += dt.timedelta(minutes = 15)
            else:
                i_time += dt.timedelta(minutes = 30)

            i += 1

        self.time_tree.set_model(hours)

        #focus on row
        if focus_row != None:
            selection = self.time_tree.get_selection()
            selection.select_path(focus_row)
            self.time_tree.scroll_to_cell(focus_row, use_align = True, row_align = 0.4)


        #move popup under the widget
        alloc = self.get_allocation()
        w = alloc.width
        if self.start_time:
            w = w * 2
        self.time_tree.set_size_request(w, alloc.height * 5)

        window = self.get_parent_window()
        dmmy, x, y= window.get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.resize(*self.time_tree.get_size_request())
        self.popup.show_all()


    def _on_time_tree_button_press_event(self, tree, event):
        model, iter = tree.get_selection().get_selected()
        time = model.get_value(iter, 0)
        self._select_time(time)


    def _on_key_press_event(self, entry, event):
        if event.keyval not in (gdk.KEY_Up, gdk.KEY_Down, gdk.KEY_Return, gdk.KEY_KP_Enter):
            #any kind of other input
            self.hide_popup()
            return False

        model, iter = self.time_tree.get_selection().get_selected()
        if not iter:
            return


        i = model.get_path(iter)[0]
        if event.keyval == gtk.gdk.KEY_Up:
            i-=1
        elif event.keyval == gtk.gdk.KEY_Down:
            i+=1
        elif (event.keyval == gtk.gdk.KEY_Return or
              event.keyval == gtk.gdk.KEY_KP_Enter):

            if self.popup.get_property("visible"):
                self._select_time(self.time_tree.get_model()[i][0])
            else:
                self._select_time(entry.get_text())
        elif (event.keyval == gtk.gdk.KEY_Escape):
            self.hide_popup()
            return

        # keep it in sane limits
        i = min(max(i, 0), len(self.time_tree.get_model()) - 1)

        self.time_tree.set_cursor(i)
        self.time_tree.scroll_to_cell(i, use_align = True, row_align = 0.4)

        # if popup is not visible, display it on up and down
        if event.keyval in (gtk.gdk.KEY_Up, gtk.gdk.KEY_Down) and self.popup.props.visible == False:
            self.show_popup()

        return True

########NEW FILE########
__FILENAME__ = stuff_test
import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster.lib import Fact

class TestActivityInputParsing(unittest.TestCase):
    def test_plain_name(self):
        # plain activity name
        activity = Fact("just a simple case")
        self.assertEquals(activity.activity, "just a simple case")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        # with time
        activity = Fact("12:35 with start time")
        self.assertEquals(activity.activity, "with start time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = Fact("12:35-14:25 with start-end time")
        self.assertEquals(activity.activity, "with start-end time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        # plain activity name
        activity = Fact("just a simple case@hamster")
        self.assertEquals(activity.activity, "just a simple case")
        self.assertEquals(activity.category, "hamster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        # plain activity name
        activity = Fact("case, with added description")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added description")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        # plain activity name
        activity = Fact("case, with added #de description #and, #some #tags")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added #de description")
        self.assertEquals(set(activity.tags), set(["and", "some", "tags"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        activity = Fact("1225-1325 case@cat, description #ta non-tag #tag #bag")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description #ta non-tag")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = boost
#! /usr/bin/env python
# encoding: utf-8

import os.path,glob,types,re,sys
import Configure,config_c,Options,Utils,Logs
from Logs import warn,debug
from Configure import conf
boost_code='''
#include <iostream>
#include <boost/version.hpp>
int main() { std::cout << BOOST_VERSION << std::endl; }
'''
boost_libpath=['/usr/lib','/usr/local/lib','/opt/local/lib','/sw/lib','/lib']
boost_cpppath=['/usr/include','/usr/local/include','/opt/local/include','/sw/include']
STATIC_NOSTATIC='nostatic'
STATIC_BOTH='both'
STATIC_ONLYSTATIC='onlystatic'
is_versiontag=re.compile('^\d+_\d+_?\d*$')
is_threadingtag=re.compile('^mt$')
is_abitag=re.compile('^[sgydpn]+$')
is_toolsettag=re.compile('^(acc|borland|como|cw|dmc|darwin|gcc|hp_cxx|intel|kylix|vc|mgw|qcc|sun|vacpp)\d*$')
is_pythontag=re.compile('^py[0-9]{2}$')
def set_options(opt):
	opt.add_option('--boost-includes',type='string',default='',dest='boostincludes',help='path to the boost directory where the includes are e.g. /usr/local/include/boost-1_35')
	opt.add_option('--boost-libs',type='string',default='',dest='boostlibs',help='path to the directory where the boost libs are e.g. /usr/local/lib')
def string_to_version(s):
	version=s.split('.')
	if len(version)<3:return 0
	return int(version[0])*100000+int(version[1])*100+int(version[2])
def version_string(version):
	major=version/100000
	minor=version/100%1000
	minor_minor=version%100
	if minor_minor==0:
		return"%d_%d"%(major,minor)
	else:
		return"%d_%d_%d"%(major,minor,minor_minor)
def libfiles(lib,pattern,lib_paths):
	result=[]
	for lib_path in lib_paths:
		libname=pattern%('boost_%s[!_]*'%lib)
		result+=glob.glob(os.path.join(lib_path,libname))
	return result
def get_boost_version_number(self,dir):
	try:
		return self.run_c_code(compiler='cxx',code=boost_code,includes=dir,execute=1,env=self.env.copy(),type='cprogram',compile_mode='cxx',compile_filename='test.cpp')
	except Configure.ConfigurationError,e:
		return-1
def set_default(kw,var,val):
	if not var in kw:
		kw[var]=val
def tags_score(tags,kw):
	score=0
	needed_tags={'threading':kw['tag_threading'],'abi':kw['tag_abi'],'toolset':kw['tag_toolset'],'version':kw['tag_version'],'python':kw['tag_python']}
	if kw['tag_toolset']is None:
		v=kw['env']
		toolset=v['CXX_NAME']
		if v['CXX_VERSION']:
			version_no=v['CXX_VERSION'].split('.')
			toolset+=version_no[0]
			if len(version_no)>1:
				toolset+=version_no[1]
		needed_tags['toolset']=toolset
	found_tags={}
	for tag in tags:
		if is_versiontag.match(tag):found_tags['version']=tag
		if is_threadingtag.match(tag):found_tags['threading']=tag
		if is_abitag.match(tag):found_tags['abi']=tag
		if is_toolsettag.match(tag):found_tags['toolset']=tag
		if is_pythontag.match(tag):found_tags['python']=tag
	for tagname in needed_tags.iterkeys():
		if needed_tags[tagname]is not None and tagname in found_tags:
			if re.compile(needed_tags[tagname]).match(found_tags[tagname]):
				score+=kw['score_'+tagname][0]
			else:
				score+=kw['score_'+tagname][1]
	return score
def validate_boost(self,kw):
	ver=kw.get('version','')
	for x in'min_version max_version version'.split():
		set_default(kw,x,ver)
	set_default(kw,'lib','')
	kw['lib']=Utils.to_list(kw['lib'])
	set_default(kw,'env',self.env)
	set_default(kw,'libpath',boost_libpath)
	set_default(kw,'cpppath',boost_cpppath)
	for x in'tag_threading tag_version tag_toolset'.split():
		set_default(kw,x,None)
	set_default(kw,'tag_abi','^[^d]*$')
	set_default(kw,'python',str(sys.version_info[0])+str(sys.version_info[1]))
	set_default(kw,'tag_python','^py'+kw['python']+'$')
	set_default(kw,'score_threading',(10,-10))
	set_default(kw,'score_abi',(10,-10))
	set_default(kw,'score_python',(10,-10))
	set_default(kw,'score_toolset',(1,-1))
	set_default(kw,'score_version',(100,-100))
	set_default(kw,'score_min',0)
	set_default(kw,'static',STATIC_NOSTATIC)
	set_default(kw,'found_includes',False)
	set_default(kw,'min_score',0)
	set_default(kw,'errmsg','not found')
	set_default(kw,'okmsg','ok')
def find_boost_includes(self,kw):
	boostPath=getattr(Options.options,'boostincludes','')
	if boostPath:
		boostPath=[os.path.normpath(os.path.expandvars(os.path.expanduser(boostPath)))]
	else:
		boostPath=Utils.to_list(kw['cpppath'])
	min_version=string_to_version(kw.get('min_version',''))
	max_version=string_to_version(kw.get('max_version',''))or(sys.maxint-1)
	version=0
	for include_path in boostPath:
		boost_paths=[p for p in glob.glob(os.path.join(include_path,'boost*'))if os.path.isdir(p)]
		debug('BOOST Paths: %r'%boost_paths)
		for path in boost_paths:
			pathname=os.path.split(path)[-1]
			ret=-1
			if pathname=='boost':
				path=include_path
				ret=self.get_boost_version_number(path)
			elif pathname.startswith('boost-'):
				ret=self.get_boost_version_number(path)
			ret=int(ret)
			if ret!=-1 and ret>=min_version and ret<=max_version and ret>version:
				boost_path=path
				version=ret
	if not version:
		self.fatal('boost headers not found! (required version min: %s max: %s)'%(kw['min_version'],kw['max_version']))
		return False
	found_version=version_string(version)
	versiontag='^'+found_version+'$'
	if kw['tag_version']is None:
		kw['tag_version']=versiontag
	elif kw['tag_version']!=versiontag:
		warn('boost header version %r and tag_version %r do not match!'%(versiontag,kw['tag_version']))
	env=self.env
	env['CPPPATH_BOOST']=boost_path
	env['BOOST_VERSION']=found_version
	self.found_includes=1
	ret='Version %s (%s)'%(found_version,boost_path)
	return ret
def find_boost_library(self,lib,kw):
	def find_library_from_list(lib,files):
		lib_pattern=re.compile('.*boost_(.*?)\..*')
		result=(None,None)
		resultscore=kw['min_score']-1
		for file in files:
			m=lib_pattern.search(file,1)
			if m:
				libname=m.group(1)
				libtags=libname.split('-')[1:]
				currentscore=tags_score(libtags,kw)
				if currentscore>resultscore:
					result=(libname,file)
					resultscore=currentscore
		return result
	lib_paths=getattr(Options.options,'boostlibs','')
	if lib_paths:
		lib_paths=[os.path.normpath(os.path.expandvars(os.path.expanduser(lib_paths)))]
	else:
		lib_paths=Utils.to_list(kw['libpath'])
	v=kw.get('env',self.env)
	(libname,file)=(None,None)
	if kw['static']in[STATIC_NOSTATIC,STATIC_BOTH]:
		st_env_prefix='LIB'
		files=libfiles(lib,v['shlib_PATTERN'],lib_paths)
		(libname,file)=find_library_from_list(lib,files)
	if libname is None and kw['static']in[STATIC_ONLYSTATIC,STATIC_BOTH]:
		st_env_prefix='STATICLIB'
		staticLibPattern=v['staticlib_PATTERN']
		if self.env['CC_NAME']=='msvc':
			staticLibPattern='lib'+staticLibPattern
		files=libfiles(lib,staticLibPattern,lib_paths)
		(libname,file)=find_library_from_list(lib,files)
	if libname is not None:
		v['LIBPATH_BOOST_'+lib.upper()]=[os.path.split(file)[0]]
		if self.env['CC_NAME']=='msvc'and os.path.splitext(file)[1]=='.lib':
			v[st_env_prefix+'_BOOST_'+lib.upper()]=['libboost_'+libname]
		else:
			v[st_env_prefix+'_BOOST_'+lib.upper()]=['boost_'+libname]
		return
	self.fatal('lib boost_'+lib+' not found!')
def check_boost(self,*k,**kw):
	if not self.env['CXX']:
		self.fatal('load a c++ compiler tool first, for example conf.check_tool("g++")')
	self.validate_boost(kw)
	ret=None
	try:
		if not kw.get('found_includes',None):
			self.check_message_1(kw.get('msg_includes','boost headers'))
			ret=self.find_boost_includes(kw)
	except Configure.ConfigurationError,e:
		if'errmsg'in kw:
			self.check_message_2(kw['errmsg'],'YELLOW')
		if'mandatory'in kw:
			if Logs.verbose>1:
				raise
			else:
				self.fatal('the configuration failed (see %r)'%self.log.name)
	else:
		if'okmsg'in kw:
			self.check_message_2(kw.get('okmsg_includes',ret))
	for lib in kw['lib']:
		self.check_message_1('library boost_'+lib)
		try:
			self.find_boost_library(lib,kw)
		except Configure.ConfigurationError,e:
			ret=False
			if'errmsg'in kw:
				self.check_message_2(kw['errmsg'],'YELLOW')
			if'mandatory'in kw:
				if Logs.verbose>1:
					raise
				else:
					self.fatal('the configuration failed (see %r)'%self.log.name)
		else:
			if'okmsg'in kw:
				self.check_message_2(kw['okmsg'])
	return ret

conf(get_boost_version_number)
conf(validate_boost)
conf(find_boost_includes)
conf(find_boost_library)
conf(check_boost)

########NEW FILE########
__FILENAME__ = fluid
#! /usr/bin/env python
# encoding: utf-8

import Task
from TaskGen import extension
Task.simple_task_type('fluid','${FLUID} -c -o ${TGT[0].abspath(env)} -h ${TGT[1].abspath(env)} ${SRC}','BLUE',shell=False,ext_out='.cxx')
def fluid(self,node):
	cpp=node.change_ext('.cpp')
	hpp=node.change_ext('.hpp')
	self.create_task('fluid',node,[cpp,hpp])
	if'cxx'in self.features:
		self.allnodes.append(cpp)
def detect(conf):
	fluid=conf.find_program('fluid',var='FLUID',mandatory=True)
	conf.check_cfg(path='fltk-config',package='',args='--cxxflags --ldflags',uselib_store='FLTK',mandatory=True)

extension('.fl')(fluid)

########NEW FILE########
__FILENAME__ = ansiterm
#! /usr/bin/env python
# encoding: utf-8

import sys,os
try:
	if(not sys.stderr.isatty())or(not sys.stdout.isatty()):
		raise ValueError('not a tty')
	from ctypes import*
	class COORD(Structure):
		_fields_=[("X",c_short),("Y",c_short)]
	class SMALL_RECT(Structure):
		_fields_=[("Left",c_short),("Top",c_short),("Right",c_short),("Bottom",c_short)]
	class CONSOLE_SCREEN_BUFFER_INFO(Structure):
		_fields_=[("Size",COORD),("CursorPosition",COORD),("Attributes",c_short),("Window",SMALL_RECT),("MaximumWindowSize",COORD)]
	class CONSOLE_CURSOR_INFO(Structure):
		_fields_=[('dwSize',c_ulong),('bVisible',c_int)]
	sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
	csinfo=CONSOLE_CURSOR_INFO()
	hconsole=windll.kernel32.GetStdHandle(-11)
	windll.kernel32.GetConsoleScreenBufferInfo(hconsole,byref(sbinfo))
	if sbinfo.Size.X<10 or sbinfo.Size.Y<10:raise Exception('small console')
	windll.kernel32.GetConsoleCursorInfo(hconsole,byref(csinfo))
except Exception:
	pass
else:
	import re,threading
	to_int=lambda number,default:number and int(number)or default
	wlock=threading.Lock()
	STD_OUTPUT_HANDLE=-11
	STD_ERROR_HANDLE=-12
	class AnsiTerm(object):
		def __init__(self):
			self.hconsole=windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
			self.cursor_history=[]
		def screen_buffer_info(self):
			sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
			windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole,byref(sbinfo))
			return sbinfo
		def clear_line(self,param):
			mode=param and int(param)or 0
			sbinfo=self.screen_buffer_info()
			if mode==1:
				line_start=COORD(0,sbinfo.CursorPosition.Y)
				line_length=sbinfo.Size.X
			elif mode==2:
				line_start=COORD(sbinfo.CursorPosition.X,sbinfo.CursorPosition.Y)
				line_length=sbinfo.Size.X-sbinfo.CursorPosition.X
			else:
				line_start=sbinfo.CursorPosition
				line_length=sbinfo.Size.X-sbinfo.CursorPosition.X
			chars_written=c_int()
			windll.kernel32.FillConsoleOutputCharacterA(self.hconsole,c_char(' '),line_length,line_start,byref(chars_written))
			windll.kernel32.FillConsoleOutputAttribute(self.hconsole,sbinfo.Attributes,line_length,line_start,byref(chars_written))
		def clear_screen(self,param):
			mode=to_int(param,0)
			sbinfo=self.screen_buffer_info()
			if mode==1:
				clear_start=COORD(0,0)
				clear_length=sbinfo.CursorPosition.X*sbinfo.CursorPosition.Y
			elif mode==2:
				clear_start=COORD(0,0)
				clear_length=sbinfo.Size.X*sbinfo.Size.Y
				windll.kernel32.SetConsoleCursorPosition(self.hconsole,clear_start)
			else:
				clear_start=sbinfo.CursorPosition
				clear_length=((sbinfo.Size.X-sbinfo.CursorPosition.X)+sbinfo.Size.X*(sbinfo.Size.Y-sbinfo.CursorPosition.Y))
			chars_written=c_int()
			windll.kernel32.FillConsoleOutputCharacterA(self.hconsole,c_char(' '),clear_length,clear_start,byref(chars_written))
			windll.kernel32.FillConsoleOutputAttribute(self.hconsole,sbinfo.Attributes,clear_length,clear_start,byref(chars_written))
		def push_cursor(self,param):
			sbinfo=self.screen_buffer_info()
			self.cursor_history.push(sbinfo.CursorPosition)
		def pop_cursor(self,param):
			if self.cursor_history:
				old_pos=self.cursor_history.pop()
				windll.kernel32.SetConsoleCursorPosition(self.hconsole,old_pos)
		def set_cursor(self,param):
			x,sep,y=param.partition(';')
			x=to_int(x,1)-1
			y=to_int(y,1)-1
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,x),sbinfo.Size.X),min(max(0,y),sbinfo.Size.Y))
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def set_column(self,param):
			x=to_int(param,1)-1
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,x),sbinfo.Size.X),sbinfo.CursorPosition.Y)
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def move_cursor(self,x_offset=0,y_offset=0):
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,sbinfo.CursorPosition.X+x_offset),sbinfo.Size.X),min(max(0,sbinfo.CursorPosition.Y+y_offset),sbinfo.Size.Y))
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def move_up(self,param):
			self.move_cursor(y_offset=-to_int(param,1))
		def move_down(self,param):
			self.move_cursor(y_offset=to_int(param,1))
		def move_left(self,param):
			self.move_cursor(x_offset=-to_int(param,1))
		def move_right(self,param):
			self.move_cursor(x_offset=to_int(param,1))
		def next_line(self,param):
			sbinfo=self.screen_buffer_info()
			self.move_cursor(x_offset=-sbinfo.CursorPosition.X,y_offset=to_int(param,1))
		def prev_line(self,param):
			sbinfo=self.screen_buffer_info()
			self.move_cursor(x_offset=-sbinfo.CursorPosition.X,y_offset=-to_int(param,1))
		escape_to_color={(0,30):0x0,(0,31):0x4,(0,32):0x2,(0,33):0x4+0x2,(0,34):0x1,(0,35):0x1+0x4,(0,36):0x2+0x4,(0,37):0x1+0x2+0x4,(1,30):0x1+0x2+0x4,(1,31):0x4+0x8,(1,32):0x2+0x8,(1,33):0x4+0x2+0x8,(1,34):0x1+0x8,(1,35):0x1+0x4+0x8,(1,36):0x1+0x2+0x8,(1,37):0x1+0x2+0x4+0x8,}
		def set_color(self,param):
			intensity,sep,color=param.partition(';')
			intensity=to_int(intensity,0)
			color=to_int(color,0)
			if intensity and not color:
				color,intensity=intensity,color
			attrib=self.escape_to_color.get((intensity,color),0x7)
			windll.kernel32.SetConsoleTextAttribute(self.hconsole,attrib)
		def show_cursor(self,param):
			csinfo.bVisible=1
			windll.kernel32.SetConsoleCursorInfo(self.hconsole,byref(csinfo))
		def hide_cursor(self,param):
			csinfo.bVisible=0
			windll.kernel32.SetConsoleCursorInfo(self.hconsole,byref(csinfo))
		ansi_command_table={'A':move_up,'B':move_down,'C':move_right,'D':move_left,'E':next_line,'F':prev_line,'G':set_column,'H':set_cursor,'f':set_cursor,'J':clear_screen,'K':clear_line,'h':show_cursor,'l':hide_cursor,'m':set_color,'s':push_cursor,'u':pop_cursor,}
		ansi_tokans=re.compile('(?:\x1b\[([0-9?;]*)([a-zA-Z])|([^\x1b]+))')
		def write(self,text):
			wlock.acquire()
			for param,cmd,txt in self.ansi_tokans.findall(text):
				if cmd:
					cmd_func=self.ansi_command_table.get(cmd)
					if cmd_func:
						cmd_func(self,param)
				else:
					chars_written=c_int()
					if isinstance(txt,unicode):
						windll.kernel32.WriteConsoleW(self.hconsole,txt,len(txt),byref(chars_written),None)
					else:
						windll.kernel32.WriteConsoleA(self.hconsole,txt,len(txt),byref(chars_written),None)
			wlock.release()
		def flush(self):
			pass
		def isatty(self):
			return True
	sys.stderr=sys.stdout=AnsiTerm()
	os.environ['TERM']='vt100'


########NEW FILE########
__FILENAME__ = Build
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,sys,errno,re,glob,gc,datetime,shutil
try:import cPickle
except:import pickle as cPickle
import Runner,TaskGen,Node,Scripting,Utils,Environment,Task,Logs,Options
from Logs import debug,error,info
from Constants import*
SAVED_ATTRS='root srcnode bldnode node_sigs node_deps raw_deps task_sigs id_nodes'.split()
bld=None
class BuildError(Utils.WafError):
	def __init__(self,b=None,t=[]):
		self.bld=b
		self.tasks=t
		self.ret=1
		Utils.WafError.__init__(self,self.format_error())
	def format_error(self):
		lst=['Build failed:']
		for tsk in self.tasks:
			txt=tsk.format_error()
			if txt:lst.append(txt)
		sep=' '
		if len(lst)>2:
			sep='\n'
		return sep.join(lst)
def group_method(fun):
	def f(*k,**kw):
		if not k[0].is_install:
			return False
		postpone=True
		if'postpone'in kw:
			postpone=kw['postpone']
			del kw['postpone']
		if postpone:
			m=k[0].task_manager
			if not m.groups:m.add_group()
			m.groups[m.current_group].post_funs.append((fun,k,kw))
			if not'cwd'in kw:
				kw['cwd']=k[0].path
		else:
			fun(*k,**kw)
	return f
class BuildContext(Utils.Context):
	def __init__(self):
		global bld
		bld=self
		self.task_manager=Task.TaskManager()
		self.id_nodes=0
		self.idx={}
		self.all_envs={}
		self.bdir=''
		self.path=None
		self.deps_man=Utils.DefaultDict(list)
		self.cache_node_abspath={}
		self.cache_scanned_folders={}
		self.uninstall=[]
		for v in'cache_node_abspath task_sigs node_deps raw_deps node_sigs'.split():
			var={}
			setattr(self,v,var)
		self.cache_dir_contents={}
		self.all_task_gen=[]
		self.task_gen_cache_names={}
		self.cache_sig_vars={}
		self.log=None
		self.root=None
		self.srcnode=None
		self.bldnode=None
		class node_class(Node.Node):
			pass
		self.node_class=node_class
		self.node_class.__module__="Node"
		self.node_class.__name__="Nodu"
		self.node_class.bld=self
		self.is_install=None
	def __copy__(self):
		raise Utils.WafError('build contexts are not supposed to be cloned')
	def load(self):
		try:
			env=Environment.Environment(os.path.join(self.cachedir,'build.config.py'))
		except(IOError,OSError):
			pass
		else:
			if env['version']<HEXVERSION:
				raise Utils.WafError('Version mismatch! reconfigure the project')
			for t in env['tools']:
				self.setup(**t)
		try:
			gc.disable()
			f=data=None
			Node.Nodu=self.node_class
			try:
				f=open(os.path.join(self.bdir,DBFILE),'rb')
			except(IOError,EOFError):
				pass
			try:
				if f:data=cPickle.load(f)
			except AttributeError:
				if Logs.verbose>1:raise
			if data:
				for x in SAVED_ATTRS:setattr(self,x,data[x])
			else:
				debug('build: Build cache loading failed')
		finally:
			if f:f.close()
			gc.enable()
	def save(self):
		gc.disable()
		self.root.__class__.bld=None
		Node.Nodu=self.node_class
		db=os.path.join(self.bdir,DBFILE)
		file=open(db+'.tmp','wb')
		data={}
		for x in SAVED_ATTRS:data[x]=getattr(self,x)
		cPickle.dump(data,file,-1)
		file.close()
		try:os.unlink(db)
		except OSError:pass
		os.rename(db+'.tmp',db)
		self.root.__class__.bld=self
		gc.enable()
	def clean(self):
		debug('build: clean called')
		precious=set([])
		for env in self.all_envs.values():
			for x in env[CFG_FILES]:
				node=self.srcnode.find_resource(x)
				if node:
					precious.add(node.id)
		def clean_rec(node):
			for x in list(node.childs.keys()):
				nd=node.childs[x]
				tp=nd.id&3
				if tp==Node.DIR:
					clean_rec(nd)
				elif tp==Node.BUILD:
					if nd.id in precious:continue
					for env in self.all_envs.values():
						try:os.remove(nd.abspath(env))
						except OSError:pass
					node.childs.__delitem__(x)
		clean_rec(self.srcnode)
		for v in'node_sigs node_deps task_sigs raw_deps cache_node_abspath'.split():
			setattr(self,v,{})
	def compile(self):
		debug('build: compile called')
		self.flush()
		self.generator=Runner.Parallel(self,Options.options.jobs)
		def dw(on=True):
			if Options.options.progress_bar:
				if on:sys.stderr.write(Logs.colors.cursor_on)
				else:sys.stderr.write(Logs.colors.cursor_off)
		debug('build: executor starting')
		back=os.getcwd()
		os.chdir(self.bldnode.abspath())
		try:
			try:
				dw(on=False)
				self.generator.start()
			except KeyboardInterrupt:
				dw()
				if Runner.TaskConsumer.consumers:
					self.save()
				raise
			except Exception:
				dw()
				raise
			else:
				dw()
				if Runner.TaskConsumer.consumers:
					self.save()
			if self.generator.error:
				raise BuildError(self,self.task_manager.tasks_done)
		finally:
			os.chdir(back)
	def install(self):
		debug('build: install called')
		self.flush()
		if self.is_install<0:
			lst=[]
			for x in self.uninstall:
				dir=os.path.dirname(x)
				if not dir in lst:lst.append(dir)
			lst.sort()
			lst.reverse()
			nlst=[]
			for y in lst:
				x=y
				while len(x)>4:
					if not x in nlst:nlst.append(x)
					x=os.path.dirname(x)
			nlst.sort()
			nlst.reverse()
			for x in nlst:
				try:os.rmdir(x)
				except OSError:pass
	def new_task_gen(self,*k,**kw):
		if self.task_gen_cache_names:
			self.task_gen_cache_names={}
		kw['bld']=self
		if len(k)==0:
			ret=TaskGen.task_gen(*k,**kw)
		else:
			cls_name=k[0]
			try:cls=TaskGen.task_gen.classes[cls_name]
			except KeyError:raise Utils.WscriptError('%s is not a valid task generator -> %s'%(cls_name,[x for x in TaskGen.task_gen.classes]))
			ret=cls(*k,**kw)
		return ret
	def __call__(self,*k,**kw):
		if self.task_gen_cache_names:
			self.task_gen_cache_names={}
		kw['bld']=self
		return TaskGen.task_gen(*k,**kw)
	def load_envs(self):
		try:
			lst=Utils.listdir(self.cachedir)
		except OSError,e:
			if e.errno==errno.ENOENT:
				raise Utils.WafError('The project was not configured: run "waf configure" first!')
			else:
				raise
		if not lst:
			raise Utils.WafError('The cache directory is empty: reconfigure the project')
		for file in lst:
			if file.endswith(CACHE_SUFFIX):
				env=Environment.Environment(os.path.join(self.cachedir,file))
				name=file[:-len(CACHE_SUFFIX)]
				self.all_envs[name]=env
		self.init_variants()
		for env in self.all_envs.values():
			for f in env[CFG_FILES]:
				newnode=self.path.find_or_declare(f)
				try:
					hash=Utils.h_file(newnode.abspath(env))
				except(IOError,AttributeError):
					error("cannot find "+f)
					hash=SIG_NIL
				self.node_sigs[env.variant()][newnode.id]=hash
		self.bldnode=self.root.find_dir(self.bldnode.abspath())
		self.path=self.srcnode=self.root.find_dir(self.srcnode.abspath())
		self.cwd=self.bldnode.abspath()
	def setup(self,tool,tooldir=None,funs=None):
		if isinstance(tool,list):
			for i in tool:self.setup(i,tooldir)
			return
		if not tooldir:tooldir=Options.tooldir
		module=Utils.load_tool(tool,tooldir)
		if hasattr(module,"setup"):module.setup(self)
	def init_variants(self):
		debug('build: init variants')
		lstvariants=[]
		for env in self.all_envs.values():
			if not env.variant()in lstvariants:
				lstvariants.append(env.variant())
		self.lst_variants=lstvariants
		debug('build: list of variants is %r',lstvariants)
		for name in lstvariants+[0]:
			for v in'node_sigs cache_node_abspath'.split():
				var=getattr(self,v)
				if not name in var:
					var[name]={}
	def load_dirs(self,srcdir,blddir,load_cache=1):
		assert(os.path.isabs(srcdir))
		assert(os.path.isabs(blddir))
		self.cachedir=os.path.join(blddir,CACHE_DIR)
		if srcdir==blddir:
			raise Utils.WafError("build dir must be different from srcdir: %s <-> %s "%(srcdir,blddir))
		self.bdir=blddir
		self.load()
		if not self.root:
			Node.Nodu=self.node_class
			self.root=Node.Nodu('',None,Node.DIR)
		if not self.srcnode:
			self.srcnode=self.root.ensure_dir_node_from_path(srcdir)
		debug('build: srcnode is %s and srcdir %s',self.srcnode.name,srcdir)
		self.path=self.srcnode
		try:os.makedirs(blddir)
		except OSError:pass
		if not self.bldnode:
			self.bldnode=self.root.ensure_dir_node_from_path(blddir)
		self.init_variants()
	def rescan(self,src_dir_node):
		if self.cache_scanned_folders.get(src_dir_node.id,None):return
		self.cache_scanned_folders[src_dir_node.id]=True
		if hasattr(self,'repository'):self.repository(src_dir_node)
		if not src_dir_node.name and sys.platform=='win32':
			return
		parent_path=src_dir_node.abspath()
		try:
			lst=set(Utils.listdir(parent_path))
		except OSError:
			lst=set([])
		self.cache_dir_contents[src_dir_node.id]=lst
		cache=self.node_sigs[0]
		for x in src_dir_node.childs.values():
			if x.id&3!=Node.FILE:continue
			if x.name in lst:
				try:
					cache[x.id]=Utils.h_file(x.abspath())
				except IOError:
					raise Utils.WafError('The file %s is not readable or has become a dir'%x.abspath())
			else:
				try:del cache[x.id]
				except KeyError:pass
				del src_dir_node.childs[x.name]
		h1=self.srcnode.height()
		h2=src_dir_node.height()
		lst=[]
		child=src_dir_node
		while h2>h1:
			lst.append(child.name)
			child=child.parent
			h2-=1
		lst.reverse()
		try:
			for variant in self.lst_variants:
				sub_path=os.path.join(self.bldnode.abspath(),variant,*lst)
				self.listdir_bld(src_dir_node,sub_path,variant)
		except OSError:
			for node in src_dir_node.childs.values():
				if node.id&3!=Node.BUILD:
					continue
				for dct in self.node_sigs.values():
					if node.id in dct:
						dct.__delitem__(node.id)
				src_dir_node.childs.__delitem__(node.name)
			for variant in self.lst_variants:
				sub_path=os.path.join(self.bldnode.abspath(),variant,*lst)
				try:
					os.makedirs(sub_path)
				except OSError:
					pass
	def listdir_src(self,parent_node):
		pass
	def remove_node(self,node):
		pass
	def listdir_bld(self,parent_node,path,variant):
		i_existing_nodes=[x for x in parent_node.childs.values()if x.id&3==Node.BUILD]
		lst=set(Utils.listdir(path))
		node_names=set([x.name for x in i_existing_nodes])
		remove_names=node_names-lst
		ids_to_remove=[x.id for x in i_existing_nodes if x.name in remove_names]
		cache=self.node_sigs[variant]
		for nid in ids_to_remove:
			if nid in cache:
				cache.__delitem__(nid)
	def get_env(self):
		return self.env_of_name('default')
	def set_env(self,name,val):
		self.all_envs[name]=val
	env=property(get_env,set_env)
	def add_manual_dependency(self,path,value):
		if isinstance(path,Node.Node):
			node=path
		elif os.path.isabs(path):
			node=self.root.find_resource(path)
		else:
			node=self.path.find_resource(path)
		self.deps_man[node.id].append(value)
	def launch_node(self):
		try:
			return self.p_ln
		except AttributeError:
			self.p_ln=self.root.find_dir(Options.launch_dir)
			return self.p_ln
	def glob(self,pattern,relative=True):
		path=self.path.abspath()
		files=[self.root.find_resource(x)for x in glob.glob(path+os.sep+pattern)]
		if relative:
			files=[x.path_to_parent(self.path)for x in files if x]
		else:
			files=[x.abspath()for x in files if x]
		return files
	def add_group(self,*k):
		self.task_manager.add_group(*k)
	def set_group(self,*k,**kw):
		self.task_manager.set_group(*k,**kw)
	def hash_env_vars(self,env,vars_lst):
		idx=str(id(env))+str(vars_lst)
		try:return self.cache_sig_vars[idx]
		except KeyError:pass
		lst=[str(env[a])for a in vars_lst]
		ret=Utils.h_list(lst)
		debug('envhash: %r %r',ret,lst)
		self.cache_sig_vars[idx]=ret
		return ret
	def name_to_obj(self,name,env):
		cache=self.task_gen_cache_names
		if not cache:
			for x in self.all_task_gen:
				vt=x.env.variant()+'_'
				if x.name:
					cache[vt+x.name]=x
				else:
					if isinstance(x.target,str):
						target=x.target
					else:
						target=' '.join(x.target)
					v=vt+target
					if not cache.get(v,None):
						cache[v]=x
		return cache.get(env.variant()+'_'+name,None)
	def flush(self,all=1):
		self.ini=datetime.datetime.now()
		self.task_gen_cache_names={}
		self.name_to_obj('',self.env)
		debug('build: delayed operation TaskGen.flush() called')
		if Options.options.compile_targets:
			debug('task_gen: posting objects %r listed in compile_targets',Options.options.compile_targets)
			mana=self.task_manager
			to_post=[]
			min_grp=0
			target_objects=Utils.DefaultDict(list)
			for target_name in Options.options.compile_targets.split(','):
				target_name=target_name.strip()
				for env in self.all_envs.values():
					tg=self.name_to_obj(target_name,env)
					if tg:
						target_objects[target_name].append(tg)
						m=mana.group_idx(tg)
						if m>min_grp:
							min_grp=m
							to_post=[tg]
						elif m==min_grp:
							to_post.append(tg)
				if not target_name in target_objects and all:
					raise Utils.WafError("target '%s' does not exist"%target_name)
			debug('group: Forcing up to group %s for target %s',mana.group_name(min_grp),Options.options.compile_targets)
			for i in xrange(len(mana.groups)):
				mana.current_group=i
				if i==min_grp:
					break
				g=mana.groups[i]
				debug('group: Forcing group %s',mana.group_name(g))
				for t in g.tasks_gen:
					debug('group: Posting %s',t.name or t.target)
					t.post()
			for t in to_post:
				t.post()
		else:
			debug('task_gen: posting objects (normal)')
			ln=self.launch_node()
			if ln.is_child_of(self.bldnode)or not ln.is_child_of(self.srcnode):
				ln=self.srcnode
			proj_node=self.root.find_dir(os.path.split(Utils.g_module.root_path)[0])
			if proj_node.id!=self.srcnode.id:
				ln=self.srcnode
			for i in xrange(len(self.task_manager.groups)):
				g=self.task_manager.groups[i]
				self.task_manager.current_group=i
				if Logs.verbose:
					groups=[x for x in self.task_manager.groups_names if id(self.task_manager.groups_names[x])==id(g)]
					name=groups and groups[0]or'unnamed'
					Logs.debug('group: group',name)
				for tg in g.tasks_gen:
					if not tg.path.is_child_of(ln):
						continue
					if Logs.verbose:
						Logs.debug('group: %s'%tg)
					tg.post()
	def env_of_name(self,name):
		try:
			return self.all_envs[name]
		except KeyError:
			error('no such environment: '+name)
			return None
	def progress_line(self,state,total,col1,col2):
		n=len(str(total))
		Utils.rot_idx+=1
		ind=Utils.rot_chr[Utils.rot_idx%4]
		ini=self.ini
		pc=(100.*state)/total
		eta=Utils.get_elapsed_time(ini)
		fs="[%%%dd/%%%dd][%%s%%2d%%%%%%s][%s]["%(n,n,ind)
		left=fs%(state,total,col1,pc,col2)
		right='][%s%s%s]'%(col1,eta,col2)
		cols=Utils.get_term_cols()-len(left)-len(right)+2*len(col1)+2*len(col2)
		if cols<7:cols=7
		ratio=int((cols*state)/total)-1
		bar=('='*ratio+'>').ljust(cols)
		msg=Utils.indicator%(left,bar,right)
		return msg
	def do_install(self,src,tgt,chmod=O644):
		if self.is_install>0:
			if not Options.options.force:
				try:
					st1=os.stat(tgt)
					st2=os.stat(src)
				except OSError:
					pass
				else:
					if st1.st_mtime>=st2.st_mtime and st1.st_size==st2.st_size:
						return False
			srclbl=src.replace(self.srcnode.abspath(None)+os.sep,'')
			info("* installing %s as %s"%(srclbl,tgt))
			try:os.remove(tgt)
			except OSError:pass
			try:
				shutil.copy2(src,tgt)
				os.chmod(tgt,chmod)
			except IOError:
				try:
					os.stat(src)
				except(OSError,IOError):
					error('File %r does not exist'%src)
				raise Utils.WafError('Could not install the file %r'%tgt)
			return True
		elif self.is_install<0:
			info("* uninstalling %s"%tgt)
			self.uninstall.append(tgt)
			try:
				os.remove(tgt)
			except OSError,e:
				if e.errno!=errno.ENOENT:
					if not getattr(self,'uninstall_error',None):
						self.uninstall_error=True
						Logs.warn('build: some files could not be uninstalled (retry with -vv to list them)')
					if Logs.verbose>1:
						Logs.warn('could not remove %s (error code %r)'%(e.filename,e.errno))
			return True
	red=re.compile(r"^([A-Za-z]:)?[/\\\\]*")
	def get_install_path(self,path,env=None):
		if not env:env=self.env
		destdir=env.get_destdir()
		path=path.replace('/',os.sep)
		destpath=Utils.subst_vars(path,env)
		if destdir:
			destpath=os.path.join(destdir,self.red.sub('',destpath))
		return destpath
	def install_dir(self,path,env=None):
		if env:
			assert isinstance(env,Environment.Environment),"invalid parameter"
		else:
			env=self.env
		if not path:
			return[]
		destpath=self.get_install_path(path,env)
		if self.is_install>0:
			info('* creating %s'%destpath)
			Utils.check_dir(destpath)
		elif self.is_install<0:
			info('* removing %s'%destpath)
			self.uninstall.append(destpath+'/xxx')
	def install_files(self,path,files,env=None,chmod=O644,relative_trick=False,cwd=None):
		if env:
			assert isinstance(env,Environment.Environment),"invalid parameter"
		else:
			env=self.env
		if not path:return[]
		if not cwd:
			cwd=self.path
		if isinstance(files,str)and'*'in files:
			gl=cwd.abspath()+os.sep+files
			lst=glob.glob(gl)
		else:
			lst=Utils.to_list(files)
		if not getattr(lst,'__iter__',False):
			lst=[lst]
		destpath=self.get_install_path(path,env)
		Utils.check_dir(destpath)
		installed_files=[]
		for filename in lst:
			if isinstance(filename,str)and os.path.isabs(filename):
				alst=Utils.split_path(filename)
				destfile=os.path.join(destpath,alst[-1])
			else:
				if isinstance(filename,Node.Node):
					nd=filename
				else:
					nd=cwd.find_resource(filename)
				if not nd:
					raise Utils.WafError("Unable to install the file %r (not found in %s)"%(filename,cwd))
				if relative_trick:
					destfile=os.path.join(destpath,filename)
					Utils.check_dir(os.path.dirname(destfile))
				else:
					destfile=os.path.join(destpath,nd.name)
				filename=nd.abspath(env)
			if self.do_install(filename,destfile,chmod):
				installed_files.append(destfile)
		return installed_files
	def install_as(self,path,srcfile,env=None,chmod=O644,cwd=None):
		if env:
			assert isinstance(env,Environment.Environment),"invalid parameter"
		else:
			env=self.env
		if not path:
			raise Utils.WafError("where do you want to install %r? (%r?)"%(srcfile,path))
		if not cwd:
			cwd=self.path
		destpath=self.get_install_path(path,env)
		dir,name=os.path.split(destpath)
		Utils.check_dir(dir)
		if isinstance(srcfile,Node.Node):
			src=srcfile.abspath(env)
		else:
			src=srcfile
			if not os.path.isabs(srcfile):
				node=cwd.find_resource(srcfile)
				if not node:
					raise Utils.WafError("Unable to install the file %r (not found in %s)"%(srcfile,cwd))
				src=node.abspath(env)
		return self.do_install(src,destpath,chmod)
	def symlink_as(self,path,src,env=None,cwd=None):
		if sys.platform=='win32':
			return
		if not path:
			raise Utils.WafError("where do you want to install %r? (%r?)"%(src,path))
		tgt=self.get_install_path(path,env)
		dir,name=os.path.split(tgt)
		Utils.check_dir(dir)
		if self.is_install>0:
			link=False
			if not os.path.islink(tgt):
				link=True
			elif os.readlink(tgt)!=src:
				link=True
			if link:
				try:os.remove(tgt)
				except OSError:pass
				info('* symlink %s (-> %s)'%(tgt,src))
				os.symlink(src,tgt)
			return 0
		else:
			try:
				info('* removing %s'%(tgt))
				os.remove(tgt)
				return 0
			except OSError:
				return 1
	def exec_command(self,cmd,**kw):
		debug('runner: system command -> %s',cmd)
		if self.log:
			self.log.write('%s\n'%cmd)
			kw['log']=self.log
		try:
			if not kw.get('cwd',None):
				kw['cwd']=self.cwd
		except AttributeError:
			self.cwd=kw['cwd']=self.bldnode.abspath()
		return Utils.exec_command(cmd,**kw)
	def printout(self,s):
		f=self.log or sys.stderr
		f.write(s)
		f.flush()
	def add_subdirs(self,dirs):
		self.recurse(dirs,'build')
	def pre_recurse(self,name_or_mod,path,nexdir):
		if not hasattr(self,'oldpath'):
			self.oldpath=[]
		self.oldpath.append(self.path)
		self.path=self.root.find_dir(nexdir)
		return{'bld':self,'ctx':self}
	def post_recurse(self,name_or_mod,path,nexdir):
		self.path=self.oldpath.pop()
	def pre_build(self):
		if hasattr(self,'pre_funs'):
			for m in self.pre_funs:
				m(self)
	def post_build(self):
		if hasattr(self,'post_funs'):
			for m in self.post_funs:
				m(self)
	def add_pre_fun(self,meth):
		try:self.pre_funs.append(meth)
		except AttributeError:self.pre_funs=[meth]
	def add_post_fun(self,meth):
		try:self.post_funs.append(meth)
		except AttributeError:self.post_funs=[meth]
	def use_the_magic(self):
		Task.algotype=Task.MAXPARALLEL
		Task.file_deps=Task.extract_deps
		self.magic=True
	install_as=group_method(install_as)
	install_files=group_method(install_files)
	symlink_as=group_method(symlink_as)


########NEW FILE########
__FILENAME__ = Configure
#! /usr/bin/env python
# encoding: utf-8

import os,shlex,sys,time
try:import cPickle
except ImportError:import pickle as cPickle
import Environment,Utils,Options,Logs
from Logs import warn
from Constants import*
try:
	from urllib import request
except:
	from urllib import urlopen
else:
	urlopen=request.urlopen
conf_template='''# project %(app)s configured on %(now)s by
# waf %(wafver)s (abi %(abi)s, python %(pyver)x on %(systype)s)
# using %(args)s
#
'''
class ConfigurationError(Utils.WscriptError):
	pass
autoconfig=False
def find_file(filename,path_list):
	for directory in Utils.to_list(path_list):
		if os.path.exists(os.path.join(directory,filename)):
			return directory
	return''
def find_program_impl(env,filename,path_list=[],var=None,environ=None):
	if not environ:
		environ=os.environ
	try:path_list=path_list.split()
	except AttributeError:pass
	if var:
		if env[var]:return env[var]
		if var in environ:env[var]=environ[var]
	if not path_list:path_list=environ.get('PATH','').split(os.pathsep)
	ext=(Options.platform=='win32')and'.exe,.com,.bat,.cmd'or''
	for y in[filename+x for x in ext.split(',')]:
		for directory in path_list:
			x=os.path.join(directory,y)
			if os.path.isfile(x):
				if var:env[var]=x
				return x
	return''
class ConfigurationContext(Utils.Context):
	tests={}
	error_handlers=[]
	def __init__(self,env=None,blddir='',srcdir=''):
		self.env=None
		self.envname=''
		self.environ=dict(os.environ)
		self.line_just=40
		self.blddir=blddir
		self.srcdir=srcdir
		self.all_envs={}
		self.cwd=self.curdir=os.getcwd()
		self.tools=[]
		self.setenv(DEFAULT)
		self.lastprog=''
		self.hash=0
		self.files=[]
		self.tool_cache=[]
		if self.blddir:
			self.post_init()
	def post_init(self):
		self.cachedir=os.path.join(self.blddir,CACHE_DIR)
		path=os.path.join(self.blddir,WAF_CONFIG_LOG)
		try:os.unlink(path)
		except(OSError,IOError):pass
		try:
			self.log=open(path,'w')
		except(OSError,IOError):
			self.fatal('could not open %r for writing'%path)
		app=Utils.g_module.APPNAME
		if app:
			ver=getattr(Utils.g_module,'VERSION','')
			if ver:
				app="%s (%s)"%(app,ver)
		now=time.ctime()
		pyver=sys.hexversion
		systype=sys.platform
		args=" ".join(sys.argv)
		wafver=WAFVERSION
		abi=ABI
		self.log.write(conf_template%vars())
	def __del__(self):
		if hasattr(self,'log')and self.log:
			self.log.close()
	def fatal(self,msg):
		raise ConfigurationError(msg)
	def check_tool(self,input,tooldir=None,funs=None):
		tools=Utils.to_list(input)
		if tooldir:tooldir=Utils.to_list(tooldir)
		for tool in tools:
			tool=tool.replace('++','xx')
			if tool=='java':tool='javaw'
			if tool.lower()=='unittest':tool='unittestw'
			mag=(tool,id(self.env),funs)
			if mag in self.tool_cache:
				continue
			self.tool_cache.append(mag)
			module=None
			try:
				module=Utils.load_tool(tool,tooldir)
			except Exception,e:
				ex=e
				if Options.options.download:
					_3rdparty=os.path.normpath(Options.tooldir[0]+os.sep+'..'+os.sep+'3rdparty')
					for x in Utils.to_list(Options.remote_repo):
						for sub in['branches/waf-%s/wafadmin/3rdparty'%WAFVERSION,'trunk/wafadmin/3rdparty']:
							url='/'.join((x,sub,tool+'.py'))
							try:
								web=urlopen(url)
								if web.getcode()!=200:
									continue
							except Exception,e:
								continue
							else:
								loc=None
								try:
									loc=open(_3rdparty+os.sep+tool+'.py','wb')
									loc.write(web.read())
									web.close()
								finally:
									if loc:
										loc.close()
								Logs.warn('downloaded %s from %s'%(tool,url))
								try:
									module=Utils.load_tool(tool,tooldir)
								except:
									Logs.warn('module %s from %s is unusable'%(tool,url))
									try:
										os.unlink(_3rdparty+os.sep+tool+'.py')
									except:
										pass
									continue
						else:
							break
					if not module:
						Logs.error('Could not load the tool %r or download a suitable replacement from the repository (sys.path %r)\n%s'%(tool,sys.path,e))
						raise ex
				else:
					Logs.error('Could not load the tool %r in %r (try the --download option?):\n%s'%(tool,sys.path,e))
					raise ex
			if funs is not None:
				self.eval_rules(funs)
			else:
				func=getattr(module,'detect',None)
				if func:
					if type(func)is type(find_file):func(self)
					else:self.eval_rules(func)
			self.tools.append({'tool':tool,'tooldir':tooldir,'funs':funs})
	def sub_config(self,k):
		self.recurse(k,name='configure')
	def pre_recurse(self,name_or_mod,path,nexdir):
		return{'conf':self,'ctx':self}
	def post_recurse(self,name_or_mod,path,nexdir):
		if not autoconfig:
			return
		self.hash=hash((self.hash,getattr(name_or_mod,'waf_hash_val',name_or_mod)))
		self.files.append(path)
	def store(self,file=''):
		if not os.path.isdir(self.cachedir):
			os.makedirs(self.cachedir)
		if not file:
			file=open(os.path.join(self.cachedir,'build.config.py'),'w')
		file.write('version = 0x%x\n'%HEXVERSION)
		file.write('tools = %r\n'%self.tools)
		file.close()
		if not self.all_envs:
			self.fatal('nothing to store in the configuration context!')
		for key in self.all_envs:
			tmpenv=self.all_envs[key]
			tmpenv.store(os.path.join(self.cachedir,key+CACHE_SUFFIX))
	def set_env_name(self,name,env):
		self.all_envs[name]=env
		return env
	def retrieve(self,name,fromenv=None):
		try:
			env=self.all_envs[name]
		except KeyError:
			env=Environment.Environment()
			env['PREFIX']=os.path.abspath(os.path.expanduser(Options.options.prefix))
			self.all_envs[name]=env
		else:
			if fromenv:warn("The environment %s may have been configured already"%name)
		return env
	def setenv(self,name):
		self.env=self.retrieve(name)
		self.envname=name
	def add_os_flags(self,var,dest=None):
		try:self.env.append_value(dest or var,Utils.to_list(self.environ[var]))
		except KeyError:pass
	def check_message_1(self,sr):
		self.line_just=max(self.line_just,len(sr))
		for x in('\n',self.line_just*'-','\n',sr,'\n'):
			self.log.write(x)
		Utils.pprint('NORMAL',"%s :"%sr.ljust(self.line_just),sep='')
	def check_message_2(self,sr,color='GREEN'):
		self.log.write(sr)
		self.log.write('\n')
		Utils.pprint(color,sr)
	def check_message(self,th,msg,state,option=''):
		sr='Checking for %s %s'%(th,msg)
		self.check_message_1(sr)
		p=self.check_message_2
		if state:p('ok '+str(option))
		else:p('not found','YELLOW')
	def check_message_custom(self,th,msg,custom,option='',color='PINK'):
		sr='Checking for %s %s'%(th,msg)
		self.check_message_1(sr)
		self.check_message_2(custom,color)
	def start_msg(self,msg):
		try:
			if self.in_msg:
				return
		except:
			self.in_msg=0
		self.in_msg+=1
		self.line_just=max(self.line_just,len(msg))
		for x in('\n',self.line_just*'-','\n',msg,'\n'):
			self.log.write(x)
		Utils.pprint('NORMAL',"%s :"%msg.ljust(self.line_just),sep='')
	def end_msg(self,result):
		self.in_msg-=1
		if self.in_msg:
			return
		color='GREEN'
		if result==True:
			msg='ok'
		elif result==False:
			msg='not found'
			color='YELLOW'
		else:
			msg=str(result)
		self.log.write(msg)
		self.log.write('\n')
		Utils.pprint(color,msg)
	def find_program(self,filename,path_list=[],var=None,mandatory=False):
		ret=None
		if var:
			if self.env[var]:
				ret=self.env[var]
			elif var in os.environ:
				ret=os.environ[var]
		if not isinstance(filename,list):filename=[filename]
		if not ret:
			for x in filename:
				ret=find_program_impl(self.env,x,path_list,var,environ=self.environ)
				if ret:break
		self.check_message_1('Checking for program %s'%' or '.join(filename))
		self.log.write('  find program=%r paths=%r var=%r\n  -> %r\n'%(filename,path_list,var,ret))
		if ret:
			Utils.pprint('GREEN',str(ret))
		else:
			Utils.pprint('YELLOW','not found')
			if mandatory:
				self.fatal('The program %r is required'%filename)
		if var:
			self.env[var]=ret
		return ret
	def cmd_to_list(self,cmd):
		if isinstance(cmd,str)and cmd.find(' '):
			try:
				os.stat(cmd)
			except OSError:
				return shlex.split(cmd)
			else:
				return[cmd]
		return cmd
	def __getattr__(self,name):
		r=self.__class__.__dict__.get(name,None)
		if r:return r
		if name and name.startswith('require_'):
			for k in['check_','find_']:
				n=name.replace('require_',k)
				ret=self.__class__.__dict__.get(n,None)
				if ret:
					def run(*k,**kw):
						r=ret(self,*k,**kw)
						if not r:
							self.fatal('requirement failure')
						return r
					return run
		self.fatal('No such method %r'%name)
	def eval_rules(self,rules):
		self.rules=Utils.to_list(rules)
		for x in self.rules:
			f=getattr(self,x)
			if not f:self.fatal("No such method '%s'."%x)
			try:
				f()
			except Exception,e:
				ret=self.err_handler(x,e)
				if ret==BREAK:
					break
				elif ret==CONTINUE:
					continue
				else:
					self.fatal(e)
	def err_handler(self,fun,error):
		pass
def conf(f):
	setattr(ConfigurationContext,f.__name__,f)
	return f
def conftest(f):
	ConfigurationContext.tests[f.__name__]=f
	return conf(f)


########NEW FILE########
__FILENAME__ = Constants
#! /usr/bin/env python
# encoding: utf-8

HEXVERSION=0x10511
WAFVERSION="1.5.17"
WAFREVISION="8002"
ABI=7
O644=420
O755=493
MAXJOBS=99999999
CACHE_DIR='c4che'
CACHE_SUFFIX='.cache.py'
DBFILE='.wafpickle-%d'%ABI
WSCRIPT_FILE='wscript'
WSCRIPT_BUILD_FILE='wscript_build'
WAF_CONFIG_LOG='config.log'
WAF_CONFIG_H='config.h'
SIG_NIL='iluvcuteoverload'
VARIANT='_VARIANT_'
DEFAULT='default'
SRCDIR='srcdir'
BLDDIR='blddir'
APPNAME='APPNAME'
VERSION='VERSION'
DEFINES='defines'
UNDEFINED=()
BREAK="break"
CONTINUE="continue"
JOBCONTROL="JOBCONTROL"
MAXPARALLEL="MAXPARALLEL"
NORMAL="NORMAL"
NOT_RUN=0
MISSING=1
CRASHED=2
EXCEPTION=3
SKIPPED=8
SUCCESS=9
ASK_LATER=-1
SKIP_ME=-2
RUN_ME=-3
LOG_FORMAT="%(asctime)s %(c1)s%(zone)s%(c2)s %(message)s"
HOUR_FORMAT="%H:%M:%S"
TEST_OK=True
CFG_FILES='cfg_files'
INSTALL=1337
UNINSTALL=-1337


########NEW FILE########
__FILENAME__ = Environment
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,copy,re
import Logs,Options,Utils
from Constants import*
re_imp=re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$',re.M)
class Environment(object):
	__slots__=("table","parent")
	def __init__(self,filename=None):
		self.table={}
		if filename:
			self.load(filename)
	def __contains__(self,key):
		if key in self.table:return True
		try:return self.parent.__contains__(key)
		except AttributeError:return False
	def __str__(self):
		keys=set()
		cur=self
		while cur:
			keys.update(cur.table.keys())
			cur=getattr(cur,'parent',None)
		keys=list(keys)
		keys.sort()
		return"\n".join(["%r %r"%(x,self.__getitem__(x))for x in keys])
	def __getitem__(self,key):
		try:
			while 1:
				x=self.table.get(key,None)
				if not x is None:
					return x
				self=self.parent
		except AttributeError:
			return[]
	def __setitem__(self,key,value):
		self.table[key]=value
	def __delitem__(self,key):
		del self.table[key]
	def pop(self,key,*args):
		if len(args):
			return self.table.pop(key,*args)
		return self.table.pop(key)
	def set_variant(self,name):
		self.table[VARIANT]=name
	def variant(self):
		try:
			while 1:
				x=self.table.get(VARIANT,None)
				if not x is None:
					return x
				self=self.parent
		except AttributeError:
			return DEFAULT
	def copy(self):
		newenv=Environment()
		newenv.parent=self
		return newenv
	def detach(self):
		tbl=self.get_merged_dict()
		try:
			delattr(self,'parent')
		except AttributeError:
			pass
		else:
			keys=tbl.keys()
			for x in keys:
				tbl[x]=copy.deepcopy(tbl[x])
			self.table=tbl
	def get_flat(self,key):
		s=self[key]
		if isinstance(s,str):return s
		return' '.join(s)
	def _get_list_value_for_modification(self,key):
		try:
			value=self.table[key]
		except KeyError:
			try:value=self.parent[key]
			except AttributeError:value=[]
			if isinstance(value,list):
				value=value[:]
			else:
				value=[value]
		else:
			if not isinstance(value,list):
				value=[value]
		self.table[key]=value
		return value
	def append_value(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			current_value.extend(value)
		else:
			current_value.append(value)
	def prepend_value(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			current_value=value+current_value
			self.table[var]=current_value
		else:
			current_value.insert(0,value)
	def append_unique(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			for value_item in value:
				if value_item not in current_value:
					current_value.append(value_item)
		else:
			if value not in current_value:
				current_value.append(value)
	def get_merged_dict(self):
		table_list=[]
		env=self
		while 1:
			table_list.insert(0,env.table)
			try:env=env.parent
			except AttributeError:break
		merged_table={}
		for table in table_list:
			merged_table.update(table)
		return merged_table
	def store(self,filename):
		file=open(filename,'w')
		merged_table=self.get_merged_dict()
		keys=list(merged_table.keys())
		keys.sort()
		for k in keys:file.write('%s = %r\n'%(k,merged_table[k]))
		file.close()
	def load(self,filename):
		tbl=self.table
		code=Utils.readf(filename)
		for m in re_imp.finditer(code):
			g=m.group
			tbl[g(2)]=eval(g(3))
		Logs.debug('env: %s',self.table)
	def get_destdir(self):
		if self.__getitem__('NOINSTALL'):return''
		return Options.options.destdir
	def update(self,d):
		for k,v in d.iteritems():
			self[k]=v
	def __getattr__(self,name):
		if name in self.__slots__:
			return object.__getattr__(self,name)
		else:
			return self[name]
	def __setattr__(self,name,value):
		if name in self.__slots__:
			object.__setattr__(self,name,value)
		else:
			self[name]=value
	def __delattr__(self,name):
		if name in self.__slots__:
			object.__delattr__(self,name)
		else:
			del self[name]


########NEW FILE########
__FILENAME__ = Logs
#! /usr/bin/env python
# encoding: utf-8

import ansiterm
import os,re,logging,traceback,sys
from Constants import*
zones=''
verbose=0
colors_lst={'USE':True,'BOLD':'\x1b[01;1m','RED':'\x1b[01;31m','GREEN':'\x1b[32m','YELLOW':'\x1b[33m','PINK':'\x1b[35m','BLUE':'\x1b[01;34m','CYAN':'\x1b[36m','NORMAL':'\x1b[0m','cursor_on':'\x1b[?25h','cursor_off':'\x1b[?25l',}
got_tty=False
term=os.environ.get('TERM','dumb')
if not term in['dumb','emacs']:
	try:
		got_tty=sys.stderr.isatty()or(sys.platform=='win32'and term in['xterm','msys'])
	except AttributeError:
		pass
import Utils
if not got_tty or'NOCOLOR'in os.environ:
	colors_lst['USE']=False
def get_color(cl):
	if not colors_lst['USE']:return''
	return colors_lst.get(cl,'')
class foo(object):
	def __getattr__(self,a):
		return get_color(a)
	def __call__(self,a):
		return get_color(a)
colors=foo()
re_log=re.compile(r'(\w+): (.*)',re.M)
class log_filter(logging.Filter):
	def __init__(self,name=None):
		pass
	def filter(self,rec):
		rec.c1=colors.PINK
		rec.c2=colors.NORMAL
		rec.zone=rec.module
		if rec.levelno>=logging.INFO:
			if rec.levelno>=logging.ERROR:
				rec.c1=colors.RED
			elif rec.levelno>=logging.WARNING:
				rec.c1=colors.YELLOW
			else:
				rec.c1=colors.GREEN
			return True
		zone=''
		m=re_log.match(rec.msg)
		if m:
			zone=rec.zone=m.group(1)
			rec.msg=m.group(2)
		if zones:
			return getattr(rec,'zone','')in zones or'*'in zones
		elif not verbose>2:
			return False
		return True
class formatter(logging.Formatter):
	def __init__(self):
		logging.Formatter.__init__(self,LOG_FORMAT,HOUR_FORMAT)
	def format(self,rec):
		if rec.levelno>=logging.WARNING or rec.levelno==logging.INFO:
			try:
				return'%s%s%s'%(rec.c1,rec.msg.decode('utf-8'),rec.c2)
			except:
				return rec.c1+rec.msg+rec.c2
		return logging.Formatter.format(self,rec)
def debug(*k,**kw):
	if verbose:
		k=list(k)
		k[0]=k[0].replace('\n',' ')
		logging.debug(*k,**kw)
def error(*k,**kw):
	logging.error(*k,**kw)
	if verbose>1:
		if isinstance(k[0],Utils.WafError):
			st=k[0].stack
		else:
			st=traceback.extract_stack()
		if st:
			st=st[:-1]
			buf=[]
			for filename,lineno,name,line in st:
				buf.append('  File "%s", line %d, in %s'%(filename,lineno,name))
				if line:
					buf.append('	%s'%line.strip())
			if buf:logging.error("\n".join(buf))
warn=logging.warn
info=logging.info
def init_log():
	log=logging.getLogger()
	log.handlers=[]
	log.filters=[]
	hdlr=logging.StreamHandler()
	hdlr.setFormatter(formatter())
	log.addHandler(hdlr)
	log.addFilter(log_filter())
	log.setLevel(logging.DEBUG)
init_log()


########NEW FILE########
__FILENAME__ = Node
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,sys,fnmatch,re,stat
import Utils,Constants
UNDEFINED=0
DIR=1
FILE=2
BUILD=3
type_to_string={UNDEFINED:"unk",DIR:"dir",FILE:"src",BUILD:"bld"}
prune_pats='.git .bzr .hg .svn _MTN _darcs CVS SCCS'.split()
exclude_pats=prune_pats+'*~ #*# .#* %*% ._* .gitignore .cvsignore vssver.scc .DS_Store'.split()
exclude_regs='''
**/*~
**/#*#
**/.#*
**/%*%
**/._*
**/CVS
**/CVS/**
**/.cvsignore
**/SCCS
**/SCCS/**
**/vssver.scc
**/.svn
**/.svn/**
**/.git
**/.git/**
**/.gitignore
**/.bzr
**/.bzr/**
**/.hg
**/.hg/**
**/_MTN
**/_MTN/**
**/_darcs
**/_darcs/**
**/.DS_Store'''
class Node(object):
	__slots__=("name","parent","id","childs")
	def __init__(self,name,parent,node_type=UNDEFINED):
		self.name=name
		self.parent=parent
		self.__class__.bld.id_nodes+=4
		self.id=self.__class__.bld.id_nodes+node_type
		if node_type==DIR:self.childs={}
		if parent and name in parent.childs:
			raise Utils.WafError('node %s exists in the parent files %r already'%(name,parent))
		if parent:parent.childs[name]=self
	def __setstate__(self,data):
		if len(data)==4:
			(self.parent,self.name,self.id,self.childs)=data
		else:
			(self.parent,self.name,self.id)=data
	def __getstate__(self):
		if getattr(self,'childs',None)is None:
			return(self.parent,self.name,self.id)
		else:
			return(self.parent,self.name,self.id,self.childs)
	def __str__(self):
		if not self.parent:return''
		return"%s://%s"%(type_to_string[self.id&3],self.abspath())
	def __repr__(self):
		return self.__str__()
	def __hash__(self):
		raise Utils.WafError('nodes, you are doing it wrong')
	def __copy__(self):
		raise Utils.WafError('nodes are not supposed to be cloned')
	def get_type(self):
		return self.id&3
	def set_type(self,t):
		self.id=self.id+t-self.id&3
	def dirs(self):
		return[x for x in self.childs.values()if x.id&3==DIR]
	def files(self):
		return[x for x in self.childs.values()if x.id&3==FILE]
	def get_dir(self,name,default=None):
		node=self.childs.get(name,None)
		if not node or node.id&3!=DIR:return default
		return node
	def get_file(self,name,default=None):
		node=self.childs.get(name,None)
		if not node or node.id&3!=FILE:return default
		return node
	def get_build(self,name,default=None):
		node=self.childs.get(name,None)
		if not node or node.id&3!=BUILD:return default
		return node
	def find_resource(self,lst):
		if isinstance(lst,str):
			lst=Utils.split_path(lst)
		if len(lst)==1:
			parent=self
		else:
			parent=self.find_dir(lst[:-1])
			if not parent:return None
		self.__class__.bld.rescan(parent)
		name=lst[-1]
		node=parent.childs.get(name,None)
		if node:
			tp=node.id&3
			if tp==FILE or tp==BUILD:
				return node
			else:
				return None
		tree=self.__class__.bld
		if not name in tree.cache_dir_contents[parent.id]:
			return None
		path=parent.abspath()+os.sep+name
		try:
			st=Utils.h_file(path)
		except IOError:
			return None
		child=self.__class__(name,parent,FILE)
		tree.node_sigs[0][child.id]=st
		return child
	def find_or_declare(self,lst):
		if isinstance(lst,str):
			lst=Utils.split_path(lst)
		if len(lst)==1:
			parent=self
		else:
			parent=self.find_dir(lst[:-1])
			if not parent:return None
		self.__class__.bld.rescan(parent)
		name=lst[-1]
		node=parent.childs.get(name,None)
		if node:
			tp=node.id&3
			if tp!=BUILD:
				raise Utils.WafError('find_or_declare found a source file where a build file was expected %r'%'/'.join(lst))
			return node
		node=self.__class__(name,parent,BUILD)
		return node
	def find_dir(self,lst):
		if isinstance(lst,str):
			lst=Utils.split_path(lst)
		current=self
		for name in lst:
			self.__class__.bld.rescan(current)
			prev=current
			if not current.parent and name==current.name:
				continue
			elif not name:
				continue
			elif name=='.':
				continue
			elif name=='..':
				current=current.parent or current
			else:
				current=prev.childs.get(name,None)
				if current is None:
					dir_cont=self.__class__.bld.cache_dir_contents
					if prev.id in dir_cont and name in dir_cont[prev.id]:
						if not prev.name:
							if os.sep=='/':
								dirname=os.sep+name
							else:
								dirname=name
						else:
							dirname=prev.abspath()+os.sep+name
						if not os.path.isdir(dirname):
							return None
						current=self.__class__(name,prev,DIR)
					elif(not prev.name and len(name)==2 and name[1]==':')or name.startswith('\\\\'):
						current=self.__class__(name,prev,DIR)
					else:
						return None
				else:
					if current.id&3!=DIR:
						return None
		return current
	def ensure_dir_node_from_path(self,lst):
		if isinstance(lst,str):
			lst=Utils.split_path(lst)
		current=self
		for name in lst:
			if not name:
				continue
			elif name=='.':
				continue
			elif name=='..':
				current=current.parent or current
			else:
				prev=current
				current=prev.childs.get(name,None)
				if current is None:
					current=self.__class__(name,prev,DIR)
		return current
	def exclusive_build_node(self,path):
		lst=Utils.split_path(path)
		name=lst[-1]
		if len(lst)>1:
			parent=None
			try:
				parent=self.find_dir(lst[:-1])
			except OSError:
				pass
			if not parent:
				parent=self.ensure_dir_node_from_path(lst[:-1])
				self.__class__.bld.rescan(parent)
			else:
				try:
					self.__class__.bld.rescan(parent)
				except OSError:
					pass
		else:
			parent=self
		node=parent.childs.get(name,None)
		if not node:
			node=self.__class__(name,parent,BUILD)
		return node
	def path_to_parent(self,parent):
		lst=[]
		p=self
		h1=parent.height()
		h2=p.height()
		while h2>h1:
			h2-=1
			lst.append(p.name)
			p=p.parent
		if lst:
			lst.reverse()
			ret=os.path.join(*lst)
		else:
			ret=''
		return ret
	def find_ancestor(self,node):
		dist=self.height()-node.height()
		if dist<0:return node.find_ancestor(self)
		cand=self
		while dist>0:
			cand=cand.parent
			dist-=1
		if cand==node:return cand
		cursor=node
		while cand.parent:
			cand=cand.parent
			cursor=cursor.parent
			if cand==cursor:return cand
	def relpath_gen(self,from_node):
		if self==from_node:return'.'
		if from_node.parent==self:return'..'
		ancestor=self.find_ancestor(from_node)
		lst=[]
		cand=self
		while not cand.id==ancestor.id:
			lst.append(cand.name)
			cand=cand.parent
		cand=from_node
		while not cand.id==ancestor.id:
			lst.append('..')
			cand=cand.parent
		lst.reverse()
		return os.sep.join(lst)
	def nice_path(self,env=None):
		tree=self.__class__.bld
		ln=tree.launch_node()
		if self.id&3==FILE:return self.relpath_gen(ln)
		else:return os.path.join(tree.bldnode.relpath_gen(ln),env.variant(),self.relpath_gen(tree.srcnode))
	def is_child_of(self,node):
		p=self
		diff=self.height()-node.height()
		while diff>0:
			diff-=1
			p=p.parent
		return p.id==node.id
	def variant(self,env):
		if not env:return 0
		elif self.id&3==FILE:return 0
		else:return env.variant()
	def height(self):
		d=self
		val=-1
		while d:
			d=d.parent
			val+=1
		return val
	def abspath(self,env=None):
		variant=(env and(self.id&3!=FILE)and env.variant())or 0
		ret=self.__class__.bld.cache_node_abspath[variant].get(self.id,None)
		if ret:return ret
		if not variant:
			if not self.parent:
				val=os.sep=='/'and os.sep or''
			elif not self.parent.name:
				val=(os.sep=='/'and os.sep or'')+self.name
			else:
				val=self.parent.abspath()+os.sep+self.name
		else:
			val=os.sep.join((self.__class__.bld.bldnode.abspath(),variant,self.path_to_parent(self.__class__.bld.srcnode)))
		self.__class__.bld.cache_node_abspath[variant][self.id]=val
		return val
	def change_ext(self,ext):
		name=self.name
		k=name.rfind('.')
		if k>=0:
			name=name[:k]+ext
		else:
			name=name+ext
		return self.parent.find_or_declare([name])
	def src_dir(self,env):
		return self.parent.srcpath(env)
	def bld_dir(self,env):
		return self.parent.bldpath(env)
	def bld_base(self,env):
		s=os.path.splitext(self.name)[0]
		return os.path.join(self.bld_dir(env),s)
	def bldpath(self,env=None):
		if self.id&3==FILE:
			return self.relpath_gen(self.__class__.bld.bldnode)
		p=self.path_to_parent(self.__class__.bld.srcnode)
		if p is not'':
			return env.variant()+os.sep+p
		return env.variant()
	def srcpath(self,env=None):
		if self.id&3==BUILD:
			return self.bldpath(env)
		return self.relpath_gen(self.__class__.bld.bldnode)
	def read(self,env):
		return Utils.readf(self.abspath(env))
	def dir(self,env):
		return self.parent.abspath(env)
	def file(self):
		return self.name
	def file_base(self):
		return os.path.splitext(self.name)[0]
	def suffix(self):
		k=max(0,self.name.rfind('.'))
		return self.name[k:]
	def find_iter_impl(self,src=True,bld=True,dir=True,accept_name=None,is_prune=None,maxdepth=25):
		bld_ctx=self.__class__.bld
		bld_ctx.rescan(self)
		for name in bld_ctx.cache_dir_contents[self.id]:
			if accept_name(self,name):
				node=self.find_resource(name)
				if node:
					if src and node.id&3==FILE:
						yield node
				else:
					node=self.find_dir(name)
					if node and node.id!=bld_ctx.bldnode.id:
						if dir:
							yield node
						if not is_prune(self,name):
							if maxdepth:
								for k in node.find_iter_impl(src,bld,dir,accept_name,is_prune,maxdepth=maxdepth-1):
									yield k
			else:
				if not is_prune(self,name):
					node=self.find_resource(name)
					if not node:
						node=self.find_dir(name)
						if node and node.id!=bld_ctx.bldnode.id:
							if maxdepth:
								for k in node.find_iter_impl(src,bld,dir,accept_name,is_prune,maxdepth=maxdepth-1):
									yield k
		if bld:
			for node in self.childs.values():
				if node.id==bld_ctx.bldnode.id:
					continue
				if node.id&3==BUILD:
					if accept_name(self,node.name):
						yield node
		raise StopIteration
	def find_iter(self,in_pat=['*'],ex_pat=exclude_pats,prune_pat=prune_pats,src=True,bld=True,dir=False,maxdepth=25,flat=False):
		if not(src or bld or dir):
			raise StopIteration
		if self.id&3!=DIR:
			raise StopIteration
		in_pat=Utils.to_list(in_pat)
		ex_pat=Utils.to_list(ex_pat)
		prune_pat=Utils.to_list(prune_pat)
		def accept_name(node,name):
			for pat in ex_pat:
				if fnmatch.fnmatchcase(name,pat):
					return False
			for pat in in_pat:
				if fnmatch.fnmatchcase(name,pat):
					return True
			return False
		def is_prune(node,name):
			for pat in prune_pat:
				if fnmatch.fnmatchcase(name,pat):
					return True
			return False
		ret=self.find_iter_impl(src,bld,dir,accept_name,is_prune,maxdepth=maxdepth)
		if flat:
			return" ".join([x.relpath_gen(self)for x in ret])
		return ret
	def ant_glob(self,*k,**kw):
		src=kw.get('src',1)
		bld=kw.get('bld',0)
		dir=kw.get('dir',0)
		excl=kw.get('excl',exclude_regs)
		incl=k and k[0]or kw.get('incl','**')
		def to_pat(s):
			lst=Utils.to_list(s)
			ret=[]
			for x in lst:
				x=x.replace('//','/')
				if x.endswith('/'):
					x+='**'
				lst2=x.split('/')
				accu=[]
				for k in lst2:
					if k=='**':
						accu.append(k)
					else:
						k=k.replace('.','[.]').replace('*','.*').replace('?','.')
						k='^%s$'%k
						accu.append(re.compile(k))
				ret.append(accu)
			return ret
		def filtre(name,nn):
			ret=[]
			for lst in nn:
				if not lst:
					pass
				elif lst[0]=='**':
					ret.append(lst)
					if len(lst)>1:
						if lst[1].match(name):
							ret.append(lst[2:])
					else:
						ret.append([])
				elif lst[0].match(name):
					ret.append(lst[1:])
			return ret
		def accept(name,pats):
			nacc=filtre(name,pats[0])
			nrej=filtre(name,pats[1])
			if[]in nrej:
				nacc=[]
			return[nacc,nrej]
		def ant_iter(nodi,maxdepth=25,pats=[]):
			nodi.__class__.bld.rescan(nodi)
			for name in nodi.__class__.bld.cache_dir_contents[nodi.id]:
				npats=accept(name,pats)
				if npats and npats[0]:
					accepted=[]in npats[0]
					node=nodi.find_resource(name)
					if node and accepted:
						if src and node.id&3==FILE:
							yield node
					else:
						node=nodi.find_dir(name)
						if node and node.id!=nodi.__class__.bld.bldnode.id:
							if accepted and dir:
								yield node
							if maxdepth:
								for k in ant_iter(node,maxdepth=maxdepth-1,pats=npats):
									yield k
			if bld:
				for node in nodi.childs.values():
					if node.id==nodi.__class__.bld.bldnode.id:
						continue
					if node.id&3==BUILD:
						npats=accept(node.name,pats)
						if npats and npats[0]and[]in npats[0]:
							yield node
			raise StopIteration
		ret=[x for x in ant_iter(self,pats=[to_pat(incl),to_pat(excl)])]
		if kw.get('flat',True):
			return" ".join([x.relpath_gen(self)for x in ret])
		return ret
	def update_build_dir(self,env=None):
		if not env:
			for env in bld.all_envs:
				self.update_build_dir(env)
			return
		path=self.abspath(env)
		lst=Utils.listdir(path)
		try:
			self.__class__.bld.cache_dir_contents[self.id].update(lst)
		except KeyError:
			self.__class__.bld.cache_dir_contents[self.id]=set(lst)
		self.__class__.bld.cache_scanned_folders[self.id]=True
		for k in lst:
			npath=path+os.sep+k
			st=os.stat(npath)
			if stat.S_ISREG(st[stat.ST_MODE]):
				ick=self.find_or_declare(k)
				if not(ick.id in self.__class__.bld.node_sigs[env.variant()]):
					self.__class__.bld.node_sigs[env.variant()][ick.id]=Constants.SIG_NIL
			elif stat.S_ISDIR(st[stat.ST_MODE]):
				child=self.find_dir(k)
				if not child:
					child=self.ensure_dir_node_from_path(k)
				child.update_build_dir(env)
class Nodu(Node):
	pass


########NEW FILE########
__FILENAME__ = Options
#! /usr/bin/env python
# encoding: utf-8

import os,sys,imp,types,tempfile,optparse
import Logs,Utils
from Constants import*
cmds='distclean configure build install clean uninstall check dist distcheck'.split()
commands={}
is_install=False
options={}
arg_line=[]
launch_dir=''
tooldir=''
lockfile=os.environ.get('WAFLOCK','.lock-wscript')
try:cache_global=os.path.abspath(os.environ['WAFCACHE'])
except KeyError:cache_global=''
platform=Utils.unversioned_sys_platform()
conf_file='conf-runs-%s-%d.pickle'%(platform,ABI)
remote_repo=['http://waf.googlecode.com/svn/']
default_prefix=os.environ.get('PREFIX')
if not default_prefix:
	if platform=='win32':
		d=tempfile.gettempdir()
		default_prefix=d[0].upper()+d[1:]
	else:default_prefix='/usr/local/'
default_jobs=os.environ.get('JOBS',-1)
if default_jobs<1:
	try:
		if'SC_NPROCESSORS_ONLN'in os.sysconf_names:
			default_jobs=os.sysconf('SC_NPROCESSORS_ONLN')
		else:
			default_jobs=int(Utils.cmd_output(['sysctl','-n','hw.ncpu']))
	except:
		if os.name=='java':
			from java.lang import Runtime
			default_jobs=Runtime.getRuntime().availableProcessors()
		else:
			default_jobs=int(os.environ.get('NUMBER_OF_PROCESSORS',1))
default_destdir=os.environ.get('DESTDIR','')
def get_usage(self):
	cmds_str=[]
	module=Utils.g_module
	if module:
		tbl=module.__dict__
		keys=list(tbl.keys())
		keys.sort()
		if'build'in tbl:
			if not module.build.__doc__:
				module.build.__doc__='builds the project'
		if'configure'in tbl:
			if not module.configure.__doc__:
				module.configure.__doc__='configures the project'
		ban=['set_options','init','shutdown']
		optlst=[x for x in keys if not x in ban and type(tbl[x])is type(parse_args_impl)and tbl[x].__doc__ and not x.startswith('_')]
		just=max([len(x)for x in optlst])
		for x in optlst:
			cmds_str.append('  %s: %s'%(x.ljust(just),tbl[x].__doc__))
		ret='\n'.join(cmds_str)
	else:
		ret=' '.join(cmds)
	return'''waf [command] [options]

Main commands (example: ./waf build -j4)
%s
'''%ret
setattr(optparse.OptionParser,'get_usage',get_usage)
def create_parser(module=None):
	Logs.debug('options: create_parser is called')
	parser=optparse.OptionParser(conflict_handler="resolve",version='waf %s (%s)'%(WAFVERSION,WAFREVISION))
	parser.formatter.width=Utils.get_term_cols()
	p=parser.add_option
	p('-j','--jobs',type='int',default=default_jobs,help='amount of parallel jobs (%r)'%default_jobs,dest='jobs')
	p('-k','--keep',action='store_true',default=False,help='keep running happily on independent task groups',dest='keep')
	p('-v','--verbose',action='count',default=0,help='verbosity level -v -vv or -vvv [default: 0]',dest='verbose')
	p('--nocache',action='store_true',default=False,help='ignore the WAFCACHE (if set)',dest='nocache')
	p('--zones',action='store',default='',help='debugging zones (task_gen, deps, tasks, etc)',dest='zones')
	p('-p','--progress',action='count',default=0,help='-p: progress bar; -pp: ide output',dest='progress_bar')
	p('--targets',action='store',default='',help='build given task generators, e.g. "target1,target2"',dest='compile_targets')
	gr=optparse.OptionGroup(parser,'configuration options')
	parser.add_option_group(gr)
	gr.add_option('-b','--blddir',action='store',default='',help='build dir for the project (configuration)',dest='blddir')
	gr.add_option('-s','--srcdir',action='store',default='',help='src dir for the project (configuration)',dest='srcdir')
	gr.add_option('--prefix',help='installation prefix (configuration) [default: %r]'%default_prefix,default=default_prefix,dest='prefix')
	gr.add_option('--download',action='store_true',default=False,help='try to download the tools if missing',dest='download')
	gr=optparse.OptionGroup(parser,'installation options')
	parser.add_option_group(gr)
	gr.add_option('--destdir',help='installation root [default: %r]'%default_destdir,default=default_destdir,dest='destdir')
	gr.add_option('-f','--force',action='store_true',default=False,help='force file installation',dest='force')
	return parser
def parse_args_impl(parser,_args=None):
	global options,commands,arg_line
	(options,args)=parser.parse_args(args=_args)
	arg_line=args
	commands={}
	for var in cmds:commands[var]=0
	if not args:
		commands['build']=1
		args.append('build')
	for arg in args:
		commands[arg]=True
	if'check'in args:
		idx=args.index('check')
		try:
			bidx=args.index('build')
			if bidx>idx:
				raise ValueError('build before check')
		except ValueError,e:
			args.insert(idx,'build')
	if args[0]!='init':
		args.insert(0,'init')
	if options.keep:options.jobs=1
	if options.jobs<1:options.jobs=1
	if'install'in sys.argv or'uninstall'in sys.argv:
		options.destdir=options.destdir and os.path.abspath(os.path.expanduser(options.destdir))
	Logs.verbose=options.verbose
	Logs.init_log()
	if options.zones:
		Logs.zones=options.zones.split(',')
		if not Logs.verbose:Logs.verbose=1
	elif Logs.verbose>0:
		Logs.zones=['runner']
	if Logs.verbose>2:
		Logs.zones=['*']
class Handler(Utils.Context):
	parser=None
	def __init__(self,module=None):
		self.parser=create_parser(module)
		self.cwd=os.getcwd()
		Handler.parser=self
	def add_option(self,*k,**kw):
		self.parser.add_option(*k,**kw)
	def add_option_group(self,*k,**kw):
		return self.parser.add_option_group(*k,**kw)
	def get_option_group(self,opt_str):
		return self.parser.get_option_group(opt_str)
	def sub_options(self,*k,**kw):
		if not k:raise Utils.WscriptError('folder expected')
		self.recurse(k[0],name='set_options')
	def tool_options(self,*k,**kw):
		
		if not k[0]:
			raise Utils.WscriptError('invalid tool_options call %r %r'%(k,kw))
		tools=Utils.to_list(k[0])
		path=Utils.to_list(kw.get('tdir',kw.get('tooldir',tooldir)))
		for tool in tools:
			tool=tool.replace('++','xx')
			if tool=='java':tool='javaw'
			if tool.lower()=='unittest':tool='unittestw'
			module=Utils.load_tool(tool,path)
			try:
				fun=module.set_options
			except AttributeError:
				pass
			else:
				fun(kw.get('option_group',self))
	def parse_args(self,args=None):
		parse_args_impl(self.parser,args)


########NEW FILE########
__FILENAME__ = Runner
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,sys,random,time,threading,traceback
try:from Queue import Queue
except ImportError:from queue import Queue
import Build,Utils,Logs,Options
from Logs import debug,error
from Constants import*
GAP=15
run_old=threading.Thread.run
def run(*args,**kwargs):
	try:
		run_old(*args,**kwargs)
	except(KeyboardInterrupt,SystemExit):
		raise
	except:
		sys.excepthook(*sys.exc_info())
threading.Thread.run=run
class TaskConsumer(threading.Thread):
	ready=Queue(0)
	consumers=[]
	def __init__(self):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.start()
	def run(self):
		try:
			self.loop()
		except:
			pass
	def loop(self):
		while 1:
			tsk=TaskConsumer.ready.get()
			m=tsk.master
			if m.stop:
				m.out.put(tsk)
				continue
			try:
				tsk.generator.bld.printout(tsk.display())
				if tsk.__class__.stat:ret=tsk.__class__.stat(tsk)
				else:ret=tsk.call_run()
			except Exception,e:
				tsk.err_msg=Utils.ex_stack()
				tsk.hasrun=EXCEPTION
				m.error_handler(tsk)
				m.out.put(tsk)
				continue
			if ret:
				tsk.err_code=ret
				tsk.hasrun=CRASHED
			else:
				try:
					tsk.post_run()
				except Utils.WafError:
					pass
				except Exception:
					tsk.err_msg=Utils.ex_stack()
					tsk.hasrun=EXCEPTION
				else:
					tsk.hasrun=SUCCESS
			if tsk.hasrun!=SUCCESS:
				m.error_handler(tsk)
			m.out.put(tsk)
class Parallel(object):
	def __init__(self,bld,j=2):
		self.numjobs=j
		self.manager=bld.task_manager
		self.manager.current_group=0
		self.total=self.manager.total()
		self.outstanding=[]
		self.maxjobs=MAXJOBS
		self.frozen=[]
		self.out=Queue(0)
		self.count=0
		self.processed=1
		self.stop=False
		self.error=False
	def get_next(self):
		if not self.outstanding:
			return None
		return self.outstanding.pop(0)
	def postpone(self,tsk):
		if random.randint(0,1):
			self.frozen.insert(0,tsk)
		else:
			self.frozen.append(tsk)
	def refill_task_list(self):
		while self.count>self.numjobs+GAP or self.count>=self.maxjobs:
			self.get_out()
		while not self.outstanding:
			if self.count:
				self.get_out()
			if self.frozen:
				self.outstanding+=self.frozen
				self.frozen=[]
			elif not self.count:
				(jobs,tmp)=self.manager.get_next_set()
				if jobs!=None:self.maxjobs=jobs
				if tmp:self.outstanding+=tmp
				break
	def get_out(self):
		ret=self.out.get()
		self.manager.add_finished(ret)
		if not self.stop and getattr(ret,'more_tasks',None):
			self.outstanding+=ret.more_tasks
			self.total+=len(ret.more_tasks)
		self.count-=1
	def error_handler(self,tsk):
		if not Options.options.keep:
			self.stop=True
		self.error=True
	def start(self):
		if TaskConsumer.consumers:
			while len(TaskConsumer.consumers)<self.numjobs:
				TaskConsumer.consumers.append(TaskConsumer())
		while not self.stop:
			self.refill_task_list()
			tsk=self.get_next()
			if not tsk:
				if self.count:
					continue
				else:
					break
			if tsk.hasrun:
				self.processed+=1
				self.manager.add_finished(tsk)
				continue
			try:
				st=tsk.runnable_status()
			except Exception,e:
				self.processed+=1
				if self.stop and not Options.options.keep:
					tsk.hasrun=SKIPPED
					self.manager.add_finished(tsk)
					continue
				self.error_handler(tsk)
				self.manager.add_finished(tsk)
				tsk.hasrun=EXCEPTION
				tsk.err_msg=Utils.ex_stack()
				continue
			if st==ASK_LATER:
				self.postpone(tsk)
			elif st==SKIP_ME:
				self.processed+=1
				tsk.hasrun=SKIPPED
				self.manager.add_finished(tsk)
			else:
				tsk.position=(self.processed,self.total)
				self.count+=1
				tsk.master=self
				TaskConsumer.ready.put(tsk)
				self.processed+=1
				if not TaskConsumer.consumers:
					TaskConsumer.consumers=[TaskConsumer()for i in xrange(self.numjobs)]
		while self.error and self.count:
			self.get_out()
		assert(self.count==0 or self.stop)


########NEW FILE########
__FILENAME__ = Scripting
#! /usr/bin/env python
# encoding: utf-8

import os,sys,shutil,traceback,datetime,inspect,errno
import Utils,Configure,Build,Logs,Options,Environment,Task
from Logs import error,warn,info
from Constants import*
g_gz='bz2'
commands=[]
def prepare_impl(t,cwd,ver,wafdir):
	Options.tooldir=[t]
	Options.launch_dir=cwd
	if'--version'in sys.argv:
		opt_obj=Options.Handler()
		opt_obj.curdir=cwd
		opt_obj.parse_args()
		sys.exit(0)
	msg1='Waf: Please run waf from a directory containing a file named "%s" or run distclean'%WSCRIPT_FILE
	build_dir_override=None
	candidate=None
	lst=os.listdir(cwd)
	search_for_candidate=True
	if WSCRIPT_FILE in lst:
		candidate=cwd
	elif'configure'in sys.argv and not WSCRIPT_BUILD_FILE in lst:
		calldir=os.path.abspath(os.path.dirname(sys.argv[0]))
		if WSCRIPT_FILE in os.listdir(calldir):
			candidate=calldir
			search_for_candidate=False
		else:
			error('arg[0] directory does not contain a wscript file')
			sys.exit(1)
		build_dir_override=cwd
	while search_for_candidate:
		if len(cwd)<=3:
			break
		dirlst=os.listdir(cwd)
		if WSCRIPT_FILE in dirlst:
			candidate=cwd
		if'configure'in sys.argv and candidate:
			break
		if Options.lockfile in dirlst:
			env=Environment.Environment()
			try:
				env.load(os.path.join(cwd,Options.lockfile))
			except:
				error('could not load %r'%Options.lockfile)
			try:
				os.stat(env['cwd'])
			except:
				candidate=cwd
			else:
				candidate=env['cwd']
			break
		cwd=os.path.dirname(cwd)
	if not candidate:
		if'-h'in sys.argv or'--help'in sys.argv:
			warn('No wscript file found: the help message may be incomplete')
			opt_obj=Options.Handler()
			opt_obj.curdir=cwd
			opt_obj.parse_args()
		else:
			error(msg1)
		sys.exit(0)
	try:
		os.chdir(candidate)
	except OSError:
		raise Utils.WafError("the folder %r is unreadable"%candidate)
	Utils.set_main_module(os.path.join(candidate,WSCRIPT_FILE))
	if build_dir_override:
		d=getattr(Utils.g_module,BLDDIR,None)
		if d:
			msg=' Overriding build directory %s with %s'%(d,build_dir_override)
			warn(msg)
		Utils.g_module.blddir=build_dir_override
	def set_def(obj,name=''):
		n=name or obj.__name__
		if not n in Utils.g_module.__dict__:
			setattr(Utils.g_module,n,obj)
	for k in[dist,distclean,distcheck,clean,install,uninstall]:
		set_def(k)
	set_def(Configure.ConfigurationContext,'configure_context')
	for k in['build','clean','install','uninstall']:
		set_def(Build.BuildContext,k+'_context')
	opt_obj=Options.Handler(Utils.g_module)
	opt_obj.curdir=candidate
	try:
		f=Utils.g_module.set_options
	except AttributeError:
		pass
	else:
		opt_obj.sub_options([''])
	opt_obj.parse_args()
	if not'init'in Utils.g_module.__dict__:
		Utils.g_module.init=Utils.nada
	if not'shutdown'in Utils.g_module.__dict__:
		Utils.g_module.shutdown=Utils.nada
	main()
def prepare(t,cwd,ver,wafdir):
	if WAFVERSION!=ver:
		msg='Version mismatch: waf %s <> wafadmin %s (wafdir %s)'%(ver,WAFVERSION,wafdir)
		print('\033[91mError: %s\033[0m'%msg)
		sys.exit(1)
	try:
		prepare_impl(t,cwd,ver,wafdir)
	except Utils.WafError,e:
		error(str(e))
		sys.exit(1)
	except KeyboardInterrupt:
		Utils.pprint('RED','Interrupted')
		sys.exit(68)
def main():
	global commands
	commands=Options.arg_line[:]
	while commands:
		x=commands.pop(0)
		ini=datetime.datetime.now()
		if x=='configure':
			fun=configure
		elif x=='build':
			fun=build
		else:
			fun=getattr(Utils.g_module,x,None)
		if not fun:
			raise Utils.WscriptError('No such command %r'%x)
		ctx=getattr(Utils.g_module,x+'_context',Utils.Context)()
		if x in['init','shutdown','dist','distclean','distcheck']:
			try:
				fun(ctx)
			except TypeError:
				fun()
		else:
			fun(ctx)
		ela=''
		if not Options.options.progress_bar:
			ela=' (%s)'%Utils.get_elapsed_time(ini)
		if x!='init'and x!='shutdown':
			info('%r finished successfully%s'%(x,ela))
		if not commands and x!='shutdown':
			commands.append('shutdown')
def configure(conf):
	src=getattr(Options.options,SRCDIR,None)
	if not src:src=getattr(Utils.g_module,SRCDIR,None)
	if not src:src=getattr(Utils.g_module,'top',None)
	if not src:
		src='.'
		incomplete_src=1
	src=os.path.abspath(src)
	bld=getattr(Options.options,BLDDIR,None)
	if not bld:bld=getattr(Utils.g_module,BLDDIR,None)
	if not bld:bld=getattr(Utils.g_module,'out',None)
	if not bld:
		bld='build'
		incomplete_bld=1
	if bld=='.':
		raise Utils.WafError('Setting blddir="." may cause distclean problems')
	bld=os.path.abspath(bld)
	try:os.makedirs(bld)
	except OSError:pass
	targets=Options.options.compile_targets
	Options.options.compile_targets=None
	Options.is_install=False
	conf.srcdir=src
	conf.blddir=bld
	conf.post_init()
	if'incomplete_src'in vars():
		conf.check_message_1('Setting srcdir to')
		conf.check_message_2(src)
	if'incomplete_bld'in vars():
		conf.check_message_1('Setting blddir to')
		conf.check_message_2(bld)
	conf.sub_config([''])
	conf.store()
	env=Environment.Environment()
	env[BLDDIR]=bld
	env[SRCDIR]=src
	env['argv']=sys.argv
	env['commands']=Options.commands
	env['options']=Options.options.__dict__
	env['hash']=conf.hash
	env['files']=conf.files
	env['environ']=dict(conf.environ)
	env['cwd']=os.path.split(Utils.g_module.root_path)[0]
	if Utils.g_module.root_path!=src:
		env.store(os.path.join(src,Options.lockfile))
	env.store(Options.lockfile)
	Options.options.compile_targets=targets
def clean(bld):
	'''removes the build files'''
	try:
		proj=Environment.Environment(Options.lockfile)
	except IOError:
		raise Utils.WafError('Nothing to clean (project not configured)')
	bld.load_dirs(proj[SRCDIR],proj[BLDDIR])
	bld.load_envs()
	bld.is_install=0
	bld.add_subdirs([os.path.split(Utils.g_module.root_path)[0]])
	try:
		bld.clean()
	finally:
		bld.save()
def check_configured(bld):
	if not Configure.autoconfig:
		return bld
	conf_cls=getattr(Utils.g_module,'configure_context',Utils.Context)
	bld_cls=getattr(Utils.g_module,'build_context',Utils.Context)
	def reconf(proj):
		back=(Options.commands,Options.options.__dict__,Logs.zones,Logs.verbose)
		Options.commands=proj['commands']
		Options.options.__dict__=proj['options']
		conf=conf_cls()
		conf.environ=proj['environ']
		configure(conf)
		(Options.commands,Options.options.__dict__,Logs.zones,Logs.verbose)=back
	try:
		proj=Environment.Environment(Options.lockfile)
	except IOError:
		conf=conf_cls()
		configure(conf)
	else:
		try:
			bld=bld_cls()
			bld.load_dirs(proj[SRCDIR],proj[BLDDIR])
			bld.load_envs()
		except Utils.WafError:
			reconf(proj)
			return bld_cls()
	try:
		proj=Environment.Environment(Options.lockfile)
	except IOError:
		raise Utils.WafError('Auto-config: project does not configure (bug)')
	h=0
	try:
		for file in proj['files']:
			if file.endswith('configure'):
				h=hash((h,Utils.readf(file)))
			else:
				mod=Utils.load_module(file)
				h=hash((h,mod.waf_hash_val))
	except(OSError,IOError):
		warn('Reconfiguring the project: a file is unavailable')
		reconf(proj)
	else:
		if(h!=proj['hash']):
			warn('Reconfiguring the project: the configuration has changed')
			reconf(proj)
	return bld_cls()
def install(bld):
	'''installs the build files'''
	bld=check_configured(bld)
	Options.commands['install']=True
	Options.commands['uninstall']=False
	Options.is_install=True
	bld.is_install=INSTALL
	build_impl(bld)
	bld.install()
def uninstall(bld):
	'''removes the installed files'''
	Options.commands['install']=False
	Options.commands['uninstall']=True
	Options.is_install=True
	bld.is_install=UNINSTALL
	try:
		def runnable_status(self):
			return SKIP_ME
		setattr(Task.Task,'runnable_status_back',Task.Task.runnable_status)
		setattr(Task.Task,'runnable_status',runnable_status)
		build_impl(bld)
		bld.install()
	finally:
		setattr(Task.Task,'runnable_status',Task.Task.runnable_status_back)
def build(bld):
	bld=check_configured(bld)
	Options.commands['install']=False
	Options.commands['uninstall']=False
	Options.is_install=False
	bld.is_install=0
	return build_impl(bld)
def build_impl(bld):
	try:
		proj=Environment.Environment(Options.lockfile)
	except IOError:
		raise Utils.WafError("Project not configured (run 'waf configure' first)")
	bld.load_dirs(proj[SRCDIR],proj[BLDDIR])
	bld.load_envs()
	info("Waf: Entering directory `%s'"%bld.bldnode.abspath())
	bld.add_subdirs([os.path.split(Utils.g_module.root_path)[0]])
	bld.pre_build()
	try:
		bld.compile()
	finally:
		if Options.options.progress_bar:print('')
		info("Waf: Leaving directory `%s'"%bld.bldnode.abspath())
	bld.post_build()
	bld.install()
excludes='.bzr .bzrignore .git .gitignore .svn CVS .cvsignore .arch-ids {arch} SCCS BitKeeper .hg _MTN _darcs Makefile Makefile.in config.log .gitattributes .hgignore .hgtags'.split()
dist_exts='~ .rej .orig .pyc .pyo .bak .tar.bz2 tar.gz .zip .swp'.split()
def dont_dist(name,src,build_dir):
	global excludes,dist_exts
	if(name.startswith(',,')or name.startswith('++')or name.startswith('.waf')or(src=='.'and name==Options.lockfile)or name in excludes or name==build_dir):
		return True
	for ext in dist_exts:
		if name.endswith(ext):
			return True
	return False
def copytree(src,dst,build_dir):
	names=os.listdir(src)
	os.makedirs(dst)
	for name in names:
		srcname=os.path.join(src,name)
		dstname=os.path.join(dst,name)
		if dont_dist(name,src,build_dir):
			continue
		if os.path.isdir(srcname):
			copytree(srcname,dstname,build_dir)
		else:
			shutil.copy2(srcname,dstname)
def distclean(ctx=None):
	'''removes the build directory'''
	global commands
	lst=os.listdir('.')
	for f in lst:
		if f==Options.lockfile:
			try:
				proj=Environment.Environment(f)
			except:
				Logs.warn('could not read %r'%f)
				continue
			try:
				shutil.rmtree(proj[BLDDIR])
			except IOError:
				pass
			except OSError,e:
				if e.errno!=errno.ENOENT:
					Logs.warn('project %r cannot be removed'%proj[BLDDIR])
			try:
				os.remove(f)
			except OSError,e:
				if e.errno!=errno.ENOENT:
					Logs.warn('file %r cannot be removed'%f)
		if not commands and f.startswith('.waf'):
			shutil.rmtree(f,ignore_errors=True)
def dist(appname='',version=''):
	'''makes a tarball for redistributing the sources'''
	import tarfile
	if not appname:appname=Utils.g_module.APPNAME
	if not version:version=Utils.g_module.VERSION
	tmp_folder=appname+'-'+version
	if g_gz in['gz','bz2']:
		arch_name=tmp_folder+'.tar.'+g_gz
	else:
		arch_name=tmp_folder+'.'+'zip'
	try:
		shutil.rmtree(tmp_folder)
	except(OSError,IOError):
		pass
	try:
		os.remove(arch_name)
	except(OSError,IOError):
		pass
	blddir=getattr(Utils.g_module,BLDDIR,None)
	if not blddir:
		blddir=getattr(Utils.g_module,'out',None)
	copytree('.',tmp_folder,blddir)
	dist_hook=getattr(Utils.g_module,'dist_hook',None)
	if dist_hook:
		back=os.getcwd()
		os.chdir(tmp_folder)
		try:
			dist_hook()
		finally:
			os.chdir(back)
	if g_gz in['gz','bz2']:
		tar=tarfile.open(arch_name,'w:'+g_gz)
		tar.add(tmp_folder)
		tar.close()
	else:
		Utils.zip_folder(tmp_folder,arch_name,tmp_folder)
	try:from hashlib import sha1 as sha
	except ImportError:from sha import sha
	try:
		digest=" (sha=%r)"%sha(Utils.readf(arch_name)).hexdigest()
	except:
		digest=''
	info('New archive created: %s%s'%(arch_name,digest))
	if os.path.exists(tmp_folder):shutil.rmtree(tmp_folder)
	return arch_name
def distcheck(appname='',version='',subdir=''):
	'''checks if the sources compile (tarball from 'dist')'''
	import tempfile,tarfile
	if not appname:appname=Utils.g_module.APPNAME
	if not version:version=Utils.g_module.VERSION
	waf=os.path.abspath(sys.argv[0])
	tarball=dist(appname,version)
	path=appname+'-'+version
	if os.path.exists(path):
		shutil.rmtree(path)
	t=tarfile.open(tarball)
	for x in t:t.extract(x)
	t.close()
	if subdir:
		build_path=os.path.join(path,subdir)
	else:
		build_path=path
	instdir=tempfile.mkdtemp('.inst','%s-%s'%(appname,version))
	ret=Utils.pproc.Popen([waf,'configure','build','install','uninstall','--destdir='+instdir],cwd=build_path).wait()
	if ret:
		raise Utils.WafError('distcheck failed with code %i'%ret)
	if os.path.exists(instdir):
		raise Utils.WafError('distcheck succeeded, but files were left in %s'%instdir)
	shutil.rmtree(path)
def add_subdir(dir,bld):
	bld.recurse(dir,'build')


########NEW FILE########
__FILENAME__ = Task
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,shutil,sys,re,random,datetime,tempfile,shlex
from Utils import md5
import Build,Runner,Utils,Node,Logs,Options
from Logs import debug,warn,error
from Constants import*
algotype=NORMAL
COMPILE_TEMPLATE_SHELL='''
def f(task):
	env = task.env
	wd = getattr(task, 'cwd', None)
	p = env.get_flat
	cmd = \'\'\' %s \'\'\' % s
	return task.exec_command(cmd, cwd=wd)
'''
COMPILE_TEMPLATE_NOSHELL='''
def f(task):
	env = task.env
	wd = getattr(task, 'cwd', None)
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	lst = []
	%s
	lst = [x for x in lst if x]
	return task.exec_command(lst, cwd=wd)
'''
file_deps=Utils.nada
class TaskManager(object):
	def __init__(self):
		self.groups=[]
		self.tasks_done=[]
		self.current_group=0
		self.groups_names={}
	def group_name(self,g):
		if not isinstance(g,TaskGroup):
			g=self.groups[g]
		for x in self.groups_names:
			if id(self.groups_names[x])==id(g):
				return x
		return''
	def group_idx(self,tg):
		se=id(tg)
		for i in range(len(self.groups)):
			g=self.groups[i]
			for t in g.tasks_gen:
				if id(t)==se:
					return i
		return None
	def get_next_set(self):
		ret=None
		while not ret and self.current_group<len(self.groups):
			ret=self.groups[self.current_group].get_next_set()
			if ret:return ret
			else:
				self.groups[self.current_group].process_install()
				self.current_group+=1
		return(None,None)
	def add_group(self,name=None,set=True):
		g=TaskGroup()
		if name and name in self.groups_names:
			error('add_group: name %s already present'%name)
		self.groups_names[name]=g
		self.groups.append(g)
		if set:
			self.current_group=len(self.groups)-1
	def set_group(self,idx):
		if isinstance(idx,str):
			g=self.groups_names[idx]
			for x in xrange(len(self.groups)):
				if id(g)==id(self.groups[x]):
					self.current_group=x
		else:
			self.current_group=idx
	def add_task_gen(self,tgen):
		if not self.groups:self.add_group()
		self.groups[self.current_group].tasks_gen.append(tgen)
	def add_task(self,task):
		if not self.groups:self.add_group()
		self.groups[self.current_group].tasks.append(task)
	def total(self):
		total=0
		if not self.groups:return 0
		for group in self.groups:
			total+=len(group.tasks)
		return total
	def add_finished(self,tsk):
		self.tasks_done.append(tsk)
		bld=tsk.generator.bld
		if bld.is_install:
			f=None
			if'install'in tsk.__dict__:
				f=tsk.__dict__['install']
				if f:f(tsk)
			else:
				tsk.install()
class TaskGroup(object):
	def __init__(self):
		self.tasks=[]
		self.tasks_gen=[]
		self.cstr_groups=Utils.DefaultDict(list)
		self.cstr_order=Utils.DefaultDict(set)
		self.temp_tasks=[]
		self.ready=0
		self.post_funs=[]
	def reset(self):
		for x in self.cstr_groups:
			self.tasks+=self.cstr_groups[x]
		self.tasks=self.temp_tasks+self.tasks
		self.temp_tasks=[]
		self.cstr_groups=Utils.DefaultDict(list)
		self.cstr_order=Utils.DefaultDict(set)
		self.ready=0
	def process_install(self):
		for(f,k,kw)in self.post_funs:
			f(*k,**kw)
	def prepare(self):
		self.ready=1
		file_deps(self.tasks)
		self.make_cstr_groups()
		self.extract_constraints()
	def get_next_set(self):
		global algotype
		if algotype==NORMAL:
			tasks=self.tasks_in_parallel()
			maxj=MAXJOBS
		elif algotype==JOBCONTROL:
			(maxj,tasks)=self.tasks_by_max_jobs()
		elif algotype==MAXPARALLEL:
			tasks=self.tasks_with_inner_constraints()
			maxj=MAXJOBS
		else:
			raise Utils.WafError("unknown algorithm type %s"%(algotype))
		if not tasks:return()
		return(maxj,tasks)
	def make_cstr_groups(self):
		self.cstr_groups=Utils.DefaultDict(list)
		for x in self.tasks:
			h=x.hash_constraints()
			self.cstr_groups[h].append(x)
	def set_order(self,a,b):
		self.cstr_order[a].add(b)
	def compare_exts(self,t1,t2):
		x="ext_in"
		y="ext_out"
		in_=t1.attr(x,())
		out_=t2.attr(y,())
		for k in in_:
			if k in out_:
				return-1
		in_=t2.attr(x,())
		out_=t1.attr(y,())
		for k in in_:
			if k in out_:
				return 1
		return 0
	def compare_partial(self,t1,t2):
		m="after"
		n="before"
		name=t2.__class__.__name__
		if name in Utils.to_list(t1.attr(m,())):return-1
		elif name in Utils.to_list(t1.attr(n,())):return 1
		name=t1.__class__.__name__
		if name in Utils.to_list(t2.attr(m,())):return 1
		elif name in Utils.to_list(t2.attr(n,())):return-1
		return 0
	def extract_constraints(self):
		keys=self.cstr_groups.keys()
		max=len(keys)
		for i in xrange(max):
			t1=self.cstr_groups[keys[i]][0]
			for j in xrange(i+1,max):
				t2=self.cstr_groups[keys[j]][0]
				val=(self.compare_exts(t1,t2)or self.compare_partial(t1,t2))
				if val>0:
					self.set_order(keys[i],keys[j])
				elif val<0:
					self.set_order(keys[j],keys[i])
	def tasks_in_parallel(self):
		if not self.ready:self.prepare()
		keys=self.cstr_groups.keys()
		unconnected=[]
		remainder=[]
		for u in keys:
			for k in self.cstr_order.values():
				if u in k:
					remainder.append(u)
					break
			else:
				unconnected.append(u)
		toreturn=[]
		for y in unconnected:
			toreturn.extend(self.cstr_groups[y])
		for y in unconnected:
			try:self.cstr_order.__delitem__(y)
			except KeyError:pass
			self.cstr_groups.__delitem__(y)
		if not toreturn and remainder:
			raise Utils.WafError("circular order constraint detected %r"%remainder)
		return toreturn
	def tasks_by_max_jobs(self):
		if not self.ready:self.prepare()
		if not self.temp_tasks:self.temp_tasks=self.tasks_in_parallel()
		if not self.temp_tasks:return(None,None)
		maxjobs=MAXJOBS
		ret=[]
		remaining=[]
		for t in self.temp_tasks:
			m=getattr(t,"maxjobs",getattr(self.__class__,"maxjobs",MAXJOBS))
			if m>maxjobs:
				remaining.append(t)
			elif m<maxjobs:
				remaining+=ret
				ret=[t]
				maxjobs=m
			else:
				ret.append(t)
		self.temp_tasks=remaining
		return(maxjobs,ret)
	def tasks_with_inner_constraints(self):
		if not self.ready:self.prepare()
		if getattr(self,"done",None):return None
		for p in self.cstr_order:
			for v in self.cstr_order[p]:
				for m in self.cstr_groups[p]:
					for n in self.cstr_groups[v]:
						n.set_run_after(m)
		self.cstr_order=Utils.DefaultDict(set)
		self.cstr_groups=Utils.DefaultDict(list)
		self.done=1
		return self.tasks[:]
class store_task_type(type):
	def __init__(cls,name,bases,dict):
		super(store_task_type,cls).__init__(name,bases,dict)
		name=cls.__name__
		if name.endswith('_task'):
			name=name.replace('_task','')
		if name!='TaskBase':
			TaskBase.classes[name]=cls
class TaskBase(object):
	__metaclass__=store_task_type
	color="GREEN"
	maxjobs=MAXJOBS
	classes={}
	stat=None
	def __init__(self,*k,**kw):
		self.hasrun=NOT_RUN
		try:
			self.generator=kw['generator']
		except KeyError:
			self.generator=self
			self.bld=Build.bld
		if kw.get('normal',1):
			self.generator.bld.task_manager.add_task(self)
	def __repr__(self):
		return'\n\t{task: %s %s}'%(self.__class__.__name__,str(getattr(self,"fun","")))
	def __str__(self):
		if hasattr(self,'fun'):
			return'executing: %s\n'%self.fun.__name__
		return self.__class__.__name__+'\n'
	def exec_command(self,*k,**kw):
		if self.env['env']:
			kw['env']=self.env['env']
		return self.generator.bld.exec_command(*k,**kw)
	def runnable_status(self):
		return RUN_ME
	def can_retrieve_cache(self):
		return False
	def call_run(self):
		if self.can_retrieve_cache():
			return 0
		return self.run()
	def run(self):
		if hasattr(self,'fun'):
			return self.fun(self)
		return 0
	def post_run(self):
		pass
	def display(self):
		col1=Logs.colors(self.color)
		col2=Logs.colors.NORMAL
		if Options.options.progress_bar==1:
			return self.generator.bld.progress_line(self.position[0],self.position[1],col1,col2)
		if Options.options.progress_bar==2:
			ela=Utils.get_elapsed_time(self.generator.bld.ini)
			try:
				ins=','.join([n.name for n in self.inputs])
			except AttributeError:
				ins=''
			try:
				outs=','.join([n.name for n in self.outputs])
			except AttributeError:
				outs=''
			return'|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n'%(self.position[1],self.position[0],ins,outs,ela)
		total=self.position[1]
		n=len(str(total))
		fs='[%%%dd/%%%dd] %%s%%s%%s'%(n,n)
		return fs%(self.position[0],self.position[1],col1,str(self),col2)
	def attr(self,att,default=None):
		ret=getattr(self,att,self)
		if ret is self:return getattr(self.__class__,att,default)
		return ret
	def hash_constraints(self):
		a=self.attr
		sum=hash((self.__class__.__name__,str(a('before','')),str(a('after','')),str(a('ext_in','')),str(a('ext_out','')),self.__class__.maxjobs))
		return sum
	def format_error(self):
		if getattr(self,"err_msg",None):
			return self.err_msg
		elif self.hasrun==CRASHED:
			try:
				return" -> task failed (err #%d): %r"%(self.err_code,self)
			except AttributeError:
				return" -> task failed: %r"%self
		elif self.hasrun==MISSING:
			return" -> missing files: %r"%self
		else:
			return''
	def install(self):
		bld=self.generator.bld
		d=self.attr('install')
		if self.attr('install_path'):
			lst=[a.relpath_gen(bld.srcnode)for a in self.outputs]
			perm=self.attr('chmod',O644)
			if self.attr('src'):
				lst+=[a.relpath_gen(bld.srcnode)for a in self.inputs]
			if self.attr('filename'):
				dir=self.install_path.rstrip(os.sep)+os.sep+self.attr('filename')
				bld.install_as(dir,lst[0],self.env,perm)
			else:
				bld.install_files(self.install_path,lst,self.env,perm)
class Task(TaskBase):
	vars=[]
	def __init__(self,env,**kw):
		TaskBase.__init__(self,**kw)
		self.env=env
		self.inputs=[]
		self.outputs=[]
		self.deps_nodes=[]
		self.run_after=[]
	def __str__(self):
		env=self.env
		src_str=' '.join([a.nice_path(env)for a in self.inputs])
		tgt_str=' '.join([a.nice_path(env)for a in self.outputs])
		if self.outputs:sep=' -> '
		else:sep=''
		return'%s: %s%s%s\n'%(self.__class__.__name__.replace('_task',''),src_str,sep,tgt_str)
	def __repr__(self):
		return"".join(['\n\t{task: ',self.__class__.__name__," ",",".join([x.name for x in self.inputs])," -> ",",".join([x.name for x in self.outputs]),'}'])
	def unique_id(self):
		try:
			return self.uid
		except AttributeError:
			m=md5()
			up=m.update
			up(self.__class__.__name__)
			up(self.env.variant())
			p=None
			for x in self.inputs+self.outputs:
				if p!=x.parent.id:
					p=x.parent.id
					up(x.parent.abspath())
				up(x.name)
			self.uid=m.digest()
			return self.uid
	def set_inputs(self,inp):
		if isinstance(inp,list):self.inputs+=inp
		else:self.inputs.append(inp)
	def set_outputs(self,out):
		if isinstance(out,list):self.outputs+=out
		else:self.outputs.append(out)
	def set_run_after(self,task):
		assert isinstance(task,TaskBase)
		self.run_after.append(task)
	def add_file_dependency(self,filename):
		node=self.generator.bld.path.find_resource(filename)
		self.deps_nodes.append(node)
	def signature(self):
		try:return self.cache_sig[0]
		except AttributeError:pass
		self.m=md5()
		exp_sig=self.sig_explicit_deps()
		var_sig=self.sig_vars()
		imp_sig=SIG_NIL
		if self.scan:
			try:
				imp_sig=self.sig_implicit_deps()
			except ValueError:
				return self.signature()
		ret=self.m.digest()
		self.cache_sig=(ret,exp_sig,imp_sig,var_sig)
		return ret
	def runnable_status(self):
		if self.inputs and(not self.outputs):
			if not getattr(self.__class__,'quiet',None):
				warn("invalid task (no inputs OR outputs): override in a Task subclass or set the attribute 'quiet' %r"%self)
		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER
		env=self.env
		bld=self.generator.bld
		new_sig=self.signature()
		key=self.unique_id()
		try:
			prev_sig=bld.task_sigs[key][0]
		except KeyError:
			debug("task: task %r must run as it was never run before or the task code changed",self)
			return RUN_ME
		for node in self.outputs:
			variant=node.variant(env)
			try:
				if bld.node_sigs[variant][node.id]!=new_sig:
					return RUN_ME
			except KeyError:
				debug("task: task %r must run as the output nodes do not exist",self)
				return RUN_ME
		if Logs.verbose:self.debug_why(bld.task_sigs[key])
		if new_sig!=prev_sig:
			return RUN_ME
		return SKIP_ME
	def post_run(self):
		bld=self.generator.bld
		env=self.env
		sig=self.signature()
		ssig=sig.encode('hex')
		variant=env.variant()
		for node in self.outputs:
			try:
				os.stat(node.abspath(env))
			except OSError:
				self.hasrun=MISSING
				self.err_msg='-> missing file: %r'%node.abspath(env)
				raise Utils.WafError
			bld.node_sigs[variant][node.id]=sig
		bld.task_sigs[self.unique_id()]=self.cache_sig
		if not Options.cache_global or Options.options.nocache or not self.outputs:
			return None
		if getattr(self,'cached',None):
			return None
		dname=os.path.join(Options.cache_global,ssig)
		tmpdir=tempfile.mkdtemp(prefix=Options.cache_global)
		try:
			shutil.rmtree(dname)
		except:
			pass
		try:
			for node in self.outputs:
				variant=node.variant(env)
				dest=os.path.join(tmpdir,node.name)
				shutil.copy2(node.abspath(env),dest)
		except(OSError,IOError):
			try:
				shutil.rmtree(tmpdir)
			except:
				pass
		else:
			try:
				os.rename(tmpdir,dname)
			except OSError:
				try:
					shutil.rmtree(tmpdir)
				except:
					pass
			else:
				try:
					os.chmod(dname,O755)
				except:
					pass
	def can_retrieve_cache(self):
		if not Options.cache_global or Options.options.nocache or not self.outputs:
			return None
		env=self.env
		sig=self.signature()
		ssig=sig.encode('hex')
		dname=os.path.join(Options.cache_global,ssig)
		try:
			t1=os.stat(dname).st_mtime
		except OSError:
			return None
		for node in self.outputs:
			variant=node.variant(env)
			orig=os.path.join(dname,node.name)
			try:
				shutil.copy2(orig,node.abspath(env))
				os.utime(orig,None)
			except(OSError,IOError):
				debug('task: failed retrieving file')
				return None
		try:
			t2=os.stat(dname).st_mtime
		except OSError:
			return None
		if t1!=t2:
			return None
		for node in self.outputs:
			self.generator.bld.node_sigs[variant][node.id]=sig
			if Options.options.progress_bar<1:
				self.generator.bld.printout('restoring from cache %r\n'%node.bldpath(env))
		self.cached=True
		return 1
	def debug_why(self,old_sigs):
		new_sigs=self.cache_sig
		def v(x):
			return x.encode('hex')
		debug("Task %r",self)
		msgs=['Task must run','* Source file or manual dependency','* Implicit dependency','* Environment variable']
		tmp='task: -> %s: %s %s'
		for x in xrange(len(msgs)):
			if(new_sigs[x]!=old_sigs[x]):
				debug(tmp,msgs[x],v(old_sigs[x]),v(new_sigs[x]))
	def sig_explicit_deps(self):
		bld=self.generator.bld
		up=self.m.update
		for x in self.inputs+getattr(self,'dep_nodes',[]):
			if not x.parent.id in bld.cache_scanned_folders:
				bld.rescan(x.parent)
			variant=x.variant(self.env)
			try:
				up(bld.node_sigs[variant][x.id])
			except KeyError:
				raise Utils.WafError('Missing node signature for %r (required by %r)'%(x,self))
		if bld.deps_man:
			additional_deps=bld.deps_man
			for x in self.inputs+self.outputs:
				try:
					d=additional_deps[x.id]
				except KeyError:
					continue
				for v in d:
					if isinstance(v,Node.Node):
						bld.rescan(v.parent)
						variant=v.variant(self.env)
						try:
							v=bld.node_sigs[variant][v.id]
						except KeyError:
							raise Utils.WafError('Missing node signature for %r (required by %r)'%(v,self))
					elif hasattr(v,'__call__'):
						v=v()
					up(v)
		for x in self.deps_nodes:
			v=bld.node_sigs[x.variant(self.env)][x.id]
			up(v)
		return self.m.digest()
	def sig_vars(self):
		bld=self.generator.bld
		env=self.env
		act_sig=bld.hash_env_vars(env,self.__class__.vars)
		self.m.update(act_sig)
		dep_vars=getattr(self,'dep_vars',None)
		if dep_vars:
			self.m.update(bld.hash_env_vars(env,dep_vars))
		return self.m.digest()
	scan=None
	def sig_implicit_deps(self):
		bld=self.generator.bld
		key=self.unique_id()
		prev_sigs=bld.task_sigs.get(key,())
		if prev_sigs:
			try:
				if prev_sigs[2]==self.compute_sig_implicit_deps():
					return prev_sigs[2]
			except(KeyError,OSError):
				pass
			del bld.task_sigs[key]
			raise ValueError('rescan')
		(nodes,names)=self.scan()
		if Logs.verbose:
			debug('deps: scanner for %s returned %s %s',str(self),str(nodes),str(names))
		bld.node_deps[key]=nodes
		bld.raw_deps[key]=names
		try:
			sig=self.compute_sig_implicit_deps()
		except KeyError:
			try:
				nodes=[]
				for k in bld.node_deps.get(self.unique_id(),[]):
					if k.id&3==2:
						if not k.id in bld.node_sigs[0]:
							nodes.append(k)
					else:
						if not k.id in bld.node_sigs[self.env.variant()]:
							nodes.append(k)
			except:
				nodes='?'
			raise Utils.WafError('Missing node signature for %r (for implicit dependencies %r)'%(nodes,self))
		return sig
	def compute_sig_implicit_deps(self):
		upd=self.m.update
		bld=self.generator.bld
		tstamp=bld.node_sigs
		env=self.env
		for k in bld.node_deps.get(self.unique_id(),[]):
			if not k.parent.id in bld.cache_scanned_folders:
				bld.rescan(k.parent)
			if k.id&3==2:
				upd(tstamp[0][k.id])
			else:
				upd(tstamp[env.variant()][k.id])
		return self.m.digest()
def funex(c):
	dc={}
	exec(c,dc)
	return dc['f']
reg_act=re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})",re.M)
def compile_fun_shell(name,line):
	extr=[]
	def repl(match):
		g=match.group
		if g('dollar'):return"$"
		elif g('backslash'):return'\\\\'
		elif g('subst'):extr.append((g('var'),g('code')));return"%s"
		return None
	line=reg_act.sub(repl,line)
	parm=[]
	dvars=[]
	app=parm.append
	for(var,meth)in extr:
		if var=='SRC':
			if meth:app('task.inputs%s'%meth)
			else:app('" ".join([a.srcpath(env) for a in task.inputs])')
		elif var=='TGT':
			if meth:app('task.outputs%s'%meth)
			else:app('" ".join([a.bldpath(env) for a in task.outputs])')
		else:
			if not var in dvars:dvars.append(var)
			app("p('%s')"%var)
	if parm:parm="%% (%s) "%(',\n\t\t'.join(parm))
	else:parm=''
	c=COMPILE_TEMPLATE_SHELL%(line,parm)
	debug('action: %s',c)
	return(funex(c),dvars)
def compile_fun_noshell(name,line):
	extr=[]
	def repl(match):
		g=match.group
		if g('dollar'):return"$"
		elif g('subst'):extr.append((g('var'),g('code')));return"<<|@|>>"
		return None
	line2=reg_act.sub(repl,line)
	params=line2.split('<<|@|>>')
	buf=[]
	dvars=[]
	app=buf.append
	for x in xrange(len(extr)):
		params[x]=params[x].strip()
		if params[x]:
			app("lst.extend(%r)"%params[x].split())
		(var,meth)=extr[x]
		if var=='SRC':
			if meth:app('lst.append(task.inputs%s)'%meth)
			else:app("lst.extend([a.srcpath(env) for a in task.inputs])")
		elif var=='TGT':
			if meth:app('lst.append(task.outputs%s)'%meth)
			else:app("lst.extend([a.bldpath(env) for a in task.outputs])")
		else:
			app('lst.extend(to_list(env[%r]))'%var)
			if not var in dvars:dvars.append(var)
	if params[-1]:
		app("lst.extend(%r)"%shlex.split(params[-1]))
	fun=COMPILE_TEMPLATE_NOSHELL%"\n\t".join(buf)
	debug('action: %s',fun)
	return(funex(fun),dvars)
def compile_fun(name,line,shell=None):
	if line.find('<')>0 or line.find('>')>0 or line.find('&&')>0:
		shell=True
	if shell is None:
		if sys.platform=='win32':
			shell=False
		else:
			shell=True
	if shell:
		return compile_fun_shell(name,line)
	else:
		return compile_fun_noshell(name,line)
def simple_task_type(name,line,color='GREEN',vars=[],ext_in=[],ext_out=[],before=[],after=[],shell=None):
	(fun,dvars)=compile_fun(name,line,shell)
	fun.code=line
	return task_type_from_func(name,fun,vars or dvars,color,ext_in,ext_out,before,after)
def task_type_from_func(name,func,vars=[],color='GREEN',ext_in=[],ext_out=[],before=[],after=[]):
	params={'run':func,'vars':vars,'color':color,'name':name,'ext_in':Utils.to_list(ext_in),'ext_out':Utils.to_list(ext_out),'before':Utils.to_list(before),'after':Utils.to_list(after),}
	cls=type(Task)(name,(Task,),params)
	TaskBase.classes[name]=cls
	return cls
def always_run(cls):
	old=cls.runnable_status
	def always(self):
		old(self)
		return RUN_ME
	cls.runnable_status=always
def update_outputs(cls):
	old_post_run=cls.post_run
	def post_run(self):
		old_post_run(self)
		bld=self.outputs[0].__class__.bld
		for output in self.outputs:
			bld.node_sigs[self.env.variant()][output.id]=Utils.h_file(output.abspath(self.env))
	cls.post_run=post_run
	old_runnable_status=cls.runnable_status
	def runnable_status(self):
		status=old_runnable_status(self)
		if status!=RUN_ME:
			return status
		try:
			bld=self.outputs[0].__class__.bld
			new_sig=self.signature()
			prev_sig=bld.task_sigs[self.unique_id()][0]
			if prev_sig==new_sig:
				for x in self.outputs:
					if not x.id in bld.node_sigs[self.env.variant()]:
						return RUN_ME
				return SKIP_ME
		except KeyError:
			pass
		except IndexError:
			pass
		return RUN_ME
	cls.runnable_status=runnable_status
def extract_outputs(tasks):
	v={}
	for x in tasks:
		try:
			(ins,outs)=v[x.env.variant()]
		except KeyError:
			ins={}
			outs={}
			v[x.env.variant()]=(ins,outs)
		for a in getattr(x,'inputs',[]):
			try:ins[a.id].append(x)
			except KeyError:ins[a.id]=[x]
		for a in getattr(x,'outputs',[]):
			try:outs[a.id].append(x)
			except KeyError:outs[a.id]=[x]
	for(ins,outs)in v.values():
		links=set(ins.iterkeys()).intersection(outs.iterkeys())
		for k in links:
			for a in ins[k]:
				for b in outs[k]:
					a.set_run_after(b)
def extract_deps(tasks):
	extract_outputs(tasks)
	out_to_task={}
	for x in tasks:
		v=x.env.variant()
		try:
			lst=x.outputs
		except AttributeError:
			pass
		else:
			for node in lst:
				out_to_task[(v,node.id)]=x
	dep_to_task={}
	for x in tasks:
		try:
			x.signature()
		except:
			pass
		v=x.env.variant()
		key=x.unique_id()
		for k in x.generator.bld.node_deps.get(x.unique_id(),[]):
			try:dep_to_task[(v,k.id)].append(x)
			except KeyError:dep_to_task[(v,k.id)]=[x]
	deps=set(dep_to_task.keys()).intersection(set(out_to_task.keys()))
	for idx in deps:
		for k in dep_to_task[idx]:
			k.set_run_after(out_to_task[idx])
	for x in tasks:
		try:
			delattr(x,'cache_sig')
		except AttributeError:
			pass


########NEW FILE########
__FILENAME__ = TaskGen
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,traceback,copy
import Build,Task,Utils,Logs,Options
from Logs import debug,error,warn
from Constants import*
typos={'sources':'source','targets':'target','include':'includes','define':'defines','importpath':'importpaths','install_var':'install_path','install_subdir':'install_path','inst_var':'install_path','inst_dir':'install_path','feature':'features',}
class register_obj(type):
	def __init__(cls,name,bases,dict):
		super(register_obj,cls).__init__(name,bases,dict)
		name=cls.__name__
		suffix='_taskgen'
		if name.endswith(suffix):
			task_gen.classes[name.replace(suffix,'')]=cls
class task_gen(object):
	__metaclass__=register_obj
	mappings={}
	mapped={}
	prec=Utils.DefaultDict(list)
	traits=Utils.DefaultDict(set)
	classes={}
	def __init__(self,*kw,**kwargs):
		self.prec=Utils.DefaultDict(list)
		self.source=''
		self.target=''
		self.meths=[]
		self.mappings={}
		self.features=list(kw)
		self.tasks=[]
		self.default_chmod=O644
		self.default_install_path=None
		self.allnodes=[]
		self.bld=kwargs.get('bld',Build.bld)
		self.env=self.bld.env.copy()
		self.path=self.bld.path
		self.name=''
		self.idx=self.bld.idx[self.path.id]=self.bld.idx.get(self.path.id,0)+1
		for key,val in kwargs.iteritems():
			setattr(self,key,val)
		self.bld.task_manager.add_task_gen(self)
		self.bld.all_task_gen.append(self)
	def __str__(self):
		return("<task_gen '%s' of type %s defined in %s>"%(self.name or self.target,self.__class__.__name__,str(self.path)))
	def __setattr__(self,name,attr):
		real=typos.get(name,name)
		if real!=name:
			warn('typo %s -> %s'%(name,real))
			if Logs.verbose>0:
				traceback.print_stack()
		object.__setattr__(self,real,attr)
	def to_list(self,value):
		if isinstance(value,str):return value.split()
		else:return value
	def apply(self):
		keys=set(self.meths)
		self.features=Utils.to_list(self.features)
		for x in self.features+['*']:
			st=task_gen.traits[x]
			if not st:
				warn('feature %r does not exist - bind at least one method to it'%x)
			keys.update(st)
		prec={}
		prec_tbl=self.prec or task_gen.prec
		for x in prec_tbl:
			if x in keys:
				prec[x]=prec_tbl[x]
		tmp=[]
		for a in keys:
			for x in prec.values():
				if a in x:break
			else:
				tmp.append(a)
		out=[]
		while tmp:
			e=tmp.pop()
			if e in keys:out.append(e)
			try:
				nlst=prec[e]
			except KeyError:
				pass
			else:
				del prec[e]
				for x in nlst:
					for y in prec:
						if x in prec[y]:
							break
					else:
						tmp.append(x)
		if prec:raise Utils.WafError("graph has a cycle %s"%str(prec))
		out.reverse()
		self.meths=out
		debug('task_gen: posting %s %d',self,id(self))
		for x in out:
			try:
				v=getattr(self,x)
			except AttributeError:
				raise Utils.WafError("tried to retrieve %s which is not a valid method"%x)
			debug('task_gen: -> %s (%d)',x,id(self))
			v()
	def post(self):
		if not self.name:
			if isinstance(self.target,list):
				self.name=' '.join(self.target)
			else:
				self.name=self.target
		if getattr(self,'posted',None):
			return
		self.apply()
		self.posted=True
		debug('task_gen: posted %s',self.name)
	def get_hook(self,ext):
		try:return self.mappings[ext]
		except KeyError:
			try:return task_gen.mappings[ext]
			except KeyError:return None
	def create_task(self,name,src=None,tgt=None,env=None):
		env=env or self.env
		task=Task.TaskBase.classes[name](env.copy(),generator=self)
		if src:
			task.set_inputs(src)
		if tgt:
			task.set_outputs(tgt)
		self.tasks.append(task)
		return task
	def name_to_obj(self,name):
		return self.bld.name_to_obj(name,self.env)
	def find_sources_in_dirs(self,dirnames,excludes=[],exts=[]):
		err_msg="'%s' attribute must be a list"
		if not isinstance(excludes,list):
			raise Utils.WscriptError(err_msg%'excludes')
		if not isinstance(exts,list):
			raise Utils.WscriptError(err_msg%'exts')
		lst=[]
		dirnames=self.to_list(dirnames)
		ext_lst=exts or list(self.mappings.keys())+list(task_gen.mappings.keys())
		for name in dirnames:
			anode=self.path.find_dir(name)
			if not anode or not anode.is_child_of(self.bld.srcnode):
				raise Utils.WscriptError("Unable to use '%s' - either because it's not a relative path"", or it's not child of '%s'."%(name,self.bld.srcnode))
			self.bld.rescan(anode)
			for name in self.bld.cache_dir_contents[anode.id]:
				if name.startswith('.'):
					continue
				(base,ext)=os.path.splitext(name)
				if ext in ext_lst and not name in lst and not name in excludes:
					lst.append((anode.relpath_gen(self.path)or'.')+os.path.sep+name)
		lst.sort()
		self.source=self.to_list(self.source)
		if not self.source:self.source=lst
		else:self.source+=lst
	def clone(self,env):
		newobj=task_gen(bld=self.bld)
		for x in self.__dict__:
			if x in['env','bld']:
				continue
			elif x in["path","features"]:
				setattr(newobj,x,getattr(self,x))
			else:
				setattr(newobj,x,copy.copy(getattr(self,x)))
		newobj.__class__=self.__class__
		if isinstance(env,str):
			newobj.env=self.bld.all_envs[env].copy()
		else:
			newobj.env=env.copy()
		return newobj
	def get_inst_path(self):
		return getattr(self,'_install_path',getattr(self,'default_install_path',''))
	def set_inst_path(self,val):
		self._install_path=val
	install_path=property(get_inst_path,set_inst_path)
	def get_chmod(self):
		return getattr(self,'_chmod',getattr(self,'default_chmod',O644))
	def set_chmod(self,val):
		self._chmod=val
	chmod=property(get_chmod,set_chmod)
def declare_extension(var,func):
	try:
		for x in Utils.to_list(var):
			task_gen.mappings[x]=func
	except:
		raise Utils.WscriptError('declare_extension takes either a list or a string %r'%var)
	task_gen.mapped[func.__name__]=func
def declare_order(*k):
	assert(len(k)>1)
	n=len(k)-1
	for i in xrange(n):
		f1=k[i]
		f2=k[i+1]
		if not f1 in task_gen.prec[f2]:
			task_gen.prec[f2].append(f1)
def declare_chain(name='',action='',ext_in='',ext_out='',reentrant=True,color='BLUE',install=0,before=[],after=[],decider=None,rule=None,scan=None):
	action=action or rule
	if isinstance(action,str):
		act=Task.simple_task_type(name,action,color=color)
	else:
		act=Task.task_type_from_func(name,action,color=color)
	act.ext_in=tuple(Utils.to_list(ext_in))
	act.ext_out=tuple(Utils.to_list(ext_out))
	act.before=Utils.to_list(before)
	act.after=Utils.to_list(after)
	act.scan=scan
	def x_file(self,node):
		if decider:
			ext=decider(self,node)
		else:
			ext=ext_out
		if isinstance(ext,str):
			out_source=node.change_ext(ext)
			if reentrant:
				self.allnodes.append(out_source)
		elif isinstance(ext,list):
			out_source=[node.change_ext(x)for x in ext]
			if reentrant:
				for i in xrange((reentrant is True)and len(out_source)or reentrant):
					self.allnodes.append(out_source[i])
		else:
			raise Utils.WafError("do not know how to process %s"%str(ext))
		tsk=self.create_task(name,node,out_source)
		if node.__class__.bld.is_install:
			tsk.install=install
	declare_extension(act.ext_in,x_file)
	return x_file
def bind_feature(name,methods):
	lst=Utils.to_list(methods)
	task_gen.traits[name].update(lst)
def taskgen(func):
	setattr(task_gen,func.__name__,func)
	return func
def feature(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for name in k:
			task_gen.traits[name].update([func.__name__])
		return func
	return deco
def before(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not func.__name__ in task_gen.prec[fun_name]:
				task_gen.prec[fun_name].append(func.__name__)
		return func
	return deco
def after(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not fun_name in task_gen.prec[func.__name__]:
				task_gen.prec[func.__name__].append(fun_name)
		return func
	return deco
def extension(var):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		try:
			for x in Utils.to_list(var):
				task_gen.mappings[x]=func
		except:
			raise Utils.WafError('extension takes either a list or a string %r'%var)
		task_gen.mapped[func.__name__]=func
		return func
	return deco
def apply_core(self):
	find_resource=self.path.find_resource
	for filename in self.to_list(self.source):
		x=self.get_hook(filename)
		if x:
			x(self,filename)
		else:
			node=find_resource(filename)
			if not node:raise Utils.WafError("source not found: '%s' in '%s'"%(filename,str(self.path)))
			self.allnodes.append(node)
	for node in self.allnodes:
		x=self.get_hook(node.suffix())
		if not x:
			raise Utils.WafError("Cannot guess how to process %s (got mappings %r in %r) -> try conf.check_tool(..)?"%(str(node),self.__class__.mappings.keys(),self.__class__))
		x(self,node)
feature('*')(apply_core)
def exec_rule(self):
	if not getattr(self,'rule',None):
		return
	try:
		self.meths.remove('apply_core')
	except ValueError:
		pass
	func=self.rule
	vars2=[]
	if isinstance(func,str):
		(func,vars2)=Task.compile_fun('',self.rule,shell=getattr(self,'shell',True))
		func.code=self.rule
	name=getattr(self,'name',None)or self.target or self.rule
	if not isinstance(name,str):
		name=str(self.idx)
	cls=Task.task_type_from_func(name,func,getattr(self,'vars',vars2))
	tsk=self.create_task(name)
	dep_vars=getattr(self,'dep_vars',['ruledeps'])
	if dep_vars:
		tsk.dep_vars=dep_vars
	if isinstance(self.rule,str):
		tsk.env.ruledeps=self.rule
	else:
		tsk.env.ruledeps=Utils.h_fun(self.rule)
	if getattr(self,'target',None):
		cls.quiet=True
		tsk.outputs=[self.path.find_or_declare(x)for x in self.to_list(self.target)]
	if getattr(self,'source',None):
		cls.quiet=True
		tsk.inputs=[]
		for x in self.to_list(self.source):
			y=self.path.find_resource(x)
			if not y:
				raise Utils.WafError('input file %r could not be found (%r)'%(x,self.path.abspath()))
			tsk.inputs.append(y)
	if self.allnodes:
		tsk.inputs.extend(self.allnodes)
	if getattr(self,'scan',None):
		cls.scan=self.scan
	if getattr(self,'install_path',None):
		tsk.install_path=self.install_path
	if getattr(self,'cwd',None):
		tsk.cwd=self.cwd
	if getattr(self,'on_results',None):
		Task.update_outputs(cls)
	if getattr(self,'always',None):
		Task.always_run(cls)
	for x in['after','before','ext_in','ext_out']:
		setattr(cls,x,getattr(self,x,[]))
feature('*')(exec_rule)
before('apply_core')(exec_rule)
def sequence_order(self):
	if self.meths and self.meths[-1]!='sequence_order':
		self.meths.append('sequence_order')
		return
	if getattr(self,'seq_start',None):
		return
	if getattr(self.bld,'prev',None):
		self.bld.prev.post()
		for x in self.bld.prev.tasks:
			for y in self.tasks:
				y.set_run_after(x)
	self.bld.prev=self
feature('seq')(sequence_order)


########NEW FILE########
__FILENAME__ = config_c
#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,imp,sys,shlex,shutil
from Utils import md5
import Build,Utils,Configure,Task,Options,Logs,TaskGen
from Constants import*
from Configure import conf,conftest
cfg_ver={'atleast-version':'>=','exact-version':'==','max-version':'<=',}
SNIP1='''
	int main() {
	void *p;
	p=(void*)(%s);
	return 0;
}
'''
SNIP2='''
int main() {
	if ((%(type_name)s *) 0) return 0;
	if (sizeof (%(type_name)s)) return 0;
}
'''
SNIP3='''
int main() {
	return 0;
}
'''
def parse_flags(line,uselib,env):
	lst=shlex.split(line)
	while lst:
		x=lst.pop(0)
		st=x[:2]
		ot=x[2:]
		if st=='-I'or st=='/I':
			if not ot:ot=lst.pop(0)
			env.append_unique('CPPPATH_'+uselib,ot)
		elif st=='-D':
			if not ot:ot=lst.pop(0)
			env.append_unique('CXXDEFINES_'+uselib,ot)
			env.append_unique('CCDEFINES_'+uselib,ot)
		elif st=='-l':
			if not ot:ot=lst.pop(0)
			env.append_unique('LIB_'+uselib,ot)
		elif st=='-L':
			if not ot:ot=lst.pop(0)
			env.append_unique('LIBPATH_'+uselib,ot)
		elif x=='-pthread'or x.startswith('+'):
			env.append_unique('CCFLAGS_'+uselib,x)
			env.append_unique('CXXFLAGS_'+uselib,x)
			env.append_unique('LINKFLAGS_'+uselib,x)
		elif x=='-framework':
			env.append_unique('FRAMEWORK_'+uselib,lst.pop(0))
		elif x.startswith('-F'):
			env.append_unique('FRAMEWORKPATH_'+uselib,x[2:])
		elif x.startswith('-std'):
			env.append_unique('CCFLAGS_'+uselib,x)
			env.append_unique('LINKFLAGS_'+uselib,x)
		elif x.startswith('-Wl'):
			env.append_unique('LINKFLAGS_'+uselib,x)
		elif x.startswith('-m')or x.startswith('-f'):
			env.append_unique('CCFLAGS_'+uselib,x)
			env.append_unique('CXXFLAGS_'+uselib,x)
def ret_msg(self,f,kw):
	if isinstance(f,str):
		return f
	return f(kw)
def validate_cfg(self,kw):
	if not'path'in kw:
		kw['path']='pkg-config --errors-to-stdout --print-errors'
	if'atleast_pkgconfig_version'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for pkg-config version >= %s'%kw['atleast_pkgconfig_version']
		return
	if'modversion'in kw:
		return
	if'variables'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for %s variables'%kw['package']
		return
	for x in cfg_ver.keys():
		y=x.replace('-','_')
		if y in kw:
			if not'package'in kw:
				raise ValueError('%s requires a package'%x)
			if not'msg'in kw:
				kw['msg']='Checking for %s %s %s'%(kw['package'],cfg_ver[x],kw[y])
			return
	if not'msg'in kw:
		kw['msg']='Checking for %s'%(kw['package']or kw['path'])
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	if not'errmsg'in kw:
		kw['errmsg']='not found'
def cmd_and_log(self,cmd,kw):
	Logs.debug('runner: %s\n'%cmd)
	if self.log:
		self.log.write('%s\n'%cmd)
	try:
		p=Utils.pproc.Popen(cmd,stdout=Utils.pproc.PIPE,stderr=Utils.pproc.PIPE,shell=True)
		(out,err)=p.communicate()
	except OSError,e:
		self.log.write('error %r'%e)
		self.fatal(str(e))
	out=str(out)
	err=str(err)
	if self.log:
		self.log.write(out)
		self.log.write(err)
	if p.returncode:
		if not kw.get('errmsg',''):
			if kw.get('mandatory',False):
				kw['errmsg']=out.strip()
			else:
				kw['errmsg']='no'
		self.fatal('fail')
	return out
def exec_cfg(self,kw):
	if'atleast_pkgconfig_version'in kw:
		cmd='%s --atleast-pkgconfig-version=%s'%(kw['path'],kw['atleast_pkgconfig_version'])
		self.cmd_and_log(cmd,kw)
		if not'okmsg'in kw:
			kw['okmsg']='yes'
		return
	for x in cfg_ver:
		y=x.replace('-','_')
		if y in kw:
			self.cmd_and_log('%s --%s=%s %s'%(kw['path'],x,kw[y],kw['package']),kw)
			if not'okmsg'in kw:
				kw['okmsg']='yes'
			self.define(self.have_define(kw.get('uselib_store',kw['package'])),1,0)
			break
	if'modversion'in kw:
		version=self.cmd_and_log('%s --modversion %s'%(kw['path'],kw['modversion']),kw).strip()
		self.define('%s_VERSION'%Utils.quote_define_name(kw.get('uselib_store',kw['modversion'])),version)
		return version
	if'variables'in kw:
		env=kw.get('env',self.env)
		uselib=kw.get('uselib_store',kw['package'].upper())
		vars=Utils.to_list(kw['variables'])
		for v in vars:
			val=self.cmd_and_log('%s --variable=%s %s'%(kw['path'],v,kw['package']),kw).strip()
			var='%s_%s'%(uselib,v)
			env[var]=val
		if not'okmsg'in kw:
			kw['okmsg']='yes'
		return
	lst=[kw['path']]
	defi=kw.get('define_variable',None)
	if not defi:
		defi=self.env.PKG_CONFIG_DEFINES or{}
	for key,val in defi.iteritems():
		lst.append('--define-variable=%s=%s'%(key,val))
	lst.append(kw.get('args',''))
	lst.append(kw['package'])
	cmd=' '.join(lst)
	ret=self.cmd_and_log(cmd,kw)
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	self.define(self.have_define(kw.get('uselib_store',kw['package'])),1,0)
	parse_flags(ret,kw.get('uselib_store',kw['package'].upper()),kw.get('env',self.env))
	return ret
def check_cfg(self,*k,**kw):
	self.validate_cfg(kw)
	if'msg'in kw:
		self.check_message_1(kw['msg'])
	ret=None
	try:
		ret=self.exec_cfg(kw)
	except Configure.ConfigurationError,e:
		if'errmsg'in kw:
			self.check_message_2(kw['errmsg'],'YELLOW')
		if'mandatory'in kw and kw['mandatory']:
			if Logs.verbose>1:
				raise
			else:
				self.fatal('the configuration failed (see %r)'%self.log.name)
	else:
		kw['success']=ret
		if'okmsg'in kw:
			self.check_message_2(self.ret_msg(kw['okmsg'],kw))
	return ret
def validate_c(self,kw):
	if not'env'in kw:
		kw['env']=self.env.copy()
	env=kw['env']
	if not'compiler'in kw:
		kw['compiler']='cc'
		if env['CXX_NAME']and Task.TaskBase.classes.get('cxx',None):
			kw['compiler']='cxx'
			if not self.env['CXX']:
				self.fatal('a c++ compiler is required')
		else:
			if not self.env['CC']:
				self.fatal('a c compiler is required')
	if not'type'in kw:
		kw['type']='cprogram'
	assert not(kw['type']!='cprogram'and kw.get('execute',0)),'can only execute programs'
	def to_header(dct):
		if'header_name'in dct:
			dct=Utils.to_list(dct['header_name'])
			return''.join(['#include <%s>\n'%x for x in dct])
		return''
	if not'compile_mode'in kw:
		kw['compile_mode']=(kw['compiler']=='cxx')and'cxx'or'cc'
	if not'compile_filename'in kw:
		kw['compile_filename']='test.c'+((kw['compile_mode']=='cxx')and'pp'or'')
	if'framework_name'in kw:
		try:TaskGen.task_gen.create_task_macapp
		except AttributeError:self.fatal('frameworks require the osx tool')
		fwkname=kw['framework_name']
		if not'uselib_store'in kw:
			kw['uselib_store']=fwkname.upper()
		if not kw.get('no_header',False):
			if not'header_name'in kw:
				kw['header_name']=[]
			fwk='%s/%s.h'%(fwkname,fwkname)
			if kw.get('remove_dot_h',None):
				fwk=fwk[:-2]
			kw['header_name']=Utils.to_list(kw['header_name'])+[fwk]
		kw['msg']='Checking for framework %s'%fwkname
		kw['framework']=fwkname
	if'function_name'in kw:
		fu=kw['function_name']
		if not'msg'in kw:
			kw['msg']='Checking for function %s'%fu
		kw['code']=to_header(kw)+SNIP1%fu
		if not'uselib_store'in kw:
			kw['uselib_store']=fu.upper()
		if not'define_name'in kw:
			kw['define_name']=self.have_define(fu)
	elif'type_name'in kw:
		tu=kw['type_name']
		if not'msg'in kw:
			kw['msg']='Checking for type %s'%tu
		if not'header_name'in kw:
			kw['header_name']='stdint.h'
		kw['code']=to_header(kw)+SNIP2%{'type_name':tu}
		if not'define_name'in kw:
			kw['define_name']=self.have_define(tu.upper())
	elif'header_name'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for header %s'%kw['header_name']
		l=Utils.to_list(kw['header_name'])
		assert len(l)>0,'list of headers in header_name is empty'
		kw['code']=to_header(kw)+SNIP3
		if not'uselib_store'in kw:
			kw['uselib_store']=l[0].upper()
		if not'define_name'in kw:
			kw['define_name']=self.have_define(l[0])
	if'lib'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for library %s'%kw['lib']
		if not'uselib_store'in kw:
			kw['uselib_store']=kw['lib'].upper()
	if'staticlib'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for static library %s'%kw['staticlib']
		if not'uselib_store'in kw:
			kw['uselib_store']=kw['staticlib'].upper()
	if'fragment'in kw:
		kw['code']=kw['fragment']
		if not'msg'in kw:
			kw['msg']='Checking for custom code'
		if not'errmsg'in kw:
			kw['errmsg']='no'
	for(flagsname,flagstype)in[('cxxflags','compiler'),('cflags','compiler'),('linkflags','linker')]:
		if flagsname in kw:
			if not'msg'in kw:
				kw['msg']='Checking for %s flags %s'%(flagstype,kw[flagsname])
			if not'errmsg'in kw:
				kw['errmsg']='no'
	if not'execute'in kw:
		kw['execute']=False
	if not'errmsg'in kw:
		kw['errmsg']='not found'
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	if not'code'in kw:
		kw['code']=SNIP3
	if not kw.get('success'):kw['success']=None
	assert'msg'in kw,'invalid parameters, read http://freehackers.org/~tnagy/wafbook/single.html#config_helpers_c'
def post_check(self,*k,**kw):
	is_success=False
	if kw['execute']:
		if kw['success']is not None:
			is_success=True
	else:
		is_success=(kw['success']==0)
	if'define_name'in kw:
		if'header_name'in kw or'function_name'in kw or'type_name'in kw or'fragment'in kw:
			if kw['execute']:
				key=kw['success']
				if isinstance(key,str):
					if key:
						self.define(kw['define_name'],key,quote=kw.get('quote',1))
					else:
						self.define_cond(kw['define_name'],True)
				else:
					self.define_cond(kw['define_name'],False)
			else:
				self.define_cond(kw['define_name'],is_success)
	if is_success and'uselib_store'in kw:
		import cc,cxx
		for k in set(cc.g_cc_flag_vars).union(cxx.g_cxx_flag_vars):
			lk=k.lower()
			if k=='CPPPATH':lk='includes'
			if k=='CXXDEFINES':lk='defines'
			if k=='CCDEFINES':lk='defines'
			if lk in kw:
				val=kw[lk]
				if isinstance(val,str):
					val=val.rstrip(os.path.sep)
				self.env.append_unique(k+'_'+kw['uselib_store'],val)
def check(self,*k,**kw):
	self.validate_c(kw)
	self.check_message_1(kw['msg'])
	ret=None
	try:
		ret=self.run_c_code(*k,**kw)
	except Configure.ConfigurationError,e:
		self.check_message_2(kw['errmsg'],'YELLOW')
		if'mandatory'in kw and kw['mandatory']:
			if Logs.verbose>1:
				raise
			else:
				self.fatal('the configuration failed (see %r)'%self.log.name)
	else:
		kw['success']=ret
		self.check_message_2(self.ret_msg(kw['okmsg'],kw))
	self.post_check(*k,**kw)
	if not kw.get('execute',False):
		return ret==0
	return ret
def run_c_code(self,*k,**kw):
	test_f_name=kw['compile_filename']
	k=0
	while k<10000:
		dir=os.path.join(self.blddir,'.conf_check_%d'%k)
		try:
			shutil.rmtree(dir)
		except OSError:
			pass
		try:
			os.stat(dir)
		except OSError:
			break
		k+=1
	try:
		os.makedirs(dir)
	except:
		self.fatal('cannot create a configuration test folder %r'%dir)
	try:
		os.stat(dir)
	except:
		self.fatal('cannot use the configuration test folder %r'%dir)
	bdir=os.path.join(dir,'testbuild')
	if not os.path.exists(bdir):
		os.makedirs(bdir)
	env=kw['env']
	dest=open(os.path.join(dir,test_f_name),'w')
	dest.write(kw['code'])
	dest.close()
	back=os.path.abspath('.')
	bld=Build.BuildContext()
	bld.log=self.log
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default']=env
	bld.lst_variants=bld.all_envs.keys()
	bld.load_dirs(dir,bdir)
	os.chdir(dir)
	bld.rescan(bld.srcnode)
	if not'features'in kw:
		kw['features']=[kw['compile_mode'],kw['type']]
	o=bld(features=kw['features'],source=test_f_name,target='testprog')
	for k,v in kw.iteritems():
		setattr(o,k,v)
	self.log.write("==>\n%s\n<==\n"%kw['code'])
	try:
		bld.compile()
	except Utils.WafError:
		ret=Utils.ex_stack()
	else:
		ret=0
	os.chdir(back)
	if ret:
		self.log.write('command returned %r'%ret)
		self.fatal(str(ret))
	if kw['execute']:
		lastprog=o.link_task.outputs[0].abspath(env)
		args=Utils.to_list(kw.get('exec_args',[]))
		proc=Utils.pproc.Popen([lastprog]+args,stdout=Utils.pproc.PIPE,stderr=Utils.pproc.PIPE)
		(out,err)=proc.communicate()
		w=self.log.write
		w(str(out))
		w('\n')
		w(str(err))
		w('\n')
		w('returncode %r'%proc.returncode)
		w('\n')
		if proc.returncode:
			self.fatal(Utils.ex_stack())
		ret=out
	return ret
def check_cxx(self,*k,**kw):
	kw['compiler']='cxx'
	return self.check(*k,**kw)
def check_cc(self,*k,**kw):
	kw['compiler']='cc'
	return self.check(*k,**kw)
def define(self,define,value,quote=1):
	assert define and isinstance(define,str)
	tbl=self.env[DEFINES]or Utils.ordered_dict()
	if isinstance(value,str):
		if quote:
			tbl[define]='"%s"'%repr('"'+value)[2:-1].replace('"','\\"')
		else:
			tbl[define]=value
	elif isinstance(value,int):
		tbl[define]=value
	else:
		raise TypeError('define %r -> %r must be a string or an int'%(define,value))
	self.env[DEFINES]=tbl
	self.env[define]=value
def undefine(self,define):
	assert define and isinstance(define,str)
	tbl=self.env[DEFINES]or Utils.ordered_dict()
	value=UNDEFINED
	tbl[define]=value
	self.env[DEFINES]=tbl
	self.env[define]=value
def define_cond(self,name,value):
	if value:
		self.define(name,1)
	else:
		self.undefine(name)
def is_defined(self,key):
	defines=self.env[DEFINES]
	if not defines:
		return False
	try:
		value=defines[key]
	except KeyError:
		return False
	else:
		return value!=UNDEFINED
def get_define(self,define):
	try:return self.env[DEFINES][define]
	except KeyError:return None
def have_define(self,name):
	return self.__dict__.get('HAVE_PAT','HAVE_%s')%Utils.quote_define_name(name)
def write_config_header(self,configfile='',env='',guard='',top=False):
	if not configfile:configfile=WAF_CONFIG_H
	waf_guard=guard or'_%s_WAF'%Utils.quote_define_name(configfile)
	if not env:env=self.env
	if top:
		diff=''
	else:
		diff=Utils.diff_path(self.srcdir,self.curdir)
	full=os.sep.join([self.blddir,env.variant(),diff,configfile])
	full=os.path.normpath(full)
	(dir,base)=os.path.split(full)
	try:os.makedirs(dir)
	except:pass
	dest=open(full,'w')
	dest.write('/* Configuration header created by Waf - do not edit */\n')
	dest.write('#ifndef %s\n#define %s\n\n'%(waf_guard,waf_guard))
	dest.write(self.get_config_header())
	env.append_unique(CFG_FILES,os.path.join(diff,configfile))
	dest.write('\n#endif /* %s */\n'%waf_guard)
	dest.close()
def get_config_header(self):
	config_header=[]
	tbl=self.env[DEFINES]or Utils.ordered_dict()
	for key in tbl.allkeys:
		value=tbl[key]
		if value is None:
			config_header.append('#define %s'%key)
		elif value is UNDEFINED:
			config_header.append('/* #undef %s */'%key)
		else:
			config_header.append('#define %s %s'%(key,value))
	return"\n".join(config_header)
def find_cpp(conf):
	v=conf.env
	cpp=None
	if v['CPP']:cpp=v['CPP']
	elif'CPP'in conf.environ:cpp=conf.environ['CPP']
	if not cpp:cpp=conf.find_program('cpp',var='CPP')
	if not cpp:cpp=v['CC']
	if not cpp:cpp=v['CXX']
	v['CPP']=cpp
def cc_add_flags(conf):
	conf.add_os_flags('CFLAGS','CCFLAGS')
	conf.add_os_flags('CPPFLAGS')
def cxx_add_flags(conf):
	conf.add_os_flags('CXXFLAGS')
	conf.add_os_flags('CPPFLAGS')
def link_add_flags(conf):
	conf.add_os_flags('LINKFLAGS')
	conf.add_os_flags('LDFLAGS','LINKFLAGS')
def cc_load_tools(conf):
	conf.check_tool('cc')
def cxx_load_tools(conf):
	conf.check_tool('cxx')

conf(ret_msg)
conf(validate_cfg)
conf(cmd_and_log)
conf(exec_cfg)
conf(check_cfg)
conf(validate_c)
conf(post_check)
conf(check)
conf(run_c_code)
conf(check_cxx)
conf(check_cc)
conf(define)
conf(undefine)
conf(define_cond)
conf(is_defined)
conf(get_define)
conf(have_define)
conf(write_config_header)
conf(get_config_header)
conftest(find_cpp)
conftest(cc_add_flags)
conftest(cxx_add_flags)
conftest(link_add_flags)
conftest(cc_load_tools)
conftest(cxx_load_tools)

########NEW FILE########
__FILENAME__ = dbus
#! /usr/bin/env python
# encoding: utf-8

import Task,Utils
from TaskGen import taskgen,before,after,feature
def add_dbus_file(self,filename,prefix,mode):
	if not hasattr(self,'dbus_lst'):
		self.dbus_lst=[]
	self.meths.append('process_dbus')
	self.dbus_lst.append([filename,prefix,mode])
def process_dbus(self):
	for filename,prefix,mode in getattr(self,'dbus_lst',[]):
		node=self.path.find_resource(filename)
		if not node:
			raise Utils.WafError('file not found '+filename)
		tsk=self.create_task('dbus_binding_tool',node,node.change_ext('.h'))
		tsk.env.DBUS_BINDING_TOOL_PREFIX=prefix
		tsk.env.DBUS_BINDING_TOOL_MODE=mode
Task.simple_task_type('dbus_binding_tool','${DBUS_BINDING_TOOL} --prefix=${DBUS_BINDING_TOOL_PREFIX} --mode=${DBUS_BINDING_TOOL_MODE} --output=${TGT} ${SRC}',color='BLUE',before='cc')
def detect(conf):
	dbus_binding_tool=conf.find_program('dbus-binding-tool',var='DBUS_BINDING_TOOL')

taskgen(add_dbus_file)
before('apply_core')(process_dbus)

########NEW FILE########
__FILENAME__ = gdc
#! /usr/bin/env python
# encoding: utf-8

import sys
import Utils,ar
from Configure import conftest
def find_gdc(conf):
	conf.find_program('gdc',var='D_COMPILER',mandatory=True)
def common_flags_gdc(conf):
	v=conf.env
	v['DFLAGS']=[]
	v['D_SRC_F']=''
	v['D_TGT_F']=['-c','-o','']
	v['DPATH_ST']='-I%s'
	v['D_LINKER']=v['D_COMPILER']
	v['DLNK_SRC_F']=''
	v['DLNK_TGT_F']=['-o','']
	v['DLIB_ST']='-l%s'
	v['DLIBPATH_ST']='-L%s'
	v['DLINKFLAGS']=[]
	v['DFLAGS_OPTIMIZED']=['-O3']
	v['DFLAGS_DEBUG']=['-O0']
	v['DFLAGS_ULTRADEBUG']=['-O0']
	v['D_shlib_DFLAGS']=[]
	v['D_shlib_LINKFLAGS']=['-shared']
	v['DHEADER_ext']='.di'
	v['D_HDR_F']='-fintfc -fintfc-file='
def detect(conf):
	conf.find_gdc()
	conf.check_tool('ar')
	conf.check_tool('d')
	conf.common_flags_gdc()
	conf.d_platform_flags()

conftest(find_gdc)
conftest(common_flags_gdc)

########NEW FILE########
__FILENAME__ = glib2
#! /usr/bin/env python
# encoding: utf-8

import Task,Utils
from TaskGen import taskgen,before,after,feature
def add_marshal_file(self,filename,prefix):
	if not hasattr(self,'marshal_list'):
		self.marshal_list=[]
	self.meths.append('process_marshal')
	self.marshal_list.append((filename,prefix))
def process_marshal(self):
	for f,prefix in getattr(self,'marshal_list',[]):
		node=self.path.find_resource(f)
		if not node:
			raise Utils.WafError('file not found %r'%f)
		h_node=node.change_ext('.h')
		c_node=node.change_ext('.c')
		task=self.create_task('glib_genmarshal',node,[h_node,c_node])
		task.env.GLIB_GENMARSHAL_PREFIX=prefix
	self.allnodes.append(c_node)
def genmarshal_func(self):
	bld=self.inputs[0].__class__.bld
	get=self.env.get_flat
	cmd1="%s %s --prefix=%s --header > %s"%(get('GLIB_GENMARSHAL'),self.inputs[0].srcpath(self.env),get('GLIB_GENMARSHAL_PREFIX'),self.outputs[0].abspath(self.env))
	ret=bld.exec_command(cmd1)
	if ret:return ret
	f=open(self.outputs[1].abspath(self.env),'wb')
	c='''#include "%s"\n'''%self.outputs[0].name
	f.write(c)
	f.close()
	cmd2="%s %s --prefix=%s --body >> %s"%(get('GLIB_GENMARSHAL'),self.inputs[0].srcpath(self.env),get('GLIB_GENMARSHAL_PREFIX'),self.outputs[1].abspath(self.env))
	ret=Utils.exec_command(cmd2)
	if ret:return ret
def add_enums_from_template(self,source='',target='',template='',comments=''):
	if not hasattr(self,'enums_list'):
		self.enums_list=[]
	self.meths.append('process_enums')
	self.enums_list.append({'source':source,'target':target,'template':template,'file-head':'','file-prod':'','file-tail':'','enum-prod':'','value-head':'','value-prod':'','value-tail':'','comments':comments})
def add_enums(self,source='',target='',file_head='',file_prod='',file_tail='',enum_prod='',value_head='',value_prod='',value_tail='',comments=''):
	if not hasattr(self,'enums_list'):
		self.enums_list=[]
	self.meths.append('process_enums')
	self.enums_list.append({'source':source,'template':'','target':target,'file-head':file_head,'file-prod':file_prod,'file-tail':file_tail,'enum-prod':enum_prod,'value-head':value_head,'value-prod':value_prod,'value-tail':value_tail,'comments':comments})
def process_enums(self):
	for enum in getattr(self,'enums_list',[]):
		task=self.create_task('glib_mkenums')
		env=task.env
		inputs=[]
		source_list=self.to_list(enum['source'])
		if not source_list:
			raise Utils.WafError('missing source '+str(enum))
		source_list=[self.path.find_resource(k)for k in source_list]
		inputs+=source_list
		env['GLIB_MKENUMS_SOURCE']=[k.srcpath(env)for k in source_list]
		if not enum['target']:
			raise Utils.WafError('missing target '+str(enum))
		tgt_node=self.path.find_or_declare(enum['target'])
		if tgt_node.name.endswith('.c'):
			self.allnodes.append(tgt_node)
		env['GLIB_MKENUMS_TARGET']=tgt_node.abspath(env)
		options=[]
		if enum['template']:
			template_node=self.path.find_resource(enum['template'])
			options.append('--template %s'%(template_node.abspath(env)))
			inputs.append(template_node)
		params={'file-head':'--fhead','file-prod':'--fprod','file-tail':'--ftail','enum-prod':'--eprod','value-head':'--vhead','value-prod':'--vprod','value-tail':'--vtail','comments':'--comments'}
		for param,option in params.iteritems():
			if enum[param]:
				options.append('%s %r'%(option,enum[param]))
		env['GLIB_MKENUMS_OPTIONS']=' '.join(options)
		task.set_inputs(inputs)
		task.set_outputs(tgt_node)
Task.task_type_from_func('glib_genmarshal',func=genmarshal_func,vars=['GLIB_GENMARSHAL_PREFIX','GLIB_GENMARSHAL'],color='BLUE',before='cc cxx')
Task.simple_task_type('glib_mkenums','${GLIB_MKENUMS} ${GLIB_MKENUMS_OPTIONS} ${GLIB_MKENUMS_SOURCE} > ${GLIB_MKENUMS_TARGET}',color='PINK',before='cc cxx')
def detect(conf):
	glib_genmarshal=conf.find_program('glib-genmarshal',var='GLIB_GENMARSHAL')
	mk_enums_tool=conf.find_program('glib-mkenums',var='GLIB_MKENUMS')

taskgen(add_marshal_file)
before('apply_core')(process_marshal)
taskgen(add_enums_from_template)
taskgen(add_enums)
before('apply_core')(process_enums)

########NEW FILE########
__FILENAME__ = gnome
#! /usr/bin/env python
# encoding: utf-8

import os,re
import TaskGen,Utils,Runner,Task,Build,Options,Logs
from Logs import error
from TaskGen import taskgen,before,after,feature
n1_regexp=re.compile('<refentrytitle>(.*)</refentrytitle>',re.M)
n2_regexp=re.compile('<manvolnum>(.*)</manvolnum>',re.M)
def postinstall_schemas(prog_name):
	if Build.bld.is_install:
		dir=Build.bld.get_install_path('${SYSCONFDIR}/gconf/schemas/%s.schemas'%prog_name)
		if not Options.options.destdir:
			Utils.pprint('YELLOW','Installing GConf schema')
			command='gconftool-2 --install-schema-file=%s 1> /dev/null'%dir
			ret=Utils.exec_command(command)
		else:
			Utils.pprint('YELLOW','GConf schema not installed. After install, run this:')
			Utils.pprint('YELLOW','gconftool-2 --install-schema-file=%s'%dir)
def postinstall_icons():
	dir=Build.bld.get_install_path('${DATADIR}/icons/hicolor')
	if Build.bld.is_install:
		if not Options.options.destdir:
			Utils.pprint('YELLOW',"Updating Gtk icon cache.")
			command='gtk-update-icon-cache -q -f -t %s'%dir
			ret=Utils.exec_command(command)
		else:
			Utils.pprint('YELLOW','Icon cache not updated. After install, run this:')
			Utils.pprint('YELLOW','gtk-update-icon-cache -q -f -t %s'%dir)
def postinstall_scrollkeeper(prog_name):
	if Build.bld.is_install:
		if os.access('/var/log/scrollkeeper.log',os.W_OK):
			dir1=Build.bld.get_install_path('${PREFIX}/var/scrollkeeper')
			dir2=Build.bld.get_install_path('${DATADIR}/omf/%s'%prog_name)
			command='scrollkeeper-update -q -p %s -o %s'%(dir1,dir2)
			ret=Utils.exec_command(command)
def postinstall(prog_name='myapp',schemas=1,icons=1,scrollkeeper=1):
	if schemas:postinstall_schemas(prog_name)
	if icons:postinstall_icons()
	if scrollkeeper:postinstall_scrollkeeper(prog_name)
class gnome_doc_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_gnome_doc(self):
	self.default_install_path='${PREFIX}/share'
def apply_gnome_doc(self):
	self.env['APPNAME']=self.doc_module
	lst=self.to_list(self.doc_linguas)
	bld=self.bld
	lst.append('C')
	for x in lst:
		if not x=='C':
			tsk=self.create_task('xml2po')
			node=self.path.find_resource(x+'/'+x+'.po')
			src=self.path.find_resource('C/%s.xml'%self.doc_module)
			out=self.path.find_or_declare('%s/%s.xml'%(x,self.doc_module))
			tsk.set_inputs([node,src])
			tsk.set_outputs(out)
		else:
			out=self.path.find_resource('%s/%s.xml'%(x,self.doc_module))
		tsk2=self.create_task('xsltproc2po')
		out2=self.path.find_or_declare('%s/%s-%s.omf'%(x,self.doc_module,x))
		tsk2.set_outputs(out2)
		node=self.path.find_resource(self.doc_module+".omf.in")
		tsk2.inputs=[node,out]
		tsk2.run_after.append(tsk)
		if bld.is_install:
			path=self.install_path+'/gnome/help/%s/%s'%(self.doc_module,x)
			bld.install_files(self.install_path+'/omf',out2,env=self.env)
			for y in self.to_list(self.doc_figures):
				try:
					os.stat(self.path.abspath()+'/'+x+'/'+y)
					bld.install_as(path+'/'+y,self.path.abspath()+'/'+x+'/'+y)
				except:
					bld.install_as(path+'/'+y,self.path.abspath()+'/C/'+y)
			bld.install_as(path+'/%s.xml'%self.doc_module,out.abspath(self.env))
			if x=='C':
				xmls=self.to_list(self.doc_includes)
				xmls.append(self.doc_entities)
				for z in xmls:
					out=self.path.find_resource('%s/%s'%(x,z))
					bld.install_as(path+'/%s'%z,out.abspath(self.env))
class xml_to_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_xml_to(self):
	Utils.def_attrs(self,source='xmlfile',xslt='xlsltfile',target='hey',default_install_path='${PREFIX}',task_created=None)
def apply_xml_to(self):
	xmlfile=self.path.find_resource(self.source)
	xsltfile=self.path.find_resource(self.xslt)
	tsk=self.create_task('xmlto',[xmlfile,xsltfile],xmlfile.change_ext('html'))
	tsk.install_path=self.install_path
def sgml_scan(self):
	node=self.inputs[0]
	env=self.env
	variant=node.variant(env)
	fi=open(node.abspath(env),'r')
	content=fi.read()
	fi.close()
	name=n1_regexp.findall(content)[0]
	num=n2_regexp.findall(content)[0]
	doc_name=name+'.'+num
	if not self.outputs:
		self.outputs=[self.generator.path.find_or_declare(doc_name)]
	return([],[doc_name])
class gnome_sgml2man_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_gnome_sgml2man(self):
	assert(getattr(self,'appname',None))
	def install_result(task):
		out=task.outputs[0]
		name=out.name
		ext=name[-1]
		env=task.env
		self.bld.install_files('${DATADIR}/man/man%s/'%ext,out,env)
	self.bld.rescan(self.path)
	for name in self.bld.cache_dir_contents[self.path.id]:
		base,ext=os.path.splitext(name)
		if ext!='.sgml':continue
		task=self.create_task('sgml2man')
		task.set_inputs(self.path.find_resource(name))
		task.task_generator=self
		if self.bld.is_install:task.install=install_result
		task.scan()
cls=Task.simple_task_type('sgml2man','${SGML2MAN} -o ${TGT[0].bld_dir(env)} ${SRC}  > /dev/null',color='BLUE')
cls.scan=sgml_scan
cls.quiet=1
Task.simple_task_type('xmlto','${XMLTO} html -m ${SRC[1].abspath(env)} ${SRC[0].abspath(env)}')
Task.simple_task_type('xml2po','${XML2PO} ${XML2POFLAGS} ${SRC} > ${TGT}',color='BLUE')
xslt_magic="""${XSLTPROC2PO} -o ${TGT[0].abspath(env)} \
--stringparam db2omf.basename ${APPNAME} \
--stringparam db2omf.format docbook \
--stringparam db2omf.lang ${TGT[0].abspath(env)[:-4].split('-')[-1]} \
--stringparam db2omf.dtd '-//OASIS//DTD DocBook XML V4.3//EN' \
--stringparam db2omf.omf_dir ${PREFIX}/share/omf \
--stringparam db2omf.help_dir ${PREFIX}/share/gnome/help \
--stringparam db2omf.omf_in ${SRC[0].abspath(env)} \
--stringparam db2omf.scrollkeeper_cl ${SCROLLKEEPER_DATADIR}/Templates/C/scrollkeeper_cl.xml \
${DB2OMF} ${SRC[1].abspath(env)}"""
Task.simple_task_type('xsltproc2po',xslt_magic,color='BLUE')
def detect(conf):
	conf.check_tool('gnu_dirs glib2 dbus')
	sgml2man=conf.find_program('docbook2man',var='SGML2MAN')
	def getstr(varname):
		return getattr(Options.options,varname,'')
	conf.define('GNOMELOCALEDIR',os.path.join(conf.env['DATADIR'],'locale'))
	xml2po=conf.find_program('xml2po',var='XML2PO')
	xsltproc2po=conf.find_program('xsltproc',var='XSLTPROC2PO')
	conf.env['XML2POFLAGS']='-e -p'
	conf.env['SCROLLKEEPER_DATADIR']=Utils.cmd_output("scrollkeeper-config --pkgdatadir",silent=1).strip()
	conf.env['DB2OMF']=Utils.cmd_output("/usr/bin/pkg-config --variable db2omf gnome-doc-utils",silent=1).strip()
def set_options(opt):
	opt.add_option('--want-rpath',type='int',default=1,dest='want_rpath',help='set rpath to 1 or 0 [Default 1]')

feature('gnome_doc')(init_gnome_doc)
feature('gnome_doc')(apply_gnome_doc)
after('init_gnome_doc')(apply_gnome_doc)
feature('xml_to')(init_xml_to)
feature('xml_to')(apply_xml_to)
after('init_xml_to')(apply_xml_to)
feature('gnome_sgml2man')(apply_gnome_sgml2man)

########NEW FILE########
__FILENAME__ = gnu_dirs
#! /usr/bin/env python
# encoding: utf-8

import Utils,Options
_options=[x.split(', ')for x in'''
bindir, user executables, ${EXEC_PREFIX}/bin
sbindir, system admin executables, ${EXEC_PREFIX}/sbin
libexecdir, program executables, ${EXEC_PREFIX}/libexec
sysconfdir, read-only single-machine data, ${PREFIX}/etc
sharedstatedir, modifiable architecture-independent data, ${PREFIX}/com
localstatedir, modifiable single-machine data, ${PREFIX}/var
libdir, object code libraries, ${EXEC_PREFIX}/lib
includedir, C header files, ${PREFIX}/include
oldincludedir, C header files for non-gcc, /usr/include
datarootdir, read-only arch.-independent data root, ${PREFIX}/share
datadir, read-only architecture-independent data, ${DATAROOTDIR}
infodir, info documentation, ${DATAROOTDIR}/info
localedir, locale-dependent data, ${DATAROOTDIR}/locale
mandir, man documentation, ${DATAROOTDIR}/man
docdir, documentation root, ${DATAROOTDIR}/doc/${PACKAGE}
htmldir, html documentation, ${DOCDIR}
dvidir, dvi documentation, ${DOCDIR}
pdfdir, pdf documentation, ${DOCDIR}
psdir, ps documentation, ${DOCDIR}
'''.split('\n')if x]
def detect(conf):
	def get_param(varname,default):
		return getattr(Options.options,varname,'')or default
	env=conf.env
	env['EXEC_PREFIX']=get_param('EXEC_PREFIX',env['PREFIX'])
	env['PACKAGE']=Utils.g_module.APPNAME
	complete=False
	iter=0
	while not complete and iter<len(_options)+1:
		iter+=1
		complete=True
		for name,help,default in _options:
			name=name.upper()
			if not env[name]:
				try:
					env[name]=Utils.subst_vars(get_param(name,default),env)
				except TypeError:
					complete=False
	if not complete:
		lst=[name for name,_,_ in _options if not env[name.upper()]]
		raise Utils.WafError('Variable substitution failure %r'%lst)
def set_options(opt):
	inst_dir=opt.add_option_group('Installation directories','By default, "waf install" will put the files in\
 "/usr/local/bin", "/usr/local/lib" etc. An installation prefix other\
 than "/usr/local" can be given using "--prefix", for example "--prefix=$HOME"')
	for k in('--prefix','--destdir'):
		option=opt.parser.get_option(k)
		if option:
			opt.parser.remove_option(k)
			inst_dir.add_option(option)
	inst_dir.add_option('--exec-prefix',help='installation prefix [Default: ${PREFIX}]',default='',dest='EXEC_PREFIX')
	dirs_options=opt.add_option_group('Pre-defined installation directories','')
	for name,help,default in _options:
		option_name='--'+name
		str_default=default
		str_help='%s [Default: %s]'%(help,str_default)
		dirs_options.add_option(option_name,help=str_help,default='',dest=name.upper())


########NEW FILE########
__FILENAME__ = intltool
#! /usr/bin/env python
# encoding: utf-8

import os,re
import Configure,TaskGen,Task,Utils,Runner,Options,Build,config_c
from TaskGen import feature,before,taskgen
from Logs import error
class intltool_in_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def iapply_intltool_in_f(self):
	try:self.meths.remove('apply_core')
	except ValueError:pass
	for i in self.to_list(self.source):
		node=self.path.find_resource(i)
		podir=getattr(self,'podir','po')
		podirnode=self.path.find_dir(podir)
		if not podirnode:
			error("could not find the podir %r"%podir)
			continue
		cache=getattr(self,'intlcache','.intlcache')
		self.env['INTLCACHE']=os.path.join(self.path.bldpath(self.env),podir,cache)
		self.env['INTLPODIR']=podirnode.srcpath(self.env)
		self.env['INTLFLAGS']=getattr(self,'flags',['-q','-u','-c'])
		task=self.create_task('intltool',node,node.change_ext(''))
		task.install_path=self.install_path
class intltool_po_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_intltool_po(self):
	try:self.meths.remove('apply_core')
	except ValueError:pass
	self.default_install_path='${LOCALEDIR}'
	appname=getattr(self,'appname','set_your_app_name')
	podir=getattr(self,'podir','')
	def install_translation(task):
		out=task.outputs[0]
		filename=out.name
		(langname,ext)=os.path.splitext(filename)
		inst_file=langname+os.sep+'LC_MESSAGES'+os.sep+appname+'.mo'
		self.bld.install_as(os.path.join(self.install_path,inst_file),out,self.env,self.chmod)
	linguas=self.path.find_resource(os.path.join(podir,'LINGUAS'))
	if linguas:
		file=open(linguas.abspath())
		langs=[]
		for line in file.readlines():
			if not line.startswith('#'):
				langs+=line.split()
		file.close()
		re_linguas=re.compile('[-a-zA-Z_@.]+')
		for lang in langs:
			if re_linguas.match(lang):
				node=self.path.find_resource(os.path.join(podir,re_linguas.match(lang).group()+'.po'))
				task=self.create_task('po')
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.mo'))
				if self.bld.is_install:task.install=install_translation
	else:
		Utils.pprint('RED',"Error no LINGUAS file found in po directory")
Task.simple_task_type('po','${POCOM} -o ${TGT} ${SRC}',color='BLUE',shell=False)
Task.simple_task_type('intltool','${INTLTOOL} ${INTLFLAGS} ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}',color='BLUE',after="cc_link cxx_link",shell=False)
def detect(conf):
	pocom=conf.find_program('msgfmt')
	if not pocom:
		conf.fatal('The program msgfmt (gettext) is mandatory!')
	conf.env['POCOM']=pocom
	intltool=conf.find_program('intltool-merge',var='INTLTOOL')
	if not intltool:
		if Options.platform=='win32':
			perl=conf.find_program('perl',var='PERL')
			if not perl:
				conf.fatal('The program perl (required by intltool) could not be found')
			intltooldir=Configure.find_file('intltool-merge',os.environ['PATH'].split(os.pathsep))
			if not intltooldir:
				conf.fatal('The program intltool-merge (intltool, gettext-devel) is mandatory!')
			conf.env['INTLTOOL']=Utils.to_list(conf.env['PERL'])+[intltooldir+os.sep+'intltool-merge']
			conf.check_message('intltool','',True,' '.join(conf.env['INTLTOOL']))
		else:
			conf.fatal('The program intltool-merge (intltool, gettext-devel) is mandatory!')
	def getstr(varname):
		return getattr(Options.options,varname,'')
	prefix=conf.env['PREFIX']
	datadir=getstr('datadir')
	if not datadir:datadir=os.path.join(prefix,'share')
	conf.define('LOCALEDIR',os.path.join(datadir,'locale'))
	conf.define('DATADIR',datadir)
	if conf.env['CC']or conf.env['CXX']:
		conf.check(header_name='locale.h')
def set_options(opt):
	opt.add_option('--want-rpath',type='int',default=1,dest='want_rpath',help='set rpath to 1 or 0 [Default 1]')
	opt.add_option('--datadir',type='string',default='',dest='datadir',help='read-only application data')

before('apply_core')(iapply_intltool_in_f)
feature('intltool_in')(iapply_intltool_in_f)
feature('intltool_po')(apply_intltool_po)

########NEW FILE########
__FILENAME__ = libtool
#! /usr/bin/env python
# encoding: utf-8

import sys,re,os,optparse
import TaskGen,Task,Utils,preproc
from Logs import error,debug,warn
from TaskGen import taskgen,after,before,feature
REVISION="0.1.3"
fakelibtool_vardeps=['CXX','PREFIX']
def fakelibtool_build(task):
	env=task.env
	dest=open(task.outputs[0].abspath(env),'w')
	sname=task.inputs[0].name
	fu=dest.write
	fu("# Generated by ltmain.sh - GNU libtool 1.5.18 - (pwn3d by BKsys II code name WAF)\n")
	if env['vnum']:
		nums=env['vnum'].split('.')
		libname=task.inputs[0].name
		name3=libname+'.'+env['vnum']
		name2=libname+'.'+nums[0]
		name1=libname
		fu("dlname='%s'\n"%name2)
		strn=" ".join([name3,name2,name1])
		fu("library_names='%s'\n"%(strn))
	else:
		fu("dlname='%s'\n"%sname)
		fu("library_names='%s %s %s'\n"%(sname,sname,sname))
	fu("old_library=''\n")
	vars=' '.join(env['libtoolvars']+env['LINKFLAGS'])
	fu("dependency_libs='%s'\n"%vars)
	fu("current=0\n")
	fu("age=0\nrevision=0\ninstalled=yes\nshouldnotlink=no\n")
	fu("dlopen=''\ndlpreopen=''\n")
	fu("libdir='%s/lib'\n"%env['PREFIX'])
	dest.close()
	return 0
def read_la_file(path):
	sp=re.compile(r'^([^=]+)=\'(.*)\'$')
	dc={}
	file=open(path,"r")
	for line in file.readlines():
		try:
			_,left,right,_=sp.split(line.strip())
			dc[left]=right
		except ValueError:
			pass
	file.close()
	return dc
def apply_link_libtool(self):
	if self.type!='program':
		linktask=self.link_task
		self.latask=self.create_task('fakelibtool',linktask.outputs,linktask.outputs[0].change_ext('.la'))
	if self.bld.is_install:
		self.bld.install_files('${PREFIX}/lib',linktask.outputs[0],self.env)
def apply_libtool(self):
	self.env['vnum']=self.vnum
	paths=[]
	libs=[]
	libtool_files=[]
	libtool_vars=[]
	for l in self.env['LINKFLAGS']:
		if l[:2]=='-L':
			paths.append(l[2:])
		elif l[:2]=='-l':
			libs.append(l[2:])
	for l in libs:
		for p in paths:
			dict=read_la_file(p+'/lib'+l+'.la')
			linkflags2=dict.get('dependency_libs','')
			for v in linkflags2.split():
				if v.endswith('.la'):
					libtool_files.append(v)
					libtool_vars.append(v)
					continue
				self.env.append_unique('LINKFLAGS',v)
				break
	self.env['libtoolvars']=libtool_vars
	while libtool_files:
		file=libtool_files.pop()
		dict=read_la_file(file)
		for v in dict['dependency_libs'].split():
			if v[-3:]=='.la':
				libtool_files.append(v)
				continue
			self.env.append_unique('LINKFLAGS',v)
Task.task_type_from_func('fakelibtool',vars=fakelibtool_vardeps,func=fakelibtool_build,color='BLUE',after="cc_link cxx_link static_link")
class libtool_la_file:
	def __init__(self,la_filename):
		self.__la_filename=la_filename
		self.linkname=str(os.path.split(la_filename)[-1])[:-3]
		if self.linkname.startswith("lib"):
			self.linkname=self.linkname[3:]
		self.dlname=None
		self.library_names=None
		self.old_library=None
		self.dependency_libs=None
		self.current=None
		self.age=None
		self.revision=None
		self.installed=None
		self.shouldnotlink=None
		self.dlopen=None
		self.dlpreopen=None
		self.libdir='/usr/lib'
		if not self.__parse():
			raise"file %s not found!!"%(la_filename)
	def __parse(self):
		if not os.path.isfile(self.__la_filename):return 0
		la_file=open(self.__la_filename,'r')
		for line in la_file:
			ln=line.strip()
			if not ln:continue
			if ln[0]=='#':continue
			(key,value)=str(ln).split('=',1)
			key=key.strip()
			value=value.strip()
			if value=="no":value=False
			elif value=="yes":value=True
			else:
				try:value=int(value)
				except ValueError:value=value.strip("'")
			setattr(self,key,value)
		la_file.close()
		return 1
	def get_libs(self):
		libs=[]
		if self.dependency_libs:
			libs=str(self.dependency_libs).strip().split()
		if libs==None:
			libs=[]
		libs.insert(0,"-l%s"%self.linkname.strip())
		libs.insert(0,"-L%s"%self.libdir.strip())
		return libs
	def __str__(self):
		return'''\
dlname = "%(dlname)s"
library_names = "%(library_names)s"
old_library = "%(old_library)s"
dependency_libs = "%(dependency_libs)s"
version = %(current)s.%(age)s.%(revision)s
installed = "%(installed)s"
shouldnotlink = "%(shouldnotlink)s"
dlopen = "%(dlopen)s"
dlpreopen = "%(dlpreopen)s"
libdir = "%(libdir)s"'''%self.__dict__
class libtool_config:
	def __init__(self,la_filename):
		self.__libtool_la_file=libtool_la_file(la_filename)
		tmp=self.__libtool_la_file
		self.__version=[int(tmp.current),int(tmp.age),int(tmp.revision)]
		self.__sub_la_files=[]
		self.__sub_la_files.append(la_filename)
		self.__libs=None
	def __cmp__(self,other):
		if not other:
			return 1
		othervers=[int(s)for s in str(other).split(".")]
		selfvers=self.__version
		return cmp(selfvers,othervers)
	def __str__(self):
		return"\n".join([str(self.__libtool_la_file),' '.join(self.__libtool_la_file.get_libs()),'* New getlibs:',' '.join(self.get_libs())])
	def __get_la_libs(self,la_filename):
		return libtool_la_file(la_filename).get_libs()
	def get_libs(self):
		libs_list=list(self.__libtool_la_file.get_libs())
		libs_map={}
		while len(libs_list)>0:
			entry=libs_list.pop(0)
			if entry:
				if str(entry).endswith(".la"):
					if entry not in self.__sub_la_files:
						self.__sub_la_files.append(entry)
						libs_list.extend(self.__get_la_libs(entry))
				else:
					libs_map[entry]=1
		self.__libs=libs_map.keys()
		return self.__libs
	def get_libs_only_L(self):
		if not self.__libs:self.get_libs()
		libs=self.__libs
		libs=[s for s in libs if str(s).startswith('-L')]
		return libs
	def get_libs_only_l(self):
		if not self.__libs:self.get_libs()
		libs=self.__libs
		libs=[s for s in libs if str(s).startswith('-l')]
		return libs
	def get_libs_only_other(self):
		if not self.__libs:self.get_libs()
		libs=self.__libs
		libs=[s for s in libs if not(str(s).startswith('-L')or str(s).startswith('-l'))]
		return libs
def useCmdLine():
	usage='''Usage: %prog [options] PathToFile.la
example: %prog --atleast-version=2.0.0 /usr/lib/libIlmImf.la
nor: %prog --libs /usr/lib/libamarok.la'''
	parser=optparse.OptionParser(usage)
	a=parser.add_option
	a("--version",dest="versionNumber",action="store_true",default=False,help="output version of libtool-config")
	a("--debug",dest="debug",action="store_true",default=False,help="enable debug")
	a("--libs",dest="libs",action="store_true",default=False,help="output all linker flags")
	a("--libs-only-l",dest="libs_only_l",action="store_true",default=False,help="output -l flags")
	a("--libs-only-L",dest="libs_only_L",action="store_true",default=False,help="output -L flags")
	a("--libs-only-other",dest="libs_only_other",action="store_true",default=False,help="output other libs (e.g. -pthread)")
	a("--atleast-version",dest="atleast_version",default=None,help="return 0 if the module is at least version ATLEAST_VERSION")
	a("--exact-version",dest="exact_version",default=None,help="return 0 if the module is exactly version EXACT_VERSION")
	a("--max-version",dest="max_version",default=None,help="return 0 if the module is at no newer than version MAX_VERSION")
	(options,args)=parser.parse_args()
	if len(args)!=1 and not options.versionNumber:
		parser.error("incorrect number of arguments")
	if options.versionNumber:
		print("libtool-config version %s"%REVISION)
		return 0
	ltf=libtool_config(args[0])
	if options.debug:
		print(ltf)
	if options.atleast_version:
		if ltf>=options.atleast_version:return 0
		sys.exit(1)
	if options.exact_version:
		if ltf==options.exact_version:return 0
		sys.exit(1)
	if options.max_version:
		if ltf<=options.max_version:return 0
		sys.exit(1)
	def p(x):
		print(" ".join(x))
	if options.libs:p(ltf.get_libs())
	elif options.libs_only_l:p(ltf.get_libs_only_l())
	elif options.libs_only_L:p(ltf.get_libs_only_L())
	elif options.libs_only_other:p(ltf.get_libs_only_other())
	return 0
if __name__=='__main__':
	useCmdLine()

feature("libtool")(apply_link_libtool)
after('apply_link')(apply_link_libtool)
feature("libtool")(apply_libtool)
before('apply_core')(apply_libtool)

########NEW FILE########
__FILENAME__ = misc
#! /usr/bin/env python
# encoding: utf-8

import shutil,re,os
import TaskGen,Node,Task,Utils,Build,Constants
from TaskGen import feature,taskgen,after,before
from Logs import debug
def copy_func(tsk):
	env=tsk.env
	infile=tsk.inputs[0].abspath(env)
	outfile=tsk.outputs[0].abspath(env)
	try:
		shutil.copy2(infile,outfile)
	except(OSError,IOError):
		return 1
	else:
		if tsk.chmod:os.chmod(outfile,tsk.chmod)
		return 0
def action_process_file_func(tsk):
	if not tsk.fun:raise Utils.WafError('task must have a function attached to it for copy_func to work!')
	return tsk.fun(tsk)
class cmd_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_cmd(self):
	if not self.fun:raise Utils.WafError('cmdobj needs a function!')
	tsk=Task.TaskBase()
	tsk.fun=self.fun
	tsk.env=self.env
	self.tasks.append(tsk)
	tsk.install_path=self.install_path
class copy_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_copy(self):
	Utils.def_attrs(self,fun=copy_func)
	self.default_install_path=0
	lst=self.to_list(self.source)
	self.meths.remove('apply_core')
	for filename in lst:
		node=self.path.find_resource(filename)
		if not node:raise Utils.WafError('cannot find input file %s for processing'%filename)
		target=self.target
		if not target or len(lst)>1:target=node.name
		newnode=self.path.find_or_declare(target)
		tsk=self.create_task('copy',node,newnode)
		tsk.fun=self.fun
		tsk.chmod=self.chmod
		tsk.install_path=self.install_path
		if not tsk.env:
			tsk.debug()
			raise Utils.WafError('task without an environment')
def subst_func(tsk):
	m4_re=re.compile('@(\w+)@',re.M)
	env=tsk.env
	infile=tsk.inputs[0].abspath(env)
	outfile=tsk.outputs[0].abspath(env)
	code=Utils.readf(infile)
	code=code.replace('%','%%')
	s=m4_re.sub(r'%(\1)s',code)
	di=tsk.dict or{}
	if not di:
		names=m4_re.findall(code)
		for i in names:
			di[i]=env.get_flat(i)or env.get_flat(i.upper())
	file=open(outfile,'w')
	file.write(s%di)
	file.close()
	if tsk.chmod:os.chmod(outfile,tsk.chmod)
class subst_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_subst(self):
	Utils.def_attrs(self,fun=subst_func)
	self.default_install_path=0
	lst=self.to_list(self.source)
	self.meths.remove('apply_core')
	self.dict=getattr(self,'dict',{})
	for filename in lst:
		node=self.path.find_resource(filename)
		if not node:raise Utils.WafError('cannot find input file %s for processing'%filename)
		if self.target:
			newnode=self.path.find_or_declare(self.target)
		else:
			newnode=node.change_ext('')
		try:
			self.dict=self.dict.get_merged_dict()
		except AttributeError:
			pass
		if self.dict and not self.env['DICT_HASH']:
			self.env=self.env.copy()
			keys=list(self.dict.keys())
			keys.sort()
			lst=[self.dict[x]for x in keys]
			self.env['DICT_HASH']=str(Utils.h_list(lst))
		tsk=self.create_task('copy',node,newnode)
		tsk.fun=self.fun
		tsk.dict=self.dict
		tsk.dep_vars=['DICT_HASH']
		tsk.install_path=self.install_path
		tsk.chmod=self.chmod
		if not tsk.env:
			tsk.debug()
			raise Utils.WafError('task without an environment')
class cmd_arg(object):
	def __init__(self,name,template='%s'):
		self.name=name
		self.template=template
		self.node=None
class input_file(cmd_arg):
	def find_node(self,base_path):
		assert isinstance(base_path,Node.Node)
		self.node=base_path.find_resource(self.name)
		if self.node is None:
			raise Utils.WafError("Input file %s not found in "%(self.name,base_path))
	def get_path(self,env,absolute):
		if absolute:
			return self.template%self.node.abspath(env)
		else:
			return self.template%self.node.srcpath(env)
class output_file(cmd_arg):
	def find_node(self,base_path):
		assert isinstance(base_path,Node.Node)
		self.node=base_path.find_or_declare(self.name)
		if self.node is None:
			raise Utils.WafError("Output file %s not found in "%(self.name,base_path))
	def get_path(self,env,absolute):
		if absolute:
			return self.template%self.node.abspath(env)
		else:
			return self.template%self.node.bldpath(env)
class cmd_dir_arg(cmd_arg):
	def find_node(self,base_path):
		assert isinstance(base_path,Node.Node)
		self.node=base_path.find_dir(self.name)
		if self.node is None:
			raise Utils.WafError("Directory %s not found in "%(self.name,base_path))
class input_dir(cmd_dir_arg):
	def get_path(self,dummy_env,dummy_absolute):
		return self.template%self.node.abspath()
class output_dir(cmd_dir_arg):
	def get_path(self,env,dummy_absolute):
		return self.template%self.node.abspath(env)
class command_output(Task.Task):
	color="BLUE"
	def __init__(self,env,command,command_node,command_args,stdin,stdout,cwd,os_env,stderr):
		Task.Task.__init__(self,env,normal=1)
		assert isinstance(command,(str,Node.Node))
		self.command=command
		self.command_args=command_args
		self.stdin=stdin
		self.stdout=stdout
		self.cwd=cwd
		self.os_env=os_env
		self.stderr=stderr
		if command_node is not None:self.dep_nodes=[command_node]
		self.dep_vars=[]
	def run(self):
		task=self
		def input_path(node,template):
			if task.cwd is None:
				return template%node.bldpath(task.env)
			else:
				return template%node.abspath()
		def output_path(node,template):
			fun=node.abspath
			if task.cwd is None:fun=node.bldpath
			return template%fun(task.env)
		if isinstance(task.command,Node.Node):
			argv=[input_path(task.command,'%s')]
		else:
			argv=[task.command]
		for arg in task.command_args:
			if isinstance(arg,str):
				argv.append(arg)
			else:
				assert isinstance(arg,cmd_arg)
				argv.append(arg.get_path(task.env,(task.cwd is not None)))
		if task.stdin:
			stdin=open(input_path(task.stdin,'%s'))
		else:
			stdin=None
		if task.stdout:
			stdout=open(output_path(task.stdout,'%s'),"w")
		else:
			stdout=None
		if task.stderr:
			stderr=open(output_path(task.stderr,'%s'),"w")
		else:
			stderr=None
		if task.cwd is None:
			cwd=('None (actually %r)'%os.getcwd())
		else:
			cwd=repr(task.cwd)
		debug("command-output: cwd=%s, stdin=%r, stdout=%r, argv=%r"%(cwd,stdin,stdout,argv))
		if task.os_env is None:
			os_env=os.environ
		else:
			os_env=task.os_env
		command=Utils.pproc.Popen(argv,stdin=stdin,stdout=stdout,stderr=stderr,cwd=task.cwd,env=os_env)
		return command.wait()
class cmd_output_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_cmd_output(self):
	Utils.def_attrs(self,stdin=None,stdout=None,stderr=None,command=None,command_is_external=False,argv=[],dependencies=[],dep_vars=[],hidden_inputs=[],hidden_outputs=[],cwd=None,os_env=None)
def apply_cmd_output(self):
	if self.command is None:
		raise Utils.WafError("command-output missing command")
	if self.command_is_external:
		cmd=self.command
		cmd_node=None
	else:
		cmd_node=self.path.find_resource(self.command)
		assert cmd_node is not None,('''Could not find command '%s' in source tree.
Hint: if this is an external command,
use command_is_external=True''')%(self.command,)
		cmd=cmd_node
	if self.cwd is None:
		cwd=None
	else:
		assert isinstance(cwd,CmdDirArg)
		self.cwd.find_node(self.path)
	args=[]
	inputs=[]
	outputs=[]
	for arg in self.argv:
		if isinstance(arg,cmd_arg):
			arg.find_node(self.path)
			if isinstance(arg,input_file):
				inputs.append(arg.node)
			if isinstance(arg,output_file):
				outputs.append(arg.node)
	if self.stdout is None:
		stdout=None
	else:
		assert isinstance(self.stdout,str)
		stdout=self.path.find_or_declare(self.stdout)
		if stdout is None:
			raise Utils.WafError("File %s not found"%(self.stdout,))
		outputs.append(stdout)
	if self.stderr is None:
		stderr=None
	else:
		assert isinstance(self.stderr,str)
		stderr=self.path.find_or_declare(self.stderr)
		if stderr is None:
			raise Utils.WafError("File %s not found"%(self.stderr,))
		outputs.append(stderr)
	if self.stdin is None:
		stdin=None
	else:
		assert isinstance(self.stdin,str)
		stdin=self.path.find_resource(self.stdin)
		if stdin is None:
			raise Utils.WafError("File %s not found"%(self.stdin,))
		inputs.append(stdin)
	for hidden_input in self.to_list(self.hidden_inputs):
		node=self.path.find_resource(hidden_input)
		if node is None:
			raise Utils.WafError("File %s not found in dir %s"%(hidden_input,self.path))
		inputs.append(node)
	for hidden_output in self.to_list(self.hidden_outputs):
		node=self.path.find_or_declare(hidden_output)
		if node is None:
			raise Utils.WafError("File %s not found in dir %s"%(hidden_output,self.path))
		outputs.append(node)
	if not(inputs or getattr(self,'no_inputs',None)):
		raise Utils.WafError('command-output objects must have at least one input file or give self.no_inputs')
	if not(outputs or getattr(self,'no_outputs',None)):
		raise Utils.WafError('command-output objects must have at least one output file or give self.no_outputs')
	task=command_output(self.env,cmd,cmd_node,self.argv,stdin,stdout,cwd,self.os_env,stderr)
	Utils.copy_attrs(self,task,'before after ext_in ext_out',only_if_set=True)
	self.tasks.append(task)
	task.inputs=inputs
	task.outputs=outputs
	task.dep_vars=self.to_list(self.dep_vars)
	for dep in self.dependencies:
		assert dep is not self
		dep.post()
		for dep_task in dep.tasks:
			task.set_run_after(dep_task)
	if not task.inputs:
		task.runnable_status=type(Task.TaskBase.run)(runnable_status,task,task.__class__)
		task.post_run=type(Task.TaskBase.run)(post_run,task,task.__class__)
def post_run(self):
	for x in self.outputs:
		h=Utils.h_file(x.abspath(self.env))
		self.generator.bld.node_sigs[self.env.variant()][x.id]=h
def runnable_status(self):
	return Constants.RUN_ME
Task.task_type_from_func('copy',vars=[],func=action_process_file_func)
TaskGen.task_gen.classes['command-output']=cmd_output_taskgen

feature('cmd')(apply_cmd)
feature('copy')(apply_copy)
before('apply_core')(apply_copy)
feature('subst')(apply_subst)
before('apply_core')(apply_subst)
feature('command-output')(init_cmd_output)
feature('command-output')(apply_cmd_output)
after('init_cmd_output')(apply_cmd_output)

########NEW FILE########
__FILENAME__ = preproc
#! /usr/bin/env python
# encoding: utf-8

import re,sys,os,string
import Logs,Build,Utils
from Logs import debug,error
import traceback
class PreprocError(Utils.WafError):
	pass
POPFILE='-'
recursion_limit=100
go_absolute=0
standard_includes=['/usr/include']
if sys.platform=="win32":
	standard_includes=[]
use_trigraphs=0
'apply the trigraph rules first'
strict_quotes=0
g_optrans={'not':'!','and':'&&','bitand':'&','and_eq':'&=','or':'||','bitor':'|','or_eq':'|=','xor':'^','xor_eq':'^=','compl':'~',}
re_lines=re.compile('^[ \t]*(#|%:)[ \t]*(ifdef|ifndef|if|else|elif|endif|include|import|define|undef|pragma)[ \t]*(.*)\r*$',re.IGNORECASE|re.MULTILINE)
re_mac=re.compile("^[a-zA-Z_]\w*")
re_fun=re.compile('^[a-zA-Z_][a-zA-Z0-9_]*[(]')
re_pragma_once=re.compile('^\s*once\s*',re.IGNORECASE)
re_nl=re.compile('\\\\\r*\n',re.MULTILINE)
re_cpp=re.compile(r"""(/\*[^*]*\*+([^/*][^*]*\*+)*/)|//[^\n]*|("(\\.|[^"\\])*"|'(\\.|[^'\\])*'|.[^/"'\\]*)""",re.MULTILINE)
trig_def=[('??'+a,b)for a,b in zip("=-/!'()<>",r'#~\|^[]{}')]
chr_esc={'0':0,'a':7,'b':8,'t':9,'n':10,'f':11,'v':12,'r':13,'\\':92,"'":39}
NUM='i'
OP='O'
IDENT='T'
STR='s'
CHAR='c'
tok_types=[NUM,STR,IDENT,OP]
exp_types=[r"""0[xX](?P<hex>[a-fA-F0-9]+)(?P<qual1>[uUlL]*)|L*?'(?P<char>(\\.|[^\\'])+)'|(?P<n1>\d+)[Ee](?P<exp0>[+-]*?\d+)(?P<float0>[fFlL]*)|(?P<n2>\d*\.\d+)([Ee](?P<exp1>[+-]*?\d+))?(?P<float1>[fFlL]*)|(?P<n4>\d+\.\d*)([Ee](?P<exp2>[+-]*?\d+))?(?P<float2>[fFlL]*)|(?P<oct>0*)(?P<n0>\d+)(?P<qual2>[uUlL]*)""",r'L?"([^"\\]|\\.)*"',r'[a-zA-Z_]\w*',r'%:%:|<<=|>>=|\.\.\.|<<|<%|<:|<=|>>|>=|\+\+|\+=|--|->|-=|\*=|/=|%:|%=|%>|==|&&|&=|\|\||\|=|\^=|:>|!=|##|[\(\)\{\}\[\]<>\?\|\^\*\+&=:!#;,%/\-\?\~\.]',]
re_clexer=re.compile('|'.join(["(?P<%s>%s)"%(name,part)for name,part in zip(tok_types,exp_types)]),re.M)
accepted='a'
ignored='i'
undefined='u'
skipped='s'
def repl(m):
	s=m.group(1)
	if s is not None:return' '
	s=m.group(3)
	if s is None:return''
	return s
def filter_comments(filename):
	code=Utils.readf(filename)
	if use_trigraphs:
		for(a,b)in trig_def:code=code.split(a).join(b)
	code=re_nl.sub('',code)
	code=re_cpp.sub(repl,code)
	return[(m.group(2),m.group(3))for m in re.finditer(re_lines,code)]
prec={}
ops=['* / %','+ -','<< >>','< <= >= >','== !=','& | ^','&& ||',',']
for x in range(len(ops)):
	syms=ops[x]
	for u in syms.split():
		prec[u]=x
def reduce_nums(val_1,val_2,val_op):
	try:a=0+val_1
	except TypeError:a=int(val_1)
	try:b=0+val_2
	except TypeError:b=int(val_2)
	d=val_op
	if d=='%':c=a%b
	elif d=='+':c=a+b
	elif d=='-':c=a-b
	elif d=='*':c=a*b
	elif d=='/':c=a/b
	elif d=='^':c=a^b
	elif d=='|':c=a|b
	elif d=='||':c=int(a or b)
	elif d=='&':c=a&b
	elif d=='&&':c=int(a and b)
	elif d=='==':c=int(a==b)
	elif d=='!=':c=int(a!=b)
	elif d=='<=':c=int(a<=b)
	elif d=='<':c=int(a<b)
	elif d=='>':c=int(a>b)
	elif d=='>=':c=int(a>=b)
	elif d=='^':c=int(a^b)
	elif d=='<<':c=a<<b
	elif d=='>>':c=a>>b
	else:c=0
	return c
def get_num(lst):
	if not lst:raise PreprocError("empty list for get_num")
	(p,v)=lst[0]
	if p==OP:
		if v=='(':
			count_par=1
			i=1
			while i<len(lst):
				(p,v)=lst[i]
				if p==OP:
					if v==')':
						count_par-=1
						if count_par==0:
							break
					elif v=='(':
						count_par+=1
				i+=1
			else:
				raise PreprocError("rparen expected %r"%lst)
			(num,_)=get_term(lst[1:i])
			return(num,lst[i+1:])
		elif v=='+':
			return get_num(lst[1:])
		elif v=='-':
			num,lst=get_num(lst[1:])
			return(reduce_nums('-1',num,'*'),lst)
		elif v=='!':
			num,lst=get_num(lst[1:])
			return(int(not int(num)),lst)
		elif v=='~':
			return(~int(num),lst)
		else:
			raise PreprocError("invalid op token %r for get_num"%lst)
	elif p==NUM:
		return v,lst[1:]
	elif p==IDENT:
		return 0,lst[1:]
	else:
		raise PreprocError("invalid token %r for get_num"%lst)
def get_term(lst):
	if not lst:raise PreprocError("empty list for get_term")
	num,lst=get_num(lst)
	if not lst:
		return(num,[])
	(p,v)=lst[0]
	if p==OP:
		if v=='&&'and not num:
			return(num,[])
		elif v=='||'and num:
			return(num,[])
		elif v==',':
			return get_term(lst[1:])
		elif v=='?':
			count_par=0
			i=1
			while i<len(lst):
				(p,v)=lst[i]
				if p==OP:
					if v==')':
						count_par-=1
					elif v=='(':
						count_par+=1
					elif v==':':
						if count_par==0:
							break
				i+=1
			else:
				raise PreprocError("rparen expected %r"%lst)
			if int(num):
				return get_term(lst[1:i])
			else:
				return get_term(lst[i+1:])
		else:
			num2,lst=get_num(lst[1:])
			if not lst:
				num2=reduce_nums(num,num2,v)
				return get_term([(NUM,num2)]+lst)
			p2,v2=lst[0]
			if p2!=OP:
				raise PreprocError("op expected %r"%lst)
			if prec[v2]>=prec[v]:
				num2=reduce_nums(num,num2,v)
				return get_term([(NUM,num2)]+lst)
			else:
				num3,lst=get_num(lst[1:])
				num3=reduce_nums(num2,num3,v2)
				return get_term([(NUM,num),(p,v),(NUM,num3)]+lst)
	raise PreprocError("cannot reduce %r"%lst)
def reduce_eval(lst):
	num,lst=get_term(lst)
	return(NUM,num)
def stringize(lst):
	lst=[str(v2)for(p2,v2)in lst]
	return"".join(lst)
def paste_tokens(t1,t2):
	p1=None
	if t1[0]==OP and t2[0]==OP:
		p1=OP
	elif t1[0]==IDENT and(t2[0]==IDENT or t2[0]==NUM):
		p1=IDENT
	elif t1[0]==NUM and t2[0]==NUM:
		p1=NUM
	if not p1:
		raise PreprocError('tokens do not make a valid paste %r and %r'%(t1,t2))
	return(p1,t1[1]+t2[1])
def reduce_tokens(lst,defs,ban=[]):
	i=0
	while i<len(lst):
		(p,v)=lst[i]
		if p==IDENT and v=="defined":
			del lst[i]
			if i<len(lst):
				(p2,v2)=lst[i]
				if p2==IDENT:
					if v2 in defs:
						lst[i]=(NUM,1)
					else:
						lst[i]=(NUM,0)
				elif p2==OP and v2=='(':
					del lst[i]
					(p2,v2)=lst[i]
					del lst[i]
					if v2 in defs:
						lst[i]=(NUM,1)
					else:
						lst[i]=(NUM,0)
				else:
					raise PreprocError("invalid define expression %r"%lst)
		elif p==IDENT and v in defs:
			if isinstance(defs[v],str):
				a,b=extract_macro(defs[v])
				defs[v]=b
			macro_def=defs[v]
			to_add=macro_def[1]
			if isinstance(macro_def[0],list):
				del lst[i]
				for x in xrange(len(to_add)):
					lst.insert(i,to_add[x])
					i+=1
			else:
				args=[]
				del lst[i]
				if i>=len(lst):
					raise PreprocError("expected '(' after %r (got nothing)"%v)
				(p2,v2)=lst[i]
				if p2!=OP or v2!='(':
					raise PreprocError("expected '(' after %r"%v)
				del lst[i]
				one_param=[]
				count_paren=0
				while i<len(lst):
					p2,v2=lst[i]
					del lst[i]
					if p2==OP and count_paren==0:
						if v2=='(':
							one_param.append((p2,v2))
							count_paren+=1
						elif v2==')':
							if one_param:args.append(one_param)
							break
						elif v2==',':
							if not one_param:raise PreprocError("empty param in funcall %s"%p)
							args.append(one_param)
							one_param=[]
						else:
							one_param.append((p2,v2))
					else:
						one_param.append((p2,v2))
						if v2=='(':count_paren+=1
						elif v2==')':count_paren-=1
				else:
					raise PreprocError('malformed macro')
				accu=[]
				arg_table=macro_def[0]
				j=0
				while j<len(to_add):
					(p2,v2)=to_add[j]
					if p2==OP and v2=='#':
						if j+1<len(to_add)and to_add[j+1][0]==IDENT and to_add[j+1][1]in arg_table:
							toks=args[arg_table[to_add[j+1][1]]]
							accu.append((STR,stringize(toks)))
							j+=1
						else:
							accu.append((p2,v2))
					elif p2==OP and v2=='##':
						if accu and j+1<len(to_add):
							t1=accu[-1]
							if to_add[j+1][0]==IDENT and to_add[j+1][1]in arg_table:
								toks=args[arg_table[to_add[j+1][1]]]
								if toks:
									accu[-1]=paste_tokens(t1,toks[0])
									accu.extend(toks[1:])
								else:
									accu.append((p2,v2))
									accu.extend(toks)
							elif to_add[j+1][0]==IDENT and to_add[j+1][1]=='__VA_ARGS__':
								va_toks=[]
								st=len(macro_def[0])
								pt=len(args)
								for x in args[pt-st+1:]:
									va_toks.extend(x)
									va_toks.append((OP,','))
								if va_toks:va_toks.pop()
								if len(accu)>1:
									(p3,v3)=accu[-1]
									(p4,v4)=accu[-2]
									if v3=='##':
										accu.pop()
										if v4==','and pt<st:
											accu.pop()
								accu+=va_toks
							else:
								accu[-1]=paste_tokens(t1,to_add[j+1])
							j+=1
						else:
							accu.append((p2,v2))
					elif p2==IDENT and v2 in arg_table:
						toks=args[arg_table[v2]]
						reduce_tokens(toks,defs,ban+[v])
						accu.extend(toks)
					else:
						accu.append((p2,v2))
					j+=1
				reduce_tokens(accu,defs,ban+[v])
				for x in xrange(len(accu)-1,-1,-1):
					lst.insert(i,accu[x])
		i+=1
def eval_macro(lst,adefs):
	reduce_tokens(lst,adefs,[])
	if not lst:raise PreprocError("missing tokens to evaluate")
	(p,v)=reduce_eval(lst)
	return int(v)!=0
def extract_macro(txt):
	t=tokenize(txt)
	if re_fun.search(txt):
		p,name=t[0]
		p,v=t[1]
		if p!=OP:raise PreprocError("expected open parenthesis")
		i=1
		pindex=0
		params={}
		prev='('
		while 1:
			i+=1
			p,v=t[i]
			if prev=='(':
				if p==IDENT:
					params[v]=pindex
					pindex+=1
					prev=p
				elif p==OP and v==')':
					break
				else:
					raise PreprocError("unexpected token (3)")
			elif prev==IDENT:
				if p==OP and v==',':
					prev=v
				elif p==OP and v==')':
					break
				else:
					raise PreprocError("comma or ... expected")
			elif prev==',':
				if p==IDENT:
					params[v]=pindex
					pindex+=1
					prev=p
				elif p==OP and v=='...':
					raise PreprocError("not implemented (1)")
				else:
					raise PreprocError("comma or ... expected (2)")
			elif prev=='...':
				raise PreprocError("not implemented (2)")
			else:
				raise PreprocError("unexpected else")
		return(name,[params,t[i+1:]])
	else:
		(p,v)=t[0]
		return(v,[[],t[1:]])
re_include=re.compile('^\s*(<(?P<a>.*)>|"(?P<b>.*)")')
def extract_include(txt,defs):
	m=re_include.search(txt)
	if m:
		if m.group('a'):return'<',m.group('a')
		if m.group('b'):return'"',m.group('b')
	toks=tokenize(txt)
	reduce_tokens(toks,defs,['waf_include'])
	if not toks:
		raise PreprocError("could not parse include %s"%txt)
	if len(toks)==1:
		if toks[0][0]==STR:
			return'"',toks[0][1]
	else:
		if toks[0][1]=='<'and toks[-1][1]=='>':
			return stringize(toks).lstrip('<').rstrip('>')
	raise PreprocError("could not parse include %s."%txt)
def parse_char(txt):
	if not txt:raise PreprocError("attempted to parse a null char")
	if txt[0]!='\\':
		return ord(txt)
	c=txt[1]
	if c=='x':
		if len(txt)==4 and txt[3]in string.hexdigits:return int(txt[2:],16)
		return int(txt[2:],16)
	elif c.isdigit():
		if c=='0'and len(txt)==2:return 0
		for i in 3,2,1:
			if len(txt)>i and txt[1:1+i].isdigit():
				return(1+i,int(txt[1:1+i],8))
	else:
		try:return chr_esc[c]
		except KeyError:raise PreprocError("could not parse char literal '%s'"%txt)
def tokenize(s):
	ret=[]
	for match in re_clexer.finditer(s):
		m=match.group
		for name in tok_types:
			v=m(name)
			if v:
				if name==IDENT:
					try:v=g_optrans[v];name=OP
					except KeyError:
						if v.lower()=="true":
							v=1
							name=NUM
						elif v.lower()=="false":
							v=0
							name=NUM
				elif name==NUM:
					if m('oct'):v=int(v,8)
					elif m('hex'):v=int(m('hex'),16)
					elif m('n0'):v=m('n0')
					else:
						v=m('char')
						if v:v=parse_char(v)
						else:v=m('n2')or m('n4')
				elif name==OP:
					if v=='%:':v='#'
					elif v=='%:%:':v='##'
				elif name==STR:
					v=v[1:-1]
				ret.append((name,v))
				break
	return ret
class c_parser(object):
	def __init__(self,nodepaths=None,defines=None):
		self.lines=[]
		if defines is None:
			self.defs={}
		else:
			self.defs=dict(defines)
		self.state=[]
		self.env=None
		self.count_files=0
		self.currentnode_stack=[]
		self.nodepaths=nodepaths or[]
		self.nodes=[]
		self.names=[]
		self.curfile=''
		self.ban_includes=[]
	def tryfind(self,filename):
		self.curfile=filename
		found=self.currentnode_stack[-1].find_resource(filename)
		for n in self.nodepaths:
			if found:
				break
			found=n.find_resource(filename)
		if not found:
			if not filename in self.names:
				self.names.append(filename)
		else:
			self.nodes.append(found)
			if filename[-4:]!='.moc':
				self.addlines(found)
		return found
	def addlines(self,node):
		self.currentnode_stack.append(node.parent)
		filepath=node.abspath(self.env)
		self.count_files+=1
		if self.count_files>recursion_limit:raise PreprocError("recursion limit exceeded")
		pc=self.parse_cache
		debug('preproc: reading file %r',filepath)
		try:
			lns=pc[filepath]
		except KeyError:
			pass
		else:
			self.lines=lns+self.lines
			return
		try:
			lines=filter_comments(filepath)
			lines.append((POPFILE,''))
			pc[filepath]=lines
			self.lines=lines+self.lines
		except IOError:
			raise PreprocError("could not read the file %s"%filepath)
		except Exception:
			if Logs.verbose>0:
				error("parsing %s failed"%filepath)
				traceback.print_exc()
	def start(self,node,env):
		debug('preproc: scanning %s (in %s)',node.name,node.parent.name)
		self.env=env
		variant=node.variant(env)
		bld=node.__class__.bld
		try:
			self.parse_cache=bld.parse_cache
		except AttributeError:
			bld.parse_cache={}
			self.parse_cache=bld.parse_cache
		self.addlines(node)
		if env['DEFLINES']:
			self.lines=[('define',x)for x in env['DEFLINES']]+self.lines
		while self.lines:
			(kind,line)=self.lines.pop(0)
			if kind==POPFILE:
				self.currentnode_stack.pop()
				continue
			try:
				self.process_line(kind,line)
			except Exception,e:
				if Logs.verbose:
					debug('preproc: line parsing failed (%s): %s %s',e,line,Utils.ex_stack())
	def process_line(self,token,line):
		ve=Logs.verbose
		if ve:debug('preproc: line is %s - %s state is %s',token,line,self.state)
		state=self.state
		if token in['ifdef','ifndef','if']:
			state.append(undefined)
		elif token=='endif':
			state.pop()
		if not token in['else','elif','endif']:
			if skipped in self.state or ignored in self.state:
				return
		if token=='if':
			ret=eval_macro(tokenize(line),self.defs)
			if ret:state[-1]=accepted
			else:state[-1]=ignored
		elif token=='ifdef':
			m=re_mac.search(line)
			if m and m.group(0)in self.defs:state[-1]=accepted
			else:state[-1]=ignored
		elif token=='ifndef':
			m=re_mac.search(line)
			if m and m.group(0)in self.defs:state[-1]=ignored
			else:state[-1]=accepted
		elif token=='include'or token=='import':
			(kind,inc)=extract_include(line,self.defs)
			if inc in self.ban_includes:return
			if token=='import':self.ban_includes.append(inc)
			if ve:debug('preproc: include found %s    (%s) ',inc,kind)
			if kind=='"'or not strict_quotes:
				self.tryfind(inc)
		elif token=='elif':
			if state[-1]==accepted:
				state[-1]=skipped
			elif state[-1]==ignored:
				if eval_macro(tokenize(line),self.defs):
					state[-1]=accepted
		elif token=='else':
			if state[-1]==accepted:state[-1]=skipped
			elif state[-1]==ignored:state[-1]=accepted
		elif token=='define':
			m=re_mac.search(line)
			if m:
				name=m.group(0)
				if ve:debug('preproc: define %s   %s',name,line)
				self.defs[name]=line
			else:
				raise PreprocError("invalid define line %s"%line)
		elif token=='undef':
			m=re_mac.search(line)
			if m and m.group(0)in self.defs:
				self.defs.__delitem__(m.group(0))
		elif token=='pragma':
			if re_pragma_once.search(line.lower()):
				self.ban_includes.append(self.curfile)
def get_deps(node,env,nodepaths=[]):
	gruik=c_parser(nodepaths)
	gruik.start(node,env)
	return(gruik.nodes,gruik.names)
re_inc=re.compile('^[ \t]*(#|%:)[ \t]*(include)[ \t]*(.*)\r*$',re.IGNORECASE|re.MULTILINE)
def lines_includes(filename):
	code=Utils.readf(filename)
	if use_trigraphs:
		for(a,b)in trig_def:code=code.split(a).join(b)
	code=re_nl.sub('',code)
	code=re_cpp.sub(repl,code)
	return[(m.group(2),m.group(3))for m in re.finditer(re_inc,code)]
def get_deps_simple(node,env,nodepaths=[],defines={}):
	nodes=[]
	names=[]
	def find_deps(node):
		lst=lines_includes(node.abspath(env))
		for(_,line)in lst:
			(t,filename)=extract_include(line,defines)
			if filename in names:
				continue
			if filename.endswith('.moc'):
				names.append(filename)
			found=None
			for n in nodepaths:
				if found:
					break
				found=n.find_resource(filename)
			if not found:
				if not filename in names:
					names.append(filename)
			elif not found in nodes:
				nodes.append(found)
				find_deps(node)
	find_deps(node)
	return(nodes,names)


########NEW FILE########
__FILENAME__ = python
#! /usr/bin/env python
# encoding: utf-8

import os,sys
import TaskGen,Utils,Utils,Runner,Options,Build
from Logs import debug,warn,info
from TaskGen import extension,taskgen,before,after,feature
from Configure import conf
EXT_PY=['.py']
FRAG_2='''
#include "Python.h"
#ifdef __cplusplus
extern "C" {
#endif
	void Py_Initialize(void);
	void Py_Finalize(void);
#ifdef __cplusplus
}
#endif
int main()
{
   Py_Initialize();
   Py_Finalize();
   return 0;
}
'''
def init_pyext(self):
	self.default_install_path='${PYTHONDIR}'
	self.uselib=self.to_list(getattr(self,'uselib',''))
	if not'PYEXT'in self.uselib:
		self.uselib.append('PYEXT')
	self.env['MACBUNDLE']=True
def pyext_shlib_ext(self):
	self.env['shlib_PATTERN']=self.env['pyext_PATTERN']
def init_pyembed(self):
	self.uselib=self.to_list(getattr(self,'uselib',''))
	if not'PYEMBED'in self.uselib:
		self.uselib.append('PYEMBED')
def process_py(self,node):
	if not(self.bld.is_install and self.install_path):
		return
	def inst_py(ctx):
		install_pyfile(self,node)
	self.bld.add_post_fun(inst_py)
def install_pyfile(self,node):
	path=self.bld.get_install_path(self.install_path+os.sep+node.name,self.env)
	self.bld.install_files(self.install_path,[node],self.env,self.chmod,postpone=False)
	if self.bld.is_install<0:
		info("* removing byte compiled python files")
		for x in'co':
			try:
				os.remove(path+x)
			except OSError:
				pass
	if self.bld.is_install>0:
		if self.env['PYC']or self.env['PYO']:
			info("* byte compiling %r"%path)
		if self.env['PYC']:
			program=("""
import sys, py_compile
for pyfile in sys.argv[1:]:
	py_compile.compile(pyfile, pyfile + 'c')
""")
			argv=[self.env['PYTHON'],'-c',program,path]
			ret=Utils.pproc.Popen(argv).wait()
			if ret:
				raise Utils.WafError('bytecode compilation failed %r'%path)
		if self.env['PYO']:
			program=("""
import sys, py_compile
for pyfile in sys.argv[1:]:
	py_compile.compile(pyfile, pyfile + 'o')
""")
			argv=[self.env['PYTHON'],self.env['PYFLAGS_OPT'],'-c',program,path]
			ret=Utils.pproc.Popen(argv).wait()
			if ret:
				raise Utils.WafError('bytecode compilation failed %r'%path)
class py_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_py(self):
	self.default_install_path='${PYTHONDIR}'
def _get_python_variables(python_exe,variables,imports=['import sys']):
	program=list(imports)
	program.append('')
	for v in variables:
		program.append("print(repr(%s))"%v)
	os_env=dict(os.environ)
	try:
		del os_env['MACOSX_DEPLOYMENT_TARGET']
	except KeyError:
		pass
	proc=Utils.pproc.Popen([python_exe,"-c",'\n'.join(program)],stdout=Utils.pproc.PIPE,env=os_env)
	output=proc.communicate()[0].split("\n")
	if proc.returncode:
		if Options.options.verbose:
			warn("Python program to extract python configuration variables failed:\n%s"%'\n'.join(["line %03i: %s"%(lineno+1,line)for lineno,line in enumerate(program)]))
		raise RuntimeError
	return_values=[]
	for s in output:
		s=s.strip()
		if not s:
			continue
		if s=='None':
			return_values.append(None)
		elif s[0]=="'"and s[-1]=="'":
			return_values.append(s[1:-1])
		elif s[0].isdigit():
			return_values.append(int(s))
		else:break
	return return_values
def check_python_headers(conf,mandatory=True):
	if not conf.env['CC_NAME']and not conf.env['CXX_NAME']:
		conf.fatal('load a compiler first (gcc, g++, ..)')
	if not conf.env['PYTHON_VERSION']:
		conf.check_python_version()
	env=conf.env
	python=env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')
	if Options.platform=='darwin':
		conf.check_tool('osx')
	try:
		v='prefix SO SYSLIBS LDFLAGS SHLIBS LIBDIR LIBPL INCLUDEPY Py_ENABLE_SHARED MACOSX_DEPLOYMENT_TARGET'.split()
		(python_prefix,python_SO,python_SYSLIBS,python_LDFLAGS,python_SHLIBS,python_LIBDIR,python_LIBPL,INCLUDEPY,Py_ENABLE_SHARED,python_MACOSX_DEPLOYMENT_TARGET)=_get_python_variables(python,["get_config_var('%s')"%x for x in v],['from distutils.sysconfig import get_config_var'])
	except RuntimeError:
		conf.fatal("Python development headers not found (-v for details).")
	conf.log.write("""Configuration returned from %r:
python_prefix = %r
python_SO = %r
python_SYSLIBS = %r
python_LDFLAGS = %r
python_SHLIBS = %r
python_LIBDIR = %r
python_LIBPL = %r
INCLUDEPY = %r
Py_ENABLE_SHARED = %r
MACOSX_DEPLOYMENT_TARGET = %r
"""%(python,python_prefix,python_SO,python_SYSLIBS,python_LDFLAGS,python_SHLIBS,python_LIBDIR,python_LIBPL,INCLUDEPY,Py_ENABLE_SHARED,python_MACOSX_DEPLOYMENT_TARGET))
	if python_MACOSX_DEPLOYMENT_TARGET:
		conf.env['MACOSX_DEPLOYMENT_TARGET']=python_MACOSX_DEPLOYMENT_TARGET
		conf.environ['MACOSX_DEPLOYMENT_TARGET']=python_MACOSX_DEPLOYMENT_TARGET
	env['pyext_PATTERN']='%s'+python_SO
	if python_SYSLIBS is not None:
		for lib in python_SYSLIBS.split():
			if lib.startswith('-l'):
				lib=lib[2:]
			env.append_value('LIB_PYEMBED',lib)
	if python_SHLIBS is not None:
		for lib in python_SHLIBS.split():
			if lib.startswith('-l'):
				env.append_value('LIB_PYEMBED',lib[2:])
			else:
				env.append_value('LINKFLAGS_PYEMBED',lib)
	if Options.platform!='darwin'and python_LDFLAGS:
		env.append_value('LINKFLAGS_PYEMBED',python_LDFLAGS.split())
	result=False
	name='python'+env['PYTHON_VERSION']
	if python_LIBDIR is not None:
		path=[python_LIBDIR]
		conf.log.write("\n\n# Trying LIBDIR: %r\n"%path)
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if not result and python_LIBPL is not None:
		conf.log.write("\n\n# try again with -L$python_LIBPL (some systems don't install the python library in $prefix/lib)\n")
		path=[python_LIBPL]
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if not result:
		conf.log.write("\n\n# try again with -L$prefix/libs, and pythonXY name rather than pythonX.Y (win32)\n")
		path=[os.path.join(python_prefix,"libs")]
		name='python'+env['PYTHON_VERSION'].replace('.','')
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if result:
		env['LIBPATH_PYEMBED']=path
		env.append_value('LIB_PYEMBED',name)
	else:
		conf.log.write("\n\n### LIB NOT FOUND\n")
	if(sys.platform=='win32'or sys.platform.startswith('os2')or sys.platform=='darwin'or Py_ENABLE_SHARED):
		env['LIBPATH_PYEXT']=env['LIBPATH_PYEMBED']
		env['LIB_PYEXT']=env['LIB_PYEMBED']
	python_config=conf.find_program('python%s-config'%('.'.join(env['PYTHON_VERSION'].split('.')[:2])),var='PYTHON_CONFIG')
	if not python_config:
		python_config=conf.find_program('python-config-%s'%('.'.join(env['PYTHON_VERSION'].split('.')[:2])),var='PYTHON_CONFIG')
	includes=[]
	if python_config:
		for incstr in Utils.cmd_output("%s %s --includes"%(python,python_config)).strip().split():
			if(incstr.startswith('-I')or incstr.startswith('/I')):
				incstr=incstr[2:]
			if incstr not in includes:
				includes.append(incstr)
		conf.log.write("Include path for Python extensions ""(found via python-config --includes): %r\n"%(includes,))
		env['CPPPATH_PYEXT']=includes
		env['CPPPATH_PYEMBED']=includes
	else:
		conf.log.write("Include path for Python extensions ""(found via distutils module): %r\n"%(INCLUDEPY,))
		env['CPPPATH_PYEXT']=[INCLUDEPY]
		env['CPPPATH_PYEMBED']=[INCLUDEPY]
	if env['CC_NAME']=='gcc':
		env.append_value('CCFLAGS_PYEMBED','-fno-strict-aliasing')
		env.append_value('CCFLAGS_PYEXT','-fno-strict-aliasing')
	if env['CXX_NAME']=='gcc':
		env.append_value('CXXFLAGS_PYEMBED','-fno-strict-aliasing')
		env.append_value('CXXFLAGS_PYEXT','-fno-strict-aliasing')
	conf.check(define_name='HAVE_PYTHON_H',uselib='PYEMBED',fragment=FRAG_2,errmsg='Could not find the python development headers',mandatory=mandatory)
def check_python_version(conf,minver=None):
	assert minver is None or isinstance(minver,tuple)
	python=conf.env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')
	cmd=[python,"-c","import sys\nfor x in sys.version_info: print(str(x))"]
	debug('python: Running python command %r'%cmd)
	proc=Utils.pproc.Popen(cmd,stdout=Utils.pproc.PIPE)
	lines=proc.communicate()[0].split()
	assert len(lines)==5,"found %i lines, expected 5: %r"%(len(lines),lines)
	pyver_tuple=(int(lines[0]),int(lines[1]),int(lines[2]),lines[3],int(lines[4]))
	result=(minver is None)or(pyver_tuple>=minver)
	if result:
		pyver='.'.join([str(x)for x in pyver_tuple[:2]])
		conf.env['PYTHON_VERSION']=pyver
		if'PYTHONDIR'in conf.environ:
			pydir=conf.environ['PYTHONDIR']
		else:
			if sys.platform=='win32':
				(python_LIBDEST,pydir)=_get_python_variables(python,["get_config_var('LIBDEST')","get_python_lib(standard_lib=0, prefix=%r)"%conf.env['PREFIX']],['from distutils.sysconfig import get_config_var, get_python_lib'])
			else:
				python_LIBDEST=None
				(pydir,)=_get_python_variables(python,["get_python_lib(standard_lib=0, prefix=%r)"%conf.env['PREFIX']],['from distutils.sysconfig import get_config_var, get_python_lib'])
			if python_LIBDEST is None:
				if conf.env['LIBDIR']:
					python_LIBDEST=os.path.join(conf.env['LIBDIR'],"python"+pyver)
				else:
					python_LIBDEST=os.path.join(conf.env['PREFIX'],"lib","python"+pyver)
		if hasattr(conf,'define'):
			conf.define('PYTHONDIR',pydir)
		conf.env['PYTHONDIR']=pydir
	pyver_full='.'.join(map(str,pyver_tuple[:3]))
	if minver is None:
		conf.check_message_custom('Python version','',pyver_full)
	else:
		minver_str='.'.join(map(str,minver))
		conf.check_message('Python version',">= %s"%minver_str,result,option=pyver_full)
	if not result:
		conf.fatal('The python version is too old (%r)'%pyver_full)
def check_python_module(conf,module_name):
	result=not Utils.pproc.Popen([conf.env['PYTHON'],"-c","import %s"%module_name],stderr=Utils.pproc.PIPE,stdout=Utils.pproc.PIPE).wait()
	conf.check_message('Python module',module_name,result)
	if not result:
		conf.fatal('Could not find the python module %r'%module_name)
def detect(conf):
	if not conf.env.PYTHON:
		conf.env.PYTHON=sys.executable
	python=conf.find_program('python',var='PYTHON')
	if not python:
		conf.fatal('Could not find the path of the python executable')
	v=conf.env
	v['PYCMD']='"import sys, py_compile;py_compile.compile(sys.argv[1], sys.argv[2])"'
	v['PYFLAGS']=''
	v['PYFLAGS_OPT']='-O'
	v['PYC']=getattr(Options.options,'pyc',1)
	v['PYO']=getattr(Options.options,'pyo',1)
def set_options(opt):
	opt.add_option('--nopyc',action='store_false',default=1,help='Do not install bytecode compiled .pyc files (configuration) [Default:install]',dest='pyc')
	opt.add_option('--nopyo',action='store_false',default=1,help='Do not install optimised compiled .pyo files (configuration) [Default:install]',dest='pyo')

before('apply_incpaths','apply_lib_vars','apply_type_vars')(init_pyext)
feature('pyext')(init_pyext)
before('apply_bundle')(init_pyext)
before('apply_link','apply_lib_vars','apply_type_vars')(pyext_shlib_ext)
after('apply_bundle')(pyext_shlib_ext)
feature('pyext')(pyext_shlib_ext)
before('apply_incpaths','apply_lib_vars','apply_type_vars')(init_pyembed)
feature('pyembed')(init_pyembed)
extension(EXT_PY)(process_py)
before('apply_core')(init_py)
after('vars_target_cprogram','vars_target_cshlib')(init_py)
feature('py')(init_py)
conf(check_python_headers)
conf(check_python_version)
conf(check_python_module)

########NEW FILE########
__FILENAME__ = Utils
#! /usr/bin/env python
# encoding: utf-8

import os,sys,imp,string,errno,traceback,inspect,re,shutil,datetime,gc
try:from UserDict import UserDict
except ImportError:from collections import UserDict
if sys.hexversion>=0x2060000 or os.name=='java':
	import subprocess as pproc
else:
	import pproc
import Logs
from Constants import*
try:
	from collections import deque
except ImportError:
	class deque(list):
		def popleft(self):
			return self.pop(0)
is_win32=sys.platform=='win32'
try:
	from collections import defaultdict as DefaultDict
except ImportError:
	class DefaultDict(dict):
		def __init__(self,default_factory):
			super(DefaultDict,self).__init__()
			self.default_factory=default_factory
		def __getitem__(self,key):
			try:
				return super(DefaultDict,self).__getitem__(key)
			except KeyError:
				value=self.default_factory()
				self[key]=value
				return value
class WafError(Exception):
	def __init__(self,*args):
		self.args=args
		try:
			self.stack=traceback.extract_stack()
		except:
			pass
		Exception.__init__(self,*args)
	def __str__(self):
		return str(len(self.args)==1 and self.args[0]or self.args)
class WscriptError(WafError):
	def __init__(self,message,wscript_file=None):
		if wscript_file:
			self.wscript_file=wscript_file
			self.wscript_line=None
		else:
			try:
				(self.wscript_file,self.wscript_line)=self.locate_error()
			except:
				(self.wscript_file,self.wscript_line)=(None,None)
		msg_file_line=''
		if self.wscript_file:
			msg_file_line="%s:"%self.wscript_file
			if self.wscript_line:
				msg_file_line+="%s:"%self.wscript_line
		err_message="%s error: %s"%(msg_file_line,message)
		WafError.__init__(self,err_message)
	def locate_error(self):
		stack=traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name=os.path.basename(frame[0])
			is_wscript=(file_name==WSCRIPT_FILE or file_name==WSCRIPT_BUILD_FILE)
			if is_wscript:
				return(frame[0],frame[1])
		return(None,None)
indicator=is_win32 and'\x1b[A\x1b[K%s%s%s\r'or'\x1b[K%s%s%s\r'
try:
	from fnv import new as md5
	import Constants
	Constants.SIG_NIL='signofnv'
	def h_file(filename):
		m=md5()
		try:
			m.hfile(filename)
			x=m.digest()
			if x is None:raise OSError("not a file")
			return x
		except SystemError:
			raise OSError("not a file"+filename)
except ImportError:
	try:
		try:
			from hashlib import md5
		except ImportError:
			from md5 import md5
		def h_file(filename):
			f=open(filename,'rb')
			m=md5()
			while(filename):
				filename=f.read(100000)
				m.update(filename)
			f.close()
			return m.digest()
	except ImportError:
		md5=None
class ordered_dict(UserDict):
	def __init__(self,dict=None):
		self.allkeys=[]
		UserDict.__init__(self,dict)
	def __delitem__(self,key):
		self.allkeys.remove(key)
		UserDict.__delitem__(self,key)
	def __setitem__(self,key,item):
		if key not in self.allkeys:self.allkeys.append(key)
		UserDict.__setitem__(self,key,item)
def exec_command(s,**kw):
	if'log'in kw:
		kw['stdout']=kw['stderr']=kw['log']
		del(kw['log'])
	kw['shell']=isinstance(s,str)
	try:
		proc=pproc.Popen(s,**kw)
		return proc.wait()
	except OSError:
		return-1
if is_win32:
	def exec_command(s,**kw):
		if'log'in kw:
			kw['stdout']=kw['stderr']=kw['log']
			del(kw['log'])
		kw['shell']=isinstance(s,str)
		if len(s)>2000:
			startupinfo=pproc.STARTUPINFO()
			startupinfo.dwFlags|=pproc.STARTF_USESHOWWINDOW
			kw['startupinfo']=startupinfo
		try:
			if'stdout'not in kw:
				kw['stdout']=pproc.PIPE
				kw['stderr']=pproc.PIPE
				proc=pproc.Popen(s,**kw)
				(stdout,stderr)=proc.communicate()
				Logs.info(stdout)
				if stderr:
					Logs.error(stderr)
				return proc.returncode
			else:
				proc=pproc.Popen(s,**kw)
				return proc.wait()
		except OSError:
			return-1
listdir=os.listdir
if is_win32:
	def listdir_win32(s):
		if re.match('^[A-Za-z]:$',s):
			s+=os.sep
		if not os.path.isdir(s):
			e=OSError()
			e.errno=errno.ENOENT
			raise e
		return os.listdir(s)
	listdir=listdir_win32
def waf_version(mini=0x010000,maxi=0x100000):
	ver=HEXVERSION
	try:min_val=mini+0
	except TypeError:min_val=int(mini.replace('.','0'),16)
	if min_val>ver:
		Logs.error("waf version should be at least %s (%s found)"%(mini,ver))
		sys.exit(1)
	try:max_val=maxi+0
	except TypeError:max_val=int(maxi.replace('.','0'),16)
	if max_val<ver:
		Logs.error("waf version should be at most %s (%s found)"%(maxi,ver))
		sys.exit(1)
def python_24_guard():
	if sys.hexversion<0x20400f0 or sys.hexversion>=0x3000000:
		raise ImportError("Waf requires Python >= 2.3 but the raw source requires Python 2.4, 2.5 or 2.6")
def ex_stack():
	exc_type,exc_value,tb=sys.exc_info()
	if Logs.verbose>1:
		exc_lines=traceback.format_exception(exc_type,exc_value,tb)
		return''.join(exc_lines)
	return str(exc_value)
def to_list(sth):
	if isinstance(sth,str):
		return sth.split()
	else:
		return sth
g_loaded_modules={}
g_module=None
def load_module(file_path,name=WSCRIPT_FILE):
	try:
		return g_loaded_modules[file_path]
	except KeyError:
		pass
	module=imp.new_module(name)
	try:
		code=readf(file_path,m='rU')
	except(IOError,OSError):
		raise WscriptError('Could not read the file %r'%file_path)
	module.waf_hash_val=code
	dt=os.path.dirname(file_path)
	sys.path.insert(0,dt)
	try:
		exec(compile(code,file_path,'exec'),module.__dict__)
	except Exception:
		exc_type,exc_value,tb=sys.exc_info()
		raise WscriptError("".join(traceback.format_exception(exc_type,exc_value,tb)),file_path)
	sys.path.remove(dt)
	g_loaded_modules[file_path]=module
	return module
def set_main_module(file_path):
	global g_module
	g_module=load_module(file_path,'wscript_main')
	g_module.root_path=file_path
	try:
		g_module.APPNAME
	except:
		g_module.APPNAME='noname'
	try:
		g_module.VERSION
	except:
		g_module.VERSION='1.0'
def to_hashtable(s):
	tbl={}
	lst=s.split('\n')
	for line in lst:
		if not line:continue
		mems=line.split('=')
		tbl[mems[0]]=mems[1]
	return tbl
def get_term_cols():
	return 80
try:
	import struct,fcntl,termios
except ImportError:
	pass
else:
	if Logs.got_tty:
		def myfun():
			dummy_lines,cols=struct.unpack("HHHH",fcntl.ioctl(sys.stderr.fileno(),termios.TIOCGWINSZ,struct.pack("HHHH",0,0,0,0)))[:2]
			return cols
		try:
			myfun()
		except:
			pass
		else:
			get_term_cols=myfun
rot_idx=0
rot_chr=['\\','|','/','-']
def split_path(path):
	return path.split('/')
def split_path_cygwin(path):
	if path.startswith('//'):
		ret=path.split('/')[2:]
		ret[0]='/'+ret[0]
		return ret
	return path.split('/')
re_sp=re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret=re.split(re_sp,path)[2:]
		ret[0]='\\'+ret[0]
		return ret
	return re.split(re_sp,path)
if sys.platform=='cygwin':
	split_path=split_path_cygwin
elif is_win32:
	split_path=split_path_win32
def copy_attrs(orig,dest,names,only_if_set=False):
	for a in to_list(names):
		u=getattr(orig,a,())
		if u or not only_if_set:
			setattr(dest,a,u)
def def_attrs(cls,**kw):
	'''
	set attributes for class.
	@param cls [any class]: the class to update the given attributes in.
	@param kw [dictionary]: dictionary of attributes names and values.

	if the given class hasn't one (or more) of these attributes, add the attribute with its value to the class.
	'''
	for k,v in kw.iteritems():
		if not hasattr(cls,k):
			setattr(cls,k,v)
def quote_define_name(path):
	fu=re.compile("[^a-zA-Z0-9]").sub("_",path)
	fu=fu.upper()
	return fu
def quote_whitespace(path):
	return(path.strip().find(' ')>0 and'"%s"'%path or path).replace('""','"')
def trimquotes(s):
	if not s:return''
	s=s.rstrip()
	if s[0]=="'"and s[-1]=="'":return s[1:-1]
	return s
def h_list(lst):
	m=md5()
	m.update(str(lst))
	return m.digest()
def h_fun(fun):
	try:
		return fun.code
	except AttributeError:
		try:
			h=inspect.getsource(fun)
		except IOError:
			h="nocode"
		try:
			fun.code=h
		except AttributeError:
			pass
		return h
def pprint(col,str,label='',sep=os.linesep):
	sys.stderr.write("%s%s%s %s%s"%(Logs.colors(col),str,Logs.colors.NORMAL,label,sep))
def check_dir(dir):
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError,e:
			raise WafError("Cannot create folder '%s' (original error: %s)"%(dir,e))
def cmd_output(cmd,**kw):
	silent=False
	if'silent'in kw:
		silent=kw['silent']
		del(kw['silent'])
	if'e'in kw:
		tmp=kw['e']
		del(kw['e'])
		kw['env']=tmp
	kw['shell']=isinstance(cmd,str)
	kw['stdout']=pproc.PIPE
	if silent:
		kw['stderr']=pproc.PIPE
	try:
		p=pproc.Popen(cmd,**kw)
		output=p.communicate()[0]
	except OSError,e:
		raise ValueError(str(e))
	if p.returncode:
		if not silent:
			msg="command execution failed: %s -> %r"%(cmd,str(output))
			raise ValueError(msg)
		output=''
	return output
reg_subst=re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr,params):
	def repl_var(m):
		if m.group(1):
			return'\\'
		if m.group(2):
			return'$'
		try:
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var,expr)
def unversioned_sys_platform_to_binary_format(unversioned_sys_platform):
	if unversioned_sys_platform in('linux','freebsd','netbsd','openbsd','sunos','gnu'):
		return'elf'
	elif unversioned_sys_platform=='darwin':
		return'mac-o'
	elif unversioned_sys_platform in('win32','cygwin','uwin','msys'):
		return'pe'
	return'elf'
def unversioned_sys_platform():
	s=sys.platform
	if s=='java':
		from java.lang import System
		s=System.getProperty('os.name')
		if s=='Mac OS X':
			return'darwin'
		elif s.startswith('Windows '):
			return'win32'
		elif s=='OS/2':
			return'os2'
		elif s=='HP-UX':
			return'hpux'
		elif s in('SunOS','Solaris'):
			return'sunos'
		else:s=s.lower()
	if s=='win32'or s.endswith('os2')and s!='sunos2':return s
	return re.split('\d+$',s)[0]
def detect_platform():
	s=sys.platform
	for x in'cygwin linux irix sunos hpux aix darwin gnu'.split():
		if s.find(x)>=0:
			return x
	if os.name in'posix java os2'.split():
		return os.name
	return s
def load_tool(tool,tooldir=None):
	'''
	load_tool: import a Python module, optionally using several directories.
	@param tool [string]: name of tool to import.
	@param tooldir [list]: directories to look for the tool.
	@return: the loaded module.

	Warning: this function is not thread-safe: plays with sys.path,
					 so must run in sequence.
	'''
	if tooldir:
		assert isinstance(tooldir,list)
		sys.path=tooldir+sys.path
	else:
		tooldir=[]
	try:
		return __import__(tool)
	finally:
		for dt in tooldir:
			sys.path.remove(dt)
def readf(fname,m='r'):
	f=open(fname,m)
	try:
		txt=f.read()
	finally:
		f.close()
	return txt
def nada(*k,**kw):
	pass
def diff_path(top,subdir):
	top=os.path.normpath(top).replace('\\','/').split('/')
	subdir=os.path.normpath(subdir).replace('\\','/').split('/')
	if len(top)==len(subdir):return''
	diff=subdir[len(top)-len(subdir):]
	return os.path.join(*diff)
class Context(object):
	def set_curdir(self,dir):
		self.curdir_=dir
	def get_curdir(self):
		try:
			return self.curdir_
		except AttributeError:
			self.curdir_=os.getcwd()
			return self.get_curdir()
	curdir=property(get_curdir,set_curdir)
	def recurse(self,dirs,name=''):
		if not name:
			name=inspect.stack()[1][3]
		if isinstance(dirs,str):
			dirs=to_list(dirs)
		for x in dirs:
			if os.path.isabs(x):
				nexdir=x
			else:
				nexdir=os.path.join(self.curdir,x)
			base=os.path.join(nexdir,WSCRIPT_FILE)
			file_path=base+'_'+name
			try:
				txt=readf(file_path,m='rU')
			except(OSError,IOError):
				try:
					module=load_module(base)
				except OSError:
					raise WscriptError('No such script %s'%base)
				try:
					f=module.__dict__[name]
				except KeyError:
					raise WscriptError('No function %s defined in %s'%(name,base))
				if getattr(self.__class__,'pre_recurse',None):
					self.pre_recurse(f,base,nexdir)
				old=self.curdir
				self.curdir=nexdir
				try:
					f(self)
				finally:
					self.curdir=old
				if getattr(self.__class__,'post_recurse',None):
					self.post_recurse(module,base,nexdir)
			else:
				dc={'ctx':self}
				if getattr(self.__class__,'pre_recurse',None):
					dc=self.pre_recurse(txt,file_path,nexdir)
				old=self.curdir
				self.curdir=nexdir
				try:
					try:
						exec(compile(txt,file_path,'exec'),dc)
					except Exception:
						exc_type,exc_value,tb=sys.exc_info()
						raise WscriptError("".join(traceback.format_exception(exc_type,exc_value,tb)),base)
				finally:
					self.curdir=old
				if getattr(self.__class__,'post_recurse',None):
					self.post_recurse(txt,file_path,nexdir)
if is_win32:
	old=shutil.copy2
	def copy2(src,dst):
		old(src,dst)
		shutil.copystat(src,src)
	setattr(shutil,'copy2',copy2)
def zip_folder(dir,zip_file_name,prefix):
	import zipfile
	zip=zipfile.ZipFile(zip_file_name,'w',compression=zipfile.ZIP_DEFLATED)
	base=os.path.abspath(dir)
	if prefix:
		if prefix[-1]!=os.sep:
			prefix+=os.sep
	n=len(base)
	for root,dirs,files in os.walk(base):
		for f in files:
			archive_name=prefix+root[n:]+os.sep+f
			zip.write(root+os.sep+f,archive_name,zipfile.ZIP_DEFLATED)
	zip.close()
def get_elapsed_time(start):
	delta=datetime.datetime.now()-start
	days=int(delta.days)
	hours=int(delta.seconds/3600)
	minutes=int((delta.seconds-hours*3600)/60)
	seconds=delta.seconds-hours*3600-minutes*60+float(delta.microseconds)/1000/1000
	result=''
	if days:
		result+='%dd'%days
	if days or hours:
		result+='%dh'%hours
	if days or hours or minutes:
		result+='%dm'%minutes
	return'%s%.3fs'%(result,seconds)
if os.name=='java':
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable=gc.enable


########NEW FILE########
