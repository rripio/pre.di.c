#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (C) 2006-2011 Roberto Ripio
# Copyright (C) 2011-2016 Alberto Miguélez
# Copyright (C) 2016-2018 Rafael Sánchez
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

import os
import sys
import time
import threading
import math as m
import subprocess as sp

import mpd

import predic as pd
import getconfigs as gc


## user config
config_filename = 'mpd_load.yaml'


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """Connect to mpd"""

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd:
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
                * mpd_conf['slider_range'] + gc.config['gain_max']))-6)
        pd.client_socket("gain " + g, quiet=True)


def set_mpd_vol_loop(gain):

    # update mpd "fake volume"
    vol = (100 * (m.exp(max(
            ((gain - gc.config['gain_max']) / mpd_conf['slider_range'] + 1),0)
            ** (1/1.293) * m.log(2)) - 1))
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
    """loads mpd and jack loop"""

    # create jack loop for connections
    # The jack_loop module will keep the loop alive, so we need to thread it
    jloop = threading.Thread( target = pd.jack_loop, args=('mpd_loop',) )
    jloop.start()

    # starts MPD
    print('(mpd_load.py) starting mpd')
    mpd_command = f'{mpd_conf["path"]} {mpd_conf["options"]}'
    try:
        sp.Popen(mpd_command.split())
    except:
        print('(mpd_load.py) mpd loading failed')
        return

    # volume linked to mpd (optional)  # THIS MUST BE REVIEWED
    if mpd_conf['volume_linked']:
        print('(mpd_load.py) waiting for mpd')
        if pd.wait4result(f'echo close|nc localhost {mpd_conf["port"]}',
                                                 'OK MPD'):
            print('(mpd_load.py) mpd started :-)')
            try:
                c = connect_mpd()
                c.timeout = 10
                c.idletimeout = None
                set_predic_vol_loop(c)
                c.close()
                c.disconnect()
            except:
                print('(mpd_load.py) mpd socket loop broke')
        else:
            print('(mpd_load.py) client_mpd didn\'t start')


def stop():
    """kills mpd"""

    sp.Popen('mpd --kill'.split())


if sys.argv[1:]:
    dir = os.path.dirname(os.path.realpath(__file__))
    mpd_conf = gc.get_yaml(dir + '/' + config_filename)
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('mpd_load.py: bad option')
else:
    print(__doc__)
