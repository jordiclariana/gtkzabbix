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

class confthread(threading.Thread):

    def __init__(self, conf_in_q, conf_out_q):
        # Setup queues and threading
        super(confthread, self).__init__()
        self.conf_in_q = conf_in_q
        self.conf_out_q = conf_out_q
        self.stoprequest = threading.Event()
        self.lock = threading.Lock()

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
                'alias', 'uri', 'username', 'password', 'enabled', 'server_type'
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
        super(confthread, self).join(timeout)

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
        server_type = kwargs["server_type"]

        try:
            if self.__get_total_servers__(enabled=None) == 0:
                self.__fetch_servers__()
            servers = self.__get_servers__(alias=alias, enabled=None)
        except Exception as e:
            pprint(e)

        if len(servers) == 0:
            self.persistent_db_cursor.execute("INSERT INTO servers VALUES (?, ?, ?, ?, ?, ?)",
                                ( alias, uri, username, self.set_password(password), enabled, server_type ))
        else:
            for server in servers:
                if not (server['uri'] == uri and \
                        server['username'] == username and \
                        self.check_password(password, server['password']) and \
                        server['enabled'] == enabled and \
                        server['server_type'] == server_type):
                    self.__mod_server__(alias=alias, uri=uri, username=username, password=self.set_password(password), enabled=enabled, server_type=server_type)

    def __mod_server__(self, *args, **kwargs):
        alias = kwargs["alias"]
        uri = kwargs["uri"]
        username = kwargs["username"]
        password = kwargs["password"]
        enabled = kwargs["enabled"]
        server_type = kwargs["server_type"]

        print("Server type: %d" % server_type)
        return self.persistent_db_cursor.execute("UPDATE servers SET uri=?, username=?, password=?, enabled=?, server_type=? WHERE alias=?",
                             (uri, username, password, enabled, server_type, alias))
    
    def __del_server__(self, *args, **kwargs):
        alias = kwargs["alias"]

        return self.persistent_db_cursor.execute("DELETE FROM servers WHERE alias=?", (alias,))

    def __get_servers__(self, *args, **kwargs):
        alias = kwargs["alias"]
        enabled = kwargs["enabled"]

        servers = []
        self.__fetch_servers__()
        for server in self.SERVERS:
            if alias != None and server['alias'] == alias:
                if enabled != None and server['enabled'] == enabled:
                    servers.append(server)
                else:
                    servers.append(server)
            elif enabled != None and server['enabled'] == enabled:
                servers.append(server)
            elif alias == None and enabled == None:
                servers.append(server)

        return servers

    def __fetch_servers__(self, *args, **kwargs):
        self.persistent_db_cursor.execute("SELECT * FROM servers")

        self.SERVERS = []
        for server in self.persistent_db_cursor.fetchall():
            self.SERVERS.append({'alias': server[self.SERVERS_COLUMNS['alias']],
                                   'uri': server[self.SERVERS_COLUMNS['uri']],
                                   'username': server[self.SERVERS_COLUMNS['username']], 
                                   'password': server[self.SERVERS_COLUMNS['password']], 
                                   'enabled': server[self.SERVERS_COLUMNS['enabled']],
                                   'server_type': server[self.SERVERS_COLUMNS['server_type']]}
                               )

    def __get_total_servers__(self, *args, **kwargs):
        enabled = kwargs["enabled"]

        try:
            return len( self.__get_servers__(alias=None, enabled=enabled) )
        except Exception as e:
            print "Exception in get_total_servers: ", e
            return 0

    def __get_setting__(self, *args, **kwargs):
        name = kwargs["name"]
        self.persistent_db_cursor.execute("SELECT value FROM settings WHERE name=?", (name,))
        value = self.persistent_db_cursor.fetchall()
        if len(value) > 0 and len(value[0]) > 0:
            return value[0][0]
        else:
            return None

    def __set_setting__(self, *args, **kwargs):
        name = kwargs["name"]
        value = kwargs["value"]

        try:
            self.persistent_db_cursor.execute("SELECT value FROM settings WHERE name=?", (name,))
            settings = self.persistent_db_cursor.fetchall()
            if len(settings) == 0:
                self.persistent_db_cursor.execute("INSERT INTO settings VALUES (?,?)", (name, value, ))
            elif settings[0][0] != value:
                self.persistent_db_cursor.execute("UPDATE settings SET value=? WHERE name=?",(value, name, ))
            else:
                return True
            self.persistent_db.commit()
            return True
        except:
            return False
