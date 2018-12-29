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

"""Control module of a parametric ecualizer based on ecasound

Usage: peq_control.py "command1 param1" "command2 param2" ...

   commandN can be:

    - native ecasound-iam command (man ecasound-iam)

    - one of this:
      PEQdump                  prints running parametric filters
      PEQdump2ecs              prints running .ecs structure
      PEQbypass on|off|toggle  EQ bypass
      PEQgain XX               sets EQ gain
"""

import sys
import os
import time
import socket
from configparser import ConfigParser

import basepaths
import getconfigs


# pool of PEQ settings
PEQs = ConfigParser()

def ecanet(command):
    """Sends commands to ecasound and accept results"""

    # note:   - ecasound needs CRLF
    #         - socket send and receive bytes (not strings),
    #           hence .encode() and .decode()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect( ('localhost', 2868) )
    s.send( (command + '\r\n').encode() )
    data = s.recv( 8192 )
    s.close()
    return data.decode()


def readChannelPEQini(fileName, channel):
    """Reads external file XXXX.peq"""

    # returns two parameter chains to get 4 + 4 parametrics per channel

    PEQs.read(fileName)

    cad = ""
    for filter in PEQs.options(channel):
        cad += "," + ",".join(PEQs.get(channel, filter).split())

    # global...filters_1-4...filters_5-8 (remove first comma of 'join')
    return cad[1:]


def loadPEQini(archivoPEQini):
    """Reloads ecasound settings on-the-fly"""

    for channel in ["left","right"]:
        # read channel from XXXXXX.peq file
        listParamsPlugins = readChannelPEQini(archivoPEQini,
                                                    channel).split(",")

        # select channel in ecasound
        ecanet("c-select " + channel)

        # check plugins list (cop) chained in ecasound channel
        plugins = ecanet("cop-list").split("\r\n")[1].split(",")
        # parse plugins (selected by ordinal number)
        for n in range(len(plugins)):

            # select plugin to change
            # ecasound numbers from "1"
            cop = n + 1
            ecanet("cop-select " + str(cop))

            # overwrite each parametric setting with INI settings
            # each plugin has 18 parameters (2 globals, 4x4 from filters)
            for pos in range(1,19):
                # (!) in case pop* exhausts before possible filters
                # admitted in ecasound
                if listParamsPlugins:
                    ecanet("cop-set " + str(cop) + "," + str(pos) + "," + listParamsPlugins.pop(0)) #(*)

    print("(peq_control) file " + archivoPEQini
                                + " has been loaded in ecasound")
    print("(peq_control) Remember to check global gain in first plugin")
    try:
        if len(listParamsPlugins) > 0:
            print("(peq_control) filter list of " + str(len(plugins))
                                + " plugins excedes ecasound capacity")
    except:
        pass


def PEQdefeat(fs):
    """Loads external ChainSetup with zeroed filters"""

    # beware that jack ports inputs to ecasound will be disconnected

    PEQbands = getconfigs.config['ecasound_filters']
    ecsDefeatFile = (basepaths.config_folder + "PEQx" + str(PEQbands)
                                        + "_defeat_" + str(fs) + ".ecs")

    if os.path.isfile(ecsDefeatFile):
        ecanet("cs-disconnect")
        ecanet("cs-remove")
        ecanet("cs-load " + ecsDefeatFile)
        ecanet("cs-connect")
        ecanet("start")

        print(("(peq_control) ecasound has loaded file: "
                                                        + ecsDefeatFile))
    else:
        print(("(peq_control) error accessing file: " + ecsDefeatFile))
        return False


def PEQgain(level):
    """ set gain in first plugin stage"""

    for chain in ("left", "right"):
        ecanet("c-select " + chain) # select channel
        ecanet("cop-select 1")      # select second filter stage
        ecanet("copp-select 2")     # select global gain
        ecanet("copp-set " + level) # set


