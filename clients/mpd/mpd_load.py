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
import math as m
import subprocess as sp
import multiprocessing as mp

import mpd

import base
import init
import predic as pd


## user config
config_filename = 'config.yml'


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """Connect to mpd"""

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd is not None:
        client.password(mpd_passwd)
    return client


def mpd_vol_loop():
    """loop: reads mpd volume, sets predic volume"""

    mpd_client = connect_mpd()
    mpd_gain_min = base.gain_max - mpd_conf['slider_range']
    while True:
        mpd_client.idle('mixer')
        mpd_vol = int(mpd_client.status()['volume'])
        # update pre.di.c level
        predic_level = round(
            (mpd_vol / 100 * mpd_conf['slider_range'])
            + mpd_gain_min
            - init.speaker['ref_level_gain']
            )
        pd.client_socket("level " + str(predic_level), quiet=True)
    mpd_client.close()
    mpd_client.disconnect()


def predic_vol_loop():
    """loop: reads predic volume, sets mpd volume"""

    interval = init.config['command_delay'] / 10
    predic_level = pd.read_state()['level']
    mpd_gain_min = base.gain_max - mpd_conf['slider_range']
    while True:
        # check level changes in pre.di.c
        predic_level_old = predic_level
        predic_level = pd.read_state()['level']
        if predic_level != predic_level_old:
            # update mpd "fake volume"
            predic_gain = predic_level + init.speaker['ref_level_gain']
            mpd_vol = round(
                (predic_gain - mpd_gain_min)
                * 100 / mpd_conf['slider_range']
                )
            # minimal mpd volume
            if mpd_vol < 0:
                mpd_vol = 0
            mpd_client = connect_mpd()
            mpd_client.setvol(int(mpd_vol))
            mpd_client.close()
        time.sleep(interval)


def start():
    """loads mpd"""

    # starts MPD
    print('(mpd_load.py) starting mpd')
    sp.Popen(mpd_conf["start_command"].split())
    if pd.wait4result(
            f'echo close|nc localhost {mpd_conf["port"]} 2>/dev/null',
            'OK MPD'):
        print('(mpd_load.py) mpd started :-)')
    else:
        print('(mpd_load.py) mpd loading failed')
        return

    # ping mpd to create jack ports
    try:
        mpd_client = connect_mpd()
        status = mpd_client.status()
        # check if there's a playlist loaded and if any \
        # get relevant status data
        # no 'song' in status if there is no playlist
        if 'song' in status:
            song = status['song']
            # no 'elapsed' in status if song stoppped
            if 'elapsed' in status:
                elapsed = status['elapsed']
            else:
                elapsed = 0
            restore = True
        else:
            restore = False

        # path to silence dummy file relative to base music directory
        silence_path = "mpd_silence.wav"
        # load silence file, plays it a bit, delete it from playlist, \
        # and restore the play pointer to previous state
        mpd_client.addid(silence_path, 0)
        mpd_client.play(0)
        time.sleep(init.config['command_delay'])
        mpd_client.delete(0)
        mpd_client.pause()
        if restore:
            mpd_client.seek(song, elapsed)
        mpd_client.close()
        # disconnect mpd_ports
        pd.client_socket('noinput')
    except:
        print('(mpd_load.py) problems with mpd ping routine')

    # volume linked to mpd (optional)
    if mpd_conf['volume_linked']:
        try:
            mpdloop = mp.Process( target = mpd_vol_loop )
            mpdloop.start()
        except:
            print('(mpd_load.py) mpd socket loop broke')
        try:
            predicloop = mp.Process( target = predic_vol_loop )
            predicloop.start()
        except:
            print('(mpd_load.py) predic socket loop broke')


def stop():
    """kills mpd and this script"""

    sp.Popen(mpd_conf["stop_command"].split())
    sp.Popen((f'pkill -f {dir}/mpd_load.py').split())


if sys.argv[1:]:
    dir = os.path.dirname(os.path.realpath(__file__))
    mpd_conf = init.get_yaml(f'{dir}/{config_filename}')
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[sys.argv[1]]()
    except KeyError:
        print('mpd_load.py: bad option')
else:
    print(__doc__)
