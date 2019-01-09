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

    User settings (presets, default) can be configured into:
        config/DVB-T.yml

    Use:   DVB.py       start  [ <preset_num> | <channel_name> ]
                        stop
                        prev  (load previous from recent presets)
                        preset <preset_num>
                        name   <channel_name>
"""

import os
HOME = os.path.expanduser("~")

import sys
import time
import subprocess as sp
import threading

#import yaml
# ruamel.yaml preserves comments and items order when dumping to a file.
# https://yaml.readthedocs.io/en/latest/basicuse.html
from ruamel.yaml import YAML

import basepaths as bp
import getconfigs as gc
import predic as pd

## User settings under config/DVB-T.yml

## Script settings:
# DVB CONFIG file storing presets and recent stations:
DVB_config_fpath = bp.config_folder + 'DVB-T.yml'
# Name used from pre.di.c. for info and pid saving
program_alias = 'mplayer-dvb'
# Mplayer DVB-T tuner file
tuner_file = f'{HOME}/.mplayer/channels.conf'

## Mplayer options:
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
        channel_name = DVB_config['presets'][ preset_num ]
        select_by_name(channel_name)
        # Rotating and saving recent preset:
        last = DVB_config['recent_presets']['last']
        if preset_num != last:
            DVB_config['recent_presets']['prev'] = last
            DVB_config['recent_presets']['last'] = preset_num
            dump_yaml( DVB_config, DVB_config_fpath )
        return True

    except:
        print( f'(scripts/DVB.py) error in preset # {preset_num}' )
        return False

def start():
    # 1. Prepare a jack loop where MPLAYER outputs can connect.
    #    The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = threading.Thread( target = pd.jack_loop, args=('dvb_loop',) )
    jloop.start()
    # 2. Launching Mplayer for DVB service:
    opts = f'{options} -idle -slave -profile dvb -input file={input_fifo}'
    command = f'{mplayer_path} {opts}'
    with open(mplayer_redirection_path, 'w') as redir:
        pd.start_pid(command, program_alias, redir)

def stop():
    pd.kill_pid(program_alias)
    # harakiri
    sp.Popen( ['pkill', '-KILL', '-f', 'profile dvb'] )
    sp.Popen( ['pkill', '-KILL', '-f', 'DVB.py start'] )

def load_yaml(fpath):
    try:
        yaml = YAML() # default round-trip mode preserve comments and items order
        doc = open(fpath, 'r')
        d = yaml.load( doc.read() )
        doc.close()
        return d
    except:
        print ( '(scripts/DVB.py) YAML error loading ' + fpath )

def dump_yaml(d, fpath):
    try:
        yaml = YAML() # default round-trip mode preserve comments and items order
        doc = open(fpath, 'w')
        yaml.dump( d, doc )
        doc.close()
    except:
        print ( '(scripts/DVB.py) YAML error dumping ' + fpath )

if __name__ == '__main__':

    ### Reading the DVB-T config file
    DVB_config = load_yaml( DVB_config_fpath )
    
    ### Reading the command line
    if sys.argv[1:]:

        opc = sys.argv[1]

        # STARTS the script and optionally load a preset/name
        if opc == 'start':
            start()
            if sys.argv[2:]:
                opc2 = sys.argv[2]
                if opc2.isdigit():
                    select_by_preset( int(opc2) )
                elif opc2.isalpha():
                    select_by_name(opc2)
            else:
                if DVB_config['default_preset'] != 0:
                    select_by_preset( DVB_config['default_preset'] )
                else:
                    select_by_preset( DVB_config['recent_presets']['last'] )

        # STOPS all this stuff
        elif opc == 'stop':
            stop()

        # ON THE FLY changing to a preset number or rotates recent
        elif opc == 'preset':
            select_by_preset( int(sys.argv[2]) )
        elif opc == 'prev':
            select_by_preset( DVB_config['recent_presets']['prev'] )

        # ON THE FLY changing to a preset name
        elif opc == 'name':
            select_by_name( sys.argv[2] )

        else:
            print( '(scripts/DVB.py) Bad option' )

    else:
        print(__doc__)
