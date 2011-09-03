'''
Created on 03/09/2011

@author: Jordi Clariana
'''
import gtk
from resource_path import resource_path
from pprint import pprint

class tooltip:
    def __init__(self):
        filename = resource_path("glade/tooltip.glade").get()
        self.builder = gtk.Builder()
        self.builder.add_from_file(filename)
        
        self.tooltipWindow = self.builder.get_object("tooltipWindow")
        self.lbl_Trigger = self.builder.get_object("lbl_Trigger")
        
        self.events_dic = {
           'on_lbl_Trigger_size_request': self.lbl_resize,
       }
        self.builder.connect_signals(self.events_dic)

        
    def show(self, x, y, text):        
        self.lbl_Trigger.set_markup(text)
        self.tooltipWindow.move(x, y)
        self.tooltipWindow.show()
        
    def hide(self):
        self.tooltipWindow.hide()
        
    def lbl_resize(self, widget, size):
        self.tooltipWindow.resize(size.width, size.height)
        return True