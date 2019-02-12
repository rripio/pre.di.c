#! /usr/bin/env python3

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

"""Stops predic audio system
    Usage:
    initaudio.py [ core | scripts | all ]   (default 'all')
    core: jack, brutefir, server
    scripts: everything else (players and clients)
    all: all of the above
"""

import sys
import os
from subprocess import Popen

import basepaths as bp
import getconfigs as gc
import predic as pd

fnull = open(os.devnull, 'w')


def main(run_level):

    if run_level in ['core', 'all']:
        # controlserver
        print('(stopaudio) stopping server')
        try:
            pd.client_socket('shutdown')
        except:
            Popen (['pkill', '-9', '-f', bp.server_path]
                                        , stdout=fnull, stderr=fnull)
        # brutefir
        print('(stopaudio) stopping brutefir')
        Popen (['killall', gc.config['brutefir_path']]
                                        , stdout=fnull, stderr=fnull)
        # jack
        print('(stopaudio) stopping jackd')
        Popen (['killall', 'jackd'], stdout=fnull, stderr=fnull)
    if run_level in ['scripts', 'all']:
        # stop external scripts, sources and clients
        print('(stopaudio) stopping scripts')
        scripts = pd.read_scripts()
        for script in scripts:
            try:
                script_path = f'{bp.scripts_folder}{script}'
                command = f'{script_path} stop'
                Popen(command.split())
                # kills launching script
                pd.kill_pid(script)
                pd.wait4result('pgrep -f ' + script, '', 5, quiet=True)
            except OSError as err:
                print(f'error launching script:\n\t{err}')
            except:
                print(f'problem launching script {script}:\n\t{err}')


if __name__ == '__main__':

    run_level = 'all'
    if sys.argv[1:]:
        run_level = sys.argv[1]
    if run_level in ['core', 'players', 'all']:
        print('(stopaudio) stopping', run_level)
        main(run_level)
    else:
        print(__doc__)
