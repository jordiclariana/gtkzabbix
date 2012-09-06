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
except Exception as e:
    print ("Error loading system modules: {0}".format(e))
    sys.exit(1)

# Custom modules
try:
    from resource_path import resource_path
    from zabbix_api import ZabbixAPI, ZabbixAPIException
    from configuration import configuration
except Exception as e:
    print ("Error loading custom modules: {0}".format(e))
    sys.exit(1)

# Debugging
try:
    from pprint import pprint
except Exception as e:
    print ("Error loading debugging modules: {0}".format(e))
    sys.exit(1)

class zbx_priorities:
    __priorities = [ 'Not classified', 'Informational', 'Warning', 'Average' ,'High', 'Disaster' ]
    __priorities_color_bg = [ '#00FF00', '#00FF00', '#FFFF00', '#FF8C00', '#FF0000', '#D02090' ]
    __priorities_color_fg = [ '#000000', '#000000', '#000000', '#000000', '#FFFFFF', '#FFFFFF' ]
    __priorities_not_color_fg = [ '#000000', '#000000', '#000000', '#000000', '#000000', '#000000' ]
    __priorities_not_color_bg = [ '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF' ]
    __priorities_icon = [ 'green.png', 'green.png', 'yellow.png', 'amber.png', 'red.png', 'red.png' ]
    __priorities_sound = [ 'trigger_on.wav' , 'trigger_on.wav', 'trigger_on_warning.wav', 'trigger_on_average.wav', 'trigger_on_high.wav', 'trigger_on_disaster.wav' ]
    __priorities_sound_off = 'trigger_off.wav'
    __white_icon = 'white.png'
    __empty_icon = 'empty.png'

    def __init__(self, priority = -1):
        self.__PRIORITY = int(priority)
    
    def get_text(self):
        return self.__priorities[self.__PRIORITY]
    
    def get_color(self, type = 0):
        if type == 0: # Background
            return self.__priorities_color_bg[self.__PRIORITY]
        else: # Foreground
            return self.__priorities_color_fg[self.__PRIORITY]
    
    def get_not_color(self, type = 0):
        if type == 0: # Background
            return self.__priorities_not_color_bg[self.__PRIORITY]
        else: # Foreground
            return self.__priorities_not_color_fg[self.__PRIORITY]

    def get_icon(self):
        if self.__PRIORITY >= 0:
            return resource_path("resources/icons/{0}".format(self.__priorities_icon[self.__PRIORITY])).get()
        else:
            return resource_path("resources/icons/{0}".format(self.__white_icon)).get()
    
    def get_empty_icon(self):
        return resource_path("resources/icons/{0}".format(self.__empty_icon)).get()
    
    def get_sound(self):
        if self.__PRIORITY >= 0:
            return resource_path("resources/audio/{0}".format(self.__priorities_sound[self.__PRIORITY])).get()
        else:
            return resource_path("resources/audio/{0}".format(self.__priorities_sound_off)).get()

