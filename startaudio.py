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

"""
Starts pre.di.c audio system
    Usage:
    startaudio.py [ core | clients | all ]   (default 'all')
    core: jack, brutefir, server
    players: everything else (players and clients)
    all: all of the above
"""

import sys
import os
import time
import shlex
import subprocess as sp

import jack

import stopaudio
import predic as pd
import basepaths as bp
import getconfigs as gc


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
    jack = sp.Popen(jack_cmd_list)
    # waiting for jackd:
    if pd.wait4result('jack_lsp', 'system'):
        print('\n(startaudio) jack started :-)')
    else:
        print('\n(startaudio) error starting jack')
        pd.stop_all()


def init_brutefir():
    """loads brutefir"""

    # cd to brutefir config folder so filter paths are relative to this
    # folder in brutefir_config
    os.chdir(bp.loudspeakers_folder + gc.config['loudspeaker'])
    print(f'\n(startaudio) starting brutefir on {os.getcwd()}')
    sp.Popen([gc.config['brutefir_path'], gc.config['brutefir_options']
            ,'brutefir_config'])
    # waiting for brutefir
    if  pd.wait4result('echo "quit" | nc localhost 3000 2>/dev/null',
                                                            'Welcome'):
        print('\n(startaudio) brutefir started :-)')
    else:
        print('\n(startaudio) error starting brutefir')
        pd.stop_all()


def init_server():
    """loads server"""

    print('\n(startaudio) starting server\n')
    try:
        control = sp.Popen(['python3'
                            , bp.server_path])
    except:
        print('\n(startaudio) server didn\'t load')
        stopaudio.main('all')
        sys.exit()
    # waiting for server
    if pd.wait4result('echo ping| nc localhost 9999 2>/dev/null', 'OK'):
        print('\n(startaudio) server started :-)')
    else:
        print('\n(startaudio) server not accesible Bye :-/')
        pd.stop_all()


def init_state_settings(state):
    """restore audio settings as stored in state.yaml
and takes care of options to reset some of them"""

    # tone
    pd.client_socket('bass ' + str(state['bass']))
    pd.client_socket('treble ' + str(state['treble']))
    # balance
    pd.client_socket('balance ' + str(state['balance']))
    # loudness
    pd.client_socket('loudness ' + state['loudness'])
    pd.client_socket('loudness_ref ' + str(state['loudness_ref']))
    # midside
    pd.client_socket('midside ' + str(state['midside']))
    # volume
    pd.client_socket('level ' + str(state['level']))
    # restore DRC_set
    pd.client_socket('drc ' + str( state['DRC_set']))
    # XO_set will be adjusted when restoring inputs


def init_inputs(state):
    """restore selected input as stored in state.ini"""

    input = state['input']
    print(f'\n(startaudio) restoring input: {input}')
    # exit if input is 'none'
    if input == 'none':
        return
    # wait for input ports to be up
    ports = pd.gc.inputs[input]['in_ports']
    jc = jack.Client('tmp')

    total_time_factor = 10
    total_time = rem_time = total_time_factor * gc.config['command_delay']
    interval_factor = 10
    interval = gc.config['command_delay'] / interval_factor

    while rem_time:
        channels = ('L','R')
        n = len(channels)
        for port_name in ports:
            if jc.get_ports(port_name):
                n -=1
        if n == 0:
            break
        rem_time -= interval
        time.sleep(interval)
    if rem_time:
        # input ports up and ready :-)
        pd.client_socket('input ' + state['input'], quiet=True)
    else:
        # input ports are down :-(
        print(f'\n(startaudio) time out restoring input \'{input}\''
                                        ', ports not available')


def get_state():
    """set initial state state as last saved or as user determined"""

    state = gc.state

    if gc.config['use_state_init']:
        state_init = gc.state_init
        for setting in state_init:
             if state_init[setting]:
                state[setting] = state_init[setting]

    return state


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
        # getting operating state
        state = get_state()
        # restoring previous state
        init_state_settings(state)
        # restoring inputs
        init_inputs(state)
        # some info
        pd.show()


if __name__ == '__main__':

    # switch runlevels
    if sys.argv[1:]:
        run_level = sys.argv[1]
    else:
        run_level = 'all'
    if run_level in ['core', 'clients', 'all']:
        print('\n(startaudio) starting runlevel ' + run_level)
        main(run_level)

    else:
        print(__doc__)
