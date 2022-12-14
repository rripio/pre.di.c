#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""selects DVB channels

    Usage: DVB_command.py [preset [startaudio]]

    preset must be one of the integer presets in presets.yml or one of
    these options: 'forth', 'back', 'last', 'previous'

    forth:      next preset number in numerical order
    back:       previous preset number in numerical order
    last:       last played preset
    previous:   preset played before last

    The 'startaudio' flag omits jack connection when switching channels
    for use when launching DVB client on pre.di.c start"""


import sys
import os
import time

import yaml

import init
import predic as pd


# where am I? here you have all files
folder = f'{os.path.dirname(sys.argv[0])}/'

# get config
config_filename = 'config.yml'
config = init.get_yaml(folder + config_filename)

# paths
state_path = folder + config["state_filename"]
presets_path = folder + config["presets_filename"]
dvb_fifo = folder + config["fifo_filename"]

# get dictionaries
state = init.get_yaml(state_path)
presets = init.get_yaml(presets_path)

def select_channel(channel_name, channel_gain):
    """ sets channel in mplayer """

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
    except:
        return False


def select_preset(preset, preset_dict=presets):
    """ selects preset from presets.yml """

    # get channel name from preset number
    if preset.isdigit():
        preset = int(preset)
        if preset in preset_dict:
            channel_name = preset_dict[preset]["name"].replace(' ','\ ')
            channel_level = preset_dict[preset]["gain"]
        else:
            return False
        if channel_name:
            # set channel in mplayer
            if select_channel(channel_name, channel_level):
                return True
    return False


def change_radio(
    selected, startflag = False, preset_dict=presets, state=state):
    """ process channel options """

    # list of presets, discarding those white in presets.yml
    state_old = state
    presets = list(map(str,sorted(
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
    elif not selected in presets:
        print(
            f'(DVB_command) option must be in {options} '
            'or be an existing integer preset'
            )
        return
    # actual channel switch
    if select_preset(selected):
        if selected != state['actual']:
            state['previous'] = state['actual']
        state['actual'] = selected
        # if starting predic give startaudio command on source switching
        if not startflag:
            # check selected source and reconnect to DVB if selected
            selected_source = pd.read_state()['source']
            if config['DVB_source'] == selected_source:
                tmax = init.config['command_delay'] * 10
                interval = init.config['command_delay'] * 0.1
                # wait for disconnection of previous channel
                time.sleep(init.config['command_delay'])
                # try to connect for newly connected ports
                if pd.wait4source(selected_source, tmax, interval):
                    # source ports up and ready :-)
                    # switch on source
                    pd.client_socket('source ' + selected_source, quiet=True)
    else:
        state['actual'] = state_old['actual']
        state['previous'] = state_old['previous']
        print('(DVB_command) Something went wrong when changing radio state')
    # write state
    with open(state_path, 'w') as f:
        yaml.dump(state, f, default_flow_style=False)


if sys.argv[1:]:
    selected = sys.argv[1]
    if sys.argv[2:]:
        startflag = sys.argv[2]
        if startflag == 'startaudio':
            startflag = True
        else:
            startflag = False
    else:
        startflag = False
    change_radio(selected, startflag)

else:
    print(__doc__)
