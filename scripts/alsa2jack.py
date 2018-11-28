#!/usr/bin/env python3

""" sets up alsa_loop ports in jack to be used from ALSA backended players

    use:    alsa2jack.py   start | stop
"""

import sys
from subprocess import run
from predic import jack_loop

def start():
    # jack_loop module will keep the loop alive
    jack_loop('alsa_loop')

def stop():
    run( 'pkill -f alsa2jack.py'.split() )
    sys.exit()

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(alsa2jack) bad option')
else:
    print(__doc__)
