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


### flags


add = False             # switch to relative commands
clamp_gain = True       # allows gain clamp


### exception definitions


class OptionsError(Exception):
    """
    exception for options revealing
    """
    
    def __init__(self, options):
        self.options = options
        
class ClampWarning(Warning):
    
    def __init__(self, clamp_value):
        self.clamp_value = clamp_value


### auxiliary functions


def disconnect_sources(jack_client):
    """
    disconnect sources from predic audio ports
    """

    for ports_group in init.config['audio_ports']:
        for in_port in ports_group:
            for out_port in jack_client.get_all_connections(in_port):
                jack_client.disconnect(out_port, in_port)


def toggle(command):
    """
    changes state of on/off commands
    """
    
    return {'off': 'on', 'on': 'off'}[init.state[command]]


def do_command(command, arg):
    """
    command wrapper
    """
    
    # backup state to restore values in case of not enough headroom \
    # or error of any kind
    state_old = init.state.copy()

    if arg:
        try:
            command(arg)
        except ClampWarning as w:
            print(f"\n(control) '{command.__name__}' value clamped: ",
                  w.clamp_value)
        except OptionsError as e:
            print("\n(control) Bad option. Options has to be in : ",
                  list(e.options))
        except ValueError as e:
            print(f"\n(control) Command '{command.__name__}' ",
                  f"needs a number: {e}")
        except Exception as e:
            init.state[command.__name__]  = state_old[command.__name__]
            print(f"\n(control) Exception in command '{command.__name__}': ",
                  e)
    else:
        print(f"\n(control) Command '{command.__name__}' needs an option")


### internal functions for commands


## commands without options


def show():
    """
    show status in a readable way
    """
    
    pd.show_file(clamp_gain)


## commands that do not depend on camilladsp config


# numerical commands that accept 'add'


def level(level):
    """
    change level (gain relative to reference_level)
    """
    # level clamp is comissioned to set_gain()
    init.state['level'] = (float(level) + init.state['level'] * add)
    gain = pd.calc_gain(init.state['level'])
    set_gain(gain)


# on/off commands


def clamp(clamp):
    """
    frees gain setting from clamping:
    useful for playing  low level files
    """
    
    # allows changing flag
    global clamp_gain

    options = {'off', 'on', 'toggle'}
    if clamp in options:
        if clamp == 'toggle':
            clamp = toggle('clamp')
        clamp_gain = {'off': False, 'on': True}[clamp]
        if clamp_gain:
            level(init.state['level'])
    else:
        raise OptionsError(options)


def mute(mute):
    """
    mute output
    """

    options = {'off', 'on', 'toggle'}
    if mute in options:
        if mute == 'toggle':
            mute = toggle('mute')
        init.state['mute'] = mute
        cdsp.set_mute({'off': False, 'on': True}[mute])
    else:
        raise OptionsError(options)


## commands that depend on camilladsp config


# numerical commands that accept 'add'


def loudness_ref(loudness_ref):
    """
    select loudness reference level (correction threshold level)
    """

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


def bass(bass):
    """
    select bass level correction
    """

    init.state['bass'] = float(bass) + init.state['bass'] * add
    # clamp bass value
    if m.fabs(init.state['bass']) > base.tone_variation:
        init.state['bass'] = m.copysign(base.tone_variation, init.state['bass'])
        raise ClampWarning(init.state['bass'])
    # set bass
    cdsp_config['filters']['f.bass']['parameters']['gain']=(
        init.state['bass']
        )
    set_gain(pd.calc_gain(init.state['level']))


def treble(treble):
    """
    select treble level correction
    """

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
    set_gain(pd.calc_gain(init.state['level']))


def balance(balance):
    """
    select balance level
    'balance' means deviation from 0 in R channel
    deviation of the L channel then goes symmetrical
    """

    init.state['balance'] = (float(balance)
                            + init.state['balance'] * add)
    # clamp balance value
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
    set_gain(pd.calc_gain(init.state['level']))


# non numerical commands


