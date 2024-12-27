# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Kill mplayer, DVB_server.py and start script."""


import os
import sys
import subprocess as sp

import init
import pdlib as pd


# get config
folder = os.path.dirname(sys.argv[0])
config_filename = 'config.yml'
config = pd.read_yaml(f'{folder}/{config_filename}')
dvb_fifo = f'{folder}/{config["fifo_filename"]}'

delay = init.config['command_delay'] * 5

dir = os.path.dirname(os.path.realpath(__file__))
sp.Popen(f'{config["stop_command"]}'.split())
sp.Popen(f'pkill -f {dir}/DVB_server.py'.split())
sp.Popen(f'pkill -f {dir}/DVB_start.py'.split())
