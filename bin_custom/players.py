#!/usr/bin/env python3

import subprocess as sp

def get_current_player():
    # WORK IN PROGRESS    
    # It is planned to check for the current player ...
    # 
    return 'spotify'

def get_current_playing():
    # Retrieve a dictionary with the current player info
    # {player: xxxx, artist: xxxx, album:xxxx, track:xxxx }

    player = get_current_player()

    if player == 'spotify':
        return get_librespot_info()

    elif player() == 'mpd':
        return get_mpd_info()

    else:
        return '{}'
        
def get_librespot_info():

    try:
        # Returns the current track played by librespot when redirected to ~/tmp/.librespotEvents
        tmp = sp.check_output( 'tail -n1 /home/predic/tmp/.librespotEvents'.split() )
        tmp = tmp.decode().split('"')[-2]
        # JSON for JavaScript on www, NOTICE required double quotes:
        return '{ "player":"Spotify", "artist":"", "album":"", "track":"' + tmp + '" }'

    except:
        return '{}'

def get_mpd_info():
    # WORK IN PROGRESS
    return '{}'
