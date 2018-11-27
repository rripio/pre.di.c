#!/usr/bin/env python3
""" A custom made script to retrieve track info from the current player
"""
import subprocess as sp
import yaml
import jack
import mpd

def get_state():
    f = open('/home/predic/config/state.yml', 'r')
    tmp = f.read()
    f.close()
    return yaml.load(tmp)

def get_inputs():
    f = open('/home/predic/config/inputs.yml', 'r')
    tmp = f.read()
    f.close()
    return yaml.load(tmp)

def find_jack_ports(pattern):
    jc = jack.Client('tmp_players')
    result = False
    if jc.get_ports(name_pattern=pattern):
        result = True
    jc.close()
    return result

def get_librespot_info():

    try:
        # Returns the current track played by librespot when redirected to ~/tmp/.librespotEvents
        tmp = sp.check_output( 'tail -n1 /home/predic/tmp/.librespotEvents'.split() )
        tmp = tmp.decode().split('"')[-2]
        # JSON for JavaScript on control web page, NOTICE json requires double quotes:
        return '{ "player":"Spotify", "artist":"", "album":"", "title":"' + tmp + '" }'

    except:
        return '{}'

def get_mpd_info(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """ gets playing info from mpd
    """
    # WORK IN PROGRESS

    client = mpd.MPDClient()
    client.connect(mpd_host, mpd_port)
    if mpd_passwd is not None:
        client.password(mpd_passwd)
    print( client.currentsong() )
    client.close()

    return '{}'

def get_current_player():
    # WORK IN PROGRESS
    # Gets the current player based on the current input name.
    # Neverless, some players does not have jack backend, then using
    # the alsa to jack plugin and none input is selected on pre.di.c

    curr_input =  get_state()['input']

    if curr_input == 'none':
        # if find_jack_ports('alsa'): # but alsa ports disappears when changing track :-/
        return 'spotify'

    elif curr_input == 'mpd':
        return 'mpd'

    else:
        return 'none'

def get_current_playing():
    # Retrieve a dictionary with the current player info
    # {player: xxxx, artist: xxxx, album:xxxx, title:xxxx }

    player = get_current_player()

    if player == 'spotify':
        return get_librespot_info()

    elif player == 'mpd':
        return get_mpd_info()

    else:
        return '{}'
