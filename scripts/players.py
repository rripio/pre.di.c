#!/usr/bin/env python3
"""
    Starts a server to manage players
    
    use:   scripts/players.py    start | stop
"""

import sys
from subprocess import Popen

def start():
    Popen( ['server_misc.py', 'players'] ) # if this fails check your paths

def stop():
    Popen( ['pkill', '-KILL', '-f',  'server_misc.py players'] )
    # harakiri
    Popen( ['pkill', '-KILL', '-f',  'scripts/players.py'] )

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
