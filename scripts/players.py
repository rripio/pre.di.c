#!/usr/bin/env python3
"""
    Starts / stops a server that process trough by the 'players' module
    
    use:   scripts/players.py    start | stop
"""

import sys, os
from subprocess import Popen
from getconfigs import config

server_path = os.path.expanduser( config['server_path'] )

def start():
    Popen( f'{server_path} players'.split() )

def stop():
    Popen( [ 'pkill', '-KILL', '-f', f'{server_path} players' ] )
    # harakiri
    Popen( ['pkill', '-KILL', '-f',  'scripts/players.py'] )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print( '(scripts/players.py) bad option' )
else:
    print(__doc__)
