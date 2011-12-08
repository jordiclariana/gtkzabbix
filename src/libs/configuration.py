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
    import sqlalchemy
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.pool import NullPool
except Exception as e:
    print ("Error loading misc modules: {0}".format(e))
    print ("Try to install them using 'pip': pip install <module name>")
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

class configuration:
    
    __SERVERS = []

    Base = declarative_base()

    class Servers(Base):

        __tablename__ = 'servers'

        alias = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
        uri = sqlalchemy.Column(sqlalchemy.String)
        username = sqlalchemy.Column(sqlalchemy.String)
        password = sqlalchemy.Column(sqlalchemy.String)
        enabled = sqlalchemy.Column(sqlalchemy.String)
        
    class Settings(Base):
        
        __tablename__ = 'settings'

        name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
        value = sqlalchemy.Column(sqlalchemy.Integer)

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
        self.db = sqlalchemy.create_engine('sqlite:///' + self.defaultDBFile, poolclass = NullPool, echo_pool = True) #, connect_args={'check_same_thread':False}, echo_pool = True)
        self.db.echo = False
        self.metadata = sqlalchemy.MetaData(self.db)

        if self.defaultDBFile == ":memory:":
            self.init_db()
        else:
            try:
                self.conf_servers = sqlalchemy.Table('servers', self.metadata, autoload=True)
                self.conf_settings = sqlalchemy.Table('settings', self.metadata, autoload=True)
                self.Session = sqlalchemy.orm.sessionmaker(bind=self.db)
                self.SQLSession = self.Session()
            except:
                self.init_db()

        st = os.stat(self.defaultDBFile)
        if str(oct(stat.S_IMODE(st[stat.ST_MODE]))) != "0600":
            os.chmod(self.defaultDBFile,0600)
        
    def close_db(self):
        if self.defaultDBFile != ":memory:":
            self.SQLSession.flush()
            self.SQLSession.close()
        
    def init_db(self):
        self.Base.metadata.create_all(self.db) 

        self.conf_servers = sqlalchemy.Table('servers', self.metadata, autoload=True)
        self.conf_settings = sqlalchemy.Table('settings', self.metadata, autoload=True)

        self.Session = sqlalchemy.orm.sessionmaker(bind=self.db)
        self.SQLSession = self.Session()

        s_i = self.conf_settings.insert()
        s_i.execute(
            { 'name': 'checkinterval', 'value': "120.0" },
            { 'name': 'soundenable', 'value': "1" },
            { 'name': 'ackalloninit', 'value': "0" },
            { 'name': 'playsoundiftriggerlastchange', 'value': "120.0" },
            { 'name': 'showdashboardinit', 'value': "1" },
            { 'name': 'playifprio', 'value': "0" },
            { 'name': 'ackafterseconds', 'value': "60.0" },
            { 'name': 'sounddelete', 'value': "1" },
        )

        self.SQLSession.flush()

    def set_server(self, alias, uri, username, password, enabled):
        if self.get_total_servers() == 0:
            self.fetch_servers()

        servers = self.get_servers(alias)
        if len(servers) == 0:
            new_server = self.Servers()
            new_server.alias = alias
            new_server.uri = uri
            new_server.username = username
            new_server.password = self.set_password(password)
            new_server.enabled = enabled

            self.SQLSession.add(new_server)
            self.SQLSession.flush()
        else:
            for server in servers:
                if not (server['uri'] == uri and \
                        server['username'] == username and \
                        self.check_password(password, server['password']) and \
                        server['enabled'] == enabled):
                    self.mod_server(alias, uri, username, self.set_password(password), enabled)
    
    def mod_server(self, alias, uri, username, password, enabled):
        server = self.SQLSession.query(self.Servers).filter(self.Servers.alias == alias)
        
        server.uri = uri
        server.username = username
        server.password = password
        server.enabled = enabled

        self.SQLSession.flush()
            
    def del_server(self, alias):
        server = self.SQLSession.query(self.Servers).filter(self.Servers.alias == alias)

        self.SQLSession.delete(server)

        self.SQLSession.flush()

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
        servers = self.SQLSession.query(self.Servers)
        
        self.__SERVERS = []
        for server in servers:
            self.__SERVERS.append({'alias': server.alias,
                                   'uri': server.uri,
                                   'username': server.username, 
                                   'password': server.password, 
                                   'enabled': server.enabled}
                                   )
        
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
        setting = self.SQLSession.query(self.Settings).filter(self.Settings.name == name)
        try:
            return setting.one().value
        except:
            return None
        
    def set_setting(self, name, value):
        setting = self.SQLSession.query(self.Settings).filter(self.Settings.name == name)
        if setting:
            setting.value = value
        else:
            s_i = self.conf_settings.insert()
            s_i.execute(
                { 'name': name, 'value': value }
            )
        self.SQLSession.flush()
                
    def close(self):
        self.close_db()
        