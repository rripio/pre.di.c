#!/usr/bin/env python3

# Copyright (c) 2018 Rafael Sánchez
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
    Starts and stops Mplayer for internet streams playback like
    podcasts or internet radio stations.
    
    Also used to change on the fly the played stream.

    Internet stream presets can be configured into:
        config/istreams.yml

    Use:   istreams.py  start  [ <preset_num> | <preset_name> ]
                        stop
                        preset <preset_num>
                        name   <preset_name>
                        url    <some_url_stream>

"""

import sys
import time
from subprocess import Popen
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
presets_fname = bp.config_folder + 'istreams.yml'
# Name used from pre.di.c. for info and pid saving
program_alias = 'mplayer-istreams'

############################
# Mplayer options:
############################
# -quiet: see channels change
# -really-quiet: silent
options = '-quiet -nolirc'
# Aditional option to avoid Mplayer defaults to "Playlist parsing disabled for security reasons."
# This applies to RTVE.es, which radio urls are given in .m3u playlist format.
# - one can download the .m3u then lauch the inside url with mplayer
# - or, easy way, we can allow playlit parsing on Mplayer.
options += " -allow-dangerous-playlist-parsing"
# Mplayer input commands fifo filename
istreams_fifo = f'{bp.main_folder}/istreams_fifo'
# Mplayer path:
mplayer_path = '/usr/bin/mplayer'
# Mplayer outputs redirected to:
mplayer_redirection_path = f'{bp.main_folder}/.istreams_events'


def load_url(url):
    try:
        command = ('loadfile ' + url + '\n' )
        with open( istreams_fifo, 'w') as f:
            f.write(command)
        return True
    except:
        return False

def select_by_name(preset_name):
    """ loads a stream by its preset name """
    for preset,dict in presets.items():
        if dict['name'] == preset_name:
            load_url( dict['url'] )
            return True
    print( f'(istreams.py) preset \'{preset_name}\' not found' )
    return False

def select_by_preset(preset_num):
    """ loads a stream by its preset number """
    try:
        load_url( presets[ int(preset_num) ]['url'] )
        return True
    except:
        print( f'(istreams.py) error in preset # {preset_num}' )
        return False

def start():

    # 1. Prepare a jack loop where MPLAYER outputs can connect.
    #    The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = threading.Thread( target = pd.jack_loop, args=('istreams_loop',) )
    jloop.start()

    # 2. Mplayer_url:
    opts = f'{options} -idle -slave -profile istreams -input file={istreams_fifo}'
    command = f'{mplayer_path} {opts}'
    with open(mplayer_redirection_path, 'w') as redir:
        pd.start_pid(command, program_alias, redir)

def stop():

    pd.kill_pid(program_alias)
    # kill bill
    Popen( 'pkill -KILL -f istreams'.split() )
    Popen( 'pkill -KILL -f istreams.py'.split() )

if __name__ == '__main__':

    ### Reading the presets stations file
    presets = {}
    f = open(presets_fname, 'r')
    tmp = f.read()
    f.close()
    try:
        presets = yaml.load(tmp)
    except:
        print ( '(istreams.py) YAML error into ' + presets_fname )

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

        # ON THE FLY loading an url stream
        elif opc == 'url':
            load_url( sys.argv[2] )

        else:
            print( '(scripts/istreams.py) Bad option' )

    else:
        print(__doc__)
