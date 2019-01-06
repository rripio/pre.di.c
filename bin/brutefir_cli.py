#!/usr/bin/env python3

# v1.1
#   remove time.sleep, will use a loop to receive data
# v1.2
#   python3 compatible

import sys
import socket

def bfcli(cmd):
    """ send commands to brutefir CLI and receive its responses
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 3000))
    s.send( f'{cmd} \n'.encode() )
    response = b''
    while True:    
        received = s.recv(4096)
        if received:
            response = response + received
        else:
            break
    s.close()
    # print response # debug
    return response.decode()

if __name__ == '__main__':
    try:
        cmd = ";".join(sys.argv[1:]) + ";"
        print( bfcli(cmd) )
    except:
        print( '(brutefir_cli.py) something was wrong :-/' )
