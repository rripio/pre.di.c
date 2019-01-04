#!/usr/bin/env python3

"""
    v0.4beta
    Script to manage pre.di.c volume through by a mouse.

    Use:
            mouse_volume_daemon.py [-sNN -bHH] &

                -sNN volume step NN dBs (default 2.0 dB)
                -bHH beeps if exceeds headroom HH dB (default 6.0 dB)
                -h   this help

                left button   -->  vol --
                right button  -->  vol ++
                mid button    -->  togles mute

    - Access permissions -

    The user must belong to the system group wich
    can access to devices under '/dev/input' folder. This group is defined
    inside '/etc/udev/rules.d/99-input.rules', also can be seen this way:

    $ ls -l /dev/input/
    total 0
    crw-rw---- 1 root input 13, 64 Mar 19 20:53 event0
    crw-rw---- 1 root input 13, 63 Mar 19 20:53 mice
    crw-rw---- 1 root input 13, 32 Mar 19 20:53 mouse0

    On the above example can be seen that the group is 'input'

"""
# v0.2beta: beeps by running the synth from SoX (play)
# v0.3beta: beeps by running 'aplay beep.wav'
# v0.4beta: from FIRtro to pre.di.c (python3 and writen as a module)

import os
import sys
import time
import subprocess as sp
import binascii
#import struct # only to debug see below

import basepaths as bp

HOME =      os.path.expanduser("~")
hostDir =   os.path.dirname( os.path.realpath(__file__) )

#### USER SETTINGS: ####
STEPdB  = 2.0
HRthr   = 6.0
beep    = False
beepPath = f'{hostDir}/2beeps.wav'
########################

def getMouseEvent():
    """
    /dev/input/mouseX is a stream of 3 bytes: [Button_value] [XX_value] [YY_value]

    You would get a 4 byte stream if the mouse is configured with the scroll wheel (intellimouse)

    /dev/input/mice emulates a PS/2 mouse in three-byte mode.

        0x09XXYY --> buttonLeftDown
        0x0aXXYY --> buttonRightDown
        0x0cXXYY --> buttonMid

    To see the correspondence of files /dev/input/xxxx

        $ cat /proc/bus/input/devices
        I: Bus=0003 Vendor=046d Product=c03d Version=0110
        N: Name="Logitech USB-PS/2 Optical Mouse"
        P: Phys=usb-3f980000.usb-1.2/input0
        S: Sysfs=/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.2/1-1.2:1.0/0003:046D:C03D.0001/input/input0
        U: Uniq=
        H: Handlers=mouse0 event0
        B: PROP=0
        B: EV=17
        B: KEY=70000 0 0 0 0 0 0 0 0
        B: REL=103
        B: MSC=10
    """
    fmice =     open( "/dev/input/mice", "rb" )
    buff = fmice.read(3);
    m = binascii.hexlify(buff).decode()
    #print m, struct.unpack('3b', buff)  # Unpacks the bytes to integers
    if   m[:2] == "09":
        return "buttonLeftDown"
    elif m[:2] == "0a":
        return "buttonRightDown"
    elif m[:2] == "0c":
        return "buttonMid"
    fmice.close()

def check_headroom():
    # To avoid reading issues while state.yml is written
    i = 0
    while i < 20:
        f = open( f'{bp.main_folder}/config/state.yml', 'r')
        conte = f.read()
        f.close()
        try:
            headroom = conte.split('headroom:')[1].split()[0]
            return float(headroom)
        except:
            pass
        i += 1
        time.sleep(.2)
    return 0.0

def beep():
    # The synth on Sox is too slow :-/
    #sp.Popen( 'play --null synth 1 sine 880 gain -10.0 > /dev/null 2>&1' )
    # then will use aplay
    sp.Popen( ['aplay', '-Djack', beepPath],
              stdout=sp.DEVNULL, stderr=sp.DEVNULL )

def main_loop():

    level_ups = False
    beeped =    False

    while True:

        # Reading the mouse
        ev = getMouseEvent();

        # Dending the order to pre.di.c
        if   ev == 'buttonLeftDown':
            # Level --
            sp.Popen( ['control', f'level -{ str(STEPdB) } add'],
                      stdout=sp.DEVNULL, stderr=sp.DEVNULL )
            level_ups = False

        elif ev == 'buttonRightDown':
            # Level ++
            sp.Popen( ['control', f'level +{ str(STEPdB) } add'],
                      stdout=sp.DEVNULL, stderr=sp.DEVNULL )
            level_ups = True

        elif ev == 'buttonMid':
            # Mute toggle
            sp.Popen( ['control', 'mute toggle'],
                      stdout=sp.DEVNULL, stderr=sp.DEVNULL )

        # Alert if crossed the headroom threshold
        if level_ups:
            hr = check_headroom()
            if hr < HRthr:
                #print(hr)
                if not beeped and beep:
                    beep()
                    beeped = True
            else:
                beeped = False

if __name__ == "__main__":

    for opc in sys.argv:

        if "-h" in opc:
            print( __doc__ )
            sys.exit()

        if "-s" in opc:
            try:
                STEPdB = float(opc.replace("-s", ""))
            except:
                pass

        if "-b" in opc:
            beep = True
            try:
                HRthr = float(opc.replace("-b", ""))
            except:
                pass

    main_loop()
