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

# GTK modules
try:
    import gtk
except Exception as e:
    print "Error loading GTK modules: {0}".format(e)
    sys.exit(1)

# Custom modules
try:
    from libs.configuration import configuration
    from libs.zabbix import zbx_priorities
    from libs.resource_path import resource_path
except Exception as e:
    print "Error loading custom modules: {0}".format(e)
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print "Error loading debugging modules: {0}".format(e)
    sys.exit(1)

class settingsWindow:
    
    __SETTINGS_LIST = [ "checkinterval", "soundenable", "ackalloninit", "playsoundiftriggerlastchange", 
                       "showdashboardinit", "playifprio", "ackafterseconds", "sounddelete" ]
    
    def __init__(self):
        filename = resource_path("resources/glade/settings.glade").get()
        self.settingsBuilder = gtk.Builder()
        self.settingsBuilder.add_from_file(filename)
        
        self.settingsWindow = self.settingsBuilder.get_object("settingsWindow")
        self.servers_liststore = self.settingsBuilder.get_object("ls_servers")
        self.txt_serveralias = self.settingsBuilder.get_object("txt_serveralias")
        self.txt_serveruri = self.settingsBuilder.get_object("txt_serveruri")
        self.txt_serverusername = self.settingsBuilder.get_object("txt_serverusername")
        self.txt_serverpassword = self.settingsBuilder.get_object("txt_serverpassword")
        self.cb_serverenabled = self.settingsBuilder.get_object("cb_serverenabled")
        self.bt_editserver = self.settingsBuilder.get_object("bt_editserver")
        self.bt_addserver = self.settingsBuilder.get_object("bt_addserver")
        self.bt_delserver = self.settingsBuilder.get_object("bt_delserver")
        self.tv_servers = self.settingsBuilder.get_object("tv_servers")
        self.ls_priorities_sound = self.settingsBuilder.get_object("ls_priorities_sound")
        self.ls_priorities_notify = self.settingsBuilder.get_object("ls_priorities_notify")
        self.cb_enablenotify = self.settingsBuilder.get_object("cb_enablenotify")
        self.box_notify = self.settingsBuilder.get_object("box_notify")
        self.serversWindow = self.settingsBuilder.get_object("serversWindow")
        
        self.settings_object_list = {}
        for setting in self.__SETTINGS_LIST:
            self.settings_object_list[setting] = self.settingsBuilder.get_object(setting)
            
        self.events_dic = {
           'on_bt_save_clicked': self.save,
           'on_bt_Cancel_clicked': self.cancel,
           'on_tv_servers_button_press_event': self.server_clicked,
           'on_txt_serveralias_changed': self.server_field_changed,
           'on_txt_serveruri_changed': self.server_field_changed,
           'on_txt_serverusername_changed': self.server_field_changed,
           'on_txt_serverpassword_changed': self.server_field_changed,
           'on_cb_serverenabled_toggled': self.server_field_changed,
           'on_bt_delserver_clicked': self.server_delete,
           'on_bt_addserver_clicked': self.server_add,
           'on_cb_enablenotify_toggled': self.enablenotify_changes,
           'on_bt_editserver_clicked': self.server_edit,
           'on_bt_servers_save_clicked': self.servers_save,
           'on_bt_servers_cancel_clicked': self.servers_cancel,
        }

        self.settingsBuilder.connect_signals(self.events_dic)
        
        self.conf = configuration()
        
        self.fill_settings_objects()
        self.fill_servers_list()
        self.settingsWindow.set_icon_from_file(zbx_priorities().get_icon())
        self.settingsWindow.show()

    def fill_settings_objects(self):
        for setting in self.__SETTINGS_LIST:
            value = self.conf.get_setting(setting)
            if value != None:
                setting_obj = self.settings_object_list[setting]
                try:
                    if isinstance(setting_obj, gtk.Entry):
                        setting_obj.set_text(value)
                    elif isinstance(setting_obj, gtk.CheckButton):
                        setting_obj.set_active(value)
                    elif isinstance(setting_obj, gtk.Adjustment):
                        setting_obj.set_value(value)
                    elif isinstance(setting_obj, gtk.ComboBox):
                        if setting == 'playifprio':
                            list = self.ls_priorities_sound

                        iter = list.get_iter_first()
                        while iter:
                            if list.get_value(iter, 0) == value:
                                setting_obj.set_active_iter(iter)
                                break
                            iter = list.iter_next(iter)
                        
                except Exception as e:
                    print "Exception {0}".format(e)
    
    def fill_servers_list(self):
        self.servers_liststore.clear()
        servers = self.conf.get_servers()
        for server in servers:
            self.servers_liststore.append([server['alias'], server['uri'], server['username'], server['enabled']])
        
    def save(self, widget, data = None):
        for setting in self.__SETTINGS_LIST:
            setting_obj = self.settings_object_list[setting]
            if isinstance(setting_obj, gtk.Entry):
                value = setting_obj.get_text()
            elif isinstance(setting_obj, gtk.CheckButton):
                value = setting_obj.get_active()
            elif isinstance(setting_obj, gtk.Adjustment):
                value = setting_obj.get_value()
            elif isinstance(setting_obj, gtk.ComboBox):
                if setting == 'playifprio':
                    list = self.ls_priorities_sound
                
                iter = setting_obj.get_active_iter()
                value = list.get_value(iter, 0)
            try:
                self.conf.set_setting(setting, value)
            except Exception as e:
                print "Exception: ", e
                print "Setting object: ".format(type(setting_obj))

        self.settingsWindow.destroy()

    def cancel(self, widget, data = None):
        self.settingsWindow.destroy()

    def server_field_changed(self, widget, data = None):
        widget.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFF00"))
    
    def servers_save(self, widget, data = None):
        self.conf.set_server(self.txt_serveralias.get_text() , self.txt_serveruri.get_text(),
                             self.txt_serverusername.get_text(), self.txt_serverpassword.get_text(),
                             self.cb_serverenabled.get_active())
        self.txt_serveralias.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serverpassword.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serveruri.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serverusername.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.cb_serverenabled.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.fill_servers_list()
        self.serversWindow.hide()

    def servers_cancel(self, widget, data = None):
        self.serversWindow.hide()

    def server_edit(self, widget, data = None):
        myselection = self.tv_servers.get_selection()
        model, selection = myselection.get_selected()
        if isinstance(selection, gtk.TreeIter):
            selectedServer = self.conf.get_servers(
                       self.servers_liststore.get_value(selection,0))[0]
            self.txt_serveralias.set_text(selectedServer['alias'])
            self.txt_serveralias.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
            self.txt_serverpassword.set_text(self.conf.get_password(selectedServer['password']))
            self.txt_serverpassword.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
            self.txt_serveruri.set_text(selectedServer['uri'])
            self.txt_serveruri.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
            self.txt_serverusername.set_text(selectedServer['username'])
            self.txt_serverusername.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
            self.cb_serverenabled.set_active(selectedServer['enabled'])
            self.cb_serverenabled.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
            self.serversWindow.show()
    
    def server_delete(self, widget, data = None):
        myselection = self.tv_servers.get_selection()
        model, selection = myselection.get_selected()
        if isinstance(selection, gtk.TreeIter):
            self.conf.del_server(self.servers_liststore.get_value(selection,0))
            self.fill_servers_list()
    
    def server_add(self, widget, data = None):
        self.txt_serveralias.set_text("")
        self.txt_serveralias.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serverpassword.set_text("")
        self.txt_serverpassword.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serveruri.set_text("")
        self.txt_serveruri.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.txt_serverusername.set_text("")
        self.txt_serverusername.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.cb_serverenabled.set_active(False)
        self.cb_serverenabled.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.serversWindow.show()

    def enablenotify_changes(self, widget, data = None):
        self.box_notify.set_sensitive(widget.get_active())
        
    def server_clicked(self, widget, event = None):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = self.tv_servers.get_path_at_pos(x, y)
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            self.tv_servers.grab_focus()
            self.tv_servers.set_cursor( path, col, 0)

        myselection = widget.get_selection()
        model, selection = myselection.get_selected()
        if isinstance(selection, gtk.TreeIter):
            self.bt_editserver.set_sensitive(True)
            self.bt_addserver.set_sensitive(True)
            self.bt_delserver.set_sensitive(True)
        else:
            self.bt_editserver.set_sensitive(False)
            self.bt_addserver.set_sensitive(True)
            self.bt_delserver.set_sensitive(False)

        # if event.button == 3:
        #     m = gtk.Menu()
        #     i = gtk.MenuItem("Hello")
        #     i.show()
        #     m.append(i)
        #     m.popup( None, None, None, event.button, time)

        return True
         
# Multiple selections:
#        self.tv_servers.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

#        model, selections = myselection.get_selected_rows()
#        for selection in selections:
#            iter = self.servers_liststore.get_iter(selection[0])

