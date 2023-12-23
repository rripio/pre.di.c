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

import init
import stopaudio
import pdlib as pd

from camilladsp import CamillaClient


port = init.config['control_port']


def stop_all():
    """
    stops all audio and the current script
    """

    stopaudio.main('all')
    sys.exit()


def init_jack():
    """
    loads jack server
    """

    try:
        print('\n(startaudio) starting jack\n')
        fs = init.speaker['devices']['samplerate']
        sp.Popen(f'{init.config["jack_command"]} -r {fs}'.split())
        # waiting for jackd:
        tmax = init.config['command_delay'] * 5
        interval = init.config['command_delay'] * 0.1
        if pd.wait4result('jack_lsp', 'system', tmax, interval):
            print('\n(startaudio) jack started :-)')
        else:
            raise Exception('no ports available')
            stop_all()
    except Exception as e:
        print('\n(startaudio) error starting jack: ', e)
        stop_all()


def init_camilladsp():
    """
    loads camilladsp
    """

    try:
        # cd to louspeaker folder so filter paths are relative to this \
        # folder in speaker.yml config file
        os.chdir(init.loudspeaker_path)
        print(f'\n(startaudio) starting camilladsp on {os.getcwd()}')
        sp.Popen((f'{init.config["camilladsp_command"]} -m -w ' +
                  f'-p {init.config["websocket_port"]}').split())

        # wait a bit
        time.sleep(init.config['command_delay'] * 1)

        # connect to camilladsp
        cdsp = CamillaClient("localhost", init.config['websocket_port'])
        cdsp.connect()

        # get general part of camilladsp config

        cdsp_config = init.camilladsp

        # get loudspeaker specific parts of camilladsp config

        # merge loudspeaker specific settings in camilladsp config
        cdsp_config['title'] = init.speaker['title']
        cdsp_config['description'] = init.speaker['description']
        cdsp_config['devices'].update(init.speaker['devices'])
        cdsp_config['filters'].update(init.speaker['filters'])
        cdsp_config['mixers'].update(init.speaker['mixers'])
        cdsp_config['pipeline'].extend(init.speaker['pipeline'])

        # send full config to camilladsp.
        # probably we should check for jack ports here...
        cdsp.config.set_active(cdsp_config)
        cdsp.disconnect()

    except Exception as e:
        print('\n(startaudio) error starting camilladsp: ', e)
        stop_all()


def init_server():
    """
    loads server
    """

    print('\n(startaudio) starting server')

    try:
        sp.Popen((f'{init.config["python_command"]} ' +
                  f'{init.main_folder}/server.py').split())

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

    except Exception as e:
        print('\n(startaudio) server didn\'t load: ', e)
        stop_all()


def set_initial_state():
    """
    set initial state state as last saved or user determined
    """

    state = init.state
    if init.config['use_state_init']:
        for setting in init.state_init:
            state[setting] = init.state_init[setting]
    return state


def init_state_settings(state):
    """
    restore audio settings as stored in state.yaml except source,
    and takes care of options to reset some of them
    """

    # it is assumed that command name and setting name are the same
    #
    # source associated phase_EQ will prevail if use_source_phase_EQ is set \
    # because init_source function is executed after this one

    for setting in (
            'balance',
            'bass',
            'channels',
            'channels_flip',
            'clamp',
            'drc',
            'drc_set',
            'eq',
            'eq_filter',
            'level',
            'loudness',
            'loudness_ref',
            'mute',
            'phase_eq',
            'polarity',
            'polarity_flip',
            'solo',
            'stereo',
            'tones',
            'treble'
            ):
        print(f'{setting} {state[setting]}')
        pd.client_socket(f'{setting} {state[setting]}', port)


def init_source(state):
    """
    restore selected source as stored in state.yml
    """

    source = state['source']
    print(f"\n(startaudio) restoring source '{source}'")
    # wait for source ports to be up
    tmax = init.config['command_delay'] * 15
    interval = init.config['command_delay'] * 0.5
    if pd.wait4source(source, tmax, interval):
        # source ports up and ready :-)
        # switch on source and leave function
        if init.sources[source]['wait_on_start']:
            # some clients (namely mpd) seems to need some extra time after \
            # ports detection for whatever reason
            time.sleep(init.config['command_delay'] * 2)

    else:
        print(f"\n(startaudio) could not connect '{source}' ports")

    # disconnect sources from eventual bad behaving clients
    pd.client_socket('sources off', port, quiet=True)
    # actual source connection
    pd.client_socket('sources on', port, quiet=True)


def main(run_level):
    """
    main loading function
    """

    # jack, brutefir, camilladsp, server
    if run_level in {'core', 'all'}:
        # load basic audio kernel
        init_jack()
        init_camilladsp()
        init_server()

    # inboard players
    if run_level in {'clients', 'all'}:
        # getting operating state
        # do it before launching clients \
        # so they get the correct setting from state file if needed
        state = set_initial_state()

        # activate command_unmute mode downstream
        pd.client_socket('command_unmute', port, quiet=True)

        # restoring previous state
        # exceptionally we add a line feed at the end \
        # since sttings restoring messages don't
        print('\n(startaudio): restoring previous settings:\n')
        init_state_settings(state)

        # write source to state file for use of clients if config ask for it
        if state['sources'] == 'on':
            # just refresh state file
            init.state['source'] = state['source']
            pd.client_socket('save', port, quiet=True)

        # launch external clients, sources and clients
        # exceptionally we add a line feed at the end \
        # since client load messages don't
        print('\n(startaudio): starting clients...\n')
        for client in pd.read_clients('start'):
            try:
                p = sp.Popen(client.split())
                print(f'pid {p.pid:4}: {client}')
            except Exception as e:
                print(f"\n(startaudio) problem launching client '{client}':",
                      e)

        # restoring sources if config mandates so
        if state['sources'] == 'on':
            init_source(state)

        # cancel command_unmute mode downstream \
        # restoring config value
        if init.config['do_mute']:
            pd.client_socket('command_mute', port, quiet=True)

        # save changes to file
        pd.client_socket('save', port, quiet=True)
        print('\n(startaudio): pre.di.c started :-)')


if __name__ == '__main__':

    # switch runlevels
    if sys.argv[1:]:
        run_level = sys.argv[1]
    else:
        run_level = 'all'
    if run_level in {'core', 'clients', 'all'}:
        print(f'\n(startaudio) starting runlevel {run_level}')
        main(run_level)
    else:
        print(__doc__)
