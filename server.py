#! /usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import asyncio

import yaml

import control
import init


async def handle_commands(reader, writer):

    rawdata = await reader.read(100)
    data = rawdata.decode()

    def write_state():
        """
        writes state to state file
        """

        with open(init.state_path, 'w') as f:
            if init.state is not None:
                yaml.dump(init.state, f, default_flow_style=False)
            else:
                print('\n(server) corrupted null state')

    try:
        if data.rstrip('\r\n') == 'status':
            # echo state to client as YAML string
            writer.write(yaml.dump(init.state,
                                   default_flow_style=False).encode())

        elif data.rstrip('\r\n') == 'save':
            # writes state to state file
            write_state()

        elif data.rstrip('\r\n') == 'ping':
            # just answers OK
            pass

        elif data.rstrip('\r\n') == 'command_unmute':
            # inhibits mute downstream
            init.config['do_mute'] = False

        elif data.rstrip('\r\n') == 'command_mute':
            # restore mute state downstream
            init.config['do_mute'] = True

        else:
            # command received in 'data', \
            # then send command to control.py

            control.proccess_commands(data)

            # this has to be after actual command sending
            # if not, command execution fails when changing terminal
            if init.config['verbose'] in [1, 2]:
                print(f'\n(server) command: {data}')
            # a try block avoids blocking of state file writing \
            # when the terminal that launched startaudio.py is closed
            try:
                # writes state file
                write_state()
            except Exception as e:
                print('\n(server) an error occurred when writing state file: ',
                      e)
    except ConnectionResetError:
        writer.write(b'ACK\n')
        print('\n(server) still no connection...')
    except Exception as e:
        writer.write(b'ACK\n')
        print('\n(server) an exception occurred: ', e)
    else:
        writer.write(b'OK\n')
        await writer.drain()
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
        print(f'\n(server) listening on address {addr}')
    await server.serve_forever()


asyncio.run(main())
