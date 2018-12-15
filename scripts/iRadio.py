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
    Start and stop mplayer for iRadio tasks, and change iRadio stations

    Use:    iradio.py   start  [ <num> | <station_name> ] &
                        stop
                        preset <num*>
                        name   <station_name*>
                        url    <some_url_stream>

    * from file:  ~/config/iradio_stations.yml

"""

import sys
import os
import time
from subprocess import Popen
import threading
import yaml

import basepaths as bp
import getconfigs as gc
import predic as pd

### Mplayer aditional options:
# -quiet: see channels change
# -really-quiet: silent
options = '-quiet -nolirc'
# Aditional option to avoid Mplayer default "Playlist parsing disabled for security reasons."
# This applies to RTVE, which iradio urls are given in .m3u playlist format.
# - one can download the .m3u then lauch the inside url with mplayer
# - or, easy way, we can allow playlit parsing on Mplayer.
#        if "rtve" in emisoraUrl:
options += " -allow-dangerous-playlist-parsing"

### Script config:
# DEFAULT iRadio station preset number:
default_station = '2'
# iRadio stations file:
stations_fname = bp.config_folder + 'iradio_stations.yml'
# command fifo filename
iradio_fifo = bp.main_folder + 'iradio_fifo'
# Mplayer path:
mplayer_path = '/usr/bin/mplayer'
# Mplayer outputs redirected to:
mplayer_redirection_path = '/home/predic/tmp/.iradio'
# name used for info and pid saving
program_alias = 'mplayer-iradio'


def load_url(url):
    try:
        command = ('loadfile ' + url + '\n' )
        with open( iradio_fifo, 'w') as f:
            f.write(command)
        return True
    except:
        return False

def select_by_name(preset_name):
    """ sets channel in mplayer """
    for preset,dict in stations.items():
        if dict['name'] == preset_name:
            load_url( dict['url'] )
            return
    print( f'(iRadio.py) station \'{preset_name}\' not found' )

def select_by_preset(preset_num):
    """ selects preset from DVB-t.ini """
    load_url( stations[ int(preset_num) ]['url'] )

def start():

    # 1. Prepare a jack loop where MPLAYER outputs can connect.
    #    The jack_loop module will keep the loop alive, so we need to thread it.
    jloop = threading.Thread( target = pd.jack_loop, args=('iradio_loop',) )
    jloop.start()

    # 2. Mplayer_url:
    opts = f'{options} -idle -slave -profile iradio -input file={iradio_fifo}'
    command = f'{mplayer_path} {opts}'
    with open(mplayer_redirection_path, 'w') as redir:
        pd.start_pid(command, program_alias, redir)

def stop():

    # kill bill
    pd.kill_pid(program_alias)
    Popen( 'pkill -f iradio'.split() )
    Popen( 'pkill -f iRadio.py'.split() )

if __name__ == '__main__':

    ### Reading the iradio stations file
    stations = {}
    f = open(stations_fname, 'r')
    tmp = f.read()
    f.close()
    try:
        stations = yaml.load(tmp)
    except:
        print ( '(iRadio.py) YAML error into ' + stations_fname )

    ### reading the command line
    if sys.argv[1:]:

        opc = sys.argv[1]

        # Start the script and optionally load a preset/name
        if opc == 'start':
            start()
            if sys.argv[2:]:
                opc2 = sys.argv[2]
                if opc2.isdigit():
                    select_by_preset(opc2)
                elif opc2.isalpha():
                    select_by_name(opc2)
            else:
                select_by_preset(default_station)

        # Stops all this stuff
        elif opc == 'stop':
            stop()

        # Selects an iRadio preset on the fly
        elif opc == 'preset':
            select_by_preset( sys.argv[2] )

        # Selects an iRadio station name on the fly
        elif opc == 'name':
            select_by_name( sys.argv[2] )

        # Loads an url stream on the fly
        elif opc == 'url':
            load_url( sys.argv[2] )

        elif '-h' in opc:
            print(__doc__)

        else:
            print('(iRadio.py) Bad option')
