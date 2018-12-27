#!/usr/bin/env python3

# Copyright (c) 2018 Roberto Ripio, Rafael Sánchez
# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018 Roberto Ripio
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

""" A module interface that controls pre.di.c.
    This module is called from the listening server.
"""

import sys
import os
import yaml

import basepaths as bp
import server_process as sp
import getconfigs as gc
import predic as pd

def do(command):
    
    state = gc.state

    if gc.config['control_output'] > 1:
        if gc.config['control_clear']:
            # optional terminal clearing
            os.system('clear')
        else:
            # separator
             print('=' * 70)

    if command.rstrip('\r\n') == 'status':
        # Reads state file and sends it back
        # as YAML string
        result = yaml.dump(state, default_flow_style=False)

    else:
        # A command to be processed by server_process.py,
        # that answers with a state dict, and warnings if any:
        (state, warnings) = sp.proccess_commands(command, state)

        try:

            # Updates state file
            with open(bp.state_path, 'w') as f:
                yaml.dump(state, f, default_flow_style=False)

            # Print warnings
            if len(warnings) > 0:
                print("Warnings:")
                for warning in warnings:
                    print("\t", warning)
                result = 'ACK\n'
            else:
                result = 'OK\n'
        except:
            result = 'ACK\n'

    # It is expected to return bytes-like things
    return result.encode()