class zbx_connections:
    def __init__(self, conf = None):
        self.zAPIs = {}
        if not conf:
            self.configuration = configuration()
        else:
            self.configuration = conf 

    def init(self):
        for zapiID in range(0, self.configuration.get_total_servers()):
            if self.configuration.get_server(zapiID, 'enabled') == True:
                alias = self.configuration.get_server(zapiID, 'alias')
                self.zAPIs[alias] = ZabbixAPI(server=self.configuration.get_server(zapiID, 'uri'),log_level=0)
                try:
                    self.zAPIs[alias].login(self.configuration.get_server(zapiID, 'username'), 
                                             self.configuration.get_password(self.configuration.get_server(zapiID, 'password')))
                    print ("Logged in {0}: {1}".format(self.configuration.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login()))
                except ZabbixAPIException, e:
                    sys.stderr.write(str(e) + '\n')
                except Exception as e:
                    print ("zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e))

    def get_connection(self, alias):
        if self.zAPIs.has_key(alias):
            return self.zAPIs[alias]
        else:
            return None

    def recheck(self):
        for zapiID in range(0, self.configuration.get_total_servers()):
            alias = self.configuration.get_server(zapiID, 'alias')
            if self.configuration.get_server(zapiID, 'enabled') == True:
                alias = self.configuration.get_server(zapiID, 'alias')
                if not self.zAPIs.has_key(alias): # New server
                    self.zAPIs[alias] = ZabbixAPI(server=self.configuration.get_server(zapiID, 'uri'),log_level=0)
                    try:
                        self.zAPIs[alias].login(self.configuration.get_server(zapiID, 'username'), 
                                                 self.configuration.get_password(self.configuration.get_server(zapiID, 'password')))
                        print ("Logged in {0}: {1}".format(self.configuration.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login()))
                    except ZabbixAPIException, e:
                        sys.stderr.write(str(e) + '\n')
                    except Exception as e:
                        print ("zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e))
                else: # Check if auth session is still good
                    try:
                        if not self.zAPIs[alias].test_login():
                            raise Exception
                    except:
                        try:
                            self.zAPIs[alias].login(self.configuration.get_server(zapiID, 'username'), 
                                                    self.configuration.get_password(self.configuration.get_server(zapiID, 'password')))
                            print ("Relogged in {0}: {1}".format(self.configuration.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login()))
                        except ZabbixAPIException, e:
                            sys.stderr.write(str(e) + '\n')
                        except Exception as e:
                            print ("zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e))
            else:
                if self.zAPIs.has_key(alias):
                    del self.zAPIs[alias]

    def alias(self):
        for alias in self.zAPIs:
            yield alias
        return
            
    def connections(self):
        for alias in self.zAPIs:
            yield (alias, self.zAPIs[alias])
        return
    
    def total_connections(self):
        return len(self.zAPIs)
    
class zbx_triggers:
    
    __TRIGGERS = []
    
    def __init__(self, conf = None):
        if not conf:
            self.configuration = configuration()
        else:
            self.configuration = conf
        self.zbxConnections = zbx_connections(self.configuration)
        self.zbxConnections.init()
        self.fetch()

    def fetch(self):
        self.zbxConnections.recheck()
        for zAPIAlias, zAPIConn in self.zbxConnections.connections():
            triggers_list = []
            try:
                for trigger in zAPIConn.trigger.get(
                    {'active' : True,
                     'monitored': True,
                     'sortfield': 'lastchange',
                     'filter': {'value': 1},
                     'skipDependent': False}):
                    
                    triggers_list.append(trigger.get('triggerid'))
        
                this_trigger = zAPIConn.trigger.get(
                    {'triggerids': triggers_list,
                     'expandDescription': True,
                     'output': 'extend',
                     'expandData': True})
                this_triggers_groups = zAPIConn.hostgroup.get({'triggerids': triggers_list, 'output': 'extend'})
                
                if type(this_trigger) is dict:
                    for triggerid in this_trigger.keys():
                        self.set_trigger(self.new_trigger(zAPIAlias, this_trigger[triggerid], this_triggers_groups))
                elif type(this_trigger) is list:
                    for trigger in this_trigger:
                        self.set_trigger(self.new_trigger(zAPIAlias, trigger, this_triggers_groups))
                else:
                    print ("Error parsing triggers. Not dict and not list. Is: {0}".format(type(this_trigger)))
                    continue
            except Exception as e:
                print ("zbx_triggers | Unexpected error getting triggers from {0}:\n\t{1}".format(zAPIAlias, e))
    
    def set_trigger(self, value):
        self.__TRIGGERS.append(value)
    
    def get_trigger(self, triggerid):
        for trigger in self.__TRIGGERS:
            if trigger.get_id() == int(triggerid):
                return(trigger)
        return False
        
    def get_triggers(self):
        for trigger in self.__TRIGGERS:
            if isinstance(trigger, zbx_trigger):
                yield trigger
            else:
                yield False
        return
    
    def new_trigger(self, serveralias, trigger, groups):
        trigger_groups = {}
        for group in groups:
            for gtrigger in group['triggers']:
                if gtrigger['triggerid'] == trigger['triggerid'] and not trigger_groups.has_key(int(group['groupid'])):
                    trigger_groups[int(group['groupid'])]= group['name']
                    
        new_trigger = zbx_trigger()
        try:
            new_trigger.set_id(trigger['triggerid'])
            new_trigger.set_hostid(trigger['hostid'])
            new_trigger.set_host(trigger['host'])
            new_trigger.set_lastchange(trigger['lastchange'])
            new_trigger.set_priority(trigger['priority'])
            new_trigger.set_description(trigger['description'])
            new_trigger.set_groups(trigger_groups)
            new_trigger.set_serveralias(serveralias)
        except Exception as e:
            print ("zbx_triggers | Exception on formating new trigger from {0}:\n\t{1}".format(serveralias, e))
            return False

        return new_trigger
    
    TRIGGERS = property(get_trigger, set_trigger, None, None)
    
class zbx_trigger:
    
    def __init__(self):
        self.__ID=0
        self.__HOSTID=0
        self.__LASTCHANGE=0
        self.__PRIORITY=0
        self.__HOST=0
        self.__DESCRIPTION=""
        self.__GROUPS=[]
        self.__SERVERALIAS=""
                
    def get_id(self):
        return self.__ID

    def get_hostid(self):
        return self.__HOSTID

    def get_lastchange(self):
        return self.__LASTCHANGE

    def get_priority(self):
        return self.__PRIORITY

    def get_host(self):
        return self.__HOST

    def get_description(self):
        return self.__DESCRIPTION

    def get_groups(self):
        return self.__GROUPS

    def get_serveralias(self):
        return self.__SERVERALIAS

    def set_id(self, value):
        self.__ID = int(value)

    def set_hostid(self, value):
        self.__HOSTID = int(value)

    def set_lastchange(self, value):
        self.__LASTCHANGE = int(value)

    def set_priority(self, value):
        self.__PRIORITY = int(value)

    def set_host(self, value):
        self.__HOST = value

    def set_description(self, value):
        self.__DESCRIPTION = value

    def set_groups(self, value):
        self.__GROUPS.append(value)

    def set_serveralias(self, value):
        self.__SERVERALIAS = value

    ID = property(get_id, set_id, None, None)
    HOSTID = property(get_hostid, set_hostid, None, None)
    LASTCHANGE = property(get_lastchange, set_lastchange, None, None)
    PRIORITY = property(get_priority, set_priority, None, None)
    HOST = property(get_host, set_host, None, None)
    DESCRIPTION = property(get_description, set_description, None, None)
    GROUPS = property(get_groups, set_groups, None, None)
    SERVERALIAS = property(get_serveralias, set_serveralias, None, None)


