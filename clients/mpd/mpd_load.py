#!/usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""
start and stop mplayer for DVB tasks

use it with 'start' and 'stop' as options
"""

import os
import sys
import time
import subprocess as sp
import multiprocessing as mp

import mpd

import baseconfig as base
import init
import pdlib as pd


# user config
config_filename = 'config.yml'

port = init.config['control_port']


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """
    Connect to mpd
    """

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd is not None:
        client.password(mpd_passwd)
    return client


def mpd_vol_loop():
    """
    loop: reads mpd volume, sets predic volume
    """

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
        pd.client_socket("level " + str(predic_level), port, quiet=True)
    mpd_client.close()
    mpd_client.disconnect()


def predic_vol_loop():
    """
    loop: reads predic volume, sets mpd volume
    """

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
    """
    loads mpd
    """

    # starts MPD
    print('\n(mpd_load) starting mpd')
    sp.Popen(mpd_conf["start_command"].split())
    if pd.wait4result(
            f'echo close|nc localhost {mpd_conf["port"]} 2>/dev/null',
            'OK MPD'):
        print('\n(mpd_load) mpd started :-)')
    else:
        print('\n(mpd_load) mpd loading failed')
        return

    # ping mpd to create jack ports
    try:
        mpd_client = connect_mpd()
        status = mpd_client.status()
        # check if there's a playlist loaded and, if any, \
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
    except Exception as e:
        print(f'\n(mpd_load) error in ping routine: {e}')

    # volume linked to mpd (optional)
    if mpd_conf['volume_linked']:
        try:
            mpdloop = mp.Process(target=mpd_vol_loop)
            mpdloop.start()
        except Exception as e:
            print('\n(mpd_load) mpd socket loop broke' +
                  f'with exception {e}')
        try:
            predicloop = mp.Process(target=predic_vol_loop)
            predicloop.start()
        except Exception as e:
            print('\n(mpd_load) predic socket loop broke' +
                  f' with exception {e}')


def stop():
    """
    kills mpd and this script
    """

    delay = init.config['command_delay']

    sp.Popen(mpd_conf["stop_command"].split())
    sp.Popen((f'pkill -f {dir}/mpd_load.py').split())
    time.sleep(delay)


if sys.argv[1:]:
    dir = os.path.dirname(os.path.realpath(__file__))
    mpd_conf = pd.get_yaml(f'{dir}/{config_filename}')
    try:
        option = {
            'start': start,
            'stop': stop
            }[sys.argv[1]]()
    except KeyError:
        print('\n(mpd_load) bad option')
else:
    print(__doc__)
