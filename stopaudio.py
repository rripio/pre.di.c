# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
Stops pre.di.c audio system.

Usage:
stopaudio.py [ core | clients | all ]   (default 'all')
core: jack, brutefir, server
clients: everything else (players and clients)
all: all of the above
"""

import sys
import os
import time
from subprocess import Popen

import init
import pdlib as pd


fnull = open(os.devnull, 'w')


def main(run_level):
    """Stop pre.di.c."""
    if run_level in {'clients', 'all'}:
        # Stop external scripts, sources and clients.
        print('(stopaudio) stopping clients:')
        for client in pd.read_clients('stop'):
            try:
                print('(stopaudio) stopping', client)
                Popen(f'{client}'.split())
            except Exception as e:
                print('\n(stopaudio) problem stopping client',
                      f'"{client}": {e}\n')
    if run_level in {'core', 'all'}:
        # controlserver
        print('(stopaudio) stopping server')
        Popen('pkill -fe server.py'.split())
        # camilladsp
        print('(stopaudio) stopping camilladsp')
        Popen('pkill -fe camilladsp'.split())
        # jack
        print('(stopaudio) stopping jackd')
        Popen('pkill -fe jackd'.split())

        # Dirty hack, rekill camilladsp.
        # Wait a bit.
        time.sleep(init.config['command_delay'] * 5)
        # camilladsp
        print('(stopaudio) stopping camilladsp')
        Popen('pkill -fe camilladsp'.split())


if __name__ == '__main__':

    run_level = 'all'
    if sys.argv[1:]:
        run_level = sys.argv[1]
    if run_level in {'core', 'clients', 'all'}:
        print('(stopaudio) stopping', run_level)
        main(run_level)
    else:
        print(__doc__)
