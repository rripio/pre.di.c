#!/usr/bin/env python3
""" A module  to retrieve track info from the current player
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

def get_mpd_info(mpd_host='localhost', mpd_port=6600, mpd_passwd=None):
    """ gets info from mpd """

    player = 'MPD'
    artist = album = title = ''

    try:
        client = mpd.MPDClient()
        client.connect(mpd_host, mpd_port)
        if mpd_passwd:
            client.password(mpd_passwd)
        # We try because not all tracks have complete metadata fields:
        try:    artist = client.currentsong()['artist']
        except: pass
        try:    album  = client.currentsong()['album']
        except: pass
        try:    title  = client.currentsong()['title']
        except: pass
        client.close()
    except:
        pass

    return '{ "player":"' + player + '", "artist":"' + artist + \
           '", "album":"' + album + '", "title":"' + title + '" }'

def get_librespot_info():
    """ gets info from librespot """
    # Unfortunately librespot only prints out the title metadata, nor artist neither album.
    # More info can be retrieved from the spotify web, but it is necessary to register
    # for getting a privative and unique http request token for authentication.

    player = 'Spotify'
    artist = album = title = ''

    try:
        # Returns the current track played by librespot when redirected to ~/tmp/.librespotEvents
        tmp = sp.check_output( 'tail -n1 /home/predic/tmp/.librespotEvents'.split() )
        title  = tmp.decode().split('"')[-2]
        # JSON for JavaScript on control web page, NOTICE json requires double quotes:
    except:
        pass

    return '{ "player":"' + player + '", "artist":"' + artist + \
           '", "album":"' + album + '", "title":"' + title + '" }'

def get_current_playing():
    # Retrieve a dictionary with the current player info
    # {player: xxxx, artist: xxxx, album:xxxx, title:xxxx }

    player = artist = album = title = ''

    listening = get_state()['input']

    if listening == 'spotify':
        return get_librespot_info()

    elif listening == 'mpd':
        return get_mpd_info()

    else:
        return '{ "player":"' + player + '", "artist":"' + artist + \
               '", "album":"' + album + '", "title":"' + title + '" }'
