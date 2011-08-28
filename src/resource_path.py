'''
Created on 27/07/2011

@author: jordi
'''

import os

class resource_path:
    def __init__(self, rel_path):
        dir_of_py_file = os.path.dirname(__file__)
        rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
        self.abs_path_to_resource = os.path.abspath(rel_path_to_resource)
    
    def get(self):
        return self.abs_path_to_resource