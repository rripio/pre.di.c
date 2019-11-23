#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (c) 2006-2011 Roberto Ripio
# Copyright (c) 2011-2016 Alberto Miguélez
# Copyright (c) 2016-2018 Rafael Sánchez
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

"""start and stop mplayer for DVB tasks
use it with 'start' and 'stop' as options"""


import sys
import os
import subprocess as sp
import multiprocessing as mp

import getconfigs as gc
import predic as pd


# initialize

# filenames
config_filename = 'config.yml'

# get program folder for subsequent aux files finding
# allways put a slash after directories
folder = f'{os.path.dirname(sys.argv[0])}/'

# get config
config = gc.get_yaml(folder + config_filename)


def start():
    """loads mplayer and jack loop"""

    # create jack loop for connections
    # The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = mp.Process( target = pd.jack_loop, args=('dvb_loop',) )
    jloop.start()

    # starts mplayer DVB:
    dvb_fifo = folder + config["fifo_filename"]
    command = f'{config["start_command"]} -input file={dvb_fifo}'
    sp.Popen(command.split())


def stop():
    """kills mplayer and this script"""

    dir = os.path.dirname(os.path.realpath(__file__))
    sp.Popen(f'{config["stop_command"]}'.split())
    sp.Popen(f'pkill -f {dir}/DVB_load.py'.split())


if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('DVB.py: bad option')
else:
    print(__doc__)

