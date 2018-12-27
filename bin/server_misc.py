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

"""
    A general purpose TCP server for pre.di.c to process auxiliary jobs

    Use:     server_misc.py <processing_module>

    e.g:     server_misc.py players
             server_misc.py aux
"""
# TODO: avoid time.sleep under run_server() maybe 'threading' or 'with' ¿?

# LISTENING ADDRESS & PORT are configured into 'config/config.yml'
from getconfigs import config

# The 'verbose' option can be useful to debug:
verbose = False

import socket
import sys
import time
import subprocess as sp

def server_socket(host, port):
    """ Makes a socket that listen to clients """

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        print( f'(server) Error creating socket: {e}' )
        sys.exit(-1)
    # We use socket.SO_REUSEADDR to avoid this error:
    # socket.error: [Errno 98] Address already in use
    # that can happen if we reinit this script.
    # This is because the previous execution has left the socket in a
    # TIME_WAIT state, and cannot be immediately reused.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # the tcp socket
    try:
        s.bind((host, port))
    except:
        print( f'(server_misc [{service}]) Error binding port', port )
        s.close()
        sys.exit(-1)

    # returns the socket object
    return s

def run_server(host, port, verbose=False):

    # create the socket
    mysocket = server_socket(host, port)

    # main loop to proccess connections
    maxconns = 10
    while True:
        # listen ports
        mysocket.listen(maxconns)  # number of connections in queue
        if verbose:
            print( f'(server_misc [{service}]) listening on \'localhost\':{port}' )
        # accept client connection
        sc, remote = mysocket.accept()
        # somo info
        if verbose:
            print( f'(server_misc [{service}]) connected to client {remote[0]}' )

        # buffer loop to proccess received command
        while True:
            # reception
            data = sc.recv(4096).decode()

            if not data:
                # nothing in buffer, client has disconnected too soon
                if verbose:
                    print (f'(server_misc [{service}]) Client disconnected. '
                          '              Closing connection...' )
                sc.close()
                break

            # Some reserved words for controling the communication:
            elif data.rstrip('\r\n') == 'quit':
                sc.send(b'OK\n')
                if verbose:
                    print( f'(server_misc [{service}]) closing connection...' )
                sc.close()
                break

            elif data.rstrip('\r\n') == 'shutdown':
                sc.send(b'OK\n')
                if verbose:
                    print( f'(server_misc [{service}]) closing connection...' )
                sc.close()
                mysocket.close()
                sys.exit(1)

            # If not a reserved word, then process the received thing:
            else:
                if verbose:
                    print  ('>>> ' + data )
                
                ############################################################
                # THE PROCESSING MODULE IMPORTED AT STARTING UP THIS SERVER,
                # must use the the do() function from the  module.
                result = processing.do(data)
                ############################################################

                # And send back the result
                if result:
                    sc.send( result )
                else:
                    sc.send( b'ACK\n' )

                if verbose:
                    print( f'(server_misc [{service}]) connected to client {remote[0]}' )

            # wait a bit, loop again
            time.sleep(0.01)

if __name__ == "__main__":
    
    service = sys.argv[1]

    address = config[ service + '_address' ]
    port    = config[ service + '_port' ]

    try:
        processing = __import__(service)
        run_server( host=address, port=port, verbose=verbose )

    except:
        print( f'(server_misc) error trying processing module \'{service}\'. Bye.' )
