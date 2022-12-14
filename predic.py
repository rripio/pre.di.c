# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""miscellanea of utility functions for use in predic scripts"""


import socket
import sys
import time
import contextlib as cl
import multiprocessing as mp
import subprocess as sp


import jack
import yaml
import numpy as np

import base
import init


# used on startaudio.py and stopaudio.py
def read_clients(phase):
    """reads list of programs to start/stop from config/clients.yml file
    phase: <'start'|'stop'> phase of client activation or deactivation"""

    clients_list_path = base.clients_path

    with open (clients_list_path) as clients_file:
        clients_dict = yaml.safe_load(clients_file)
        # init a list of client actions
        clients = [
            clients_dict[i][phase]
            for i in clients_dict if phase in clients_dict[i]
            ]
    return clients


def client_socket(data, quiet=True):
    """makes a socket for talking to the server"""

    # avoid void command to reach server and get processed due to encoding
    if data == '':
        return b'ACK\n'

    server = 'localhost'
    port = init.config['control_port']

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        try:
            if not quiet:
                print(f'Connecting to {server}, port {str(port)}...')
            s.connect((server,port))
        except socket.gaierror as e:
            print(f'Address-related error connecting to server: {e}')
            sys.exit(-1)
        except socket.error as e:
            print(f'Connection error: {e}')
            sys.exit(-1)
        if not quiet:
            print('Connected')
        try:
            # if a parameter is passed it is send to server
            s.send(data.encode())
            # return raw bytes server answer
            return s.recv(256)
        except Exception:
            print(f'(client) unexpected error: {sys.exc_info()[0]}')


def read_state():
    """retrieve state dictionary from server"""

    return yaml.safe_load(client_socket('status').decode().replace('OK\n', ''))


def wait4result(command, answer, tmax=5, interval=0.1):
    """looks for chain "answer" in "command" output"""

    time_start = time.time()

    def elapsed():
        return time.time() - time_start

    while elapsed() < tmax:
        try:
            if init.config['server_output'] in [0, 1] :
                output={"stderr": sp.DEVNULL}
            else :
                output={}
            if answer in sp.check_output(
                    command, shell=True, universal_newlines=True, **output):
                if init.config['server_output'] in [1, 2]:
                    print(
                        f'\nfound string "{answer}" in output of '
                        f'command: {command}'
                        )
                return True
        except Exception as e:
            if init.config['server_output'] in [2] :
                print(e)
        time.sleep(interval)
    else:
        if init.config['server_output'] in [1, 2]:
            print(
                f'\ntime out >{tmax}s waiting for string "{answer}"'
                f' in output of command: {command}'
                )
        return False


def wait4source(source, tmax=5, interval=0.1):
    """wait for source jack ports to be up"""

    time_start = time.time()
    jc = jack.Client('tmp')
    source_ports = init.sources[source]['source_ports']
    # get base name of ports for up ports query
    source_ports_name = source_ports[1].split(':',1)[0]
    while (time.time() - time_start) < tmax:
        try:
            # names of up source ports at this very moment as a generator
            up_ports = (
                port.name for port in
                jc.get_ports(source_ports_name, is_output=True)
                )
            # compare sets and, if used source ports are among up source ports,
            # then source ports are up and ready :-)
            if (set(source_ports).issubset(set(up_ports))):
            # go on
                return True
            else:
               time.sleep(interval)
        except KeyError:
            print(
                f'\nincorrect source \'{source}\''
                '\n please revise state files\n'
                )
            return False
    # time is exhausted and source ports are down :-(
    # leave function without any connection made
    print(f'\ntime out restoring source \'{source}\', ports not available')
    return False


