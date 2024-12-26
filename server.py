# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Server to process commands."""

import asyncio

import yaml

import control
import init
import pdlib as pd


async def handle_commands(reader, writer):
    """Async process to handle commands."""
    rawdata = await reader.read(100)
    data = rawdata.decode().rstrip('\r\n')
    say_OK = True

    def write_state():
        """Write state to state file."""
        with open(init.state_path, 'w') as f:
            if init.state is not None:
                yaml.dump(init.state, f, default_flow_style=False)
            else:
                raise Exception('corrupted null state file\n')

    def write_camillaconfig():
        """Write camilladsp config to file in loudspeaker folder."""
        camillaconfig = init.loudspeaker_path + '/actual_config.yaml'
        with open(camillaconfig, 'w') as f:
            yaml.dump(control.cdsp_config, f, default_flow_style=False)

    try:
        if data == 'status':
            # Echo state to client as YAML string
            writer.write(yaml.dump(init.state,
                                   default_flow_style=False).encode())

        elif data == 'save':
            # Write state to state file
            write_state()

        elif data == 'camillaconfig':
            # Write camilladsp config to file
            write_camillaconfig()

        elif data == 'ping':
            # just answers OK
            pass

        elif data == 'command_unmute':
            # Inhibit mute downstream
            init.config['do_mute'] = False

        elif data == 'command_mute':
            # Restore mute state downstream
            init.config['do_mute'] = True

        elif data == 'show':
            # Print human readable status
            say_OK = False
            writer.write(pd.show().encode())

        elif data == 'help':
            # Print command help
            say_OK = False
            writer.write(pd.help_str.encode())

        else:
            # command received in 'data', \
            # then send command to control.py
            if init.config['verbose'] in {1, 2}:
                writer.write(b'\ncommand: ' + data.encode())

            if not control.proccess_commands(data):
                raise Exception(control.message)

            writer.write(b'\n' + control.message.encode())
            # a try block avoids blocking of state file writing \
            # when the terminal that launched startaudio.py is closed
            try:
                # writes state file
                write_state()
            except Exception as e:
                writer.write(b'\nan error occurred when writing state file: '
                             + str(e).encode())
                writer.write(b'\nACK')

    except Exception as e:
        writer.write(b'\n' + str(e).encode())
        writer.write(b'\nACK')
    else:
        if say_OK:
            writer.write(b'\nOK')
    finally:
        try:
            await writer.drain()
        except ConnectionResetError:
            writer.write(b'\nstill no connection...')
            writer.write(b'\nACK')
        control.message = ''
        writer.close()


async def main():
    """Start server."""
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
