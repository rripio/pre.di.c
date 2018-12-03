#!/usr/bin/env python2
"""
    Starts the server_aux.py for some tasks as amplifier switch on/off and players management
    
    use:   scripts/server_aux.py    start | stop
"""

import sys
from subprocess import Popen

def start():
    Popen( ['server_aux.py'] ) # if this fails check your paths

def stop():
    Popen( 'pkill -KILL -f server_aux.py'.split() )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(server_aux) bad option')
else:
    print(__doc__)
