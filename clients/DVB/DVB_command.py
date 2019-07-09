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

"""selects DVB channels"""


import sys
import os

import yaml

import getconfigs as gc
import predic as pd


# filenames
dvb_fifo_filename = 'DVB_fifo'
state_filename = 'state.yml'
presets_filename = 'presets.yml'
# get program folder for subsequent aux files finding
# allways put a slash after directories
folder = f'{os.path.dirname(sys.argv[0])}/'
# configs paths
state_path = folder + state_filename
presets_path = folder + presets_filename
# get dictionaries
state = gc.get_yaml(state_path)
presets = gc.get_yaml(presets_path)
# get command fifo name
dvb_fifo = folder + dvb_fifo_filename


def select_channel(channel_name):
    """ sets channel in mplayer """

    try:
        command = ('loadfile dvb://' + channel_name + '\n')
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
            channel_name = preset_dict[preset].replace(' ','\ ')
        else:
            return False
        if channel_name:
            # set channel in mplayer
            if select_channel(channel_name):
                return True
    return False


def change_radio(selected, preset_dict=presets, state=state):
    """ process channel options """

    # list of presets, discarding those white in presets.yml
    state_old = state
    presets = sorted(
            [str(preset) for preset in preset_dict if preset_dict[preset]]
            )
    # command arguments
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
    if select_preset(selected):
        if selected != state['actual']:
            state['previous'] = state['actual']
        state['actual'] = selected
    else:
        state['actual'] = state_old['actual']
        state['previous'] = state_old['previous']
        print('(DVB_command) Something went wrong '
                                    'when changing radio state')
    return state


if sys.argv[1:]:
    new_state = change_radio(sys.argv[1])
    with open(state_path, 'w') as f:
        yaml.dump(new_state, f, default_flow_style=False)
else:
    print(__doc__)
