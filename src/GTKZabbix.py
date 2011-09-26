'''
Created on 25/07/2011

@author: Jordi Clariana
'''
import sys, os
import gtk, gobject
import zbx_connections
import appindicator
from zabbix_api import ZabbixAPI, ZabbixAPIException
from pprint import pprint
import datetime
import gst
import threading
import time
import configuration
from zbx_priorities import zbx_priorities
from resource_path import resource_path
from zbx_connections import zbx_connections
import notify
import settingsWindow
import tooltip

class GTKZabbix:
    
    def __init__(self):
        self.conf_main = configuration.configuration()
        
        filename = resource_path("glade/main.glade").get()
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
           'on_treeZabbix_button_press_event': self.treeZabbix_click,
           'on_sb_fontsize_value_changed': self.change_fontsize,
           'on_mainWindow_key_press_event': self.keypress,
        }

        self.builder.connect_signals(self.events_dic)

        self.list_zabbix_store_ack.connect('toggled', self.ack_toggled_callback, self.list_zabbix_store)
        
        # The indicator!
        self.ind = appindicator.Indicator("Zabbix Notify",
                                          "Zabbix Notify",
                                           appindicator.CATEGORY_APPLICATION_STATUS)
        self.ind.set_status(appindicator.STATUS_ACTIVE)
        self.ind.set_icon(zbx_priorities().get_icon())
        self.menu_setup()
        self.ind.set_menu(self.menu)
        
        # GST Player instance
        self.gstPlayer = gst.element_factory_make("playbin2", "player")
        self.gstPlayer_bus = self.gstPlayer.get_bus()
        self.gstPlayer_bus.add_signal_watch()
        self.gstPlayer_bus.connect("message", self.gstplayer_on_message)
        
        self.list_zabbix_store.clear()

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

        #self.window.fullscreen()
        self.isFullscreen = False
        
        self.tooltipWindow = tooltip.tooltip()
        
        self.window.maximize()
        if self.conf_main.get_setting('showdashboardinit'):
            self.conf_main.close()
            del self.conf_main
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
        adj_fontsize = self.builder.get_object("adj_fontsize")
        
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            self.list_zabbix_store.set_value(iter, 12, int(adj_fontsize.get_value())*1000)
            iter = self.list_zabbix_store.iter_next(iter)

    def treeZabbix_click(self, widget, event):
        if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            myselection = widget.get_selection()
            model, selection = myselection.get_selected()
            if isinstance(selection, gtk.TreeIter):
                rootwin = widget.get_screen().get_root_window()
                x, y, mods = rootwin.get_pointer()
                self.tooltipWindow.show(x, y, '<b>{0}</b>: <i>{1}</i>'.format(model.get_value(selection, 4), model.get_value(selection, 5)))
                
            else:
                pprint(selection)
            return True
        elif event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self.tooltipWindow.hide()
            return False

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
        if ((time.time() - int(trigger.get('lastchange'))) < 300):
            notify.notify(trigger.get('priority'), alias + ": " + trigger.get('host'), trigger.get('description'), 10)

        print "Add {0} - {1} - {2}".format(trigger.get('triggerid'),
            trigger.get('host'), trigger.get('description'))
        
    def add_zbx_triggers(self, triggers):
        iter = self.list_zabbix_store.get_iter_first()
        current_triggers = {}
        while iter:
            current_triggers[self.list_zabbix_store.get_value(iter, 0)] = \
                [ self.list_zabbix_store.get_value(iter, 2), self.list_zabbix_store.get_value(iter, 11)]
            iter = self.list_zabbix_store.iter_next(iter)
        
        # Insert
        for trigger in triggers:
            if current_triggers.has_key(int(trigger[1].get('triggerid'))) and \
                current_triggers[int(trigger[1].get('triggerid'))][1] == trigger[0]:
                    if current_triggers[int(trigger[1].get('triggerid'))][0] < int(trigger[1].get('lastchange')):
                        self.append_zbx_trigger(trigger[1], trigger[0])
            else: # Empty ListStore
                self.append_zbx_trigger(trigger[1], trigger[0])
    
    def del_zbx_triggers(self, triggers):
        # Cleanup
        deleted = False
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            delete_flag = True
            for trigger in triggers:
                if int(self.list_zabbix_store.get_value(iter, 0)) == int(trigger[1].get('triggerid')) and \
                 self.list_zabbix_store.get_value(iter, 11) == trigger[0]:
                    delete_flag = False
            if delete_flag:
                print "Delete {0} - {1} - {2}".format(self.list_zabbix_store.get_value(iter, 0),
                      self.list_zabbix_store.get_value(iter, 4), self.list_zabbix_store.get_value(iter, 5))
                deleted = True
                self.list_zabbix_store.remove(iter)
                iter = self.list_zabbix_store.get_iter_first()
            else:
                iter = self.list_zabbix_store.iter_next(iter)
        return deleted
    
    def get_maxprio_zbx_triggers(self):
        max_prio = -1
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            cur_prio = int(self.list_zabbix_store.get_value(iter, 3))
            cur_isack = int(self.list_zabbix_store.get_value(iter, 10))
            if cur_prio > max_prio and cur_isack == 0:
                max_prio = cur_prio
            iter = self.list_zabbix_store.iter_next(iter)
        return max_prio
    
    def get_play_alarm_priority(self):
        max_prio = -1
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            cur_prio = int(self.list_zabbix_store.get_value(iter, 3))
            cur_isack = bool(self.list_zabbix_store.get_value(iter, 10))
            cur_timestamps = int(self.list_zabbix_store.get_value(iter, 2))
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
            if (cur_time - self.list_zabbix_store.get_value(iter, 2)) > seconds:
                self.list_zabbix_store.set_value(iter, 10, 1)
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
                     'withUnacknowledgedEvents': True}
                    ):
                    
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
                    print "Error parsing triggers. Not dict and not list. Is: {0}".format(type(this_trigger))

            except Exception as e:
                print "GTKZabbix | Unexpected error getting triggers from {0}:\n\t{1}".format(zAPIAlias, e)
             
        return triggers
    
    def update_dashboard(self, once = False):
        self.conf_threaded = configuration.configuration()
        self.zbxConnections = zbx_connections(self.conf_threaded)
        self.zbxConnections.init()
        first = True
        while True:
            print "{0} | Updating dashboard".format(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            triggers = self.get_zbx_triggers()
            gtk.gdk.threads_enter()
            try:
                self.add_zbx_triggers(triggers)
            except Exception as e:
                print "GTKZabbixNotify | Exception adding triggers:\n\t{0}".format(e)
            if first:
                first = False
                self.list_zabbix_store.set_sort_column_id(2, gtk.SORT_DESCENDING)
                if self.conf_threaded.get_setting('ackalloninit'):
                    try:
                        self.ackall(None)
                    except Exception as e:
                        print "GTKZabbixNotify | Exception ACKing triggers:\n\t{0}".format(e)
            try:
                deleted = self.del_zbx_triggers(triggers)
            except Exception as e:
                print "GTKZabbixNotify | Exception deleting triggers:\n\t{0}".format(e)
            self.auto_ack(self.conf_threaded.get_setting('ackafterseconds'))
            max_prio = self.get_play_alarm_priority()
            self.lbl_lastupdated_num.set_text(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            gtk.gdk.threads_leave()
            
            if deleted and self.conf_threaded.get_setting('sounddelete'):
                self.play_sound(-1)
                if max_prio >= 0:
                    time.sleep(0.75)
            if max_prio >= 0:
                self.play_sound(max_prio)
            
            if once:
                break
            # self.notify.notify(4, "Server Name", "Trigger description")
            time.sleep(self.conf_threaded.get_setting('checkinterval'))
        self.conf_threaded.close()
        
    def menu_setup(self):
        self.menu = gtk.Menu()

        self.show_item = gtk.MenuItem("Show Dashboard")
        self.show_item.connect("activate", self.show)
        self.show_item.show()
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
        self.menu.append(self.settings_item)
        self.menu.append(self.ackall_item)
        self.menu.append(self.quit_item)
    
    def ackall(self, widget, data = None):
        iter = self.list_zabbix_store.get_iter_first()
        while iter:
            self.list_zabbix_store.set_value(iter, 10, 1)
            iter = self.list_zabbix_store.iter_next(iter)
        
    def ack_toggled_callback(self, cell, path, model=None):
        iter = model.get_iter(path)
        model.set_value(iter, 10, not cell.get_active())        
    
    def show(self, widget, data=None):
        self.window.present()
        return True
    
    def hide(self, widget, data=None):
        self.tooltipWindow.hide()
        self.window.hide()
        return True
            
    def quit(self, widget, data=None):
        print "Quit!"
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
                if self.list_zabbix_store.get_value(iter, 10) == 0:
                    if self.blinkFlag:
                        self.ind.set_icon(zbx_priorities(self.get_maxprio_zbx_triggers()).get_icon())
                        self.window.set_icon_from_file(zbx_priorities(self.get_maxprio_zbx_triggers()).get_icon())
                    else:
                        self.ind.set_icon(zbx_priorities().get_empty_icon())
                        self.window.set_icon_from_file(zbx_priorities().get_empty_icon())
                    counter = counter + 1
                    break
                iter=self.list_zabbix_store.iter_next(iter)
            if counter == 0:
                if self.ind.get_icon() != zbx_priorities().get_icon() :
                    self.ind.set_icon(zbx_priorities().get_icon())
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
                if self.list_zabbix_store.get_value(iter, 10) == 1: # Is ACKed?
                    if self.list_zabbix_store.get_value(iter, 8) == zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_not_color(0):
                        self.list_zabbix_store.set_value(iter, 8, 
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_color(0))
                        self.list_zabbix_store.set_value(iter, 9,
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_color(1))
                else: # If not blink
                    if self.blinkFlag:
                        self.list_zabbix_store.set_value(iter, 8, 
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_color(0))
                        self.list_zabbix_store.set_value(iter, 9,
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_color(1))
                    else:
                        self.list_zabbix_store.set_value(iter, 8, 
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_not_color(0))
                        self.list_zabbix_store.set_value(iter, 9,
                             zbx_priorities(self.list_zabbix_store.get_value(iter, 3)).get_not_color(1))
    
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
        settingsWindow.settingsWindow()
        
if __name__ == '__main__':
    gtk.gdk.threads_init()
    app = GTKZabbix()
    gtk.main()
