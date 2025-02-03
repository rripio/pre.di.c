# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Process commands."""

import time
import jack
import math as m

import numpy as np

import baseconfig as base
import init
import pdlib as pd

from camilladsp import CamillaClient


# Connect to camilladsp and get camilladsp config once.
cdsp = CamillaClient("localhost", init.config['websocket_port'])
cdsp.connect()
cdsp_config = cdsp.config.active()


# Flags


add = False             # Switch to relative commands.
do_mute = False         # Mute during command.

# Gets camilladsp setting for volume ramp, and use it for mute waiting.
ramp_time = cdsp_config['devices']['volume_ramp_time']/1000

message = ''

# Exception definitions


class OptionsError(Exception):
    """Exception for options revealing."""

    def __init__(self, options):
        self.options = options


class ClampWarning(Warning):
    """Exception for volume clamp."""

    def __init__(self, clamp_value):
        self.clamp_value = clamp_value


# Auxiliary functions


def disconnect_sources(jack_client):
    """Disconnect sources from predic audio ports."""
    for ports_group in init.config['audio_ports']:
        for in_port in ports_group:
            for out_port in jack_client.get_all_connections(in_port):
                jack_client.disconnect(out_port, in_port)


def toggle(command):
    """Change state of on/off commands."""
    return {'off': 'on', 'on': 'off'}[init.state[command]]


def do_source(source_arg):
    """Process source commands, avoiding muting already selected sources."""
    global message
    global do_mute

    success = False

    sources = init.sources
    # Sources check is done here, not in proper function.
    if source_arg in sources:
        # Check for already selected source.
        if init.state['source'] == source_arg:
            message = 'source already selected'
        else:
            do_mute = True
            success = do_command(source, source_arg)
    else:
        message = f"source has to be in : {str(list(sources))}"

    return success


def do_command(command, arg):
    """General command wrapper."""
    global message

    success = False

    # Backup state to restore values in case of not enough headroom
    # or error of any kind.
    state_old = init.state.copy()

    if arg:
        try:
            if do_mute and init.config['do_mute']:
                cdsp.volume.set_main_mute(True)
                # 2x volume ramp_time for security (estimated).
                time.sleep(ramp_time*2)

            command(arg)

        except ClampWarning as w:
            message = (f"'{command.__name__}' value clamped: {w.clamp_value}")
        except OptionsError as e:
            options = str(list(e.options))
            message = (
                f"'{command.__name__}' options have to be in: {options}")
        except ValueError as e:
            message = (f"command '{command.__name__}' needs a number: {e}")
        except Exception as e:
            # Restore state as it was before command.
            init.state[command.__name__] = state_old[command.__name__]
            message = (f"exception in command '{command.__name__}': {str(e)}")
        else:
            success = True
        finally:
            if do_mute and init.config['do_mute']:
                # 0.8x command_delay to give time for command to finish
                # (estimated).
                time.sleep(init.config['command_delay'] * 0.8)
                mute(init.state['mute'])

    else:
        message = f"command '{command.__name__}' needs an option"

    return success


# Internal functions for commands

# Commands that do not depend on camilladsp config.

# Numerical commands that accept 'add'.

def level(level):
    """Change level (gain relative to reference_level)."""
    # level clamp is comissioned to set_gain()
    init.state['level'] = (float(level) + init.state['level'] * add)
    gain = pd.calc_gain(init.state['level'])
    set_gain(gain)


# on/off commands.

def clamp(clamp):
    """Free gain setting from clamping, useful for playing  low level files."""
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
    """Mute output."""
    options = {'off', 'on', 'toggle'}
    if mute in options:
        if mute == 'toggle':
            mute = toggle('mute')
        init.state['mute'] = mute
        cdsp.volume.set_main_mute({'off': False, 'on': True}[mute])
    else:
        raise OptionsError(options)


# Commands that depend on camilladsp config.

# Numerical commands that accept 'add'.

