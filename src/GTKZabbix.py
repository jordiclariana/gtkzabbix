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
    import logging
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

# Misc modules
try:
    from apscheduler.scheduler import Scheduler
except Exception as e:
    print ("Error loading misc modules: {0}".format(e))
    print ("Try to install them using 'pip'")
    sys.exit(1)

# Custom modules
try:
    from libs.configuration import configuration
    from libs.zabbix_api import ZabbixAPI, ZabbixAPIException
    from libs.zabbix import zbx_priorities, resource_path, zbx_triggers
    from libs.views import zbx_listview, zbx_groupview
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

logging.basicConfig(filename='/tmp/GTKZabbix.log',level=logging.WARNING)

class GTKZabbix:

    def __init__(self):

        self.conf = configuration()

        self.first = True

        filename = resource_path("resources/glade/main.glade").get()
        self.builder = gtk.Builder()
        self.builder.add_from_file(filename)

        self.window = self.builder.get_object("mainWindow")

        self.list_zabbix_model = self.builder.get_object("treeZabbix")
        self.list_zabbix_store = zbx_listview(self.list_zabbix_model)
        self.list_zabbix_model.set_model(self.list_zabbix_store)

        self.group_zabbix_model = self.builder.get_object("treeZabbixGroup")
        self.group_zabbix_store = zbx_groupview(self.group_zabbix_model)
        self.group_zabbix_model.set_model(self.group_zabbix_store)

        self.list_zabbix_store_ack = self.builder.get_object("crt_ack")
        self.lbl_lastupdated_num = self.builder.get_object("lbl_lastupdated_num")

        self.window.set_icon_from_file(zbx_priorities().get_icon())

        self.events_dic = {
           'on_mainWindow_delete_event': self.hide,
           'on_sb_fontsize_value_changed': self.change_fontsize,
           'on_sc_fontsize_value_changed': self.change_fontsize,
           'on_mainWindow_key_press_event': self.keypress,
           'on_treeZabbixGroup_button_press_event': self.on_click,
           'on_treeZabbix_button_press_event': self.on_click,
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

        self.triggers = zbx_triggers(self.conf)

        self.sched = Scheduler({'daemonic': False})
        self.sched.start()

        self.sched.add_interval_job(self.update_dashboard,
            seconds = int(self.conf.get_setting('checkinterval')),
            start_date = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M'),
            args = [self.conf])

        self.sched.add_interval_job(self.appind_blink, seconds = 1)

        self.sched.add_interval_job(self.priocolumn_blink, seconds = 1)

        self.isFullscreen = False
        self.isControlRoomMode = False

        if self.conf.get_setting('showdashboardinit'):
            self.conf.close()
            del self.conf
            self.window.present()

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
                          'lbl_lastupdated',
                          'lbl_hostgroup',
                          'lbl_disaster',
                          'lbl_high',
                          'lbl_average',
                          'lbl_warning',
                          'lbl_information',
                          'lbl_notclassified' ]

        adj_fontsize = self.builder.get_object("adj_fontsize")
        for col_label in column_labels:
            column_label_object = self.builder.get_object(col_label)
            column_label_object.modify_font(pango.FontDescription(str(adj_fontsize.get_value())))
        self.lbl_lastupdated_num.modify_font(pango.FontDescription(str(adj_fontsize.get_value())))

        self.list_zabbix_store.change_fontsize(int(adj_fontsize.get_value())*1000)
        self.group_zabbix_store.change_fontsize(int(adj_fontsize.get_value())*1000)

    def update_dashboard(self, conf, once = False):
        self.conf = conf
        no_triggers_timestamp = None

        print ("{0} | Updating dashboard".format(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')))
        
        self.triggers.fetch()
        # Set threads_enter because we are going to change widgets properties on the wild using several threads.
        gtk.gdk.threads_enter()

        try:
            if self.triggers.count() > 0:
                self.group_zabbix_store.add_triggers(self.triggers)
                self.list_zabbix_store.add_triggers(self.triggers)
                self.crm_change_display(True)
        except Exception as e:
            print ("GTKZabbixNotify | Exception adding triggers:\n\t{0}".format(e))

        if self.first:
            self.first = False
            self.group_zabbix_model.expand_all()
            self.list_zabbix_store.set_sort_column_id(2, gtk.SORT_DESCENDING)
            if self.conf.get_setting('ackalloninit'):
                try:
                    self.ackall(None)
                except Exception as e:
                    print ("GTKZabbixNotify | Exception ACKing triggers:\n\t{0}".format(e))
        try:
            deleted = self.list_zabbix_store.del_triggers(self.triggers)
        except Exception as e:
            print ("GTKZabbixNotify | Exception deleting triggers:\n\t{0}".format(e))

        
        self.list_zabbix_store.auto_ack(self.conf.get_setting('ackafterseconds'))

        max_prio = self.list_zabbix_store.get_play_alarm_priority(
            self.conf.get_setting('playsoundiftriggerlastchange'),
            self.conf.get_setting('playifprio'))

        self.lbl_lastupdated_num.set_text(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
        # Leaving dangerous section
        gtk.gdk.threads_leave()

        if self.conf.get_setting('soundenable'):
            # Play sound if we have delete triggers (and if is it set to do so)
            if deleted and self.conf.get_setting('sounddelete'):
                self.play_sound(-1)
                if max_prio >= 0:
                    time.sleep(0.75)

            # Play Sound
            if max_prio >= 0:
                self.play_sound(max_prio)

        # Control Room Mode
        if self.triggers.count() == 0 and self.isControlRoomMode:
            if not no_triggers_timestamp:
                no_triggers_timestamp = time.time()
            if time.time() > (no_triggers_timestamp + 300):
                self.crm_change_display(False)
        elif no_triggers_timestamp:
            no_triggers_timestamp = None
            self.crm_change_display(True)

        self.conf.close()

    def menu_setup(self):
        self.menu = gtk.Menu()

        self.show_item = gtk.MenuItem("Show Dashboard")
        self.show_item.connect("activate", self.show)
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
        self.menu.popup(None, None, gtk.status_icon_position_menu, 1, gtk.get_current_event_time(), self.tray)

    def control_room_mode(self, widget, data = None):
        self.isControlRoomMode = not self.isControlRoomMode

    def ackall(self, widget, data = None):
        self.list_zabbix_store.ackall()

    def ack_toggled_callback(self, cell, path, model=None):
        iter = model.get_iter(path)
        model.set_value(iter, LISTZABBIX['ack'], not cell.get_active())

    def show(self, widget, data=None):
        self.window.present()
        return True

    def hide(self, widget, data=None):
        self.window.hide()
        return True

    def quit(self, widget, data=None):
        print ("Quit!")
        self.sched.shutdown(wait=False)
        gtk.main_quit()

    def appind_blink(self):
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
                        self.ind.set_icon(
                            zbx_priorities(
                                self.list_zabbix_store.get_max_priority()
                            ).get_icon()
                        )
                    else:
                        self.tray.set_icon_from_file(
                            zbx_priorities(
                                self.list_zabbix_store.get_max_priority()
                            ).get_icon()
                        )
                else:
                    if loaded_indicator:
                        self.ind.set_icon(zbx_priorities().get_empty_icon())
                    else:
                        self.tray.set_icon_from_file(zbx_priorities().get_empty_icon())
                    self.window.set_icon_from_file(zbx_priorities().get_empty_icon())
                counter = counter + 1
                break
            iter=self.list_zabbix_store.iter_next(iter)
        if counter == 0:
            if loaded_indicator:
                if self.ind.get_icon() != zbx_priorities().get_icon() :
                    self.ind.set_icon(zbx_priorities().get_icon())
                    self.window.set_icon_from_file(zbx_priorities().get_icon())
            else:
                if self.tray.get_icon_name() != zbx_priorities().get_icon() :
                    self.tray.set_icon_from_file(zbx_priorities().get_icon())
                    self.window.set_icon_from_file(zbx_priorities().get_icon())
        gtk.gdk.threads_leave()

    def priocolumn_blink(self):
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

    def play_sound(self, priority):
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

    def on_click(self, widget, event):
        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            myselection = widget.get_selection()
            model, selection = myselection.get_selected()
            if isinstance(selection, gtk.TreeIter):
                # If click is not over a row, unselect everyrow.
                x, y, mods = widget.get_bin_window().get_pointer()
                if not widget.get_path_at_pos(x, y):
                    myselection.unselect_all()
    
        return False

if __name__ == '__main__':
    gtk.gdk.threads_init()
    app = GTKZabbix()
    try:
        gtk.main()
    except KeyboardInterrupt:
        print ("")

