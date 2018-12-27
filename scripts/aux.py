#!/usr/bin/env python3
"""
    Starts / stops a server which listen for some auxiliary tasks
    supported by the 'aux' module
    
    use:   scripts/aux.py    start | stop
"""

import sys
from subprocess import Popen

def start():
    Popen( ['server_misc.py', 'aux'] ) # if this fails check your paths

def stop():
    Popen( ['pkill', '-KILL', '-f',  'server_misc.py aux'] )
    # harakiri
    Popen( ['pkill', '-KILL', '-f',  'scripts/aux.py'] )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print( '(scripts/aux.py) bad option' )
else:
    print(__doc__)
