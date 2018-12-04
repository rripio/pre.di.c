#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018 Roberto Ripio
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

"""start and stop mplayer for DVB tasks
use it with 'start' and 'stop' as options"""

import sys
import os
import time
from subprocess import Popen
import threading

import basepaths as bp
import getconfigs as gc
import predic as pd

## mplayer aditional options

# -quiet: see channels change
# -really-quiet: silent
options = '-quiet -nolirc'
# command fifo filename
dvb_fifo = 'dvb_fifo'
# mplayer path:
mplayer_path = '/usr/bin/mplayer'
# name used for info and pid saving
program_alias = 'mplayer-dvb'

# initialize
dvb_fifo = bp.main_folder + dvb_fifo


def select_channel(channel_name):
    """ sets channel in mplayer """

    try:
        command = ('loadfile dvb://' + channel_name + '\n')
        with open(bp.main_folder + gc.config['mplayer_dvb_fifo'], 'w') as f:
            f.write(command)
        return True
    except:
        return False


def select_preset(preset):
    """ selects preset from DVB-t.ini """

    # get channel name from preset number
    if preset.isdigit():
        preset = int(preset)
        if preset in gc.channels['presets']:
            channel_name = gc.channels['presets'][preset].replace(' ','\ ')
        else:
            return False
        if channel_name != '':
            # set channel in mplayer
            if select_channel(channel_name):
                return True
    return False

"""
def change_radio(new_radiopreset, state=state):

    # list of defined presets, discarding those white in DVB-t.ini
    ldp = [ preset for preset in gc.channels['presets'] if preset ]
    # command arguments
    # 'next|prev' to walk through preset list
    if new_radiopreset == 'next':
        new_radiopreset = ldp[ (ldp.index(state['radio']) + 1)
                                % len(ldp) ]
    elif new_radiopreset == 'prev':
        new_radiopreset = ldp[ (ldp.index(state['radio']) - 1)
                                % len(ldp) ]
    # last used preset, that is, 'radio':
    elif new_radiopreset == 'restore':
        new_radiopreset = state['radio']
    #previously used preset, that is, 'radio_prev':
    elif new_radiopreset == 'back':
        new_radiopreset = state['radio_prev']
    # direct preset selection
    if select_preset(new_radiopreset):
        if new_radiopreset != state['radio']:
            state['radio_prev'] = state['radio']
        state['radio'] = new_radiopreset
    else:
        state['radio'] = state_old['radio']
        state['radio_prev'] = state_old['radio_prev']
        warnings.append('Something went wrong when changing radio state')
    return state
"""

def start():

    # 1. Prepare a jack loop where MPLAYER outputs can connect.
    #    The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = threading.Thread( target = pd.jack_loop, args=('dvb_loop',) )
    jloop.start()


    # 2. Mplayer DVB:
    opts = f'{options} -idle -slave -profile dvb -input file={dvb_fifo}'
    command = f'{mplayer_path} {opts}'
    pd.start_pid(command, program_alias)


def stop():

    pd.kill_pid(program_alias)

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('DVB.py: bad option')
else:
    print(__doc__)

