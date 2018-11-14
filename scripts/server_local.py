#!/usr/bin/env python2
import sys
from subprocess import Popen

def start():
    Popen( '/home/predic/bin/server_local.py' )

def stop():
    Popen( 'pkill -KILL -f server_local.py'.split() )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(server_local) bad option')
else:
    print(__doc__)
