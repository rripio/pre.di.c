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

from camilladsp import CamillaClient


# connect to camilladsp and get camilladsp config once
cdsp = CamillaClient("localhost", init.config['websocket_port'])
cdsp.connect()
cdsp_config = cdsp.config.active()


# flags


add = False             # switch to relative commands
do_mute = False         # mute during command

# gets camilladsp setting for volume ramp, and use it for mute waiting
ramp_time = cdsp_config['devices']['volume_ramp_time']/1000

message = ''

# exception definitions


class OptionsError(Exception):
    """
    exception for options revealing
    """

    def __init__(self, options):
        self.options = options


class ClampWarning(Warning):

    def __init__(self, clamp_value):
        self.clamp_value = clamp_value


# auxiliary functions


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


def do_source(source_arg):
    """
    wrapper for source command, avoiding muting already selected sources
    """

    global message
    global do_mute

    success = False

    sources = init.sources
    # sources check is done here, not in proper function
    if source_arg in sources:
        # check for already selected source
        if init.state['source'] == source_arg:
            message = 'source already selected'
        else:
            do_mute = True
            success = do_command(source, source_arg)
    else:
        message = f"source has to be in : {str(list(sources))}"

    return success


def do_command(command, arg):
    """
    general command wrapper
    """

    global message

    success = False

    # backup state to restore values in case of not enough headroom \
    # or error of any kind
    state_old = init.state.copy()

    if arg:
        try:
            if do_mute and init.config['do_mute']:
                cdsp.mute.set_main(True)
                # 2x volume ramp_time for security (estimated)
                time.sleep(ramp_time*2)

            command(arg)

        except ClampWarning as w:
            message = (f"'{command.__name__}' value clamped: {w.clamp_value}")
        except OptionsError as e:
            message = (f"options has to be in : {str(list(e.options))}")
        except ValueError as e:
            message = (f"command '{command.__name__}' needs a number: {e}")
        except Exception as e:
            # restore state as it was before command
            init.state[command.__name__] = state_old[command.__name__]
            message = (f"exception in command '{command.__name__}': {str(e)}")
        else:
            success = True
        finally:
            if do_mute and init.config['do_mute']:
                # 0.8x command_delay to give time for command to finish
                # (estimated)
                time.sleep(init.config['command_delay'] * 0.8)
                mute(init.state['mute'])

    else:
        message = f"command '{command.__name__}' needs an option"

    return success


# internal functions for commands


# commands that do not depend on camilladsp config


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

    options = {'off', 'on', 'toggle'}
    if clamp in options:
        if clamp == 'toggle':
            clamp = toggle('clamp')
        init.state['clamp'] = clamp
        if init.state['clamp'] == 'on':
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
        cdsp.mute.set_main({'off': False, 'on': True}[mute])
    else:
        raise OptionsError(options)


# commands that depend on camilladsp config


# numerical commands that accept 'add'


def loudness_ref(loudness_ref):
    """
    select loudness reference level (correction threshold level)
    """

    init.state['loudness_ref'] = (float(loudness_ref)
                                  + init.state['loudness_ref'] * add)

    # clamp loudness_ref value
    if abs(init.state['loudness_ref']) > base.loudness_ref_variation:
        init.state['loudness_ref'] = m.copysign(
                                    base.loudness_ref_variation,
                                    init.state['loudness_ref']
                                    )
        raise ClampWarning(init.state['loudness_ref'])
    # set loudness reference_level as absolute gain
    cdsp_config['filters']['f.loudness']['parameters']['reference_level'] = (
        pd.calc_gain(init.state['loudness_ref']))