def source(source):
    """
    change source
    """
    
    
    # allows changing flag
    global clamp_gain
    # reset clamp_gain to True when changing sources
    clamp_gain = True

    options = init.sources
    if source in options:
        init.state['source'] = source
        source_ports = init.sources[init.state['source']]['source_ports']
        source_ports_len = len(source_ports)
        tmp = jack.Client('tmp')

        # check if ports are already connected
        connected = False
        for ports_group in init.config['audio_ports']:
            # for audio_port in ports_group:
            # get max number of possible connectios
            num_ports=min(len(ports_group), source_ports_len)
            for i in range(num_ports):
                for port in tmp.get_all_connections(ports_group[i]):
                    connected = port.name in source_ports
        if connected:
            print('\n(control) source already selected')
            tmp.close()
            return
        else:
            disconnect_sources(tmp)
            for ports_group in init.config['audio_ports']:
                # make no more than possible connections,
                # i.e., minimum of input or output ports
                num_ports=min(len(ports_group), source_ports_len)
                for i in range(num_ports):
                    # audio sources
                    tmp.connect(source_ports[i], ports_group[i])
            tmp.close()
            # source change went OK
            set_gain(pd.calc_gain(init.state['level']))
            # change phase_eq if configured so
            if init.config['use_source_phase_eq']:
                phase_eq(init.sources[source]['phase_eq'])
    else:
        raise OptionsError(options)


def drc_set(drc_set):
    """
    change drc filters
    """

    options = init.drc
    if drc_set in options:
        init.state['drc_set'] = drc_set
        set_pipeline()
    else:
        raise OptionsError(options)


def eq_filter(eq_filter):
    """
    select general equalizer filter
    """

    options = init.eq
    if eq_filter in options:
        init.state['eq_filter'] = eq_filter
        set_pipeline()
    else:
        raise OptionsError(options)


def stereo(stereo):
    """
    change mix to normal stereo, mono, or midside side
    """

    options = {'normal', 'mid', 'side'}
    if stereo in options:
        init.state['stereo'] = stereo
        set_mixer()
    else:
        raise OptionsError(options)


def channels(channels):
    """
    select input channels (mixed to both output channels)
    """
    
    options = {'lr', 'l', 'r'}
    if channels in options:
        init.state['channels'] = channels
        set_mixer()
    else:
        raise OptionsError(options)
    

def solo(solo):
    """
    isolate output channels
    """

    options = {'lr', 'l', 'r'}
    if solo in options:
        init.state['solo'] = solo
        set_mixer()
    else:
        raise OptionsError(options)


# on/off commands


def drc(drc):
    """
    toggle drc
    """

    options = {'off', 'on', 'toggle'}
    if drc in options:
        if drc == 'toggle':
            drc = toggle('drc')
        init.state['drc'] = drc
        set_pipeline()
    else:
        raise OptionsError(options)


def phase_eq(phase_eq):
    """
    toggle phase equalizer
    """

    options = {'off', 'on', 'toggle'}
    if phase_eq in options:
        if phase_eq == 'toggle':
            phase_eq = toggle('phase_eq')
        init.state['phase_eq'] = phase_eq
        set_pipeline()
    else:
        raise OptionsError(options)


def loudness(loudness):
    """
    toggle loudness
    """

    options = {'off', 'on', 'toggle'}
    if loudness in options:
        if loudness == 'toggle':
            loudness = toggle('loudness')
        init.state['loudness'] = loudness

        # Put volume_filter filters after the mixer m.mixer
        mixer_index = cdsp_config['pipeline'].index(
            {'type': 'Mixer', 'name': 'm.mixer'}
            )

        if init.state['loudness'] == 'off':
            volume_filter = "f.volume"
        else:
            volume_filter = "f.loudness"

        cdsp_config['pipeline'][mixer_index + 1]['names'] = [volume_filter]
        cdsp_config['pipeline'][mixer_index + 2]['names'] = [volume_filter]
    else:
        raise OptionsError(options)


def tones(tones):
    """
    toggle tone controls
    """

    options = {'off', 'on', 'toggle'}
    if tones in options:
        if tones == 'toggle':
            tones = toggle('tones')
        init.state['tones'] = tones
        set_pipeline()
    else:
        raise OptionsError(options)


def eq(eq):
    """
    toggle general equalizer (not linked to a particular speaker)
    """

    options = {'off', 'on', 'toggle'}
    if eq in options:
        if eq == 'toggle':
            eq = toggle('eq')
        init.state['eq'] = eq
        set_pipeline()
    else:
        raise OptionsError(options)


def sources(sources):
    """
    toggle connection of sources
    """

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


def channels_flip(channels_flip):
    """
    toggle channels flip
    """
    
    options = {'off', 'on', 'toggle'}
    if channels_flip in options:
        if channels_flip == 'toggle':
            channels_flip = toggle('channels_flip')
        init.state['channels_flip'] = channels_flip
        set_mixer()
    else:
        raise OptionsError(options)
    

