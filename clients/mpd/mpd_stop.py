# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Kill mpd and start script."""

import os

import init
import pdlib as pd
import subprocess as sp


# user config
config_filename = 'config.yml'

dir = os.path.dirname(os.path.realpath(__file__))
mpd_conf = pd.read_yaml(f'{dir}/{config_filename}')

delay = init.config['command_delay']
sp.Popen(mpd_conf["mpd_stop_command"].split())
sp.Popen((f'pkill -f {dir}/mpd_start.py').split())
