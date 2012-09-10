import os
import sys

# adding libs directory at the beginning of sys.path.
# all external dependencies are included => no need for the user to pip install/setup.py install anything
this_file = os.path.realpath(__file__) 
this_loc =  os.path.dirname(this_file)
libs_loc = os.path.join(this_loc, "libs")
sys.path = [libs_loc] + sys.path
if this_loc not in sys.path:
	sys.path = [this_loc] + sys.path

