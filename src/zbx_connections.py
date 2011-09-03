'''
Created on 02/08/2011

@author: jordi
'''
from zabbix_api import ZabbixAPI, ZabbixAPIException
from configuration import configuration
from pprint import pprint
import sys

class zbx_connections:
    def __init__(self, conf = None):
        self.zAPIs = {}
        if conf == None:
            self.conf = configuration()
        else:
            self.conf = conf 

    def init(self):
        for zapiID in range(0, self.conf.get_total_servers()):
            if self.conf.get_server(zapiID, 'enabled') == True:
                alias = self.conf.get_server(zapiID, 'alias')
                self.zAPIs[alias] = ZabbixAPI(server=self.conf.get_server(zapiID, 'uri'),log_level=0)
                try:
                    self.zAPIs[alias].login(self.conf.get_server(zapiID, 'username'), 
                                             self.conf.get_password(self.conf.get_server(zapiID, 'password')))
                    print "Logged in {0}: {1}".format(self.conf.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login())
                except ZabbixAPIException, e:
                    sys.stderr.write(str(e) + '\n')
                except Exception as e:
                    print "zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e)

    def get_connection(self, alias):
        if self.zAPIs.has_key(alias):
            return self.zAPIs[alias]
        else:
            return None

    def recheck(self):
        for zapiID in range(0, self.conf.get_total_servers()):
            alias = self.conf.get_server(zapiID, 'alias')
            if self.conf.get_server(zapiID, 'enabled') == True:
                alias = self.conf.get_server(zapiID, 'alias')
                if not self.zAPIs.has_key(alias): # New server
                    self.zAPIs[alias] = ZabbixAPI(server=self.conf.get_server(zapiID, 'uri'),log_level=0)
                    try:
                        self.zAPIs[alias].login(self.conf.get_server(zapiID, 'username'), 
                                                 self.conf.get_password(self.conf.get_server(zapiID, 'password')))
                        print "Logged in {0}: {1}".format(self.conf.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login())
                    except ZabbixAPIException, e:
                        sys.stderr.write(str(e) + '\n')
                    except Exception as e:
                        print "zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e)
                else: # Check if auth session is still good
                    try:
                        if not self.zAPIs[alias].test_login():
                            raise Exception
                    except:
                        try:
                            self.zAPIs[alias].login(self.conf.get_server(zapiID, 'username'), 
                                                    self.conf.get_password(self.conf.get_server(zapiID, 'password')))
                            print "Relogged in {0}: {1}".format(self.conf.get_server(zapiID, 'alias'), self.zAPIs[alias].test_login())
                        except ZabbixAPIException, e:
                            sys.stderr.write(str(e) + '\n')
                        except Exception as e:
                            print "zbx_connections | Unexpected error connecting to {0}:\n\t{1}".format(alias,e)
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
    
