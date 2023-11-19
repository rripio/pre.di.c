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
                writer.write(b'\ncorrupted null state file')

    try:
        if data.rstrip('\r\n') == 'status':
            # echo state to client as YAML string
            writer.write(yaml.dump(init.state,
                                   default_flow_style=False).encode())
            await writer.drain()

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
            if init.config['verbose'] in {1, 2}:
                writer.write(b'\ncommand: ' + data.encode())
                await writer.drain()

            control.proccess_commands(data)

            writer.write(control.message.encode() + b'\n')
            await writer.drain()
            control.message = ''
            # a try block avoids blocking of state file writing \
            # when the terminal that launched startaudio.py is closed
            try:
                # writes state file
                write_state()
            except Exception as e:
                writer.write(b'ACK\n')
                writer.write(b'an error occurred when writing state file: '
                      + str(e).encode() + b'\n')
                await writer.drain()

    except ConnectionResetError:
        writer.write(b'ACK\n')
        writer.write(b'still no connection...\n')
        await writer.drain()
    except Exception as e:
        writer.write(b'ACK\n')
        writer.write(b'an exception occurred: ' + str(e).encode() + b'\n')
        await writer.drain()
    else:
        writer.write(b'OK\n')
        # error not understood. temporaly commented
        # await writer.drain()
    finally:
        writer.close()


async def main():

    server = await asyncio.start_server(
                handle_commands,
                init.config['control_address'],
                init.config['control_port']
                )
    addr = server.sockets[0].getsockname()
    if init.config['verbose'] in {1, 2}:
        print(f'\n(server) listening on address {addr}')
    await server.serve_forever()


asyncio.run(main())