def polarity(polarity):
    """
    toggle polarity inversion
    """
    
    options = {'off', 'on', 'toggle'}
    if polarity in options:
        if polarity == 'toggle':
            polarity = toggle('polarity')
        init.state['polarity'] = polarity
        set_mixer()
    else:
        raise OptionsError(options)
    

def polarity_flip(polarity_flip):
    """
    toggle polarity flip (change polarity in one channel only)
    """
    
    options = {'off', 'on', 'toggle'}
    if polarity_flip in options:
        if polarity_flip == 'toggle':
            polarity_flip = toggle('polarity_flip')
        init.state['polarity_flip'] = polarity_flip
        set_mixer()
    else:
        raise OptionsError(options)
    

### funtions that perform actual backend adjustments


def set_pipeline():
    """
    set camilladsp pipeline from state settings
    """

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

    # Put selected filters after the volume or loudness filters, \
    # taken their fixed positions after mixer m.mixer
    mixer_index = cdsp_config['pipeline'].index(
        {'type': 'Mixer', 'name': 'm.mixer'}
        )
    cdsp_config['pipeline'][mixer_index + 3]['names'] = pipeline[0]
    cdsp_config['pipeline'][mixer_index + 4]['names'] = pipeline[1]


def set_mixer():
    """
    set general mixer in camilladsp from state settings
    """

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
        print(f'\n(control) mixer matrix : \n{mixer}\n')


def set_gain(gain):
    """
    set_gain, aka 'the volume machine' :-)
    gain is clamped to avoid positive gain \
    considering balance, tones and source gain shift
    """

    # gain command send its str argument directly
    gain = float(gain)
    # clamp gain value
    # just for information, numerical bounds before math range or \
    # math domain error are +6165 dB and -6472 dB
    # max gain is clamped downstream when calculating headroom
    if gain < base.gain_min:
        gain = base.gain_min
        print(f'\n(control) min. gain must be more than {base.gain_min} dB')
        print('(control) gain clamped')
    # calculate headroom and clamp gain if clamp_gain allows to do so
    if clamp_gain:
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
            print('\n(control) headroom hit, lowering gain...')
    else:
        cdsp.set_volume(gain)

### main command proccessing function


def proccess_commands(full_command):
    """
    procces commands for predic control
    """

    # let camilladsp connection be accessible
    global cdsp
    # let flag 'add' be accessible
    global add
    add = False
    
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
        if full_command[2] == 'add':
            add = True

    # initializes gain since it is calculated from level
    gain = pd.calc_gain(init.state['level'])

    ## parse  commands and select corresponding actions

    try:
        # commands without options
        if command in {'show'}:
            {
            'show':             show            #
            }[command]()

        # commands that do not depend on camilladsp config
        elif command in {'clamp', 'mute', 'level', 'gain'}:
            do_command(
            {
            # numerical commands that accept 'add'
            'level':            level,          #[level] add
            # on/off commands
            'clamp':            clamp,          #['off','on','toggle']
            'mute':             mute,           #['off','on','toggle']
            # special utility command
            'gain':             set_gain        #[gain]
            }[command], arg)

        # commands that depend on camilladsp config
        else:
            do_command(
            {
            # numerical commands that accept 'add'
            'loudness_ref':     loudness_ref,   #[loudness_ref] add
            'bass':             bass,           #[bass] add
            'treble':           treble,         #[treble] add
            'balance':          balance,        #[balance] add

            # non numerical commands
            'source':           source,         #[source]
            'drc_set':          drc_set,        #[drc_set]
            'eq_filter':        eq_filter,      #[eq_filter]
            'stereo':           stereo,         #['off','mid','side']
            'channels':         channels,       #['lr','l','r']
            'solo':             solo,           #['lr','l','r']

            # on/off commands
            'drc':              drc,            #['off','on','toggle']
            'phase_eq':         phase_eq,       #['off','on','toggle']
            'loudness':         loudness,       #['off','on','toggle']
            'tones':            tones,          #['off','on','toggle']
            'eq':               eq,             #['off','on','toggle']
            'sources':          sources,        #['off','on','toggle']
            'channels_flip':    channels_flip,  #['off','on','toggle']
            'polarity':         polarity,       #['off','on','toggle']
            'polarity_flip':    polarity_flip   #['off','on','toggle']
            }[command], arg)

        # dispatch config
        cdsp.set_config(cdsp_config)

    except KeyError:
        print(f"\n(control) Unknown command '{command}'")

# end of proccess_commands()
