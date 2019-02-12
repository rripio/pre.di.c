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

"""Miscellanea of utility functions for use in predic scripts"""


import socket
import sys
import time
import os
import numpy as np
import subprocess as sp
import contextlib as cl
import threading

import jack

import basepaths as bp
import getconfigs as gc


def read_scripts():
    """reads list of scripts to launch from config/scripts file"""

    with open (bp.script_list_path) as scripts_file:
        # init a list of scripts to load
        scripts = []
        for line in scripts_file:
            # skip blank lines
            if not line.strip():
                continue
            # skip commented lines
            if line.strip()[0] != '#':
                # dispise options if incorrectly set
                script = line.split()[0]
                scripts.append(script)
    return scripts


def start_pid(command, alias):
    """starts a program and writes its pid
    command: full path with options
    alias  : name given for pid retrieving and error output"""

    try:
        p = sp.Popen(command.split())
        print(f'\tpid {p.pid:4}: {alias}')
        with open(f'{bp.pids_folder}{alias}.pid', 'w') as pidfile:
            pidfile.write(f'{p.pid}')
    except OSError as err:
        print(f'error launching {alias}:\n\t{err}')
    except:
        print(f'problem launching {alias}')


def kill_pid(script):
    """kills a script process after retrieving its saved pid"""

    try:
        pid_path = f'{bp.pids_folder}{script}.pid'
        with open(pid_path) as pidfile:
            pid = int(pidfile.readline())
            os.remove(pid_path)
            os.kill(pid, 9)
    except:
        print(f'problem killing {script}')

def jack_loop(clientname):
    """creates a jack loop with given 'clientname'"""
    # CREDITS:  https://jackclient-python.readthedocs.io/en/0.4.5/examples.html

    # The jack module instance for our looping ports
    client = jack.Client(name=clientname, no_start_server=True)

    if client.status.name_not_unique:
        client.close()
        print( f'(predic.jack_loop) \'{clientname}\' already exists in JACK, nothing done.' )
        return

    # Will use the threading.Event mechanism to keep this alive
    event = threading.Event()

    # This sets the actual loop that copies frames from our capture to our playback ports
    @client.set_process_callback
    def process(frames):
        assert len(client.inports) == len(client.outports)
        assert frames == client.blocksize
        for i, o in zip(client.inports, client.outports):
            o.get_buffer()[:] = i.get_buffer()

    # If jack shutdowns, will trigger on 'event' so that the below 'whith client' will break.
    @client.set_shutdown_callback
    def shutdown(status, reason):
        print('(predic.jack_loop) JACK shutdown!')
        print('(predic.jack_loop) JACK status:', status)
        print('(predic.jack_loop) JACK reason:', reason)
        # This triggers an event so that the below 'with client' will terminate
        event.set()

    # Create the ports
    for n in 1, 2:
        client.inports.register(f'input_{n}')
        client.outports.register(f'output_{n}')
    # client.activate() not needed, see below

    # This is the keeping trick
    with client:
        # When entering this with-statement, client.activate() is called.
        # This tells the JACK server that we are ready to roll.
        # Our above process() callback will start running now.

        print( f'(predic.jack_loop) running {clientname}' )
        try:
            event.wait()
        except KeyboardInterrupt:
            print('\n(predic.jack_loop) Interrupted by user')
        except:
            print('\n(predic.jack_loop)  Terminated')


def server_socket(host, port):
    """Makes a socket for listening clients"""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        print(f'(server) Error creating socket: {e}')
        sys.exit(-1)
    # we use opción socket.SO_REUSEADDR to avoid this error:
    # socket.error: [Errno 98] Address already in use
    # that can happen if we reinit this script.
    # This is because the previous execution has left the socket in a
    # TIME_WAIT state, and cannot be immediately reused.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # tcp socket
    try:
        s.bind((host, port))
    except:
        print('(server) Error binding port', port)
        s.close()
        sys.exit(-1)

    # return socket state
    return s


