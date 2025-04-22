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


# User config.
config_filename = 'config.yml'

# Globals.
port = init.config['control_port']


class Predic_vol_watch(FileSystemEventHandler):
    """Watch predic volume gain."""

    # Initial gain for comparison.
    predic_gain = pd.calc_gain(pd.get_state()['level'])

    def on_modified(self, event):
        """Process volume changes."""
        # Check gain changes in pre.di.c.
        predic_gain_old = Predic_vol_watch.predic_gain
        Predic_vol_watch.predic_gain = pd.calc_gain(pd.get_state()['level'])
        predic_gain = Predic_vol_watch.predic_gain
        if predic_gain != predic_gain_old:
            update_mpd_vol(predic_gain)


def update_mpd_vol(predic_gain):
    """Update mpd "fake volume"."""
    mpd_vol = round((predic_gain - base.gain_max)
        / mpd_conf['gain_precision'] + 100)
    # Clamp mpd volume.
    if mpd_vol < 0:
        mpd_vol = 0
    if mpd_vol > 100:
        mpd_vol = 100
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
    while True:
        # Wait for changes in mpd mixer.
        mpd_client.idle('mixer')
        mpd_vol = int(mpd_client.status()['volume'])
        # Update pre.di.c gain.
        predic_gain = ((mpd_vol - 100) * mpd_conf['gain_precision']
                       + base.gain_max)
        pd.client_socket("gain " + str(predic_gain), port, quiet=True)
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

# Ping mpd to create jack ports.
try:
    mpd_client = connect_mpd()
    status = mpd_client.status()
    # Check if there's a playlist loaded and, if any,
    # get relevant status data.
    # No 'song' in status if there is no playlist.
    if 'song' in status:
        song = status['song']
        # No 'elapsed' in status if song stoppped.
        if 'elapsed' in status:
            elapsed = status['elapsed']
        else:
            elapsed = 0
        restore = True
    else:
        restore = False
    # Load silence file, plays it a bit, delete it from playlist,
    # and restore the play pointer to previous state.
    songid = mpd_client.addid(mpd_conf['silence_path'], )
    mpd_client.playid(songid)
    time.sleep(1)
    mpd_client.stop()
    mpd_client.deleteid(songid)
    if restore:
        mpd_client.seek(song, elapsed)
    mpd_client.pause()
    mpd_client.close()
except Exception as e:
    print(f'\n(mpd_load) error in ping routine: {e}')

# Volume linked to mpd (optional).
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
    # Initialize mpd volume:
    update_mpd_vol(pd.calc_gain(pd.get_state()['level']))
