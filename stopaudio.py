#! /usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (C) 2006-2011 Roberto Ripio
# Copyright (C) 2011-2016 Alberto Miguélez
# Copyright (C) 2016-2018 Rafael Sánchez
#
# pre.di.c is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pre.di.c is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pre.di.c.  If not, see <https://www.gnu.org/licenses/>.

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

import base
import getconfigs as gc
import predic as pd


fnull = open(os.devnull, 'w')


def main(run_level):
    """main stop function"""

    if run_level in ['clients', 'all']:
        # stop external scripts, sources and clients
        print('(stopaudio) stopping clients')
        clients_stop = pd.read_clients('stop')
        for command in clients_stop:
            try:
                Popen(f'{base.clients_folder}{command}'.split())
            except Exception:
                print(f'problem stopping client "{client}":\n\t{err}')
    if run_level in ['core', 'all']:
        # controlserver
        print('(stopaudio) stopping server')
        Popen ('pkill -f server.py'.split(), stdout=fnull, stderr=fnull)
        # brutefir
        print('(stopaudio) stopping brutefir')
        Popen ('pkill -f brutefir'.split(), stdout=fnull, stderr=fnull)
        # jack
        print('(stopaudio) stopping jackd')
        Popen ('pkill -f jackd'.split(), stdout=fnull, stderr=fnull)


if __name__ == '__main__':

    run_level = 'all'
    if sys.argv[1:]:
        run_level = sys.argv[1]
    if run_level in ['core', 'clients', 'all']:
        print('(stopaudio) stopping', run_level)
        main(run_level)
    else:
        print(__doc__)