def client_socket(data, quiet=True):
    """Makes a socket for talking to the server"""

    server = 'localhost'
    port = gc.config['control_port']

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        try:
            if not quiet: print(f'Connecting to {server}, port {str(port)}...')
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
            # and then connection is closed
            if data:
                s.send(data.encode())
        except:
            print(f'(client) unexpected error: {sys.exc_info()[0]}')
        if not quiet:
            print('Closing connection...')


def wait4result(command, answer, tmax=4, quiet=False):
    """looks for chain "answer" in "command" output"""

    # wait tmax seconds to get an answer
    tryings =  20
    refresh_time = float(tmax) / tryings
    while tryings:
        try:
            if answer in sp.check_output(command, shell=True,
                        universal_newlines=True):
                if not quiet:
                    print('found {answer} in command {command}')
                break
        except:
            pass
        tryings -= 1
        time.sleep(refresh_time)

    if tryings:
        return True
    else:
        if not quiet:
            print(f'Time out >{tmax}s waiting for{answer}'
                    f' in command {command}')
        return False


def calc_gain(level, input):

    input_gain = calc_input_gain(input)
    gain = (level + gc.speaker['ref_level_gain'] + input_gain)
    return gain


def calc_level(gain, input):

    input_gain = calc_input_gain(input)
    level = (gain - gc.speaker['ref_level_gain'] - input_gain)
    return level


def calc_headroom(gain, balance, eq_mag):
    """ calculate headroom from gain and equalizer """

    headroom = ( gc.config['gain_max'] - gain - np.max(eq_mag)
                    - abs(balance/2))
    return headroom


def calc_input_gain(input):

    return (gc.inputs[input]['gain'] if input in gc.inputs else 0)


def get_target():

    # reload target, so we can change it for testing
    # overwriting the target files outside predic
    target_mag = np.loadtxt(gc.target_mag_path)
    target_pha = np.loadtxt(gc.target_pha_path)

    return target_mag, target_pha


def show(throw_it=None, state=gc.state):
    """ shows a status report """

    gain = calc_gain(gc.state['level'] , gc.state['input'])
    headroom = calc_headroom(gain, gc.state['balance'], get_target()[0])
    input_gain = calc_input_gain(gc.state['input'])
    tracking_loud = (' ' if gc.state['loudness_track'] else '(tracking off)')

    print()
    print(f"Loudspeaker is {gc.config['loudspeaker']}")
    print()
    print(f"fs             {gc.speaker['fs']:6}")
    print(f"Ref level gain {gc.speaker['ref_level_gain']: 6.1f}")

    print()
    muted = ('(muted)' if gc.state['muted'] else ' ')
    print(f"Level          {gc.state['level']: 6.1f}", muted)
    print(f"Balance        {gc.state['balance']: 6.1f}")
    print(f"Polarity            {gc.state['polarity']:6}")
    if gc.state['mono']:
        print(f"Mono           {'on':>6s}")
    else:
        print(f"Mono           {'off':>6s}")

    print()
    print(f"Bass           {gc.state['bass']: 6.1f}")
    print(f"Treble         {gc.state['treble']: 6.1f}")
    print(f"Loudness ref   {gc.state['loudness_ref']: 6.1f}", tracking_loud)

    print()
    print(f"Crossover set  {gc.state['XO_set']:>6s}")
    print(f"DRC set        {gc.state['DRC_set']:>6s}")
    print(f"PEQ            {gc.state['PEQ_set']:>6s}")

    print()
    print(f"Input          {gc.state['input']:>6s}")
    print(f'Input gain     {input_gain: 6.1f}')

    print()
    print(f"Gain           {gain: 6.1f}")
    print(f"Headroom       {headroom: 6.1f}")

    print('\n')

    return state

def show_file(throw_it=None, state=gc.state):
    """ writes a status report to temp file """

    with open('/tmp/predic', 'w') as f:
        with cl.redirect_stdout(f):
            state = show()
    return state
