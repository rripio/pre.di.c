#!/usr/bin/env python3

"""
    a mouse as volume control

    use:   mouse_volume.py   start | stop
"""

import sys
from subprocess import Popen

import mouse_volume_daemon as mvd

def start():
    mvd.main_loop()

def stop():
    Popen( ['pkill', '-f',  'mouse_volume.py'] )

if sys.argv[1:]:

    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(mouse_volume_daemon) bad option')
else:
    print(__doc__)