def loudness_ref(loudness_ref):
    """Select loudness reference level (correction threshold level)."""
    init.state['loudness_ref'] = (float(loudness_ref)
                                  + init.state['loudness_ref'] * add)

    # Clamp loudness_ref value.
    if abs(init.state['loudness_ref']) > base.loudness_ref_variation:
        init.state['loudness_ref'] = m.copysign(
                                    base.loudness_ref_variation,
                                    init.state['loudness_ref']
                                    )
        raise ClampWarning(init.state['loudness_ref'])
    # Set loudness reference_level as absolute gain.
    cdsp_config['filters']['f.loudness']['parameters']['reference_level'] = (
        pd.calc_gain(init.state['loudness_ref']))


def bass(bass):
    """Select bass level correction."""
    init.state['bass'] = float(bass) + init.state['bass'] * add
    # Clamp bass value.
    if m.fabs(init.state['bass']) > base.tone_variation:
        init.state['bass'] = m.copysign(
                            base.tone_variation, init.state['bass'])
        raise ClampWarning(init.state['bass'])
    # Set bass.
    cdsp_config['filters']['f.bass']['parameters']['gain'] = (
        init.state['bass']
        )
    set_gain(pd.calc_gain(init.state['level']))


def treble(treble):
    """Select treble level correction."""
    init.state['treble'] = (float(treble)
                            + init.state['treble'] * add)
    # Clamp treble value.
    if m.fabs(init.state['treble']) > base.tone_variation:
        init.state['treble'] = m.copysign(
                                base.tone_variation, init.state['treble'])
        raise ClampWarning(init.state['treble'])
    # Set treble.
    cdsp_config['filters']['f.treble']['parameters']['gain'] = (
        init.state['treble']
        )
    set_gain(pd.calc_gain(init.state['level']))


def balance(balance):
    """
    Select balance level.

    'Balance' means deviation from 0 in R channel.
    Deviation of the L channel then goes symmetrical.
    """
    init.state['balance'] = (float(balance)
                             + init.state['balance'] * add)
    # Clamp balance value.
    if m.fabs(init.state['balance']) > base.balance_variation:
        init.state['balance'] = m.copysign(
                                base.balance_variation,
                                init.state['balance']
                                )
        raise ClampWarning(init.state['balance'])
    # Add balance dB gains.
    atten_dB_r = init.state['balance']
    atten_dB_l = - (init.state['balance'])
    cdsp_config['filters']['f.balance.L']['parameters']['gain'] = (
        atten_dB_l
        )
    cdsp_config['filters']['f.balance.R']['parameters']['gain'] = (
        atten_dB_r
        )
    set_gain(pd.calc_gain(init.state['level']))


# Non numerical commands.

def source(source):
    """Change source."""
    global message

    # Reset clamp to 'on' when changing sources.
    init.state['clamp'] = 'on'

    # Additional waiting after muting.
    if do_mute and init.config['do_mute']:
        time.sleep(init.config['command_delay'] * 0.5)

    source_ports = init.sources[source]['source_ports']
    source_ports_len = len(source_ports)
    tmp = jack.Client('source_client')

    disconnect_sources(tmp)
    try:
        for ports_group in init.config['audio_ports']:
            # Make no more than possible connections,
            # i.e., minimum of input or output ports.
            num_ports = min(len(ports_group), source_ports_len)
            for i in range(num_ports):
                # Audio sources.
                tmp.connect(source_ports[i], ports_group[i])
    except Exception as e:
        message = f'error connecting ports: {e}'
        sources(init.state['sources'])
        return
    else:
        init.state['source'] = source
    finally:
        tmp.close()

    # Source change went OK.
    set_gain(pd.calc_gain(init.state['level']))
    # Change phase_eq if configured so.
    if init.config['use_source_phase_eq']:
        # reveal error if 'on'/'off' options lacks quotes in config
        try:
            phase_eq(init.sources[source]['phase_eq'])
        except OptionsError as e:
            options = str(list(e.options))
            message = (f"'phase_eq' options have to be in : {options}")

    # Additional waiting before unmuting.
    if do_mute and init.config['do_mute']:
        time.sleep(init.config['command_delay'] * 0.5)


def drc_set(drc_set):
    """Change drc filters."""
    options = init.drc
    if drc_set in options:
        init.state['drc_set'] = drc_set
        cdsp_config['filters']['f.drc.L'] = init.drc[drc_set]['f.drc.L']
        cdsp_config['filters']['f.drc.R'] = init.drc[drc_set]['f.drc.R']
        cdsp.config.set_active(cdsp_config)
    else:
        raise OptionsError(options)


