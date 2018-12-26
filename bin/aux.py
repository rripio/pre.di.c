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

""" A module that runs miscels
"""

import subprocess as sp
import yaml
import jack
import mpd
import time

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

    # User macros: macro files are named this way: '~/macros/N_macro_name',
    #              so N will serve as button keypad position from web control page
    elif data[:6] == 'macro_':
        try:
            cmd = '/home/predic/macros/' + data[6:]
            sp.run( "'" + cmd + "'", shell=True ) # needs shell to user bash scripts to work
            return b'done'
        except:
            return b'error'
