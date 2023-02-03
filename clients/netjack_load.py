#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
start netjack
"""

import time
from subprocess import Popen


## user configuration

netjack_path = '/usr/bin/jack_load netmanager'


print('\n(netjack_load.py) starting netjack\n')
Popen(netjack_path.split())