def eq_filter(eq_filter):
    """Select general equalizer filter."""
    options = init.eq
    if eq_filter in options:
        init.state['eq_filter'] = eq_filter
        cdsp_config['filters']['f.eq'] = init.drc[drc_set]['f.eq']
        cdsp.config.set_active(cdsp_config)
    else:
        raise OptionsError(options)


def stereo(stereo):
    """Change mix to normal stereo, mono, or midside side."""
    options = {'normal', 'mid', 'side'}
    if stereo in options:
        init.state['stereo'] = stereo
        set_mixer()
    else:
        raise OptionsError(options)


def channels(channels):
    """Select input channels (mixed to both output channels)."""
    options = {'lr', 'l', 'r'}
    if channels in options:
        init.state['channels'] = channels
        set_mixer()
    else:
        raise OptionsError(options)


def solo(solo):
    """Isolate output channels."""
    options = {'lr', 'l', 'r'}
    if solo in options:
        init.state['solo'] = solo
        set_mixer()
    else:
        raise OptionsError(options)


# on/off commands.

def drc(drc):
    """Toggle drc."""
    options = {'off', 'on', 'toggle'}
    if drc in options:
        if drc == 'toggle':
            drc = toggle('drc')
        init.state['drc'] = drc

        set_bypass('drc', drc)

    else:
        raise OptionsError(options)


def phase_eq(phase_eq):
    """Toggle phase equalizer."""
    options = {'off', 'on', 'toggle'}
    if phase_eq in options:
        if phase_eq == 'toggle':
            phase_eq = toggle('phase_eq')
        init.state['phase_eq'] = phase_eq

        set_bypass('phase_eq', phase_eq)

    else:
        raise OptionsError(options)


def loudness(loudness):
    """Toggle loudness."""
    options = {'off', 'on', 'toggle'}
    if loudness in options:
        if loudness == 'toggle':
            loudness = toggle('loudness')
        init.state['loudness'] = loudness

        set_bypass('loudness', loudness)

    else:
        raise OptionsError(options)


def tones(tones):
    """Toggle tone controls."""
    options = {'off', 'on', 'toggle'}
    if tones in options:
        if tones == 'toggle':
            tones = toggle('tones')
        init.state['tones'] = tones

        set_bypass('tones', tones)

    else:
        raise OptionsError(options)


def eq(eq):
    """Toggle general equalizer (not linked to a particular speaker)."""
    options = {'off', 'on', 'toggle'}
    if eq in options:
        if eq == 'toggle':
            eq = toggle('eq')
        init.state['eq'] = eq

        set_bypass('eq', eq)

    else:
        raise OptionsError(options)


def sources(sources):
    """Toggle connection of sources."""
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
                # First check for source ports existence.
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
    """Toggle channels flip."""
    options = {'off', 'on', 'toggle'}
    if channels_flip in options:
        if channels_flip == 'toggle':
            channels_flip = toggle('channels_flip')
        init.state['channels_flip'] = channels_flip
        set_mixer()
    else:
        raise OptionsError(options)


def polarity(polarity):
    """Toggle polarity inversion."""
    options = {'off', 'on', 'toggle'}
    if polarity in options:
        if polarity == 'toggle':
            polarity = toggle('polarity')
        init.state['polarity'] = polarity
        set_mixer()
    else:
        raise OptionsError(options)


def polarity_flip(polarity_flip):
    """Toggle polarity flip (change polarity in one channel only)."""
    options = {'off', 'on', 'toggle'}
    if polarity_flip in options:
        if polarity_flip == 'toggle':
            polarity_flip = toggle('polarity_flip')
        init.state['polarity_flip'] = polarity_flip
        set_mixer()
    else:
        raise OptionsError(options)


def set_bypass(step, arg):
    """Set bypass state of certain steps in pipeline."""
    state = {'off': True, 'on': False}[arg]

    for index, element in enumerate(cdsp_config['pipeline']):
        if element['description'] == step:
            cdsp_config['pipeline'][index]['bypassed'] = state


