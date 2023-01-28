# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import time
import jack
import math as m

import numpy as np

import baseconfig as base
import init
import pdlib as pd

from camilladsp import CamillaConnection

# connect to camilladsp and get camilladsp config once
cdsp = CamillaConnection("localhost", init.config['websocket_port'])
cdsp.connect()
cdsp_config = cdsp.get_config()

# merge drc filters in camilladsp config
for drc_set in init.drc:
    drc_channels = init.drc[drc_set]['channels']
    for channel in range(len(drc_channels)):
        cdsp_config['filters'].update(drc_channels[channel]['filters'])

# merge eq filters in camilladsp config
for eq_set in init.eq:
    cdsp_config['filters'].update(init.eq[eq_set]['filters'])

# merge loudspeaker specific settings in camilladsp config
cdsp_config['filters'].update(init.speaker['filters'])
cdsp_config['mixers'].update(init.speaker['mixers'])
cdsp_config['pipeline'].extend(init.speaker['pipeline'])


class OptionsError(Exception):
    """exception for options revealing"""
    
    def __init__(self, options):
        self.options = options
        
class ClampWarning(Warning):
    
    def __init__(self, clamp_value):
        self.clamp_value = clamp_value


# main function for command proccessing
def proccess_commands(full_command, state=init.state):
    """proccesses commands for predic control"""

    # let camilladsp connection be visible
    global cdsp
    # control variable for switching to relative commands
    add = False
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

    def disconnect_sources(jack_client):
        """disconnect sources from predic audio ports"""

        for port_group in init.config['audio_ports']:
            for port in port_group:
                sources = jack_client.get_all_connections(port)
                for source in sources:
                    jack_client.disconnect(source.name, port)

    
    def toggle(command, state=state):
        """changes state of on/off commands"""
        
        return {'off': 'on', 'on': 'off'}[state[command]]
    

    def do_command(command, arg, state=state):
        
        if arg:
            try:
                command(arg, state)
            except ClampWarning as w:
                print(f"'{command.__name__}' value clamped: {w.clamp_value}")
            except OptionsError as e:
                print(f"Bad option. Options has to be in : {list(e.options)}")
            except Exception as e:
                state[command.__name__]  = state_old[command.__name__]
                print(f"Exception in command '{command.__name__}': ", e)
        else:
            print(f"Command '{command.__name__}' needs an option")
        return state
    
    
    ## internal functions for actions

    def show(state=state):
        """show status in a readable way"""
        
        pd.show_file()
        return state


    def mute(mute, state=state):

        options = {'off', 'on', 'toggle'}
        if mute in options:
            if mute == 'toggle':
                mute = toggle('mute')
            state['mute'] = mute
            match mute:
                case 'off':
                    cdsp.set_mute(False)
                case 'on':
                    cdsp.set_mute(True)
        else:
            raise OptionsError(options)
        return state


    def level(level, state=state, add=add):

        # level clamp is comissioned to set_gain()
        state['level'] = (float(level) + state['level'] * add)
        gain = pd.calc_gain(state['level'])
        state = set_gain(gain)
        return state


    def sources(sources, state=state):

        options = {'off', 'on', 'toggle'}
        if sources in options:
            if sources == 'toggle':
                sources = toggle('sources')
            state['sources'] = sources
            match sources:
                case 'off':
                    tmp = jack.Client('tmp')
                    disconnect_sources(tmp)
                    tmp.close()
                case 'on':
                    source(state['source'])
        else:
            raise OptionsError(options)
        return state


    def source(source, state=state):

        options = init.sources
        if source in options:
            state['source'] = source
            source_ports = init.sources[state['source']]['source_ports']
            # switch
            tmp = jack.Client('tmp')
            disconnect_sources(tmp)
            for ports_group in init.config['audio_ports']:
                # make no more than possible connections,
                # i.e., minimum of input or output ports
                num_ports=min(len(ports_group), len(source_ports))
                for i in range(num_ports):
                    # audio sources
                    tmp.connect(source_ports[i], ports_group[i])
            tmp.close()
            # source change went OK
            state = set_gain(gain)
            # change phase_eq if configured so
            if init.config['use_source_phase_eq']:
                phase_eq(init.sources[source]['phase_eq'])
        else:
            raise OptionsError(options)
        return state


    def drc(drc, state=state):

        options = {'off', 'on', 'toggle'}
        if drc in options:
            if drc == 'toggle':
                drc = toggle('drc')
            state['drc'] = drc
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    def drc_set(drc_set, state=state):

        options = init.drc
        if drc_set in options:
            state['drc_set'] = drc_set
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    def phase_eq(phase_eq, state=state):

        options = {'off', 'on', 'toggle'}
        if phase_eq in options:
            if phase_eq == 'toggle':
                phase_eq = toggle('phase_eq')
            state['phase_eq'] = phase_eq
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    def channels(channels, state=state):
        
        options = {'lr', 'l', 'r'}
        if channels in options:
            state['channels'] = channels
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state
        

    def channels_flip(channels_flip, state=state):
        
        options = {'off', 'on', 'toggle'}
        if channels_flip in options:
            if channels_flip == 'toggle':
                channels_flip = toggle('channels_flip')
            state['channels_flip'] = channels_flip
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state
        

    def polarity(polarity, state=state):
        
        options = {'off', 'on', 'toggle'}
        if polarity in options:
            if polarity == 'toggle':
                polarity = toggle('polarity')
            state['polarity'] = polarity
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state
        

    def polarity_flip(polarity_flip, state=state):
        
        options = {'off', 'on', 'toggle'}
        if polarity_flip in options:
            if polarity_flip == 'toggle':
                polarity_flip = toggle('polarity_flip')
            state['polarity_flip'] = polarity_flip
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state
        

    def stereo(stereo, state=state):

        options = {'normal', 'mid', 'side'}
        if stereo in options:
            state['stereo'] = stereo
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state


    def solo(solo, state=state):

        options = {'lr', 'l', 'r'}
        if solo in options:
            state['solo'] = solo
            state = set_mixer()
        else:
            raise OptionsError(options)
        return state
    
    
    def loudness(loudness, state=state):

        options = {'off', 'on', 'toggle'}
        if loudness in options:
            if loudness == 'toggle':
                loudness = toggle('loudness')
            state['loudness'] = loudness
            if state['loudness'] == 'off':
                cdsp_config['pipeline'][0]['names'] = ["f.volume"]
                cdsp_config['pipeline'][1]['names'] = ["f.volume"]
            else:
                cdsp_config['pipeline'][0]['names'] = ["f.loudness"]
                cdsp_config['pipeline'][1]['names'] = ["f.loudness"]
        else:
            raise OptionsError(options)
        return state


    def loudness_ref(loudness_ref, state=state, add=add):

        state['loudness_ref'] = (float(loudness_ref)
                                    + state['loudness_ref'] * add
                                    )
        # clamp loudness_ref value
        if abs(state['loudness_ref']) > base.loudness_ref_variation:
            state['loudness_ref'] = m.copysign(
                                        base.loudness_ref_variation,
                                        state['loudness_ref']
                                        )
            raise ClampWarning(state['loudness_ref'])
        # set loudness reference_level as absolute gain
        cdsp_config['filters']['f.loudness']['parameters']['reference_level']=(
            pd.calc_gain(state['loudness_ref']))
        return state


    def tones(tones, state=state):

        options = {'off', 'on', 'toggle'}
        if tones in options:
            if tones == 'toggle':
                tones = toggle('tones')
            state['tones'] = tones
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    # following funtions prepares their corresponding actions to be performed \
    # by the set_gain() function

    def treble(treble, state=state, add=add):

        state['treble'] = (float(treble)
                                + state['treble'] * add)
        # clamp treble value
        if m.fabs(state['treble']) > base.tone_variation:
            state['treble'] = m.copysign(base.tone_variation, state['treble'])
            raise ClampWarning(state['treble'])
        # set treble
        cdsp_config['filters']['f.treble']['parameters']['gain']=(
            state['treble']
            )
        state = set_gain(gain)
        return state


    def bass(bass, state=state, add=add):

        state['bass'] = float(bass) + state['bass'] * add
        # clamp bass value
        if m.fabs(state['bass']) > base.tone_variation:
            state['bass'] = m.copysign(base.tone_variation, state['bass'])
            raise ClampWarning(state['bass'])
        # set bass
        cdsp_config['filters']['f.bass']['parameters']['gain']=(
            state['bass']
            )
        state = set_gain(gain)
        return state


    def eq(eq, state=state):

        options = {'off', 'on', 'toggle'}
        if eq in options:
            if eq == 'toggle':
                eq = toggle('eq')
            state['eq'] = eq
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    def eq_filter(eq_filter, state=state):

        options = init.eq
        if eq_filter in options:
            state['eq_filter'] = eq_filter
            set_pipeline()
        else:
            raise OptionsError(options)
        return state


    def balance(balance, state=state, add=add):

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
            raise ClampWarning(state['balance'])
        # add balance dB gains
        atten_dB_r = state['balance']
        atten_dB_l = - (state['balance'])
        cdsp_config['filters']['f.balance.L']['parameters']['gain']=(
            atten_dB_l
            )
        cdsp_config['filters']['f.balance.R']['parameters']['gain']=(
            atten_dB_r
            )
        state = set_gain(gain)
        return state


    ## following funtions perform actual backend adjustments

    def set_pipeline():

        pipeline_common = []
        if state['tones'] == 'on':
            pipeline_common.extend(['f.bass','f.treble'])
        if state['phase_eq'] == 'on':
            pipeline_common.append('f.phase_eq')
        if state['eq'] == 'on':
            pipeline_common.extend(init.eq[state['eq_filter']]['pipeline'])
        
        pipeline = [['f.balance.L'],['f.balance.R']]
        for channel in range(2):
            pipeline[channel].extend(pipeline_common)
            if state['drc'] == 'on':
                drc_channels = (init.drc[state['drc_set']]['channels'])
                pipeline[channel].extend(drc_channels[channel]['pipeline'])

        cdsp_config['pipeline'][3]['names'] = pipeline[0]
        cdsp_config['pipeline'][4]['names'] = pipeline[1]


    def set_mixer(state=state):
    
        mixer = np.identity(2)
        
        if state['channels_flip'] == 'on':
            mixer = np.array([[0,1],[1,0]])

        match state['channels']:
            case 'l':       mixer = mixer @ np.array([[1,1],[0,0]])
            case 'r':       mixer = mixer @ np.array([[0,0],[1,1]])

        match state['stereo']:
            case 'mid':     mixer = mixer @ np.array([[0.5,0.5],[0.5,0.5]])
            case 'side':    mixer = mixer @ np.array([[0.5,0.5],[-0.5,-0.5]])

        if state['polarity'] == 'on':
            mixer = mixer @ np.array([[-1,0],[0,-1]])

        if state['polarity_flip'] == 'on':
            mixer = mixer @ np.array([[1,0],[0,-1]])

        match state['solo']:
            case 'l':       mixer = mixer * np.array([[1,0],[1,0]])
            case 'r':       mixer = mixer * np.array([[0,1],[0,1]])

        # gain
        for sources in range(2):
            for dest in range(2):
                if mixer[sources, dest]:
                    (cdsp_config['mixers']['m.mixer']['mapping'][dest]
                        ['sources'][sources]['gain']) = (
                            pd.gain_dB(abs(mixer[sources, dest]))
                            )
                else:
                    (cdsp_config['mixers']['m.mixer']['mapping'][dest]
                        ['sources'][sources]['gain']) = (
                            0
                            )
        
        # inverted
        for sources in range(2):
            for dest in range(2):
                (cdsp_config['mixers']['m.mixer']['mapping'][dest]
                    ['sources'][sources]['inverted']) = (
                        bool(mixer[sources, dest] < 0)
                        )
        
        # mute
        for sources in range(2):
            for dest in range(2):
                (cdsp_config['mixers']['m.mixer']['mapping'][dest] 
                    ['sources'][sources]['mute']) = (
                        not bool(mixer[sources, dest])
                        )

        # for debug
        if init.config['verbose'] in {1, 2}:
            print(f'mixer matrix : \n{mixer}\n')
    

    def set_gain(gain, state=state):
        """set_gain, aka 'the volume machine' :-)"""

        # gain command send its str argument directly
        gain = float(gain)
        # clamp gain value
        # just for information, numerical bounds before math range or \
        # math domain error are +6165 dB and -6472 dB
        # max gain is clamped downstream when calculating headroom
        if gain < base.gain_min:
            gain = base.gain_min
            print(f'min. gain must be more than {base.gain_min} dB')
            print('gain clamped')
        # calculate headroom
        headroom = pd.calc_headroom(gain, state)
        # adds source gain. It can lead to clipping \
        # because assumes equal dynamic range between sources
        real_gain = gain + pd.calc_source_gain(state['source'])
        # if enough headroom commit changes
        # since there is no state['gain'] we set state['level']
        if headroom >= 0:
            cdsp.set_volume(real_gain)
            state['level'] = pd.calc_level(gain)
        # if not enough headroom tries lowering gain
        else:
            set_gain(gain + headroom)
            print('headroom hit, lowering gain...')
        return state


    ## parse  commands and select corresponding actions

    try:
        if command in {'show'}:
            # commands without options
            state = {
                'show':             show            #
                }[command]()

        elif command in {'mute', 'level', 'gain'}:
            # commands that do not depend on camilladsp
            state = do_command(
                {
                'mute':             mute,           #['off','on','toggle']
                'level':            level,          #[level] add
                'gain':             set_gain        #[gain]
                }[command], arg)

        else:
            # commands that depend on camilladsp
            state = do_command(
                {
                'sources':          sources,        #['off','on','toggle']
                'source':           source,         #[source]
                'drc':              drc,            #['off','on','toggle']
                'drc_set':          drc_set,        #[drc_set]
                'phase_eq':         phase_eq,       #['off','on','toggle']

                'channels':         channels,       #['lr','l','r']
                'channels_flip':    channels_flip,  #['off','on','toggle']
                'polarity':         polarity,       #['off','on','toggle']
                'polarity_flip':    polarity_flip,  #['off','on','toggle']
                'stereo':           stereo,         #['off','mid','side']
                'solo':             solo,           #['lr','l','r']

                'loudness':         loudness,       #['off','on','toggle']
                'loudness_ref':     loudness_ref,   #[loudness_ref] add
                'tones':            tones,          #['off','on','toggle']
                'treble':           treble,         #[treble] add
                'bass':             bass,           #[bass] add
                'eq':               eq,             #['off','on','toggle']
                'eq_filter':        eq_filter,      #[eq_filter]
                'balance':          balance         #[balance] add
                }[command], arg)

            # dispatch config
            cdsp.set_config(cdsp_config)

    except KeyError:
        print(f"Unknown command '{command}'")
    # except Exception as e:
    #     print(f"Problems in command '{command}': ", e)

    # return a dictionary of predic state
    return (state)

# end of proccess_commands()