def bass(bass):
    """
    select bass level correction
    """

    init.state['bass'] = float(bass) + init.state['bass'] * add
    # clamp bass value
    if m.fabs(init.state['bass']) > base.tone_variation:
        init.state['bass'] = m.copysign(
                            base.tone_variation, init.state['bass'])
        raise ClampWarning(init.state['bass'])
    # set bass
    cdsp_config['filters']['f.bass']['parameters']['gain'] = (
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
        init.state['treble'] = m.copysign(
                                base.tone_variation, init.state['treble'])
        raise ClampWarning(init.state['treble'])
    # set treble
    cdsp_config['filters']['f.treble']['parameters']['gain'] = (
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
    cdsp_config['filters']['f.balance.L']['parameters']['gain'] = (
        atten_dB_l
        )
    cdsp_config['filters']['f.balance.R']['parameters']['gain'] = (
        atten_dB_r
        )
    set_gain(pd.calc_gain(init.state['level']))


# non numerical commands


def source(source):
    """
    change source
    """

    global message

    # reset clamp to 'on' when changing sources
    init.state['clamp'] = 'on'

    # additional waiting after muting
    time.sleep(init.config['command_delay'] * 0.2)

    source_ports = init.sources[source]['source_ports']
    source_ports_len = len(source_ports)
    tmp = jack.Client('source_client')

    disconnect_sources(tmp)
    try:
        for ports_group in init.config['audio_ports']:
            # make no more than possible connections,
            # i.e., minimum of input or output ports
            num_ports = min(len(ports_group), source_ports_len)
            for i in range(num_ports):
                # audio sources
                tmp.connect(source_ports[i], ports_group[i])
    except Exception as e:
        message = f'error connecting ports: {e}'
        sources(init.state['sources'])
        return
    else:
        init.state['source'] = source
    finally:
        tmp.close()

    # source change went OK
    set_gain(pd.calc_gain(init.state['level']))
    # change phase_eq if configured so
    if init.config['use_source_phase_eq']:
        phase_eq(init.sources[source]['phase_eq'])

    # additional waiting before unmuting
    time.sleep(init.config['command_delay'] * 0.2)


def drc_set(drc_set):
    """
    change drc filters
    """

    options = init.drc
    if drc_set in options:
        init.state['drc_set'] = drc_set
        cdsp_config['filters']['f.drc.L'] = init.drc[drc_set]['f.drc.L']
        cdsp_config['filters']['f.drc.R'] = init.drc[drc_set]['f.drc.R']
        cdsp.config.set_active(cdsp_config)
    else:
        raise OptionsError(options)


def eq_filter(eq_filter):
    """
    select general equalizer filter
    """

    options = init.eq
    if eq_filter in options:
        init.state['eq_filter'] = eq_filter
        cdsp_config['filters']['f.eq'] = init.drc[drc_set]['f.eq']
        cdsp.config.set_active(cdsp_config)
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

        set_bypass('drc', drc)

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

        set_bypass('phase_eq', phase_eq)

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

        set_bypass('loudness', loudness)

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

        set_bypass('tones', tones)

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

        set_bypass('eq', eq)

    else:
        raise OptionsError(options)


def sources(sources):
    """
    toggle connection of sources
    """

    global message

    options = {'off', 'on', 'toggle'}
    if sources in options:
        if sources == 'toggle':
            sources = toggle('sources')
        init.state['sources'] = sources
        tmp = jack.Client('sources_client')
        match sources:
            case 'off':
                disconnect_sources(tmp)
                tmp.close()
            case 'on':
                # first check for source ports existence
                source_selected = init.state['source']
                source_ports = init.sources[source_selected]['source_ports']
                delay = init.config['command_delay'] * 0.1
                if pd.wait4ports(source_ports, delay):
                    source(source_selected)
                else:
                    message = 'error: source ports are down'
                tmp.close()
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


def set_bypass(step, arg):
    """
    set bypass state of certain steps in pipeline
    """

    state = {'off': True, 'on': False}[arg]

    for index, element in enumerate(cdsp_config['pipeline']):
        if element['description'] == step:
            cdsp_config['pipeline'][index]['bypassed'] = state


def set_mixer():
    """
    set general mixer in camilladsp from state settings
    """

    global message

    mixer = np.identity(2)

    if init.state['channels_flip'] == 'on':
        mixer = np.array([[0, 1], [1, 0]])

    match init.state['channels']:
        case 'l':       mixer = mixer @ np.array([[1, 1], [0, 0]])
        case 'r':       mixer = mixer @ np.array([[0, 0], [1, 1]])

    match init.state['stereo']:
        case 'mid':     mixer = mixer @ np.array([[0.5, 0.5], [0.5, 0.5]])
        case 'side':    mixer = mixer @ np.array([[0.5, 0.5], [-0.5, -0.5]])

    if init.state['polarity'] == 'on':
        mixer = mixer @ np.array([[-1, 0], [0, -1]])

    if init.state['polarity_flip'] == 'on':
        mixer = mixer @ np.array([[1, 0], [0, -1]])

    match init.state['solo']:
        case 'l':       mixer = mixer * np.array([[1, 0], [1, 0]])
        case 'r':       mixer = mixer * np.array([[0, 1], [0, 1]])

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
        message = f'mixer matrix : \n{mixer}'


def set_gain(gain):
    """
    set_gain, aka 'the volume machine' :-)
    gain is clamped to avoid positive gain \
    considering balance, tones and source gain shift
    """

    global message

    # gain command send its str argument directly
    gain = float(gain)
    # clamp gain value
    # just for information, numerical bounds before math range or \
    # math domain error are +6165 dB and -6472 dB
    # max gain is clamped downstream when calculating headroom
    if gain < base.gain_min:
        gain = base.gain_min
        message = (f'min. gain must be more than {base.gain_min} ' +
                   + 'dB\ngain clamped')
    # calculate headroom and clamp gain if clamp_gain allows to do so
    if init.state['clamp'] == 'on':
        headroom = pd.calc_headroom(gain)
        # adds source gain. It can lead to clipping \
        # because assumes equal dynamic range between sources
        real_gain = gain + pd.calc_source_gain(init.state['source'])
        # if enough headroom commit changes
        # since there is no init.state['gain'] we set init.state['level']
        if headroom >= 0:
            cdsp.volume.set_main(real_gain)
            init.state['level'] = pd.calc_level(gain)
        # if not enough headroom tries lowering gain
        else:
            set_gain(gain + headroom)
            message = 'headroom hit, lowering gain...'
    else:
        cdsp.volume.set_main(gain)


# main command proccessing function


def proccess_commands(full_command):
    """
    procces commands for predic control
    """

    global cdsp             # let camilladsp connection be accesible
    global add
    global do_mute
    global message

    add = False
    do_mute = False
    success = False

    # strips command final characters and split command from arguments
    full_command = full_command.split()
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

    # parse  commands and select corresponding actions

    try:
        # commands that do not depend on camilladsp config

        if command in {'clamp', 'mute', 'level', 'gain'}:
            success = do_command(
             {
                # numerical commands that accept 'add'
                'level':            level,          # [level] add
                # on/off commands
                'clamp':            clamp,          # ['off','on','toggle']
                'mute':             mute,           # ['off','on','toggle']
                # special utility command
                'gain':             set_gain        # [gain]
                }[command], arg)

        # commands that depend on camilladsp config

        elif command == 'source':
            # source                            # [source]
            success = do_source(arg)
            # dispatch config
            cdsp.config.set_active(cdsp_config)

        elif command in {'loudness_ref', 'bass', 'treble', 'balance'}:
            success = do_command(
             {
                # numerical commands that accept 'add'
                'loudness_ref':     loudness_ref,   # [loudness_ref] add
                'bass':             bass,           # [bass] add
                'treble':           treble,         # [treble] add
                'balance':          balance,        # [balance] add
                }[command], arg)
            # dispatch config
            cdsp.config.set_active(cdsp_config)

        else:
            # these commands benefit for silencing switching noise
            do_mute = True
            success = do_command(
             {
                # non numerical commands
                'drc_set':          drc_set,        # [drc_set]
                'eq_filter':        eq_filter,      # [eq_filter]
                'stereo':           stereo,         # ['off','mid','side']
                'channels':         channels,       # ['lr','l','r']
                'solo':             solo,           # ['lr','l','r']

                # on/off commands
                'drc':              drc,            # ['off','on','toggle']
                'phase_eq':         phase_eq,       # ['off','on','toggle']
                'loudness':         loudness,       # ['off','on','toggle']
                'tones':            tones,          # ['off','on','toggle']
                'eq':               eq,             # ['off','on','toggle']
                'sources':          sources,        # ['off','on','toggle']
                'channels_flip':    channels_flip,  # ['off','on','toggle']
                'polarity':         polarity,       # ['off','on','toggle']
                'polarity_flip':    polarity_flip   # ['off','on','toggle']
                }[command], arg)
            # dispatch config
            cdsp.config.set_active(cdsp_config)

    except KeyError:
        message = f"unknown command '{command}'"

    return success


# end of proccess_commands()