def set_mixer():
    """Set general mixer in camilladsp from state settings."""
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

    # Gain
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

    # Inverted
    for sources in range(2):
        for dest in range(2):
            (cdsp_config['mixers']['m.mixer']['mapping'][dest]
                ['sources'][sources]['inverted']) = (
                    bool(mixer[sources, dest] < 0)
                    )

    # Mute
    for sources in range(2):
        for dest in range(2):
            (cdsp_config['mixers']['m.mixer']['mapping'][dest]
                ['sources'][sources]['mute']) = (
                    not bool(mixer[sources, dest])
                    )

    # For debug
    if init.config['verbose'] in {1, 2}:
        message = f'mixer matrix : \n{mixer}'


def set_gain(gain):
    """
    Set_gain, aka 'the volume machine'.

    Gain is clamped to avoid positive gain,
    considering balance, tones and source gain shift.
    """
    global message

    # Gain command send its str argument directly.
    gain = float(gain)
    # Clamp gain value.
    # Just for information, numerical bounds before math range or
    # math domain error are +6165 dB and -6472 dB.
    # Max gain is clamped downstream when calculating headroom.
    if gain < base.gain_min:
        gain = base.gain_min
        message = (f'min. gain must be more than {base.gain_min} ' +
                   + 'dB\ngain clamped')
    # Calculate headroom and clamp gain if clamp_gain allows to do so.
    if init.state['clamp'] == 'on':
        headroom = pd.calc_headroom(gain)
        # Adds source gain. It can lead to clipping
        # because assumes equal dynamic range between sources.
        real_gain = gain + pd.calc_source_gain(init.state['source'])
        # If enough headroom commit changes.
        # Since there is no init.state['gain'] we set init.state['level'].
        if headroom >= 0:
            cdsp.volume.set_main_volume(real_gain)
            init.state['level'] = pd.calc_level(gain)
        # If not enough headroom tries lowering gain.
        else:
            set_gain(gain + headroom)
            message = 'headroom hit, lowering gain...'
    else:
        cdsp.volume.set_main_volume(gain)


# Main command proccessing function.
def proccess_commands(full_command):
    """Procces commands for predic control."""
    global cdsp             # let camilladsp connection be accesible
    global add
    global do_mute
    global message

    add = False
    do_mute = False
    success = False

    # Strips command final characters and split command from arguments.
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

    # Parse  commands and select corresponding actions.
    try:
        # Commands that do not depend on camilladsp config.

        if command in {'clamp', 'mute', 'level', 'gain'}:
            success = do_command(
             {
                # Numerical commands that accept 'add'.
                'level':            level,          # [level] add
                # on/off commands.
                'clamp':            clamp,          # ['off','on','toggle']
                'mute':             mute,           # ['off','on','toggle']
                # Special utility command.
                'gain':             set_gain        # [gain]
                }[command], arg)

        # Commands that depend on camilladsp config.

        elif command == 'source':
            success = do_source(arg)                # [source]
            # Dispatch config.
            cdsp.config.set_active(cdsp_config)

        elif command in {'loudness_ref', 'bass', 'treble', 'balance'}:
            success = do_command(
             {
                # Numerical commands that accept 'add'.
                'loudness_ref':     loudness_ref,   # [loudness_ref] add
                'bass':             bass,           # [bass] add
                'treble':           treble,         # [treble] add
                'balance':          balance,        # [balance] add
                }[command], arg)
            # Dispatch config.
            cdsp.config.set_active(cdsp_config)

        else:
            # These commands benefit for silencing switching noise.
            do_mute = True
            success = do_command(
             {
                # Non numerical commands.
                'drc_set':          drc_set,        # [drc_set]
                'eq_filter':        eq_filter,      # [eq_filter]
                'stereo':           stereo,         # ['off','mid','side']
                'channels':         channels,       # ['lr','l','r']
                'solo':             solo,           # ['lr','l','r']

                # on/off commands.
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
            # Dispatch config.
            cdsp.config.set_active(cdsp_config)

    except KeyError:
        message = f"unknown command '{command}'"

    return success

# End of proccess_commands().
