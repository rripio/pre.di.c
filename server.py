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

import socket
import sys
import time
import os
import yaml

import control
import basepaths as bp
import getconfigs as gc
import predic as pd


state = gc.state
fsocket = pd.server_socket(gc.config['control_address']
                        , gc.config['control_port'])
# main loop to proccess conections
# number of connections in queue
backlog = 10
while True:
    # listen ports
    fsocket.listen(backlog)
    if gc.config['server_output'] > 1:
        print('(server) listening on address '
                f"{gc.config['control_address']}"
                f", port{gc.config['control_port']}...")
    # accept client connection
    sc, addr = fsocket.accept()
    # somo info
    if gc.config['server_output'] > 1:
        if gc.config['server_clear']:
            # optional terminal clearing
            os.system('clear')
        else:
            # separator
             print('=' * 70)
        print(f'(server) connected to client {addr[0]}')
    # buffer loop to proccess received command
    while True:
    # reception
        data = sc.recv(4096).decode()
        if not data:
            # nothing in buffer, client has disconnected too soon
            if gc.config['server_output'] > 1:
                print('(server) client disconnected. '
                                       'Closing connection...')
            sc.close()
            break
        elif data.rstrip('\r\n') == 'status':
            # echo state to client as YAML string
            sc.send(yaml.dump(state,
                                default_flow_style=False).encode())
            sc.send(b'OK\n')
        elif data.rstrip('\r\n') == 'quit':
            sc.send(b'OK\n')
            if gc.config['server_output'] > 1:
                print('(server) closing connection...')
            sc.close()
            break
        elif data.rstrip('\r\n') == 'shutdown':
            sc.send(b'OK\n')
            if gc.config['server_output'] > 1:
                print('(server) closing connection...')
            sc.close()
            fsocket.close()
            sys.exit(1)
        else:
            # command received in 'data',
            # then send command to control.py,
            # that answers with state dict
            (state, warnings) = (control.proccess_commands
                                            (data, state))
            # writes state file
            try:
                with open(bp.state_path, 'w') as f:
                    yaml.dump(state, f, default_flow_style=False)
            # print warnings
                if len(warnings) > 0:
                    print("Warnings:")
                    for warning in warnings:
                        print("\t", warning)
                    sc.send(b'ACK\n')
                else:
                    sc.send(b'OK\n')
            except:
                sc.send(b'ACK\n')
            if gc.config['server_output'] > 1:
                print(f'(server) connected to client {addr[0]}')
        # wait a bit, loop again
        time.sleep(0.01 * gc.config['command_delay'])


