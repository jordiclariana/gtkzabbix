#   GTK dashboard for Zabbix server.
#   Copyright (C) 2011  Jordi Clariana jordiclariana(at)gmail(dot)com
#   This file is part of GTKZabbix.
#
#   GTKZabbix is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   GTKZabbix is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with GTKZabbix.  If not, see <http://www.gnu.org/licenses/>.

# System modules
try:
    import sys
    import os
    import datetime
    import threading
    import time
    import subprocess
    import shlex
except Exception as e:
    print ("Error loading system modules: {0}".format(e))
    sys.exit(1)

# GTK modules
try:
    import gtk
    import gobject
    import pango
except Exception as e:
    print ("Error loading GTK modules: {0}".format(e))
    sys.exit(1)

try:
    import appindicator
    loaded_indicator = True
except ImportError, ex:
    loaded_indicator = False
except Exception as e:
    print ("Error loading GTK modules: {0}".format(e))
    sys.exit(1)

# Audio modules
try:
    import gst
except Exception as e:
    print ("Error loading audio modules: {0}".format(e))
    sys.exit(1)

# Custom modules
try:
    from libs.configuration import configuration
    from libs.zabbix_api import ZabbixAPI, ZabbixAPIException
    from libs.zabbix import zbx_connections, zbx_priorities, zbx_connections, resource_path
    from settingsWindow import settingsWindow
    #import notify
except Exception as e:
    print ("Error loading custom modules: {0}".format(e))
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

XSET='/usr/bin/xset'

LISTZABBIX = {
    'triggerid': 0,
    'hostid': 1,
    'lastchange': 2,
    'priority': 3,
    'host': 4,
    'description': 5,
    'vlastchange': 6,
    'vpriority': 7,
    'priobackgroundcolor': 8,
    'prioforegroundcolor': 9,
    'ack': 10,
    'vzalias': 11,
    'fontsize': 12
}

