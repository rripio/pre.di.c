#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""sets up loop ports in jack """

import sys
import subprocess as sp
import multiprocessing as mp

import pdlib as pd

def start():

    # create jack loop for connections
    # The jack_loop module will keep the loop alive, so we need to thread it.
    #jd.jack_loop('alsa_loop')
    jloop = mp.Process( target = pd.jack_loop, args=('stream_loop',) )
    jloop.start()


def stop():

    sp.Popen('pkill -f stream_loop.py'.split())


if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('stream_loop.py: bad option')
else:
    print(__doc__)


