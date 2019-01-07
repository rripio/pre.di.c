#!/usr/bin/env python3

"""
    Launch the spotify_monitor.py daemon which:
    - listen for GLib events from Spotify Desktop
    - and writes down the metadata into a file for others to read it.

    use:   spotify_monitor.py   start | stop
"""

import sys
from subprocess import Popen
import basepaths as bp

def start():
    Popen( f'{bp.main_folder}/clients/bin/spotify_monitor.py' )

def stop():
    Popen( ['pkill', '-f',  'spotify_monitor.py'] )

if sys.argv[1:]:

    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print('(spotify_monitor) bad option')
else:
    print(__doc__)