def PEQbypass(mode):
    """mode: on | off | toggle"""

    for chain in ("left", "right"):
        ecanet("c-select " + chain)
        ecanet("c-bypass " + mode)
        # experimental, seems neccessary
        time.sleep(getconfigs.config['command_delay'] * .2)

    for chain in ecanet("c-status").replace("[selected] ", "").split("\n")[2:4]:
        tmp = ""
        if "bypass" in chain.split()[2]:
            tmp = chain.split()[2]
        print((" ".join(chain.split()[:2]) + " " + tmp))


def PEQdump(fname=None):

    dump = ""
    dump += ("\n# " + "Active".rjust(8) + "Freq".rjust(9) + "BW".rjust(7)
                                                    + "Gain".rjust(8) + "\n")
    tmp = ecanet("cs-status").split("\n")

    # channel L in field 7 of tmp, R in field 8
    for pos in (7,8):
        chain = tmp[pos].split(" ")
        # chain name= channel
        dump += "\n" + chain[3].replace('":',']').replace('"','[') + "\n"
        pluginNum = 1
        filterNum = 1
        for n in range(len(chain)): # parse chain fields
            if "eli:" in chain[n]:  # it's a plugin
                # let's see inside
                dump += auxPEQdump(chain[n], pluginNum, filterNum)
                pluginNum += 1
                filterNum += 4

    if fname:
        try:
            with open(fname, "w") as f:
                f.write(dump)
        except:
            print(("\n(peq_control) (!) file " + fname
                                                + " couldn't be dumped\n"))

    return dump


def auxPEQdump(plugin, pluginNum, filterNum):

    tmp = ""
    p = plugin.split(",")
    tmp += ("global"+str(pluginNum)+" = " + p[ 1][0].rjust(2)
                                                    + p[ 2].rjust(24) + "\n")
    tmp += ("f"+str(filterNum+0).ljust(2)+" =     " + p[ 3][0].rjust(2)
                    + p[ 4].rjust(9) + p[ 5].rjust(7) + p[ 6].rjust(8) + "\n")
    tmp += ("f"+str(filterNum+1).ljust(2)+" =     " + p[ 7][0].rjust(2)
                    + p[ 8].rjust(9) + p[ 9].rjust(7) + p[10].rjust(8) + "\n")
    tmp += ("f"+str(filterNum+2).ljust(2)+" =     " + p[11][0].rjust(2)
                    + p[12].rjust(9) + p[13].rjust(7) + p[14].rjust(8) + "\n")
    tmp += ("f"+str(filterNum+3).ljust(2)+" =     " + p[15][0].rjust(2)
                    + p[16].rjust(9) + p[17].rjust(7) + p[18].rjust(8) + "\n")

    return tmp


def PEQdump2ecs():

    ecanet("cs-save-as /home/predic/tmp.ecs")
    with open("/home/predic/tmp.ecs", "r") as f:
        print((f.read()))
    os.remove("/home/predic/tmp.ecs")


if __name__ == '__main__':

    try:
        ecanet("") # is ecasound listening?
    except:
        print("(!) ecasound server not running")

    dumpfile =  basepaths.loudspeakers_folder + \
                getconfigs.config['loudspeaker'] + "/peqdump.txt"

    # we can pass more than one command from command line to ecasound
    if len(sys.argv) > 1:
        commands = sys.argv[1:]
        for command in commands: # parse command list
            if not("PEQ" in command):
                print((ecanet(command)))
            else:

                if command == "PEQdump":
                    print((PEQdump(dumpfile)))

                elif command == "PEQdump2ecs":
                    PEQdump2ecs()

                elif "PEQbypass" in command:
                    try:
                        PEQbypass(command.split()[1])
                    except:
                        print("lacking on | off | toggle parameter")

                elif "PEQgain" in command:
                    try:
                        gain = command.split()[1]
                        PEQgain(gain)
                        # PEQdump()
                    except:
                        print("lacking gain in dB")

                else:
                    print(("(!) error en command " + command))
                    print(__doc__)

    else:
        print(__doc__)
