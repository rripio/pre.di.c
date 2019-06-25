#!/usr/bin/env python3

"""sets up alsa_loop ports in jack to be used from ALSA sound
backend players"""

import sys
import threading
import predic as pd
import subprocess as sp


def start():

    # create jack loop for connections
    # The jack_loop module will keep the loop alive, so we need to thread it.
    #pd.jack_loop('alsa_loop')
    jloop = threading.Thread( target = pd.jack_loop, args=('alsa_loop',) )
    jloop.start()


def stop():

    sp.Popen('pkill -f alsa_loop_load.py'.split())


if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('alsa_loop_load.py: bad option')
else:
    print(__doc__)

