#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
start and stop mplayer for DVB tasks

use it with 'start' and 'stop' as options
"""


import os
import sys
import time
import subprocess as sp

import init
import pdlib as pd


# initialize

# get config
folder = os.path.dirname(sys.argv[0])
config_filename = 'config.yml'
config = pd.get_yaml(f'{folder}/{config_filename}')
dvb_fifo = f'{folder}/{config["fifo_filename"]}'

delay = init.config['command_delay'] * 5


def start():
    """
    loads mplayer and DVB_server.py
    """

    # starts mplayer DVB:
    command = f'{config["start_command"]} -input file={dvb_fifo}'
    print('\n(DVB_load) starting mplayer')
    sp.Popen(command.split())

    # starts DVB_server.py
    
    print('\n(DVB_load) starting DVB server')
    sp.Popen(f'{folder}/DVB_server.py')

    time.sleep(delay)
    if config["play_on_start"]:
        print('\n(DVB_load) starting DVB play')
        pd.client_socket(f'{config["preset"]} startaudio',
                         config["control_port"])


def stop():
    """
    kills mplayer, DVB_server.py and this script
    """

    dir = os.path.dirname(os.path.realpath(__file__))
    sp.Popen(f'{config["stop_command"]}'.split())
    sp.Popen(f'pkill -f {dir}/DVB_server.py'.split())
    sp.Popen(f'pkill -f {dir}/DVB_load.py'.split())


if sys.argv[1:]:
    try:
        option = {
            'start': start,
            'stop': stop
            }[sys.argv[1]]()
    except KeyError:
        print('\n(DVB_load) bad option')
else:
    print(__doc__)
