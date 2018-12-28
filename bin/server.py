#!/usr/bin/env python3

# Copyright (c) 2018 Roberto Ripio, Rafael Sánchez
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
    A general purpose TCP server for pre.di.c to run processing modules

    Use:     server.py <processing_module>

    e.g:     server.py control
             server.py aux
"""

####################################################################
# The LISTENING ADDRESS & PORT will be read from 'config/config.yml'
from getconfigs import config
####################################################################

# The 'verbose' option can be useful when debugging:
verbose = False

import socket
import sys

def server_socket(host, port):
    """ Returns a socket 's' that listen to clients """

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
        print( f'(server.py [{service}]) Error binding port', port )
        s.close()
        sys.exit(-1)

    # returns the socket object
    return s

def run_server(host, port, verbose=False):
    """ This is the server itself.
        Inside, it is called the desired processing module
        to perform actions and giving results.
    """

    # Creates the socket
    mysocket = server_socket(host, port)

    # Main loop to proccess connections
    maxconns = 10
    while True:
        # Listen for a queue of connections
        mysocket.listen(maxconns)
        if verbose:
            print( f'(server.py [{service}]) listening on \'localhost\':{port}' )

        # Waits for a client to be connected:
        sc, remote = mysocket.accept()
        if verbose:
            print( f'(server.py [{service}]) connected to client {remote[0]}' )

        # A buffer loop to proccess received data
        while True:
            # Reception
            data = sc.recv(4096).decode()

            if not data:
                # Nothing in buffer, then will close because the client has disconnected too soon.
                if verbose:
                    print (f'(server.py [{service}]) Client disconnected. \
                             Closing connection...' )
                sc.close()
                break

            # Reserved words for controling the communication ('quit' or 'shutdown')
            elif data.rstrip('\r\n') == 'quit':
                sc.send(b'OK\n')
                if verbose:
                    print( f'(server.py [{service}]) closing connection...' )
                sc.close()
                break

            elif data.rstrip('\r\n') == 'shutdown':
                sc.send(b'OK\n')
                if verbose:
                    print( f'(server.py [{service}]) Shutting down the server...' )
                sc.close()
                mysocket.close()
                sys.exit(1)

            # If not a reserved word, then process the received data as a command:
            else:
                if verbose:
                    print  ('>>> ' + data )
                
                #######################################################################
                # PROCESSING by using the IMPORTED MODULE when starting up this server,
                # always must use the the module do() function.
                result = processing.do(data)
                #######################################################################

                # And sending back the result
                # NOTICE: it is expected to receive a result as a bytes-like object
                if result:
                    sc.send( result )
                else:
                    sc.send( b'ACK\n' )

                if verbose:
                    print( f'(server.py [{service}]) connected to client {remote[0]}' )


if __name__ == "__main__":
    
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(-1)
    
    service = sys.argv[1]

    # Setting the address and port for this server
    address = config[ service + '_address' ]
    port    = config[ service + '_port' ]

    try:
        processing = __import__(service)
        run_server( host=address, port=port, verbose=verbose )

    except:
        print( f'(server.py) error trying the processing module \'{service}\'. Bye.' )
