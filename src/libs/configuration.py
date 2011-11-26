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
    import os, stat
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

class configuration:
    
    __SERVERS_COLUMNS={'alias': 0, 'uri': 1, 'username': 2, 'password': 3, 'enabled': 4}
    __SERVERS = []

    def __init__(self):
        self.defaultDBFile = os.path.expanduser('~') + "/.GTKZabbixNotify.sqlite"
        self.open_db()

    def set_password(self, raw_password):
        return(base64.b64encode(raw_password))

    def check_password(self, raw_password, enc_password):
        try:
            return raw_password == base64.b64decode(enc_password)
        except:
            return False

    def get_password(self, password):
        return base64.b64decode(password)
    
    def open_db(self):
        self.SQLconn = sqlite3.connect(self.defaultDBFile) #, check_same_thread = False)
        SQLcur = self.SQLconn.cursor()
        if self.defaultDBFile == ":memory:":
            self.init_db()
        else:
            try:
                SQLcur.execute("SELECT * FROM servers")
                SQLcur.execute("SELECT * FROM settings")
            except:
                self.init_db()
        st = os.stat(self.defaultDBFile)
        if str(oct(stat.S_IMODE(st[stat.ST_MODE]))) != "0600":
            os.chmod(self.defaultDBFile,0600)
        SQLcur.close()
        
    def close_db(self):
        if self.defaultDBFile != ":memory:":
            self.SQLconn.commit()
            self.SQLconn.close()
        
    def init_db(self):
        SQLcur = self.SQLconn.cursor()
        SQLcur.executescript("""
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

        """)
        SQLcur.close()

    def set_server(self, alias, uri, username, password, enabled):
        SQLcur = self.SQLconn.cursor()
        if self.get_total_servers() == 0:
            self.fetch_servers()

        servers = self.get_servers(alias)
        if len(servers) == 0:
            SQLcur.execute("INSERT INTO servers VALUES (?, ?, ?, ?, ?)",
                                ( alias, uri, username, self.set_password(password), enabled ))
        else:
            for server in servers:
                if not (server['uri'] == uri and \
                        server['username'] == username and \
                        self.check_password(password, server['password']) and \
                        server['enabled'] == enabled):
                    self.mod_server(alias, uri, username, self.set_password(password), enabled)
        self.SQLconn.commit()
        SQLcur.close()
    
    def mod_server(self, alias, uri, username, password, enabled):
        SQLcur = self.SQLconn.cursor()
        SQLcur.execute("UPDATE servers SET uri=?, username=?, password=?, enabled=? WHERE alias=?",
                             (uri, username, password, enabled, alias))
        self.SQLconn.commit()
        SQLcur.close()
    
    def del_server(self, alias):
        SQLcur = self.SQLconn.cursor()
        SQLcur.execute("DELETE FROM servers WHERE alias=?", (alias,))
        self.SQLconn.commit()
        SQLcur.close()
        
    def get_servers(self, alias = None, enabled = None):
        servers = []
        self.fetch_servers()
        for server in self.__SERVERS:
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

    def fetch_servers(self):
        SQLcur = self.SQLconn.cursor()
        SQLcur.execute("SELECT * FROM servers")
        
        self.__SERVERS = []
        for server in SQLcur.fetchall():
            self.__SERVERS.append({'alias': server[self.__SERVERS_COLUMNS['alias']],
                                                                       'uri': server[self.__SERVERS_COLUMNS['uri']],
                                                                       'username': server[self.__SERVERS_COLUMNS['username']], 
                                                                       'password': server[self.__SERVERS_COLUMNS['password']], 
                                                                       'enabled': server[self.__SERVERS_COLUMNS['enabled']]}
                                                                       )
        SQLcur.close()
        
    def get_server(self, id, column):
        if id in range(0, len(self.__SERVERS)):
            return self.__SERVERS[id][column]
        else:
            return False

    def get_total_servers(self, enabled = None):
        try:
            return len(self.get_servers(enabled = enabled))
        except Exception as e:
            print "Exception in get_total_servers: ", e
            return 0
        
    def get_setting(self, name):
        SQLcur = self.SQLconn.cursor()
        SQLcur.execute("SELECT value FROM settings WHERE name=?", (name,))
        value = SQLcur.fetchall()
        SQLcur.close()
        if len(value) > 0 and len(value[0]) > 0:
            return value[0][0]
        else:
            return None
        
    def set_setting(self, name, value):
        SQLcur = self.SQLconn.cursor()
        SQLcur.execute("SELECT value FROM settings WHERE name=?", (name,))
        settings = SQLcur.fetchall()
        if len(settings) == 0:
            SQLcur.execute("INSERT INTO settings VALUES (?,?)", (name, value))
        elif settings[0][0] != value:
            SQLcur.execute("UPDATE settings SET value=? WHERE name=?",(value, name))
        
        self.SQLconn.commit()
        SQLcur.close()
                
    def close(self):
        self.close_db()
        