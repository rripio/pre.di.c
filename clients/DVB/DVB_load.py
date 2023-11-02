#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
start and stop mplayer for DVB tasks

use it with 'start' and 'stop' as options
"""


import sys
import os
import subprocess as sp

import pdlib as pd


# initialize

# get config
folder = os.path.dirname(sys.argv[0])
config_filename = 'config.yml'
config = pd.get_yaml(f'{folder}/{config_filename}')
dvb_fifo = f'{folder}/{config["fifo_filename"]}'


def start():
    """
    loads mplayer
    """

    # starts mplayer DVB:
    command = f'{config["start_command"]} -input file={dvb_fifo}'
    print('\n(DVB_load.py) starting DVB')
    sp.Popen(command.split())
    if config["play_on_start"]:
        sp.Popen(
            f'{folder}/DVB_command.py {config["preset"]} startaudio'.split()
            )


def stop():
    """
    kills mplayer and this script
    """

    dir = os.path.dirname(os.path.realpath(__file__))
    sp.Popen(f'{config["stop_command"]}'.split())
    sp.Popen(f'pkill -f {dir}/DVB_load.py'.split())


if sys.argv[1:]:
    try:
        option = {
            'start': start,
            'stop': stop
            }[sys.argv[1]]()
    except KeyError:
        print('\n(DVB_load.py) bad option')
else:
    print(__doc__)