class GTKZabbix:

    def __init__(self):
        self.conf_main = configuration()

        filename = resource_path("resources/glade/main.glade").get()
        self.builder = gtk.Builder()
        self.builder.add_from_file(filename)

        self.window = self.builder.get_object("mainWindow")
        self.list_zabbix_model = self.builder.get_object("treeZabbix")
        self.list_zabbix_store = self.builder.get_object("listZabbix")
        self.list_zabbix_store_ack = self.builder.get_object("crt_ack")
        self.lbl_lastupdated_num = self.builder.get_object("lbl_lastupdated_num")

        self.window.set_icon_from_file(zbx_priorities().get_icon())

        self.events_dic = {
           'on_mainWindow_delete_event': self.hide,
           'on_sb_fontsize_value_changed': self.change_fontsize,
           'on_sc_fontsize_value_changed': self.change_fontsize,
           'on_mainWindow_key_press_event': self.keypress,
        }

        self.builder.connect_signals(self.events_dic)

        self.list_zabbix_store_ack.connect('toggled', self.ack_toggled_callback, self.list_zabbix_store)

        self.menu_setup()

        if loaded_indicator:
            # The indicator!
            self.ind = appindicator.Indicator("GTKZabbix",
                                              "GTKZabbix Indicator",
                                               appindicator.CATEGORY_APPLICATION_STATUS)
            self.ind.set_status(appindicator.STATUS_ACTIVE)
            self.ind.set_icon(zbx_priorities().get_icon())
            self.ind.set_menu(self.menu)
        else:
            self.tray = gtk.StatusIcon()
            self.tray.set_from_file(zbx_priorities().get_icon())
            self.tray.set_visible(True)
            self.tray.connect('popup-menu', self.tray_right_click_event)
            self.tray.connect('activate', self.tray_left_click_event)
            self.tray.set_tooltip('GTKZabbix')

        # GST Player instance
        self.gstPlayer = gst.element_factory_make("playbin2", "player")
        self.gstPlayer_bus = self.gstPlayer.get_bus()
        self.gstPlayer_bus.add_signal_watch()
        self.gstPlayer_bus.connect("message", self.gstplayer_on_message)

        self.list_zabbix_store.clear()

        self.isFullscreen = False
        self.isControlRoomMode = False

        self.update_dashboard_thread = threading.Thread(target=self.update_dashboard)
        self.update_dashboard_thread.setDaemon(True)
        self.update_dashboard_thread.start()

        self.appind_blink_thread = threading.Thread(target=self.appind_blink)
        self.appind_blink_thread.setDaemon(True)
        self.appind_blink_thread.start()

        self.priocolumn_blink_thread = threading.Thread(target=self.priocolumn_blink)
        self.priocolumn_blink_thread.setDaemon(True)
        self.priocolumn_blink_thread.start()
        #gobject.timeout_add(30000, self.update_dashboard)
        #gobject.timeout_add(750, self.appind_blink)
        #gobject.timeout_add(750, self.priocolumn_blink)

        self.window.maximize()
        if self.conf_main.get_setting('showdashboardinit'):
            self.conf_main.close()
            del self.conf_main
            self.show_item.set_active(True)

    def keypress(self, widget, event = None):
        if event.keyval == gtk.keysyms.F11:
            if self.isFullscreen:
                self.window.unfullscreen()
                self.isFullscreen = False
            else:
                self.window.fullscreen()
                self.isFullscreen = True

    def change_fontsize(self, widget, data = None):
        column_labels = [ 'lbl_tv_ack',
                          'lbl_tv_priority',
                          'lbl_tv_zalias',
                          'lbl_tv_host',
                          'lbl_tv_description',
                          'lbl_tv_lastchange',
                          'lbl_lastupdated' ]

        adj_fontsize = self.builder.get_object("adj_fontsize")
        for col_label in column_labels:
            column_label_object = self.builder.get_object(col_label)
            column_label_object.modify_font(pango.FontDescription(str(adj_fontsize.get_value())))
        self.lbl_lastupdated_num.modify_font(pango.FontDescription(str(adj_fontsize.get_value())))

        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            self.list_zabbix_store.set_value(iter, LISTZABBIX['fontsize'], int(adj_fontsize.get_value())*1000)
            iter = self.list_zabbix_store.iter_next(iter)

    def append_zbx_trigger(self, trigger, alias):
        adj_fontsize = self.builder.get_object("adj_fontsize")
        self.list_zabbix_store.append([
            int(trigger.get('triggerid')),
            int(trigger.get('hostid')),
            int(trigger.get('lastchange')),
            int(trigger.get('priority')),
            trigger.get('host'),
            trigger.get('description'),
            datetime.datetime.fromtimestamp(int(trigger.get('lastchange'))).strftime('%Y-%m-%d %H:%M:%S'),
            zbx_priorities(trigger.get('priority')).get_text(),
            zbx_priorities(trigger.get('priority')).get_color(0),
            zbx_priorities(trigger.get('priority')).get_color(1),
            0,
            alias,
            int(adj_fontsize.get_value())*1000]
        )

        # libNotify
        #if ((time.time() - int(trigger.get('lastchange'))) < 300):
        #    notify.notify(trigger.get('priority'), alias + ": " + trigger.get('host'), trigger.get('description'), 10)

        print ("Add {0} - {1} - {2}".format(trigger.get('triggerid'),
            trigger.get('host'), trigger.get('description')))


    def add_zbx_triggers(self, triggers):
        # Get current triggers to compare with new ones in order to know if
        # they have to be added or if in the other hand they already are in the list
        iter = self.list_zabbix_store.get_iter_first()

        if not iter and len(triggers)>0: # List is empty, adding all items
            for trigger in triggers:
                self.append_zbx_trigger(trigger[1], trigger[0])
        else:
            for trigger in triggers:
                found = False
                while iter:
                    if self.list_zabbix_store.get_value(iter, LISTZABBIX['triggerid']) == int(trigger[1].get('triggerid')) and \
                        self.list_zabbix_store.get_value(iter, LISTZABBIX['vzalias']) == trigger[0]:
                        # Item already exist on the list
                        found = True
                        if self.list_zabbix_store.get_value(iter, LISTZABBIX['lastchange']) < int(trigger[1].get('lastchange')):
                            # Update lastchange of this trigger
                            self.list_zabbix_store.set_value(iter, LISTZABBIX['lastchange'], int(trigger[1].get('lastchange')))
                        iter = self.list_zabbix_store.get_iter_first()
                        break
                    iter = self.list_zabbix_store.iter_next(iter)

                if not found:
                        # No item found, add it
                        self.crm_change_display(True)
                        self.append_zbx_trigger(trigger[1], trigger[0])
                        # Start over again
                        iter = self.list_zabbix_store.get_iter_first()

    def del_zbx_triggers(self, triggers):
        # Cleanup
        deleted = False
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            delete_flag = True
            for trigger in triggers:
                if int(self.list_zabbix_store.get_value(iter, LISTZABBIX['triggerid'])) == int(trigger[1].get('triggerid')) and \
                 self.list_zabbix_store.get_value(iter, LISTZABBIX['vzalias']) == trigger[0]:
                    delete_flag = False
            if delete_flag:
                print ("Delete {0} - {1} - {2}".format(self.list_zabbix_store.get_value(iter, LISTZABBIX['triggerid']),
                      self.list_zabbix_store.get_value(iter, LISTZABBIX['host']), self.list_zabbix_store.get_value(iter, LISTZABBIX['description'])))
                deleted = True
                self.list_zabbix_store.remove(iter)
                # Better get first iter again than keep on with current altered index
                iter = self.list_zabbix_store.get_iter_first()
            else:
                iter = self.list_zabbix_store.iter_next(iter)
        return deleted

    def get_maxprio_zbx_triggers(self):
        max_prio = -1
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            cur_prio = int(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority']))
            cur_isack = int(self.list_zabbix_store.get_value(iter, LISTZABBIX['ack']))
            if cur_prio > max_prio and cur_isack == 0:
                max_prio = cur_prio
            iter = self.list_zabbix_store.iter_next(iter)
        return max_prio

    def get_play_alarm_priority(self):
        max_prio = -1
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            cur_prio = int(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority']))
            cur_isack = bool(self.list_zabbix_store.get_value(iter, LISTZABBIX['ack']))
            cur_timestamps = int(self.list_zabbix_store.get_value(iter, LISTZABBIX['lastchange']))
            diff_time = (time.time() - cur_timestamps)
            if diff_time <= self.conf_threaded.get_setting('playsoundiftriggerlastchange') and cur_prio > max_prio \
                and cur_isack == False and cur_prio >= self.conf_threaded.get_setting('playifprio'):
                max_prio = cur_prio
            iter = self.list_zabbix_store.iter_next(iter)
        return max_prio

    def auto_ack(self, seconds):
        if seconds == 0:
            return

        cur_time = time.time()
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            if (cur_time - self.list_zabbix_store.get_value(iter, LISTZABBIX['lastchange'])) > seconds:
                self.list_zabbix_store.set_value(iter, LISTZABBIX['ack'], 1)
            iter = self.list_zabbix_store.iter_next(iter)

    def get_zbx_triggers(self):
        triggers = []
        self.zbxConnections.recheck()
        for zAPIAlias, zAPIConn in self.zbxConnections.connections():
            triggers_list = []
            try:
                for trigger in zAPIConn.trigger.get(
                    {'active' : True,
                     'monitored': True,
                     'sortfield': 'lastchange',
                     'filter': {'value': 1},
                     'withUnacknowledgedEvents': True,
                     'skipDependent': False}):

                    triggers_list.append(trigger.get('triggerid'))

                this_trigger = zAPIConn.trigger.get(
                    {'triggerids': triggers_list,
                     'expandDescription': True,
                     'output': 'extend',
                     'expandData': True}
                )

                if type(this_trigger) is dict:
                    for triggerid in this_trigger.keys():
                        triggers.append([ zAPIAlias, this_trigger[triggerid] ])
                elif type(this_trigger) is list:
                    for trigger in this_trigger:
                        triggers.append([ zAPIAlias, trigger ])
                else:
                    print ("Error parsing triggers. Not dict and not list. Is: {0}".format(type(this_trigger)))

            except Exception as e:
                print ("GTKZabbix | Unexpected error getting triggers from {0}:\n\t{1}".format(zAPIAlias, e))

        return triggers

    def update_dashboard(self, once = False):
        self.conf_threaded = configuration()
        self.zbxConnections = zbx_connections(self.conf_threaded)
        self.zbxConnections.init()
        first = True
        no_triggers_timestamp = None
        while True:
            print ("{0} | Updating dashboard".format(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')))
            triggers = self.get_zbx_triggers()
            # Set threads_enter because we are going to change widgets properties on the wild using several threads.
            gtk.gdk.threads_enter()
            try:
                self.add_zbx_triggers(triggers)
            except Exception as e:
                print ("GTKZabbixNotify | Exception adding triggers:\n\t{0}".format(e))
            if first:
                first = False
                self.list_zabbix_store.set_sort_column_id(2, gtk.SORT_DESCENDING)
                if self.conf_threaded.get_setting('ackalloninit'):
                    try:
                        self.ackall(None)
                    except Exception as e:
                        print ("GTKZabbixNotify | Exception ACKing triggers:\n\t{0}".format(e))
            try:
                deleted = self.del_zbx_triggers(triggers)
            except Exception as e:
                print ("GTKZabbixNotify | Exception deleting triggers:\n\t{0}".format(e))

            self.auto_ack(self.conf_threaded.get_setting('ackafterseconds'))
            max_prio = self.get_play_alarm_priority()
            self.lbl_lastupdated_num.set_text(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            # Leaving dangerous section
            gtk.gdk.threads_leave()

            # Play sound if we have delete triggers (and if is it set to do so)
            if deleted and self.conf_threaded.get_setting('sounddelete'):
                self.play_sound(-1)
                if max_prio >= 0:
                    time.sleep(0.75)

            # Play Sound
            if max_prio >= 0:
                self.play_sound(max_prio)

            # Control Room Mode
            if len(triggers) == 0 and self.isControlRoomMode:
                if not no_triggers_timestamp:
                    no_triggers_timestamp = time.time()
                if time.time() > (no_triggers_timestamp + 300):
                    self.crm_change_display(False)
            elif no_triggers_timestamp:
                no_triggers_timestamp = None
                self.crm_change_display(True)

            if once:
                break
            # self.notify.notify(4, "Server Name", "Trigger description")
            time.sleep(self.conf_threaded.get_setting('checkinterval'))
        self.conf_threaded.close()

    def menu_setup(self):
        self.menu = gtk.Menu()

        self.show_item = gtk.CheckMenuItem("Show Dashboard")
        self.show_item.connect("toggled", self.show)
        self.show_item.show()
        self.crm_item = gtk.CheckMenuItem("Control Room Mode")
        self.crm_item.connect("activate", self.control_room_mode)
        self.crm_item.show()
        self.settings_item = gtk.MenuItem("Settings")
        self.settings_item.connect("activate", self.settings_window)
        self.settings_item.show()
        self.ackall_item = gtk.MenuItem("ACK all")
        self.ackall_item.connect("activate", self.ackall)
        self.ackall_item.show()
        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.show_item)
        self.menu.append(self.crm_item)
        self.menu.append(self.settings_item)
        self.menu.append(self.ackall_item)
        self.menu.append(self.quit_item)

    def tray_right_click_event(self, icon, button, time):
        self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.tray)

    def tray_left_click_event(self, data):
        self.show_item.set_active(not self.show_item.get_active())

    def control_room_mode(self, widget, data = None):
        self.isControlRoomMode = not self.isControlRoomMode

    def ackall(self, widget, data = None):
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            self.list_zabbix_store.set_value(iter, LISTZABBIX['ack'], 1)
            iter = self.list_zabbix_store.iter_next(iter)

    def ack_toggled_callback(self, cell, path, model=None):
        iter = model.get_iter(path)
        model.set_value(iter, LISTZABBIX['ack'], not cell.get_active())

    def show(self, widget, data=None):
        if not self.show_item.get_active():
            self.window.hide()
        else:
            self.window.present()
        return True
        
    def hide(self, widget, data=None):
        self.show_item.set_active(False)
        return True

    def quit(self, widget, data=None):
        print ("Quit!")
        gtk.main_quit()

    def appind_blink(self):
        while True:
            counter = 0
            gtk.gdk.threads_enter()
            if not hasattr(self, 'blinkFlag'):
                self.blinkFlag = True

            iter = self.list_zabbix_store.get_iter_first()
            while iter:
                counter = 0
                if self.list_zabbix_store.get_value(iter, LISTZABBIX['ack']) == 0:
                    if self.blinkFlag:
                        if loaded_indicator:
                            self.ind.set_icon(zbx_priorities(self.get_maxprio_zbx_triggers()).get_icon())
                        else:
                            self.tray.set_from_file(zbx_priorities(self.get_maxprio_zbx_triggers()).get_icon())
                        self.window.set_icon_from_file(zbx_priorities(self.get_maxprio_zbx_triggers()).get_icon())
                    else:
                        if loaded_indicator:
                            self.ind.set_icon(zbx_priorities().get_empty_icon())
                        else:
                            self.tray.set_from_file(zbx_priorities().get_empty_icon())
                        self.window.set_icon_from_file(zbx_priorities().get_empty_icon())
                    counter = counter + 1
                    break
                iter=self.list_zabbix_store.iter_next(iter)
            if counter == 0:
                if loaded_indicator:
                    if self.ind.get_icon() != zbx_priorities().get_icon():
                        self.ind.set_icon(zbx_priorities().get_icon())
                        self.window.set_icon_from_file(zbx_priorities().get_icon())
                else:
                    self.tray.set_from_file(zbx_priorities().get_icon())
                    self.window.set_icon_from_file(zbx_priorities().get_icon())

            gtk.gdk.threads_leave()
            time.sleep(0.75)

    def priocolumn_blink(self):
        while True:
            gtk.gdk.threads_enter()
            if not hasattr(self, 'blinkFlag'):
                self.blinkFlag = True

            iter = self.list_zabbix_store.get_iter_first()
            while iter:
                if self.list_zabbix_store.get_value(iter, LISTZABBIX['ack']) == 1: # Is ACKed?
                    if self.list_zabbix_store.get_value(iter, LISTZABBIX['priobackgroundcolor']) == zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_not_color(0):
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['priobackgroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_color(0))
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['prioforegroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_color(1))
                else: # If not blink
                    if self.blinkFlag:
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['priobackgroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_color(0))
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['prioforegroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_color(1))
                    else:
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['priobackgroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_not_color(0))
                        self.list_zabbix_store.set_value(iter, LISTZABBIX['prioforegroundcolor'],
                             zbx_priorities(self.list_zabbix_store.get_value(iter, LISTZABBIX['priority'])).get_not_color(1))

                iter=self.list_zabbix_store.iter_next(iter)
            gtk.gdk.threads_leave()
            self.blinkFlag = not self.blinkFlag
            time.sleep(0.75)

    def play_sound(self, priority):
        if self.conf_threaded.get_setting('soundenable'):
            uri = 'file://' + zbx_priorities(priority).get_sound()
            self.gstPlayer.set_property('uri', uri)
            self.gstPlayer.set_state(gst.STATE_PLAYING)

    def gstplayer_on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.gstPlayer.set_state(gst.STATE_NULL)
        if t == gst.MESSAGE_ERROR:
            self.gstPlayer.set_state(gst.STATE_NULL)

    def settings_window(self, widget, data=None):
        settingsWindow()

    def crm_change_display(self, on_off):
        if on_off:
            self.cmd_execute(XSET + " dpms force on")
            self.cmd_execute(XSET + " s reset")
        else:
            self.cmd_execute(XSET + " dpms force off")

    def cmd_execute(self, command):
        cmd = shlex.split(command, posix = False)
        try:
            p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            preturn = p.wait()
            stdout = ''
            tmp_stdout = p.stdout.readline()
            while tmp_stdout:
                stdout = stdout + tmp_stdout.decode('UTF-8')
                tmp_stdout = p.stdout.readline()
            return [stdout, preturn]
        except Exception as e:
            print ("Exception on execution:\n{0}".format(e))
            return False



if __name__ == '__main__':
    gtk.gdk.threads_init()
    app = GTKZabbix()
    gtk.main()
