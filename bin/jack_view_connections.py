#!/usr/bin/env python3

# Copyright (c) 2016-2018 Rafael Sánchez
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
    Prints jack connnections in a friendly way

    jack_view_connections.py [ -c | -p ] [pattern]

    -c view capture  -->-- playback ports   (DEFAULT)
    -p view playback --<-- capture  ports

    Example:  jack_view_connections.py brutefir
"""
# v1.1b
#   defaults to print capture  -->--  playback
# v1.2
#   Python3 and new jack client

import jack
import sys

def jackConns(pattern='', InOut='all'):
    """
        Select ports by name and/or by capture/playback.
        Returns the selected ports connectios as string triplets:
            [ (A_port, B_port, direction), ... ]
    """
    triplets = []
    jc = jack.Client('tmp')
    
    if   InOut == 'out':
        A_ports = jc.get_ports( name_pattern=pattern, is_output=True )

    elif InOut == 'in':
        A_ports = jc.get_ports( name_pattern=pattern, is_input=True )

    elif InOut == 'all':
        A_ports = jc.get_ports( name_pattern=pattern )

    for A_port in A_ports:
        B_ports = jc.get_all_connections(A_port)
        for B_port in B_ports:
            if A_port.is_input:
                direction = '<'
            else:
                direction = '>'
            triplets.append( (A_port.name, B_port.name, direction) )

    jc.close()
    
    return triplets

if __name__ == "__main__" :

    pattern   = ''
    InOut     = '-c'

    if len(sys.argv) > 1:
        for opc in sys.argv[1:]:
            if opc == '-c':
                InOut = 'out'
            elif opc == '-p':
                InOut = 'in'
            elif "-h" in opc:
                print( __doc__ )
                sys.exit(0)
            else:
                pattern = opc

    print()
    for a,b,d in jackConns(pattern, InOut):
        print(f'{a:30}', f'--{d}--    ', b)
    print()
