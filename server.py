#! /usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import asyncio

import yaml

import control
import init


async def handle_commands(reader, writer):

    state = init.state
    rawdata = await reader.read(100)
    data = rawdata.decode()
    addr = writer.get_extra_info('peername')

    def write_state(state):
        """writes state to state file"""

        with open(init.state_path, 'w') as f:
            yaml.dump(state, f, default_flow_style=False)


    try:
        if data.rstrip('\r\n') == 'status':
            # echo state to client as YAML string
            writer.write(yaml.dump(state, default_flow_style=False).encode())
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['verbose'] == 2:
                print('(server) closing connection...')

        elif data.rstrip('\r\n') == 'save':
            # writes state to state file
            write_state(state)
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['verbose'] == 2:
                print('(server) closing connection...')

        elif data.rstrip('\r\n') == 'ping':
            # just answers OK
            writer.write(b'OK\n')
            await writer.drain()
            if init.config['verbose'] == 2:
                print('(server) closing connection...')

        else:
            # command received in 'data', \
            # then send command to control.py, \
            # that answers with state dict
            (state) = control.proccess_commands(data, state)
            # a try block avoids blocking of state file writing \
            # when the terminal that launched startaudio.py is closed
            try:
                if init.config['verbose'] in [1, 2]:
                    print(f'Command: {data}')
            except Exception as e:
                print(f'(server) Exception: {e}')

            try:
                # writes state file
                write_state(state)
                writer.write(b'OK\n')
                await writer.drain()
            except Exception as e:
                print('An error occurred when writing state file: ', e)
    except ConnectionResetError:
        print('(server) still no connection...')
    except Exception as e:
        print('(server) An exception occurred: ', e)
    finally:
        writer.close()


async def main():

    server = await asyncio.start_server(
                handle_commands,
                init.config['control_address'],
                init.config['control_port']
                )
    addr = server.sockets[0].getsockname()
    if init.config['verbose'] in [1, 2]:
        print(f'(server) listening on address {addr}')
    await server.serve_forever()


asyncio.run(main())
