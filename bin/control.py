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

""" A module interface that controls pre.di.c and  
    prints out information to the running terminal.
    This module is called from the listening server.
    This module uses 'server_process' that is the true pre.di.c controller.
"""

import sys
import os
import yaml

import basepaths
import getconfigs
import server_process

def do(command):
    """ Returns:
        - 'OK' if the command was succesfully processed.
        - 'ACK' if not.
        - The state dictionary is command = 'status'
    """
    
    # terminal print out behavior
    if getconfigs.config['control_output'] > 1:
        if getconfigs.config['control_clear']:
            # optional terminal clearing
            os.system('clear')
        else:
            # separator
             print('=' * 70)

    # server_process.py will need to know the current status when querying to do something
    state = getconfigs.state
    result = ''

    # 'status' will read the state file and send it back as an YAML string
    if command.rstrip('\r\n') == 'status':
        result = yaml.dump(state, default_flow_style=False)

    # Any else command will be processed by the 'server_process' module,
    # that answers with a state dict, and warnings if any:
    else:
        (state, warnings) = server_process.proccess_commands(command, state)

        try:
            # Updates state file
            with open(basepaths.state_path, 'w') as f:
                yaml.dump(state, f, default_flow_style=False)

            # Prints warnings
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
