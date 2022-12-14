#! /usr/bin/env python3

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

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

import base
import init
import stopaudio
import predic as pd


def stop_all():
    """ stops all audio and the current script """

    stopaudio.main('all')
    sys.exit()


def init_jack():
    """loads jack server"""

    print('\n(startaudio) starting jack\n')
    jack = sp.Popen(
        f'{init.config["jack_command"]} -r {init.speaker["fs"]}'.split()
        )
    # waiting for jackd:
    tmax = init.config['command_delay'] * 5
    interval = init.config['command_delay'] * 0.1
    if pd.wait4result('jack_lsp', 'system', tmax, interval):
        print('\n(startaudio) jack started :-)')
    else:
        print('\n(startaudio) error starting jack')
        stop_all()


def init_brutefir():
    """loads brutefir"""

    # cd to brutefir config folder so filter paths are relative to this \
    # folder in brutefir_config
    os.chdir(base.loudspeakers_folder + init.config['loudspeaker'])
    print(f'\n(startaudio) starting brutefir on {os.getcwd()}')
    brutefir = sp.Popen(
        f'{init.config["brutefir_command"]} brutefir_config'.split()
        )
    # waiting for brutefir
    tmax = init.config['command_delay'] * 5
    interval = init.config['command_delay'] * 0.1
    if pd.wait4result(
            'echo "quit" | nc localhost 3000 2>/dev/null',
            'Welcome', tmax, interval):
        print('\n(startaudio) brutefir started :-)')
    else:
        print('\n(startaudio) error starting brutefir')
        stop_all()


def init_server():
    """loads server"""

    print('\n(startaudio) starting server\n')
    try:
        control = sp.Popen(f'python3 {base.main_folder}server.py'.split())
    except Exception as e:
        print('\n(startaudio) server didn\'t load: ', e)
        stopaudio.main('all')
        sys.exit()
    # waiting for server
    tmax = init.config['command_delay'] * 5
    interval = init.config['command_delay'] * 0.1
    if pd.wait4result(
            'echo ping| nc localhost 9999 2>/dev/null',
            'OK', tmax, interval):
        print('\n(startaudio) server started :-)')
    else:
        print('\n(startaudio) server not accesible Bye :-/')
        stop_all()


def set_initial_state():
    """set initial state state as last saved or as user determined"""

    state = init.state
    if init.config['use_state_init']:
        state_init = init.state_init
        for setting in state_init:
            state[setting] = state_init[setting]
    return state


def init_state_settings(state):
    """restore audio settings as stored in state.yaml except source, 
and takes care of options to reset some of them"""

    # it is assumed that command name and setting name are the same
    #
    # source associated xo will prevail if use_source_xo is set \
    # because init_sources function is executed after this one

    for setting in [
            'xo',
            'drc',
            'channels',
            'polarity_inv',
            'polarity_flip',
            'midside',
            'solo',
            'mute',
            'loudness',
            'loudness_ref',
            'treble',
            'bass',
            'balance',
            'level'
            ]:
        pd.client_socket(f'{setting} {state[setting]}')


def init_sources(state):
    """restore selected source as stored in state.yml"""

    source = state['source']
    print(f'\n(startaudio) restoring source: {source}')
    # wait for source ports to be up
    tmax = init.config['command_delay'] * 15
    interval = init.config['command_delay'] * 0.5
    if pd.wait4source(source, tmax, interval):
        # source ports up and ready :-)
        # switch on source and leave function
        # some clients (mpd) seems to need some extra time after
        # ports detection for whatever reason
        time.sleep(init.config['command_delay'] * 2)
        try:
            pd.client_socket('source ' + source, quiet=True)
        except Exception as e:
            print('\n(startaudio) error connecting source: ', e)
        return True
    else:
        return False


def main(run_level):
    """main loading function"""

    # jack, brutefir, server
    if run_level in ['core', 'all']:
        # load basic audio kernel
        init_jack()
        init_brutefir()
        init_server()
    # inboard players
    if run_level in ['clients', 'all']:
        # getting operating state
        # do it before launching clients \
        # so they get the correct setting from state file if needed
        state = set_initial_state()
        # restoring previous state
        init_state_settings(state)
        # write source to state file for use of clients if config ask for it
        if init.config['connect_sources']:
            # just refresh state file
            init.state['source'] = state['source']
            pd.client_socket('save', quiet=True)
       # launch external clients, sources and clients
        print('\n(startaudio): starting clients...')
        clients_start = pd.read_clients('start')
        for client in clients_start:
            try:
                command_path = f'{base.clients_folder}{client}'
                p=sp.Popen(command_path.split())
                print(f'pid {p.pid:4}: {client}')
            except Exception as e:
                print(f'problem launching client {client}: ', e)
        # restoring sources if config mandates so
        if init.config['connect_sources']:
            init_sources(state)
        # some info
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
