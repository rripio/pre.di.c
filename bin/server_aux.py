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

""" A TCP server that listen for certain tasks to be executed on local:
    - Switches on/off an amplifier
    - Controls and gets metadata info from the player we are listen to
    - User macros under ~/macros
    - Other tasks are still not implemented
"""

# This server is secured by allowing only certain orders
# to be translated to actual local commands.

#####################
LISTENING_PORT = 9988
#####################

import socket
import sys
import time
import subprocess as sp
import yaml
import players # to comunicate to the current music player

def process(data):
    """
        Only certain received 'data' will be validated and processed,
        then returns back some useful info to the asking client.
    """

    # First clearing the new line
    data = data.replace('\n','')

    # A custom script that switches on/off the amplifier
    # notice: subprocess.check_output(cmd) returns bytes-like,
    #         but if cmd fails an exception will be raised, so used with 'try'
    if data == 'ampli on':
        try:
            sp.check_output( '/home/predic/bin_custom/ampli.sh on'.split() )
            return b'done'
        except:
            return b'error'
    elif data == 'ampli off':
        try:
            sp.check_output( '/home/predic/bin_custom/ampli.sh off'.split() )
            return b'done'
        except:
            return b'error'

    # Queries the current music player
    elif data == 'player_get_meta':
        return players.get_meta().encode()
    elif data == 'player_state':
        return players.control('state')
    elif data == 'player_stop':
        return players.control('stop')
    elif data == 'player_pause':
        return players.control('pause')
    elif data == 'player_play':
        return players.control('play')
    elif data == 'player_next':
        return players.control('next')
    elif data == 'player_previous':
        return players.control('previous')

    # User macros: macro files are named this way: '~/macros/N_macro_name',
    #              so N will serve as button keypad position from web control page
    elif data[:6] == 'macro_':
        try:
            cmd = '/home/predic/macros/' + data[6:]
            sp.run( "'" + cmd + "'", shell=True ) # needs shell to user bash scripts to work
            return b'done'
        except:
            return b'error'


def server_socket(host, port):
    """ Makes a socket for listening clients """

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
        print('(server_aux) Error binding port', port)
        s.close()
        sys.exit(-1)

    # return socket state
    return s

if __name__ == '__main__':

    verbose = False
    fsocket = server_socket('localhost', LISTENING_PORT)

    for opc in sys.argv:
        if '-v' in opc:
            verbose = True

    # main loop to proccess conections
    backlog = 10
    while True:
        # listen ports
        fsocket.listen(10)  # number of connections in queue
        if verbose:
            print(f'(server_aux) listening on \'localhost\':{LISTENING_PORT}')
        # accept client connection
        sc, addr = fsocket.accept()
        # somo info
        if verbose:
            print(f'(server_aux) connected to client {addr[0]}')
        # buffer loop to proccess received command
        while True:
        # reception
            data = sc.recv(4096).decode()
            if not data:
                # nothing in buffer, client has disconnected too soon
                if verbose:
                    print('(server_aux) client disconnected. '
                                           'Closing connection...')
                sc.close()
                break
            elif data.rstrip('\r\n') == 'status':
                # echo state to client as YAML string
                sc.send(yaml.dump( 'status: running',
                                   default_flow_style=False).encode() )
                sc.send(b'OK\n')
            elif data.rstrip('\r\n') == 'quit':
                sc.send(b'OK\n')
                if verbose:
                    print('(server_aux) closing connection...')
                sc.close()
                break
            elif data.rstrip('\r\n') == 'shutdown':
                sc.send(b'OK\n')
                if verbose:
                    print('(server_aux) closing connection...')
                sc.close()
                fsocket.close()
                sys.exit(1)
            else:
                # a command to run has been received in 'data':
                if verbose:
                    print ('>>> ' + data)
                # process() will validate the data, and if so then executed
                result = process(data)
                if result:
                    sc.send( result )
                else:
                    sc.send( b'ACK\n' )

                if verbose:
                    print(f'(server_aux) connected to client {addr[0]}')

            # wait a bit, loop again
            time.sleep(0.01)
