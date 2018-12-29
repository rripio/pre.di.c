#!/usr/bin/env python2
# -*- coding: utf-8 -*-

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
# TODO: python3

import jack     # NOTICE this is the old jack module because we use here python2
import sys

def jackConns(pattern="", direction='all'):
    """        returns:  port, connection , port
    """
    ports = []
    jack.attach("tmp")
    for p in [x for x in jack.get_ports() if pattern in x]:
        connections = jack.get_connections(p)
        for conn in connections:
            flags = jack.get_port_flags(conn)
            # Returns an integer which is the bitwise-or of all flags for a given port.
            # haciendo pruebas veamos algunos flags de puertos:
            # puertos escribibles (playback): 1 21     impares, ultimo bit a 1
            # puertos leibles     (capture) : 2 18 22  pares,   ultimo bit a 0
            if   flags % 2 :
                d = "-c"
            else:
                d = "-p"
            if direction == d or direction == "all":
                ports.append((p, d , conn))
    jack.detach()
    return ports

if __name__ == "__main__" :
    pname   = ""
    dir     = '-c'
    if len(sys.argv) > 1:
        for opc in sys.argv[1:]:
            if opc in ('-c', '-p'):
                dir = opc
            elif "-h" in opc:
                print __doc__
                sys.exit(0)
            else:
                pname = opc
    print
    for x in jackConns(pname, dir):
        if x[1] == '-c':
            tmp = '-->--'
        if x[1] == '-p':
            tmp = '--<--'
        print x[0].ljust(30) + tmp.ljust(8) + x[2]
    print
