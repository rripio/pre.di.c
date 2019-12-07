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
import subprocess as sp

import jack

import stopaudio
import init
import predic as pd
import getconfigs as gc


def init_jack():
    """loads jack server"""

    print('\n(startaudio) starting jack\n')
    jack = sp.Popen(
                f'{gc.config["jack_command"]} -r {gc.speaker["fs"]}'.split())
    # waiting for jackd:
    if pd.wait4result('jack_lsp', 'system'):
        print('\n(startaudio) jack started :-)')
    else:
        print('\n(startaudio) error starting jack')
        pd.stop_all()


def init_brutefir():
    """loads brutefir"""

    # cd to brutefir config folder so filter paths are relative to this \
    # folder in brutefir_config
    os.chdir(init.loudspeakers_folder + gc.config['loudspeaker'])
    print(f'\n(startaudio) starting brutefir on {os.getcwd()}')
    brutefir = sp.Popen(
                f'{gc.config["brutefir_command"]} brutefir_config'.split())
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
        control = sp.Popen(f'python3 {init.main_folder}server.py'.split())
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

    # it is assumed that command name and setting name are the same
    #
    # input associated xo will prevail if use_input_xo is set \
    # because init_inputs function is executed after this one

    for setting in [
            'xo',
            'drc',
            'polarity',
            'midside',
            'mute',
            'solo',
            'loudness',
            'loudness_ref',
            'treble',
            'bass',
            'balance',
            'level'
            ]:
        pd.client_socket(f'{setting} {state[setting]}')


def init_inputs(state):
    """restore selected input as stored in state.ini"""

    input = state['input']
    print(f'\n(startaudio) restoring input: {input}')
    # wait for input ports to be up
    time_start = time.time()
    tmax = gc.config['command_delay'] * 5
    interval = gc.config['command_delay'] * 0.1
    # make a jack client and tried to connect it to input ports
    jc = jack.Client('tmp')
    while (time.time() - time_start) < tmax:
        connected = False
        try:
            for port_name in gc.inputs[input]['in_ports']:
                connected = connected and jc.get_ports(port_name)
        except KeyError:
            print(f'\n(startaudio) incorrect input \'{input}\''
                            '\n(startaudio) please revise state files\n')
            return False
        if connected:
            # input ports up and ready :-)
            # switch on input and leave function
            pd.client_socket('input ' + state['input'], quiet=True)
            return True
        else:
            time.sleep(interval)
    # time is exhausted and input ports are down :-(
    # leave function without any connection made
    print(f'\n(startaudio) time out restoring input \'{input}\''
                                    ', ports not available')
    return True


def get_state():
    """set initial state state as last saved or as user determined"""

    state = gc.state
    if gc.config['use_state_init']:
        state_init = gc.state_init
        for setting in state_init:
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
                command_path = f'{init.clients_folder}{client}'
                p=sp.Popen(command_path.split())
                print(f'pid {p.pid:4}: {client}')
            except:
                print(f'problem launching client {client}')
        # getting operating state
        state = get_state()
        # restoring previous state
        init_state_settings(state)
        # restoring inputs if config mandates so
        if gc.config['connect_inputs']:
            if init_inputs(state):
                # some info
                # if input is wrong will make input gain retrieval brake
                # and so show() would spit some garbage
                pd.show()


if __name__ == '__main__':

    # switch runlevels
    if sys.argv[1:]:
        run_level = sys.argv[1]
    else:
        run_level = 'all'
    if run_level in ['core', 'clients', 'all']:
        print(f'\n(startaudio) starting runlevel {run_level}')
        main(run_level)
    else:
        print(__doc__)
