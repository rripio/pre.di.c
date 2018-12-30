#!/usr/bin/env python3

# Copyright (c) 2018 Rafael Sánchez
# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (c) 2006-2011 Roberto Ripio
# Copyright (c) 2011-2016 Alberto Miguélez
# Copyright (c) 2016-2018 Rafael Sánchez
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

""" A module that controls and retrieve metadata info from the current player.
    This module is ussually called from a listening server.
"""

# TODO: a command line interface could be useful

import subprocess as sp
import yaml
import mpd
import time

import basepaths as bp

# MPD settings:
mpd_host    = 'localhost'
mpd_port    = 6600
mpd_passwd  = None

def get_predic_state():
    """ returns the YAML pre.di.c's status info """

    f = open( bp.main_folder + 'config/state.yml', 'r')
    tmp = f.read()
    f.close()
    return yaml.load(tmp)

def mpd_client(query):
    """ comuticates to MPD music player daemon """

    def get_meta():
        """ gets info from mpd """

        player = 'MPD'
        time_pos = time_tot = '-:-'
        bitrate = artist = album = title = '-'
        
        if mpd_online:

            # We try because not all tracks have complete metadata fields:
            try:    artist   = client.currentsong()['artist']
            except: pass
            try:    album    = client.currentsong()['album']
            except: pass
            try:    title    = client.currentsong()['title']
            except: pass
            try:    bitrate  = client.status()['bitrate']   # given in kbps
            except: pass
            try:    time_pos = timeFmt( float( client.status()['elapsed'] ) )
            except: pass
            try:    time_tot = timeFmt( float( client.currentsong()['time'] ) )
            except: pass

            client.close()

        return '{ "player":"' + player + '", "bitrate":"' + bitrate + \
               '", "time_pos":"' + time_pos + '", "time_tot":"' + time_tot + \
               '", "artist":"' + artist + '", "album":"' + album + '", "title":"' + title + '" }'

    def stop():
        if mpd_online:
            client.stop()
            return client.status()['state']
    def pause():
        if mpd_online:
            client.pause()
            return client.status()['state']
    def play():
        if mpd_online:
            client.play()
            return client.status()['state']
    def next():
        if mpd_online:
            client.next()
            return client.status()['state']
    def previous():
        if mpd_online:
            client.previous()
            return client.status()['state']
    def state():
        if mpd_online:
            return client.status()['state']

    client = mpd.MPDClient()
    try:
        client.connect(mpd_host, mpd_port)
        if mpd_passwd:
            client.password(mpd_passwd)
        mpd_online = True
    except:
        mpd_online = False

    result = {  'get_meta':   get_meta,
                'stop':       stop,
                'pause':      pause,
                'play':       play,
                'next':       next,
                'previous':   previous,
                'state':      state
             }[query]()

    return result

def get_librespot_meta():
    """ gets metadata info from librespot """
    # Unfortunately librespot only prints out the title metadata, nor artist neither album.
    # More info can be retrieved from the spotify web, but it is necessary to register
    # for getting a privative and unique http request token for authentication.

    player = 'Spotify'
    time_pos = time_tot = '-:-'
    bitrate = artist = album = title = '-'

    try:
        # Returns the current track title played by librespot.
        # 'scripts/librespot.py' handles the libresport print outs to be 
        #                        redirected to 'tmp/.librespotEvents'
        tmp = sp.check_output( f'tail -n1 {bp.main_folder}/.librespot_events'.split() )
        title  = tmp.decode().split('"')[-2]
        # JSON for JavaScript on control web page, NOTICE json requires double quotes:
    except:
        pass

    return '{ "player":"' + player + '", "bitrate":"' + bitrate + \
           '", "time_pos":"' + time_pos + '", "time_tot":"' + time_tot + \
           '", "artist":"' + artist + '", "album":"' + album + '", "title":"' + title + '" }'

def mplayer_cmd(cmd, service):
    """ Sends a command to Mplayer trough by its input fifo """
    # Notice: Mplayer sends its responses to the terminal where Mplayer was launched,
    #         or to a redirected file.

    # We prefer to translate previuos/next commands to seeking -/+ 60 seconds:
    if cmd == 'previous':
        cmd = 'seek -60 0' # 0: relative (http://www.mplayerhq.hu/DOCS/tech/slave.txt)
    if cmd == 'next':
        cmd = 'seek +60 0'

    sp.Popen( f'echo "{cmd}" > {bp.main_folder}/{service}_fifo', shell=True)