def jack_loop(clientname):
    """creates a jack loop with given 'clientname'"""
    # CREDITS:
    # https://jackclient-python.readthedocs.io/en/0.4.5/examples.html

    # the jack module instance for our looping ports
    client = jack.Client(name=clientname, no_start_server=True)

    if client.status.name_not_unique:
        client.close()
        print( f'(predic.jack_loop) \'{clientname}\''
                            'already exists in JACK, nothing done.' )
        return

    # will use the multiprocessing.Event mechanism to keep this alive
    event = mp.Event()

    # this sets the actual loop that copies frames from our capture \
    # to our playback ports
    @client.set_process_callback
    def process(frames):
        assert len(client.inports) == len(client.outports)
        assert frames == client.blocksize
        for i, o in zip(client.inports, client.outports):
            o.get_buffer()[:] = i.get_buffer()

    # if jack shutdowns, will trigger on 'event' so that the below \
    # 'whith client' will break.
    @client.set_shutdown_callback
    def shutdown(status, reason):
        print('(predic.jack_loop) JACK shutdown!')
        print('(predic.jack_loop) JACK status:', status)
        print('(predic.jack_loop) JACK reason:', reason)
        # this triggers an event so that the below 'with client' \
        # will terminate
        event.set()

    # create the ports
    for n in 1, 2:
        client.inports.register(f'input_{n}')
        client.outports.register(f'output_{n}')
    # client.activate() not needed, see below

    # this is the keeping trick
    with client:
        # when entering this with-statement, client.activate() is called
        # this tells the JACK server that we are ready to roll
        # our above process() callback will start running now

        print( f'(predic.jack_loop) running {clientname}' )
        try:
            event.wait()
        except KeyboardInterrupt:
            print('\n(predic.jack_loop) Interrupted by user')
        except Exception as e:
            print('\n(predic.jack_loop)  Terminated: ', e)


def calc_gain(level):
    """calculates gain from level and reference gain"""

    gain = level + init.speaker['ref_level_gain']
    return gain


def calc_level(gain):

    level = gain - init.speaker['ref_level_gain']
    return level


def calc_headroom(gain, balance, eq_mag):
    """calculates headroom from gain and equalizer"""

    headroom = base.gain_max - gain - np.max(eq_mag) - abs(balance)
    return headroom


def calc_source_gain(source):

    return (init.sources[source]['gain'])


def show(throw_it=None, state=init.state):
    """shows a status report"""

    source_gain = calc_source_gain(init.state['source'])
    gain = calc_gain(init.state['level']) + source_gain
    headroom = calc_headroom(gain, init.state['balance'], init.target['mag'])

    print()
    print(f"Loudspeaker: {init.config['loudspeaker']}")
    print()
    print(f"fs                  {init.speaker['fs']:6}")
    print(f"Reference level     {init.speaker['ref_level_gain']: 6.1f}")

    print()
    print(f"Mute                {init.state['mute']:>6s}")
    print(f"Level               {init.state['level']: 6.1f}")
    print(f"Balance             {init.state['balance']: 6.1f}")

    print()
    print(f"Channels            {init.state['channels']:>6s}")
    print(f"Polarity inversion  {init.state['polarity_inv']:>6s}")
    print(f"Polarity flip       {init.state['polarity_flip']:>6s}")
    print(f"Midside             {init.state['midside']:>6s}")
    print(f"Solo                {init.state['solo']:>6s}")

    print()
    print(f"Bass                {init.state['bass']: 6.1f}")
    print(f"Treble              {init.state['treble']: 6.1f}")
    print(f"Loudness            {init.state['loudness']:>6s}")
    print(f"Loudness reference  {init.state['loudness_ref']: 6.1f}")

    print()
    print(f"Crossover set       {init.state['xo']:>6s}")
    print(f"DRC set             {init.state['drc']:>6s}")

    print()
    print(f"Source               {init.state['source']:>6s}")
    print(f'Source gain          {source_gain: 6.1f}')

    print()
    print(f"Gain                {gain: 6.1f}")
    print(f"Headroom            {headroom: 6.1f}")

    print('\n')

    return state

def show_file(throw_it=None, state=init.state):
    """writes a status report to temp file"""

    with open('/tmp/predic', 'w') as f:
        with cl.redirect_stdout(f):
            state = show()
    return state
