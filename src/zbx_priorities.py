'''
Created on 27/07/2011

@author: Jordi Clariana
'''

from resource_path import resource_path

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
            return resource_path("icons/{0}".format(self.__priorities_icon[self.__PRIORITY])).get()
        else:
            return resource_path("icons/{0}".format(self.__white_icon)).get()
    
    def get_empty_icon(self):
        return resource_path("icons/{0}".format(self.__empty_icon)).get()
    
    def get_sound(self):
        if self.__PRIORITY >= 0:
            return resource_path("audio/{0}".format(self.__priorities_sound[self.__PRIORITY])).get()
        else:
            return resource_path("audio/{0}".format(self.__priorities_sound_off)).get()
