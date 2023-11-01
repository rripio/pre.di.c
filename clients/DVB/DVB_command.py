#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
selects DVB channels

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

# add main pre.di.c folder to module search path
# get script folder
folder = os.path.dirname(sys.argv[0])
# goes up two directories to get main predic folder
predic_dir = os.path.dirname(os.path.dirname(folder))
sys.path.append(predic_dir)

import pdlib as pd

# mute as soon as possible
pd.client_socket('mute on', quiet=True)


import time

import yaml

import init

# get config
config_filename = 'config.yml'
config = pd.get_yaml(f'{folder}/{config_filename}')

# paths
state_path = f'{folder}/{config["state_filename"]}'
presets_path = f'{folder}/{config["presets_filename"]}'
dvb_fifo = f'{folder}/{config["fifo_filename"]}'

# get dictionaries
state = pd.get_yaml(state_path)
presets = pd.get_yaml(presets_path)


def select_channel(channel_name, channel_gain):
    """
    sets channel in mplayer
    """

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
    """
    selects preset from presets.yml
    """

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
    """
    process channel options
    """

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
        print(
            f'\n(DVB_command)\noption must be in {options} '
            f'\nor be one of these integer presets: {presets}\n'
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
            selected_source = init.state['source']
            if selected_source == config['DVB_source']:
                tmax = init.config['command_delay'] * 10
                interval = init.config['command_delay'] * 0.1
                # wait for disconnection of previous channel
                time.sleep(init.config['command_delay'] * 0.5)
                # try to connect for newly connected ports
                if pd.wait4source(selected_source, tmax, interval):
                    # source ports up and ready :-)
                    # switch on source
                    pd.client_socket('sources on', quiet=True)
    else:
        state['actual'] = state_old['actual']
        state['previous'] = state_old['previous']
        print('(DVB_command) Something went wrong when changing radio state')

    # restore previous mute state
    pd.client_socket(f"mute {init.state['mute']}", quiet=True)

    # write state
    with open(state_path, 'w') as f:
        yaml.dump(state, f, default_flow_style=False)


if sys.argv[1:]:
    selected = sys.argv[1]
    if sys.argv[2:]:
        if sys.argv[2] == 'startaudio':
            startflag = True
        else:
            startflag = False
    else:
        startflag = False
    change_radio(selected, startflag)

else:
    print(__doc__)
