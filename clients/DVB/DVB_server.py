# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
selects DVB channels.

Usage: DVB_command.py [preset [startaudio]]

preset must be one of the integer presets in presets.yml or one of
these options: 'forth', 'back', 'last', 'previous'

forth:      next preset number in numerical order
back:       previous preset number in numerical order
last:       last played preset
previous:   preset played before last

The 'startaudio' flag omits jack connection when switching channels
for use when launching DVB client on pre.di.c start
"""


import sys
import os
import time
import asyncio

import yaml

import init
import pdlib as pd


# get config
folder = os.path.dirname(sys.argv[0])
config_filename = 'config.yml'
config = pd.read_yaml(f'{folder}/{config_filename}')

# paths
state_path = f'{folder}/{config["state_filename"]}'
presets_path = f'{folder}/{config["presets_filename"]}'
dvb_fifo = f'{folder}/{config["fifo_filename"]}'

# get dictionaries
state = pd.read_yaml(state_path)
presets = pd.read_yaml(presets_path)

port = config['control_port']


async def handle_commands(reader, writer):
    """Read command data."""
    rawdata = await reader.read(100)
    data = rawdata.decode().rstrip('\r\n').split()

    def select_channel(channel_name, channel_gain):
        """Set channel in mplayer."""
        try:
            command = (
                f"stop\n"
                f"loadfile dvb://{channel_name}\n"
                f"af_cmdline volume {channel_gain}\n"
                'get_property volume\n'
                )
            with open(dvb_fifo, 'w') as f:
                f.write(command)
            return True
        except Exception:
            return False

    def select_preset(preset, preset_dict=presets):
        """Select preset from presets.yml."""
        # get channel name from preset number
        if preset.isdigit():
            preset = int(preset)
            if preset in preset_dict:
                channel_name = preset_dict[preset]["name"].replace(' ', r'\ ')
                channel_level = preset_dict[preset]["gain"]
            else:
                return False
            if channel_name:
                # set channel in mplayer
                if select_channel(channel_name, channel_level):
                    return True
        return False

    def change_radio(
            selected, startflag=False, preset_dict=presets, state=state):
        """Process channel options."""
        # list of presets, discarding those white in presets.yml
        state_old = state
        presets = list(map(str, sorted(
                [preset for preset in preset_dict if preset_dict[preset]]
                )))
        # command arguments
        options = ['forth', 'back', 'last', 'previous']
        if selected in options:
            # 'forth|back' to walk through preset list
            if selected == 'forth':
                selected = presets[
                    (presets.index(state['actual']) + 1) % len(presets)
                    ]
            elif selected == 'back':
                selected = presets[
                    (presets.index(state['actual']) - 1) % len(presets)
                    ]
            # last used preset, that is, 'actual':
            elif selected == 'last':
                selected = state['actual']
            # previously used preset, that is, 'previous':
            elif selected == 'previous':
                selected = state['previous']
        # wrong preset selection
        elif selected not in presets:
            writer.write(
                f'\n(DVB_command)\noption must be in {options} '.encode() +
                f'\nor be one of these integer presets: \n{presets}\n'.encode()
                )
            return
        # actual channel switch

        if select_preset(selected):
            if selected != state['actual']:
                state['previous'] = state['actual']
            state['actual'] = selected
            # if starting predic 'startaudio.py'  makes actual switching
            if not startflag:
                # check selected source and reconnect to DVB if selected
                selected_source = pd.get_state()['source']
                if selected_source == config['DVB_source_name']:
                    tmax = init.config['command_delay'] * 10
                    interval = init.config['command_delay'] * 0.1
                    # wait for disconnection of previous channel
                    time.sleep(init.config['command_delay'] * 0.5)
                    # try to connect for newly connected ports
                    if pd.wait4source(selected_source, tmax, interval):
                        # source ports up and ready :-)
                        # switch on source
                        pd.client_socket('sources on',
                                         init.config['control_port'],
                                         quiet=True)

        else:
            state['actual'] = state_old['actual']
            state['previous'] = state_old['previous']
            writer.write(
               b'(DVB_command) Something went wrong when changing radio state')

        # write state
        with open(state_path, 'w') as f:
            yaml.dump(state, f, default_flow_style=False)

    if data[0:]:

        if data[0] == 'help':
            writer.write(__doc__.encode())

        else:
            if data[1:]:
                if data[1] == 'startaudio':
                    startflag = True
                else:
                    startflag = False
            else:
                startflag = False

            change_radio(data[0], startflag)

    await writer.drain()
    writer.close()


async def main():
    """Start funcion."""
    server = await asyncio.start_server(
                handle_commands,
                config['control_address'],
                config['control_port']
                )
    addr = server.sockets[0].getsockname()
    if init.config['verbose'] in {1, 2}:
        print(f'\n(DVB_server) listening on address {addr}')
    await server.serve_forever()


asyncio.run(main())
