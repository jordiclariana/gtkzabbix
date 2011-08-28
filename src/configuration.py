'''
Created on 27/07/2011

@author: Jordi Clariana
'''

import os, stat
import sqlite3
import base64
from pprint import pprint

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
        self.SQLcur = self.SQLconn.cursor()
        if self.defaultDBFile == ":memory:":
            self.init_db()
        else:
            try:
                self.SQLcur.execute("SELECT * FROM servers")
                self.SQLcur.execute("SELECT * FROM settings")
            except:
                self.init_db()
        st = os.stat(self.defaultDBFile)
        if str(oct(stat.S_IMODE(st[stat.ST_MODE]))) != "0600":
            os.chmod(self.defaultDBFile,0600)
        self.SQLcur.close()
        
    def close_db(self):
        if self.defaultDBFile != ":memory:":
            self.SQLconn.commit()
            self.SQLconn.close()
        
    def init_db(self):
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.executescript("""
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
        self.SQLcur.close()

    def set_server(self, alias, uri, username, password, enabled):
        self.SQLcur = self.SQLconn.cursor()
        if self.get_total_servers() == 0:
            self.fetch_servers()

        servers = self.get_servers(alias)
        if len(servers) == 0:
            self.SQLcur.execute("INSERT INTO servers VALUES (?, ?, ?, ?, ?)",
                                ( alias, uri, username, self.set_password(password), enabled ))
        else:
            for server in servers:
                if not (server['uri'] == uri and \
                        server['username'] == username and \
                        self.check_password(password, server['password']) and \
                        server['enabled'] == enabled):
                    self.mod_server(alias, uri, username, self.set_password(password), enabled)
        self.SQLconn.commit()
        self.SQLcur.close()
    
    def mod_server(self, alias, uri, username, password, enabled):
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.execute("UPDATE servers SET uri=?, username=?, password=?, enabled=? WHERE alias=?",
                             (uri, username, password, enabled, alias))
        self.SQLconn.commit()
        self.SQLcur.close()
    
    def del_server(self, alias):
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.execute("DELETE FROM servers WHERE alias=?", (alias,))
        self.SQLconn.commit()
        self.SQLcur.close()
        
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
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.execute("SELECT * FROM servers")
        
        self.__SERVERS = []
        for server in self.SQLcur.fetchall():
            self.__SERVERS.append({'alias': server[self.__SERVERS_COLUMNS['alias']],
                                                                       'uri': server[self.__SERVERS_COLUMNS['uri']],
                                                                       'username': server[self.__SERVERS_COLUMNS['username']], 
                                                                       'password': server[self.__SERVERS_COLUMNS['password']], 
                                                                       'enabled': server[self.__SERVERS_COLUMNS['enabled']]}
                                                                       )
        self.SQLcur.close()
        
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
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.execute("SELECT value FROM settings WHERE name=?", (name,))
        value = self.SQLcur.fetchall()
        self.SQLcur.close()
        if len(value) > 0 and len(value[0]) > 0:
            return value[0][0]
        else:
            return None
        
    def set_setting(self, name, value):
        self.SQLcur = self.SQLconn.cursor()
        self.SQLcur.execute("SELECT value FROM settings WHERE name=?", (name,))
        settings = self.SQLcur.fetchall()
        if len(settings) == 0:
            self.SQLcur.execute("INSERT INTO settings VALUES (?,?)", (name, value))
        elif settings[0][0] != value:
            self.SQLcur.execute("UPDATE settings SET value=? WHERE name=?",(value, name))
        
        self.SQLconn.commit()
        self.SQLcur.close()
                
    def close(self):
        self.close_db()
        