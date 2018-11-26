#!/usr/bin/env python3

""" Listen for certain commands to be executed on local
"""
# This server is secured by allowing only certain orders
# to be translated to actual local commands.

import socket
import sys
import time
import subprocess as sp
import yaml

def process(data):
    """
        Only certain received 'data' will be validated and processed,
        then returns back some useful info to the client.
    """
    # NOTICE:   subprocess.check_output(cmd) returns bytes-like,
    #           but if cmd fails an exception will be raised

    # First clearing the new line
    data = data.replace('\n','')

    # A custom script that switches on/off the amplifier
    if data == 'ampli on':
        try:
            sp.check_output( '/home/predic/bin_custom/ampli.sh on'.split() )
            return b'done'
        except:
            return b'error'
    if data == 'ampli off':
        try:
            sp.check_output( '/home/predic/bin_custom/ampli.sh off'.split() )
            return b'done'
        except:
            return b'error'

    # This returns the current track played by librespot when redirected to ~/tmp/.librespotEvents
    if data == 'get_current_librespot':
        try:
            tmp = sp.check_output( 'tail -n1 /home/predic/tmp/.librespotEvents'.split() )
            tmp = tmp.decode().split('"')[-2]
            return tmp.encode()
        except:
            return b'error'

    # Checks for librespot to be running
    if data == 'librespot_running':
        try:
            tmp = sp.check_output ( 'pgrep -f /usr/bin/librespot'.split() )
            return b'true'
        except:
            return b'false'


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
        print('(server_local) Error binding port', port)
        s.close()
        sys.exit(-1)

    # return socket state
    return s

if __name__ == '__main__':

    verbose = False
    fsocket = server_socket('localhost', 9988)

    for opc in sys.argv:
        if '-v' in opc:
            verbose = True

    # main loop to proccess conections
    backlog = 10
    while True:
        # listen ports
        fsocket.listen(10)  # number of connections in queue
        if verbose:
            print('(server_local) listening on \'localhost\':9988')
        # accept client connection
        sc, addr = fsocket.accept()
        # somo info
        if verbose:
            print(f'(server_local) connected to client {addr[0]}')
        # buffer loop to proccess received command
        while True:
        # reception
            data = sc.recv(4096).decode()
            if not data:
                # nothing in buffer, client has disconnected too soon
                if verbose:
                    print('(server_local) client disconnected. '
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
                    print('(server_local) closing connection...')
                sc.close()
                break
            elif data.rstrip('\r\n') == 'shutdown':
                sc.send(b'OK\n')
                if verbose:
                    print('(server_local) closing connection...')
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
                    print(f'(server_local) connected to client {addr[0]}')

            # wait a bit, loop again
            time.sleep(0.01)
