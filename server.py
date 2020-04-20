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

import yaml

import base
import control
import init


async def handle_commands(reader, writer):

    state = init.state
    rawdata = await reader.read(100)
    data = rawdata.decode()
    addr = writer.get_extra_info('peername')

    def write_state(state):
        """writes state to state file"""

        with open(base.state_path, 'w') as f:
            yaml.dump(state, f, default_flow_style=False)


    try:
        if data.rstrip('\r\n') == 'status':
            # echo state to client as YAML string
            writer.write(yaml.dump(state, default_flow_style=False).encode())
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['server_output'] == 2:
                print('(server) closing connection...')

        elif data.rstrip('\r\n') == 'save':
            # writes state to state file
            write_state(state)
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['server_output'] == 2:
                print('(server) closing connection...')

        elif data.rstrip('\r\n') == 'ping':
            # just answers OK
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['server_output'] == 2:
                print('(server) closing connection...')

        else:
            # command received in 'data', \
            # then send command to control.py, \
            # that answers with state dict
            (state, warnings) = control.proccess_commands(data, state)
            # a try block avoids blocking of state file writing \
            # when the terminal that launched startaudio.py is closed
            try:
                if init.config['server_output'] in [1, 2]:
                    print(f'Command: {data}')
            except Exception:
                pass

            try:
                # writes state file
                write_state(state)
                # print warnings
                if len(warnings) > 0:
                    print('Warnings:')
                    for warning in warnings:
                        print('\t', warning)
                    writer.write(b'ACK\n')
                    await writer.drain()
                else:
                    writer.write(b'OK\n')
                    await writer.drain()
            except Exception:
                writer.write(b'ACK\n')
                await writer.drain()
    except ConnectionResetError:
        print('(server) still no connection...')
    except Exception:
        print('(server) An exception occured...')
    finally:
        writer.close()


async def main():

    server = await asyncio.start_server(
                handle_commands,
                init.config['control_address'],
                init.config['control_port']
                )
    addr = server.sockets[0].getsockname()
    if init.config['server_output'] in [1, 2]:
        print(f'(server) listening on address {addr}')
    await server.serve_forever()


asyncio.run(main())
