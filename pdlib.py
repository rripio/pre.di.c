# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Miscellanea of utility functions for use in predic scripts."""


import socket
import sys
import time
import subprocess as sp
import math as m

import jack
import yaml
import numpy as np

import baseconfig as base
import init


# Used on startaudio.py and stopaudio.py.
def read_clients(phase):
    """
    Read list of programs to start/stop from config/clients.yml file.

    phase: <'start'|'stop'> phase of client activation or deactivation
    """
    clients_list_path = init.clients_path

    with open(clients_list_path) as clients_file:
        clients_dict = yaml.safe_load(clients_file)
        # Init a list of client actions.
        clients = [
            clients_dict[i][phase]
            for i in clients_dict if phase in clients_dict[i]
            ]
    return clients


def read_yaml(filepath):
    """Return dictionary from yaml config file."""
    with open(filepath) as configfile:
        config_dict = yaml.safe_load(configfile)

    return config_dict


def client_socket(data, port, quiet=True):
    """Make a socket for talking to the server."""
    # Avoid void command to reach server and get processed due to encoding.
    if data == '':
        return b'ACK\n'

    server = 'localhost'
    # port = init.config['control_port']

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        try:
            if not quiet:
                print(f'\n(lib) Connecting to {server}, port {str(port)}...')
            s.connect((server, port))
        except socket.gaierror as e:
            print(f'\n(lib) Address-related error connecting to server: {e}')
            sys.exit(-1)
        except socket.error as e:
            print(f'\n(lib) Connection error: {e}')
            sys.exit(-1)
        if not quiet:
            print('\n(lib) Connected')
        try:
            # If a parameter is passed it is send to server.
            s.send(data.encode())
            # Return raw bytes server answer.
            return s.recv(2048)
        except Exception:
            print(f'\n(lib) unexpected error: {sys.exc_info()[0]}')


def get_state():
    """Retrieve state dictionary from server to be used by clients."""
    string = client_socket('status', init.config['control_port'])

    return yaml.safe_load(string.decode().replace('\nOK', ''))


def wait4result(command, answer, tmax=5, interval=0.1):
    """Look for chain "answer" in "command" output."""
    time_start = time.time()

    def elapsed():
        return time.time() - time_start

    while elapsed() < tmax:
        try:
            if init.config['verbose'] in {0, 1}:
                output = {"stderr": sp.DEVNULL}
            else:
                output = {}
            if answer in sp.check_output(
                    command, shell=True, universal_newlines=True, **output):
                if init.config['verbose'] in {1, 2}:
                    print(
                        f'\n(lib) found string "{answer}" in output of '
                        f'command: {command}'
                        )
                return True
        except Exception as e:
            if init.config['verbose'] in {2}:
                print(e)
        time.sleep(interval)
    else:
        if init.config['verbose'] in {1, 2}:
            print(
                f'\n(lib) time out >{tmax}s waiting for string "{answer}"'
                f' in output of command: {command}'
                )
        return False


def wait4source(source, tmax=5, interval=0.1):
    """Wait for source jack ports to be up."""
    source_ports = init.sources[source]['source_ports']
    if wait4ports(source_ports, tmax, interval):
        return True
    else:
        return False


def wait4ports(ports, tmax=5, interval=0.1):
    """Wait for jack ports to be up."""
    time_start = time.time()
    jc = jack.Client('wait_client')

    ports_name = ports[1].split(':', 1)[0]
    while (time.time() - time_start) < tmax:
        # Names of up ports at this very moment as a generator.
        up_ports = (
            port.name for port in
            jc.get_ports(ports_name)
            )
        # Compare sets and, if wanted ports are among up ports,
        # then wanted ports are up and ready :-)
        if set(ports).issubset(set(up_ports)):
            # Go on.
            jc.close()
            return True
        else:
            time.sleep(interval)
    # Time is exhausted and source ports are down :-(
    # Leave function without any connection made.
    jc.close()
    return False


def gain_dB(x):
    """Calculate gain in dB from gain multiplier."""
    return 20 * m.log10(x)


