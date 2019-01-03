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

"""
    Starts and stops Mplayer for DVB-T playback.

    Also used to change on the fly the played stream.

    DVB-T tuned channels are ussually stored at
        ~/.mplayer/channels.conf

    User presets can be configured into:
        config/DVB-T.yml

    Use:   DVB.py       start  [ <preset_num> | <channel_name> ]
                        stop
                        preset <preset_num>
                        name   <channel_name>
"""

import os
HOME = os.path.expanduser("~")

import sys
import time
import subprocess as sp
import threading
import yaml

import basepaths as bp
import getconfigs as gc
import predic as pd

##################
# Script settings:
##################
# DEFAULT PRESET number:
default_preset = '2'
# PRESETS FILE for internet streams / stations:
presets_fname = bp.config_folder + 'DVB-T.yml'
# Name used from pre.di.c. for info and pid saving
program_alias = 'mplayer-dvb'
# Mplayer DVB-T tuner file
tuner_file = f'{HOME}/.mplayer/channels.conf'

############################
# Mplayer options:
############################
# -quiet: see channels change
# -really-quiet: silent
options = '-quiet -nolirc'
# Mplayer input commands fifo filename
input_fifo = f'{bp.main_folder}/dvb_fifo'
# Mplayer path:
mplayer_path = '/usr/bin/mplayer'
# Mplayer outputs redirected to:
mplayer_redirection_path = f'{bp.main_folder}/.dvb_events'

def select_by_name(channel_name):
    """ loads a stream by its preset name """

    try:
        # check_output will fail if no command output
        sp.check_output( ['grep', channel_name, tuner_file] ).decode()
    except:
        print( f'(scripts/DVB.py) Channel NOT found: \'{channel_name}\'' )
        return False

    try:
        print( f'(scripts/DVB.py) trying to load \'{channel_name}\'' )
        channel_name = channel_name.replace(" ", "\\ ")
        command = ('loadfile dvb://' + channel_name + '\n' )
        f = open( input_fifo, 'w')
        f.write(command)
        f.close()
        return True
    except:
        return False

def select_by_preset(preset_num):
    """ loads a stream by its preset number """
    try:
        channel_name = presets[ int(preset_num) ]
        select_by_name(channel_name)
        return True
    except:
        print( f'(scripts/DVB.py) error in preset # {preset_num}' )
        return False

def start():
    # 1. Prepare a jack loop where MPLAYER outputs can connect.
    #    The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = threading.Thread( target = pd.jack_loop, args=('dvb_loop',) )
    jloop.start()
    # 2. Mplayer DVB:
    opts = f'{options} -idle -slave -profile dvb -input file={input_fifo}'
    command = f'{mplayer_path} {opts}'
    with open(mplayer_redirection_path, 'w') as redir:
        pd.start_pid(command, program_alias, redir)

def stop():
    pd.kill_pid(program_alias)
    # harakiri
    sp.Popen( ['pkill', '-KILL', '-f', 'profile dvb'] )
    sp.Popen( ['pkill', '-KILL', '-f', 'DVB.py start'] )


if __name__ == '__main__':

    ### Reading the presets stations file
    presets = {}
    f = open(presets_fname, 'r')
    tmp = f.read()
    f.close()
    try:
        presets = yaml.load(tmp)
    except:
        print ( '(scripts/DVB.py) YAML error into ' + presets_fname )

    ### Reading the command line
    if sys.argv[1:]:

        opc = sys.argv[1]

        # STARTS the script and optionally load a preset/name
        if opc == 'start':
            start()
            if sys.argv[2:]:
                opc2 = sys.argv[2]
                if opc2.isdigit():
                    select_by_preset(opc2)
                elif opc2.isalpha():
                    select_by_name(opc2)
            else:
                select_by_preset(default_preset)

        # STOPS all this stuff
        elif opc == 'stop':
            stop()

        # ON THE FLY changing a preset number
        elif opc == 'preset':
            select_by_preset( sys.argv[2] )

        # ON THE FLY changing a preset name
        elif opc == 'name':
            select_by_name( sys.argv[2] )

        else:
            print( '(scripts/DVB.py) Bad option' )

    else:
        print(__doc__)
