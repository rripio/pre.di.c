#!/usr/bin/env python2
import sys
from subprocess import Popen

def start():
    Popen( ['server_local.py'] ) # if this fails check your paths

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
