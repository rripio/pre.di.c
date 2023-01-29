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
def proccess_commands(full_command):
    """proccesses commands for predic control"""

    # let camilladsp connection be visible
    global cdsp
    # control variable for switching to relative commands
    add = False
    # backup state to restore values in case of not enough headroom \
    # or error of any kind
    state_old = init.state.copy()

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
    gain = pd.calc_gain(init.state['level'])


    ## auxiliary functions

    def disconnect_sources(jack_client):
        """disconnect sources from predic audio ports"""

        for port_group in init.config['audio_ports']:
            for port in port_group:
                sources = jack_client.get_all_connections(port)
                for source in sources:
                    jack_client.disconnect(source.name, port)

    
    def toggle(command):
        """changes state of on/off commands"""
        
        return {'off': 'on', 'on': 'off'}[init.state[command]]
    

    def do_command(command, arg):
        
        if arg:
            try:
                command(arg)
            except ClampWarning as w:
                print(f"'{command.__name__}' value clamped: {w.clamp_value}")
            except OptionsError as e:
                print(f"Bad option. Options has to be in : {list(e.options)}")
            except Exception as e:
                init.state[command.__name__]  = state_old[command.__name__]
                print(f"Exception in command '{command.__name__}': ", e)
        else:
            print(f"Command '{command.__name__}' needs an option")
    
    
    ## internal functions for actions

    def show():
        """show status in a readable way"""
        
        pd.show_file()


    def mute(mute):

        options = {'off', 'on', 'toggle'}
        if mute in options:
            if mute == 'toggle':
                mute = toggle('mute')
            init.state['mute'] = mute
            match mute:
                case 'off':
                    cdsp.set_mute(False)
                case 'on':
                    cdsp.set_mute(True)
        else:
            raise OptionsError(options)


    def level(level, add=add):

        # level clamp is comissioned to set_gain()
        init.state['level'] = (float(level) + init.state['level'] * add)
        gain = pd.calc_gain(init.state['level'])
        set_gain(gain)


    def sources(sources):

        options = {'off', 'on', 'toggle'}
        if sources in options:
            if sources == 'toggle':
                sources = toggle('sources')
            init.state['sources'] = sources
            match sources:
                case 'off':
                    tmp = jack.Client('tmp')
                    disconnect_sources(tmp)
                    tmp.close()
                case 'on':
                    source(init.state['source'])
        else:
            raise OptionsError(options)


    def source(source):

        options = init.sources
        if source in options:
            init.state['source'] = source
            source_ports = init.sources[init.state['source']]['source_ports']
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
            set_gain(gain)
            # change phase_eq if configured so
            if init.config['use_source_phase_eq']:
                phase_eq(init.sources[source]['phase_eq'])
        else:
            raise OptionsError(options)


    def drc(drc):

        options = {'off', 'on', 'toggle'}
        if drc in options:
            if drc == 'toggle':
                drc = toggle('drc')
            init.state['drc'] = drc
            set_pipeline()
        else:
            raise OptionsError(options)


    def drc_set(drc_set):

        options = init.drc
        if drc_set in options:
            init.state['drc_set'] = drc_set
            set_pipeline()
        else:
            raise OptionsError(options)


    def phase_eq(phase_eq):

        options = {'off', 'on', 'toggle'}
        if phase_eq in options:
            if phase_eq == 'toggle':
                phase_eq = toggle('phase_eq')
            init.state['phase_eq'] = phase_eq
            set_pipeline()
        else:
            raise OptionsError(options)


    def channels(channels):
        
        options = {'lr', 'l', 'r'}
        if channels in options:
            init.state['channels'] = channels
            set_mixer()
        else:
            raise OptionsError(options)
        

    def channels_flip(channels_flip):
        
        options = {'off', 'on', 'toggle'}
        if channels_flip in options:
            if channels_flip == 'toggle':
                channels_flip = toggle('channels_flip')
            init.state['channels_flip'] = channels_flip
            set_mixer()
        else:
            raise OptionsError(options)
        

    def polarity(polarity):
        
        options = {'off', 'on', 'toggle'}
        if polarity in options:
            if polarity == 'toggle':
                polarity = toggle('polarity')
            init.state['polarity'] = polarity
            set_mixer()
        else:
            raise OptionsError(options)
        

    def polarity_flip(polarity_flip):
        
        options = {'off', 'on', 'toggle'}
        if polarity_flip in options:
            if polarity_flip == 'toggle':
                polarity_flip = toggle('polarity_flip')
            init.state['polarity_flip'] = polarity_flip
            set_mixer()
        else:
            raise OptionsError(options)
        

    def stereo(stereo):

        options = {'normal', 'mid', 'side'}
        if stereo in options:
            init.state['stereo'] = stereo
            set_mixer()
        else:
            raise OptionsError(options)


    def solo(solo):

        options = {'lr', 'l', 'r'}
        if solo in options:
            init.state['solo'] = solo
            set_mixer()
        else:
            raise OptionsError(options)
    
    
    def loudness(loudness):

        options = {'off', 'on', 'toggle'}
        if loudness in options:
            if loudness == 'toggle':
                loudness = toggle('loudness')
            init.state['loudness'] = loudness
            if init.state['loudness'] == 'off':
                cdsp_config['pipeline'][0]['names'] = ["f.volume"]
                cdsp_config['pipeline'][1]['names'] = ["f.volume"]
            else:
                cdsp_config['pipeline'][0]['names'] = ["f.loudness"]
                cdsp_config['pipeline'][1]['names'] = ["f.loudness"]
        else:
            raise OptionsError(options)


    def loudness_ref(loudness_ref, add=add):

        init.state['loudness_ref'] = (float(loudness_ref)
                                    + init.state['loudness_ref'] * add
                                    )
        # clamp loudness_ref value
        if abs(init.state['loudness_ref']) > base.loudness_ref_variation:
            init.state['loudness_ref'] = m.copysign(
                                        base.loudness_ref_variation,
                                        init.state['loudness_ref']
                                        )
            raise ClampWarning(init.state['loudness_ref'])
        # set loudness reference_level as absolute gain
        cdsp_config['filters']['f.loudness']['parameters']['reference_level']=(
            pd.calc_gain(init.state['loudness_ref']))


    def tones(tones):

        options = {'off', 'on', 'toggle'}
        if tones in options:
            if tones == 'toggle':
                tones = toggle('tones')
            init.state['tones'] = tones
            set_pipeline()
        else:
            raise OptionsError(options)


    # following funtions prepares their corresponding actions to be performed \
    # by the set_gain() function

    def treble(treble, add=add):

        init.state['treble'] = (float(treble)
                                + init.state['treble'] * add)
        # clamp treble value
        if m.fabs(init.state['treble']) > base.tone_variation:
            init.state['treble'] = m.copysign(base.tone_variation, init.state['treble'])
            raise ClampWarning(init.state['treble'])
        # set treble
        cdsp_config['filters']['f.treble']['parameters']['gain']=(
            init.state['treble']
            )
        set_gain(gain)


    def bass(bass, add=add):

        init.state['bass'] = float(bass) + init.state['bass'] * add
        # clamp bass value
        if m.fabs(init.state['bass']) > base.tone_variation:
            init.state['bass'] = m.copysign(base.tone_variation, init.state['bass'])
            raise ClampWarning(init.state['bass'])
        # set bass
        cdsp_config['filters']['f.bass']['parameters']['gain']=(
            init.state['bass']
            )
        set_gain(gain)


    def eq(eq):

        options = {'off', 'on', 'toggle'}
        if eq in options:
            if eq == 'toggle':
                eq = toggle('eq')
            init.state['eq'] = eq
            set_pipeline()
        else:
            raise OptionsError(options)


    def eq_filter(eq_filter):

        options = init.eq
        if eq_filter in options:
            init.state['eq_filter'] = eq_filter
            set_pipeline()
        else:
            raise OptionsError(options)


    def balance(balance, add=add):

        init.state['balance'] = (float(balance)
                                + init.state['balance'] * add)
        # clamp balance value
        # 'balance' means deviation from 0 in R channel
        # deviation of the L channel then goes symmetrical
        if m.fabs(init.state['balance']) > base.balance_variation:
            init.state['balance'] = m.copysign(
                                    base.balance_variation,
                                    init.state['balance']
                                    )
            raise ClampWarning(init.state['balance'])
        # add balance dB gains
        atten_dB_r = init.state['balance']
        atten_dB_l = - (init.state['balance'])
        cdsp_config['filters']['f.balance.L']['parameters']['gain']=(
            atten_dB_l
            )
        cdsp_config['filters']['f.balance.R']['parameters']['gain']=(
            atten_dB_r
            )
        set_gain(gain)


    ## following funtions perform actual backend adjustments

    def set_pipeline():

        pipeline_common = []
        if init.state['tones'] == 'on':
            pipeline_common.extend(['f.bass','f.treble'])
        if init.state['phase_eq'] == 'on':
            pipeline_common.append('f.phase_eq')
        if init.state['eq'] == 'on':
            pipeline_common.extend(init.eq[init.state['eq_filter']]['pipeline'])
        
        pipeline = [['f.balance.L'],['f.balance.R']]
        for channel in range(2):
            pipeline[channel].extend(pipeline_common)
            if init.state['drc'] == 'on':
                drc_channels = (init.drc[init.state['drc_set']]['channels'])
                pipeline[channel].extend(drc_channels[channel]['pipeline'])

        cdsp_config['pipeline'][3]['names'] = pipeline[0]
        cdsp_config['pipeline'][4]['names'] = pipeline[1]


    def set_mixer():
    
        mixer = np.identity(2)
        
        if init.state['channels_flip'] == 'on':
            mixer = np.array([[0,1],[1,0]])

        match init.state['channels']:
            case 'l':       mixer = mixer @ np.array([[1,1],[0,0]])
            case 'r':       mixer = mixer @ np.array([[0,0],[1,1]])

        match init.state['stereo']:
            case 'mid':     mixer = mixer @ np.array([[0.5,0.5],[0.5,0.5]])
            case 'side':    mixer = mixer @ np.array([[0.5,0.5],[-0.5,-0.5]])

        if init.state['polarity'] == 'on':
            mixer = mixer @ np.array([[-1,0],[0,-1]])

        if init.state['polarity_flip'] == 'on':
            mixer = mixer @ np.array([[1,0],[0,-1]])

        match init.state['solo']:
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
    

    def set_gain(gain):
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
        headroom = pd.calc_headroom(gain)
        # adds source gain. It can lead to clipping \
        # because assumes equal dynamic range between sources
        real_gain = gain + pd.calc_source_gain(init.state['source'])
        # if enough headroom commit changes
        # since there is no init.state['gain'] we set init.state['level']
        if headroom >= 0:
            cdsp.set_volume(real_gain)
            init.state['level'] = pd.calc_level(gain)
        # if not enough headroom tries lowering gain
        else:
            set_gain(gain + headroom)
            print('headroom hit, lowering gain...')


    ## parse  commands and select corresponding actions

    try:
        if command in {'show'}:
            # commands without options
                {
                'show':             show            #
                }[command]()

        elif command in {'mute', 'level', 'gain'}:
            # commands that do not depend on camilladsp
            do_command(
                {
                'mute':             mute,           #['off','on','toggle']
                'level':            level,          #[level] add
                'gain':             set_gain        #[gain]
                }[command], arg)

        else:
            # commands that depend on camilladsp
            do_command(
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

# end of proccess_commands()
