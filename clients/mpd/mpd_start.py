# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Start mpd."""

import os
import time
import subprocess as sp
import multiprocessing as mp

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import mpd

import baseconfig as base
import init
import pdlib as pd


# user config
config_filename = 'config.yml'

# globals
port = init.config['control_port']


class Predic_vol_watch(FileSystemEventHandler):
    """Watch predic volume level."""

    # initial level for comparison
    predic_level = pd.get_state()['level']

    def on_modified(self, event):
        """Process volume changes."""
        # check level changes in pre.di.c
        predic_level_old = Predic_vol_watch.predic_level
        Predic_vol_watch.predic_level = pd.get_state()['level']
        predic_level = Predic_vol_watch.predic_level
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


def connect_mpd(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """Connect to mpd."""
    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd is not None:
        client.password(mpd_passwd)
    return client


def mpd_vol_loop():
    """Read mpd volume, sets predic volume, on loop."""
    mpd_client = connect_mpd()
    mpd_gain_min = base.gain_max - mpd_conf['slider_range']
    while True:
        # wait for changes in mpd mixer
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
    """Read predic volume, sets mpd volume, on loop."""
    interval = init.config['command_delay'] / 2

    event_handler = Predic_vol_watch()
    observer = Observer()
    observer.schedule(event_handler, init.config_folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(interval)

    finally:
        observer.stop()
        observer.join()


dir = os.path.dirname(os.path.realpath(__file__))
mpd_conf = pd.read_yaml(f'{dir}/{config_filename}')
mpd_gain_min = base.gain_max - mpd_conf['slider_range']

print('\n(mpd_load) starting mpd')
sp.Popen(mpd_conf["mpd_start_command"].split())

delay = init.config['command_delay']*10
if pd.wait4result(
        f'echo close|nc localhost {mpd_conf["port"]} 2>/dev/null',
        'OK MPD', delay):
    print('\n(mpd_load) mpd started :-)')
else:
    print('\n(mpd_load) mpd loading failed')
    quit()

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

    # load silence file, plays it a bit, delete it from playlist, \
    # and restore the play pointer to previous state
    mpd_client.addid(mpd_conf['silence_path'], 0)
    mpd_client.play(0)
    time.sleep(delay)
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
