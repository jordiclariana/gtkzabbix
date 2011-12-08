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
    import time
    import datetime
except Exception as e:
    print ("Error loading system modules: {0}".format(e))
    sys.exit(1)

# GTK modules
try:
    import gtk, gobject
except Exception as e:
    print ("Error loading GTK modules: {0}".format(e))
    sys.exit(1)

# Custom modules
try:
    from zabbix import zbx_priorities
except Exception as e:
    print ("Error loading custom modules: {0}".format(e))
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

class zbx_fontsize:        
    __fontsize = 10000 # 10 * 1000

    def set_fontsize(self, value):
        self.__fontsize=value
    
    def get_fontsize(self):
        return self.__fontsize

    def change_fontsize(self, value = None):
        if value:
            self.set_fontsize(value)

        iter = self.get_iter_first()
        while iter:
            self.set_value(iter, self.LISTCOLUMNS['fontsize'], self.get_fontsize())
            if self.iter_has_child(iter):
                child_iter = self.iter_children(iter)
                while child_iter:
                    self.set_value(child_iter, self.LISTCOLUMNS['fontsize'], self.get_fontsize())
                    child_iter = self.iter_next(child_iter)
                    
            iter = self.iter_next(iter)

class zbx_listview(gtk.ListStore, zbx_fontsize):

    LISTCOLUMNS = {
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
     
    def __init__(self, model):
        super( zbx_listview, self ).__init__(
            gobject.TYPE_UINT,      # triggerid
            gobject.TYPE_UINT,      # hostid
            gobject.TYPE_UINT,      # lastchange
            gobject.TYPE_UINT,      # priority
            gobject.TYPE_STRING,    # host
            gobject.TYPE_STRING,    # description
            gobject.TYPE_STRING,    # vlastchange
            gobject.TYPE_STRING,    # vpriority
            gobject.TYPE_STRING,    # priobackgroundcolor
            gobject.TYPE_STRING,    # prioforegroundcolor
            gobject.TYPE_UINT,      # ACK
            gobject.TYPE_STRING,    # vzalias
            gobject.TYPE_UINT       # fontsize
        )
        
        self.model = model

    def auto_ack(self, seconds):
        if seconds == 0:
            return

        cur_time = time.time()
        iter = self.get_iter_first()
        while iter:
            if (cur_time - self.get_value(iter, self.LISTCOLUMNS['lastchange'])) > seconds:
                self.set_value(iter, self.LISTCOLUMNS['ack'], 1)
            iter = self.iter_next(iter)

    def ackall(self):
        iter = self.get_iter_first()
        while iter:
            self.set_value(iter, self.LISTCOLUMNS['ack'], 1)
            iter = self.iter_next(iter)

    def append_trigger(self, trigger):
        self.append([
            trigger.get_id(),
            trigger.get_hostid(),
            trigger.get_lastchange(),
            trigger.get_priority(),
            trigger.get_host(),
            trigger.get_description(),
            datetime.datetime.fromtimestamp(
                    trigger.get_lastchange()
                ).strftime('%Y-%m-%d %H:%M:%S'),
            zbx_priorities(trigger.get_priority()).get_text(),
            zbx_priorities(trigger.get_priority()).get_color(0),
            zbx_priorities(trigger.get_priority()).get_color(1),
            0,
            trigger.get_serveralias(),
            self.get_fontsize()]
        )

        # libNotify
        #if ((time.time() - int(trigger.get('lastchange'))) < 300):
        #    notify.notify(trigger.get('priority'), alias + ": " + trigger.get('host'), trigger.get('description'), 10)

        print ("Add {0} - {1} - {2}".format(trigger.get_id(),
            trigger.get_host(), trigger.get_description()))

    def add_triggers(self, triggers, fontsize = None):
        if fontsize:
            self.set_fontsize(fontsize)

        # Get current triggers to compare with new ones in order to know if
        # they have to be added or if in the other hand they already are in the list
        iter = self.get_iter_first()
        if not iter and triggers.count() > 0: # List is empty, adding all items
            for trigger in triggers.get_triggers():
                self.append_trigger(trigger)
        elif triggers.count() > 0:
            for trigger in triggers.get_triggers():
                found = False
                while iter:
                    if self.get_value(iter, self.LISTCOLUMNS['triggerid']) == trigger.get_id() and \
                        self.get_value(iter, self.LISTCOLUMNS['vzalias']) == trigger.get_serveralias():
                        # Item already exist on the list
                        found = True
                        if self.get_value(iter, self.LISTCOLUMNS['lastchange']) < int(trigger.get_lastchange()):
                            # Update lastchange of this trigger
                            self.set_value(iter, self.LISTCOLUMNS['lastchange'], int(trigger.get_lastchange()))
                        iter = self.get_iter_first()
                        break
                    iter = self.iter_next(iter)

    def del_triggers(self, triggers):
        # Cleanup
        deleted = False
        iter = self.get_iter_first()
        while iter:
            delete_flag = True
            for trigger in triggers.get_triggers():
                if self.get_value(iter, self.LISTCOLUMNS['triggerid']) == trigger.get_id() and \
                 self.get_value(iter, self.LISTCOLUMNS['vzalias']) == trigger.get_serveralias():
                    delete_flag = False
            if delete_flag:
                print ("Delete {0} - {1} - {2}".format(self.get_value(iter, self.LISTCOLUMNS['triggerid']),
                      self.get_value(iter, self.LISTCOLUMNS['host']), self.get_value(iter, self.LISTCOLUMNS['description'])))
                deleted = True
                self.remove(iter)
                # Better get first iter again than keep on with current altered index
                iter = self.get_iter_first()
            else:
                iter = self.iter_next(iter)
        return deleted

    def get_max_priority(self):
        max_prio = -1
        iter = self.get_iter_first()
        while iter:
            cur_prio = int(self.get_value(iter, self.LISTCOLUMNS['priority']))
            cur_isack = int(self.get_value(iter, self.LISTCOLUMNS['ack']))
            if cur_prio > max_prio and cur_isack == 0:
                max_prio = cur_prio
            iter = self.iter_next(iter)
        return max_prio

    def get_play_alarm_priority(self, maxtime, minprio):
        max_prio = -1
        iter = self.get_iter_first()
        while iter:
            cur_prio = int(self.get_value(iter, self.LISTCOLUMNS['priority']))
            cur_isack = bool(self.get_value(iter, self.LISTCOLUMNS['ack']))
            cur_timestamps = int(self.get_value(iter, self.LISTCOLUMNS['lastchange']))
            diff_time = (time.time() - cur_timestamps)
            if diff_time <= maxtime and cur_prio > max_prio \
                and cur_isack == False and cur_prio >= minprio:
                max_prio = cur_prio
            iter = self.iter_next(iter)
        return max_prio


class zbx_groupview(gtk.TreeStore, zbx_fontsize):

    LISTCOLUMNS = {
    'hostgroup': 0,
    'notclassified': 1,
    'information': 2,
    'warning': 3,
    'average': 4,
    'high': 5,
    'disaster': 6,
    'fontsize': 7
    }

    COLUMNS = {
    'notclassified': 6,
    'information': 5,
    'warning': 4,
    'average': 3,
    'high': 2,
    'disaster': 1
    }

    def __init__(self, model):
        super( zbx_groupview, self ).__init__(
            gobject.TYPE_STRING,    # hostgroup
            gobject.TYPE_UINT,      # notclassified
            gobject.TYPE_UINT,      # information
            gobject.TYPE_UINT,      # warning
            gobject.TYPE_UINT,      # average
            gobject.TYPE_UINT,      # high
            gobject.TYPE_UINT,      # disaster
            gobject.TYPE_UINT       # fontsize
        )

        self.model = model
        for column_name, column_num in self.LISTCOLUMNS.iteritems():
            if column_num in range(self.COLUMNS['disaster'], self.COLUMNS['notclassified'] + 1):
                column = self.model.get_column(self.COLUMNS[column_name])
                column_cells = column.get_cell_renderers()
                for column_cell in column_cells:
                    column.set_cell_data_func(column_cell, self.set_cell_color, column_name)

    def set_cell_color(self, column, cell_renderer, model, iter, column_name):
        if model.get_value(iter, self.LISTCOLUMNS[column_name]) == 0:  
            cell_renderer.set_property("background", zbx_priorities(0).get_color(0))
            cell_renderer.set_property("foreground", zbx_priorities(0).get_color(1))
        else:
            cell_renderer.set_property("background", zbx_priorities(self.LISTCOLUMNS[column_name]-1).get_color(0))
            cell_renderer.set_property("foreground", zbx_priorities(self.LISTCOLUMNS[column_name]-1).get_color(1))

    def add_triggers(self, triggers, fontsize = None):
        if fontsize:
            self.set_fontsize(fontsize)
        
        self.current_triggers = triggers

        groups_data = {}
        serveraliases_data = {}

        # Collect data and create rows if necessary
        for trigger in self.current_triggers.get_triggers():
            for group in trigger.get_group():
                group_row = self.search(group)
                if not group_row:
                    group_row = self.append(None, [group, 0, 0, 0, 0, 0, 0, self.get_fontsize()])

                if not group in groups_data.keys():
                    groups_data[group] = [0, 0, 0, 0, 0, 0]

                groups_data[group][trigger.get_priority()] =+ 1

                serveralias_row = self.search(group, trigger.get_serveralias())
                if not serveralias_row:
                    serveralias_row = self.append(group_row, [trigger.get_serveralias(), 0, 0, 0, 0, 0, 0, self.get_fontsize()])

                if not trigger.get_serveralias() in serveraliases_data.keys():
                    serveraliases_data[trigger.get_serveralias()] = [0, 0, 0, 0, 0, 0]
                
                serveraliases_data[trigger.get_serveralias()][trigger.get_priority()] =+ 1

        # Set collected data to the rows
        for group, group_data in groups_data.iteritems():
            group_row = self.search(group)
            if group_row:
                for prio in range(0, len(group_data)):
                    self.set_value(group_row, self.LISTCOLUMNS[zbx_priorities(prio).get_key()], group_data[prio])

                for serveralias, serveralias_data in serveraliases_data.iteritems():
                    serveralias_row = self.search(group, serveralias)
                    if serveralias_row:
                        for prio in range(0, len(serveralias_data)):
                            self.set_value(serveralias_row, self.LISTCOLUMNS[zbx_priorities(prio).get_key()], serveralias_data[prio])

    def search(self, group, serveralias = None):
        iter = self.get_iter_root()
        while iter:
            if group == self.get_value(iter, self.LISTCOLUMNS['hostgroup']):
                if serveralias:
                    if self.iter_has_child(iter):
                        child_iter = self.iter_children(iter)
                        while child_iter:
                            if serveralias == self.get_value(child_iter, self.LISTCOLUMNS['hostgroup']):
                                return child_iter
                            child_iter = self.iter_next(child_iter)
                    return False
                else:
                    return iter
            iter = self.iter_next(iter)
        return False