def get_mplayer_istreams_info():
    """ gets metadata from Mplayer as per
        http://www.mplayerhq.hu/DOCS/tech/slave.txt """

    player = 'Mplayer'
    time_pos = time_tot = '-:-'
    bitrate = artist = album = title = '-'

    # This is the file were Mplayer standard output has been redirected to,
    # so we can read there any answer when required to Mplayer slave daemon:
    mplayer_redirection_path = f'{bp.main_folder}/.istreams_events'

    # Communicates to Mplayer trough by its input fifo to get the current media filename and bitrate:
    mplayer_cmd(cmd='get_audio_bitrate', service='istreams')
    mplayer_cmd(cmd='get_file_name',     service='istreams')
    mplayer_cmd(cmd='get_time_pos',      service='istreams')
    mplayer_cmd(cmd='get_time_length',   service='istreams')

    # Waiting Mplayer ANS_xxxx to be writen to output file
    time.sleep(.25)

    # Trying to read the ANS_xxxx from the Mplayer output file
    with open(mplayer_redirection_path, 'r') as file:
        try:
            tmp = file.read().split('\n')[-5:] # get last 4 lines plus the empty one when splitting
        except:
            tmp = []

    #print('DEBUG\n', tmp)

    # Flushing the Mplayer output file to avoid continue growing:
    with open(mplayer_redirection_path, 'w') as file:
        file.write('')

    # Reading the intended metadata chunks
    if len(tmp) >= 4: # to avoid indexes issues while no relevant metadata are available

        if 'ANS_AUDIO_BITRATE=' in tmp[0]:
            bitrate = tmp[0].split('ANS_AUDIO_BITRATE=')[1].split('\n')[0].replace("'","")
            bitrate = bitrate.split()[0]

        if 'ANS_FILENAME=' in tmp[1]:
            title = tmp[1].split('ANS_FILENAME=')[1].split('?')[0].replace("'","")

        if 'ANS_TIME_POSITION=' in tmp[2]:
            time_pos = tmp[2].split('ANS_TIME_POSITION=')[1].split('\n')[0]
            time_pos = timeFmt( float( time_pos ) )

        if 'ANS_LENGTH=' in tmp[3]:
            time_tot = tmp[3].split('ANS_LENGTH=')[1].split('\n')[0]
            time_tot = timeFmt( float( time_tot ) )

    return '{ "player":"' + player + '", "bitrate":"' + bitrate + \
           '", "time_pos":"' + time_pos + '", "time_tot":"' + time_tot + \
           '", "artist":"' + artist + '", "album":"' + album + '", "title":"' + title + '" }'

def timeFmt(x):
    min = int(x / 60)
    sec = int(round(x % 60))
    return f'{min:0>2}:{sec:0>2}'

def predic_source():
    """ retrieves the current input source """
    source = None
    # It is possible to fail while state file is updating :-/
    times = 4
    while times:
        try:
            source = get_predic_state()['input']
            break
        except:
            times -= 1
        time.sleep(.25)
    return source

def get_meta():
    """ Constructs a dictionary-like string with the current track metadata
        '{player: xxxx, artist: xxxx, album:xxxx, title:xxxx, etc... }'
        Then will return a bytes-like object from the referred string.
    """
    player   = '-'
    time_pos = time_tot = '-:-'
    bitrate = artist = album = title = '-'
    source = predic_source()
    
    result  = '{ "player":"' + player + '", "bitrate":"' + bitrate + \
               '", "time_pos":"' + time_pos + '", "time_tot":"' + time_tot + \
               '", "artist":"' + artist + '", "album":"' + album + '", "title":"' + title + '" }'

    if   source == 'spotify':
        result = get_librespot_meta()

    elif source == 'mpd':
        result = mpd_client('get_meta')

    elif source == 'istreams':
        result = get_mplayer_istreams_info()

    # As this is used by a server, we will return a bytes-like object:
    return result.encode()

def control(action):
    """ controls the playback """
    result = ''

    if   predic_source() == 'mpd':
        result = mpd_client(action)

    elif predic_source() == 'spotify':
        # WORK IN PROGRESS
        pass

    elif predic_source() == 'tdt':
        # WORK IN PROGRESS
        pass

    elif predic_source() in ['istreams', 'iradio']:
        mplayer_cmd(cmd=action, service='istreams')

    else:
        pass

    # As this is used by a server, we will return a bytes-like object:
    if result:
        return result.encode()
    else:
        return ''.encode()

def do(task):
    """
        This do() is the entry interface function from a listening server.
        Only certain received 'tasks' will be validated and processed,
        then returns back some useful info to the asking client.
    """

    # First clearing the new line
    task = task.replace('\n','')

    # Tasks to querying the current music player
    if   task == 'player_get_meta':
        return get_meta()
    elif task == 'player_state':
        return control('state')
    elif task == 'player_stop':
        return control('stop')
    elif task == 'player_pause':
        return control('pause')
    elif task == 'player_play':
        return control('play')
    elif task == 'player_next':
        return control('next')
    elif task == 'player_previous':
        return control('previous')

    # A pseudo task, an url to be played back:
    elif task[:7] == 'http://':
        sp.run( bp.main_folder + f'scripts/istreams.py url {task}'.split() )
