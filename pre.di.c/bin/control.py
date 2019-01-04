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

import socket
import sys
import jack
import math
import numpy as np
import yaml

import peq_control
import basepaths as bp
import getconfigs as gc
import predic as pd

## initialize

# EQ curves
cf = bp.config_folder
try:
    curves = {
        'freq'                : np.loadtxt(cf
                                + gc.config['frequencies']),
        'loudness_mag_curves' : np.loadtxt(cf
                                + gc.config['loudness_mag_curves']),
        'loudness_pha_curves' : np.loadtxt(cf
                                + gc.config['loudness_pha_curves']),
        'treble_mag'          : np.loadtxt(cf
                                + gc.config['treble_mag_curves']),
        'treble_pha'          : np.loadtxt(cf
                                + gc.config['treble_pha_curves']),
        'bass_mag'            : np.loadtxt(cf
                                + gc.config['bass_mag_curves']),
        'bass_pha'            : np.loadtxt(cf
                                + gc.config['bass_pha_curves']),
        'target_mag'          : np.loadtxt(gc.target_mag_path),
        'target_pha'          : np.loadtxt(gc.target_pha_path)
        }
except:
    print('Failed to load EQ files')
    sys.exit(-1)

# audio ports: Brutefir or Ecasound
if gc.config['load_ecasound']:
    audio_ports = gc.config['ecasound_ports']
else:
    audio_ports = gc.config['brutefir_ports']

# warnings
warnings = []


def unplug_sources_of(jack_client, predic_ports):
    """ Disconnect clients from predic inputs and monitor inputs """

    def disconnect(pb_ports):
        try:
            sources_0 = jack_client.get_all_connections(pb_ports[0])
            sources_1 = jack_client.get_all_connections(pb_ports[1])
            for source in sources_0:
                jack_client.disconnect(source.name, pb_ports[0])
            for source in sources_1:
                jack_client.disconnect(source.name, pb_ports[1])
        except:
            print(f'error disconnecting [{pb_ports}]')

    disconnect(predic_ports)
    monitor_ports = gc.config['jack_monitors'].split()
    if monitor_ports:
        disconnect(monitor_ports)


def do_change_input(input_name, in_ports, out_ports, resampled=False):
    """ 'in_ports':   list [L,R] of jack capture ports of chosen source
    'out_ports':  list of ports in 'audio_ports' variable
                  depends on use of brutefir/ecasound """

    monitor_ports = gc.config['jack_monitors'].split()
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
            if gc.config['control_output'] > 1:
                print('command sent to brutefir')
        except:
            warnings.append ('Brutefir error')

