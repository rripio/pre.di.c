# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (C) 2006-2011 Roberto Ripio
# Copyright (C) 2011-2016 Alberto Miguélez
# Copyright (C) 2016-2018 Rafael Sánchez
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

import time
import socket
import sys
import jack
import math as m
import numpy as np

import init
import getconfigs as gc
import predic as pd

## initialize

# target curves
try:
    target = {
        'target_mag'          : np.loadtxt(gc.target_mag_path),
        'target_pha'          : np.loadtxt(gc.target_pha_path)
        }
except:
    print('Failed to load target files')
    sys.exit(-1)
# audio ports
audio_ports = gc.config['audio_ports']
# warnings
warnings = []


def unplug_sources_of(jack_client, out_ports):
    """disconnect clients from predic inputs and monitor inputs"""

    try:
        # sources_L = jack.get_connections(out_ports[0])
        sources_L = jack_client.get_all_connections(out_ports[0])
        sources_R = jack_client.get_all_connections(out_ports[1])
        for source in sources_L:
            jack_client.disconnect(source.name, out_ports[0])
        for source in sources_R:
            jack_client.disconnect(source.name, out_ports[1])
    except:
        print('error disconnecting outputs')


def do_change_input(input_name, in_ports, out_ports):
    """'in_ports':   list [L,R] of jack capture ports of chosen source
'out_ports':  list of ports in 'audio_ports' variable"""

    monitor_ports = gc.config['monitors_ports'].split()
    # switch
    try:
        # jack.attach('tmp')
        tmp = jack.Client('tmp')
        unplug_sources_of(tmp, out_ports)
        for i in range(len(in_ports)):
            # audio inputs
            try:
                tmp.connect(in_ports[i], out_ports[i])
            except:
                print(f'error connecting {in_ports[i]} <--> {out_ports[i]}')
           # monitor inputs
            try:
                if monitor_ports:
                    tmp.connect(in_ports[i], monitor_ports[i])
            except:
                print('error connecting monitors')
        tmp.close()
    except:
        # on exception returns False
        print(f'error changing to input "{input_name}"')
        tmp.close()
        return False
    return True


def bf_cli(command):
    """send commands to brutefir"""

    global warnings
    with socket.socket() as s:
        try:
            s.connect((gc.config['bfcli_address'], gc.config['bfcli_port']))
            command = command + '; quit\n'
            s.send(command.encode())
            if gc.config['server_output'] == 2:
                print('command sent to brutefir')
        except:
            warnings.append ('Brutefir error')


