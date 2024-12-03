# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
loads mplayer and DVB_server.py
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
config = pd.read_yaml(f'{folder}/{config_filename}')
dvb_fifo = f'{folder}/{config["fifo_filename"]}'

delay = init.config['command_delay'] * 5


# starts mplayer DVB:
command = f'{config["start_command"]} -input file={dvb_fifo}'
print('\n(DVB_load) starting mplayer')
sp.Popen(command.split())

# starts DVB_server.py

print('\n(DVB_load) starting DVB server')
sp.Popen(f'{init.config["python_command"]} {folder}/DVB_server.py'.split())

time.sleep(delay)
if config["play_on_start"]:
    print('\n(DVB_load) starting DVB play')
    pd.client_socket(f'{config["preset"]} startaudio',
                        config["control_port"])
