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
    import os, sys
    import stat
    import threading
    import Queue
except Exception as e:
    print ("Error loading system modules: {0}".format(e))
    sys.exit(1)

# Misc modules
try:
    import sqlite3
    import base64
except Exception as e:
    print ("Error loading misc modules: {0}".format(e))
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

class configuration(threading.Thread):

    __SERVERS_COLUMNS={'alias': 0, 'uri': 1, 'username': 2, 'password': 3, 'enabled': 4}
    __SERVERS = []

    def __init__(self, conf_in_q, conf_out_q):
        super(configuration, self).__init__()
        self.conf_in_q = conf_in_q
        self.conf_out_q = conf_out_q
        self.stoprequest = threading.Event()
        self.lock = threading.Lock()
        self.defaultDBFile = os.path.expanduser('~') + "/.GTKZabbixNotify.sqlite"

    def run(self):
        self.db_init()
        while not self.stoprequest.isSet():
            try:
                self.lock.acquire()
                precmd = self.conf_in_q.get(True, 0.05)
                cmd = getattr(self, precmd[0])
                self.conf_out_q.put(cmd(None, **precmd[1]))
                self.persistent_db.commit()
            except Queue.Empty:
                continue
            except Exception as e:
                print("Configuration command queue exception:\n{0}".format(str(e)))
                pprint(precmd)
                self.conf_out_q.put(False)
            finally:
                self.lock.release()

        self.persistent_db.commit()
        self.persistent_db_cursor.close()
        self.persistent_db.close()

    def db_init(self):
        self.persistent_db = sqlite3.connect(self.defaultDBFile)
        self.persistent_db_cursor = self.persistent_db.cursor()

        try:
            self.persistent_db_cursor.execute("SELECT * FROM servers")
            self.persistent_db_cursor.execute("SELECT * FROM settings")
        except:
            self.persistent_db_cursor.executescript("""
            CREATE TABLE servers (
                'alias', 'uri', 'username', 'password', 'enabled'
            );
            
            CREATE TABLE settings (
                'name', 'value'
            );
            
            INSERT INTO settings VALUES ('checkinterval', 120.0);
            INSERT INTO settings VALUES ('soundenable', 1);
            INSERT INTO settings VALUES ('ackalloninit', 0);
            INSERT INTO settings VALUES ('playsoundiftriggerlastchange', 120.0);
            INSERT INTO settings VALUES ('showdashboardinit', 1);
            INSERT INTO settings VALUES ('playifprio', 0);
            INSERT INTO settings VALUES ('ackafterseconds', 60.0);
            INSERT INTO settings VALUES ('sounddelete', 1);
            INSERT INTO settings VALUES ('font', 12);

            """)

        self.persistent_db.commit()

    def stop(self, timeout=None):
        self.stoprequest.set()
        super(configuration, self).join(timeout)

    def set_password(self, raw_password):
        return(base64.b64encode(raw_password))

    def check_password(self, raw_password, enc_password):
        try:
            return raw_password == base64.b64decode(enc_password)
        except:
            return False

    def get_password(self, password):
        return base64.b64decode(password)
    
    def __set_server__(self, *args, **kwargs):
        alias = kwargs["alias"]
        uri = kwargs["uri"]
        username = kwargs["username"]
        password = kwargs["password"]
        enabled = kwargs["enabled"]

        try:
            if self.__get_total_servers__(enabled=None) == 0:
                self.__fetch_servers__()
            servers = self.__get_servers__(alias=alias, enabled=None)
        except Exception as e:
            pprint(e)

        if len(servers) == 0:
            self.persistent_db_cursor.execute("INSERT INTO servers VALUES (?, ?, ?, ?, ?)",
                                ( alias, uri, username, self.set_password(password), enabled ))
        else:
            for server in servers:
                if not (server['uri'] == uri and \
                        server['username'] == username and \
                        self.check_password(password, server['password']) and \
                        server['enabled'] == enabled):
                    self.__mod_server__(alias=alias, uri=uri, username=username, password=self.set_password(password), enabled=enabled)

    def set_server(self, alias, uri, username, password, enabled):
        self.conf_in_q.put(["__set_server__", {"alias": alias, "uri": uri, "username": username, "password": password, "enabled": enabled }])
        return self.conf_out_q.get()

    def __mod_server__(self, *args, **kwargs):
        return self.persistent_db_cursor.execute("UPDATE servers SET uri=?, username=?, password=?, enabled=? WHERE alias=?",
                             (kwargs["uri"], kwargs["username"], kwargs["password"], kwargs["enabled"], kwargs["alias"]))
    
    def mod_server(self, alias, uri, username, password, enabled):
        self.conf_in_q.put(["__mod_server__", {"alias": alias, "uri": uri, "username": username, "password": password, "enabled": enabled }])
        return self.conf_out_q.get()

    def __del_server__(self, *args, **kwargs):
        return self.persistent_db_cursor.execute("DELETE FROM servers WHERE alias=?", (kwargs["alias"],))

    def del_server(self, alias):
        self.conf_in_q.put(["__del_server__", {"alias": alias }])
        return self.conf_out_q.get()

    def __get_servers__(self, *args, **kwargs):
        servers = []
        self.__fetch_servers__()
        for server in self.__SERVERS:
            if kwargs["alias"] != None and server['alias'] == kwargs["alias"]:
                if kwargs["enabled"] != None and server['enabled'] == kwargs["enabled"]:
                    servers.append(server)
                else:
                    servers.append(server)
            elif kwargs["enabled"] != None and server['enabled'] == kwargs["enabled"]:
                servers.append(server)
            elif kwargs["alias"] == None and kwargs["enabled"] == None:
                servers.append(server)

        return servers

    def get_servers(self, alias = None, enabled = None):
        self.conf_in_q.put(["__get_servers__", { "alias": alias, "enabled": enabled }])
        return self.conf_out_q.get()

    def __fetch_servers__(self, *args, **kwargs):
        self.persistent_db_cursor.execute("SELECT * FROM servers")

        self.__SERVERS = []
        for server in self.persistent_db_cursor.fetchall():
            self.__SERVERS.append({'alias': server[self.__SERVERS_COLUMNS['alias']],
                                                                       'uri': server[self.__SERVERS_COLUMNS['uri']],
                                                                       'username': server[self.__SERVERS_COLUMNS['username']], 
                                                                       'password': server[self.__SERVERS_COLUMNS['password']], 
                                                                       'enabled': server[self.__SERVERS_COLUMNS['enabled']]}
                                                                       )

    def fetch_servers(self):
        self.conf_in_q.put(["__fetch_servers__", { "None": None } ])
        return self.conf_out_q.get()
        
    def get_server(self, id, column):
        if id in range(0, len(self.__SERVERS)):
            return self.__SERVERS[id][column]
        else:
            return False

    def __get_total_servers__(self, *args, **kwargs):
        enabled = kwargs["enabled"]

        try:
            return len(self.__get_servers__(alias=None, enabled=enabled))
        except Exception as e:
            print "Exception in get_total_servers: ", e
            return 0

    def get_total_servers(self, enabled = None):
        self.conf_in_q.put(["__get_total_servers__", { "enabled": enabled } ])
        return self.conf_out_q.get()

    def __get_setting__(self, *args, **kwargs):
        self.persistent_db_cursor.execute("SELECT value FROM settings WHERE name=?", (kwargs["name"],))
        value = self.persistent_db_cursor.fetchall()
        if len(value) > 0 and len(value[0]) > 0:
            return value[0][0]
        else:
            return None


    def __set_setting__(self, *args, **kwargs):
        try:
            self.persistent_db_cursor.execute("SELECT value FROM settings WHERE name=?", (kwargs["name"],))
            settings = self.persistent_db_cursor.fetchall()
            if len(settings) == 0:
                self.persistent_db_cursor.execute("INSERT INTO settings VALUES (?,?)", (kwargs["name"], kwargs["value"], ))
            elif settings[0][0] != kwargs["value"]:
                self.persistent_db_cursor.execute("UPDATE settings SET value=? WHERE name=?",(kwargs["value"], kwargs["name"], ))
            else:
                return True
            self.persistent_db.commit()
            return True
        except:
            return False

    def get_setting(self, name):
        self.conf_in_q.put(["__get_setting__", {"name": name }])
        return self.conf_out_q.get()

    def set_setting(self, name, value):
        self.conf_in_q.put(["__set_setting__", {"name": name, "value": value}])
        return self.conf_out_q.get()