########################################
# Main function for command proccessing
########################################
def proccess_commands(full_command, state=gc.state, curves=curves):
    """ Proccesses commands for predic control
        Input:  command phrase, state dictionary, curves
        Output: new state dict, warnings
    """

    # normally write state, but there are exceptions
    state_write = True
    change_peq = False
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

    #######################################
    ## internal functions for do() actions:
    #######################################

    def change_target(throw_it):

        try:
            (curves['target_mag'], curves['target_pha']) = pd.get_target()
            state = change_gain(gain, True)
        except:
            warnings.append('Something went wrong when changing target state')


    def change_input(input, state=state):

        state['input'] = input
        # if none disconnects all inputs
        if input == 'none':
            disconnect_inputs()
            return state
        elif input == None:
            raise
        elif input in gc.inputs:
            state['XO_set'] = gc.inputs[input]['xo']
        else:
            state['input'] = state_old['input']
            warnings.append('Input name "%s" incorrect' % input)
            return state
        try:
            if do_change_input (input
                    , gc.inputs[state['input']]['in_ports']
                    , audio_ports.split()
                    , gc.inputs[input]['resampled']):
                    # input change went OK
                state = change_xovers(state['XO_set'])
                state = change_gain(gain, True)
            else:
                warnings.append('Error changing to input ' + input)
                state['input']  = state_old['input']
                state['XO_set'] = state_old['XO_set']
        except:
            state['input']  = state_old['input']
            state['XO_set'] = state_old['XO_set']
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

        state['XO_set'] = XO_set
        try:
            if XO_set in gc.speaker['XO']['sets']:
                coeffs = gc.speaker['XO']['sets'][XO_set]
                filters = gc.speaker['XO']['filters']
                # Allows no filtering e.g for fullrange loudspeakers:
                coeffsTmp = coeffs.copy() # (a copy does not modify the original)
                for index, item in enumerate(coeffsTmp):
                    if item == 'none':
                        coeffsTmp[index] = '-1'
                    else:
                        coeffsTmp[index] = '"' + item + '"'
                for i in range(len(filters)):
                    bf_cli( 'cfc "' + filters[i] + '" ' + coeffsTmp[i] )
            else:
                state['XO_set'] = state_old['XO_set']
                print('bad XO name')
        except:
            state['XO_set'] = state_old['XO_set']
            warnings.append('Something went wrong when changing XO state')

        return state


    def change_drc(DRC_set, state=state):

        state['DRC_set'] = DRC_set
        # if drc 'none' coefficient -1 is set, so latency and CPU usage
        # are improved
        if DRC_set == 'none':
            filters = gc.speaker['DRC']['filters']
            for i in range(len(filters)):
                bf_cli('cfc "'
                        + filters[i] + '" -1')
        else:
            try:
                if DRC_set in gc.speaker['DRC']['sets']:
                    coeffs = gc.speaker['DRC']['sets'][DRC_set]
                    filters = gc.speaker['DRC']['filters']
                    for i in range(len(filters)):
                        bf_cli('cfc "'
                                + filters[i] + '" "' + coeffs[i] + '"')
                else:
                    state['DRC_set'] = state_old['DRC_set']
                    print('bad DRC name')
            except:
                state['DRC_set'] = state_old['DRC_set']
                warnings.append('Something went wrong when changing DRC state')
        return state


    def change_peq(PEQ_set, state=state):

        state['PEQ_set'] = PEQ_set
        try:
            if PEQ_set in gc.speaker['PEQ']:
                peqFile = gc.speaker['PEQ'][PEQ_set]
                if peqFile == 'none':
                    peq_control.PEQdefeat( gc.speaker['fs'] )
                    # restore input connections because peq defeating causes
                    # ecasaound input jack ports to be disconnected:
                    change_input( state['input'], state )
                else:
                    peq_control.loadPEQini( peqFile )
            else:
                state['PEQ_set'] = state_old['PEQ_set']
                print('bad PEQ name')
        except:
            state['PEQ_set'] = state_old['PEQ_set']
            warnings.append('Something went wrong when changing PEQ state')

        return state


    def change_polarity(polarity, state=state):

        if polarity in ['+', '-', 'toggle']:
            if polarity == 'toggle':
                polarity = {
                    '+': '-',
                    '-': '+'
                    }[state['polarity']]
            state['polarity'] = polarity
            try:
                bf_cli('cfia 0 0 m' + polarity + '1 '
                     '; cfia 1 1 m' + polarity + '1')
                state = change_gain(gain)
            except:
                state['polarity'] = state_old['polarity']
                warnings.append('Something went wrong when changing polarity state')
        else:
            state['polarity'] = state_old['polarity']
            warnings.append('bad polarity option: has to be "+", "-"'
                                'or "toggle"')
        return state


    def change_mono(mono, state=state):

        try:
            state['mono'] = {
                'on':       True,
                'off':      False,
                'toggle':   not state['mono']
                }[mono]
        except KeyError:
            state['mono'] = state_old['mono']
            warnings.append('Option ' + arg + ' incorrect')
            return state
        try:
            if state['mono']:
                bf_cli('cffa 2 0 m0.5 ; cffa 2 1 m0.5 '
                       '; cffa 3 1 m0.5 ; cffa 3 0 m0.5')
            else:
                bf_cli('cffa 2 0 m1 ; cffa 2 1 m0 ; cffa 3 1 m1 ; cffa 3 0 m0')
        except:
            state['mono'] = state_old['mono']
            warnings.append('Something went wrong when changing mono state')
        return state


    def change_mute(mute, state=state):

        try:
            state['muted'] = {
                'on':       True,
                'off':      False,
                'toggle':   not state['muted']
                }[mute]
        except KeyError:
            state['muted'] = state_old['muted']
            warnings.append('Option ' + arg + ' incorrect')
            return state
        try:
            state = change_gain(gain)
        except:
            state['muted'] = state_old['muted']
            warnings.append('Something went wrong when changing mute state')
        return state


    def change_loudness_track(loudness_track, state=state):

        try:
            state['loudness_track'] = {
                'on':       True,
                'off':      False,
                'toggle':   not state['loudness_track']
                }[loudness_track]
        except KeyError:
            state['loudness_track'] = state_old['loudness_track']
            warnings.append('Option ' + arg + ' incorrect')
            return state
        try:
            state = change_gain(gain)
        except:
            state['loudness_track'] = state_old['loudness_track']
            warnings.append('Something went wrong when changing loudness_track state')
        return state


    def change_loudness_ref(loudness_ref, state=state, add=add):

        try:
            state['loudness_ref'] = (float(loudness_ref)
                                    + state['loudness_ref'] * add)
            state = change_gain(gain, True)
        except:
            state['loudness_ref'] = state_old['loudness_ref']
            warnings.append('Something went wrong when changing loudness_ref state')
        return state


    def change_treble(treble, state=state, add=add):

        try:
            state['treble'] = (float(treble)
                                    + state['treble'] * add)
            state = change_gain(gain, True)
        except:
            state['treble'] = state_old['treble']
            warnings.append('Something went wrong when changing treble state')
        return state


    def change_bass(bass, state=state, add=add):

        try:
            state['bass'] = (float(bass)
                                    + state['bass'] * add)
            state = change_gain(gain, True)
        except:
            state['bass'] = state_old['bass']
            warnings.append('Something went wrong when changing bass state')
        return state


    def change_balance(balance, state=state, add=add):

        try:
            state['balance'] = (float(balance)
                                    + state['balance'] * add)
            state = change_gain(gain, True)
        except:
            state['balance'] = state_old['balance']
            warnings.append('Something went wrong when changing balance state')
        return state


    def change_level(level, state=state, add=add):

        try:
            state['level'] = (float(level)
                                    + state['level'] * add)
            gain = pd.calc_gain(state['level'], state['input'])
            state = change_gain(gain, True)
        except:
            state['level'] = state_old['level']
            warnings.append('Something went wrong when changing %s state'
                                                                % command)
        return state


    def change_gain(gain, do_change_eq=False, state=state):
        """change_gain, aka 'the volume machine' :-)"""

        # gain command send its str argument directly
        gain = float(gain)

        def change_eq():

            eq_str = ''
            l = len(curves['freq'])
            for i in range(l):
                eq_str = eq_str + str(curves['freq'][i]) + '/' + str(eq_mag[i])
                if i != l:
                    eq_str += ', '
            bf_cli('lmc eq "c.eq" mag ' + eq_str)
            eq_str = ''
            for i in range(l):
                eq_str = eq_str + str(curves['freq'][i]) + '/' + str(eq_pha[i])
                if i != l:
                    eq_str += ', '
            bf_cli('lmc eq "c.eq" phase ' + eq_str)


        def change_loudness():

            loudness_max_i = (gc.config['loudness_SPLmax']
                                        - gc.config['loudness_SPLmin'])
            if state['loudness_track']:
                if (math.fabs(state['loudness_ref'])
                        > gc.config['loudness_variation']):
                    state['loudness_ref'] = math.copysign(
                        gc.config['loudness_variation'], state['loudness_ref'])
                loudness_i = (gc.config['loudness_SPLmax']
                    - (state['level'] + gc.config['loudness_SPLref']
                                            + state['loudness_ref']))
            else:
                # index of all zeros curve
                loudness_i = gc.config['loudness_variation']
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

            treble_i = gc.config['tone_variation'] - state['treble']
            if treble_i < 0:
                treble_i = 0
            if treble_i > 2 * gc.config['tone_variation']:
                treble_i = 2 * gc.config['tone_variation']
            # force integer
            treble_i = int(round(treble_i))
            eq_mag = curves['treble_mag'][:,treble_i]
            eq_pha = curves['treble_pha'][:,treble_i]
            state['treble'] = gc.config['tone_variation'] - treble_i
            return eq_mag, eq_pha


        def change_bass():

            bass_i = gc.config['tone_variation'] - state['bass']
            if bass_i < 0:
                bass_i = 0
            if bass_i > 2 * gc.config['tone_variation']:
                bass_i = 2 * gc.config['tone_variation']
            # force integer
            bass_i = int(round(bass_i))
            eq_mag = curves['bass_mag'][:,bass_i]
            eq_pha = curves['bass_pha'][:,bass_i]
            state['bass'] = gc.config['tone_variation'] - bass_i
            return eq_mag, eq_pha


        def commit_gain():

            bf_atten_dB_0 = gain
            bf_atten_dB_1 = gain
            # add balance dB gains
            if abs(state['balance']) > gc.config['balance_variation']:
                state['balance'] = math.copysign(
                        gc.config['balance_variation'] ,state['balance'])
            bf_atten_dB_0 = bf_atten_dB_0 - (state['balance'] / 2)
            bf_atten_dB_1 = bf_atten_dB_1 + (state['balance'] / 2)
            # from dB to multiplier to implement easily
            # polarity and mute
            m_polarity = {'+': 1, '-': -1}[state['polarity']]
            m_muted = float(not state['muted'])
            m_gain = lambda x: math.pow(10, x/20) * m_polarity * m_muted
            m_gain_0 = m_gain(bf_atten_dB_0)
            m_gain_1 = m_gain(bf_atten_dB_1)
            # commit final gain change
            bf_cli('cfia 0 0 m' + str(m_gain_0)
              + ' ; cfia 1 1 m' + str(m_gain_1))


        # backs up actual gain
        gain_old = gain
        # EQ curves: loudness + treble + bass
        l_mag,      l_pha      = change_loudness()
        t_mag,      t_pha      = change_treble()
        b_mag,      b_pha      = change_bass()
        # compose EQ curves with target
        eq_mag = curves['target_mag'] + l_mag + t_mag + b_mag
        eq_pha = curves['target_pha'] + l_pha + t_pha + b_pha
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
            print('headroom hitted, lowering gain...')
        return state
    # end of change_gain()

    ####################################################
    ## parse commands and select corresponding actions
    ####################################################
    if gc.config['control_output'] > 0:
        print(f'Command: {full_command}')

    try:
        state = {
            'target':           change_target,
            'show':             pd.show,
            'input':            change_input,
            'xo':               change_xovers,
            'drc':              change_drc,
            'peq':              change_peq,
            'polarity':         change_polarity,
            'mono':             change_mono,
            'mute':             change_mute,
            'loudness_track':   change_loudness_track,
            'loudness_ref':     change_loudness_ref,
            'treble':           change_treble,
            'bass':             change_bass,
            'balance':          change_balance,
            'level':            change_level,
            'gain':             change_gain
            }[command](arg)

    except KeyError:
        warnings.append(f"Unknown command '{command}'")

    except:
        warnings.append(f"Problems in command '{command}'")


    # return a dictionary of predic state
    return (state, warnings)

###################################
# Interfacing function for servers
###################################
def do( cmdline ):
    """ Returns:
        - The state dictionary if cmdline = 'status'
        - 'OK' if the command was succesfully processed.
        - 'ACK' if not.
    """
    
    # terminal print out behavior
    if gc.config['control_output'] > 1:
        if gc.config['control_clear']:
            # optional terminal clearing
            os.system('clear')
        else:
            # separator
             print('=' * 70)

    result = ''

    # 'status' will read the state file and send it back as an YAML string
    if cmdline.rstrip('\r\n') == 'status':
        result = yaml.dump( gc.state, default_flow_style=False )

    # Any else cmdline phrase will be processed by the 'proccess_commands()' function,
    # that answers with a state dict, and warnings if any:
    else:
        (state, warnings) = proccess_commands( cmdline )

        try:
            # Updates state file
            with open( bp.state_path, 'w' ) as f:
                yaml.dump( state, f, default_flow_style=False )

            # Prints warnings
            if len(warnings) > 0:
                print("Warnings:")
                for warning in warnings:
                    print("\t", warning)
                result = 'ACK\n'
            else:
                result = 'OK\n'
        except:
            result = 'ACK\n'

    # It is expected to return bytes-like things to the server
    return result.encode()
