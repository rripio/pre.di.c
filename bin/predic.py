#!/usr/bin/env python3

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
import jack
import threading

import basepaths as bp
import getconfigs as gc

def jack_loop(clientname):
    """ creates a jack loop with given 'clientname'
        NOTICE: this process will keep running until broken,
                so if necessary you'll need to thread this when calling here.
    """
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


def start_pid(command, alias, redir_file=None):
    """starts a program and writes its pid
    command:    full executable path with options
    alias  :    name given for pid retrieving and error output
    redir_file: a file object to redirect the executable output """

    try:
        if redir_file:
            p = sp.Popen( command.split(), shell=False, stdout=redir_file, stderr=redir_file )
        else:
            p = sp.Popen( command.split() )
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
                    print(f'found {answer} in command {command}')
                break
        except:
            pass
        tryings -= 1
        time.sleep(refresh_time)

    if tryings:
        return True
    else:
        if not quiet:
            print(f'Time out >{tmax}s waiting for {answer}'
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


def show( throw_it=None, state=gc.state ):
    """ A status report addressed to:
        - stdout
        - and /tmp/predic for others to get this info
    """

    gain            = calc_gain(gc.state['level'] , gc.state['input'])
    headroom        = calc_headroom(gain, gc.state['balance'], get_target()[0])
    input_gain      = calc_input_gain(gc.state['input'])
    muted           = ('(muted)' if gc.state['muted'] else ' ')
    tracking_loud   = (' ' if gc.state['loudness_track'] else '(tracking off)')

    tmp  = "\n"
    tmp += ( f"Loudspeaker is {gc.config['loudspeaker']}\n" )
    tmp += "\n"
    tmp += ( f"fs             {gc.speaker['fs']:6}\n" )
    tmp += ( f"Ref level gain {gc.speaker['ref_level_gain']: 6.1f}\n" )

    tmp += "\n"
    tmp += ( f"Level          {gc.state['level']: 6.1f} " + muted + "\n")
    tmp += ( f"Balance        {gc.state['balance']: 6.1f}\n" )
    tmp += ( f"Polarity            {gc.state['polarity']:6}\n" )
    if gc.state['mono']:
        tmp += ( f"Mono           {'on':>6s}\n" )
    else:
        tmp += ( f"Mono           {'off':>6s}\n" )

    tmp += "\n"
    tmp += ( f"Bass           {gc.state['bass']: 6.1f}\n" )
    tmp += ( f"Treble         {gc.state['treble']: 6.1f}\n" )
    tmp += ( f"Loudness ref   {gc.state['loudness_ref']: 6.1f} " + tracking_loud + "\n")

    tmp += "\n"
    tmp += ( f"Crossover set  {gc.state['XO_set']:>6s}\n" )
    tmp += ( f"DRC set        {gc.state['DRC_set']:>6s}\n" )
    tmp += ( f"PEQ            {gc.state['PEQ_set']:>6s}\n" )
    tmp += "\n"
    tmp += ( f"Input          {gc.state['input']:>6s}\n" )
    tmp += ( f'Input gain     {input_gain: 6.1f}\n' )

    tmp += "\n"
    tmp += ( f"Gain           {gain: 6.1f}\n" )
    tmp += ( f"Headroom       {headroom: 6.1f}\n" )
    tmp += "\n"

    # writes the report to stdout
    print( tmp )
            
    # and to /tmp/predic
    f = open( '/tmp/predic', 'w')
    f.write(tmp)
    f.close()
    
    return state