# main function for command proccessing
def proccess_commands(
        full_command, state=gc.state, curves=init.curves, target = target):
    """proccesses commands for predic control"""

    # normally write state, but there are exceptions
    state_write = True
    # control variable for switching to relative commands
    add = False
    # erase warnings
    warnings = []
    # backup state to restore values in case of not enough headroom
    # or error of any kind
    state_old = state.copy()
    # strips command final characters and split command from arguments
    full_command = full_command.rstrip('\r\n').split()

    if len(full_command) > 0:
        command = full_command[0]
    else:
        command = ''
    if len(full_command) > 1:
        arg = full_command[1]
    else:
        arg = None
    if len(full_command) > 2:
        add = (True if full_command[2] == 'add' else False)
    # initializes gain since it is calculated from level
    gain = pd.calc_gain(state['level'], state['input'])


    ## internal functions for actions

    def change_target(throw_it):

        try:
            (target['target_mag'], target['target_pha']) = pd.get_target()
            state = change_gain(gain)
        except:
            warnings.append('Something went wrong when changing target state')


    def show(throw_it):

        state = pd.show_file()
        return(state)

    def change_input(input, state=state):

        state['input'] = input
        try:
            # if 'none', disconnects all inputs
            if input == 'none':
                disconnect_inputs()
                return state
            elif input == None:
                raise
            elif input in gc.inputs:
                if do_change_input (input,
                        gc.inputs[state['input']]['in_ports'],
                        audio_ports.split()):
                        # input change went OK
                    state = change_gain(gain)
                    # change xo if configured so
                    if gc.config['use_input_xo']:
                        state['xo'] = gc.inputs[input]['xo']
                        state = change_xovers(state['xo'])
                else:
                    warnings.append('Error changing to input ' + input)
                    state['input']  = state_old['input']
                    state['xo'] = state_old['xo']
            else:
                state['input'] = state_old['input']
                warnings.append('Input name "%s" incorrect' % input)
                return state
        except:
            state['input']  = state_old['input']
            state['xo'] = state_old['xo']
            warnings.append('Something went wrong when changing input state')
        return state


    def disconnect_inputs():

        try:
            tmp = jack.Client('tmp')
            unplug_sources_of(tmp, audio_ports.split())
            tmp.close()
        except:
            warnings.append('Something went wrong when diconnecting inputs')


    def change_xovers(XO_set, state=state):

        state['xo'] = XO_set
        try:
            if XO_set in gc.speaker['XO']['sets']:
                coeffs = gc.speaker['XO']['sets'][XO_set]
                filters = gc.speaker['XO']['filters']
                for i in range(len(filters)):
                    bf_cli('cfc "'
                            + filters[i] + '" "' + coeffs[i] + '"')
            else:
                state['xo'] = state_old['xo']
                print('bad XO name')
        except:
            state['xo'] = state_old['xo']
            warnings.append('Something went wrong when changing XO state')
        return state


    def change_drc(drc, state=state):

        state['drc'] = drc
        # if drc 'none' coefficient -1 is set, so latency and CPU usage
        # are improved
        if drc == 'none':
            filters = gc.speaker['DRC']['filters']
            for i in range(len(filters)):
                bf_cli('cfc "'
                        + filters[i] + '" -1')
        else:
            try:
                if drc in gc.speaker['DRC']['sets']:
                    coeffs = gc.speaker['DRC']['sets'][drc]
                    filters = gc.speaker['DRC']['filters']
                    for i in range(len(filters)):
                        bf_cli('cfc "'
                                + filters[i] + '" "' + coeffs[i] + '"')
                else:
                    state['drc'] = state_old['drc']
                    print('bad DRC name')
            except:
                state['drc'] = state_old['drc']
                warnings.append('Something went wrong when changing DRC state')
        return state


    def change_polarity(polarity, state=state):

        if polarity in ['+', '-', '+-', '-+']:
            state['polarity'] = polarity
            try:
                state = change_gain(gain)
            except:
                state['polarity'] = state_old['polarity']
                warnings.append(
                        'Something went wrong when changing polarity state')
        else:
            state['polarity'] = state_old['polarity']
            warnings.append('bad polarity option: has to be "+", "-", "+-" '
                                'or "-+"')
        return state


    def change_midside(midside, state=state):

        if midside in ['mid', 'side', 'off']:
            state['midside'] = midside
            try:
                if state['midside']=='mid':
                    bf_cli('cfia 0 0 m0.5 ; cfia 0 1 m0.5 '
                            '; cfia 1 0 m0.5 ; cfia 1 1 m0.5')
                elif state['midside']=='side':
                    bf_cli('cfia 0 0 m0.5 ; cfia 0 1 m-0.5 '
                            '; cfia 1 0 m0.5 ; cfia 1 1 m-0.5')
                elif state['midside']=='off':
                    bf_cli('cfia 0 0 m1 ; cfia 0 1 m0 '
                            '; cfia 1 0 m0 ; cfia 1 1 m1')
            except:
                state['midside'] = state_old['midside']
                warnings.append('Something went wrong when changing '
                                'midside state')
        else:
            state['midside'] = state_old['midside']
            warnings.append('bad midside option: has to be "mid", "side"'
                                'or "off"')
        return state


    def change_mute(mute, state=state):

        if mute in ['on', 'off']:
            state['mute'] = mute
            try:
                state = change_gain(gain)
            except:
                state['mute'] = state_old['mute']
                warnings.append('Something went wrong '
                                'when changing mute state')
        else:
            state['mute'] = state_old['mute']
            warnings.append('bad mute option: has to be "on" or "off"')
        return state


    def change_solo(solo, state=state):

        if solo in ['off', 'l', 'r']:
            state['solo'] = solo
            try:
                state = change_gain(gain)
            except:
                state['solo'] = state_old['solo']
                warnings.append('Something went wrong '
                                'when changing solo state')
        else:
            state['solo'] = state_old['solo']
            warnings.append('bad solo option: has to be "l", "r" or "off"')
        return state


    def change_loudness_track(loudness, state=state):

        if loudness in ['on', 'off']:
            state['loudness'] = loudness
            try:
                state = change_gain(gain)
            except:
                state['loudness'] = state_old['loudness']
                warnings.append('Something went wrong when changing loudness state')
        else:
            state['mute'] = state_old['mute']
            warnings.append('bad loudness option: '
                                'has to be "on" or "off"')
        return state


    def change_loudness_ref(loudness_ref, state=state, add=add):

        try:
            state['loudness_ref'] = (float(loudness_ref)
                                    + state['loudness_ref'] * add)
            state = change_gain(gain)
        except:
            state['loudness_ref'] = state_old['loudness_ref']
            warnings.append('Something went wrong when changing loudness_ref state')
        return state


    def change_treble(treble, state=state, add=add):

        try:
            state['treble'] = (float(treble)
                                    + state['treble'] * add)
            state = change_gain(gain)
        except:
            state['treble'] = state_old['treble']
            warnings.append('Something went wrong when changing treble state')
        return state


    def change_bass(bass, state=state, add=add):

        try:
            state['bass'] = (float(bass)
                                    + state['bass'] * add)
            state = change_gain(gain)
        except:
            state['bass'] = state_old['bass']
            warnings.append('Something went wrong when changing bass state')
        return state


    def change_balance(balance, state=state, add=add):

        try:
            state['balance'] = (float(balance)
                                    + state['balance'] * add)
            state = change_gain(gain)
        except:
            state['balance'] = state_old['balance']
            warnings.append('Something went wrong when changing balance state')
        return state


    def change_level(level, state=state, add=add):

        try:
            state['level'] = (float(level) + state['level'] * add)
            gain = pd.calc_gain(state['level'], state['input'])
            state = change_gain(gain)
        except:
            state['level'] = state_old['level']
            warnings.append('Something went wrong when changing %s state'
                                                                % command)
        return state


    def change_gain(gain, state=state):
        """change_gain, aka 'the volume machine' :-)"""

        # gain command send its str argument directly
        gain = float(gain)

        def change_eq():

            eq_str = ''
            l = len(curves['frequencies'])
            for i in range(l):
                eq_str = (eq_str + str(curves['frequencies'][i])
                                                + '/' + str(eq_mag[i]))
                if i != l:
                    eq_str += ', '
            bf_cli('lmc eq "c.eq" mag ' + eq_str)
            eq_str = ''
            for i in range(l):
                eq_str = (eq_str + str(curves['frequencies'][i])
                                                + '/' + str(eq_pha[i]))
                if i != l:
                    eq_str += ', '
            bf_cli('lmc eq "c.eq" phase ' + eq_str)


        def change_loudness():

            loudness_max_i = (init.loudness_SPLmax
                                        - init.loudness_SPLmin)
            loudness_variation = (init.loudness_SPLmax
                                        - init.loudness_SPLref)
            if state['loudness'] == 'on':
                if (m.fabs(state['loudness_ref']) > loudness_variation):
                    state['loudness_ref'] = m.copysign(
                            loudness_variation, state['loudness_ref'])
                loudness_i = (init.loudness_SPLmax
                    - (state['level'] + init.loudness_SPLref
                                            + state['loudness_ref']))
            else:
                # index of all zeros curve
                loudness_i = loudness_variation
            if loudness_i < 0:
                loudness_i = 0
            if loudness_i > loudness_max_i:
                loudness_i = loudness_max_i
            # loudness_i must be integer as it will be used as
            # index of loudness curves array
            loudness_i = int(round(loudness_i))
            loudeq_mag = curves['loudness_mag_curves'][:,loudness_i]
            eq_mag = loudeq_mag
            eq_pha = curves['loudness_pha_curves'][:,loudness_i]
            return eq_mag, eq_pha


        def change_treble():

            treble_i = init.tone_variation - state['treble']
            if treble_i < 0:
                treble_i = 0
            if treble_i > 2 * init.tone_variation:
                treble_i = 2 * init.tone_variation
            # force integer
            treble_i = int(round(treble_i))
            eq_mag = curves['treble_mag_curves'][:,treble_i]
            eq_pha = curves['treble_pha_curves'][:,treble_i]
            state['treble'] = init.tone_variation - treble_i
            return eq_mag, eq_pha


        def change_bass():

            bass_i = init.tone_variation - state['bass']
            if bass_i < 0:
                bass_i = 0
            if bass_i > 2 * init.tone_variation:
                bass_i = 2 * init.tone_variation
            # force integer
            bass_i = int(round(bass_i))
            eq_mag = curves['bass_mag_curves'][:,bass_i]
            eq_pha = curves['bass_pha_curves'][:,bass_i]
            state['bass'] = init.tone_variation - bass_i
            return eq_mag, eq_pha


        def commit_gain():

            bf_atten_dB_l = gain
            bf_atten_dB_r = gain
            # add balance dB gains
            if abs(state['balance']) > init.balance_variation:
                state['balance'] = m.copysign(
                        init.balance_variation ,state['balance'])
            bf_atten_dB_l = bf_atten_dB_l - (state['balance'] / 2)
            bf_atten_dB_r = bf_atten_dB_r + (state['balance'] / 2)
            # from dB to multiplier to implement easily
            # polarity and mute
            #
            # then channel gains are the product of
            # gain, polarity, mute and solo
            m_mute = {'on': 0, 'off': 1}[state['mute']]
            m_polarity_l = {'+': 1, '-': -1,
                             '+-': 1, '-+': -1}[state['polarity']]
            m_polarity_r = {'+': 1, '-': -1,
                             '+-': -1, '-+': 1}[state['polarity']]
            m_solo_l  = {'off': 1, 'l': 1, 'r': 0}[state['solo']]
            m_solo_r  = {'off': 1, 'l': 0, 'r': 1}[state['solo']]
            m_gain = lambda x: m.pow(10, x/20) * m_mute
            m_gain_l = (m_gain(bf_atten_dB_l)
                            * m_polarity_l * m_solo_l)
            m_gain_r = (m_gain(bf_atten_dB_r)
                            * m_polarity_r * m_solo_r)
            # commit final gain change
            bf_cli('cffa 2 0 m' + str(m_gain_l)
                        + ' ; cffa 3 1 m' + str(m_gain_r))


        # backs up actual gain
        gain_old = gain
        # EQ curves: loudness + treble + bass
        l_mag,      l_pha      = change_loudness()
        t_mag,      t_pha      = change_treble()
        b_mag,      b_pha      = change_bass()
        # compose EQ curves with target
        eq_mag = target['target_mag'] + l_mag + t_mag + b_mag
        eq_pha = target['target_pha'] + l_pha + t_pha + b_pha
        # calculate headroom
        headroom = pd.calc_headroom(gain, abs(state['balance']/2), eq_mag)
        # moves headroom to accomodate input gain. It can lead to clipping
        # because assumes equal dynamic range between sources
        headroom += pd.calc_input_gain(state['input'])
        # if enough headroom commit changes
        if headroom >= 0:
            commit_gain()
            change_eq()
            state['level'] = pd.calc_level(gain, state['input'])
        # if not enough headroom tries lowering gain
        else:
            change_gain(gain + headroom)
            print('headroom hit, lowering gain...')
        return state
    # end of change_gain()


    ## parse  commands and select corresponding actions

#    try:
    state = {
        'target':           change_target,
        'show':             show,
        'input':            change_input,
        'xo':               change_xovers,
        'drc':              change_drc,
        'polarity':         change_polarity,
        'midside':          change_midside,
        'mute':             change_mute,
        'solo':             change_solo,
        'loudness':         change_loudness_track,
        'loudness_ref':     change_loudness_ref,
        'treble':           change_treble,
        'bass':             change_bass,
        'balance':          change_balance,
        'level':            change_level,
        'gain':             change_gain
        }[command](arg)
#    except KeyError:
#        warnings.append(f"Unknown command '{command}'")
#    except:
#        warnings.append(f"Problems in command '{command}'")

    # return a dictionary of predic state
    return (state, warnings)

# end of proccess_commands()
