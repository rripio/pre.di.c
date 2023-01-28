#! /usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
Stops pre.di.c audio system

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
    """main stop function"""

    if run_level in {'clients', 'all'}:
        # stop external scripts, sources and clients
        print('(stopaudio) stopping clients')
        for command in pd.read_clients('stop'):
            try:
                Popen(f'{init.clients_folder}/{command}'.split())
            except Exception:
                print(f'problem stopping client "{command}":\n\t{err}')
    if run_level in {'core', 'all'}:
        # controlserver
        print('(stopaudio) stopping server')
        Popen ('pkill -f server.py'.split(), stdout=fnull, stderr=fnull)
        # camilladsp
        print('(stopaudio) stopping camilladsp')
        Popen ('pkill -f camilladsp'.split(), stdout=fnull, stderr=fnull)
        # jack
        print('(stopaudio) stopping jackd')
        Popen ('pkill -f jackd'.split(), stdout=fnull, stderr=fnull)


if __name__ == '__main__':

    run_level = 'all'
    if sys.argv[1:]:
        run_level = sys.argv[1]
    if run_level in {'core', 'clients', 'all'}:
        print('(stopaudio) stopping', run_level)
        main(run_level)
    else:
        print(__doc__)
