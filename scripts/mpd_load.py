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

"""start and stop MPD
use it with 'start' and 'stop' as options"""

import os
import sys
import time
import math as m
from subprocess import Popen
import threading

# Needs the package 'python-mpd', but for Raspberry Pi with berryconda (python 3.6) then 'pip install python-mpd2'
import mpd

import predic as pd
import getconfigs as gc


## user config
mpd_path = '/usr/bin/mpd'
mpd_options = ''
mpd_alias = 'mpd'
#mpd_volume_linked = True
mpd_volume_linked = False   # DOES NOT USE THIS. PENDING TO REVIEW THIS STUFF
# Must be positive integer
slider_range = 48


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """Connect to mpd"""

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd is not None:
        client.password(mpd_passwd)
    return client


def set_predic_vol_loop(c):
    """loop: reads mpd volume, sets predic volume"""

    while True:
        # 'c.idle' waits for a MPD change...,
        # 'mixer' filters only volume events
        c.idle('mixer')
        # when something happens idle ends
        newVol = c.status()['volume']
        # set gain
        g = str(int(round(
                ((m.log(1+float(newVol)/100)/m.log(2))**1.293-1)
                * slider_range + gc.config['gain_max'])))
        pd.client_socket("gain " + g, quiet=True)


def set_mpd_vol_loop(gain):

    # update mpd "fake volume"
    vol = (100 * (m.exp(max(
            ((gain - gc.config['gain_max']) / slider_range + 1),0)
            ** (1/1.293) * m.log(2)) - 1))

#    vol = 100*(m.exp(max((gain/slider_range+1),0)
#                                    **(1/1.293)*m.log(2))-1)
     # minimal mpd volume
    if vol < 1: vol = 1
    try:
        c = connect_mpd()
        c.setvol(int(vol))
        c.close()
        c.disconnect()
    except:
        print("problem setting mpd volume")

def start():
    """loads mpd"""

    # 1. Request pre.di.c to create a jack loop to connect the MPD outputs
    #    This will be a daemond like thread to continue to starting MPD
    loop = threading.Thread( target = pd.jack_loop('mpd_loop') )
    loop.setDaemon(True)
    loop.start()

    # 2. Starts MPD
    print('starting mpd')
    command = f'{mpd_path} {mpd_options}'
    pd.start_pid(command, mpd_alias)
    time.sleep(gc.config['command_delay'])

    # volume linked to mpd (optional)  # DOES NOT USE THIS. PENDING TO REVIEW THIS STUFF
    if mpd_volume_linked:
        print('waiting for mpd')
        if  pd.wait4result('pgrep -l mpd', 'mpd', tmax=10, quiet=True):
            print('mpd started :-)')
        else:
            print('error detecting mpd, client_mpd'
                                                ' won\'t start')
        try:
            c = connect_mpd('localhost', 6600)
            c.timeout = 10
            c.idletimeout = None
            set_predic_vol_loop(c)
            c.close()
            c.disconnect()
        except:
            print("mpd socket loop broke")


def stop():
    """kills mpd"""

#    pd.kill_pid(mpd_alias)
    Popen('mpd --kill'.split())
    time.sleep(gc.config['command_delay']*5)


if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('mpd_load.py: bad option')
else:
    print(__doc__)