def calc_gain(level):
    """Calculate gain from level and reference gain."""
    gain = level + init.speaker['ref_level_gain']
    return gain


def calc_level(gain):
    """Calculate level from gain and reference gain."""
    level = gain - init.speaker['ref_level_gain']
    return level


def calc_headroom(gain):
    """Calculate headroom from gain and equalizer."""
    tones = {'off': 0, 'on': 1}[init.state['tones']]
    headroom = (base.gain_max
                - gain
                - np.clip(init.state['bass'], 0, None) * tones
                - np.clip(init.state['treble'], 0, None) * tones
                - abs(init.state['balance'])
                )
    return headroom


def calc_source_gain(source):
    """Retrieve source gain shift."""
    return init.sources[source]['gain']


def show():
    """Compose a status report string."""
    source_gain = calc_source_gain(init.state['source'])
    gain = calc_gain(init.state['level']) + source_gain
    headroom = calc_headroom(gain)
    source_headroom = headroom - source_gain

    show_str = f'''
    Loudspeaker:        {init.config['loudspeaker']: >10s}

    fs                  {init.speaker['devices']['samplerate']: 10d}
    Reference level     {init.speaker['ref_level_gain']: 10.1f}

    Mute                {init.state['mute']: >10s}
    Level               {init.state['level']: 10.1f}
    Balance             {init.state['balance']: 10.1f}

    Channels            {init.state['channels']: >10s}
    Channels flip       {init.state['channels_flip']: >10s}
    Polarity            {init.state['polarity']: >10s}
    Polarity flip       {init.state['polarity_flip']: >10s}
    Stereo              {init.state['stereo']: >10s}
    Solo                {init.state['solo']: >10s}

    Tones               {init.state['tones']: >10s}
    Bass                {init.state['bass']: 10.1f}
    Treble              {init.state['treble']: 10.1f}
    Loudness            {init.state['loudness']: >10s}
    Loudness reference  {init.state['loudness_ref']: 10.1f}

    DRC                 {init.state['drc']: >10s}
    DRC set             {init.state['drc_set']: >10s}
    Phase equalizer     {init.state['phase_eq']: >10s}
    EQ                  {init.state['eq']: >10s}
    EQ filter           {init.state['eq_filter']: >10s}

    Sources             {init.state['sources']: >10s}
    Source              {init.state['source']: >10s}
    Source gain         {source_gain: 10.1f}
    Source headroom     {source_headroom: 10.1f}

    Gain                {gain: 10.1f}
    Headroom            {headroom: 10.1f}
    Clamp gain          {init.state['clamp']: >10s}
    '''

    return show_str


help_str = '''
    help                                This help
    status                              Display status
    save                                Save status
    camillaconfig                       Save actual camilladsp config
    ping                                Request an answer from server

    show                                Show a human readable status
    clamp <off|on|toggle>               Set or toggle level clamp
    sources <off|on|toggle>             Set or toggle  sources
    source <input>                      Select source
    drc <off|on|toggle>                 Set or toggle DRC filters
    drc_set <drc_set>                   Select DRC filters set
    phase_eq <off|on|toggle>            Set or toggle phase equalizer filter

    channels <lr|l|r>                   Set input channels selector mode
    channels_flip <off|on|toggle>       Set or toggle channels flip
    polarity <off|on|toggle>            Set or toggle polarity inversion
    polarity_flip <off|on|toggle>       Set or toggle polarity flip
    stereo <normal|mid|side>            Set input channels mixer mode
    solo <lr|l|r>                       Set output channels selector mode

    mute <off|on|toggle>                Set or toggle mute
    loudness <off|on|toggle>            Set or toggle loudness control
    loudness_ref <loudness_ref> [add]   Set loudness reference level
    tones <off|on|toggle>               Set or toggle tone control
    treble <treble> [add]               Set treble level
    bass <bass> [add]                   Set bass level
    balance <balance> [add]             Set balance (- left , + for right)
    level <level> [add]                 Set volume level
    gain <gain>                         Set digital gain

    'add' option makes previous number be an increment
    'camillaconfig' command saves actual config in loudspeaker folder
    '''
