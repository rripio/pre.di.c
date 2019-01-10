#!/usr/bin/env python3
"""
    Launch 'librespot', a Spotify Connect player client

    use:    librespot.py   start | stop
"""

import sys
from subprocess import Popen
from socket import gethostname

import basepaths

def start():
    # 'librespot' binary prints out the playing track and some info to stdout/stderr.
    # We redirect the print outs to a temporary file that will be periodically
    # read from a player control daemon.

    cmd =  f'/usr/bin/librespot --name {gethostname()} --bitrate 320 --backend alsa' + \
           ' --device jack --disable-audio-cache --initial-volume=99'

    logFileName = f'{basepaths.main_folder}/.librespot_events'

    with open(logFileName, 'w') as logfile:
        Popen( cmd.split(), stdout=logfile, stderr=logfile )

def stop():
    """ harakiri """
    Popen( 'pkill -f librespot'.split() )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(librespot.py) bad option')
else:
    print(__doc__)
