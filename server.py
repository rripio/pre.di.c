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

import asyncio
import sys
import time
import os
import yaml

import control
import basepaths as bp
import getconfigs as gc
import predic as pd



async def handle_commands(reader, writer):

    state = gc.state
    rawdata = await reader.read(100)
    data = rawdata.decode()
    addr = writer.get_extra_info('peername')

    if data.rstrip('\r\n') == 'status':
        # echo state to client as YAML string
        writer.write(yaml.dump(state, default_flow_style=False).encode())
        writer.write(b'OK\n')
        await writer.drain()
    elif data.rstrip('\r\n') == 'quit':
        writer.write(b'OK\n')
        await writer.drain()
        if gc.config['server_output'] > 1:
            print('(server) closing connection...')
    elif data.rstrip('\r\n') == 'shutdown':
        writer.write(b'OK\n')
        await writer.drain()
        if gc.config['server_output'] > 1:
            print('(server) closing connection...')
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
                writer.write(b'ACK\n')
                await writer.drain()
            else:
                writer.write(b'OK\n')
                await writer.drain()
        except:
            writer.write(b'ACK\n')
            await writer.drain()

    writer.close()

async def main():

    server = await asyncio.start_server(
                handle_commands,
                gc.config['control_address'],
                gc.config['control_port'])
    addr = server.sockets[0].getsockname()
    if gc.config['server_output'] > 0:
        print(f"(server) listening on address {addr}")

#    async with server:
#        await server.serve_forever()
    try:
        await server.serve_forever()
    except SystemExit:
        print('(server) closing server...')
        raise
    finally:
        server.close()

asyncio.run(main())

