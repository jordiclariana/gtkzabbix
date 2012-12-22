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

import os, sys

try:
    import confthread
except Exception as e:
    print("Error loading confthread module")
    sys.exit(1)
# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

class configuration(confthread.confthread):

    OLDCONFIG = os.path.expanduser('~') + "/.GTKZabbixNotify.sqlite"
    NEWCONFIG = os.path.expanduser('~') + "/.GTKZabbix.sqlite"
    SERVERS_COLUMNS = { 'alias': 0, 'uri': 1, 'username': 2, 'password': 3, 'enabled': 4, 'server_type': 5 }
    SERVERS_TYPE = [ "Zabbix Server", "GTKZabbix" ]
    SERVERS = []

    def __init__(self, conf_in_q, conf_out_q):
        # Little config file migration :P
        if os.path.isfile(self.OLDCONFIG) and not os.path.isfile(self.NEWCONFIG):
            os.rename(self.OLDCONFIG, self.NEWCONFIG)
            print("Config file migrated from {0} to {1}".format(self.OLDCONFIG, self.NEWCONFIG))

        # Set config file
        self.defaultDBFile = self.NEWCONFIG

        # inherit confthread class
        super(configuration, self).__init__(conf_in_q, conf_out_q)

    # confthread methods wrappers
    def set_server(self, alias, uri, username, password, enabled, server_type):
        self.conf_in_q.put(["__set_server__", {"alias": alias, "uri": uri, "username": username, "password": password, "enabled": enabled, "server_type": server_type }])
        return self.conf_out_q.get()

    def mod_server(self, alias, uri, username, password, enabled, server_type):
        self.conf_in_q.put(["__mod_server__", {"alias": alias, "uri": uri, "username": username, "password": password, "enabled": enabled, "server_type": server_type }])
        return self.conf_out_q.get()

    def del_server(self, alias):
        self.conf_in_q.put(["__del_server__", {"alias": alias }])
        return self.conf_out_q.get()

    def get_servers(self, alias = None, enabled = None):
        self.conf_in_q.put(["__get_servers__", { "alias": alias, "enabled": enabled }])
        return self.conf_out_q.get()

    def fetch_servers(self):
        self.conf_in_q.put(["__fetch_servers__", { "None": None } ])
        return self.conf_out_q.get()
    
    def get_total_servers(self, enabled = None):
        self.conf_in_q.put(["__get_total_servers__", { "enabled": enabled } ])
        return self.conf_out_q.get()

    def get_setting(self, name):
        self.conf_in_q.put(["__get_setting__", {"name": name }])
        return self.conf_out_q.get()

    def set_setting(self, name, value):
        self.conf_in_q.put(["__set_setting__", {"name": name, "value": value}])
        return self.conf_out_q.get()

    # This is no wrapper, no need to
    def get_server(self, id, column):
        if id in range(0, len(self.SERVERS)):
            return self.SERVERS[id][column]
        else:
            return False
