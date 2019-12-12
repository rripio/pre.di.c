#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (c) 2006-2011 Roberto Ripio
# Copyright (c) 2011-2016 Alberto Miguélez
# Copyright (c) 2016-2018 Rafael Sánchez
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

"""selects DVB channels
Usage: DVB_command.py [preset ['startaudio']]

The 'startaudio' flag omit jack connection when switching channels
for use when launchong DVB client on pre.di.c start"""


import sys
import os
import time

import yaml

import getconfigs as gc
import predic as pd


# where am I? here you have all files
folder = f'{os.path.dirname(sys.argv[0])}/'

# get config
config_filename = 'config.yml'
config = gc.get_yaml(folder + config_filename)

# paths
state_path = folder + config["state_filename"]
presets_path = folder + config["presets_filename"]
dvb_fifo = folder + config["fifo_filename"]

# get dictionaries
state = gc.get_yaml(state_path)
presets = gc.get_yaml(presets_path)

def select_channel(channel_name, channel_gain):
    """ sets channel in mplayer """

    try:
        command = (f"loadfile dvb://{channel_name}\n"
                    f"af_cmdline volume {channel_gain}\n"
                    'get_property volume\n')
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


def change_radio(selected, startflag = False,
                                        preset_dict=presets, state=state):
    """ process channel options """

    # list of presets, discarding those white in presets.yml
    state_old = state
    presets = sorted(
            [str(preset) for preset in preset_dict if preset_dict[preset]])
    # command arguments
    options = ['next', 'prev', 'restore', 'back']
    if selected in options:
        # 'next|prev' to walk through preset list
        if selected == 'next':
            selected = presets[ (presets.index(state['actual']) + 1)
                                                            % len(presets) ]
        elif selected == 'prev':
            selected = presets[ (presets.index(state['actual']) - 1)
                                                            % len(presets) ]
        # last used preset, that is, 'actual':
        elif selected == 'restore':
            selected = state['actual']
        # previously used preset, that is, 'previous':
        elif selected == 'back':
            selected = state['previous']
    # direct preset selection
    elif not selected in presets:
        print(f'(DVB_command) option must be in {options} or be an '
                                                         'integer preset')
        return
    # actual canal switch
    if select_preset(selected):
        if selected != state['actual']:
            state['previous'] = state['actual']
        state['actual'] = selected
        # if starting predic give startaudio command on input switching
        if not startflag:
            # check selected input and reconnect to DVB if selected
            selected_input = pd.read_state()['input']
            if config['DVB_input'] == selected_input:
                tmax = gc.config['command_delay'] * 10
                interval = gc.config['command_delay'] * 0.1
                # wait for disconnection of previous channel
                time.sleep(gc.config['command_delay'])
                # try to connect for newly connected ports
                if pd.wait4source(selected_input, tmax, interval):
                    # input ports up and ready :-)
                    # switch on input
                    pd.client_socket('input ' + selected_input, quiet=True)
    else:
        state['actual'] = state_old['actual']
        state['previous'] = state_old['previous']
        print('(DVB_command) Something went wrong '
                                    'when changing radio state')
    return state


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
    new_state = change_radio(selected, startflag)

    with open(state_path, 'w') as f:
        yaml.dump(new_state, f, default_flow_style=False)
else:
    print(__doc__)
