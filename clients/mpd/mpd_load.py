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
config_filename = 'config.yml'


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """Connect to mpd"""

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd:
        client.password(mpd_passwd)
    return client


def mpd_vol_loop():
    """loop: reads mpd volume, sets predic volume"""

    while True:
        interval = gc.config['command_delay'] / 10
        mpd_client = connect_mpd()
        mpd_vol = int(mpd_client.status()['volume'])
        predic_level = pd.get_state()['level']
        mpd_gain_min = gc.config['gain_max'] - mpd_conf['slider_range']
        try:
            while True:
                # check level changes in pre.di.c
                predic_level_old = predic_level
                predic_level = pd.get_state()['level']
                if predic_level != predic_level_old:
                    # update mpd "fake volume"
                    predic_gain = predic_level + gc.speaker['ref_level_gain']
                    mpd_vol = round((predic_gain - mpd_gain_min)
                                            * 100 / mpd_conf['slider_range'])
                    # minimal mpd volume
                    if mpd_vol < 0: mpd_vol = 0
                    mpd_client.setvol(int(mpd_vol))
                # check volume changes in mpd
                mpd_vol_old = mpd_vol
                mpd_vol = int(mpd_client.status()['volume'])
                if mpd_vol != mpd_vol_old:
                    # update pre.di.c level
                    predic_level = round((mpd_vol / 100
                                        * mpd_conf['slider_range'])
                                        + mpd_gain_min
                                        - gc.speaker['ref_level_gain'])
                    pd.client_socket("level " + str(predic_level), quiet=True)
                time.sleep(interval)
        except:
            pass
        mpd_client.close()
        mpd_client.disconnect()


def start():
    """loads mpd and jack loop"""

    # create jack loop for connections
    # The jack_loop function will keep the loop alive, so we need to thread it
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

    # volume linked to mpd (optional)
    if mpd_conf['volume_linked']:
        print('(mpd_load.py) waiting for mpd')
        if pd.wait4result(
                f'echo close|nc localhost {mpd_conf["port"]} 2>/dev/null',
                                                                 'OK MPD'):
            print('(mpd_load.py) mpd started :-)')
            try:
                mpdloop = threading.Thread( target = mpd_vol_loop )
                mpdloop.start()
            except:
                print('(mpd_load.py) mpd socket loop broke')
        else:
            print('(mpd_load.py) client_mpd didn\'t start')


def stop():
    """kills mpd and this script"""

    sp.Popen(('pkill -f ' +
                '/home/predic/pre.di.c/clients/mpd/mpd_load.py').split())
    sp.Popen('pkill -f /usr/bin/mpd'.split())


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
