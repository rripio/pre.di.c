# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import time
import socket
import sys
import jack
import math as m

import numpy as np

import base
import init
import predic as pd


# main function for command proccessing
def proccess_commands(
        full_command, state=init.state, 
        curves=init.curves, target = init.target):
    """proccesses commands for predic control"""

    # normally write state, but there are exceptions
    state_write = True
    # control variable for switching to relative commands
    add = False
    # erase warnings
    warnings = []
    # backup state to restore values in case of not enough headroom \
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
    gain = pd.calc_gain(state['level'])


    ## auxiliary functions

    def disconnect_outputs(jack_client):
        """disconnect sources from predic audio ports"""

        try:
            for port_group in init.config['audio_ports']:
                for port in port_group:
                    sources = jack_client.get_all_connections(port)
                    for source in sources:
                        jack_client.disconnect(source.name, port)
        except Exception as e:
            print('error disconnecting inputs: ', e)


    def bf_cli(command):
        """send commands to brutefir"""

        with socket.socket() as s:
            try:
                s.connect((init.config['bfcli_address'],
                    init.config['bfcli_port']))
                command = f'{command}; quit\n'
                s.send(command.encode())
                if init.config['server_output'] == 2:
                    print('command sent to brutefir')
            except Exception as e:
                warnings.append('Brutefir error: ', e)


    ## internal functions for actions

    def show(throw_it):

        state = pd.show_file()
        return(state)


    def noinput(throw_it, state=state):
        """convenience command that make disconnect_outputs() 
        externally available"""

        try:
            tmp = jack.Client('tmp')
            disconnect_outputs(tmp)
            tmp.close()
        except Exception as e:
            warnings.append('Exception when disconnecting inputs: ', e)
        return state


    def change_target(throw_it):

        try:
            init.target['mag'] = np.loadtxt(init.target_mag_path)
            init.target['pha'] = np.loadtxt(init.target_pha_path)
            state = change_gain(gain)
        except Exception as e:
            warnings.append('Exception when changing target state: ', e)


    def change_input(input, state=state):

        def do_change_input(input_name, source_ports):
            """'source_ports': list [L,R] of jack output ports of chosen source
            """

            # switch
            try:
                tmp = jack.Client('tmp')
                disconnect_outputs(tmp)
                for ports_group in init.config['audio_ports']:
                    # make no more than possible connections,
                    # i.e., minimum of input or output ports
                    num_ports=min(len(ports_group), len(source_ports))
                    for i in range(num_ports):
                        # audio inputs
                        try:
                            tmp.connect(source_ports[i], ports_group[i])
                        except Exception as e:
                            warnings.append(
                                f'error connecting {source_ports[i]} <--> '
                                f'{ports_group[i]}: ', e
                                )
                tmp.close()
            except Exception as e:
                # on exception returns False
                warnings.append(f'error changing to input "{input_name}": ', e)
                tmp.close()
                return False
            return True


        state['input'] = input
        try:
            if input is None:
                raise
            elif input in init.inputs:
                if do_change_input (
                        input,
                        init.inputs[state['input']]['source_ports']):
                        # input change went OK
                    state = change_gain(gain)
                    # change xo if configured so
                    if init.config['use_input_xo']:
                        state['xo'] = init.inputs[input]['xo']
                        state = change_xovers(state['xo'])
                else:
                    warnings.append(f'Error changing to input {input}')
                    state['input']  = state_old['input']
                    state['xo'] = state_old['xo']
            else:
                state['input'] = state_old['input']
                warnings.append(
                    f'bad name: input has to be in {list(init.inputs)}'
                    )
                return state
        except Exception as e:
            state['input']  = state_old['input']
            state['xo'] = state_old['xo']
            warnings.append('Exception when changing input state: ', e)
        return state


    def change_xovers(XO_set, state=state):

        state['xo'] = XO_set
        try:
            if XO_set in init.speaker['XO']['sets']:
                coeffs = init.speaker['XO']['sets'][XO_set]
                filters = init.speaker['XO']['filters']
                for i in range(len(filters)):
                    bf_cli(f'cfc "{filters[i]}" "{coeffs[i]}"')
            else:
                state['xo'] = state_old['xo']
                warnings.append(
                    'bad name: XO has to be in '
                    f'{list(init.speaker["XO"]["sets"])}'
                    )
        except Exception as e:
            state['xo'] = state_old['xo']
            warnings.append('Exception when changing XO state: ', e)
        return state


    def change_drc(drc, state=state):

        state['drc'] = drc
        # if drc 'off' coefficient -1 is set, so latency and CPU usage \
        # are improved
        if drc == 'off':
            filters = init.speaker['DRC']['filters']
            for i in range(len(filters)):
                bf_cli(f'cfc "{filters[i]}" -1')
        else:
            try:
                if drc in init.speaker['DRC']['sets']:
                    coeffs = init.speaker['DRC']['sets'][drc]
                    filters = init.speaker['DRC']['filters']
                    for i in range(len(filters)):
                        bf_cli(f'cfc "{filters[i]}" "{coeffs[i]}"')
                else:
                    state['drc'] = state_old['drc']
                    warnings.append(
                        'bad name: DRC has to be in '
                        f'{list(init.speaker["DRC"]["sets"])}'
                        ' or \'off\''
                        )
            except Exception as e:
                state['drc'] = state_old['drc']
                warnings.append('Exception when changing DRC state: ', e)
        return state


    # following funtions prepares their corresponding actions to be performed \
    # by the change_mixer() function


    def change_channels(channels, state=state):
        
        options = ['off', 'flip', 'l', 'r']
        if channels in options:
            state['channels'] = channels
            try:
                state = change_mixer()
            except Exception as e:
                state['channels'] = state_old['channels']
                warnings.append('Exception when changing channels state: ', e)
        else:
            state['channels'] = state_old['channels']
            warnings.append(f'bad option: channels has to be in {options}')
        return state
        

    def change_polarity_inv(polarity_inv, state=state):
        
        options = ['off', 'on']
        if polarity_inv in options:
            state['polarity_inv'] = polarity_inv
            try:
                state = change_mixer()
            except Exception as e:
                state['polarity_inv'] = state_old['polarity_inv']
                warnings.append(
                    'Exception when changing polarity_inv state: ', e
                    )
        else:
            state['polarity_inv'] = state_old['polarity_inv']
            warnings.append(f'bad option: polarity_inv has to be in {options}')
        return state
        

    def change_polarity_flip(polarity_flip, state=state):
        
        options = ['off', 'on']
        if polarity_flip in options:
            state['polarity_flip'] = polarity_flip
            try:
                state = change_mixer()
            except Exception as e:
                state['polarity_flip'] = state_old['polarity_flip']
                warnings.append(
                    'Exception when changing polarity_flip state: ', e
                    )
        else:
            state['polarity_flip'] = state_old['polarity_flip']
            warnings.append(f'bad option: polarity_flip has to be in {options}')
        return state
        

    def change_midside(midside, state=state):

        options = ['off', 'mid', 'side']
        if midside in options:
            state['midside'] = midside
            try:
                state = change_mixer()
            except Exception as e:
                state['midside'] = state_old['midside']
                warnings.append('Exception when changing midside state: ', e)
        else:
            state['midside'] = state_old['midside']
            warnings.append(f'bad option: midside has to be in {options}')
        return state


    def change_solo(solo, state=state):

        options = ['off', 'l', 'r']
        if solo in options:
            state['solo'] = solo
            try:
                state = change_mixer()
            except Exception as e:
                state['solo'] = state_old['solo']
                warnings.append('Exception when changing solo state: ', e)
        else:
            state['solo'] = state_old['solo']
            warnings.append(f'bad option: solo has to be in {options}')
        return state
    
    
    # and here the change_mixer function itself

    def change_mixer(state=state):
    
        mixer = np.identity(2)
        
        match state['channels']:
            case 'flip':    mixer = np.array([[0,1],[1,0]])
            case 'l':       mixer = np.array([[1,1],[0,0]])
            case 'r':       mixer = np.array([[0,0],[1,1]])

        match state['midside']:
            case 'mid':     mixer = mixer @ np.array([[0.5,0.5],[0.5,0.5]])
            case 'side':    mixer = mixer @ np.array([[0.5,0.5],[-0.5,-0.5]])

        if state['polarity_inv'] == 'on':
            mixer = mixer @ np.array([[-1,0],[0,-1]])

        if state['polarity_flip'] == 'on':
            mixer = mixer @ np.array([[1,0],[0,-1]])

        match state['solo']:
            case 'l':       mixer = mixer * np.array([[1,0],[1,0]])
            case 'r':       mixer = mixer * np.array([[0,1],[0,1]])

        bf_cli( f'cffa "f.eq.L" "f.vol.L" m{mixer[0,0]} ; '
                f'cffa "f.eq.R" "f.vol.L" m{mixer[0,1]} ; '
                f'cffa "f.eq.L" "f.vol.R" m{mixer[1,0]} ; '
                f'cffa "f.eq.R" "f.vol.R" m{mixer[1,1]}')
    
    
    # following funtions prepares their corresponding actions to be performed \
    # by the change_gain() function

    def change_mute(mute, state=state):

        options = ['off', 'on']
        if mute in options:
            state['mute'] = mute
            try:
                state = change_gain(gain)
            except Exception as e:
                state['mute'] = state_old['mute']
                warnings.append('Exception when changing mute state: ', e)
        else:
            state['mute'] = state_old['mute']
            warnings.append(f'bad option: mute has to be in {options}')
        return state


    def change_loudness(loudness, state=state):

        if loudness in ['off', 'on']:
            state['loudness'] = loudness
            try:
                state = change_gain(gain)
            except Exception as e:
                state['loudness'] = state_old['loudness']
                warnings.append('Exception when changing loudness state: ', e)
        else:
            state['mute'] = state_old['mute']
            warnings.append(
                'bad loudness option: has to be "on" or "off"'
                )
        return state


    def change_loudness_ref(loudness_ref, state=state, add=add):

        try:
            state['loudness_ref'] = (float(loudness_ref)
                                     + state['loudness_ref'] * add
                                     )
            # clamp loudness_ref value
            if abs(state['loudness_ref']) > base.loudness_ref_variation:
                state['loudness_ref'] = m.copysign(
                                            base.loudness_ref_variation,
                                            state['loudness_ref']
                                            )
                warnings.append(
                    'loudness reference level must be in the '
                    f'+-{base.loudness_ref_variation} interval'
                    )
                warnings.append('loudness reference level clamped')
            state = change_gain(gain)
        except Exception as e:
            state['loudness_ref'] = state_old['loudness_ref']
            warnings.append('Exception when changing loudness_ref state: ', e)
        return state


    def change_treble(treble, state=state, add=add):

        try:
            state['treble'] = (float(treble)
                                    + state['treble'] * add)
            # clamp treble value
            if m.fabs(state['treble']) > base.tone_variation:
                state['treble'] = m.copysign(
                                    base.tone_variation, state['treble']
                                    )
                warnings.append(
                    'treble must be in the '
                    f'+-{base.tone_variation} interval'
                    )
                warnings.append('treble clamped')
            state = change_gain(gain)
        except Exception as e:
            state['treble'] = state_old['treble']
            warnings.append('Exception when changing treble state: ', e)
        return state


    def change_bass(bass, state=state, add=add):

        try:
            state['bass'] = float(bass) + state['bass'] * add
            # clamp bass value
            if m.fabs(state['bass']) > base.tone_variation:
                state['bass'] = m.copysign(base.tone_variation, state['bass'])
                warnings.append(
                    'bass must be in the '
                    f'+-{base.tone_variation} interval'
                    )
                warnings.append('bass clamped')
            state = change_gain(gain)
        except Exception as e:
            state['bass'] = state_old['bass']
            warnings.append('Exception when changing bass state: ', e)
        return state


    def change_balance(balance, state=state, add=add):

        try:
            state['balance'] = (float(balance)
                                    + state['balance'] * add)
            # clamp balance value
            # 'balance' means deviation from 0 in R channel
            # deviation of the L channel then goes symmetrical
            if m.fabs(state['balance']) > base.balance_variation:
                state['balance'] = m.copysign(
                                        base.balance_variation,
                                        state['balance']
                                        )
                warnings.append(
                    'balance must be in the '
                    f'+-{base.balance_variation} interval'
                    )
                warnings.append('balance clamped')
            state = change_gain(gain)
        except Exception as e:
            state['balance'] = state_old['balance']
            warnings.append('Exception when changing balance state: ', e)
        return state


    def change_level(level, state=state, add=add):

        # level clamp is comissioned to change_gain()
        try:
            state['level'] = (float(level) + state['level'] * add)
            gain = pd.calc_gain(state['level'])
            state = change_gain(gain)
        except Exception as e:
            state['level'] = state_old['level']
            warnings.append(f'Exception when changing {command} state: ', e)
        return state


    # and here the change_gain function itself

    def change_gain(gain, state=state):
        """change_gain, aka 'the volume machine' :-)"""

        def change_eq():

            eq_str = ''
            l = len(curves['frequencies'])
            for i in range(l):
                eq_str = (f'{eq_str}{curves["frequencies"][i]}/{eq_mag[i]}')
                if i != l:
                    eq_str += ', '
            bf_cli(f'lmc eq "c.eq" mag {eq_str}')
            eq_str = ''
            for i in range(l):
                eq_str = (f'{eq_str}{curves["frequencies"][i]}/{eq_pha[i]}')
                if i != l:
                    eq_str += ', '
            bf_cli(f'lmc eq "c.eq" phase {eq_str}')


        def change_loudness():

            # index of max loudness tones boost
            loudness_max_i = (base.loudness_SPLmax - base.loudness_SPLmin)
            # index of all zeros curve
            loudness_null_i = (base.loudness_SPLmax - base.loudness_SPLref)
            # set curve index
            # higher index means higher boost
            # increasing 'level' decreases boost
            # increasing 'loudness_ref' increases boost
            if state['loudness'] == 'on':
                loudness_i = (
                    loudness_null_i
                    - state['level']
                    + state['loudness_ref']
                    )
            else:
                # all zeros curve
                loudness_i = loudness_null_i
            if loudness_i < 0:
                loudness_i = 0
            if loudness_i > loudness_max_i:
                loudness_i = loudness_max_i
            # loudness_i must be integer as it will be used as \
            # index of loudness curves array
            loudness_i = int(round(loudness_i))
            loudeq_mag = curves['loudness_mag_curves'][:,loudness_i]
            eq_mag = loudeq_mag
            eq_pha = curves['loudness_pha_curves'][:,loudness_i]
            return eq_mag, eq_pha


        def change_treble():

            treble_i = base.tone_variation - state['treble']
            # force integer
            treble_i = int(round(treble_i))
            eq_mag = curves['treble_mag_curves'][:,treble_i]
            eq_pha = curves['treble_pha_curves'][:,treble_i]
            return eq_mag, eq_pha


        def change_bass():

            bass_i = base.tone_variation - state['bass']
            # force integer
            bass_i = int(round(bass_i))
            eq_mag = curves['bass_mag_curves'][:,bass_i]
            eq_pha = curves['bass_pha_curves'][:,bass_i]
            return eq_mag, eq_pha


        def commit_gain(gain):

            bf_atten_dB_l = gain
            bf_atten_dB_r = gain
            # add balance dB gains
            bf_atten_dB_l = bf_atten_dB_l - state['balance']
            bf_atten_dB_r = bf_atten_dB_r + state['balance']
            # from dB to multiplier to implement mute easily
            # then channel gains are the product of \
            # gain and mute
            m_mute = {'on': 0, 'off': 1}[state['mute']]
            def m_gain(x): return m.pow(10, x/20) * m_mute
            m_gain_l = m_gain(bf_atten_dB_l)
            m_gain_r = m_gain(bf_atten_dB_r)
            # commit final gain change
            bf_cli(f'cfia "f.vol.L" "i.L" m{str(m_gain_l)} ; '
                   f'cfia "f.vol.R" "i.R" m{str(m_gain_r)}')


        # gain command send its str argument directly
        gain = float(gain)
        # clamp gain value
        # just for information, numerical bounds before math range or \
        # math domain error are +6165 dB and -6472 dB
        # max gain is clamped downstream when calculating headroom
        if gain < base.gain_min:
            gain = base.gain_min
            warnings.append(f'min. gain must be more than {base.gain_min} dB')
            warnings.append('gain clamped')
        # EQ curves: loudness + treble + bass
        l_mag,      l_pha      = change_loudness()
        t_mag,      t_pha      = change_treble()
        b_mag,      b_pha      = change_bass()
        # compose EQ curves with target
        eq_mag = init.target['mag'] + l_mag + t_mag + b_mag
        eq_pha = init.target['pha'] + l_pha + t_pha + b_pha
        # calculate headroom
        headroom = pd.calc_headroom(gain, state['balance'], eq_mag)
        # adds input gain. It can lead to clipping \
        # because assumes equal dynamic range between sources
        real_gain = gain + pd.calc_input_gain(state['input'])
        # if enough headroom commit changes
        if headroom >= 0:
            commit_gain(real_gain)
            change_eq()
            state['level'] = pd.calc_level(gain)
        # if not enough headroom tries lowering gain
        else:
            change_gain(gain + headroom)
            print('headroom hit, lowering gain...')
        return state
    # end of change_gain()


    ## parse  commands and select corresponding actions

    try:
        state = {
            'show':             show,                   #
            'noinput':          noinput,                #
            'target':           change_target,          #
            'input':            change_input,           #[input]
            'xo':               change_xovers,          #[XO_set]
            'drc':              change_drc,             #['off',drc]

            'channels':         change_channels,        #['off','flip','l','r']
            'polarity_inv':     change_polarity_inv,    #['off','on']
            'polarity_flip':    change_polarity_flip,   #['off','on']
            'midside':          change_midside,         #['off','mid','side']
            'solo':             change_solo,            #['off','l','r']

            'mute':             change_mute,            #['off','on']
            'loudness':         change_loudness,        #['off','on']
            'loudness_ref':     change_loudness_ref,    #[loudness_ref]
            'treble':           change_treble,          #[treble]
            'bass':             change_bass,            #[bass]
            'balance':          change_balance,         #[balance]
            'level':            change_level,           #[level]
            'gain':             change_gain             #[gain]
            }[command](arg)
    except KeyError:
        warnings.append(f"Unknown command '{command}'")
    except Exception as e:
        print(f"Problems in command '{command}': ", e)

    # return a dictionary of predic state
    return (state, warnings)

# end of proccess_commands()
