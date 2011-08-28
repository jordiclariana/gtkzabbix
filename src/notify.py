'''
Created on 29/07/2011

@author: Jordi Clariana
'''
import pynotify
from zbx_priorities import zbx_priorities

class notify:
    def __init__(self, priority, title, message, timeout):
        if not pynotify.init("GTKZabbix"):
            print "there was a problem initializing the pynotify module"
        else:
            n = pynotify.Notification(title, message, "file://" + zbx_priorities(priority).get_icon())
            n.set_timeout(timeout)
            n.show()