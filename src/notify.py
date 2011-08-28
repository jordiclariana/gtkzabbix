'''
Created on 29/07/2011

@author: Jordi Clariana
'''
import pynotify
from zbx_priorities import zbx_priorities

class notify:
    def __init__(self):
        if not pynotify.init("ZabbixNotify"):
            print "there was a problem initializing the pynotify module"
    
    def notify(self, priority, title, message):
        if pynotify.is_initted():
            n = pynotify.Notification(title, message, "file://" + zbx_priorities(priority).get_icon())
            n.show()
