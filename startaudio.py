#! /usr/bin/env python3

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

"""Starts pre.di.c audio system
    Usage:
    startaudio.py [ core | clients | all ]   (default 'all')
    core: jack, brutefir, server
    players: everything else (players and clients)
    all: all of the above
"""

import sys
import os
import time
import subprocess as sp

import jack

import stopaudio
import predic as pd
import basepaths as bp
import getconfigs as gc


def limit_level(level_on_startup, max_level_on_startup):
    """limit volume as specified in config.ini"""

    # if fixed volume on startup
    if level_on_startup:
        level = level_on_startup
    elif max_level_on_startup:
        if gc.state['level'] > max_level_on_startup:
            level = max_level_on_startup
        else:
            level = gc.state['level']
    else:
        level = gc.state['level']
    pd.client_socket('level ' + str(level))


def init_jack():
    """loads jack server"""

    print('\n(startaudio) starting jack\n')
    jack_cmd_list = ([gc.config['jack_path']]
                        + gc.config['jack_options'].split()
                        + ['-r'] + [str(gc.speaker['fs'])])
    if 'alsa' in gc.config['jack_options']:
        jack_cmd_list += ['-d' + gc.config['system_card']]
    elif not 'dummy' in gc.config['jack_options']:
        print('\n(startaudio) error starting jack: unknown backend')
        sys.exit(-1)
    try:
        jack = sp.Popen(jack_cmd_list)
        # waiting for jackd:
        sp.run('jack_wait -w'.split())
        print('\n(startaudio) jack started :-)')
    except:
        print('\n(startaudio) error starting jack')
        sys.exit()

def init_brutefir():
    """loads brutefir"""

    # cd to brutefir config folder so filter paths are relative to this
    # folder in brutefir_config
    os.chdir(bp.loudspeakers_folder + gc.config['loudspeaker'])
    print(f'\n(startaudio) starting brutefir on {os.getcwd()}')
    sp.Popen([gc.config['brutefir_path'], gc.config['brutefir_options']
            ,'brutefir_config'])
    # waiting for brutefir
    if  pd.wait4result('echo "quit" | nc localhost 3000', 'Welcome',
        tmax=5):
        print('\n(startaudio) brutefir started :-)')
    else:
        print('\n(startaudio) error starting brutefir')
        sys.exit()

def init_server():
    """loads server"""

    print('\n(startaudio) starting server\n')
    try:
        control = sp.Popen(['python3'
                            , bp.server_path])
    except:
        print('\n(startaudio) server didn\'t load')
        sys.exit() # initaudio stopped
    # waiting for server
    total_time = rem_time = 10 * gc.config['command_delay']
    while rem_time:
        print(f'(startaudio) waiting for server ({(total_time-rem_time)}s)')
        try:
            pd.client_socket('status')
            break
        except:
            pass
        rem_time -= 1 * gc.config['command_delay']
        time.sleep(gc.config['command_delay'])
    if rem_time:
        print('\n(startaudio) server started :-)')
    else:
        print('\n(startaudio) server not accesible Bye :-/')
        sys.exit() # initaudio stopped


def init_state_settings():
    """restore audio settings as stored in state.yaml
and takes care of options to reset some of them"""

    # tone reset
    if gc.config['tone_reset_on_startup']:
        pd.client_socket('bass 0')
        pd.client_socket('treble 0')
    else:
        pd.client_socket('bass ' + str(gc.state['bass']))
        pd.client_socket('treble ' + str(gc.state['treble']))
    # balance reset
    if gc.config['balance_reset_on_startup']:
        pd.client_socket('balance 0')
    else:
        pd.client_socket('balance ' + str(gc.state['balance']))
    # loudness reset
    if gc.config['loudness_reset_on_startup']:
        pd.client_socket('loudness_track off')
        pd.client_socket('loudness_ref 0')
    else:
        pd.client_socket('loudness_track ' + gc.state['loudness_track'])
        pd.client_socket('loudness_ref ' + str(gc.state['loudness_ref']))
    # midside reset
    if gc.config['midside_reset_on_startup']:
        pd.client_socket('midside off')
    else:
        pd.client_socket('midside ' + str(gc.state['midside']))
    # optional limited volume on start
    limit_level(gc.config['level_on_startup']
                , gc.config['max_level_on_startup'])
    # restore DRC_set
    pd.client_socket( 'drc ' + str( gc.state['DRC_set'] ) )
    # XO_set will be adjusted when restoring inputs


def init_inputs():
    """restore selected input as stored in state.ini"""

    input = gc.state['input']
    print(f'\n(startaudio) restoring input: {input}')
    # exit if input is 'none'
    if input == 'none':
        return
    # wait for input ports to be up
    ports = pd.gc.inputs[input]['in_ports']
    jc = jack.Client('tmp')
    # lets try 20 times to connect to input ports
    loops = 20
    while loops:
        channels = ('L','R')
        n = len(channels)
        for port_name in ports:
            if jc.get_ports(port_name):
                n -=1
        if n == 0:
            break
        time.sleep(gc.config['command_delay'] * 0.5)
        loops -= 1
    if loops:
        # input ports up and ready :-)
        pd.client_socket('input ' + gc.state['input'], quiet=True)
    else:
        # input ports are down :-(
        print(f'\n(startaudio) time out restoring input \'{input}\''
                                        ', ports not available')


def main(run_level):
    """main loading function"""

    # Jack, Brutefir, Server
    if run_level in ['core', 'all']:
        # load basic audio kernel
        init_jack()
        init_brutefir()
        init_server()
        # inboard players
    if run_level in ['clients', 'all']:
        # launch external clients, sources and clients
        print('\n(startaudio): starting clients...')
        clients_start = pd.read_clients('start')
        for client in clients_start:
            try:
                command_path = f'{bp.clients_folder}{client}'
                p=sp.Popen(command_path.split())
                print(f'pid {p.pid:4}: {client}')
            except:
                print(f'problem launching client {client}')
        # restoring previous state
        init_state_settings()
        # restoring inputs
        init_inputs()
        # some info
        pd.show()


if __name__ == '__main__':

    # switch runlevels
    if sys.argv[1:]:
        run_level = sys.argv[1]
    else:
        run_level = 'all'
    if run_level in ['core', 'all']:
        # stop proccesses
        print('\n(startaudio) stopping proccesses\n')
        stopaudio.main(run_level)
        print('\n(startaudio) starting runlevel ' + run_level)
        main(run_level)
    else:
        print(__doc__)
